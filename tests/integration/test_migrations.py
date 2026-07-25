from alembic.config import Config
from sqlalchemy import inspect

from alembic import command
from evidenceforge.db.session import create_engine_for_url
from evidenceforge.settings import get_settings


def test_initial_migration_upgrade_check_and_downgrade(
    tmp_path,
    monkeypatch,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'migration.sqlite'}"
    monkeypatch.setenv("EVIDENCEFORGE_DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        config = Config("alembic.ini")

        command.upgrade(config, "head")
        engine = create_engine_for_url(database_url)
        tables = set(inspect(engine).get_table_names())
        assert {
            "alembic_version",
            "briefs",
            "claims",
            "qa_reports",
            "revision_changes",
        } <= tables

        command.check(config)
        command.downgrade(config, "base")
        remaining = set(inspect(engine).get_table_names())
        assert not {"briefs", "claims", "qa_reports", "revision_changes"} & remaining
    finally:
        get_settings.cache_clear()
