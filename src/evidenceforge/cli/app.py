"""EvidenceForge command-line interface."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from evidenceforge import __version__
from evidenceforge.clients.terminology import ICD10CMClient, RxNormClient
from evidenceforge.clients.terminology.base import TerminologyClientError
from evidenceforge.exporters import render_markdown
from evidenceforge.llm import LLMProvider, MockLLMProvider, OpenAIProvider
from evidenceforge.pipelines import CodedBriefPipeline
from evidenceforge.settings import get_settings

app = typer.Typer(
    name="evidenceforge",
    help="Build traceable clinical evidence briefs for research use.",
    no_args_is_help=True,
)
brief_app = typer.Typer(help="Create and inspect coded clinical briefs.")
app.add_typer(brief_app, name="brief")


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


if __name__ == "__main__":
    app()
