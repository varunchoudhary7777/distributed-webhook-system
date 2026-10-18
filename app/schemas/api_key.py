from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_API_KEY_SCOPES = {
    "events:write",
    "events:read",
    "webhooks:manage",
    "deliveries:read",
}

class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(min_length=1, max_length=10)
    expires_at: datetime | None = None

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, values):
        unknown = set(values) - ALLOWED_API_KEY_SCOPES
        if unknown:
            raise ValueError(f"Unsupported scopes: {sorted(unknown)}")
        if len(set(values)) != len(values):
            raise ValueError("Scopes must not contain duplicates")
        return values


class APIKeyCreated(BaseModel):
    id: str
    name: str
    key: str
    key_prefix: str
    scopes: list[str]
    expires_at: datetime | None



class APIKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None