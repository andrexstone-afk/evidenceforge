"""FastAPI dependency accessors for injected application services."""

from typing import cast

from fastapi import Request

from evidenceforge.db.repository import BriefRepository
from evidenceforge.services.brief_exports import BriefExportService


def get_brief_repository(request: Request) -> BriefRepository:
    """Return the application-scoped repository dependency."""

    return cast(BriefRepository, request.app.state.brief_repository)


def get_brief_export_service(request: Request) -> BriefExportService:
    """Return the application-scoped canonical export service."""

    return cast(BriefExportService, request.app.state.brief_export_service)
