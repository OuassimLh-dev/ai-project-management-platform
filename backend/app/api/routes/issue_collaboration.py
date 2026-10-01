from typing import Annotated

from fastapi import APIRouter, Path, Response

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models import IssueActivity, IssueComment
from app.schemas.issue_collaboration import IssueActivityRead, IssueCommentCreate, IssueCommentRead, IssueCommentUpdate
from app.services import issue_collaboration as service

router = APIRouter(tags=["issue collaboration"])
PathID = Annotated[int, Path(gt=0)]


@router.post("/issues/{issue_id}/comments", response_model=IssueCommentRead, status_code=201)
def create(issue_id: PathID, payload: IssueCommentCreate, user: CurrentUser, db: DatabaseSession) -> IssueComment:
    return service.create_comment(db, issue_id, user.id, payload)


@router.get("/issues/{issue_id}/comments", response_model=list[IssueCommentRead])
def comments(issue_id: PathID, user: CurrentUser, db: DatabaseSession) -> list[IssueComment]:
    return service.list_comments(db, issue_id, user.id)


@router.patch("/issues/{issue_id}/comments/{comment_id}", response_model=IssueCommentRead)
def update(issue_id: PathID, comment_id: PathID, payload: IssueCommentUpdate, user: CurrentUser, db: DatabaseSession) -> IssueComment:
    return service.update_comment(db, issue_id, comment_id, user.id, payload)


@router.delete("/issues/{issue_id}/comments/{comment_id}", status_code=204)
def delete(issue_id: PathID, comment_id: PathID, user: CurrentUser, db: DatabaseSession) -> Response:
    service.delete_comment(db, issue_id, comment_id, user.id)
    return Response(status_code=204)


@router.get("/issues/{issue_id}/activity", response_model=list[IssueActivityRead])
def activity(issue_id: PathID, user: CurrentUser, db: DatabaseSession) -> list[IssueActivity]:
    return service.list_activity(db, issue_id, user.id)
