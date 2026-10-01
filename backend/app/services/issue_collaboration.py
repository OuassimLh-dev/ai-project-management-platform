from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IssueActivity, IssueComment
from app.schemas.issue_collaboration import IssueCommentCreate, IssueCommentUpdate
from app.services.issue import IssueError, get_issue


def create_comment(db: Session, issue_id: int, actor_id: int, payload: IssueCommentCreate) -> IssueComment:
    get_issue(db, issue_id, actor_id, lock=True)
    comment = IssueComment(issue_id=issue_id, author_id=actor_id, body=payload.body)
    db.add(comment)
    commit(db)
    db.refresh(comment)
    return comment


def list_comments(db: Session, issue_id: int, actor_id: int) -> list[IssueComment]:
    get_issue(db, issue_id, actor_id)
    return list(db.scalars(select(IssueComment).where(IssueComment.issue_id == issue_id).order_by(IssueComment.id)))


def editable_comment(db: Session, issue_id: int, comment_id: int, actor_id: int) -> IssueComment:
    get_issue(db, issue_id, actor_id, lock=True)
    comment = db.scalar(select(IssueComment).where(IssueComment.id == comment_id, IssueComment.issue_id == issue_id)
                        .execution_options(populate_existing=True).with_for_update())
    if comment is None:
        raise IssueError(404, "Comment not found")
    if comment.author_id != actor_id:
        raise IssueError(403, "Only the comment author may edit or delete it")
    return comment


def update_comment(db: Session, issue_id: int, comment_id: int, actor_id: int, payload: IssueCommentUpdate) -> IssueComment:
    comment = editable_comment(db, issue_id, comment_id, actor_id)
    comment.body = payload.body
    commit(db)
    db.refresh(comment)
    return comment


def delete_comment(db: Session, issue_id: int, comment_id: int, actor_id: int) -> None:
    db.delete(editable_comment(db, issue_id, comment_id, actor_id))
    commit(db)


def list_activity(db: Session, issue_id: int, actor_id: int) -> list[IssueActivity]:
    get_issue(db, issue_id, actor_id)
    return list(db.scalars(select(IssueActivity).where(IssueActivity.issue_id == issue_id)
                           .order_by(IssueActivity.created_at, IssueActivity.id)))


def commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
