import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullanle=False,
        index=True,
    )

    owner = relationship(
        "User",
        back_populates="projects",
    )

    api_keys = relationship(
        "APIKey",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    webhook_endpoints = relationship(
        "WebhookEndpoint",
        back_populates="project",
        cascade="all, delete-orphan",
    )