import uuid
from datetime import datetime

from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text, Index, func, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey, CreatedAt, UpdatedAt


class DeliveryStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"

class Delivery(Base, UUIDPrimaryKey, CreatedAt, UpdatedAt):
    __tablename__ = "deliveries"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "webhook_id",
            name="uq_deliveries_event_webhook",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="attempt_count_nonnegative",
        ),
        Index(
            "ix_deliveries_webhook_created",
            "status",
            "next_attempt_at",
        ),
        Index(
            "ix_deliveries_webhook_created",
            "webhook_id",
            "created_at",
        ),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "events.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        SQLEnum(DeliveryStatus, name="delivery_status"),
        nullable=False,
        default=DeliveryStatus.PENDING,
        index=True,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_http_status: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
    )

    last_error_code: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )

    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    succeeded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "webhook.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

class DeliveryAttempt(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "delivery_attempts"
    __table_args__ = (
        UniqueConstraint(
            "delivery_id",
            "attempt_number",
            name="uq_attempts_delivery_number",
        ),
        Index(
            "ix_attempts_delivery_created",
            "delivery_id",
            "created_at",
        ),
    )

    delivery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "deliveries.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    finished_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    outcome: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="started",
    )
    http_status: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    response_headers: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    response_body_preview: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )