from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.models.issue import IssuePriority, IssueStatus, IssueType

IssueTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
IssueDescription = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10000)]
PositiveID = Annotated[int, Field(strict=True, gt=0)]


class IssueCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: IssueTitle
    description: IssueDescription | None = None
    issue_type: IssueType
    priority: IssuePriority = IssuePriority.MEDIUM
    status: IssueStatus = IssueStatus.BACKLOG
    assignee_id: PositiveID | None = None
    sprint_id: PositiveID | None = None


class IssueUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: IssueTitle | None = None
    description: IssueDescription | None = None
    issue_type: IssueType | None = None
    priority: IssuePriority | None = None
    status: IssueStatus | None = None
    assignee_id: PositiveID | None = None
    sprint_id: PositiveID | None = None

    @field_validator("title", "issue_type", "priority", "status")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class IssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: int
    project_id: int
    number: int
    issue_key: str
    title: str
    description: str | None
    issue_type: IssueType
    priority: IssuePriority
    status: IssueStatus
    reporter_id: int
    assignee_id: int | None
    sprint_id: int | None
    created_at: datetime
    updated_at: datetime
