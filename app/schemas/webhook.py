from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

class WebhookCreate(BaseModel):
    url: HttpUrl
    description: str | None = Field(default=None, max_length=500)
    secret: str = Field(min_length=32, max_length=512)
    event_types: list[str] = Field(min_length=1, max_length=100)
    timeout_seconds: int = Field(default=10, ge=1, le=60)

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value or len(value) > 200 for value in cleaned):
            raise ValueError("Each event must contain 1 to 200 characters")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Event types must not contain duplicates")
        return cleaned

class WebhookUpdate(BaseModel):
    url: HttpUrl | None = None
    description: str | None = Field(default=None, max_length=500)
    event_types: list[str] | None = Field(default=None, min_length=1, max_length=100)
    timeout_seconds: int | None = Field(default=None, ge=1, le=60)
    is_active: bool | None = None

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return values
        cleaned = [value.strip() for value in values]
        if any(not value or len(value) > 200 for value in values):
            raise ValueError("Each event type must contain 1 to 200 characters")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Event types must not contain duplicates")
        return cleaned

class WebhookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    description: str | None
    event_types: list[str]
    is_active: bool
    timeout_seconds: int
    created_at: datetime
    updated_at: datetime

class WebhookCreated(WebhookResponse):
    secret: str
    