from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token, verify_api_key
from app.models.api_key import APIKey
from app.models.project import Project
from app.models.user import User


bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise unauthorized

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_project_api_key(
    db: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> APIKey:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired API key",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    raw_key = credentials.credentials
    if not raw_key.startswith("whk_") or len(raw_key) < 20:
        raise unauthorized

    # Key prefix is public and indexed; only the hash is secret.
    prefix = raw_key[:12]
    key = await db.scalar(select(APIKey).where(APIKey.key_prefix == prefix))
    if key is None or not verify_api_key(raw_key, key.key_hash):
        raise unauthorized

    now = datetime.now(timezone.utc)
    if (
        not key.is_active
        or key.revoked_at is not None
        or (key.expires_at is not None and key.expires_at <= now)
    ):
        raise unauthorized

    project = await db.get(Project, key.project_id)
    if project is None or not project.is_active:
        raise unauthorized

    key.last_used_at = now
    await db.commit()
    return key


CurrentAPIKey = Annotated[APIKey, Depends(get_project_api_key)]


async def require_owned_project(
    project_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> Project:
    project = await db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.owner_user_id == user.id,
            Project.is_active.is_(True),
        )
    )
    if project is None:
        # Avoid confirming that another user's project exists.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


OwnedProject = Annotated[Project, Depends(require_owned_project)]