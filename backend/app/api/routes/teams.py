from fastapi import APIRouter, Response

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models import Team, TeamMember
from app.schemas.team import MemberAddRequest, MemberRoleUpdate, TeamCreate, TeamMemberRead, TeamRead, TeamUpdate
from app.services import team as service

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("", response_model=TeamRead, status_code=201)
def create(payload: TeamCreate, user: CurrentUser, db: DatabaseSession) -> Team:
    return service.create_team(db, user.id, payload)


@router.get("", response_model=list[TeamRead])
def list_teams(user: CurrentUser, db: DatabaseSession) -> list[Team]:
    return service.list_teams(db, user.id)


@router.get("/{team_id}", response_model=TeamRead)
def get(team_id: int, user: CurrentUser, db: DatabaseSession) -> Team:
    return service.get_team(db, team_id, user.id)


@router.patch("/{team_id}", response_model=TeamRead)
def update(team_id: int, payload: TeamUpdate, user: CurrentUser, db: DatabaseSession) -> Team:
    return service.update_team(db, team_id, user.id, payload)


@router.get("/{team_id}/members", response_model=list[TeamMemberRead])
def members(team_id: int, user: CurrentUser, db: DatabaseSession) -> list[TeamMember]:
    return service.list_members(db, team_id, user.id)


@router.post("/{team_id}/members", response_model=TeamMemberRead, status_code=201)
def add(team_id: int, payload: MemberAddRequest, user: CurrentUser, db: DatabaseSession) -> TeamMember:
    return service.add_member(db, team_id, user.id, payload)


@router.patch("/{team_id}/members/{user_id}", response_model=TeamMemberRead)
def change_role(team_id: int, user_id: int, payload: MemberRoleUpdate, user: CurrentUser, db: DatabaseSession) -> TeamMember:
    return service.change_member_role(db, team_id, user.id, user_id, payload.role)


@router.delete("/{team_id}/members/{user_id}", status_code=204)
def remove(team_id: int, user_id: int, user: CurrentUser, db: DatabaseSession) -> Response:
    service.remove_member(db, team_id, user.id, user_id)
    return Response(status_code=204)
