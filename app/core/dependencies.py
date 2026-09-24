import uuid

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Annotated

from app.core.config import settings
from app.core.database import get_db
from app.models.api_key import APIKey
from app.models.project import Project
from app.models.user import User
from app.core.security import hash_api_key

from fastapi.security import APIKeyHeader

api_key_scheme = APIKeyHeader(
    name="X-API-Key",
    auto_error=True,
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
)

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:

    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid authentication credentials",
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        user_id = payload.get("sub")

        if not user_id:
            raise credentials_exception

        user_uuid = uuid.UUID(user_id)

    except(JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(
        select(User).where(
            User.id == user_uuid,
        )
    )

    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise credentials_exception

    return user

async def get_project_from_api_key(
    api_key: Annotated[str, Depends(api_key_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Project:

    key_hash = hash_api_key(api_key)

    result = await db.execute(
        select(APIKey)
        .where(
            APIKey.key_hash == key_hash,
            APIKey.is_active.is_(True),
        )
    )

    api_key_record = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    result = await db.execute(
        select(Project)
        .where(
            Project.id == api_key_record.project_id,
        )
    )

    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=401,
            detail="Project not found",
        )

    return project