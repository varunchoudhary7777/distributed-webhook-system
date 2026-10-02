from pydantic import BaseModel, ConfigDict, Field

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    is_active: bool
class ProjectUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)