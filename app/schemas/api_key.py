from pydantic import BaseModel

class APIKeyCreate(BaseModel):
    name: str

class APIKeyResponse(BaseModel):
    id: str
    name: str
    key: str