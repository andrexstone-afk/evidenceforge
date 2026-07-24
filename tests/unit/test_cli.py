from pathlib import Path

import pytest
from click import unstyle
from typer.testing import CliRunner

from evidenceforge.cli.app import app
from evidenceforge.llm import MockLLMProvider
from evidenceforge.models import PICO
from evidenceforge.pipelines.coded_brief import load_pico_prompt


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


def _plain_output(value: str) -> str:
    return " ".join(unstyle(value).split())
