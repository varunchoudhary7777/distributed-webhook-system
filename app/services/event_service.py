import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.outbox import Outbox
from app.utils.hashing import event_request_hash

@dataclass
class IdempotencyConflict(Exception):
    message: str = "Idempotency key was already used with a different request"

async def accept_event(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    idempotency_key: str,
    event_type: str,
    payload: dict,
) -> tuple[Event, bool]:
    request_hash = event_request_hash(event_type, payload)

    async with db.begin():
        statement = (
            insert(Event)
            .values(
                id=uuid.uuid4(),
                project_id=project_id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                event_type=event_type,
                payload=payload,
            )
            .on_conflict_do_nothing(
                constraint="uq_events_project_idempotency",
            )
            .returning(Event.id)
        )
        inserted_id = (await db.execute(statement)).scalar_one_or_none()

        if inserted_id is not None:
            event = await db.get(Event, inserted_id)
            if event is None:
                raise RuntimeError("Inserted event could not be loaded")

            db.add(
                Outbox(
                    topic="event.accepted",
                    aggregate_id=event.id,
                    paload={"event_id": str(event.id)},
                    status="pending",
                    attempt_count=0,
                )
            )
            return event, True

        existing = await db.scalar(
            select(Event).where(
                Event.project_id == project_id,
                Event.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise RuntimeError("Conflicting event row could not be loaded")

        if existing.request_hash != request_hash:
            raise IdempotencyConflict()

        return existing, False