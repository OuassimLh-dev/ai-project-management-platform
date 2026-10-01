from datetime import date, datetime, timezone
from itertools import product

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token, hash_password
from app.models import Issue, IssueType, IssuePriority, IssueStatus, Project, ProjectMember, ProjectRole, Sprint, Team, TeamMember, TeamRole, User
from app.schemas.issue import IssueCreate
from app.services import issue as service

PAYLOAD = {"title": " Fix login ", "description": " Reproduction steps ", "issue_type": "bug"}


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
    return {"actors": actors, "project_id": projects[0], "other_id": projects[1], "path": f"/api/v1/projects/{projects[0]}/issues"}


@pytest.fixture
def issue(client, setup):
    response = client.post(setup["path"], headers=setup["actors"]["member"]["headers"], json=PAYLOAD)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def sprints(setup, db_session):
    rows = [Sprint(project_id=project_id, name="Iteration", start_date=date(2026, 1, 1), end_date=date(2026, 1, 2))
            for project_id in (setup["project_id"], setup["project_id"], setup["other_id"])]
    db_session.add_all(rows)
    db_session.commit()
    return [row.id for row in rows]


@pytest.mark.parametrize("actor,allowed", [("owner", True), ("admin", True), ("manager", True), ("member", True), ("unassigned", False), ("outsider", False)])
def test_permissions(client, setup, issue, actor, allowed):
    headers = setup["actors"][actor]["headers"]
    path = f"/api/v1/issues/{issue['id']}"
    assert client.post(setup["path"], headers=headers, json=PAYLOAD).status_code == (201 if allowed else 404)
    assert client.get(setup["path"], headers=headers).status_code == (200 if allowed else 404)
    assert client.get(path, headers=headers).status_code == (200 if allowed else 404)
    assert client.patch(path, headers=headers, json={"title": "Updated"}).status_code == (200 if allowed else 404)


@pytest.mark.parametrize("method,path,body", [("POST", "/projects/1/issues", PAYLOAD), ("GET", "/projects/1/issues", None), ("GET", "/issues/1", None), ("PATCH", "/issues/1", {"title": "New"})])
def test_authentication(client, method, path, body):
    assert client.request(method, "/api/v1" + path, json=body).status_code == 401


@pytest.mark.parametrize("actor", ["owner", "admin", "manager", "member"])
def test_creation_defaults_reporter(client, setup, db_session, actor):
    response = client.post(setup["path"], headers=setup["actors"][actor]["headers"], json=PAYLOAD)
    data = response.json()
    assert response.status_code == 201
    assert data["title"] == "Fix login" and data["description"] == "Reproduction steps"
    assert data["reporter_id"] == setup["actors"][actor]["id"]
    assert data["number"] == 1 and data["issue_key"] == "ONE-1"
    assert data["status"] == "backlog" and data["priority"] == "medium"
    assert data["assignee_id"] is None and data["sprint_id"] is None
    assert set(data) == {"id", "project_id", "number", "issue_key", "title", "description", "issue_type", "priority", "status", "reporter_id", "assignee_id", "sprint_id", "created_at", "updated_at"}
    row = db_session.get(Issue, data["id"])
    assert row.created_by_id == row.reporter_id == data["reporter_id"]
    assert row.reporter.id == data["reporter_id"] and row.project.id == data["project_id"]


@pytest.mark.parametrize("field,value", [("id", 1), ("project_id", 1), ("number", 1), ("reporter_id", 1), ("created_by_id", 1), ("created_at", "2026-01-01"), ("updated_at", "2026-01-01"), ("title", " "), ("title", "x" * 201), ("description", "x" * 10001), ("title", None), ("issue_type", None), ("priority", None), ("status", None), ("issue_type", "invalid"), ("priority", "invalid"), ("status", "invalid"), ("assignee_id", True), ("sprint_id", False), ("assignee_id", 0), ("sprint_id", -1), ("assignee_id", 1.2), ("sprint_id", "1")])
def test_invalid_inputs(client, setup, issue, field, value):
    headers = setup["actors"]["member"]["headers"]
    assert client.post(setup["path"], headers=headers, json=PAYLOAD | {field: value}).status_code == 422
    assert client.patch(f"/api/v1/issues/{issue['id']}", headers=headers, json={field: value}).status_code == 422


