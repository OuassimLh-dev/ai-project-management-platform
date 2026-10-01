from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models import Issue, IssuePriority, IssueStatus, IssueType
from app.schemas.issue import IssueCreate, IssueRead, IssueUpdate
from app.services import issue as service

router = APIRouter(tags=["issues"])
PathID = Annotated[int, Path(gt=0)]
FilterID = Annotated[int | None, Query(gt=0)]


@router.post("/projects/{project_id}/issues", response_model=IssueRead, status_code=201)
def create(project_id: PathID, payload: IssueCreate, user: CurrentUser, db: DatabaseSession) -> Issue:
    return service.create_issue(db, project_id, user.id, payload)


@router.get("/projects/{project_id}/issues", response_model=list[IssueRead])
def list_issues(project_id: PathID, user: CurrentUser, db: DatabaseSession,
                status: IssueStatus | None = None, priority: IssuePriority | None = None,
                issue_type: IssueType | None = None, assignee_id: FilterID = None,
                sprint_id: FilterID = None) -> list[Issue]:
    return service.list_issues(db, project_id, user.id, status=status, priority=priority,
                               issue_type=issue_type, assignee_id=assignee_id, sprint_id=sprint_id)


@router.get("/issues/{issue_id}", response_model=IssueRead)
def get(issue_id: PathID, user: CurrentUser, db: DatabaseSession) -> Issue:
    return service.get_issue(db, issue_id, user.id)


@router.patch("/issues/{issue_id}", response_model=IssueRead)
def update(issue_id: PathID, payload: IssueUpdate, user: CurrentUser, db: DatabaseSession) -> Issue:
    return service.update_issue(db, issue_id, user.id, payload)
