"""Stable versioned request, response, and error contracts."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from evidenceforge.db.schemas import BriefPersistenceInput
from evidenceforge.models.ontology import Mapping
from evidenceforge.models.pico import PICO
from evidenceforge.models.qa import QAReport, RevisionArtifact, SynthesisQAResult
from evidenceforge.pipelines.evidence_retrieval import EvidenceRetrievalResult


class BriefCreateRequest(BaseModel):
    """Completed Phase 3 artifact accepted by the Phase 4 persistence boundary."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=10)
    pico: PICO
    mappings: tuple[Mapping, ...] = ()
    retrieval: EvidenceRetrievalResult
    synthesis_qa: SynthesisQAResult
    confirm_no_phi: Literal[True]


class BriefLinks(BaseModel):
    """Discoverable stable URLs for a persisted brief."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    result: str
    qa: str
    export: str


class BriefCreateResponse(BaseModel):
    """Synchronous v1 result shaped for a future asynchronous job transition."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    brief_id: str
    processing_status: Literal["completed"]
    qa_status: str
    correlation_id: str
    links: BriefLinks


class BriefReadResponse(BaseModel):
    """Complete reconstructed persisted brief."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    brief_id: str
    aggregate: BriefPersistenceInput


class BriefQAResponse(BaseModel):
    """Original and final QA artifacts with any preserved revision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    brief_id: str
    original_qa: QAReport
    final_qa: QAReport
    revision: RevisionArtifact | None


class BriefExportResponse(BaseModel):
    """JSON export envelope; Markdown and PDF arrive in Phase 5."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    brief_id: str
    format: Literal["json"]
    media_type: Literal["application/json"]
    content: dict[str, Any]


class ErrorDetail(BaseModel):
    """Machine-readable API error payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str
    correlation_id: str
    details: list[dict[str, Any]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Consistent error response envelope."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    error: ErrorDetail
