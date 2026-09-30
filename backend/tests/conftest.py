import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.models import User  # noqa: F401 -- register metadata

from app.core.config import Settings, get_settings
from app.db.session import create_db_engine

TEST_JWT_SECRET = "test-only-fake-secret-never-use-in-production-123456"

TEST_DATABASE_URL = "postgresql://test_user:test_password@localhost:5432/test_only"


@pytest.fixture(autouse=True)
def isolated_configuration(monkeypatch, tmp_path):
    # Never read developer configuration or inherit application environment values.
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for key in ("APP_NAME", "ENVIRONMENT", "API_V1_PREFIX", "DATABASE_URL",
                "JWT_SECRET_KEY", "JWT_ALGORITHM", "ACCESS_TOKEN_EXPIRE_MINUTES"):
        monkeypatch.delenv(key, raising=False)
        monkeypatch.delenv(key.lower(), raising=False)
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings():
    return Settings(database_url=TEST_DATABASE_URL, environment="test", jwt_secret_key=TEST_JWT_SECRET)


@pytest.fixture
def client(monkeypatch, settings, auth_engine):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    from app.main import create_app
    application = create_app(settings)
    def test_db():
        with Session(auth_engine) as session:
            yield session
    application.dependency_overrides[get_db] = test_db
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def engine():
    engine = create_db_engine("sqlite+pysqlite:///:memory:")
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def auth_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:",
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(auth_engine):
    with Session(auth_engine) as session:
        yield session
