from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import CurrentUser, DbSession
from app.core.security import (
    ACCESS_TOKEN_MINUTES,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)


router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup(body: SignupRequest, db: DbSession):
    email = body.email.lower()

    existing = await db.scalar(select(User.id).where(User.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        is_active=True,
    )
    db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        # The unique constraint handles two concurrent signup requests.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    await db.refresh(user)
    return UserResponse(
        id=str(user.id),
        email=user.email,
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbSession):
    email = body.email.lower()
    user = await db.scalar(select(User).where(User.email == email))

    # Use one generic error for unknown users and wrong passwords.
    if (
        user is None
        or not user.is_active
        or not verify_password(body.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user_id=user.id)
    return TokenResponse(
        access_token=token,
        expires_in=ACCESS_TOKEN_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser):
    return UserResponse(
        id=str(user.id),
        email=user.email,
        is_active=user.is_active,
    )