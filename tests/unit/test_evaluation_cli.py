import json
import os
from pathlib import Path

import pytest
from click import unstyle
from typer.testing import CliRunner

from evidenceforge.cli import app as cli_module
from evidenceforge.cli.app import app
from tests.fixtures.evaluation import synthetic_evaluation_run

QUESTION_SET_PATH = (
    Path(__file__).parents[2] / "examples" / "evaluation" / "benchmark-question-set-v0.1.json"
)


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
    assert schemas["benchmark_question_set"]["properties"]["schema_version"]["const"] == "1.0"
    assert schemas["evaluation_run"]["properties"]["schema_version"]["const"] == "1.0"
    assert schemas["evaluation_report"]["properties"]["scoring_version"]["const"] == "1.0"


def test_evaluation_cli_writes_question_review_packet(tmp_path: Path) -> None:
    output_path = tmp_path / "review-packet.md"

    result = CliRunner().invoke(
        app,
        [
            "evaluation",
            "review-packet",
            "--input",
            str(QUESTION_SET_PATH),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    packet = output_path.read_text(encoding="utf-8")
    assert "DRAFT — NOT PHYSICIAN REVIEWED" in packet
    assert packet.count("- [ ] Include as written") == 3
    assert "Wrote question review packet" in result.output


def test_evaluation_cli_does_not_overwrite_review_packet_without_force(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "review-packet.md"
    output_path.write_text("preserve", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "evaluation",
            "review-packet",
            "--input",
            str(QUESTION_SET_PATH),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code != 0
    assert "pass --force" in _plain_output(result.output)
    assert output_path.read_text(encoding="utf-8") == "preserve"


def test_evaluation_review_packet_distinguishes_missing_input_from_output_error(
    tmp_path: Path,
) -> None:
    missing_input = tmp_path / "missing.json"
    missing_result = CliRunner().invoke(
        app,
        [
            "evaluation",
            "review-packet",
            "--input",
            str(missing_input),
            "--output",
            str(tmp_path / "packet.md"),
        ],
    )

    assert missing_result.exit_code != 0
    assert "Evaluation input does not exist" in _plain_output(missing_result.output)
    assert missing_input.name in _plain_output(missing_result.output)

    invalid_output = tmp_path / "missing-directory" / "packet.md"
    output_result = CliRunner().invoke(
        app,
        [
            "evaluation",
            "review-packet",
            "--input",
            str(QUESTION_SET_PATH),
            "--output",
            str(invalid_output),
        ],
    )

    assert output_result.exit_code != 0
    assert "Could not read or write evaluation artifacts" in _plain_output(output_result.output)
    assert "Evaluation input does not exist" not in _plain_output(output_result.output)


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


def test_evaluation_cli_rejects_non_regular_input(tmp_path: Path) -> None:
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO creation is unavailable on this platform")
    input_path = tmp_path / "run.fifo"
    os.mkfifo(input_path)

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
    assert "must be a regular file" in _plain_output(result.output)


def test_evaluation_cli_reads_only_through_size_boundary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    input_path = tmp_path / "oversized.json"
    input_path.write_bytes(b"x" * 9)
    monkeypatch.setattr(cli_module, "MAX_EVALUATION_INPUT_BYTES", 8)
    original_fdopen = os.fdopen
    read_sizes: list[int] = []

    class TrackingStream:
        def __init__(self, stream) -> None:
            self.stream = stream

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def read(self, size: int = -1) -> bytes:
            read_sizes.append(size)
            return self.stream.read(size)

    def tracked_fdopen(*args, **kwargs):
        return TrackingStream(original_fdopen(*args, **kwargs))

    monkeypatch.setattr(cli_module.os, "fdopen", tracked_fdopen)

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
    assert "exceeds the 10 MiB safety limit" in _plain_output(result.output)
    assert read_sizes == [9]


def _plain_output(value: str) -> str:
    return " ".join(unstyle(value).replace("│", " ").split())
