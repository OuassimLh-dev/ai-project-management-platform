from datetime import date, datetime, timezone
from itertools import product

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token, hash_password
from app.models import Project, ProjectMember, ProjectRole, Sprint, SprintStatus, Team, TeamMember, TeamRole, User

PAYLOAD = {"name": " Sprint one ", "goal": " Deliver foundation ", "start_date": "2026-10-01", "end_date": "2026-10-14"}


@pytest.fixture(scope="module")
def password_hash():
    return hash_password("Sprint-test-password-123!")


@pytest.fixture
def setup(db_session, settings, password_hash):
    actors = {}
    for name in ("owner", "admin", "manager", "member", "unassigned", "outsider"):
        user = User(first_name=name.title(), last_name="Test", email=f"{name}@example.com", hashed_password=password_hash)
        db_session.add(user)
        db_session.flush()
        actors[name] = {"id": user.id, "headers": {"Authorization": f"Bearer {create_access_token(user.id, settings)}"}}
    team = Team(name="Sprint team", created_by_id=actors["owner"]["id"])
    db_session.add(team)
    db_session.flush()
    for name, actor in actors.items():
        if name != "outsider":
            db_session.add(TeamMember(team_id=team.id, user_id=actor["id"], role=TeamRole(name) if name in ("owner", "admin") else TeamRole.MEMBER))
    projects = []
    for key in ("ONE", "TWO"):
        project = Project(team_id=team.id, name=key, key=key, created_by_id=actors["owner"]["id"])
        db_session.add(project)
        db_session.flush()
        projects.append(project.id)
    for name in ("manager", "member"):
        db_session.add(ProjectMember(project_id=projects[0], user_id=actors[name]["id"], role=ProjectRole(name)))
    db_session.commit()
    return {"actors": actors, "project_id": projects[0], "other_id": projects[1], "path": f"/api/v1/projects/{projects[0]}/sprints"}


@pytest.fixture
def sprint(client, setup):
    response = client.post(setup["path"], headers=setup["actors"]["manager"]["headers"], json=PAYLOAD)
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize("actor,expected", [("owner", 201), ("admin", 201), ("manager", 201), ("member", 403), ("unassigned", 404), ("outsider", 404)])
def test_create_access_and_defaults(client, setup, db_session, actor, expected):
    response = client.post(setup["path"], headers=setup["actors"][actor]["headers"], json=PAYLOAD)
    assert response.status_code == expected
    rows = list(db_session.scalars(select(Sprint)))
    if expected != 201:
        assert rows == []
        return
    data = response.json()
    assert set(data) == {"id", "project_id", "name", "goal", "start_date", "end_date", "status", "created_at", "updated_at"}
    assert data["name"] == "Sprint one" and data["goal"] == "Deliver foundation"
    assert data["status"] == "planned" and data["project_id"] == setup["project_id"]
    assert data["created_at"] and data["updated_at"]
    assert rows[0].project.id == setup["project_id"]
    assert rows[0].status is SprintStatus.PLANNED


@pytest.mark.parametrize("method,path,body", [("POST", "/projects/1/sprints", PAYLOAD), ("GET", "/projects/1/sprints", None), ("GET", "/sprints/1", None), ("PATCH", "/sprints/1", {"name": "New"})])
def test_auth_required(client, method, path, body):
    assert client.request(method, "/api/v1" + path, json=body).status_code == 401


@pytest.mark.parametrize("actor,read,write", [("owner", 200, 200), ("admin", 200, 200), ("manager", 200, 200), ("member", 200, 403), ("unassigned", 404, 404), ("outsider", 404, 404)])
def test_read_and_update_permissions(client, setup, sprint, actor, read, write):
    headers = setup["actors"][actor]["headers"]
    assert client.get(setup["path"], headers=headers).status_code == read
    path = f"/api/v1/sprints/{sprint['id']}"
    assert client.get(path, headers=headers).status_code == read
    assert client.patch(path, headers=headers, json={"name": "Updated"}).status_code == write
    actual = client.get(path, headers=setup["actors"]["owner"]["headers"]).json()
    assert actual["name"] == ("Updated" if write == 200 else sprint["name"])


@pytest.mark.parametrize("changes", [{"name": " "}, {"name": "x" * 151}, {"goal": "x" * 5001}, {"name": None}, {"start_date": None}, {"end_date": None}, {"status": None}, {"status": "invalid"}, {"project_id": 1}, {"created_by_id": 1}, {"start_date": "bad"}, {"start_date": "2026-11-01", "end_date": "2026-10-01"}])
def test_invalid_payloads(client, setup, sprint, changes):
    headers = setup["actors"]["manager"]["headers"]
    assert client.post(setup["path"], headers=headers, json=PAYLOAD | changes).status_code == 422
    assert client.patch(f"/api/v1/sprints/{sprint['id']}", headers=headers, json=changes).status_code == 422


@pytest.mark.parametrize("field", ["name", "start_date", "end_date"])
def test_required_create_fields(client, setup, field):
    body = PAYLOAD.copy()
    del body[field]
    assert client.post(setup["path"], headers=setup["actors"]["manager"]["headers"], json=body).status_code == 422


@pytest.mark.parametrize("status", ["active", "completed", "cancelled"])
def test_new_sprints_must_be_planned(client, setup, status):
    assert client.post(setup["path"], headers=setup["actors"]["manager"]["headers"], json=PAYLOAD | {"status": status}).status_code == 400


