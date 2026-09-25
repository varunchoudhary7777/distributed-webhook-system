from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import (
    generate_api_key,
    hash_api_key,
)
from app.models.api_key import APIKey
from app.models.project import Project
from app.models.user import User
from app.schemas.api_key import (
    APIKeyCreate,
    APIKeyResponse,
)

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/api-keys",
    tags=["API Keys"],
)

@router.post(
    "",
    response_model=APIKeyResponse,
)
async def create_api_key(
    project_id: str,
    data: APIKeyCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == user.id,
        )
    )

    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    raw_key = generate_api_key()

    api_key = APIKey(
        project_id=project.id,
        name=data.name,
        key_prefix=raw_key[:16],
        key_hash=hash_api_key(raw_key),
    )

    db.add(api_key)

    await db.commit()
    await db.refresh(api_key)

    return APIKeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        key=raw_key,
    )