import uuid


from sqlalchemy import (
    ForeignKey,
    JSON,
    String,
    UniqueConstraint, Index, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey, CreatedAt


class Event(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "events"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    request_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_events_project_idempotency",
        ),
        CheckConstraint(
            "length(idempotency_key) > 0",
            name="idempotency_key_nonempty",
        ),
        Index(
            "ix_events_project_created",
            "project_id",
            "created_at",
        ),
    )