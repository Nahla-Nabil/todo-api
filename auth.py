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
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]


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
