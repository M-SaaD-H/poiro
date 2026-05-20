"""FastAPI dependency for extracting and validating the current authenticated user."""

import logging
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import decode_access_token
from app.database import get_session

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> uuid.UUID:
    """Extract and validate the Bearer JWT, returning the user's UUID.

    Raises HTTP 401 if the token is missing, malformed, or expired.
    """
    try:
        user_id_str = decode_access_token(credentials.credentials)
        return uuid.UUID(user_id_str)
    except (JWTError, ValueError) as exc:
        logger.warning("Invalid JWT token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> "User":  # type: ignore[name-defined]  # noqa: F821
    """Resolve the current user from the database.

    Raises HTTP 401 if the user no longer exists.
    """
    from app.auth.models import User  # local import to avoid circular deps

    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
