"""EvidenceForge command-line interface."""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer
import uvicorn
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from evidenceforge import __version__
from evidenceforge.clients.terminology import ICD10CMClient, RxNormClient
from evidenceforge.clients.terminology.base import TerminologyClientError
from evidenceforge.core.safety import UnsafeClinicalQuestionError, validate_no_phi_artifact
from evidenceforge.db.repository import BriefNotFoundError, BriefRepository
from evidenceforge.db.session import create_engine_for_url, create_session_factory
from evidenceforge.evaluation import score_evaluation
from evidenceforge.exporters import PDFExportError, render_markdown
from evidenceforge.llm import LLMProvider, MockLLMProvider, OpenAIProvider
from evidenceforge.models.evaluation import EvaluationReport, EvaluationRun
from evidenceforge.pipelines import CodedBriefPipeline
from evidenceforge.services.brief_exports import BriefExportService, ExportFormat
from evidenceforge.settings import get_settings

app = typer.Typer(
    name="evidenceforge",
    help="Build traceable clinical evidence briefs for research use.",
    no_args_is_help=True,
)
brief_app = typer.Typer(help="Create and inspect coded clinical briefs.")
evaluation_app = typer.Typer(help="Score validated evaluation runs.")
app.add_typer(brief_app, name="brief")
app.add_typer(evaluation_app, name="evaluation")

MAX_EVALUATION_INPUT_BYTES = 10 * 1024 * 1024


@app.command()
def version() -> None:
    """Print the installed EvidenceForge version."""

    typer.echo(__version__)


@app.command()
def serve() -> None:
    """Run the local API server."""

    settings = get_settings()
    uvicorn.run(
        "evidenceforge.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
    )


@brief_app.command("create")
def create_brief(
    question: Annotated[
        str,
        typer.Option("--question", "-q", help="Plain-English clinical question."),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Markdown output path."),
    ] = None,
    confirm_no_phi: Annotated[
        bool,
        typer.Option(
            "--confirm-no-phi",
            help="Confirm the question contains no patient-identifiable information.",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing output file."),
    ] = False,
) -> None:
    """Create a terminology-coded Markdown brief."""

    if not confirm_no_phi:
        raise typer.BadParameter("--confirm-no-phi is required")
    if output is not None and output.exists() and not force:
        raise typer.BadParameter(f"Output already exists: {output}; pass --force to replace it")
    try:
        asyncio.run(_create_brief(question=question, output=output))
    except (TerminologyClientError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


async def _create_brief(*, question: str, output: Path | None) -> None:
    settings = get_settings()
    provider: LLMProvider
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise typer.BadParameter(
                "EVIDENCEFORGE_OPENAI_API_KEY is required when LLM provider is openai"
            )
        provider = OpenAIProvider(
            api_key=settings.openai_api_key.get_secret_value(),
            model=settings.openai_model,
            timeout_seconds=settings.request_timeout_seconds,
            retries=settings.request_retries,
            reasoning_effort=(
                settings.openai_reasoning_effort if settings.openai_reasoning_enabled else None
            ),
        )
    else:
        provider = MockLLMProvider()

    icd10 = ICD10CMClient(
        timeout_seconds=settings.request_timeout_seconds,
        retries=settings.request_retries,
    )
    rxnorm = RxNormClient(
        timeout_seconds=settings.request_timeout_seconds,
        retries=settings.request_retries,
    )
    try:
        brief = await CodedBriefPipeline(
            llm=provider,
            icd10=icd10,
            rxnorm=rxnorm,
        ).run(question, confirmed_no_phi=True)
    finally:
        await icd10.aclose()
        await rxnorm.aclose()
        await provider.aclose()

    markdown = render_markdown(brief)
    if output is None:
        typer.echo(markdown)
    else:
        output.write_text(markdown, encoding="utf-8")
        typer.echo(f"Wrote {output}")


@brief_app.command("export")
def export_brief(
    brief_id: Annotated[
        UUID,
        typer.Option("--brief-id", help="Persisted brief UUID."),
    ],
    export_format: Annotated[
        ExportFormat,
        typer.Option("--format", help="Artifact format: json, markdown, or pdf."),
    ],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Destination file."),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing output file."),
    ] = False,
) -> None:
    """Export a persisted reviewed brief to JSON, Markdown, or PDF."""

    if output.is_dir():
        raise typer.BadParameter(f"Output path is a directory: {output}")
    if output.exists() and not force:
        raise typer.BadParameter(f"Output already exists: {output}; pass --force to replace it")
    settings = get_settings()
    repository = BriefRepository(
        create_session_factory(create_engine_for_url(settings.database_url))
    )
    try:
        rendered = BriefExportService(repository).render(str(brief_id), export_format)
        _write_export_transactionally(
            repository=repository,
            brief_id=str(brief_id),
            export_format=export_format,
            output=output,
            content=rendered.content,
            force=force,
        )
    except BriefNotFoundError as error:
        raise typer.BadParameter(f"Brief does not exist: {error}") from error
    except PDFExportError as error:
        raise typer.BadParameter(str(error)) from error
    except SQLAlchemyError as error:
        raise typer.BadParameter(
            "Brief database is unavailable; run the documented migrations first"
        ) from error
    except FileExistsError as error:
        raise typer.BadParameter(
            f"Output already exists: {output}; pass --force to replace it"
        ) from error
    except OSError as error:
        raise typer.BadParameter(f"Could not write export: {error}") from error
    typer.echo(f"Wrote {export_format.value} export to {output}")


