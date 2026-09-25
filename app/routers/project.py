from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.project import Project
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
)

router = APIRouter(
    prefix="/api/v1/projects",
    tags=["Projects"],
)

@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    data: ProjectCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):

    project = Project(
        name=data.name,
        owner_id=user.id,
    )

    db.add(project)

    await db.commit()
    await db.refresh(project)

    return ProjectResponse(
        id=str(project.id),
        name=project.name,
    )