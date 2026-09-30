from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.models.project import ProjectRole
from app.schemas.team import Description, TeamName as ProjectName

ProjectKey = Annotated[str, StringConstraints(min_length=1, max_length=20, pattern=r"^[A-Z][A-Z0-9]*$")]


class ProjectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("key", mode="before", check_fields=False)
    @classmethod
    def normalize_key(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


class ProjectCreate(ProjectInput):
    name: ProjectName
    key: ProjectKey
    description: Description | None = None
    is_active: bool = True


class ProjectUpdate(ProjectInput):
    name: ProjectName | None = None
    key: ProjectKey | None = None
    description: Description | None = None
    is_active: bool | None = None

    @field_validator("name", "key", "is_active")
    @classmethod
    def nonnullable_fields(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    team_id: int
    name: str
    key: str
    description: str | None
    created_by_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProjectMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    user_id: int
    role: ProjectRole
    joined_at: datetime


class ProjectMemberAddRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int = Field(gt=0, strict=True)
    role: ProjectRole


class ProjectMemberRoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: ProjectRole
