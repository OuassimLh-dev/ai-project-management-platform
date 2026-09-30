from datetime import datetime, timezone

import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token, hash_password
from app.models import Project, ProjectMember, ProjectRole, Team, TeamMember, TeamRole, User
from app.schemas.project import ProjectCreate, ProjectMemberAddRequest
from app.services import project as service
from app.services.project_authorization import ProjectError

BASE = "/api/v1/projects"


@pytest.fixture(scope="module")
def password_hash():
    return hash_password("Fake-project-test-password-123!")


@pytest.fixture
def setup(db_session, settings, password_hash):
    actors = {}
    for name in ("owner", "admin", "manager", "manager2", "member", "unassigned", "outsider", "new"):
        user = User(first_name=name.title(), last_name="Test", email=f"{name}@example.com", hashed_password=password_hash)
        db_session.add(user)
        db_session.flush()
        actors[name] = {"id": user.id, "headers": {"Authorization": f"Bearer {create_access_token(user.id, settings)}"}}
    team = Team(name="Parent", created_by_id=actors["owner"]["id"])
    db_session.add(team)
    db_session.flush()
    for name, actor in actors.items():
        if name != "outsider":
            db_session.add(TeamMember(team_id=team.id, user_id=actor["id"], role=TeamRole(name) if name in ("owner", "admin") else TeamRole.MEMBER))
    db_session.commit()
    return {"actors": actors, "team_id": team.id, "path": f"/api/v1/teams/{team.id}/projects"}


@pytest.fixture
def project(client, setup):
    actors = setup["actors"]
    response = client.post(setup["path"], headers=actors["owner"]["headers"], json={"name": "Project", "key": "API"})
    assert response.status_code == 201
    project = response.json()
    path = f"{BASE}/{project['id']}/members"
    for name, role in (("manager", "manager"), ("member", "member")):
        assert client.post(path, headers=actors["owner"]["headers"], json={"user_id": actors[name]["id"], "role": role}).status_code == 201
    assert client.delete(f"{path}/{actors['owner']['id']}", headers=actors["owner"]["headers"]).status_code == 204
    return project


@pytest.mark.parametrize("actor,status", [("owner", 201), ("admin", 201), ("member", 403), ("outsider", 404)])
def test_creation_permissions(client, setup, db_session, actor, status):
    who = setup["actors"][actor]
    response = client.post(setup["path"], headers=who["headers"], json={"name": " Project name ", "key": " app ", "description": " Notes "})
    assert response.status_code == status
    if status != 201:
        assert db_session.scalar(select(func.count()).select_from(Project)) == 0
        return
    data = response.json()
    assert data["name"] == "Project name" and data["key"] == "APP" and data["description"] == "Notes"
    assert data["created_by_id"] == who["id"] and data["team_id"] == setup["team_id"]
    assert data["is_active"] is True and data["created_at"] and data["updated_at"]
    assert set(data) == {"id", "team_id", "name", "key", "description", "created_by_id", "is_active", "created_at", "updated_at"}
    members = list(db_session.scalars(select(ProjectMember).where(ProjectMember.project_id == data["id"])))
    assert len(members) == 1 and members[0].role == ProjectRole.MANAGER
    assert members[0].user_id == who["id"] and members[0].joined_at


def test_atomic_creation(setup, db_session):
    def fail(*args):
        raise RuntimeError("membership failure")
    event.listen(ProjectMember, "before_insert", fail)
    try:
        with pytest.raises(RuntimeError, match="membership failure"):
            service.create_project(db_session, setup["team_id"], setup["actors"]["owner"]["id"], ProjectCreate(name="Rollback", key="ROLL"))
    finally:
        event.remove(ProjectMember, "before_insert", fail)
    assert db_session.scalar(select(func.count()).select_from(Project)) == 0
    assert db_session.scalar(select(func.count()).select_from(ProjectMember)) == 0


@pytest.mark.parametrize("method,path,body", [
    ("POST", "/api/v1/teams/1/projects", {"name": "Test", "key": "TEST"}),
    ("GET", "/api/v1/teams/1/projects", None), ("GET", BASE + "/1", None),
    ("PATCH", BASE + "/1", {"name": "New"}), ("GET", BASE + "/1/members", None),
    ("POST", BASE + "/1/members", {"user_id": 1, "role": "member"}),
    ("PATCH", BASE + "/1/members/1", {"role": "member"}), ("DELETE", BASE + "/1/members/1", None),
])
def test_auth_required(client, method, path, body):
    assert client.request(method, path, json=body).status_code == 401


@pytest.mark.parametrize("changes", [{"name": " "}, {"name": "x" * 151}, {"key": ""}, {"key": "2BAD"},
    {"key": "A-B"}, {"key": "A" * 21}, {"description": "x" * 5001}, {"team_id": 1}, {"created_by_id": 1}])
def test_invalid_create(client, setup, changes):
    assert client.post(setup["path"], headers=setup["actors"]["owner"]["headers"],
                       json={"name": "Valid", "key": "VALID"} | changes).status_code == 422


def test_key_scope_and_conflicts(client, setup, project):
    headers = setup["actors"]["owner"]["headers"]
    assert client.post(setup["path"], headers=headers, json={"name": "Duplicate", "key": " api "}).status_code == 409
    second = client.post(setup["path"], headers=headers, json={"name": "Second", "key": "TWO"}).json()
    assert client.patch(f"{BASE}/{second['id']}", headers=headers, json={"key": "api"}).status_code == 409
    another_team = client.post("/api/v1/teams", headers=headers, json={"name": "Another"}).json()
    assert client.post(f"/api/v1/teams/{another_team['id']}/projects", headers=headers,
                       json={"name": "Same key, different team", "key": "API"}).status_code == 201


def test_listing_visibility_order_and_team_scope(client, setup, project):
    actors = setup["actors"]
    second = client.post(setup["path"], headers=actors["admin"]["headers"], json={"name": "Second", "key": "TWO"}).json()
    for name in ("owner", "admin"):
        assert [p["id"] for p in client.get(setup["path"], headers=actors[name]["headers"]).json()] == [project["id"], second["id"]]
    for name in ("manager", "member"):
        assert [p["id"] for p in client.get(setup["path"], headers=actors[name]["headers"]).json()] == [project["id"]]
    assert client.get(setup["path"], headers=actors["unassigned"]["headers"]).json() == []
    assert client.get(setup["path"], headers=actors["outsider"]["headers"]).status_code == 404
    assert client.get("/api/v1/teams/99999/projects", headers=actors["owner"]["headers"]).status_code == 404
    assert client.post("/api/v1/teams/99999/projects", headers=actors["owner"]["headers"], json={"name": "Missing", "key": "MISS"}).status_code == 404
    another = client.post("/api/v1/teams", headers=actors["owner"]["headers"], json={"name": "Separate"}).json()
    assert client.get(f"/api/v1/teams/{another['id']}/projects", headers=actors["owner"]["headers"]).json() == []


@pytest.mark.parametrize("actor,status", [("owner", 200), ("admin", 200), ("manager", 200), ("member", 200), ("unassigned", 404), ("outsider", 404)])
def test_access_and_members(client, setup, project, actor, status):
    headers = setup["actors"][actor]["headers"]
    response = client.get(f"{BASE}/{project['id']}", headers=headers)
    assert response.status_code == status
    response = client.get(f"{BASE}/{project['id']}/members", headers=headers)
    assert response.status_code == status
    if status == 200:
        assert len(response.json()) == 2
        for member in response.json():
            assert set(member) == {"id", "project_id", "user_id", "role", "joined_at"}


@pytest.mark.parametrize("actor,status", [("owner", 200), ("admin", 200), ("manager", 200), ("member", 403), ("unassigned", 404), ("outsider", 404)])
def test_update_permissions(client, setup, project, actor, status):
    path = f"{BASE}/{project['id']}"
    response = client.patch(path, headers=setup["actors"][actor]["headers"], json={"name": " Revised ", "description": None, "is_active": False})
    assert response.status_code == status
    record = client.get(path, headers=setup["actors"]["owner"]["headers"]).json()
    assert record["name"] == ("Revised" if status == 200 else "Project")
    assert record["team_id"] == setup["team_id"]


@pytest.mark.parametrize("body", [{"name": None}, {"name": " "}, {"key": None}, {"is_active": None},
    {"team_id": 1}, {"created_by_id": 1}, {"description": "x" * 5001}])
