import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError

from app.models import Issue, IssueActivity, IssueComment
from app.schemas.issue import IssueCreate, IssueUpdate
from app.services import issue as service
from tests.test_issues import PAYLOAD, setup, password_hash, issue, sprints  # noqa: F401 -- shared scenario fixtures


def comment_path(issue):
    return f"/api/v1/issues/{issue['id']}/comments"


def history(client, issue, headers):
    response = client.get(f"/api/v1/issues/{issue['id']}/activity", headers=headers)
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize("actor,allowed", [("owner", True), ("admin", True), ("manager", True), ("member", True), ("unassigned", False), ("outsider", False)])
def test_collaboration_access(client, setup, issue, actor, allowed):
    headers = setup["actors"][actor]["headers"]
    path = comment_path(issue)
    response = client.post(path, headers=headers, json={"body": " Discussion "})
    assert response.status_code == (201 if allowed else 404)
    assert client.get(path, headers=headers).status_code == (200 if allowed else 404)
    assert client.get(f"/api/v1/issues/{issue['id']}/activity", headers=headers).status_code == (200 if allowed else 404)
    if allowed:
        data = response.json()
        assert data["body"] == "Discussion" and data["author_id"] == setup["actors"][actor]["id"]
        assert data["issue_id"] == issue["id"] and data["created_at"] and data["updated_at"]
        assert set(data) == {"id", "issue_id", "author_id", "body", "created_at", "updated_at"}


@pytest.mark.parametrize("method,suffix,body", [("POST", "/comments", {"body": "Test"}), ("GET", "/comments", None), ("GET", "/activity", None), ("PATCH", "/comments/1", {"body": "Test"}), ("DELETE", "/comments/1", None)])
def test_auth_and_missing_issue(client, setup, method, suffix, body):
    path = "/api/v1/issues/9999" + suffix
    assert client.request(method, path, json=body).status_code == 401
    assert client.request(method, path, headers=setup["actors"]["owner"]["headers"], json=body).status_code == 404


@pytest.mark.parametrize("payload", [{"body": " "}, {"body": None}, {"body": "x" * 10001}, {}, {"body": "Valid", "author_id": 1}, {"body": "Valid", "issue_id": 1}, {"body": "Valid", "id": 1}, {"body": "Valid", "created_at": "2026-01-01"}, {"body": "Valid", "updated_at": "2026-01-01"}])
def test_comment_validation(client, setup, issue, payload):
    headers = setup["actors"]["member"]["headers"]
    path = comment_path(issue)
    created = client.post(path, headers=headers, json={"body": "Original"}).json()
    assert client.post(path, headers=headers, json=payload).status_code == 422
    assert client.patch(f"{path}/{created['id']}", headers=headers, json=payload).status_code == 422
    assert client.get(path, headers=headers).json()[0]["body"] == "Original"


def test_author_edit_delete_and_no_comment_activity(client, setup, issue, db_session):
    headers = setup["actors"]["member"]["headers"]
    path = comment_path(issue)
    created = client.post(path, headers=headers, json={"body": "Original"}).json()
    row = db_session.get(IssueComment, created["id"])
    assert row.issue.id == issue["id"] and row.author.id == created["author_id"]
    response = client.patch(f"{path}/{created['id']}", headers=headers, json={"body": " Revised "})
    assert response.status_code == 200 and response.json()["body"] == "Revised"
    response = client.delete(f"{path}/{created['id']}", headers=headers)
    assert response.status_code == 204 and response.content == b""
    assert client.get(path, headers=headers).json() == []
    assert client.get(f"/api/v1/issues/{issue['id']}", headers=headers).status_code == 200
    assert len(history(client, issue, headers)) == 1


