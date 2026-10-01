import pytest
from sqlalchemy import event, inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.ai.provider import AnalysisResult, IssueInput, ProviderError, ProviderUnavailable
from app.api.routes.ai_analysis import get_provider_factory
from app.models import AIAnalysis, Issue, IssueActivity, ProjectMember
from app.services import ai_analysis as service
from tests.test_ai_provider import INVALID_RESULTS, RESULT
from tests.test_issues import PAYLOAD, setup, password_hash, issue, sprints  # noqa: F401 -- shared fixtures


class FakeProvider:
    model_name = "fake/test-model"

    def __init__(self):
        self.calls = []
        self.result = AnalysisResult(**RESULT)
        self.error = None
        self.on_call = None

    def analyze_issue(self, issue_input):
        self.calls.append(issue_input)
        if self.on_call:
            self.on_call()
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def provider(client):
    fake = FakeProvider()
    client.app.dependency_overrides[get_provider_factory] = lambda: lambda: fake
    yield fake
    client.app.dependency_overrides.pop(get_provider_factory, None)


def base(issue):
    return f"/api/v1/issues/{issue['id']}/ai"


def snapshot(db, issue_id):
    db.expire_all()
    row = db.get(Issue, issue_id)
    fields = {column.key: getattr(row, column.key) for column in inspect(Issue).columns}
    activities = [tuple(getattr(event, column.key) for column in inspect(IssueActivity).columns)
                  for event in db.scalars(select(IssueActivity).order_by(IssueActivity.id))]
    return fields, activities


@pytest.mark.parametrize("actor,allowed", [("owner", True), ("admin", True), ("manager", True), ("member", True), ("unassigned", False), ("outsider", False)])
def test_authorization_and_success(client, setup, issue, provider, db_session, actor, allowed):
    headers = setup["actors"][actor]["headers"]
    response = client.post(base(issue) + "/analyze", headers=headers)
    assert response.status_code == (201 if allowed else 404)
    history = client.get(base(issue) + "/analyses", headers=headers)
    assert history.status_code == (200 if allowed else 404)
    if not allowed:
        assert provider.calls == [] and list(db_session.scalars(select(AIAnalysis))) == []
        return
    data = response.json()
    assert data.items() >= RESULT.items()
    assert data["issue_id"] == issue["id"] and data["requested_by_id"] == setup["actors"][actor]["id"]
    assert data["model_name"] == "fake/test-model" and data["created_at"]
    assert set(data) == {"id", "issue_id", "requested_by_id", "summary", "suggested_type", "suggested_priority", "explanation", "model_name", "created_at"}
    assert history.json() == [data]
    assert len(list(db_session.scalars(select(AIAnalysis)))) == 1
    row = db_session.get(AIAnalysis, data["id"])
    assert row.issue.id == issue["id"] and row.requested_by.id == data["requested_by_id"]
    assert provider.calls == [IssueInput(issue["title"], issue["description"])]


@pytest.mark.parametrize("method,suffix", [("POST", "/analyze"), ("GET", "/analyses")])
def test_auth_and_missing(client, setup, provider, method, suffix):
    path = "/api/v1/issues/9999/ai" + suffix
    assert client.request(method, path).status_code == 401
    assert client.request(method, path, headers=setup["actors"]["owner"]["headers"]).status_code == 404
    assert provider.calls == []


def test_advice_never_mutates_issue_or_activity(client, setup, issue, provider, db_session, sprints):
    headers = setup["actors"]["member"]["headers"]
    path = f"/api/v1/issues/{issue['id']}"
    assert client.patch(path, headers=headers, json={"issue_type": "feature", "priority": "low", "assignee_id": setup["actors"]["member"]["id"], "sprint_id": sprints[0]}).status_code == 200
    before = snapshot(db_session, issue["id"])
    response = client.post(base(issue) + "/analyze", headers=headers)
    assert response.status_code == 201
    assert response.json()["suggested_type"] != before[0]["issue_type"]
    assert response.json()["suggested_priority"] != before[0]["priority"]
    assert snapshot(db_session, issue["id"]) == before


