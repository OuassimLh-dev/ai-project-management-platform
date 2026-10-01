from enum import Enum

from sqlalchemy.orm import Session

from app.models import Issue, IssueActivity


def activity_value(value) -> str | None:
    if value is None:
        return None
    return str(value.value if isinstance(value, Enum) else value)


def record_creation(db: Session, issue: Issue, actor_id: int) -> None:
    db.add(IssueActivity(issue=issue, actor_id=actor_id, action="created"))


def record_changes(db: Session, issue: Issue, actor_id: int, changes: dict) -> None:
    # Caller commits history and issue together. Compare before mutating ORM values.
    for field, value in changes.items():
        previous = getattr(issue, field)
        if previous != value:
            db.add(IssueActivity(issue=issue, actor_id=actor_id, action="field_changed",
                                 field_name=field, old_value=activity_value(previous), new_value=activity_value(value)))