@pytest.mark.parametrize("actor", ["owner", "admin", "manager"])
def test_no_moderation_override(client, setup, issue, actor):
    path = comment_path(issue)
    created = client.post(path, headers=setup["actors"]["member"]["headers"], json={"body": "Private authorship"}).json()
    headers = setup["actors"][actor]["headers"]
    assert client.patch(f"{path}/{created['id']}", headers=headers, json={"body": "Override"}).status_code == 403
    assert client.delete(f"{path}/{created['id']}", headers=headers).status_code == 403
    # An ordinary member also cannot rewrite an administrator's comment.
    other = client.post(path, headers=headers, json={"body": "Other author"}).json()
    assert client.patch(f"{path}/{other['id']}", headers=setup["actors"]["member"]["headers"], json={"body": "Override"}).status_code == 403


def test_isolation_order_and_membership_history(client, setup, issue):
    owner = setup["actors"]["owner"]["headers"]
    member = setup["actors"]["member"]["headers"]
    path = comment_path(issue)
    first = client.post(path, headers=member, json={"body": "First"}).json()
    second = client.post(path, headers=member, json={"body": "Second"}).json()
    other = client.post(f"/api/v1/projects/{setup['other_id']}/issues", headers=owner, json=PAYLOAD).json()
    other_path = comment_path(other)
    client.post(other_path, headers=owner, json={"body": "Other"})
    assert [row["id"] for row in client.get(path, headers=owner).json()] == [first["id"], second["id"]]
    assert client.patch(f"{other_path}/{first['id']}", headers=owner, json={"body": "Wrong issue"}).status_code == 404
    assert client.delete(f"{other_path}/{first['id']}", headers=owner).status_code == 404
    assert client.get(other_path, headers=member).status_code == 404
    assert client.get(f"/api/v1/issues/{other['id']}/activity", headers=member).status_code == 404
    assert client.delete(f"/api/v1/projects/{setup['project_id']}/members/{setup['actors']['member']['id']}", headers=owner).status_code == 204
    assert client.patch(f"{path}/{first['id']}", headers=member, json={"body": "Lost access"}).status_code == 404
    assert client.delete(f"{path}/{first['id']}", headers=member).status_code == 404
    assert client.get(path, headers=owner).json()[0]["author_id"] == setup["actors"]["member"]["id"]
    events = history(client, issue, owner)
    assert events[0]["actor_id"] == setup["actors"]["member"]["id"]
    assert all(row["issue_id"] == issue["id"] for row in events)


def test_creation_activity(client, setup, issue, db_session):
    events = history(client, issue, setup["actors"]["owner"]["headers"])
    assert len(events) == 1
    data = events[0]
    assert data["action"] == "created" and data["actor_id"] == issue["reporter_id"]
    assert data["issue_id"] == issue["id"] and data["created_at"]
    assert data["field_name"] is data["old_value"] is data["new_value"] is None
    assert set(data) == {"id", "issue_id", "actor_id", "action", "field_name", "old_value", "new_value", "created_at"}
    row = db_session.get(IssueActivity, data["id"])
    assert row.issue.id == issue["id"] and row.actor.id == issue["reporter_id"]


@pytest.mark.parametrize("field,value,old", [("title", "New title", "Fix login"), ("description", "New description", "Reproduction steps"), ("issue_type", "task", "bug"), ("priority", "high", "medium"), ("status", "in_progress", "backlog"), ("assignee_id", "member", None), ("sprint_id", "sprint", None)])
def test_field_activity(client, setup, issue, sprints, field, value, old):
    headers = setup["actors"]["manager"]["headers"]
    if value == "member":
        value = setup["actors"]["member"]["id"]
    elif value == "sprint":
        value = sprints[0]
    path = f"/api/v1/issues/{issue['id']}"
    assert client.patch(path, headers=headers, json={field: value}).status_code == 200
    events = history(client, issue, headers)
    assert len(events) == 2
    changed = events[-1]
    assert (changed["action"], changed["field_name"], changed["old_value"], changed["new_value"]) == ("field_changed", field, old, str(value))
    assert changed["actor_id"] == setup["actors"]["manager"]["id"]
    assert client.patch(path, headers=headers, json={field: value}).status_code == 200
    assert client.patch(path, headers=headers, json={}).status_code == 200
    assert history(client, issue, headers) == events
    if field in ("description", "assignee_id", "sprint_id"):
        assert client.patch(path, headers=headers, json={field: None}).status_code == 200
        cleared = history(client, issue, headers)[-1]
        assert cleared["old_value"] == str(value) and cleared["new_value"] is None
        assert client.patch(path, headers=headers, json={field: value}).status_code == 200
        assert history(client, issue, headers)[-1]["old_value"] is None


def test_multiple_changes_and_failure_adds_nothing(client, setup, issue):
    headers = setup["actors"]["member"]["headers"]
    path = f"/api/v1/issues/{issue['id']}"
    assert client.patch(path, headers=headers, json={"title": "Changed", "priority": "critical", "status": "done"}).status_code == 200
    events = history(client, issue, headers)
    assert len(events) == 4
    assert {row["field_name"] for row in events[1:]} == {"title", "priority", "status"}
    assert [(row["created_at"], row["id"]) for row in events] == sorted((row["created_at"], row["id"]) for row in events)
    assert client.patch(path, headers=headers, json={"title": "Invalid", "assignee_id": 9999}).status_code == 404
    assert client.patch(path, headers=headers, json={"actor_id": 1}).status_code == 422
    assert history(client, issue, headers) == events


@pytest.mark.parametrize("operation", ["create", "update"])
def test_activity_failure_rolls_back_issue(setup, db_session, operation):
    actor_id = setup["actors"]["member"]["id"]
    existing = service.create_issue(db_session, setup["project_id"], actor_id, IssueCreate(**PAYLOAD))
    original_id = existing.id
    before = list(db_session.scalars(select(IssueActivity.id)))
    def fail_after_insert(mapper, connection, target):
        raise RuntimeError("Simulated activity persistence failure")
    event.listen(IssueActivity, "after_insert", fail_after_insert)
    try:
        with pytest.raises(RuntimeError, match="activity persistence failure"):
            if operation == "create":
                service.create_issue(db_session, setup["project_id"], actor_id, IssueCreate(**PAYLOAD))
            else:
                service.update_issue(db_session, original_id, actor_id, IssueUpdate(title="Must roll back", priority="high"))
    finally:
        event.remove(IssueActivity, "after_insert", fail_after_insert)
    db_session.expire_all()
    assert list(db_session.scalars(select(Issue.id))) == [original_id]
    assert db_session.get(Issue, original_id).title == "Fix login"
    assert db_session.get(Issue, original_id).priority.value == "medium"
    assert list(db_session.scalars(select(IssueActivity.id))) == before


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE"])
def test_history_has_no_mutation_routes(client, setup, issue, method):
    headers = setup["actors"]["owner"]["headers"]
    path = f"/api/v1/issues/{issue['id']}/activity"
    assert client.request(method, path, headers=headers, json={"actor_id": 1, "action": "created"}).status_code == 405
    assert client.request(method, path + "/1", headers=headers, json={}).status_code == 404


@pytest.mark.parametrize("changes", [{"issue_id": 9999}, {"author_id": 9999}, {"body": " "}, {"body": "x" * 10001}])
def test_comment_database_constraints(setup, issue, db_session, changes):
    row = IssueComment(**({"issue_id": issue["id"], "author_id": setup["actors"]["member"]["id"], "body": "Valid"} | changes))
    db_session.add(row)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


@pytest.mark.parametrize("changes", [{"issue_id": 9999}, {"actor_id": 9999}, {"action": "invalid"}, {"action": "field_changed"}, {"field_name": "password"}])
def test_activity_database_constraints(setup, issue, db_session, changes):
    row = IssueActivity(**({"issue_id": issue["id"], "actor_id": setup["actors"]["member"]["id"], "action": "created"} | changes))
    db_session.add(row)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
