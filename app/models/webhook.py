import uuid


from sqlalchemy import Boolean, ForeignKey, String, Text, text, Integer, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKey, CreatedAt, UpdatedAt


class WebhookEndpoint(Base, UUIDPrimaryKey, CreatedAt, UpdatedAt):
    __tablename__ = "webhook_endpoints"
    __table_args__ = (
        CheckConstraint(
            "timeout_seconds BETWEEN 1 AND 60",
            name="timeout_seconds_range",
        ),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=False,
    )

    secret_ciphertext: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    project = relationship(
        "Project",
        back_populates="webhook_endpoints",
    )

    event_types: Mapped[list[str]] = mapped_column(
        ARRAY(String(200)),
        nullable=False,
        server_default=text("'{}'")
    )

    custom_headers: Mapped[dict] =  mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb")
    )

    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )