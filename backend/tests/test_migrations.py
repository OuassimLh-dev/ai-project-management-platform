from io import StringIO
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from app.db.base import Base
from tests.conftest import TEST_DATABASE_URL, TEST_JWT_SECRET

CONFIG = Path(__file__).resolve().parents[1] / "alembic.ini"


def test_migration_upgrade_and_downgrade_on_disposable_sqlite(engine):
    config = Config(str(CONFIG))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        assert set(inspect(connection).get_table_names()) == {"users", "teams", "team_members", "projects", "project_members", "sprints", "issues", "issue_comments", "issue_activity", "ai_analyses", "alembic_version"}
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0007"
        indexes = inspect(connection).get_indexes("users")
        assert any(index["name"] == "ix_users_email" and index["unique"] for index in indexes)
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        connection.execute(text("INSERT INTO users (first_name, last_name, email, hashed_password) "
                                "VALUES ('Migration', 'Test', 'migration@example.com', 'test-only-hash')"))
        # Re-applying head must preserve the already migrated schema.
        command.upgrade(config, "head")
        command.downgrade(config, "0006")
        assert set(inspect(connection).get_table_names()) == {"users", "teams", "team_members", "projects", "project_members", "sprints", "issues", "issue_comments", "issue_activity", "alembic_version"}
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0006"
        command.downgrade(config, "0005")
        assert set(inspect(connection).get_table_names()) == {"users", "teams", "team_members", "projects", "project_members", "sprints", "issues", "alembic_version"}
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0005"
        command.downgrade(config, "0004")
        assert set(inspect(connection).get_table_names()) == {"users", "teams", "team_members", "projects", "project_members", "sprints", "alembic_version"}
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0004"
        command.downgrade(config, "0003")
        assert set(inspect(connection).get_table_names()) == {"users", "teams", "team_members", "projects", "project_members", "alembic_version"}
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0003"
        command.downgrade(config, "0002")
        assert set(inspect(connection).get_table_names()) == {"users", "teams", "team_members", "alembic_version"}
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0002"
        command.downgrade(config, "0001")
        assert set(inspect(connection).get_table_names()) == {"users", "alembic_version"}
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
        assert connection.scalar(text("SELECT email FROM users")) == "migration@example.com"
        command.downgrade(config, "base")
        assert set(inspect(connection).get_table_names()) == {"alembic_version"}
        command.upgrade(config, "head")
        assert "users" in inspect(connection).get_table_names()


def test_postgresql_offline_migration(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    output = StringIO()
    config = Config(str(CONFIG), output_buffer=output)
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE ai_analyses" in sql
    assert "CREATE TABLE issue_comments" in sql
    assert "CREATE TABLE issue_activity" in sql
    assert "CREATE TABLE issues" in sql
    assert "CREATE TABLE sprints" in sql
    assert "CREATE TABLE projects" in sql
    assert "CREATE TABLE project_members" in sql
    assert "CREATE TABLE users" in sql
    assert "CREATE TABLE teams" in sql
    assert "CREATE TABLE team_members" in sql
    assert "CREATE UNIQUE INDEX uq_team_members_owner" in sql
    assert "CREATE UNIQUE INDEX ix_users_email" in sql
    assert "TIMESTAMP WITH TIME ZONE" in sql
    assert "test_password" not in sql
