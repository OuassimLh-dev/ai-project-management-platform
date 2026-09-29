import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker

from app.db import session as database


def test_sqlite_session_executes_statement(engine):
    with sessionmaker(bind=engine)() as session:
        assert session.scalar(text("SELECT 1")) == 1
    # Building an engine/session never creates application tables automatically.
    assert inspect(engine).get_table_names() == []


@pytest.mark.parametrize("scheme", ["postgresql", "postgresql+psycopg"])
def test_postgresql_engine_normalization(scheme):
    engine = database.create_db_engine(f"{scheme}://test:p%40ss@localhost/test_db")
    try:
        assert engine.url.drivername == "postgresql+psycopg"
        assert engine.url.password == "p@ss"
        assert engine.url.database == "test_db"
    finally:
        engine.dispose()


@pytest.mark.parametrize("failure", [False, True])
def test_dependency_releases_connection_and_rolls_back(engine, settings, monkeypatch, failure):
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE lifecycle_check (value INTEGER)"))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(database, "get_session_factory", lambda url: factory)
    dependency = database.get_db(settings)
    session = next(dependency)
    session.execute(text("INSERT INTO lifecycle_check VALUES (1)"))
    connection = session.connection()
    if failure:
        with pytest.raises(RuntimeError, match="request failed"):
            dependency.throw(RuntimeError("request failed"))
    else:
        with pytest.raises(StopIteration):
            next(dependency)
    assert connection.closed
    with engine.connect() as check:
        assert check.scalar(text("SELECT COUNT(*) FROM lifecycle_check")) == 0


def test_session_factory_reuses_engine(engine, monkeypatch):
    calls = []
    def create(url):
        calls.append(url)
        return engine
    database.get_session_factory.cache_clear()
    monkeypatch.setattr(database, "create_db_engine", create)
    try:
        factory = database.get_session_factory("test-only")
        assert factory is database.get_session_factory("test-only")
        assert calls == ["test-only"]
        with factory() as session:
            assert session.scalar(text("SELECT 1")) == 1
    finally:
        database.get_session_factory.cache_clear()
