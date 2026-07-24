"""EvidenceForge HTTP application."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from evidenceforge import __version__


class HealthResponse(BaseModel):
    """Stable health response contract."""

    status: Literal["ok"]
    service: str
    version: str


def create_app() -> FastAPI:
    """Create the API application without import-time side effects."""

    application = FastAPI(
        title="EvidenceForge",
        version=__version__,
        description=(
            "Research evidence-synthesis prototype; not a medical device or a source "
            "of individualized clinical advice."
        ),
    )

    @application.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", service="evidenceforge", version=__version__)

    return application


app = create_app()