def test_invalid_update(client, setup, project, body):
    assert client.patch(f"{BASE}/{project['id']}", headers=setup["actors"]["owner"]["headers"], json=body).status_code == 422


@pytest.mark.parametrize("actor,role,status", [("manager", "manager", 201), ("manager", "member", 201),
    ("owner", "manager", 201), ("admin", "member", 201), ("member", "member", 403),
    ("unassigned", "member", 404), ("outsider", "member", 404)])
def test_add_permissions(client, setup, project, actor, role, status):
    response = client.post(f"{BASE}/{project['id']}/members", headers=setup["actors"][actor]["headers"],
                           json={"user_id": setup["actors"]["new"]["id"], "role": role})
    assert response.status_code == status
    if status == 201:
        assert response.json()["role"] == role


def test_target_must_belong_to_team(client, setup, project, db_session):
    path = f"{BASE}/{project['id']}/members"
    headers = setup["actors"]["manager"]["headers"]
    for name, status in (("outsider", 400), ("member", 409)):
        assert client.post(path, headers=headers, json={"user_id": setup["actors"][name]["id"], "role": "member"}).status_code == status
    assert client.post(path, headers=headers, json={"user_id": 99999, "role": "member"}).status_code == 404
    assert db_session.scalar(select(TeamMember.id).where(TeamMember.user_id == setup["actors"]["outsider"]["id"])) is None


@pytest.mark.parametrize("body", [{"user_id": 0, "role": "member"}, {"user_id": -1, "role": "member"},
    {"user_id": True, "role": "member"}, {"user_id": 1, "role": "developer"},
    {"user_id": 1, "role": "owner"}, {"user_id": 1, "role": "member", "extra": "no"}])
def test_invalid_member_payload(client, setup, project, body):
    assert client.post(f"{BASE}/{project['id']}/members", headers=setup["actors"]["owner"]["headers"], json=body).status_code == 422


@pytest.mark.parametrize("actor,status", [("owner", 200), ("admin", 200), ("manager", 200), ("member", 403), ("unassigned", 404), ("outsider", 404)])
def test_promote_then_demote(client, setup, project, actor, status):
    headers = setup["actors"][actor]["headers"]
    path = f"{BASE}/{project['id']}/members/{setup['actors']['member']['id']}"
    response = client.patch(path, headers=headers, json={"role": "manager"})
    assert response.status_code == status
    if status == 200:
        assert response.json()["role"] == "manager"
        assert client.patch(path, headers=headers, json={"role": "member"}).json()["role"] == "member"


@pytest.mark.parametrize("actor", ["owner", "admin", "manager"])
@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
def test_last_manager_protected(client, setup, project, actor, method):
    response = client.request(method, f"{BASE}/{project['id']}/members/{setup['actors']['manager']['id']}",
                              headers=setup["actors"][actor]["headers"], json={"role": "member"} if method == "PATCH" else None)
    assert response.status_code == 400
    assert "at least one manager" in response.json()["detail"]


@pytest.mark.parametrize("actor,status", [("owner", 204), ("admin", 204), ("manager", 204), ("member", 403), ("unassigned", 404), ("outsider", 404)])
def test_remove_member(client, setup, project, actor, status):
    response = client.delete(f"{BASE}/{project['id']}/members/{setup['actors']['member']['id']}", headers=setup["actors"][actor]["headers"])
    assert response.status_code == status
    if status == 204:
        assert response.content == b""
        assert client.get(f"{BASE}/{project['id']}", headers=setup["actors"]["member"]["headers"]).status_code == 404


def test_remove_another_manager_and_self_demotion(client, setup, project):
    actors = setup["actors"]
    path = f"{BASE}/{project['id']}/members"
    headers = actors["manager"]["headers"]
    assert client.post(path, headers=headers, json={"user_id": actors["manager2"]["id"], "role": "manager"}).status_code == 201
    assert client.delete(f"{path}/{actors['manager2']['id']}", headers=headers).status_code == 204
    assert client.post(path, headers=headers, json={"user_id": actors["manager2"]["id"], "role": "manager"}).status_code == 201
    assert client.patch(f"{path}/{actors['manager']['id']}", headers=headers, json={"role": "member"}).status_code == 200
    assert client.patch(f"{BASE}/{project['id']}", headers=headers, json={"name": "Denied now"}).status_code == 403


