from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, DbSession, OwnedProject
from app.models.project import Project
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
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
    user: CurrentUser,
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

@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: DbSession, user: CurrentUser):
    projects = await db.scalars(
        select(Project)
        .where(
            Project.owner_user_id == user.id,
            Project.is_active.is_(True),
        )
    )
    return [
        ProjectResponse.model_validate(project)
        for project in projects
    ]

@router.get("/{project_id", response_model=ProjectResponse)
async def get_project(project: OwnedProject):
    return ProjectResponse.model_validate(project)

@router.patch("/{project_id}", response_model=ProjectResponse)
async def rename_project(
    body: ProjectUpdate,
    project: OwnedProject,
    db: DbSession,
    user: CurrentUser,
):
    project.name=body.name.strip()
    await db.commit()
    await db.refresh(project)

    return ProjectResponse.model_validate(project)