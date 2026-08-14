"""
Supabase-authenticated REST API built with FastAPI.

Five routes:
    POST /auth/signup          - create a Supabase user
    POST /auth/login           - exchange email/password for tokens
    POST /auth/logout          - protected, invalidate the current session
    GET  /protected/profile    - protected, return the caller's profile
    GET  /public/info          - open to everyone

Run with:
    uvicorn main:app --reload
"""

import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from supabase import Client, create_client

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY must be set (see .env.example). "
        "Create a .env file with real Supabase project credentials."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(
    title="Supabase Auth API",
    description="A small FastAPI app that adds Supabase-based authentication to a REST API.",
    version="1.0.0",
)

# HTTPBearer security scheme -> makes Swagger UI show the "Authorize" padlock
# on any route that depends on it.
bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------
# The spec requires bare error bodies like {"error": "..."} rather than
# FastAPI's default {"detail": ...} envelope, so HTTPExceptions raised with a
# dict `detail` are returned as-is.


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class AuthCredentials(BaseModel):
    """Body for /auth/signup and /auth/login.

    Fields are optional at the model level so that a missing email/password
    results in the spec's 400 response instead of FastAPI's default 422
    validation error.
    """

    email: Optional[str] = None
    password: Optional[str] = None


# ---------------------------------------------------------------------------
# Auth dependency (reused by every protected route)
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """Verify the bearer token against Supabase and return the caller's info.

    Raises:
        401 {"error": "Access token required"}   - no Authorization header sent
        401 {"error": "Invalid or expired token"} - Supabase rejects the token
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Access token required"},
        )

    token = credentials.credentials

    try:
        user_response = supabase.auth.get_user(token)
    except Exception:
        user_response = None

    user = getattr(user_response, "user", None) if user_response else None

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid or expired token"},
        )

    return {"user": user, "token": token}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
async def signup(credentials: AuthCredentials):
    if not credentials.email or not credentials.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Email and password are required"},
        )

    try:
        result = supabase.auth.sign_up(
            {"email": credentials.email, "password": credentials.password}
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(exc)},
        )

    user = result.user
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Signup failed"},
        )

    return {"id": user.id, "email": user.email}


@app.post("/auth/login")
async def login(credentials: AuthCredentials):
    if not credentials.email or not credentials.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Email and password are required"},
        )

    try:
        result = supabase.auth.sign_in_with_password(
            {"email": credentials.email, "password": credentials.password}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid login credentials"},
        )

    if result.session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid login credentials"},
        )

    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
    }


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: dict = Depends(get_current_user)):
    try:
        supabase.auth.sign_out()
    except Exception:
        # Even if Supabase's sign-out call itself fails, the token has
        # already been verified above; there is nothing meaningful left
        # for the client to retry, so we still report success.
        pass

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/protected/profile")
async def profile(current_user: dict = Depends(get_current_user)):
    user = current_user["user"]
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at,
    }


@app.get("/public/info")
async def public_info():
    return {"message": "Welcome stranger! This info is public."}


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