@pytest.mark.parametrize("field", ["title", "issue_type"])
def test_required_fields(client, setup, field):
    payload = PAYLOAD.copy()
    del payload[field]
    assert client.post(setup["path"], headers=setup["actors"]["member"]["headers"], json=payload).status_code == 422


def test_numbering_and_key_changes(client, setup):
    headers = setup["actors"]["owner"]["headers"]
    for number in (1, 2, 3):
        data = client.post(setup["path"], headers=headers, json=PAYLOAD).json()
        assert data["number"] == number and data["issue_key"] == f"ONE-{number}"
    other = client.post(f"/api/v1/projects/{setup['other_id']}/issues", headers=headers, json=PAYLOAD).json()
    assert other["number"] == 1 and other["issue_key"] == "TWO-1"
    assert client.patch(f"/api/v1/projects/{setup['project_id']}", headers=headers, json={"key": "NEW"}).status_code == 200
    listed = client.get(setup["path"], headers=headers).json()
    assert [row["number"] for row in listed] == [1, 2, 3]
    assert [row["issue_key"] for row in listed] == ["NEW-1", "NEW-2", "NEW-3"]


@pytest.mark.parametrize("actor,expected", [("member", 201), ("manager", 201), ("owner", 400), ("admin", 400), ("unassigned", 400), ("outsider", 400), (None, 404)])
def test_assignee_rules(client, setup, issue, actor, expected):
    target = setup["actors"][actor]["id"] if actor else 9999
    headers = setup["actors"]["member"]["headers"]
    assert client.post(setup["path"], headers=headers, json=PAYLOAD | {"assignee_id": target}).status_code == expected
    assert client.patch(f"/api/v1/issues/{issue['id']}", headers=headers, json={"assignee_id": target}).status_code == (200 if expected == 201 else expected)


@pytest.mark.parametrize("index,expected", [(0, 201), (2, 400), (None, 404)])
def test_sprint_rules(client, setup, issue, sprints, index, expected):
    sprint_id = sprints[index] if index is not None else 9999
    headers = setup["actors"]["member"]["headers"]
    assert client.post(setup["path"], headers=headers, json=PAYLOAD | {"sprint_id": sprint_id}).status_code == expected
    assert client.patch(f"/api/v1/issues/{issue['id']}", headers=headers, json={"sprint_id": sprint_id}).status_code == (200 if expected == 201 else expected)


def test_updates_and_nullable_fields(client, setup, issue, sprints, db_session):
    headers = setup["actors"]["member"]["headers"]
    path = f"/api/v1/issues/{issue['id']}"
    row = db_session.get(Issue, issue["id"])
    row.updated_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
    db_session.commit()
    for actor, sprint_id in zip(("member", "manager"), sprints):
        response = client.patch(path, headers=headers, json={"title": " Changed ", "description": " Notes ", "issue_type": "feature", "priority": "critical", "status": "done", "assignee_id": setup["actors"][actor]["id"], "sprint_id": sprint_id})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Changed" and data["description"] == "Notes"
        assert data["status"] == "done" and data["priority"] == "critical" and data["issue_type"] == "feature"
        assert data["assignee_id"] == setup["actors"][actor]["id"] and data["sprint_id"] == sprint_id
        assert not data["updated_at"].startswith("2000-")
    assert client.patch(path, headers=headers, json={}).json() == data
    cleared = client.patch(path, headers=headers, json={"description": None, "assignee_id": None, "sprint_id": None}).json()
    assert all(cleared[field] is None for field in ("description", "assignee_id", "sprint_id"))
    assert cleared["status"] == "done" and cleared["reporter_id"] == issue["reporter_id"]
    failed = client.patch(path, headers=headers, json={"title": "Bad mutation", "assignee_id": 9999})
    assert failed.status_code == 404
    assert client.get(path, headers=headers).json()["title"] == "Changed"