@pytest.mark.parametrize("current,requested", list(product(SprintStatus, repeat=2)))
def test_lifecycle(client, setup, sprint, db_session, current, requested):
    row = db_session.get(Sprint, sprint["id"])
    row.status = current
    db_session.commit()
    allowed = current == requested or (current.value, requested.value) in {("planned", "active"), ("planned", "cancelled"), ("active", "completed"), ("active", "cancelled")}
    response = client.patch(f"/api/v1/sprints/{row.id}", headers=setup["actors"]["manager"]["headers"], json={"status": requested.value, "name": "Changed"})
    assert response.status_code == (200 if allowed else 400)
    db_session.refresh(row)
    assert row.status == (requested if allowed else current)
    assert row.name == ("Changed" if allowed else sprint["name"])


def test_updates_dates_optional_goal_and_timestamps(client, setup, sprint, db_session):
    headers = setup["actors"]["manager"]["headers"]
    path = f"/api/v1/sprints/{sprint['id']}"
    row = db_session.get(Sprint, sprint["id"])
    row.updated_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
    db_session.commit()
    for change in ({"start_date": "2026-10-15"}, {"end_date": "2026-09-30"}):
        assert client.patch(path, headers=headers, json=change | {"name": "Must not persist"}).status_code == 400
        assert client.get(path, headers=headers).json()["name"] == sprint["name"]
    result = client.patch(path, headers=headers, json={"name": " Updated ", "start_date": "2026-11-01", "end_date": "2026-11-01", "status": "active"}).json()
    assert result["name"] == "Updated" and result["goal"] == sprint["goal"]
    assert result["start_date"] == result["end_date"] == "2026-11-01"
    assert result["updated_at"] != "2000-01-01T00:00:00"
    assert client.patch(path, headers=headers, json={"goal": None}).json()["goal"] is None
    assert client.patch(path, headers=headers, json={}).status_code == 200
    assert client.patch(path, headers=headers, json={"goal": " Trimmed "}).json()["goal"] == "Trimmed"


def test_listing_isolation_duplicate_names_and_independent_access(client, setup, sprint, db_session):
    owner = setup["actors"]["owner"]["headers"]
    member = setup["actors"]["member"]["headers"]
    other_path = f"/api/v1/projects/{setup['other_id']}/sprints"
    assert client.get(other_path, headers=owner).json() == []
    other = client.post(other_path, headers=owner, json=PAYLOAD).json()
    second = client.post(setup["path"], headers=owner, json=PAYLOAD).json()
    listed = client.get(setup["path"], headers=member).json()
    assert [item["id"] for item in listed] == [sprint["id"], second["id"]]
    path = f"/api/v1/sprints/{other['id']}"
    assert client.get(path, headers=member).status_code == 404
    assert client.patch(path, headers=setup["actors"]["manager"]["headers"], json={"name": "Forbidden"}).status_code == 404
    assert client.get(other_path, headers=member).status_code == 404
    assert client.patch(path, headers=owner, json={"project_id": setup["project_id"]}).status_code == 422
    db_session.add(ProjectMember(project_id=setup["other_id"], user_id=setup["actors"]["member"]["id"], role=ProjectRole.MEMBER))
    db_session.commit()
    assert client.get(path, headers=member).status_code == 200
    assert client.patch(path, headers=member, json={"name": "Denied"}).status_code == 403


def test_inactive_project_and_same_day_optional_goal(client, setup, db_session):
    project = db_session.get(Project, setup["project_id"])
    project.is_active = False
    db_session.commit()
    headers = setup["actors"]["manager"]["headers"]
    body = {"name": "Same day", "start_date": "2020-01-01", "end_date": "2020-01-01"}
    response = client.post(setup["path"], headers=headers, json=body)
    assert response.status_code == 201
    data = response.json()
    assert data["goal"] is None and data["status"] == "planned"
    assert client.patch(f"/api/v1/sprints/{data['id']}", headers=headers, json={"name": "Still editable"}).status_code == 200


@pytest.mark.parametrize("method,path,body", [("POST", "/projects/9999/sprints", PAYLOAD), ("GET", "/projects/9999/sprints", None), ("GET", "/sprints/9999", None), ("PATCH", "/sprints/9999", {"name": "Updated"})])
def test_missing_resources(client, setup, method, path, body):
    assert client.request(method, "/api/v1" + path, headers=setup["actors"]["owner"]["headers"], json=body).status_code == 404


@pytest.mark.parametrize("changes", [{"project_id": 9999}, {"name": " "}, {"end_date": "2026-09-01"}, {"status": "invalid"}])
def test_database_constraints(setup, db_session, changes):
    values = {"project_id": setup["project_id"], "name": "Constraint", "start_date": "2026-10-01", "end_date": "2026-10-14", "status": "planned"} | changes
    with pytest.raises(IntegrityError):
        db_session.execute(text("INSERT INTO sprints (project_id, name, start_date, end_date, status) VALUES (:project_id, :name, :start_date, :end_date, :status)"), values)
        db_session.commit()
    db_session.rollback()


@pytest.mark.parametrize("status", list(SprintStatus))
def test_model_status_and_timestamps(setup, db_session, status):
    row = Sprint(project_id=setup["project_id"], name="Model", start_date=date(2026, 10, 1), end_date=date(2026, 10, 1), status=status)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    assert row.status is status and row.created_at and row.updated_at
    assert row.project.id == setup["project_id"]
    assert db_session.scalar(text("SELECT status FROM sprints WHERE id = :id"), {"id": row.id}) == status.value
