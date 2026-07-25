"""Transactional repository for normalized and lossless brief persistence."""

from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from evidenceforge.db.models import (
    BriefEvidenceRow,
    BriefRow,
    BriefVersionRow,
    ClaimRow,
    ClaimSourceLinkRow,
    EvidenceRecordRow,
    LlmRunRow,
    OntologyCandidateRow,
    OntologyMappingRow,
    PicoElementRow,
    QaFindingRow,
    QaReportRow,
    QuestionRow,
    RevisionChangeRow,
    RevisionRow,
    SearchRow,
    TrialRow,
)
from evidenceforge.db.schemas import BriefPersistenceInput, StoredBrief
from evidenceforge.models.evidence import ClinicalTrialRecord, PubMedRecord, SearchMetadata
from evidenceforge.models.llm import LLMRunMetadata
from evidenceforge.models.qa import QAReport, SynthesisDraft


class BriefNotFoundError(LookupError):
    """Raised when a requested persisted brief does not exist."""


class BriefRepository:
    """Persist and reconstruct complete synthesis/QA aggregates transactionally."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, aggregate: BriefPersistenceInput) -> StoredBrief:
        """Persist one validated aggregate and return its stable identity."""

        brief_id = str(uuid4())
        question_id = str(uuid4())
        created_at = aggregate.created_at
        with self._session_factory.begin() as session:
            session.add(
                QuestionRow(
                    id=question_id,
                    original_question=aggregate.question,
                    created_at=created_at,
                )
            )
            session.flush()
            self._add_pico(session, question_id, aggregate)
            self._add_mappings(session, question_id, aggregate)
            session.add(
                BriefRow(
                    id=brief_id,
                    question_id=question_id,
                    final_qa_status=aggregate.synthesis_qa.final_qa.status.value,
                    aggregate_payload=aggregate.model_dump(mode="json"),
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
            session.flush()
            self._add_searches(session, brief_id, aggregate)
            evidence_ids = self._add_evidence(session, brief_id, aggregate)
            self._add_versions_and_claims(session, brief_id, evidence_ids, aggregate)
            llm_run_ids = self._add_llm_runs(session, brief_id, aggregate)
            self._add_qa_reports(session, brief_id, llm_run_ids, aggregate)
            self._add_revision(session, brief_id, llm_run_ids, aggregate)
        return StoredBrief(brief_id=brief_id, aggregate=aggregate)

    def get(self, brief_id: str) -> StoredBrief:
        """Reconstruct the validated aggregate or raise a domain not-found error."""

        with self._session_factory() as session:
            row = session.get(BriefRow, brief_id)
            if row is None:
                raise BriefNotFoundError(brief_id)
            aggregate = BriefPersistenceInput.model_validate(row.aggregate_payload)
        return StoredBrief(brief_id=brief_id, aggregate=aggregate)

    @staticmethod
    def _add_pico(
        session: Session,
        question_id: str,
        aggregate: BriefPersistenceInput,
    ) -> None:
        pico = aggregate.pico
        values: list[tuple[str, str]] = [
            ("population", pico.population),
            ("condition", pico.condition),
            ("intervention", pico.intervention),
            ("comparator", pico.comparator),
        ]
        values.extend(("outcome", value) for value in pico.outcomes)
        values.extend(("ambiguity", value) for value in pico.ambiguities)
        values.extend(("missing_information", value) for value in pico.missing_information)
        values.extend(("normalized_search_term", value) for value in pico.normalized_search_terms)
        if pico.time_horizon is not None:
            values.append(("time_horizon", pico.time_horizon))
        if pico.study_context is not None:
            values.append(("study_context", pico.study_context))
        positions: dict[str, int] = {}
        for element_type, value in values:
            position = positions.get(element_type, 0)
            positions[element_type] = position + 1
            session.add(
                PicoElementRow(
                    question_id=question_id,
                    element_type=element_type,
                    position=position,
                    value=value,
                )
            )

    @staticmethod
    def _add_mappings(
        session: Session,
        question_id: str,
        aggregate: BriefPersistenceInput,
    ) -> None:
        for mapping in aggregate.mappings:
            row = OntologyMappingRow(
                question_id=question_id,
                original_term=mapping.original_term,
                normalized_term=mapping.normalized_term,
                ontology=mapping.ontology.value,
                selected_code=mapping.selected.code if mapping.selected else None,
                match_method=mapping.match_method,
                human_review_required=mapping.human_review_required,
                review_reason=mapping.review_reason,
            )
            session.add(row)
            session.flush()
            for candidate in mapping.candidates:
                session.add(
                    OntologyCandidateRow(
                        mapping_id=row.id,
                        ontology=candidate.ontology.value,
                        code=candidate.code,
                        preferred_label=candidate.preferred_label,
                        source_url=str(candidate.source_url),
                        source_rank=candidate.source_rank,
                        score=candidate.score,
                        selected=mapping.selected == candidate,
                    )
                )

    @staticmethod
    def _add_searches(
        session: Session,
        brief_id: str,
        aggregate: BriefPersistenceInput,
    ) -> None:
        for metadata in (
            aggregate.retrieval.pubmed.metadata,
            aggregate.retrieval.clinical_trials.metadata,
        ):
            session.add(_search_row(brief_id, metadata))

    @staticmethod
    def _add_evidence(
        session: Session,
        brief_id: str,
        aggregate: BriefPersistenceInput,
    ) -> dict[str, int]:
        evidence: list[PubMedRecord | ClinicalTrialRecord] = [
            *aggregate.retrieval.pubmed.records,
            *aggregate.retrieval.clinical_trials.records,
        ]
        retrieved_at = {
            aggregate.retrieval.pubmed.metadata.source.value: (
                aggregate.retrieval.pubmed.metadata.executed_at
            ),
            aggregate.retrieval.clinical_trials.metadata.source.value: (
                aggregate.retrieval.clinical_trials.metadata.executed_at
            ),
        }
        ranking_by_id = {
            item.record_id: (position, item)
            for position, item in enumerate(aggregate.retrieval.ranking, start=1)
        }
        evidence_ids: dict[str, int] = {}
        for record in evidence:
            source = "pubmed" if isinstance(record, PubMedRecord) else "clinicaltrials.gov"
            row = EvidenceRecordRow(
                source=source,
                external_id=record.record_id,
                title=record.title,
                source_url=record.url,
                retrieved_at=retrieved_at[source],
                normalized_payload=record.model_dump(mode="json"),
            )
            session.add(row)
            session.flush()
            evidence_ids[record.record_id] = row.id
            ranking = ranking_by_id.get(record.record_id)
            session.add(
                BriefEvidenceRow(
                    brief_id=brief_id,
                    evidence_record_id=row.id,
                    rank=ranking[0] if ranking else None,
                    score=ranking[1].score if ranking else None,
                    ranking_components=(
                        ranking[1].components.model_dump(mode="json") if ranking else None
                    ),
                    ranking_method=ranking[1].method if ranking else None,
                )
            )
            if isinstance(record, ClinicalTrialRecord):
                session.add(
                    TrialRow(
                        evidence_record_id=row.id,
                        overall_status=record.overall_status,
                        study_type=record.study_type,
                        allocation=record.allocation,
                        enrollment=record.enrollment,
                        has_results=record.has_results,
                    )
                )
        return evidence_ids

    @staticmethod
    def _add_versions_and_claims(
        session: Session,
        brief_id: str,
        evidence_ids: dict[str, int],
        aggregate: BriefPersistenceInput,
    ) -> None:
        drafts = [("original", aggregate.synthesis_qa.original_draft)]
        if aggregate.synthesis_qa.revision is not None:
            drafts.append(("revised", aggregate.synthesis_qa.revision.revised_draft))
        for version_kind, draft in drafts:
            version = BriefVersionRow(
                brief_id=brief_id,
                version_kind=version_kind,
                clinical_question=draft.clinical_question,
                executive_answer=draft.executive_answer,
                evidence_summary=draft.evidence_summary,
                clinical_interpretation=draft.clinical_interpretation,
                prompt_version=draft.prompt_version,
                draft_payload=draft.model_dump(mode="json"),
            )
            session.add(version)
            session.flush()
            _add_claims(session, version.id, draft, evidence_ids)

    @staticmethod
    def _add_llm_runs(
        session: Session,
        brief_id: str,
        aggregate: BriefPersistenceInput,
    ) -> dict[str, int]:
        runs: list[tuple[str, LLMRunMetadata]] = [
            ("synthesis", aggregate.synthesis_qa.synthesis_run),
            ("original_qa", aggregate.synthesis_qa.original_qa.llm_run),
            ("final_qa", aggregate.synthesis_qa.final_qa.llm_run),
        ]
        if aggregate.synthesis_qa.revision is not None:
            runs.append(("revision", aggregate.synthesis_qa.revision.llm_run))
        run_ids: dict[str, int] = {}
        for stage, metadata in runs:
            row = LlmRunRow(
                brief_id=brief_id,
                stage=stage,
                provider=metadata.provider,
                model=metadata.model,
                latency_ms=metadata.latency_ms,
                input_tokens=metadata.input_tokens,
                output_tokens=metadata.output_tokens,
                retry_count=metadata.retry_count,
            )
            session.add(row)
            session.flush()
            run_ids[stage] = row.id
        return run_ids

    @staticmethod
    def _add_qa_reports(
        session: Session,
        brief_id: str,
        llm_run_ids: dict[str, int],
        aggregate: BriefPersistenceInput,
    ) -> None:
        reports = (
            ("original", "original_qa", aggregate.synthesis_qa.original_qa),
            ("final", "final_qa", aggregate.synthesis_qa.final_qa),
        )
        for report_kind, run_stage, report in reports:
            row = QaReportRow(
                brief_id=brief_id,
                llm_run_id=llm_run_ids[run_stage],
                report_kind=report_kind,
                status=report.status.value,
                reviewed_draft_sha256=report.reviewed_draft_sha256,
                prompt_version=report.prompt_version,
            )
            session.add(row)
            session.flush()
            _add_findings(session, row.id, report)

    @staticmethod
    def _add_revision(
        session: Session,
        brief_id: str,
        llm_run_ids: dict[str, int],
        aggregate: BriefPersistenceInput,
    ) -> None:
        revision = aggregate.synthesis_qa.revision
        if revision is None:
            return
        row = RevisionRow(
            brief_id=brief_id,
            llm_run_id=llm_run_ids["revision"],
            prompt_version=revision.prompt_version,
        )
        session.add(row)
        session.flush()
        for change in revision.changes:
            session.add(
                RevisionChangeRow(
                    revision_id=row.id,
                    claim_key=change.claim_id,
                    original_text=change.original_text,
                    revised_text=change.revised_text,
                    original_source_ids=list(change.original_source_ids),
                    revised_source_ids=list(change.revised_source_ids),
                    reason=change.reason,
                )
            )


def _search_row(brief_id: str, metadata: SearchMetadata) -> SearchRow:
    return SearchRow(
        brief_id=brief_id,
        source=metadata.source.value,
        query=metadata.query,
        filters=metadata.filters,
        executed_at=metadata.executed_at,
        total_count=metadata.total_count,
        page_size=metadata.page_size,
        offset=metadata.offset,
        page_token=metadata.page_token,
        next_page_token=metadata.next_page_token,
    )


def _add_claims(
    session: Session,
    version_id: int,
    draft: SynthesisDraft,
    evidence_ids: dict[str, int],
) -> None:
    for claim in draft.claims:
        row = ClaimRow(
            brief_version_id=version_id,
            claim_key=claim.claim_id,
            text=claim.text,
            claim_type=claim.claim_type.value,
        )
        session.add(row)
        session.flush()
        passages_by_source: dict[str, list[tuple[str | None, str | None]]] = {}
        for passage in claim.supporting_passages:
            passages_by_source.setdefault(passage.source_id, []).append(
                (passage.text, passage.location)
            )
        source_ids = set(claim.linked_source_ids) | set(passages_by_source)
        for source_id in sorted(source_ids):
            passages = passages_by_source.get(source_id, [(None, None)])
            for passage_text, passage_location in passages:
                session.add(
                    ClaimSourceLinkRow(
                        claim_id=row.id,
                        evidence_record_id=evidence_ids.get(source_id),
                        external_source_id=source_id,
                        passage_text=passage_text,
                        passage_location=passage_location,
                    )
                )


def _add_findings(session: Session, report_id: int, report: QAReport) -> None:
    for assessment in report.assessments:
        session.add(
            QaFindingRow(
                qa_report_id=report_id,
                finding_kind="assessment",
                claim_key=assessment.claim_id,
                classification=assessment.classification.value,
                severity=assessment.severity.value,
                explanation=assessment.explanation,
                recommended_correction=assessment.recommended_correction,
                finding_payload=assessment.model_dump(mode="json"),
            )
        )
    for deterministic in report.deterministic_findings:
        session.add(
            QaFindingRow(
                qa_report_id=report_id,
                finding_kind="deterministic",
                claim_key=deterministic.claim_id,
                severity=deterministic.severity.value,
                explanation=deterministic.message,
                recommended_correction=deterministic.recommended_correction,
                finding_payload=deterministic.model_dump(mode="json"),
            )
        )
    for untracked in report.untracked_claims:
        session.add(
            QaFindingRow(
                qa_report_id=report_id,
                finding_kind="untracked",
                severity=untracked.severity.value,
                explanation=untracked.explanation,
                recommended_correction=untracked.recommended_correction,
                finding_payload=untracked.model_dump(mode="json"),
            )
        )