@pytest.mark.parametrize("initial,target", list(product(IssueStatus, repeat=2)))
def test_free_status_changes(client, setup, initial, target):
    headers = setup["actors"]["member"]["headers"]
    created = client.post(setup["path"], headers=headers, json=PAYLOAD | {"status": initial.value})
    assert created.status_code == 201
    result = client.patch(f"/api/v1/issues/{created.json()['id']}", headers=headers, json={"status": target.value})
    assert result.status_code == 200 and result.json()["status"] == target.value


@pytest.mark.parametrize("filters", [{"status": "todo"}, {"priority": "high"}, {"issue_type": "task"}, {"assignee_id": "member"}, {"sprint_id": "same"}, {"status": "todo", "priority": "high", "issue_type": "task", "assignee_id": "member", "sprint_id": "same"}])
def test_filters(client, setup, sprints, filters):
    headers = setup["actors"]["owner"]["headers"]
    target = {"status": "todo", "priority": "high", "issue_type": "task", "assignee_id": setup["actors"]["member"]["id"], "sprint_id": sprints[0]}
    client.post(setup["path"], headers=headers, json=PAYLOAD)
    wanted = client.post(setup["path"], headers=headers, json=PAYLOAD | target).json()
    client.post(f"/api/v1/projects/{setup['other_id']}/issues", headers=headers, json=PAYLOAD | {"status": "todo", "priority": "high", "issue_type": "task"})
    query = {key: target[key] for key in filters}
    assert [row["id"] for row in client.get(setup["path"], headers=headers, params=query).json()] == [wanted["id"]]


@pytest.mark.parametrize("query", [{"status": "invalid"}, {"priority": "invalid"}, {"issue_type": "invalid"}, {"assignee_id": "true"}, {"sprint_id": -1}, {"assignee_id": "1.5"}])
def test_invalid_filters(client, setup, query):
    assert client.get(setup["path"], headers=setup["actors"]["member"]["headers"], params=query).status_code == 422


def test_cross_project_isolation(client, setup, sprints, db_session):
    owner = setup["actors"]["owner"]["headers"]
    member = setup["actors"]["member"]["headers"]
    path = f"/api/v1/projects/{setup['other_id']}/issues"
    other = client.post(path, headers=owner, json=PAYLOAD).json()
    detail = f"/api/v1/issues/{other['id']}"
    assert client.get(detail, headers=member).status_code == 404
    assert client.patch(detail, headers=member, json={"title": "Hidden"}).status_code == 404
    assert client.get(path, headers=member).status_code == 404
    assert client.get(setup["path"], headers=member).json() == []
    for change in ({"sprint_id": sprints[0]}, {"assignee_id": setup["actors"]["member"]["id"]}):
        assert client.patch(detail, headers=owner, json=change).status_code == 400
    db_session.add(ProjectMember(project_id=setup["other_id"], user_id=setup["actors"]["member"]["id"], role=ProjectRole.MEMBER))
    db_session.commit()
    assert client.get(detail, headers=member).status_code == 200
    assert client.patch(detail, headers=member, json={"title": "Independent access"}).status_code == 200


@pytest.mark.parametrize("method,path,body", [("POST", "/projects/9999/issues", PAYLOAD), ("GET", "/projects/9999/issues", None), ("GET", "/issues/9999", None), ("PATCH", "/issues/9999", {"title": "New"})])
def test_missing_resources(client, setup, method, path, body):
    assert client.request(method, "/api/v1" + path, headers=setup["actors"]["owner"]["headers"], json=body).status_code == 404


