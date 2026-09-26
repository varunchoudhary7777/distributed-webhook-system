import uuid

from sqlalchemy import ForeignKey, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKey, CreatedAt, UpdatedAt


class Project(Base, UUIDPrimaryKey, CreatedAt, UpdatedAt):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
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

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )