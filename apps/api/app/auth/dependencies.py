"""FastAPI dependency for extracting and validating the current authenticated user.

Accepts Bearer tokens issued by Supabase Auth (HS256 JWTs).
"""

import logging
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import verify_supabase_token
from app.database import get_session

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> uuid.UUID:
    """Extract and validate the Supabase Bearer JWT, returning the user's UUID.

    Raises HTTP 401 if the token is missing, malformed, or expired.
    """
    try:
        return verify_supabase_token(credentials.credentials)
    except (JWTError, ValueError) as exc:
        logger.warning("Invalid Supabase JWT: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> "User":  # type: ignore[name-defined]  # noqa: F821
    """Resolve the current user from the public.users profile table.

    Raises HTTP 401 if the profile row does not exist.
    """
    from app.auth.models import User  # local import to avoid circular deps

    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User profile not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
