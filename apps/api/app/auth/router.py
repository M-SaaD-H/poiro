"""Authentication router: register, login, and get current user.

Auth (sign-up / sign-in) is delegated to Supabase Auth.
On registration, a profile row is inserted into public.users using the UUID
issued by Supabase so that our ORM models can reference it via foreign key.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.auth.service import login_with_supabase, register_with_supabase
from app.database import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Register a new user via Supabase Auth and create a public profile row."""
    # 1. Create the identity in Supabase Auth (raises 409 on duplicate email).
    user_id, access_token, refresh_token = register_with_supabase(body.email, body.password)

    # 2. Insert the public profile row so our FK relationships work.
    user = User(
        id=user_id,
        email=body.email,
        display_name=body.display_name,
    )
    session.add(user)
    await session.flush()

    logger.info("New user registered: %s (id=%s)", body.email, user_id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Authenticate via Supabase Auth and return tokens + profile."""
    # 1. Verify credentials with Supabase Auth.
    user_id, access_token, refresh_token = login_with_supabase(body.email, body.password)

    # 2. Fetch the public profile row.
    user = await session.get(User, user_id)
    if user is None:
        # Supabase Auth succeeded but the profile is missing — shouldn't normally happen.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found. Please contact support.",
        )

    logger.info("User logged in: %s", body.email)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)
