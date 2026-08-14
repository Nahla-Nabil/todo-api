"""The one module that talks to Supabase Auth. Every route in main.py that
needs to sign a user up, log them in/out, or verify a token calls a function
here — nothing outside this file touches the Supabase SDK directly.

Same shape as db.py and cache.py: a fresh client per call instead of one
shared global. That matters more here than it looks — the Python SDK's
sign_in/sign_out calls store session state *on the client object*, so a
single shared client would leak one user's session into another user's
concurrent request.
"""

import os

from dotenv import load_dotenv
from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

# auto_error=False so a missing/malformed Authorization header lands in
# require_user() as credentials=None instead of FastAPI's generic 403 —
# that's what lets us return the exact 401 bodies the spec asks for. Using
# this scheme as a dependency is also what makes the Swagger "Authorize"
# padlock appear on protected routes for free (Stage 5).
bearer_scheme = HTTPBearer(auto_error=False)


class AuthError(Exception):
    """Carries a status code and message straight through to the handler
    registered in main.py, so every auth failure responds with
    {"error": "..."} instead of FastAPI's default {"detail": "..."}."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message


class AuthedUser:
    """What require_user() hands to a route: the verified user's safe
    metadata plus the raw token, since /auth/logout needs the token again
    to ask Supabase to revoke the session."""

    def __init__(self, id: str, email: str | None, created_at: str | None, token: str):
        self.id = id
        self.email = email
        self.created_at = created_at
        self.token = token


def get_client() -> Client:
    """A fresh Supabase client per call — see the module docstring."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def ping() -> None:
    """Confirms SUPABASE_URL/SUPABASE_KEY are present and well-formed by
    constructing a client — same "fail fast on startup" reasoning as
    db.init_db() and cache.ping_with_retry()."""
    get_client()


def sign_up(email: str, password: str):
    return get_client().auth.sign_up({"email": email, "password": password})


def sign_in(email: str, password: str):
    return get_client().auth.sign_in_with_password({"email": email, "password": password})


def get_user(token: str):
    """Asks Supabase whether `token` is real — a network call, so the
    answer is trustworthy (unlike just decoding the JWT locally)."""
    return get_client().auth.get_user(token)


def sign_out(token: str) -> None:
    """Best-effort sign-out. The SDK's sign_out() reads session state off
    the client object, which we don't have from just a bearer token — so
    this builds a throwaway client and primes it with set_session() first.

    Either way, the access token itself stays valid until it naturally
    expires (JWTs are stateless — nothing server-side can un-sign them).
    This only revokes the refresh token / session, which is why the route
    calling this still returns 204 even if the Supabase call fails: the
    token was already verified valid before we got here.
    """
    client = get_client()
    client.auth.set_session(token, token)
    client.auth.sign_out()


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> AuthedUser:
    """The reusable guard. Apply as Depends(require_user) to any route that
    should only answer for a logged-in user — written once here, reused by
    /protected/profile, /protected/dashboard, and /auth/logout.
    """
    if credentials is None or not credentials.credentials:
        raise AuthError(401, "Access token required")

    token = credentials.credentials
    try:
        user = get_user(token).user
    except Exception:
        user = None

    if user is None:
        raise AuthError(401, "Invalid or expired token")

    return AuthedUser(
        id=user.id,
        email=user.email,
        created_at=str(user.created_at) if user.created_at else None,
        token=token,
    )
