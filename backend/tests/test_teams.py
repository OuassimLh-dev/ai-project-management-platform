import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token, hash_password
from app.models import Team, TeamMember, TeamRole, User
from app.schemas.team import TeamCreate
from app.services import team as service

BASE = "/api/v1/teams"


@pytest.fixture(scope="module")
def password_hash():
    return hash_password("Fake-team-test-password-123!")


@pytest.fixture
def actors(db_session, settings, password_hash):
    users = {}
    for name in ("owner", "admin", "admin2", "member", "outsider", "new"):
        user = User(first_name=name.title(), last_name="Test", email=f"{name}@example.com", hashed_password=password_hash)
        db_session.add(user)
        db_session.flush()
        users[name] = {"id": user.id, "email": user.email,
                       "headers": {"Authorization": f"Bearer {create_access_token(user.id, settings)}"}}
    db_session.commit()
    return users


@pytest.fixture
def team(client, actors):
    response = client.post(BASE, headers=actors["owner"]["headers"], json={"name": " Team Alpha ", "description": " Initial "})
    assert response.status_code == 201
    result = response.json()
    for name in ("admin", "admin2", "member"):
        response = client.post(f"{BASE}/{result['id']}/members", headers=actors["owner"]["headers"],
                               json={"email": actors[name]["email"], "role": "member" if name == "member" else "admin"})
        assert response.status_code == 201
    return result


def test_creation_creates_single_owner(client, actors, db_session):
    response = client.post(BASE, headers=actors["owner"]["headers"], json={"name": "  New team  "})
    assert response.status_code == 201
    data = response.json()
    assert set(data) == {"id", "name", "description", "created_by_id", "created_at", "updated_at"}
    assert data["name"] == "New team" and data["description"] is None
    assert data["created_by_id"] == actors["owner"]["id"]
    assert data["created_at"] and data["updated_at"]
    memberships = list(db_session.scalars(select(TeamMember).where(TeamMember.team_id == data["id"])))
    assert len(memberships) == 1
    assert memberships[0].role == TeamRole.OWNER
    assert memberships[0].user_id == actors["owner"]["id"]
    assert memberships[0].joined_at


def test_creation_is_atomic(actors, db_session):
    def fail_membership(*args):
        raise RuntimeError("simulated membership failure")
    event.listen(TeamMember, "before_insert", fail_membership)
    try:
        with pytest.raises(RuntimeError, match="membership failure"):
            service.create_team(db_session, actors["owner"]["id"], TeamCreate(name="Must roll back"))
    finally:
        event.remove(TeamMember, "before_insert", fail_membership)
    assert db_session.scalar(select(func.count()).select_from(Team)) == 0
    assert db_session.scalar(select(func.count()).select_from(TeamMember)) == 0


@pytest.mark.parametrize("method,path,body", [
    ("post", "", {"name": "Team"}), ("get", "", None), ("get", "/1", None),
    ("patch", "/1", {"name": "Update"}), ("get", "/1/members", None),
    ("post", "/1/members", {"email": "new@example.com", "role": "member"}),
    ("patch", "/1/members/1", {"role": "member"}), ("delete", "/1/members/1", None),
])
def test_all_routes_require_authentication(client, method, path, body):
    assert client.request(method, BASE + path, json=body).status_code == 401


@pytest.mark.parametrize("payload", [{"name": " "}, {"name": "x" * 151}, {},
    {"name": "Team", "description": "x" * 5001}, {"name": "Team", "created_by_id": 1}])
def test_invalid_create(client, actors, payload):
    assert client.post(BASE, headers=actors["owner"]["headers"], json=payload).status_code == 422


def test_list_only_current_memberships(client, actors, team):
    headers = actors["outsider"]["headers"]
    assert client.get(BASE, headers=headers).json() == []
    second = client.post(BASE, headers=headers, json={"name": "Other"}).json()
    assert [t["id"] for t in client.get(BASE, headers=headers).json()] == [second["id"]]
    assert client.post(f"{BASE}/{team['id']}/members", headers=actors["owner"]["headers"],
                       json={"email": actors["outsider"]["email"], "role": "member"}).status_code == 201
    assert {t["id"] for t in client.get(BASE, headers=headers).json()} == {team["id"], second["id"]}
    assert [t["id"] for t in client.get(BASE, headers=actors["owner"]["headers"]).json()] == [team["id"]]


@pytest.mark.parametrize("actor", ["owner", "admin", "member"])
def test_member_reads(client, actors, team, actor):
    headers = actors[actor]["headers"]
    assert client.get(f"{BASE}/{team['id']}", headers=headers).json() == team
    response = client.get(f"{BASE}/{team['id']}/members", headers=headers)
    assert response.status_code == 200 and len(response.json()) == 4
    for member in response.json():
        assert set(member) == {"id", "team_id", "user_id", "role", "joined_at"}
    assert sorted(member["role"] for member in response.json()) == ["admin", "admin", "member", "owner"]


@pytest.mark.parametrize("method,suffix,payload", [
    ("get", "", None), ("patch", "", {"name": "Hacked"}), ("get", "/members", None),
    ("post", "/members", {"email": "new@example.com", "role": "member"}),
    ("patch", "/members/1", {"role": "member"}), ("delete", "/members/1", None),
])
def test_outsider_and_missing_team_are_hidden(client, actors, team, method, suffix, payload):
    for team_id in (team["id"], 99999):
        response = client.request(method, f"{BASE}/{team_id}{suffix}", headers=actors["outsider"]["headers"], json=payload)
        assert response.status_code == 404
        assert response.json() == {"detail": "Team not found"}


