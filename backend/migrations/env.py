from alembic import context
from sqlalchemy.engine import Connection

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import create_db_engine
from app.models import User  # noqa: F401 -- register application metadata

config = context.config
target_metadata = Base.metadata


def run_with_connection(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    engine = create_db_engine(get_settings().database_url)
    try:
        context.configure(url=engine.url, target_metadata=target_metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
    finally:
        engine.dispose()
else:
    # Tests supply an isolated connection; CLI uses the validated application URL.
    connection = config.attributes.get("connection")
    if connection is not None:
        run_with_connection(connection)
    else:
        engine = create_db_engine(get_settings().database_url)
        try:
            with engine.connect() as connection:
                run_with_connection(connection)
        finally:
            engine.dispose()
