from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Sprint, SprintStatus
from app.schemas.sprint import SprintCreate, SprintUpdate
from app.services.project_authorization import resolve_project


class SprintError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


TRANSITIONS = {
    SprintStatus.PLANNED: {SprintStatus.ACTIVE, SprintStatus.CANCELLED},
    SprintStatus.ACTIVE: {SprintStatus.COMPLETED, SprintStatus.CANCELLED},
    SprintStatus.COMPLETED: set(),
    SprintStatus.CANCELLED: set(),
}


def validate_transition(current: SprintStatus, requested: SprintStatus) -> None:
    if requested != current and requested not in TRANSITIONS[current]:
        raise SprintError(400, f"Cannot transition sprint from {current.value} to {requested.value}")


def create_sprint(db: Session, project_id: int, actor_id: int, payload: SprintCreate) -> Sprint:
    resolve_project(db, project_id, actor_id, manage=True, lock=True)
    if payload.status != SprintStatus.PLANNED:
        raise SprintError(400, "New sprints must start in planned status")
    sprint = Sprint(project_id=project_id, **payload.model_dump())
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return sprint


def list_sprints(db: Session, project_id: int, actor_id: int) -> list[Sprint]:
    resolve_project(db, project_id, actor_id)
    return list(db.scalars(select(Sprint).where(Sprint.project_id == project_id).order_by(Sprint.id)))


def get_sprint(db: Session, sprint_id: int, actor_id: int, *, manage=False, lock=False) -> Sprint:
    project_id = db.scalar(select(Sprint.project_id).where(Sprint.id == sprint_id))
    if project_id is None:
        raise SprintError(404, "Sprint not found")
    # Parent identity comes exclusively from persistence; mutation lock order is team/project/sprint.
    resolve_project(db, project_id, actor_id, manage=manage, lock=lock)
    query = select(Sprint).where(Sprint.id == sprint_id).execution_options(populate_existing=True)
    if lock:
        query = query.with_for_update()
    sprint = db.scalar(query)
    if sprint is None:
        raise SprintError(404, "Sprint not found")
    return sprint


def update_sprint(db: Session, sprint_id: int, actor_id: int, payload: SprintUpdate) -> Sprint:
    sprint = get_sprint(db, sprint_id, actor_id, manage=True, lock=True)
    changes = payload.model_dump(exclude_unset=True)
    start = changes.get("start_date", sprint.start_date)
    end = changes.get("end_date", sprint.end_date)
    if end < start:
        raise SprintError(400, "end_date must not be before start_date")
    if "status" in changes:
        validate_transition(sprint.status, changes["status"])
    # Validate merged state before changing any ORM fields.
    for field, value in changes.items():
        setattr(sprint, field, value)
    db.commit()
    db.refresh(sprint)
    return sprint
