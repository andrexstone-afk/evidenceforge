"""FastAPI dependency accessors for injected application services."""

from typing import cast

from fastapi import Request

from evidenceforge.db.repository import BriefRepository


def get_brief_repository(request: Request) -> BriefRepository:
    """Return the application-scoped repository dependency."""

    return cast(BriefRepository, request.app.state.brief_repository)
