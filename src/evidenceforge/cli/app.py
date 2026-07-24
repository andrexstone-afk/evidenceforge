"""EvidenceForge command-line interface."""

import typer
import uvicorn

from evidenceforge import __version__
from evidenceforge.settings import get_settings

app = typer.Typer(
    name="evidenceforge",
    help="Build traceable clinical evidence briefs for research use.",
    no_args_is_help=True,
)


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


if __name__ == "__main__":
    app()
