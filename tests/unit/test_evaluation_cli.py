import json
from pathlib import Path

from click import unstyle
from typer.testing import CliRunner

from evidenceforge.cli.app import app
from tests.fixtures.evaluation import synthetic_evaluation_run


def test_evaluation_cli_writes_validated_report(tmp_path: Path) -> None:
    input_path = tmp_path / "run.json"
    output_path = tmp_path / "report.json"
    input_path.write_text(synthetic_evaluation_run().model_dump_json(), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "evaluation",
            "score",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["review_status"] == "synthetic_test"
    assert report["metrics"]["mapping_top1_accuracy"]["value"] == 0.5


def test_evaluation_cli_exposes_versioned_json_schemas() -> None:
    result = CliRunner().invoke(app, ["evaluation", "schema"])

    assert result.exit_code == 0
    schemas = json.loads(result.stdout)
    assert schemas["evaluation_run"]["properties"]["schema_version"]["const"] == "1.0"
    assert schemas["evaluation_report"]["properties"]["scoring_version"]["const"] == "1.0"


def test_evaluation_cli_does_not_overwrite_without_force(tmp_path: Path) -> None:
    input_path = tmp_path / "run.json"
    output_path = tmp_path / "report.json"
    input_path.write_text(synthetic_evaluation_run().model_dump_json(), encoding="utf-8")
    output_path.write_text("preserve", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "evaluation",
            "score",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        terminal_width=40,
    )

    assert result.exit_code != 0
    assert "pass --force" in _plain_output(result.output)
    assert output_path.read_text(encoding="utf-8") == "preserve"


def test_evaluation_cli_rejects_invalid_json_without_traceback(tmp_path: Path) -> None:
    input_path = tmp_path / "invalid.json"
    input_path.write_text('{"review_status": "physician_reviewed"}', encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "evaluation",
            "score",
            "--input",
            str(input_path),
            "--output",
            str(tmp_path / "report.json"),
        ],
    )

    assert result.exit_code != 0
    assert "Invalid evaluation input" in _plain_output(result.output)
    assert "Traceback" not in result.output


def _plain_output(value: str) -> str:
    return " ".join(unstyle(value).replace("│", " ").split())
