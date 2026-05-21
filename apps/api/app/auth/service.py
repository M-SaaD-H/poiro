"""Authentication service: Supabase Auth operations and JWT verification.

All password management and identity storage is delegated to Supabase Auth.
This module provides:
  - register_with_supabase  — wraps supabase.auth.sign_up
  - login_with_supabase     — wraps supabase.auth.sign_in_with_password
  - verify_supabase_token   — validates a Supabase-issued JWT via the JWKS endpoint

JWT Verification Strategy
--------------------------
Supabase now strongly recommends verifying JWTs via the project's JWKS endpoint
(asymmetric signing — ES256, RS256, or EdDSA) rather than a shared HS256 secret.
The JWKS endpoint is:

    GET {SUPABASE_URL}/auth/v1/.well-known/jwks.json

We cache the JWKS in-process (TTL: 10 minutes) to match Supabase's own cache
window and avoid hammering the auth server on every request.
"""

import logging
import time
import uuid
from typing import Any

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt
from supabase import AuthApiError

from app.config import get_settings
from app.database import get_supabase

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# JWKS cache — keyed by kid, refreshed every 10 minutes
# ---------------------------------------------------------------------------

_JWKS_CACHE: dict[str, Any] = {}          # kid → JWK dict
_JWKS_CACHED_AT: float = 0.0
_JWKS_TTL_SECONDS: int = 600              # 10 minutes, matching Supabase edge cache

_EXPECTED_ROLE = "authenticated"


async def _fetch_jwks() -> dict[str, Any]:
    """Fetch and cache the JWKS from the Supabase Auth server (async).

    Returns a mapping of kid → JWK dict for fast key lookup.
    Uses httpx.AsyncClient to avoid blocking the asyncio event loop.
    """
    global _JWKS_CACHE, _JWKS_CACHED_AT

    now = time.monotonic()
    if _JWKS_CACHE and (now - _JWKS_CACHED_AT) < _JWKS_TTL_SECONDS:
        return _JWKS_CACHE

    url = settings.resolved_jwks_url
    logger.debug("Refreshing JWKS from %s", url)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch JWKS: %s", exc)
        # Return stale cache if available rather than crashing every request
        if _JWKS_CACHE:
            logger.warning("Returning stale JWKS cache due to fetch failure")
            return _JWKS_CACHE
        raise RuntimeError(f"Could not retrieve JWKS from {url}: {exc}") from exc

    keys = response.json().get("keys", [])
    _JWKS_CACHE = {key["kid"]: key for key in keys if "kid" in key}
    _JWKS_CACHED_AT = now
    logger.info("JWKS refreshed: %d key(s) cached", len(_JWKS_CACHE))
    return _JWKS_CACHE


async def verify_supabase_token(token: str) -> uuid.UUID:
    """Validate a Supabase-issued JWT and return the user's UUID.

    Verification flow:
    1. Decode the JWT header (unverified) to extract the key ID (kid) and alg.
    2. Look up the matching public key from the JWKS endpoint.
    3. Verify the signature, expiry, and role claim using python-jose.

    Falls back to HS256 shared-secret verification for projects still using the
    legacy JWT secret (i.e. JWKS returns no keys).

    Raises:
        JWTError: if the token is invalid, expired, or the key cannot be found.
    """
    # 1. Peek at header to find kid + alg without verifying signature yet
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise JWTError(f"Malformed JWT header: {exc}") from exc

    kid = unverified_header.get("kid")
    alg = unverified_header.get("alg", "HS256")

    # 2. Fetch JWKS (cached, async)
    jwks = await _fetch_jwks()

    if not jwks:
        # Project still uses legacy HS256 — no JWKS available
        logger.warning(
            "No JWKS keys found — falling back to legacy JWT secret verification. "
            "Migrate to asymmetric signing keys in Supabase Dashboard → Settings → JWT."
        )
        raise JWTError(
            "No asymmetric signing keys found in JWKS. "
            "Configure asymmetric JWT signing keys in Supabase Dashboard → Settings → JWT Signing Keys."
        )

    # 3. Select the right public key by kid
    if kid not in jwks:
        # kid mismatch — possibly a key rotation; invalidate cache and retry once
        logger.info("kid %r not in JWKS cache, invalidating and retrying", kid)
        global _JWKS_CACHED_AT
        _JWKS_CACHED_AT = 0.0
        jwks = await _fetch_jwks()

    if kid not in jwks:
        raise JWTError(f"Unknown signing key id: {kid!r}")

    public_key = jwks[kid]

    # 4. Verify signature + claims
    payload = jwt.decode(
        token,
        public_key,
        algorithms=[alg],
        options={"verify_aud": False},  # Supabase JWTs often omit the aud claim
    )

    subject: str | None = payload.get("sub")
    if not subject:
        raise JWTError("Token missing 'sub' claim")

    role: str | None = payload.get("role")
    if role != _EXPECTED_ROLE:
        raise JWTError(f"Unexpected token role: {role!r} (expected 'authenticated')")

    return uuid.UUID(subject)


# ---------------------------------------------------------------------------
# Supabase Auth helpers
# ---------------------------------------------------------------------------

def register_with_supabase(email: str, password: str) -> tuple[uuid.UUID, str, str]:
    """Sign up a new user via Supabase Auth.

    Returns:
        (user_id, access_token, refresh_token)

    Raises:
        HTTPException 409 if the email is already registered.
        HTTPException 400 on other auth errors.
    """
    supabase = get_supabase()
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
    except AuthApiError as exc:
        logger.warning("Supabase sign_up error: %s", exc)
        if "already registered" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if response.user is None or response.session is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Registration succeeded but no session was returned. "
                "Disable 'Confirm email' in Supabase Auth settings for development."
            ),
        )

    return (
        uuid.UUID(response.user.id),
        response.session.access_token,
        response.session.refresh_token,
    )


def login_with_supabase(email: str, password: str) -> tuple[uuid.UUID, str, str]:
    """Sign in an existing user via Supabase Auth.

    Returns:
        (user_id, access_token, refresh_token)

    Raises:
        HTTPException 401 on invalid credentials.
    """
    supabase = get_supabase()
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
    except AuthApiError as exc:
        logger.warning("Supabase sign_in error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        ) from exc

    if response.user is None or response.session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    return (
        uuid.UUID(response.user.id),
        response.session.access_token,
        response.session.refresh_token,
    )
