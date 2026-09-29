from fastapi.testclient import TestClient
from sqlalchemy import Engine


def test_health_without_database_connection(client, monkeypatch):
    def unexpected_connection(*args, **kwargs):
        raise AssertionError("Health must not connect to a database")
    monkeypatch.setattr(Engine, "connect", unexpected_connection)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert client.app.title == "AI Project Management Platform API"


def test_custom_prefix_and_title(client, settings):
    from app.main import create_app
    settings.api_v1_prefix = "/custom/v1"
    settings.app_name = "Test Platform"
    with TestClient(create_app(settings)) as custom_client:
        assert custom_client.get("/custom/v1/health").json() == {"status": "ok"}
        assert custom_client.get("/api/v1/health").status_code == 404
        assert custom_client.app.title == "Test Platform API"
