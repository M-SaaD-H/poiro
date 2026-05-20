"""Authentication service: password hashing, JWT creation and verification."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the given plain-text password."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the plain password matches the bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str | uuid.UUID) -> str:
    """Create a signed JWT with the given subject (user id) and configured expiry."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, str] = {
        "sub": str(subject),
        "exp": str(int(expire.timestamp())),
        "iat": str(int(datetime.now(timezone.utc).timestamp())),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> str:
    """Decode and validate a JWT, returning the subject (user id string).

    Raises JWTError on invalid or expired tokens.
    """
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    subject: str | None = payload.get("sub")
    if subject is None:
        raise JWTError("Token missing 'sub' claim")
    return subject
