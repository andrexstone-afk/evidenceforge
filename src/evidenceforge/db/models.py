"""Normalized relational schema for persisted evidence briefs."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from evidenceforge.db.base import Base
from evidenceforge.db.types import UTCDateTime


class QuestionRow(Base):
    """Original population-level clinical question."""

    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_question: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class PicoElementRow(Base):
    """One normalized PICO scalar or repeated element."""

    __tablename__ = "pico_elements"
    __table_args__ = (
        UniqueConstraint("question_id", "element_type", "position", name="uq_pico_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[str] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
        index=True,
    )
    element_type: Mapped[str] = mapped_column(String(64), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class OntologyMappingRow(Base):
    """Terminology mapping decision for a question entity."""

    __tablename__ = "ontology_mappings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[str] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
        index=True,
    )
    original_term: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_term: Mapped[str] = mapped_column(Text, nullable=False)
    ontology: Mapped[str] = mapped_column(String(32), nullable=False)
    selected_code: Mapped[str | None] = mapped_column(String(64))
    match_method: Mapped[str] = mapped_column(String(64), nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    review_reason: Mapped[str | None] = mapped_column(Text)


class OntologyCandidateRow(Base):
    """Service-returned terminology candidate retained for review."""

    __tablename__ = "ontology_candidates"
    __table_args__ = (UniqueConstraint("mapping_id", "source_rank", name="uq_candidate_rank"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mapping_id: Mapped[int] = mapped_column(
        ForeignKey("ontology_mappings.id", ondelete="CASCADE"),
        index=True,
    )
    ontology: Mapped[str] = mapped_column(String(32), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    preferred_label: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SearchRow(Base):
    """Reproducible evidence-source search metadata."""

    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    brief_id: Mapped[str] = mapped_column(
        ForeignKey("briefs.id", ondelete="CASCADE"),
        index=True,
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    executed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    page_size: Mapped[int] = mapped_column(Integer, nullable=False)
    offset: Mapped[int | None] = mapped_column(Integer)
    page_token: Mapped[str | None] = mapped_column(Text)
    next_page_token: Mapped[str | None] = mapped_column(Text)


class EvidenceRecordRow(Base):
    """Normalized evidence identity and common source fields."""

    __tablename__ = "evidence_records"
    # Deliberately no global (source, external_id) uniqueness constraint: upstream
    # records are mutable, and each brief retains the exact snapshot it reviewed.

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    normalized_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class TrialRow(Base):
    """Queryable ClinicalTrials.gov-specific fields."""

    __tablename__ = "trials"

    evidence_record_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_records.id", ondelete="CASCADE"),
        primary_key=True,
    )
    overall_status: Mapped[str] = mapped_column(String(64), nullable=False)
    study_type: Mapped[str] = mapped_column(String(64), nullable=False)
    allocation: Mapped[str | None] = mapped_column(String(64))
    enrollment: Mapped[int | None] = mapped_column(Integer)
    has_results: Mapped[bool] = mapped_column(Boolean, nullable=False)


class BriefRow(Base):
    """Root persisted brief and lossless validated aggregate supplement."""

    __tablename__ = "briefs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    question_id: Mapped[str] = mapped_column(
        ForeignKey("questions.id", ondelete="RESTRICT"),
        index=True,
    )
    final_qa_status: Mapped[str] = mapped_column(String(32), nullable=False)
    aggregate_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class BriefEvidenceRow(Base):
    """Evidence membership and transparent ranking for one brief."""

    __tablename__ = "brief_evidence"

    brief_id: Mapped[str] = mapped_column(
        ForeignKey("briefs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    evidence_record_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_records.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    rank: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[float | None] = mapped_column(Float)
    ranking_components: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ranking_method: Mapped[str | None] = mapped_column(String(128))


class LlmRunRow(Base):
    """Observable LLM execution metadata without prompts or secrets."""

    __tablename__ = "llm_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    brief_id: Mapped[str] = mapped_column(
        ForeignKey("briefs.id", ondelete="CASCADE"),
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False)


class BriefVersionRow(Base):
    """Original or revised immutable synthesis version."""

    __tablename__ = "brief_versions"
    __table_args__ = (UniqueConstraint("brief_id", "version_kind", name="uq_brief_version_kind"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    brief_id: Mapped[str] = mapped_column(
        ForeignKey("briefs.id", ondelete="CASCADE"),
        index=True,
    )
    version_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    clinical_question: Mapped[str] = mapped_column(Text, nullable=False)
    executive_answer: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    clinical_interpretation: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    draft_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ClaimRow(Base):
    """Explicit substantive claim belonging to one draft version."""

    __tablename__ = "claims"
    __table_args__ = (
        UniqueConstraint("brief_version_id", "claim_key", name="uq_version_claim_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    brief_version_id: Mapped[int] = mapped_column(
        ForeignKey("brief_versions.id", ondelete="CASCADE"),
        index=True,
    )
    claim_key: Mapped[str] = mapped_column(String(16), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(32), nullable=False)


class ClaimSourceLinkRow(Base):
    """Claim-to-evidence link with source-preserving passage."""

    __tablename__ = "claim_source_links"
    __table_args__ = (
        UniqueConstraint(
            "claim_id",
            "external_source_id",
            "passage_text",
            name="uq_claim_source_passage",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    claim_id: Mapped[int] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"),
        index=True,
    )
    evidence_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence_records.id", ondelete="RESTRICT"),
        index=True,
    )
    external_source_id: Mapped[str] = mapped_column(String(32), nullable=False)
    passage_text: Mapped[str | None] = mapped_column(Text)
    passage_location: Mapped[str | None] = mapped_column(Text)


class QaReportRow(Base):
    """Original or final QA report and deterministic status."""

    __tablename__ = "qa_reports"
    __table_args__ = (UniqueConstraint("brief_id", "report_kind", name="uq_brief_report_kind"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    brief_id: Mapped[str] = mapped_column(
        ForeignKey("briefs.id", ondelete="CASCADE"),
        index=True,
    )
    llm_run_id: Mapped[int] = mapped_column(
        ForeignKey("llm_runs.id", ondelete="RESTRICT"),
    )
    report_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reviewed_draft_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)


class QaFindingRow(Base):
    """Normalized reviewer, deterministic, or untracked QA finding."""

    __tablename__ = "qa_findings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    qa_report_id: Mapped[int] = mapped_column(
        ForeignKey("qa_reports.id", ondelete="CASCADE"),
        index=True,
    )
    finding_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    claim_key: Mapped[str | None] = mapped_column(String(16))
    classification: Mapped[str | None] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_correction: Mapped[str | None] = mapped_column(Text)
    finding_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class RevisionRow(Base):
    """Revision run linking the original and revised immutable artifacts."""

    __tablename__ = "revisions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    brief_id: Mapped[str] = mapped_column(
        ForeignKey("briefs.id", ondelete="CASCADE"),
        unique=True,
    )
    llm_run_id: Mapped[int] = mapped_column(
        ForeignKey("llm_runs.id", ondelete="RESTRICT"),
    )
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)


class RevisionChangeRow(Base):
    """Auditable claim-level change made by one revision."""

    __tablename__ = "revision_changes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("revisions.id", ondelete="CASCADE"),
        index=True,
    )
    claim_key: Mapped[str] = mapped_column(String(16), nullable=False)
    original_text: Mapped[str | None] = mapped_column(Text)
    revised_text: Mapped[str | None] = mapped_column(Text)
    original_source_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    revised_source_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class ExportedArtifactRow(Base):
    """Metadata for later Markdown, JSON, or PDF exports."""

    __tablename__ = "exported_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    brief_id: Mapped[str] = mapped_column(
        ForeignKey("briefs.id", ondelete="CASCADE"),
        index=True,
    )
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    storage_reference: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
