import json
from datetime import datetime
from http.client import HTTPException
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=200)
    payload: dict[str, Any]

    @field_validator("event_type")
    @classmethod
    def strip_event_type(cls, value: str) -> str:
        value = value.strip()
        if value is None:
            raise ValueError("event_type cannot be blank")
        return value

    @field_validator("payload")
    @classmethod
    def enforce_payload_sie(cls, payload: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > 256 * 1024:
            raise ValueError("Payload exceeds the 256 KiB limit")
        return payload

class EventAccepted(BaseModel):
    id: UUID
    event_type: str
    status: str
    created_at: datetime

class EventResponse(BaseModel):
    id: UUID
    event_type: str
    payload: dict[str, Any]
    created_at: datetime