@pytest.mark.parametrize("changes", [{"project_id": 9999}, {"created_by_id": 9999}, {"assignee_id": 9999}, {"sprint_id": 9999}, {"title": " "}, {"number": 0}, {"number": 1}, {"issue_type": "invalid"}, {"status": "invalid"}, {"priority": "invalid"}])
def test_database_constraints(setup, issue, db_session, changes):
    values = {"project_id": setup["project_id"], "created_by_id": setup["actors"]["member"]["id"], "number": 2, "title": "Constraint", "issue_type": "task", "status": "backlog", "priority": "medium", "assignee_id": None, "sprint_id": None} | changes
    with pytest.raises(IntegrityError):
        db_session.execute(text("INSERT INTO issues (project_id, created_by_id, number, title, issue_type, status, priority, assignee_id, sprint_id) VALUES (:project_id, :created_by_id, :number, :title, :issue_type, :status, :priority, :assignee_id, :sprint_id)"), values)
        db_session.commit()
    db_session.rollback()


@pytest.mark.parametrize("kind,priority", list(product(IssueType, IssuePriority)))
def test_model_enum_persistence(setup, db_session, sprints, kind, priority):
    actor = setup["actors"]["member"]["id"]
    row = Issue(project_id=setup["project_id"], reporter_id=actor, assignee_id=actor, sprint_id=sprints[0], number=1, title="Model", issue_type=kind, priority=priority)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    assert row.issue_type is kind and row.priority is priority and row.status is IssueStatus.BACKLOG
    assert row.created_at and row.updated_at and row.assignee.id == actor and row.sprint.id == sprints[0]
    assert tuple(db_session.execute(text("SELECT issue_type, priority FROM issues WHERE id=:id"), {"id": row.id}).one()) == (kind.value, priority.value)


def test_creation_rolls_back_on_failure(setup, db_session, monkeypatch):
    def fail():
        raise IntegrityError("insert", {}, Exception("private database details"))
    monkeypatch.setattr(db_session, "commit", fail)
    with pytest.raises(service.IssueError) as error:
        service.create_issue(db_session, setup["project_id"], setup["actors"]["member"]["id"], IssueCreate(**PAYLOAD))
    assert error.value.status_code == 409 and "private" not in error.value.detail
    assert list(db_session.scalars(select(Issue))) == []


def test_number_conflict_retries(client, setup, issue, db_session, monkeypatch):
    original = service.next_number
    calls = []
    def collide_once(db, project_id):
        calls.append(project_id)
        return 1 if len(calls) == 1 else original(db, project_id)
    monkeypatch.setattr(service, "next_number", collide_once)
    result = service.create_issue(db_session, setup["project_id"], setup["actors"]["member"]["id"], IssueCreate(**PAYLOAD))
    assert result.number == 2 and len(calls) == 2


def test_no_n_plus_one(client, setup, db_session):
    headers = setup["actors"]["member"]["headers"]
    counts = []
    def record(*args):
        counts.append(args[2])
    for _ in range(3):
        client.post(setup["path"], headers=headers, json=PAYLOAD)
    event.listen(db_session.bind, "before_cursor_execute", record)
    try:
        assert len(client.get(setup["path"], headers=headers).json()) == 3
        initial = len(counts)
        client.post(setup["path"], headers=headers, json=PAYLOAD)
        counts.clear()
        assert len(client.get(setup["path"], headers=headers).json()) == 4
        assert len(counts) == initial
    finally:
        event.remove(db_session.bind, "before_cursor_execute", record)


def test_inactive_project_and_sprint_status_do_not_change_issue(client, setup, sprints, db_session):
    db_session.get(Project, setup["project_id"]).is_active = False
    db_session.commit()
    headers = setup["actors"]["manager"]["headers"]
    created = client.post(setup["path"], headers=headers, json=PAYLOAD | {"sprint_id": sprints[0], "status": "in_review"})
    assert created.status_code == 201
    assert client.patch(f"/api/v1/sprints/{sprints[0]}", headers=headers, json={"status": "cancelled"}).status_code == 200
    path = f"/api/v1/issues/{created.json()['id']}"
    assert client.get(path, headers=headers).json()["status"] == "in_review"
    assert client.patch(path, headers=headers, json={"title": "Still editable"}).status_code == 200


