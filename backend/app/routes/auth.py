"""
routes/auth.py

Authentication routes for VeriSight officers.

Endpoints:
  POST   /auth/signup   — Register a new officer account
  POST   /auth/login    — Sign in, receive JWT tokens
  GET    /auth/me       — Return the authenticated officer's profile
  POST   /auth/refresh  — Refresh an expired access_token
"""

from fastapi import APIRouter, HTTPException, Depends
try:
    # pyrefly: ignore [missing-import]
    from gotrue.errors import AuthApiError
except ImportError:
    try:
        # pyrefly: ignore [missing-import]
        from supabase_auth.errors import AuthApiError
    except ImportError:
        class AuthApiError(Exception):
            pass

from app.schemas.officer import OfficerSignup, OfficerLogin, TokenRefresh
from app.services.supabase import supabase, supabase_admin
from app.dependencies.auth import get_current_user

router = APIRouter()


# ----------------------------------------------------------------
# POST /auth/signup
# ----------------------------------------------------------------
@router.post("/signup", summary="Register a new officer")
async def signup(officer: OfficerSignup):
    """
    Create a Supabase Auth account and insert the officer profile row.

    Returns the officer_id on success.
    """
    # 1. Create auth account
    try:
        auth_response = supabase.auth.sign_up({
            "email":    officer.officer_email,
            "password": officer.password,
        })
    except AuthApiError as exc:
        msg = str(exc).lower()
        if "rate limit" in msg:
            raise HTTPException(
                status_code=429,
                detail="Email signup rate limit exceeded. Please try again later.",
            ) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to create account: {exc}",
        ) from exc

    if not auth_response.user:
        raise HTTPException(
            status_code=400,
            detail="Unable to create account. The email may already be in use.",
        )

    user_id = auth_response.user.id

    # 2. Insert officer profile (uses admin client to bypass RLS)
    profile = {
        "id":            user_id,
        "first_name":    officer.first_name,
        "last_name":     officer.last_name,
        "officer_id":    officer.officer_id,
        "officer_email": officer.officer_email,
        "organization":  officer.organization,
        "designation":   officer.designation,
    }

    profile_response = (
        supabase_admin
        .table("officer_profiles")
        .insert(profile)
        .execute()
    )

    if not profile_response.data:
        # Auth account was created but profile insert failed —
        # attempt a best-effort cleanup so the email is not orphaned.
        try:
            supabase_admin.auth.admin.delete_user(user_id)
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail="Officer account was created but profile could not be saved. Please try again.",
        )

    return {
        "message":    "Officer account created successfully.",
        "officer_id": officer.officer_id,
    }


# ----------------------------------------------------------------
# POST /auth/login
# ----------------------------------------------------------------
def _resolve_login_email(officer: OfficerLogin) -> str:
    """Map officer_id to officer_email when only ID is provided."""
    if officer.officer_email:
        return str(officer.officer_email)

    response = (
        supabase_admin
        .table("officer_profiles")
        .select("officer_email")
        .eq("officer_id", officer.officer_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=401,
            detail="Invalid officer ID or password.",
        )

    return response.data[0]["officer_email"]


@router.post("/login", summary="Sign in and receive JWT tokens")
async def login(officer: OfficerLogin):
    """
    Sign in with officer_id or officer_email plus password.

    Password is verified by Supabase Auth (auth.users), not officer_profiles.
    Returns access_token (short-lived JWT) and refresh_token.
    """
    email = _resolve_login_email(officer)

    try:
        response = supabase.auth.sign_in_with_password({
            "email":    email,
            "password": officer.password,
        })

        if not response.session or not response.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials.",
            )

        # Ensure this auth user is a registered officer
        profile = (
            supabase_admin
            .table("officer_profiles")
            .select("id")
            .eq("id", response.user.id)
            .limit(1)
            .execute()
        )

        if not profile.data:
            raise HTTPException(
                status_code=403,
                detail="Account exists but is not registered as an officer.",
            )

        return {
            "message":       "Login successful.",
            "access_token":  response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type":    "bearer",
            "expires_in":    response.session.expires_in,
        }

    except HTTPException:
        raise

    except AuthApiError:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials.",
        )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials.",
        )


# ----------------------------------------------------------------
# GET /auth/me
# ----------------------------------------------------------------
@router.get("/me", summary="Get the authenticated officer's profile")
async def get_me(current_user=Depends(get_current_user)):
    """
    Return the full officer profile for the authenticated user.

    Requires: Authorization: Bearer <access_token>
    """
    response = (
        supabase_admin
        .table("officer_profiles")
        .select("*")
        .eq("id", current_user.id)
        .single()
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Officer profile not found.",
        )

    return response.data


# ----------------------------------------------------------------
# POST /auth/refresh
# ----------------------------------------------------------------
@router.post("/refresh", summary="Refresh an expired access token")
async def refresh_token(body: TokenRefresh):
    """
    Exchange a valid refresh_token for a new access_token.

    The old refresh_token is invalidated after use.
    """
    try:
        response = supabase.auth.refresh_session(body.refresh_token)

        if not response.session:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired refresh token.",
            )

        return {
            "access_token":  response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type":    "bearer",
            "expires_in":    response.session.expires_in,
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token.",
        )
