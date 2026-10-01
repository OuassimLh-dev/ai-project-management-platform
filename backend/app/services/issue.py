from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import Issue, ProjectMember, Sprint, User
from app.schemas.issue import IssueCreate, IssueUpdate
from app.services.project_authorization import resolve_project
from app.services.issue_activity import record_creation, record_changes


class IssueError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def validate_assignee(db: Session, project_id: int, assignee_id: int | None) -> None:
    if assignee_id is None:
        return
    if db.get(User, assignee_id) is None:
        raise IssueError(404, "Assignee user not found")
    if db.scalar(select(ProjectMember.id).where(ProjectMember.project_id == project_id,
                                                ProjectMember.user_id == assignee_id)) is None:
        raise IssueError(400, "Assignee must be an explicit project member")


def validate_sprint(db: Session, project_id: int, sprint_id: int | None) -> None:
    if sprint_id is None:
        return
    sprint = db.get(Sprint, sprint_id)
    if sprint is None:
        raise IssueError(404, "Sprint not found")
    if sprint.project_id != project_id:
        raise IssueError(400, "Sprint must belong to the issue's project")


def next_number(db: Session, project_id: int) -> int:
    # Caller holds the parent project lock through insertion and commit.
    return (db.scalar(select(func.max(Issue.number)).where(Issue.project_id == project_id)) or 0) + 1


def create_issue(db: Session, project_id: int, actor_id: int, payload: IssueCreate) -> Issue:
    for attempt in range(2):
        project = resolve_project(db, project_id, actor_id, lock=True)
        validate_assignee(db, project_id, payload.assignee_id)
        validate_sprint(db, project_id, payload.sprint_id)
        number = next_number(db, project_id)
        issue = Issue(project=project, number=number, reporter_id=actor_id, **payload.model_dump())
        try:
            db.add(issue)
            record_creation(db, issue, actor_id)
            db.commit()
        except IntegrityError:
            db.rollback()
            conflict = db.scalar(select(Issue.id).where(Issue.project_id == project_id, Issue.number == number))
            if conflict is not None and attempt == 0:
                continue
            raise IssueError(409, "Issue creation conflicted with another change; retry the request") from None
        except Exception:
            db.rollback()
            raise
        return get_issue(db, issue.id, actor_id)
    raise AssertionError("Unreachable")


def list_issues(db: Session, project_id: int, actor_id: int, **filters) -> list[Issue]:
    resolve_project(db, project_id, actor_id)
    query = select(Issue).options(joinedload(Issue.project)).where(Issue.project_id == project_id)
    for field in ("status", "priority", "issue_type", "assignee_id", "sprint_id"):
        if filters.get(field) is not None:
            query = query.where(getattr(Issue, field) == filters[field])
    return list(db.scalars(query.order_by(Issue.number)))


def get_issue(db: Session, issue_id: int, actor_id: int, *, lock=False) -> Issue:
    project_id = db.scalar(select(Issue.project_id).where(Issue.id == issue_id))
    if project_id is None:
        raise IssueError(404, "Issue not found")
    resolve_project(db, project_id, actor_id, lock=lock)
    query = select(Issue).options(joinedload(Issue.project)).where(Issue.id == issue_id).execution_options(populate_existing=True)
    if lock:
        query = query.with_for_update(of=Issue)
    issue = db.scalar(query)
    if issue is None:
        raise IssueError(404, "Issue not found")
    return issue


def update_issue(db: Session, issue_id: int, actor_id: int, payload: IssueUpdate) -> Issue:
    issue = get_issue(db, issue_id, actor_id, lock=True)
    changes = payload.model_dump(exclude_unset=True)
    if "assignee_id" in changes:
        validate_assignee(db, issue.project_id, changes["assignee_id"])
    if "sprint_id" in changes:
        validate_sprint(db, issue.project_id, changes["sprint_id"])
    try:
        record_changes(db, issue, actor_id, changes)
        for field, value in changes.items():
            setattr(issue, field, value)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise IssueError(409, "Issue update conflicted with another change; retry the request") from None
    except Exception:
        db.rollback()
        raise
    return get_issue(db, issue_id, actor_id)
