from fastapi import APIRouter

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models import Sprint
from app.schemas.sprint import SprintCreate, SprintRead, SprintUpdate
from app.services import sprint as service

router = APIRouter(tags=["sprints"])


@router.post("/projects/{project_id}/sprints", response_model=SprintRead, status_code=201)
def create(project_id: int, payload: SprintCreate, user: CurrentUser, db: DatabaseSession) -> Sprint:
    return service.create_sprint(db, project_id, user.id, payload)


@router.get("/projects/{project_id}/sprints", response_model=list[SprintRead])
def list_sprints(project_id: int, user: CurrentUser, db: DatabaseSession) -> list[Sprint]:
    return service.list_sprints(db, project_id, user.id)


@router.get("/sprints/{sprint_id}", response_model=SprintRead)
def get(sprint_id: int, user: CurrentUser, db: DatabaseSession) -> Sprint:
    return service.get_sprint(db, sprint_id, user.id)


@router.patch("/sprints/{sprint_id}", response_model=SprintRead)
def update(sprint_id: int, payload: SprintUpdate, user: CurrentUser, db: DatabaseSession) -> Sprint:
    return service.update_sprint(db, sprint_id, user.id, payload)