def test_history_and_cross_issue_isolation(client, setup, issue, provider):
    owner = setup["actors"]["owner"]["headers"]
    member = setup["actors"]["member"]["headers"]
    expected = []
    for index in range(3):
        provider.result = AnalysisResult(**(RESULT | {"summary": f"Analysis {index}"}))
        expected.append(client.post(base(issue) + "/analyze", headers=owner).json())
    other = client.post(f"/api/v1/projects/{setup['other_id']}/issues", headers=owner, json=PAYLOAD).json()
    other_analysis = client.post(base(other) + "/analyze", headers=owner).json()
    assert client.get(base(issue) + "/analyses", headers=member).json() == expected
    assert len({row["id"] for row in expected}) == 3
    assert [(row["created_at"], row["id"]) for row in expected] == sorted((row["created_at"], row["id"]) for row in expected)
    assert client.get(base(other) + "/analyses", headers=owner).json() == [other_analysis]
    assert client.get(base(other) + "/analyses", headers=member).status_code == 404
    calls = len(provider.calls)
    assert client.post(base(other) + "/analyze", headers=member).status_code == 404
    assert len(provider.calls) == calls


@pytest.mark.parametrize("invalid", INVALID_RESULTS)
def test_malformed_result_has_no_side_effects(client, setup, issue, provider, db_session, invalid):
    provider.result = invalid
    before = snapshot(db_session, issue["id"])
    response = client.post(base(issue) + "/analyze", headers=setup["actors"]["member"]["headers"])
    assert response.status_code == 502 and response.json()["detail"] == "AI provider returned an invalid response"
    assert list(db_session.scalars(select(AIAnalysis))) == []
    assert snapshot(db_session, issue["id"]) == before


@pytest.mark.parametrize("error,expected", [(ProviderUnavailable(), 503), (ProviderError("secret-upstream-error"), 502)])
def test_provider_failure(client, setup, issue, provider, db_session, error, expected):
    provider.error = error
    before = snapshot(db_session, issue["id"])
    response = client.post(base(issue) + "/analyze", headers=setup["actors"]["member"]["headers"])
    assert response.status_code == expected and "secret" not in response.text
    assert list(db_session.scalars(select(AIAnalysis))) == []
    assert snapshot(db_session, issue["id"]) == before


def test_unconfigured_ai_preserves_normal_endpoints(client, setup, issue, db_session):
    headers = setup["actors"]["member"]["headers"]
    before = snapshot(db_session, issue["id"])
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.get(f"/api/v1/issues/{issue['id']}", headers=headers).status_code == 200
    assert client.get(base(issue) + "/analyses", headers=headers).json() == []
    assert client.post(base(issue) + "/analyze", headers=headers).status_code == 503
    assert client.post(base(issue) + "/analyze", headers=setup["actors"]["outsider"]["headers"]).status_code == 404
    assert snapshot(db_session, issue["id"]) == before
    assert list(db_session.scalars(select(AIAnalysis))) == []


@pytest.mark.parametrize("field", ["id", "issue_id", "project_id", "requested_by_id", "actor_id", "summary", "suggested_type", "suggested_priority", "explanation", "provider", "model_name", "created_at"])
def test_server_owned_fields(client, setup, issue, provider, field):
    response = client.post(base(issue) + "/analyze", headers=setup["actors"]["member"]["headers"], json={field: "forged"})
    assert response.status_code == 422 and provider.calls == []


@pytest.mark.parametrize("method,suffix", [("PATCH", "/analyses"), ("DELETE", "/analyses"), ("POST", "/analyses"), ("PATCH", "/analyses/1"), ("DELETE", "/analyses/1")])
def test_history_has_no_mutation_routes(client, setup, issue, method, suffix):
    response = client.request(method, base(issue) + suffix, headers=setup["actors"]["member"]["headers"])
    assert response.status_code in (404, 405)


