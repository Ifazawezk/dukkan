from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.types import TypeDecorator

from app import models  # noqa: F401  (registers every table on Base.metadata)
from app.config import get_settings
from app.db import Base, make_engine

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def database_url() -> str:
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def render_item(type_, obj, autogen_context):
    # Write our custom column types as their plain storage type so migration
    # files never import application code.
    if type_ == "type" and isinstance(obj, TypeDecorator):
        return f"sa.{obj.impl!r}"
    return False


def configure(**kwargs) -> None:
    context.configure(
        target_metadata=target_metadata,
        render_as_batch=True,  # needed for ALTER TABLE on SQLite
        render_item=render_item,
        compare_type=True,
        **kwargs,
    )


def run_migrations_offline() -> None:
    configure(url=database_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = make_engine(database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