def _write_export_transactionally(
    *,
    repository: BriefRepository,
    brief_id: str,
    export_format: ExportFormat,
    output: Path,
    content: bytes,
    force: bool,
) -> None:
    """Restore the filesystem if export-metadata persistence does not commit."""

    backup: Path | None = None
    output_created = False
    try:
        if output.is_dir():
            raise IsADirectoryError(output)
        if output.exists() or output.is_symlink():
            if not force:
                raise FileExistsError(output)
            descriptor, backup_name = tempfile.mkstemp(
                prefix=f".{output.name}.",
                suffix=".backup",
                dir=output.parent,
            )
            os.close(descriptor)
            backup = Path(backup_name)
            output.replace(backup)
        with output.open("xb") as stream:
            output_created = True
            stream.write(content)
        repository.record_export(
            brief_id,
            export_format=export_format.value,
            storage_reference="local-cli-output",
        )
    except Exception:
        if output_created:
            output.unlink(missing_ok=True)
        if backup is not None and backup.exists():
            backup.replace(output)
        raise
    else:
        if backup is not None:
            backup.unlink(missing_ok=True)


@evaluation_app.command("score")
def score_evaluation_run(
    input_path: Annotated[
        Path,
        typer.Option("--input", help="Validated evaluation-run JSON input."),
    ],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Destination JSON report."),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing output file."),
    ] = False,
) -> None:
    """Score one aligned evaluation run without network or model calls."""

    if output.is_dir():
        raise typer.BadParameter(f"Output path is a directory: {output}")
    if output.exists() and not force:
        raise typer.BadParameter(f"Output already exists: {output}; pass --force to replace it")
    try:
        if input_path.stat().st_size > MAX_EVALUATION_INPUT_BYTES:
            raise typer.BadParameter("Evaluation input exceeds the 10 MiB safety limit")
        serialized = input_path.read_text(encoding="utf-8")
        validate_no_phi_artifact(serialized)
        run = EvaluationRun.model_validate_json(serialized)
        report = score_evaluation(run, tool_version=__version__)
        _write_evaluation_report(
            output=output,
            content=report.model_dump_json(indent=2) + "\n",
            force=force,
        )
    except FileNotFoundError as error:
        raise typer.BadParameter(f"Evaluation input does not exist: {input_path}") from error
    except UnicodeDecodeError as error:
        raise typer.BadParameter("Evaluation input must be UTF-8 JSON") from error
    except UnsafeClinicalQuestionError as error:
        raise typer.BadParameter(str(error)) from error
    except ValidationError as error:
        raise typer.BadParameter(
            "Invalid evaluation input; see docs/evaluation.md for the versioned contract"
        ) from error
    except FileExistsError as error:
        raise typer.BadParameter(
            f"Output already exists: {output}; pass --force to replace it"
        ) from error
    except OSError as error:
        raise typer.BadParameter(
            f"Could not read or write evaluation artifacts: {error}"
        ) from error
    typer.echo(f"Wrote evaluation report to {output}")


@evaluation_app.command("schema")
def show_evaluation_schema() -> None:
    """Print the versioned evaluation input and report JSON Schemas."""

    typer.echo(
        json.dumps(
            {
                "evaluation_run": EvaluationRun.model_json_schema(),
                "evaluation_report": EvaluationReport.model_json_schema(),
            },
            indent=2,
        )
    )


def _write_evaluation_report(*, output: Path, content: str, force: bool) -> None:
    """Write a report without partial forced replacements or silent overwrites."""

    if not force:
        created = False
        try:
            with output.open("x", encoding="utf-8") as stream:
                created = True
                stream.write(content)
        except Exception:
            if created:
                output.unlink(missing_ok=True)
            raise
        return

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    app()
