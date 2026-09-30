from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Project, ProjectMember, ProjectRole, User
from app.schemas.project import ProjectCreate, ProjectMemberAddRequest, ProjectUpdate
from app.services.team import get_membership, get_team
from app.services.project_authorization import (
    ProjectError, get_project_membership, is_team_manager, preserve_manager, resolve_project,
)


def key_exists(db: Session, team_id: int, key: str, exclude_id: int | None = None) -> bool:
    query = select(Project.id).where(Project.team_id == team_id, Project.key == key)
    if exclude_id is not None:
        query = query.where(Project.id != exclude_id)
    return db.scalar(query) is not None


def create_project(db: Session, team_id: int, actor_id: int, payload: ProjectCreate) -> Project:
    get_team(db, team_id, actor_id, lock=True)
    if not is_team_manager(get_membership(db, team_id, actor_id)):
        raise ProjectError(403, "Only team owners/admins may create projects")
    if key_exists(db, team_id, payload.key):
        raise ProjectError(409, "Project key already exists in this team")
    project = Project(**payload.model_dump(), team_id=team_id, created_by_id=actor_id)
    try:
        db.add(project)
        db.flush()
        db.add(ProjectMember(project_id=project.id, user_id=actor_id, role=ProjectRole.MANAGER))
        db.commit()
    except IntegrityError:
        db.rollback()
        if key_exists(db, team_id, payload.key):
            raise ProjectError(409, "Project key already exists in this team") from None
        raise
    except Exception:
        db.rollback()
        raise
    db.refresh(project)
    return project


def list_projects(db: Session, team_id: int, actor_id: int) -> list[Project]:
    get_team(db, team_id, actor_id)
    query = select(Project).where(Project.team_id == team_id)
    if not is_team_manager(get_membership(db, team_id, actor_id)):
        query = query.join(ProjectMember).where(ProjectMember.user_id == actor_id)
    return list(db.scalars(query.order_by(Project.id)))


def update_project(db: Session, project_id: int, actor_id: int, payload: ProjectUpdate) -> Project:
    project = resolve_project(db, project_id, actor_id, manage=True, lock=True)
    team_id = project.team_id
    key = payload.key if "key" in payload.model_fields_set else project.key
    if key_exists(db, team_id, key, project_id):
        raise ProjectError(409, "Project key already exists in this team")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if key_exists(db, team_id, key, project_id):
            raise ProjectError(409, "Project key already exists in this team") from None
        raise
    db.refresh(project)
    return project


def list_members(db: Session, project_id: int, actor_id: int) -> list[ProjectMember]:
    resolve_project(db, project_id, actor_id)
    return list(db.scalars(select(ProjectMember).where(ProjectMember.project_id == project_id).order_by(ProjectMember.id)))


def add_member(db: Session, project_id: int, actor_id: int, payload: ProjectMemberAddRequest) -> ProjectMember:
    project = resolve_project(db, project_id, actor_id, manage=True, lock=True)
    if db.get(User, payload.user_id) is None:
        raise ProjectError(404, "User not found")
    if get_membership(db, project.team_id, payload.user_id) is None:
        raise ProjectError(400, "User must already belong to the parent team")
    if get_project_membership(db, project_id, payload.user_id) is not None:
        raise ProjectError(409, "User is already a project member")
    member = ProjectMember(project_id=project_id, user_id=payload.user_id, role=payload.role)
    db.add(member)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if get_project_membership(db, project_id, payload.user_id) is not None:
            raise ProjectError(409, "User is already a project member") from None
        raise
    db.refresh(member)
    return member


def target_member(db: Session, project_id: int, user_id: int) -> ProjectMember:
    target = get_project_membership(db, project_id, user_id)
    if target is None:
        raise ProjectError(404, "Project member not found")
    return target


def change_role(db: Session, project_id: int, actor_id: int, user_id: int, role: ProjectRole) -> ProjectMember:
    resolve_project(db, project_id, actor_id, manage=True, lock=True)
    target = target_member(db, project_id, user_id)
    if role != ProjectRole.MANAGER:
        preserve_manager(db, target)
    target.role = role
    db.commit()
    db.refresh(target)
    return target


def remove_member(db: Session, project_id: int, actor_id: int, user_id: int) -> None:
    resolve_project(db, project_id, actor_id, manage=True, lock=True)
    target = target_member(db, project_id, user_id)
    preserve_manager(db, target)
    db.delete(target)
    db.commit()