@pytest.mark.parametrize("actor,role,status", [
    ("owner", "admin", 201), ("owner", "member", 201), ("admin", "member", 201),
    ("admin", "admin", 403), ("member", "member", 403),
])
def test_add_permissions(client, actors, team, actor, role, status):
    response = client.post(f"{BASE}/{team['id']}/members", headers=actors[actor]["headers"],
                           json={"email": " NEW@Example.com ", "role": role})
    assert response.status_code == status
    if status == 201:
        assert response.json()["user_id"] == actors["new"]["id"]
        assert response.json()["role"] == role


def test_add_unknown_and_duplicate(client, actors, team):
    path = f"{BASE}/{team['id']}/members"
    headers = actors["owner"]["headers"]
    assert client.post(path, headers=headers, json={"email": "missing@example.com", "role": "member"}).status_code == 404
    assert client.post(path, headers=headers, json={"email": " MEMBER@example.com ", "role": "member"}).status_code == 409


@pytest.mark.parametrize("actor", ["owner", "admin", "member"])
def test_cannot_assign_owner(client, actors, team, actor):
    path = f"{BASE}/{team['id']}/members"
    headers = actors[actor]["headers"]
    assert client.post(path, headers=headers, json={"email": "new@example.com", "role": "owner"}).status_code == 400
    assert client.patch(f"{path}/{actors['member']['id']}", headers=headers, json={"role": "owner"}).status_code == 400


@pytest.mark.parametrize("actor,target,role,status", [
    ("owner", "member", "admin", 200), ("owner", "admin", "member", 200),
    ("owner", "owner", "member", 400), ("admin", "owner", "member", 400),
    ("admin", "admin2", "member", 403), ("admin", "admin", "member", 403),
    ("admin", "member", "admin", 403), ("admin", "member", "member", 200),
    ("member", "member", "admin", 403),
])
def test_role_change_permissions(client, actors, team, db_session, actor, target, role, status):
    response = client.patch(f"{BASE}/{team['id']}/members/{actors[target]['id']}",
                            headers=actors[actor]["headers"], json={"role": role})
    assert response.status_code == status
    if status == 200:
        assert response.json()["role"] == role
    owners = list(db_session.scalars(select(TeamMember).where(TeamMember.team_id == team["id"], TeamMember.role == TeamRole.OWNER)))
    assert len(owners) == 1 and owners[0].user_id == actors["owner"]["id"]


@pytest.mark.parametrize("actor,target,status", [
    ("owner", "member", 204), ("owner", "admin", 204), ("admin", "member", 204),
    ("admin", "admin2", 403), ("admin", "admin", 403), ("admin", "owner", 400),
    ("owner", "owner", 400), ("member", "member", 403), ("member", "admin", 403),
])
def test_removal_permissions(client, actors, team, actor, target, status):
    path = f"{BASE}/{team['id']}/members/{actors[target]['id']}"
    response = client.delete(path, headers=actors[actor]["headers"])
    assert response.status_code == status
    if status == 204:
        assert not response.content
        assert client.get(f"{BASE}/{team['id']}", headers=actors[target]["headers"]).status_code == 404
        assert client.get(BASE, headers=actors[target]["headers"]).json() == []


@pytest.mark.parametrize("actor,status", [("owner", 200), ("admin", 200), ("member", 403), ("outsider", 404)])
def test_update_team_permissions(client, actors, team, actor, status):
    path = f"{BASE}/{team['id']}"
    response = client.patch(path, headers=actors[actor]["headers"], json={"name": " Revised ", "description": None})
    assert response.status_code == status
    data = client.get(path, headers=actors["owner"]["headers"]).json()
    assert data["name"] == ("Revised" if status == 200 else "Team Alpha")
    assert data["description"] == (None if status == 200 else "Initial")
    assert data["created_by_id"] == actors["owner"]["id"]


@pytest.mark.parametrize("payload", [{"name": None}, {"name": " "}, {"name": "x" * 151},
    {"created_by_id": 2}, {"description": "x" * 5001}])
def test_invalid_update(client, actors, team, payload):
    assert client.patch(f"{BASE}/{team['id']}", headers=actors["owner"]["headers"], json=payload).status_code == 422


def test_missing_target(client, actors, team):
    for user_id in (actors["outsider"]["id"], 99999):
        path = f"{BASE}/{team['id']}/members/{user_id}"
        assert client.patch(path, headers=actors["owner"]["headers"], json={"role": "member"}).status_code == 404
        assert client.delete(path, headers=actors["owner"]["headers"]).status_code == 404


def test_database_membership_constraints(actors, team, db_session):
    for user_id, role in [(actors["member"]["id"], TeamRole.MEMBER), (actors["new"]["id"], TeamRole.OWNER),
                          (99999, TeamRole.MEMBER)]:
        db_session.add(TeamMember(team_id=team["id"], user_id=user_id, role=role))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
    db_session.add(TeamMember(team_id=99999, user_id=actors["new"]["id"], role=TeamRole.MEMBER))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    with pytest.raises(IntegrityError):
        db_session.execute(text("UPDATE team_members SET role = 'invalid' WHERE user_id = :user"), {"user": actors["member"]["id"]})
    db_session.rollback()
    assert db_session.scalar(text("SELECT role FROM team_members WHERE user_id = :user"), {"user": actors["owner"]["id"]}) == "owner"


def test_team_creator_foreign_key(actors, db_session):
    db_session.add(Team(name="Invalid creator", created_by_id=99999))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
