from pathlib import Path

import pytest
from click import unstyle
from sqlalchemy import select
from typer.testing import CliRunner

from evidenceforge.cli.app import app
from evidenceforge.db.base import Base
from evidenceforge.db.models import ExportedArtifactRow
from evidenceforge.db.repository import BriefNotFoundError, BriefRepository
from evidenceforge.db.session import create_engine_for_url, create_session_factory
from evidenceforge.llm import MockLLMProvider
from evidenceforge.models import PICO
from evidenceforge.pipelines.coded_brief import load_pico_prompt
from evidenceforge.settings import get_settings
from tests.fixtures.persistence import persistence_input


def test_version_command() -> None:
    result = CliRunner().invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0"


async def test_mock_provider_rejects_unrelated_questions() -> None:
    provider = MockLLMProvider()

    with pytest.raises(ValueError, match="supports only"):
        await provider.generate_structured(
            system_prompt="extract",
            user_prompt="Does aspirin prevent stroke?",
            response_model=PICO,
        )


def test_versioned_pico_prompt_is_loadable() -> None:
    assert "Do not invent" in load_pico_prompt()


def test_cli_requires_no_phi_confirmation() -> None:
    result = CliRunner().invoke(
        app,
        ["brief", "create", "--question", "Does aspirin prevent stroke in adults?"],
    )

    assert result.exit_code != 0
    assert "--confirm-no-phi is required" in _plain_output(result.output)


