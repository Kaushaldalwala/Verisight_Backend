"""
auth.py  (dependencies)

FastAPI dependency that validates a Supabase JWT and returns the
authenticated user object.

Usage:
    current_user = Depends(get_current_user)
    officer_id   = current_user.id
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.supabase import supabase

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Extract and validate the Bearer token from the Authorization header.

    Raises 401 if the token is missing, expired, or invalid.
    Returns the Supabase user object on success.
    """
    token = credentials.credentials

    try:
        response = supabase.auth.get_user(token)

        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return response.user

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
