import pytest
from pydantic import ValidationError

from app.core.config import Settings
from tests.conftest import TEST_DATABASE_URL, TEST_JWT_SECRET


def test_cors_disabled_by_default(client, settings):
    assert settings.cors_allowed_origins == []
    response = client.get('/api/v1/health', headers={'Origin': 'https://untrusted.example'})
    assert response.status_code == 200
    assert 'access-control-allow-origin' not in response.headers


def test_explicit_origin_and_bearer_preflight(client, settings):
    from app.main import create_app
    from fastapi.testclient import TestClient
    settings.cors_allowed_origins = ['http://localhost:5173']
    with TestClient(create_app(settings)) as browser:
        allowed = browser.options('/api/v1/issues/1', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'PATCH', 'Access-Control-Request-Headers': 'Authorization,Content-Type'})
        assert allowed.status_code == 200
        assert allowed.headers['access-control-allow-origin'] == 'http://localhost:5173'
        assert 'access-control-allow-credentials' not in allowed.headers
        denied = browser.options('/api/v1/issues/1', headers={'Origin': 'https://untrusted.example', 'Access-Control-Request-Method': 'PATCH'})
        assert denied.status_code == 400
        assert 'access-control-allow-origin' not in denied.headers


@pytest.mark.parametrize('origin', ['*', 'https://example.com/path', 'ftp://example.com', 'https://user:pass@example.com', 'https://example.com?x=1', 'not-an-origin'])
def test_invalid_cors_origin(origin):
    with pytest.raises(ValidationError):
        Settings(database_url=TEST_DATABASE_URL, jwt_secret_key=TEST_JWT_SECRET, cors_allowed_origins=[origin])


def test_cors_environment(monkeypatch):
    monkeypatch.setenv('CORS_ALLOWED_ORIGINS', '["http://localhost:5173"]')
    assert Settings(database_url=TEST_DATABASE_URL, jwt_secret_key=TEST_JWT_SECRET).cors_allowed_origins == ['http://localhost:5173']
