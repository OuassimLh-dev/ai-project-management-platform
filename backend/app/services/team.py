from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Project, ProjectMember, Team, TeamMember, TeamRole
from app.schemas.team import MemberAddRequest, TeamCreate, TeamUpdate
from app.services.auth import find_user_by_email
from app.services.team_authorization import TeamError, require_manager, require_membership_change


def get_membership(db: Session, team_id: int, user_id: int) -> TeamMember | None:
    return db.scalar(select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
                     .execution_options(populate_existing=True))


def get_team(db: Session, team_id: int, user_id: int, *, lock: bool = False) -> Team:
    query = select(Team).where(Team.id == team_id)
    if lock:
        # Serialize team mutations before reading the actor's current permissions.
        query = query.with_for_update().execution_options(populate_existing=True)
    team = db.scalar(query)
    if team is None or get_membership(db, team_id, user_id) is None:
        # Deliberately hide team existence from outsiders.
        raise TeamError(404, "Team not found")
    return team


def create_team(db: Session, user_id: int, payload: TeamCreate) -> Team:
    team = Team(**payload.model_dump(), created_by_id=user_id)
    try:
        db.add(team)
        db.flush()
        db.add(TeamMember(team_id=team.id, user_id=user_id, role=TeamRole.OWNER))
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(team)
    return team


def list_teams(db: Session, user_id: int) -> list[Team]:
    return list(db.scalars(select(Team).join(TeamMember).where(TeamMember.user_id == user_id).order_by(Team.id)))


def update_team(db: Session, team_id: int, user_id: int, payload: TeamUpdate) -> Team:
    team = get_team(db, team_id, user_id, lock=True)
    require_manager(get_membership(db, team_id, user_id))
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(team, field, value)
    db.commit()
    db.refresh(team)
    return team


def list_members(db: Session, team_id: int, user_id: int) -> list[TeamMember]:
    get_team(db, team_id, user_id)
    return list(db.scalars(select(TeamMember).where(TeamMember.team_id == team_id).order_by(TeamMember.id)))


def add_member(db: Session, team_id: int, actor_id: int, payload: MemberAddRequest) -> TeamMember:
    get_team(db, team_id, actor_id, lock=True)
    require_membership_change(get_membership(db, team_id, actor_id), new_role=payload.role)
    user = find_user_by_email(db, str(payload.email))
    if user is None:
        raise TeamError(404, "User not found")
    user_id = user.id
    if get_membership(db, team_id, user_id) is not None:
        raise TeamError(409, "User is already a team member")
    member = TeamMember(team_id=team_id, user_id=user_id, role=payload.role)
    db.add(member)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if get_membership(db, team_id, user_id) is not None:
            raise TeamError(409, "User is already a team member") from None
        raise
    db.refresh(member)
    return member


def change_member_role(db: Session, team_id: int, actor_id: int, user_id: int, role: TeamRole) -> TeamMember:
    get_team(db, team_id, actor_id, lock=True)
    actor = get_membership(db, team_id, actor_id)
    require_manager(actor)
    target = get_membership(db, team_id, user_id)
    if target is None:
        raise TeamError(404, "Team member not found")
    require_membership_change(actor, target, role)
    target.role = role
    db.commit()
    db.refresh(target)
    return target


def remove_member(db: Session, team_id: int, actor_id: int, user_id: int) -> None:
    get_team(db, team_id, actor_id, lock=True)
    actor = get_membership(db, team_id, actor_id)
    require_manager(actor)
    target = get_membership(db, team_id, user_id)
    if target is None:
        raise TeamError(404, "Team member not found")
    require_membership_change(actor, target)
    assigned = db.scalar(select(ProjectMember.id).join(Project).where(
        Project.team_id == team_id, ProjectMember.user_id == user_id).limit(1))
    if assigned is not None:
        raise TeamError(400, "Remove project memberships before removing this team member")
    db.delete(target)
    db.commit()
