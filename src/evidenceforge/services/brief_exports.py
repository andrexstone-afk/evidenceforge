"""Shared rendering service for persisted reviewed-brief exports."""

from dataclasses import dataclass
from enum import StrEnum

from evidenceforge.db.repository import BriefRepository
from evidenceforge.exporters import (
    PDFBackend,
    build_export_document,
    render_export_json,
    render_export_markdown,
    render_export_pdf,
)


class ExportFormat(StrEnum):
    """Formats supported by the stable API and CLI export boundary."""

    JSON = "json"
    MARKDOWN = "markdown"
    PDF = "pdf"


@dataclass(frozen=True)
class RenderedBriefExport:
    """One rendered artifact with transport metadata."""

    content: bytes
    media_type: str
    extension: str


class BriefExportService:
    """Load one persisted aggregate and render it through canonical exporters."""

    def __init__(
        self,
        repository: BriefRepository,
        *,
        pdf_backend: PDFBackend | None = None,
    ) -> None:
        self._repository = repository
        self._pdf_backend = pdf_backend

    def render(self, brief_id: str, export_format: ExportFormat) -> RenderedBriefExport:
        """Render a persisted brief without making external requests."""

        stored = self._repository.get(brief_id)
        document = build_export_document(
            brief_id=stored.brief_id,
            aggregate=stored.aggregate,
        )
        if export_format is ExportFormat.JSON:
            return RenderedBriefExport(
                content=render_export_json(document).encode(),
                media_type="application/json",
                extension="json",
            )
        if export_format is ExportFormat.MARKDOWN:
            return RenderedBriefExport(
                content=render_export_markdown(document).encode(),
                media_type="text/markdown; charset=utf-8",
                extension="md",
            )
        return RenderedBriefExport(
            content=render_export_pdf(document, backend=self._pdf_backend),
            media_type="application/pdf",
            extension="pdf",
        )