@pytest.mark.parametrize("target_role", ["member", "manager"])
def test_assigned_membership_removal_requires_unassignment(client, setup, db_session, target_role):
    project_id = setup["project_id"]
    target_id = setup["actors"]["member"]["id"]
    headers = setup["actors"]["owner"]["headers"]
    member_path = f"/api/v1/projects/{project_id}/members/{target_id}"
    if target_role == "manager":
        assert client.patch(member_path, headers=headers, json={"role": "manager"}).status_code == 200
    created = client.post(setup["path"], headers=setup["actors"]["member"]["headers"],
                          json=PAYLOAD | {"assignee_id": target_id})
    assert created.status_code == 201
    issue_id = created.json()["id"]
    issue_path = f"/api/v1/issues/{issue_id}"

    response = client.delete(member_path, headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "Unassign issues before removing this project member"
    db_session.expire_all()
    assert db_session.scalar(select(ProjectMember.id).where(
        ProjectMember.project_id == project_id, ProjectMember.user_id == target_id)) is not None
    assert db_session.get(Issue, issue_id).assignee_id == target_id

    assert client.patch(issue_path, headers=headers, json={"assignee_id": None}).status_code == 200
    assert client.delete(member_path, headers=headers).status_code == 204
    db_session.expire_all()
    assert db_session.scalar(select(ProjectMember.id).where(
        ProjectMember.project_id == project_id, ProjectMember.user_id == target_id)) is None
    row = db_session.get(Issue, issue_id)
    assert row.assignee_id is None and row.reporter_id == target_id
    # Neither creation nor updates can reassign a removed member.
    assert client.patch(issue_path, headers=headers, json={"assignee_id": target_id}).status_code == 400
    assert client.post(setup["path"], headers=headers, json=PAYLOAD | {"assignee_id": target_id}).status_code == 400
    assert client.get(issue_path, headers=headers).json()["assignee_id"] is None


def test_removal_ignores_other_members_and_other_project_assignments(client, setup, db_session):
    headers = setup["actors"]["owner"]["headers"]
    target_id = setup["actors"]["member"]["id"]
    manager_id = setup["actors"]["manager"]["id"]
    db_session.add(ProjectMember(project_id=setup["other_id"], user_id=target_id, role=ProjectRole.MEMBER))
    db_session.commit()
    local = client.post(setup["path"], headers=headers, json=PAYLOAD | {"assignee_id": manager_id})
    other = client.post(f"/api/v1/projects/{setup['other_id']}/issues", headers=headers,
                        json=PAYLOAD | {"assignee_id": target_id})
    assert local.status_code == other.status_code == 201
    assert client.delete(f"/api/v1/projects/{setup['project_id']}/members/{target_id}", headers=headers).status_code == 204
    db_session.expire_all()
    assert db_session.get(Issue, local.json()["id"]).assignee_id == manager_id
    assert db_session.get(Issue, other.json()["id"]).assignee_id == target_id
    assert db_session.scalar(select(ProjectMember.id).where(
        ProjectMember.project_id == setup["other_id"], ProjectMember.user_id == target_id)) is not None


def test_unassignment_does_not_bypass_last_manager_rule(client, setup):
    headers = setup["actors"]["owner"]["headers"]
    manager_id = setup["actors"]["manager"]["id"]
    created = client.post(setup["path"], headers=headers, json=PAYLOAD | {"assignee_id": manager_id})
    assert created.status_code == 201
    assert client.patch(f"/api/v1/issues/{created.json()['id']}", headers=headers,
                        json={"assignee_id": None}).status_code == 200
    response = client.delete(f"/api/v1/projects/{setup['project_id']}/members/{manager_id}", headers=headers)
    assert response.status_code == 400
    assert "at least one manager" in response.json()["detail"]
