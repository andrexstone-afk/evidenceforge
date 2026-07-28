import json

from sqlalchemy import func, select

from evidenceforge.db.base import Base
from evidenceforge.db.models import ExportedArtifactRow
from evidenceforge.db.repository import BriefRepository
from evidenceforge.db.session import create_engine_for_url, create_session_factory
from evidenceforge.services.brief_exports import BriefExportService, ExportFormat
from tests.fixtures.persistence import persistence_input


class _SyntheticPDFBackend:
    def render(self, html: str) -> bytes:
        assert "Claims and supporting passages" in html
        assert "Final claim-level QA" in html
        return b"%PDF-synthetic-e2e"


async def test_persisted_reviewed_brief_exports_all_formats_end_to_end(tmp_path) -> None:
    engine = create_engine_for_url(f"sqlite:///{tmp_path / 'export-e2e.sqlite'}")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    repository = BriefRepository(session_factory)
    stored = repository.save(await persistence_input())
    service = BriefExportService(repository, pdf_backend=_SyntheticPDFBackend())

    rendered = {
        export_format: service.render(stored.brief_id, export_format)
        for export_format in ExportFormat
    }
    for export_format in ExportFormat:
        repository.record_export(
            stored.brief_id,
            export_format=export_format.value,
            storage_reference="synthetic-e2e",
        )

    json_document = json.loads(rendered[ExportFormat.JSON].content)
    assert json_document["aggregate"]["question"] == stored.aggregate.question
    assert json_document["metatags"]["qa_status"] == "pass"
    assert b"## Claim-level QA" in rendered[ExportFormat.MARKDOWN].content
    assert rendered[ExportFormat.PDF].content.startswith(b"%PDF-")
    with session_factory() as session:
        artifact_count = session.scalar(select(func.count()).select_from(ExportedArtifactRow))
        assert artifact_count == 3
