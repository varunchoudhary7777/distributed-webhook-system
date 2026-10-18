from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentAPIKey, DbSession
from app.models.event import Event
from app.schemas.event import (
    EventAccepted,
    EventCreate,
    EventResponse,
)
from app.services.event_service import IdempotencyConflict, accept_event


router = APIRouter(
    prefix="/v1/events",
    tags=["events"],
)

@router.post("", response_model=EventAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_event(
    body: EventCreate,
    db: DbSession,
    api_key: CurrentAPIKey,
    idempotency_key: str = Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=255,
    ),
):
    try:
        event, _created = await accept_event(
            db,
            project_id=api_key.project_id,
            idempotency_key=idempotency_key,
            event_type=body.event_type,
            payload=body.payload,
        )

    except IdempotencyConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.message,
        ) from exc

    return EventAccepted(
        id=event.id,
        event_type=event.event_type,
        status="accepted",
        created_at=event.created_at,
    )

@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: UUID,
    db: DbSession,
    api_key: CurrentAPIKey,
):
    event = await db.scalar(
        select(Event).where(
            Event.id == event_id,
            Event.project_id == api_key.project_id,
        )
    )
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    return EventResponse(
        id=event.id,
        event_type=event.event_type,
        payload=event.payload,
        created_at=event.created_at,
    )