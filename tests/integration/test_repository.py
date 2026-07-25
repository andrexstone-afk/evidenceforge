from datetime import UTC

import pytest
from sqlalchemy import func, select

from evidenceforge.db.base import Base
from evidenceforge.db.models import (
    BriefRow,
    ClaimRow,
    ClaimSourceLinkRow,
    EvidenceRecordRow,
    ExportedArtifactRow,
    LlmRunRow,
    OntologyCandidateRow,
    OntologyMappingRow,
    QaFindingRow,
    QaReportRow,
    RevisionChangeRow,
    RevisionRow,
    SearchRow,
)
from evidenceforge.db.repository import (
    MAX_EXPORT_RECORDS_PER_BRIEF,
    BriefNotFoundError,
    BriefRepository,
)
from evidenceforge.db.session import create_engine_for_url, create_session_factory
from tests.fixtures.persistence import persistence_input


async def test_repository_round_trips_normalized_synthesis_qa(tmp_path) -> None:
    engine = create_engine_for_url(f"sqlite:///{tmp_path / 'repository.sqlite'}")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    repository = BriefRepository(session_factory)
    aggregate = await persistence_input()

    stored = repository.save(aggregate)
    restored = repository.get(stored.brief_id)

    assert restored == stored
    assert restored.aggregate == aggregate

    expected_counts = {
        BriefRow: 1,
        OntologyMappingRow: 1,
        OntologyCandidateRow: 1,
        SearchRow: 2,
        EvidenceRecordRow: 2,
        ClaimRow: 4,
        ClaimSourceLinkRow: 4,
        LlmRunRow: 4,
        QaReportRow: 2,
        QaFindingRow: 5,
        RevisionRow: 1,
        RevisionChangeRow: 1,
    }
    with session_factory() as session:
        for row_type, expected in expected_counts.items():
            count = session.scalar(select(func.count()).select_from(row_type))
            assert count == expected
        assert session.scalar(select(BriefRow.created_at)).tzinfo is UTC
        assert session.scalar(select(EvidenceRecordRow.retrieved_at)).tzinfo is UTC
        assert session.scalar(select(SearchRow.executed_at)).tzinfo is UTC
        null_passages = session.scalar(
            select(func.count())
            .select_from(ClaimSourceLinkRow)
            .where(
                ClaimSourceLinkRow.passage_text.is_(None)
                | ClaimSourceLinkRow.passage_location.is_(None)
            )
        )
        assert null_passages == 0


async def test_repository_preserves_evidence_as_brief_scoped_snapshots(tmp_path) -> None:
    engine = create_engine_for_url(f"sqlite:///{tmp_path / 'snapshots.sqlite'}")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    repository = BriefRepository(session_factory)
    aggregate = await persistence_input()

    first = repository.save(aggregate)
    second = repository.save(aggregate)

    assert first.brief_id != second.brief_id
    with session_factory() as session:
        evidence_count = session.scalar(select(func.count()).select_from(EvidenceRecordRow))
        assert evidence_count == 4


async def test_repository_records_successful_export_metadata(tmp_path) -> None:
    engine = create_engine_for_url(f"sqlite:///{tmp_path / 'exports.sqlite'}")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    repository = BriefRepository(session_factory)
    stored = repository.save(await persistence_input())

    repository.record_export(
        stored.brief_id,
        export_format="markdown",
        storage_reference="/safe/output/brief.md",
    )

    with session_factory() as session:
        row = session.scalar(select(ExportedArtifactRow))
        assert row is not None
        assert row.brief_id == stored.brief_id
        assert row.format == "markdown"
        assert row.storage_reference == "/safe/output/brief.md"
        assert row.created_at.tzinfo is UTC


async def test_repository_bounds_export_metadata_per_brief(tmp_path) -> None:
    engine = create_engine_for_url(f"sqlite:///{tmp_path / 'bounded-exports.sqlite'}")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    repository = BriefRepository(session_factory)
    stored = repository.save(await persistence_input())

    for position in range(MAX_EXPORT_RECORDS_PER_BRIEF + 5):
        repository.record_export(
            stored.brief_id,
            export_format="json",
            storage_reference=f"synthetic-{position}",
        )

    with session_factory() as session:
        rows = list(
            session.scalars(
                select(ExportedArtifactRow)
                .where(ExportedArtifactRow.brief_id == stored.brief_id)
                .order_by(ExportedArtifactRow.id)
            )
        )
        assert len(rows) == MAX_EXPORT_RECORDS_PER_BRIEF
        assert rows[0].storage_reference == "synthetic-5"


def test_repository_raises_domain_error_for_unknown_brief(tmp_path) -> None:
    engine = create_engine_for_url(f"sqlite:///{tmp_path / 'missing.sqlite'}")
    Base.metadata.create_all(engine)
    repository = BriefRepository(create_session_factory(engine))

    with pytest.raises(BriefNotFoundError) as captured:
        repository.get("00000000-0000-0000-0000-000000000000")

    assert str(captured.value) == "00000000-0000-0000-0000-000000000000"
