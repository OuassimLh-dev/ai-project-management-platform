from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

CommentBody = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]


class IssueCommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: CommentBody


class IssueCommentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: CommentBody


class IssueCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: int
    issue_id: int
    author_id: int
    body: str
    created_at: datetime
    updated_at: datetime


class IssueActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: int
    issue_id: int
    actor_id: int
    action: str
    field_name: str | None
    old_value: str | None
    new_value: str | None
    created_at: datetime