def test_invalid_role_and_missing_target(client, setup, project):
    headers = setup["actors"]["manager"]["headers"]
    for role in ("admin", "owner", "developer", None):
        assert client.patch(f"{BASE}/{project['id']}/members/{setup['actors']['member']['id']}", headers=headers, json={"role": role}).status_code == 422
    for user_id in (setup["actors"]["unassigned"]["id"], 99999):
        assert client.patch(f"{BASE}/{project['id']}/members/{user_id}", headers=headers, json={"role": "member"}).status_code == 404
        assert client.delete(f"{BASE}/{project['id']}/members/{user_id}", headers=headers).status_code == 404


@pytest.mark.parametrize("method,suffix,body", [("GET", "", None), ("PATCH", "", {"name": "New"}),
    ("GET", "/members", None), ("POST", "/members", {"user_id": 1, "role": "member"}),
    ("PATCH", "/members/1", {"role": "member"}), ("DELETE", "/members/1", None)])
def test_missing_project(client, setup, method, suffix, body):
    assert client.request(method, BASE + "/99999" + suffix, headers=setup["actors"]["owner"]["headers"], json=body).status_code == 404


def test_team_removal_cannot_orphan_project_members(client, setup, project):
    actors = setup["actors"]
    for target in ("member", "manager"):
        path = f"/api/v1/teams/{setup['team_id']}/members/{actors[target]['id']}"
        assert client.delete(path, headers=actors["owner"]["headers"]).status_code == 400
    assert client.delete(f"{BASE}/{project['id']}/members/{actors['member']['id']}", headers=actors["owner"]["headers"]).status_code == 204
    assert client.delete(f"/api/v1/teams/{setup['team_id']}/members/{actors['member']['id']}", headers=actors["owner"]["headers"]).status_code == 204
    assert client.post(f"{BASE}/{project['id']}/members", headers=actors["owner"]["headers"], json={"user_id": actors["member"]["id"], "role": "member"}).status_code == 400


def test_membership_duplicate_race_rolls_back(setup, project, db_session, monkeypatch):
    real = service.get_project_membership
    calls = 0
    def miss_once(db, project_id, user_id):
        nonlocal calls
        calls += 1
        return None if calls == 1 else real(db, project_id, user_id)
    monkeypatch.setattr(service, "get_project_membership", miss_once)
    with pytest.raises(ProjectError) as error:
        service.add_member(db_session, project["id"], setup["actors"]["owner"]["id"],
                           ProjectMemberAddRequest(user_id=setup["actors"]["member"]["id"], role="member"))
    assert error.value.status_code == 409
    assert db_session.scalar(select(func.count()).select_from(ProjectMember)) == 2


def test_project_database_constraints_and_timestamps(setup, project, db_session):
    record = db_session.get(Project, project["id"])
    created = record.created_at
    record.updated_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
    db_session.commit()
    record.name = "Changed"
    db_session.commit()
    db_session.refresh(record)
    assert record.updated_at.year > 2000 and record.created_at == created
    for team_id, creator_id, key, name in [(99999, setup["actors"]["owner"]["id"], "NEW", "Valid"),
        (setup["team_id"], 99999, "NEW", "Valid"), (setup["team_id"], setup["actors"]["owner"]["id"], "API", "Duplicate"),
        (setup["team_id"], setup["actors"]["owner"]["id"], "NEW", " ")]:
        db_session.add(Project(team_id=team_id, created_by_id=creator_id, key=key, name=name))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
    for project_id, user_id in [(project["id"], setup["actors"]["member"]["id"]), (99999, setup["actors"]["new"]["id"]), (project["id"], 99999)]:
        db_session.add(ProjectMember(project_id=project_id, user_id=user_id, role=ProjectRole.MEMBER))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
    with pytest.raises(IntegrityError):
        db_session.execute(text("UPDATE project_members SET role = 'invalid'"))
    db_session.rollback()
    assert db_session.scalar(text("SELECT role FROM project_members WHERE user_id = :user"), {"user": setup["actors"]["manager"]["id"]}) == "manager"