def test_no_transaction_during_provider_and_database_failure_rolls_back(setup, issue, db_session):
    provider = FakeProvider()
    provider.on_call = lambda: assert_no_transaction(db_session)
    before = snapshot(db_session, issue["id"])
    def fail(mapper, connection, target):
        raise IntegrityError("insert", {}, Exception("private-db-detail"))
    event.listen(AIAnalysis, "after_insert", fail)
    try:
        with pytest.raises(service.AIAnalysisError) as error:
            service.analyze_issue(db_session, issue["id"], setup["actors"]["member"]["id"], lambda: provider)
        assert error.value.status_code == 503 and "private" not in str(error.value)
    finally:
        event.remove(AIAnalysis, "after_insert", fail)
    assert len(provider.calls) == 1
    assert list(db_session.scalars(select(AIAnalysis))) == []
    assert snapshot(db_session, issue["id"]) == before


def assert_no_transaction(db):
    assert not db.in_transaction()


def test_access_rechecked_after_provider(setup, issue, db_session):
    provider = FakeProvider()
    actor_id = setup["actors"]["member"]["id"]
    def revoke():
        assert_no_transaction(db_session)
        member = db_session.scalar(select(ProjectMember).where(ProjectMember.project_id == setup["project_id"], ProjectMember.user_id == actor_id))
        db_session.delete(member)
        db_session.commit()
    provider.on_call = revoke
    from app.services.project_authorization import ProjectError
    with pytest.raises(ProjectError) as error:
        service.analyze_issue(db_session, issue["id"], actor_id, lambda: provider)
    assert error.value.status_code == 404
    assert list(db_session.scalars(select(AIAnalysis))) == []


def test_programming_bug_is_not_provider_error(setup, issue, db_session):
    provider = FakeProvider()
    provider.error = RuntimeError("Bug in adapter")
    with pytest.raises(RuntimeError, match="Bug in adapter"):
        service.analyze_issue(db_session, issue["id"], setup["actors"]["member"]["id"], lambda: provider)


@pytest.mark.parametrize("changes", [{"issue_id": 9999}, {"requested_by_id": 9999}, {"summary": " "}, {"summary": None},
    {"summary": "x" * 2001}, {"explanation": " "}, {"explanation": "x" * 1001}, {"model_name": " "}, {"model_name": None},
    {"model_name": "x" * 201}, {"suggested_type": "invalid"}, {"suggested_priority": "invalid"}])
def test_database_constraints(setup, issue, db_session, changes):
    values = RESULT | {"issue_id": issue["id"], "requested_by_id": setup["actors"]["member"]["id"], "model_name": "fake/test"} | changes
    with pytest.raises(IntegrityError):
        db_session.execute(text("INSERT INTO ai_analyses (issue_id, requested_by_id, summary, suggested_type, suggested_priority, explanation, model_name) VALUES (:issue_id, :requested_by_id, :summary, :suggested_type, :suggested_priority, :explanation, :model_name)"), values)
        db_session.commit()
    db_session.rollback()


@pytest.mark.parametrize("failure", ["timeout", "network", "malformed"])
def test_real_adapter_failures_at_api_boundary(client, setup, issue, db_session, failure):
    import httpx
    from pydantic import SecretStr
    from app.ai.openai_provider import OpenAIProvider
    def respond(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("upstream-secret", request=request)
        if failure == "network":
            raise httpx.ConnectError("upstream-secret", request=request)
        return httpx.Response(200, text="upstream-secret")
    adapter = OpenAIProvider("test-model", SecretStr("fake-secret"), 5, transport=httpx.MockTransport(respond))
    client.app.dependency_overrides[get_provider_factory] = lambda: lambda: adapter
    before = snapshot(db_session, issue["id"])
    response = client.post(base(issue) + "/analyze", headers=setup["actors"]["member"]["headers"])
    assert response.status_code == (502 if failure == "malformed" else 503)
    assert "secret" not in response.text
    assert list(db_session.scalars(select(AIAnalysis))) == []
    assert snapshot(db_session, issue["id"]) == before
