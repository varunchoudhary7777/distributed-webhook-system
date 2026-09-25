from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.annotation import Annotated

from app.core.database import get_db
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.utils.hashing import (
    hash_password,
    verify_password,
)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

DbSession = Annotated[AsyncSession, Depends(get_db)]

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    db: DbSession,
):
    result = await db.execute(
        select(User).where(
            User.email == data.email
        )
    )

    existing_user = result.scalar_one_or_none

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    user = User(
        email=data.email,
        password_hash=hash_password(
            data.password
        ),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "id": str(user.id),
        "email": user.email,
    }


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
        data: LoginRequest,
        db: DbSession,
):

    result = await db.execute(
        select(User).where(
            User.email == data.email,
        )
    )

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_access_token(
        str(user.id)
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }