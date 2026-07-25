"""EvidenceForge HTTP application."""

import re
from typing import Any, Literal
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from evidenceforge import __version__
from evidenceforge.api.routes.briefs import router as briefs_router
from evidenceforge.api.schemas import ErrorDetail, ErrorResponse
from evidenceforge.core.safety import UnsafeClinicalQuestionError
from evidenceforge.db.repository import BriefNotFoundError, BriefRepository
from evidenceforge.db.session import create_engine_for_url, create_session_factory
from evidenceforge.settings import Settings, get_settings

logger = structlog.get_logger(__name__)
CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class HealthResponse(BaseModel):
    """Stable health response contract."""

    status: Literal["ok"]
    service: str
    version: str


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attach a bounded correlation ID to request state and every response."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        incoming = request.headers.get("X-Correlation-ID", "")
        correlation_id = incoming if CORRELATION_ID_PATTERN.fullmatch(incoming) else str(uuid4())
        request.state.correlation_id = correlation_id
        try:
            response = await call_next(request)
        except Exception as error:
            logger.error(
                "unhandled_api_error",
                correlation_id=correlation_id,
                error_type=type(error).__name__,
            )
            response = _error_response(
                request,
                status_code=500,
                code="internal_error",
                message="An unexpected error occurred.",
            )
        response.headers["X-Correlation-ID"] = correlation_id
        return response


def create_app(
    *,
    repository: BriefRepository | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Create the API application with explicitly injectable dependencies."""

    resolved_settings = settings or get_settings()
    if repository is None:
        engine = create_engine_for_url(resolved_settings.database_url)
        repository = BriefRepository(create_session_factory(engine))
    application = FastAPI(
        title="EvidenceForge",
        version=__version__,
        description=(
            "Research evidence-synthesis prototype; not a medical device or a source "
            "of individualized clinical advice."
        ),
    )
    application.state.brief_repository = repository
    application.add_middleware(CorrelationIdMiddleware)
    application.include_router(briefs_router)

    @application.exception_handler(BriefNotFoundError)
    async def brief_not_found(request: Request, _error: BriefNotFoundError) -> JSONResponse:
        return _error_response(
            request,
            status_code=404,
            code="brief_not_found",
            message="The requested brief does not exist.",
        )

    @application.exception_handler(UnsafeClinicalQuestionError)
    async def unsafe_question(
        request: Request,
        error: UnsafeClinicalQuestionError,
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=422,
            code="unsafe_clinical_question",
            message=str(error),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=422,
            code="validation_error",
            message="Request validation failed.",
            details=_validation_details(error),
        )

    @application.exception_handler(ValidationError)
    async def domain_validation_error(
        request: Request,
        error: ValidationError,
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=422,
            code="validation_error",
            message="Validated artifact consistency check failed.",
            details=_validation_details(error),
        )

    @application.exception_handler(SQLAlchemyError)
    async def persistence_error(
        request: Request,
        error: SQLAlchemyError,
    ) -> JSONResponse:
        logger.error(
            "persistence_error",
            correlation_id=request.state.correlation_id,
            error_type=type(error).__name__,
        )
        return _error_response(
            request,
            status_code=503,
            code="persistence_unavailable",
            message="Brief persistence is temporarily unavailable.",
        )

    @application.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", service="evidenceforge", version=__version__)

    return application


def _validation_details(
    error: RequestValidationError | ValidationError,
) -> list[dict[str, Any]]:
    """Return stable JSON-safe diagnostics without reflecting submitted values."""

    return [
        {
            "type": item["type"],
            "loc": list(item["loc"]),
            "msg": item["msg"],
        }
        for item in error.errors()
    ]


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            correlation_id=request.state.correlation_id,
            details=details or [],
        )
    )
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


app = create_app()
