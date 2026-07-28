"""Schema-validating client for the local EvidenceForge API."""

from dataclasses import dataclass
from typing import ClassVar, Literal
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from evidenceforge.api.schemas import BriefQAResponse, BriefReadResponse

ExportName = Literal["json", "markdown", "pdf"]


class HealthPayload(BaseModel):
    """Validated API health response used by the interface."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["ok"]
    service: Literal["evidenceforge"]
    version: str


@dataclass(frozen=True)
class ExportArtifact:
    """Downloaded artifact bytes plus the media metadata needed by Streamlit."""

    content: bytes
    media_type: str
    filename: str


class EvidenceForgeAPIError(RuntimeError):
    """Stable user-facing API failure without response-body or exception leakage."""


class EvidenceForgeAPIClient:
    """Load validated briefs, QA artifacts, and reviewed exports over HTTP."""

    _MEDIA_TYPES: ClassVar[dict[ExportName, str]] = {
        "json": "application/json",
        "markdown": "text/markdown",
        "pdf": "application/pdf",
    }

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout_seconds)
        self._transport = transport

    def health(self) -> HealthPayload:
        """Return a schema-validated API health response."""

        response = self._get("/api/v1/health")
        return self._validate_json(response, HealthPayload)

    def get_brief(self, brief_id: UUID) -> BriefReadResponse:
        """Return one schema-validated persisted brief."""

        response = self._get(f"/api/v1/briefs/{brief_id}")
        return self._validate_json(response, BriefReadResponse)

    def get_qa(self, brief_id: UUID) -> BriefQAResponse:
        """Return the dedicated schema-validated QA artifact."""

        response = self._get(f"/api/v1/briefs/{brief_id}/qa")
        return self._validate_json(response, BriefQAResponse)

    def get_review_bundle(
        self,
        brief_id: UUID,
    ) -> tuple[BriefReadResponse, BriefQAResponse]:
        """Return matching brief and QA responses or reject inconsistent API state."""

        brief = self.get_brief(brief_id)
        qa = self.get_qa(brief_id)
        synthesis = brief.aggregate.synthesis_qa
        if (
            qa.brief_id != brief.brief_id
            or qa.original_qa != synthesis.original_qa
            or qa.final_qa != synthesis.final_qa
            or qa.revision != synthesis.revision
        ):
            raise EvidenceForgeAPIError("The API returned inconsistent review artifacts.")
        return brief, qa

    def download_export(self, brief_id: UUID, export_format: ExportName) -> ExportArtifact:
        """Download one reviewed export after validating its declared media type."""

        response = self._get(
            f"/api/v1/briefs/{brief_id}/export",
            params={"format": export_format, "download": "true"},
        )
        expected = self._MEDIA_TYPES[export_format]
        actual = response.headers.get("content-type", "").split(";", maxsplit=1)[0].lower()
        if actual != expected:
            raise EvidenceForgeAPIError("The API returned an unexpected export format.")
        extension = "md" if export_format == "markdown" else export_format
        return ExportArtifact(
            content=response.content,
            media_type=expected,
            filename=f"evidenceforge-{brief_id}.{extension}",
        )

    def _get(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        try:
            with httpx.Client(
                base_url=self._base_url,
                timeout=self._timeout,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = client.get(path, params=params)
        except httpx.TimeoutException as error:
            raise EvidenceForgeAPIError("The EvidenceForge API timed out.") from error
        except httpx.RequestError as error:
            raise EvidenceForgeAPIError("The EvidenceForge API is unavailable.") from error
        if response.status_code == 404:
            raise EvidenceForgeAPIError("The requested brief was not found.")
        if response.status_code == 422:
            raise EvidenceForgeAPIError("The API rejected the brief or export request.")
        if response.status_code == 503:
            raise EvidenceForgeAPIError("The requested EvidenceForge service is unavailable.")
        if not 200 <= response.status_code < 300:
            raise EvidenceForgeAPIError("The EvidenceForge API returned an unexpected error.")
        return response

    @staticmethod
    def _validate_json[ModelT: BaseModel](
        response: httpx.Response,
        model: type[ModelT],
    ) -> ModelT:
        try:
            return model.model_validate_json(response.content)
        except ValidationError as error:
            raise EvidenceForgeAPIError("The API returned an invalid response.") from error
