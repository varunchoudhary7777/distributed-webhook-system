from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession
from app.core.security import create_api_key
from app.models.api_key import APIKey
from app.models.base import UUIDPrimaryKey
from app.models.project import Project
from app.schemas.api_key import APIKeyCreate, APIKeyCreated, APIKeyResponse

router = APIRouter(
    prefix = "/v1/projects/{project_id}/api_keys",
    tags=["api keys"],
)

async def _get_owned_project(project_id: UUID, db:DbSession, user: CurrentUser):
    project = await db.scalar(
        select(Project)
        .where(
            Project.id == project_id,
            Project.owner_user_id == user.id,
            Project.is_active.is_(True),
        )
    )
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="project not found",
        )
    return project

@router.post("", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_key(
    project_id: UUID,
    body: APIKeyCreate,
    db: DbSession,
    user: CurrentUser,
):
    project = await _get_owned_project(project_id, db, user)
    raw_key, prefix, key_hash = create_api_key()

    record = APIKey(
        project_id=project.id,
        key_prefix=prefix,
        key_hash=key_hash,
        name=body.name.strip(),
        is_active=True,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return APIKeyCreated.model_validate(record)

@router.get("", response_model=list[APIKeyResponse])
async def list_keys(
    project_id: UUID,
    db: DbSession,
    user: CurrentUser,
):
    project = await _get_owned_project(project_id, db, user)
    records = await db.scalars(
        select(APIKey)
        .where(APIKey.project_id == project.id)
        .order_by(APIKey.created_at.desc())
    )
    return [
        APIKeyResponse.model_validate(key)
        for key in records
    ]

@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(
    project_id: UUID,
    key_id: UUID,
    db: DbSession,
    user: CurrentUser,
):
    project = await _get_owned_project(project_id, db, user)
    record = await db.scalar(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.project_id == project.id,
        )
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    record.is_active = False
    record.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return None