from datetime import datetime
from typing import Annotated, Literal

from pydantic import BeforeValidator, BaseModel, ConfigDict, StringConstraints, field_validator

from pydantic_core import PydanticCustomError

from app.models.team import TeamRole
from app.schemas.user import EmailInput

TeamName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]
def reject_owner(value: object) -> object:
    if value == TeamRole.OWNER:
        raise PydanticCustomError("owner_assignment", "Ownership transfer is not supported")
    return value


AssignableRole = Annotated[Literal[TeamRole.ADMIN, TeamRole.MEMBER], BeforeValidator(reject_owner)]


class TeamCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: TeamName
    description: Description | None = None


class TeamUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: TeamName | None = None
    description: Description | None = None

    @field_validator("name")
    @classmethod
    def name_not_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Team name cannot be null")
        return value


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class TeamMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    team_id: int
    user_id: int
    role: TeamRole
    joined_at: datetime


class MemberAddRequest(EmailInput):
    role: AssignableRole


class MemberRoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: AssignableRole
