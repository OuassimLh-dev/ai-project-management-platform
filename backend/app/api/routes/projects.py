from fastapi import APIRouter, Response

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models import Project, ProjectMember
from app.schemas.project import ProjectCreate, ProjectMemberAddRequest, ProjectMemberRead, ProjectMemberRoleUpdate, ProjectRead, ProjectUpdate
from app.services import project as service
from app.services.project_authorization import resolve_project

router = APIRouter(tags=["projects"])


@router.post("/teams/{team_id}/projects", response_model=ProjectRead, status_code=201)
def create(team_id: int, payload: ProjectCreate, user: CurrentUser, db: DatabaseSession) -> Project:
    return service.create_project(db, team_id, user.id, payload)


@router.get("/teams/{team_id}/projects", response_model=list[ProjectRead])
def list_projects(team_id: int, user: CurrentUser, db: DatabaseSession) -> list[Project]:
    return service.list_projects(db, team_id, user.id)


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get(project_id: int, user: CurrentUser, db: DatabaseSession) -> Project:
    return resolve_project(db, project_id, user.id)


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update(project_id: int, payload: ProjectUpdate, user: CurrentUser, db: DatabaseSession) -> Project:
    return service.update_project(db, project_id, user.id, payload)


@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberRead])
def members(project_id: int, user: CurrentUser, db: DatabaseSession) -> list[ProjectMember]:
    return service.list_members(db, project_id, user.id)


@router.post("/projects/{project_id}/members", response_model=ProjectMemberRead, status_code=201)
def add(project_id: int, payload: ProjectMemberAddRequest, user: CurrentUser, db: DatabaseSession) -> ProjectMember:
    return service.add_member(db, project_id, user.id, payload)


@router.patch("/projects/{project_id}/members/{user_id}", response_model=ProjectMemberRead)
def change_role(project_id: int, user_id: int, payload: ProjectMemberRoleUpdate, user: CurrentUser, db: DatabaseSession) -> ProjectMember:
    return service.change_role(db, project_id, user.id, user_id, payload.role)


@router.delete("/projects/{project_id}/members/{user_id}", status_code=204)
def remove(project_id: int, user_id: int, user: CurrentUser, db: DatabaseSession) -> Response:
    service.remove_member(db, project_id, user.id, user_id)
    return Response(status_code=204)
