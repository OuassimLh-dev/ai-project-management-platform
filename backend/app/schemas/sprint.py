from datetime import date, datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

from app.models.sprint import SprintStatus

SprintName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
SprintGoal = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]


class SprintCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: SprintName
    goal: SprintGoal | None = None
    start_date: date
    end_date: date
    status: SprintStatus = SprintStatus.PLANNED

    @model_validator(mode="after")
    def ordered_dates(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class SprintUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: SprintName | None = None
    goal: SprintGoal | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: SprintStatus | None = None

    @field_validator("name", "start_date", "end_date", "status")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @model_validator(mode="after")
    def ordered_dates(self) -> Self:
        if self.start_date is not None and self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class SprintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    goal: str | None
    start_date: date
    end_date: date
    status: SprintStatus
    created_at: datetime
    updated_at: datetime