def test_cli_does_not_overwrite_without_force(tmp_path: Path) -> None:
    output = tmp_path / "brief.md"
    output.write_text("preserve me")

    result = CliRunner().invoke(
        app,
        [
            "brief",
            "create",
            "--question",
            "Does aspirin prevent stroke in adults?",
            "--confirm-no-phi",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code != 0
    assert "pass --force" in _plain_output(result.output)
    assert output.read_text() == "preserve me"


def test_cli_formats_pipeline_validation_errors_without_traceback() -> None:
    result = CliRunner().invoke(
        app,
        [
            "brief",
            "create",
            "--question",
            "too short",
            "--confirm-no-phi",
        ],
    )
    output = _plain_output(result.output)

    assert result.exit_code != 0
    assert "at least 10 characters" in output
    assert "Traceback" not in output


async def test_cli_exports_persisted_reviewed_markdown(tmp_path: Path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli.sqlite'}"
    engine = create_engine_for_url(database_url)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    repository = BriefRepository(session_factory)
    stored = repository.save(await persistence_input())
    output = tmp_path / "reviewed-brief.md"
    monkeypatch.setenv("EVIDENCEFORGE_DATABASE_URL", database_url)
    get_settings.cache_clear()

    try:
        result = CliRunner().invoke(
            app,
            [
                "brief",
                "export",
                "--brief-id",
                stored.brief_id,
                "--format",
                "markdown",
                "--output",
                str(output),
            ],
        )
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0
    assert "Wrote markdown export" in result.stdout
    assert output.read_text().startswith("---\nbrief_id:")
    assert "## Claim-level QA" in output.read_text()
    with session_factory() as session:
        artifact = session.scalar(select(ExportedArtifactRow))
        assert artifact is not None
        assert artifact.storage_reference == "local-cli-output"


def test_cli_export_rejects_unknown_brief_without_traceback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'missing-cli.sqlite'}"
    engine = create_engine_for_url(database_url)
    Base.metadata.create_all(engine)
    monkeypatch.setenv("EVIDENCEFORGE_DATABASE_URL", database_url)
    get_settings.cache_clear()

    try:
        result = CliRunner().invoke(
            app,
            [
                "brief",
                "export",
                "--brief-id",
                "00000000-0000-0000-0000-000000000000",
                "--format",
                "json",
                "--output",
                str(tmp_path / "missing.json"),
            ],
        )
    finally:
        get_settings.cache_clear()

    assert result.exit_code != 0
    assert "Brief does not exist" in _plain_output(result.output)
    assert "Traceback" not in result.output


async def test_cli_export_removes_file_when_metadata_recording_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'metadata-failure.sqlite'}"
    engine = create_engine_for_url(database_url)
    Base.metadata.create_all(engine)
    repository = BriefRepository(create_session_factory(engine))
    stored = repository.save(await persistence_input())
    output = tmp_path / "retryable.json"
    monkeypatch.setenv("EVIDENCEFORGE_DATABASE_URL", database_url)
    get_settings.cache_clear()
    original_record_export = BriefRepository.record_export
    failure_calls = 0

    def fail_record_export(
        _repository,
        _brief_id: str,
        *,
        export_format: str,
        storage_reference: str,
    ) -> None:
        nonlocal failure_calls
        failure_calls += 1
        del export_format, storage_reference
        raise BriefNotFoundError(_brief_id)

    monkeypatch.setattr(BriefRepository, "record_export", fail_record_export)
    first = CliRunner().invoke(
        app,
        [
            "brief",
            "export",
            "--brief-id",
            stored.brief_id,
            "--format",
            "json",
            "--output",
            str(output),
        ],
    )
    assert first.exit_code != 0
    assert failure_calls == 1
    assert not output.exists()

    monkeypatch.setattr(BriefRepository, "record_export", original_record_export)
    second = CliRunner().invoke(
        app,
        [
            "brief",
            "export",
            "--brief-id",
            stored.brief_id,
            "--format",
            "json",
            "--output",
            str(output),
        ],
    )
    get_settings.cache_clear()

    assert second.exit_code == 0
    assert output.read_bytes().startswith(b"{")


async def test_cli_export_restores_forced_output_when_metadata_recording_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'restore.sqlite'}"
    engine = create_engine_for_url(database_url)
    Base.metadata.create_all(engine)
    repository = BriefRepository(create_session_factory(engine))
    stored = repository.save(await persistence_input())
    output = tmp_path / "existing.json"
    output.write_text("preserve original")
    monkeypatch.setenv("EVIDENCEFORGE_DATABASE_URL", database_url)
    get_settings.cache_clear()
    failure_calls = 0

    def fail_record_export(
        _repository,
        _brief_id: str,
        *,
        export_format: str,
        storage_reference: str,
    ) -> None:
        nonlocal failure_calls
        failure_calls += 1
        del export_format, storage_reference
        raise BriefNotFoundError(_brief_id)

    monkeypatch.setattr(BriefRepository, "record_export", fail_record_export)
    try:
        result = CliRunner().invoke(
            app,
            [
                "brief",
                "export",
                "--brief-id",
                stored.brief_id,
                "--format",
                "json",
                "--output",
                str(output),
                "--force",
            ],
        )
    finally:
        get_settings.cache_clear()

    assert result.exit_code != 0
    assert failure_calls == 1
    assert output.read_text() == "preserve original"
    assert list(tmp_path.glob(".*.backup")) == []


async def test_cli_export_never_replaces_directory_with_force(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'directory.sqlite'}"
    engine = create_engine_for_url(database_url)
    Base.metadata.create_all(engine)
    repository = BriefRepository(create_session_factory(engine))
    stored = repository.save(await persistence_input())
    output = tmp_path / "keep-directory"
    output.mkdir()
    marker = output / "preserve.txt"
    marker.write_text("preserve")
    monkeypatch.setenv("EVIDENCEFORGE_DATABASE_URL", database_url)
    get_settings.cache_clear()

    try:
        result = CliRunner().invoke(
            app,
            [
                "brief",
                "export",
                "--brief-id",
                stored.brief_id,
                "--format",
                "json",
                "--output",
                str(output),
                "--force",
            ],
        )
    finally:
        get_settings.cache_clear()

    assert result.exit_code != 0
    assert "Output path is a directory" in _plain_output(result.output)
    assert marker.read_text() == "preserve"


def _plain_output(value: str) -> str:
    return " ".join(unstyle(value).split())
