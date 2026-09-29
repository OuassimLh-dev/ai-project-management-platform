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
        assert set(inspect(connection).get_table_names()) == {"users", "alembic_version"}
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
        indexes = inspect(connection).get_indexes("users")
        assert any(index["name"] == "ix_users_email" and index["unique"] for index in indexes)
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        # Re-applying head must preserve the already migrated schema.
        command.upgrade(config, "head")
        command.downgrade(config, "base")
        assert "users" not in inspect(connection).get_table_names()
        command.upgrade(config, "head")
        assert "users" in inspect(connection).get_table_names()


def test_postgresql_offline_migration(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    output = StringIO()
    config = Config(str(CONFIG), output_buffer=output)
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE users" in sql
    assert "CREATE UNIQUE INDEX ix_users_email" in sql
    assert "TIMESTAMP WITH TIME ZONE" in sql
    assert "test_password" not in sql
