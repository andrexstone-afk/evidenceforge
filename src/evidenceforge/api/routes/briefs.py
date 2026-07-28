"""Persistence-backed brief API routes."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from evidenceforge.api.dependencies import get_brief_export_service, get_brief_repository
from evidenceforge.api.schemas import (
    BriefCreateRequest,
    BriefCreateResponse,
    BriefExportResponse,
    BriefLinks,
    BriefQAResponse,
    BriefReadResponse,
    ErrorResponse,
)
from evidenceforge.core.safety import validate_no_phi_artifact, validate_population_question
from evidenceforge.db.repository import BriefRepository
from evidenceforge.db.schemas import BriefPersistenceInput
from evidenceforge.exporters import BriefExportDocument
from evidenceforge.services.brief_exports import BriefExportService, ExportFormat

router = APIRouter(prefix="/api/v1/briefs", tags=["briefs"])
RepositoryDependency = Annotated[BriefRepository, Depends(get_brief_repository)]
ExportServiceDependency = Annotated[BriefExportService, Depends(get_brief_export_service)]


@router.post(
    "",
    response_model=BriefCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {"model": ErrorResponse, "description": "Invalid or unsafe input"},
        503: {"model": ErrorResponse, "description": "Persistence unavailable"},
    },
    summary="Persist a completed validated evidence brief",
)
def create_brief(
    payload: BriefCreateRequest,
    request: Request,
    repository: RepositoryDependency,
) -> BriefCreateResponse:
    """Persist a completed Phase 3 artifact synchronously in API v1."""

    question = validate_population_question(
        payload.question,
        confirmed_no_phi=payload.confirm_no_phi,
    )
    validate_no_phi_artifact(payload.model_dump_json())
    aggregate = BriefPersistenceInput(
        question=question,
        pico=payload.pico,
        mappings=payload.mappings,
        retrieval=payload.retrieval,
        synthesis_qa=payload.synthesis_qa,
        created_at=datetime.now(UTC),
    )
    stored = repository.save(aggregate)
    base = f"/api/v1/briefs/{stored.brief_id}"
    return BriefCreateResponse(
        brief_id=stored.brief_id,
        processing_status="completed",
        qa_status=stored.aggregate.synthesis_qa.final_qa.status.value,
        correlation_id=request.state.correlation_id,
        links=BriefLinks(result=base, qa=f"{base}/qa", export=f"{base}/export"),
    )


@router.get(
    "/{brief_id}",
    response_model=BriefReadResponse,
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse, "description": "Invalid brief identifier"},
    },
)
def get_brief(brief_id: UUID, repository: RepositoryDependency) -> BriefReadResponse:
    """Return a fully reconstructed validated brief aggregate."""

    brief_key = str(brief_id)
    stored = repository.get(brief_key)
    return BriefReadResponse(brief_id=brief_key, aggregate=stored.aggregate)


@router.get(
    "/{brief_id}/qa",
    response_model=BriefQAResponse,
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse, "description": "Invalid brief identifier"},
    },
)
def get_brief_qa(brief_id: UUID, repository: RepositoryDependency) -> BriefQAResponse:
    """Return original and final QA artifacts without unrelated retrieval payloads."""

    brief_key = str(brief_id)
    stored = repository.get(brief_key)
    synthesis_qa = stored.aggregate.synthesis_qa
    return BriefQAResponse(
        brief_id=brief_key,
        original_qa=synthesis_qa.original_qa,
        final_qa=synthesis_qa.final_qa,
        revision=synthesis_qa.revision,
    )


@router.get(
    "/{brief_id}/export",
    response_model=BriefExportResponse | BriefExportDocument,
    responses={
        200: {
            "description": "Canonical reviewed brief artifact",
            "content": {
                "application/json": {
                    "schema": {
                        "anyOf": [
                            {"$ref": "#/components/schemas/BriefExportResponse"},
                            {"$ref": "#/components/schemas/BriefExportDocument"},
                        ]
                    }
                },
                "text/markdown": {},
                "application/pdf": {},
            },
        },
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse, "description": "Invalid identifier or format"},
        503: {"model": ErrorResponse, "description": "PDF renderer unavailable"},
    },
    response_class=Response,
)
def export_brief(
    brief_id: UUID,
    repository: RepositoryDependency,
    service: ExportServiceDependency,
    export_format: Annotated[ExportFormat, Query(alias="format")] = ExportFormat.JSON,
    download: Annotated[
        bool,
        Query(
            description=("Download canonical JSON instead of the backward-compatible JSON envelope")
        ),
    ] = False,
) -> Response:
    """Return stable JSON or download a canonical JSON, Markdown, or PDF artifact."""

    brief_key = str(brief_id)
    if export_format is ExportFormat.JSON and not download:
        stored = repository.get(brief_key)
        payload = BriefExportResponse(
            brief_id=brief_key,
            format="json",
            media_type="application/json",
            content=stored.aggregate.model_dump(mode="json"),
        )
        return Response(
            content=payload.model_dump_json(),
            media_type="application/json",
        )

    rendered = service.render(brief_key, export_format)
    repository.record_export(
        brief_key,
        export_format=export_format.value,
        storage_reference="api-download",
    )
    filename = f"evidenceforge-{brief_key}.{rendered.extension}"
    return Response(
        content=rendered.content,
        media_type=rendered.media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
