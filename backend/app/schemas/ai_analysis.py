from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.issue import IssuePriority, IssueType


class AIAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: int
    issue_id: int
    requested_by_id: int
    summary: str
    suggested_type: IssueType
    suggested_priority: IssuePriority
    explanation: str
    model_name: str
    created_at: datetime
