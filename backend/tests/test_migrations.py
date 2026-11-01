"""The Alembic migrations must build exactly the schema the models describe."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.db import Base, make_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config(url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logger"] = False
    return config


def test_upgrade_head_matches_models(tmp_path):
    url = f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}"
    command.upgrade(alembic_config(url), "head")

    engine = make_engine(url)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        differences = compare_metadata(context, Base.metadata)
    engine.dispose()
    assert differences == []


def test_downgrade_to_base_removes_everything(tmp_path):
    url = f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}"
    config = alembic_config(url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = make_engine(url)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()
    assert tables <= {"alembic_version"}
