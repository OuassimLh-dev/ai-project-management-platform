from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Project, ProjectMember, ProjectRole, Team, TeamMember, TeamRole
from app.services.team import get_membership


class ProjectError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def is_team_manager(membership: TeamMember) -> bool:
    return membership.role in (TeamRole.OWNER, TeamRole.ADMIN)


def get_project_membership(db: Session, project_id: int, user_id: int) -> ProjectMember | None:
    return db.scalar(select(ProjectMember).where(ProjectMember.project_id == project_id,
                                                ProjectMember.user_id == user_id)
                     .execution_options(populate_existing=True))


def resolve_project(db: Session, project_id: int, user_id: int, *, manage=False, lock=False) -> Project:
    team_id = db.scalar(select(Project.team_id).where(Project.id == project_id))
    if team_id is None:
        raise ProjectError(404, "Project not found")
    if lock:
        # Always lock team before project: coordinates with team member removal/role changes.
        db.scalar(select(Team).where(Team.id == team_id).with_for_update())
    query = select(Project).where(Project.id == project_id).execution_options(populate_existing=True)
    if lock:
        query = query.with_for_update()
    project = db.scalar(query)
    team_member = get_membership(db, team_id, user_id)
    if project is None or team_member is None:
        raise ProjectError(404, "Project not found")
    membership = get_project_membership(db, project_id, user_id)
    team_manager = is_team_manager(team_member)
    if not team_manager and membership is None:
        raise ProjectError(404, "Project not found")
    if manage and not team_manager and membership.role != ProjectRole.MANAGER:
        raise ProjectError(403, "Project management requires manager permissions")
    return project


def preserve_manager(db: Session, membership: ProjectMember) -> None:
    # Caller holds parent team + project locks until commit.
    if membership.role == ProjectRole.MANAGER:
        count = db.scalar(select(func.count()).select_from(ProjectMember).where(
            ProjectMember.project_id == membership.project_id, ProjectMember.role == ProjectRole.MANAGER))
        if count <= 1:
            raise ProjectError(400, "A project must retain at least one manager")
