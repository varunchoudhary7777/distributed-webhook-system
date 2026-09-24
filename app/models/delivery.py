import uuid
from datetime import datetime

from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

class DeliveryStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"

class Delivery(Base, TimestampMixin):
    __tablename__ = "deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
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
        defalt=0,
    )

    last_http_status: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
    )

    last_error: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )

    next_retry_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )