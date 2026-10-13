from uuid import UUID
from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession
from app.models.project import Project
from app.models.webhook import Webhook
from app.schemas.webhook import (
    WebhookCreate,
    WebhookCreated,
    WebhookResponse,
    WebhookUpdate,
)
from app.utils.crypto import encrypt_secret
from app.utils.url_validation import UnsafeWebhookURL, validate_webhook_url

router = APIRouter(
    prefix="/v1/projects/{project_id}/webhooks",
    tags=["webhooks"],
)

async def get_owned_project(project_id: UUID, db: DbSession, user: CurrentUser):
    project = await db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.owner_user_id == user.id,
            Project.is_active.is_(True),
        )
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project

@router.post("", response_model=WebhookCreated, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    project_id: UUID,
    body: WebhookCreate,
    db: DbSession,
    user: CurrentUser,
):
    project = await get_owned_project(project_id, db, user)

    try:
        safe_url = validate_webhook_url(str(body.url))
    except UnsafeWebhookURL as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    webhook = Webhook(
        project_id=project.id,
        url=safe_url,
        description=body.description,
        secret_ciphertext=encrypt_secret(body.secret),
        event_types=body.event_types,
        custom_headers={},
        is_active=True,
        timeout_seconds=body.timeout_seconds,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)

    return WebhookCreated(
        id=webhook.id,
        url=webhook.url,
        description=webhook.description,
        event_types=webhook.event_types,
        is_active=webhook.is_active,
        timeout_seconds=webhook.timeout_seconds,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
        secret=body.secret,
    )


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(
    project_id: UUID,
    db: DbSession,
    user: CurrentUser,
):
    project = await get_owned_project(project_id, db, user)
    rows = await db.scalars(
        select(Webhook)
        .where(Webhook.project_id == project.id)
        .order_by(Webhook.created_at.desc())
    )

    return [
        WebhookResponse(
            id=row.id,
            url=row.url,
            description=row.description,
            event_types=row.event_types,
            is_active=row.is_active,
            timeout_seconds=row.timeout_seconds,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    project_id: UUID,
    webhook_id: UUID,
    body: WebhookUpdate,
    db: DbSession,
    user: CurrentUser,
):
    project = await get_owned_project(project_id, db, user)
    webhook = await db.scalar(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.project_id == project.id,
        )
    )
    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")

    changes = body.model_dump(exclude_unset=True)

    if "url" in changes and changes["url"] is not None:
        try:
            changes["url"] = validate_webhook_url(str(changes["url"]))
        except UnsafeWebhookURL as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    for field, value in changes.items():
        setattr(webhook, field, value)

    await db.commit()
    await db.refresh(webhook)

    return WebhookResponse(
        id=webhook.id,
        url=webhook.url,
        description=webhook.description,
        event_types=webhook.event_types,
        is_active=webhook.is_active,
        timeout_seconds=webhook.timeout_seconds,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
    )


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_webhook(
    project_id: UUID,
    webhook_id: UUID,
    db: DbSession,
    user: CurrentUser,
):
    project = await get_owned_project(project_id, db, user)
    webhook = await db.scalar(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.project_id == project.id,
        )
    )
    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")

    # Keep history and references intact; stop future fan-out.
    webhook.is_active = False
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)