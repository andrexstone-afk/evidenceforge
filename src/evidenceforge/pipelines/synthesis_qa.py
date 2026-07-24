"""Structured synthesis, independent claim QA, revision, and re-review."""

import json
from collections.abc import Mapping as MappingABC

from evidenceforge.core.prompts import load_versioned_prompt
from evidenceforge.llm.base import LLMProvider
from evidenceforge.models.evidence import ClinicalTrialRecord, PubMedRecord
from evidenceforge.models.llm import LLMRunMetadata
from evidenceforge.models.ontology import Mapping
from evidenceforge.models.pico import PICO
from evidenceforge.models.qa import (
    Claim,
    ClaimAssessment,
    QAReport,
    QAReviewerOutput,
    QAStatus,
    RevisedDraftOutput,
    RevisionArtifact,
    RevisionChange,
    SynthesisDraft,
    SynthesisQAResult,
    derive_qa_status,
    reviewed_draft_sha256,
)
from evidenceforge.pipelines.evidence_retrieval import EvidenceRetrievalResult
from evidenceforge.qa import evidence_record_text, run_deterministic_checks

EvidenceRecord = PubMedRecord | ClinicalTrialRecord


class SynthesisQAPipeline:
    """Run synthesis and independent QA with an auditable revision boundary."""

    def __init__(
        self,
        *,
        synthesis_llm: LLMProvider,
        qa_llm: LLMProvider,
        revision_llm: LLMProvider,
    ) -> None:
        self._synthesis_llm = synthesis_llm
        self._qa_llm = qa_llm
        self._revision_llm = revision_llm

    async def run(
        self,
        *,
        question: str,
        pico: PICO,
        mappings: list[Mapping],
        retrieval: EvidenceRetrievalResult,
    ) -> SynthesisQAResult:
        """Create, review, revise when needed, and independently re-review."""

        cleaned_question = question.strip()
        if len(cleaned_question) < 10:
            raise ValueError("Clinical question must contain at least 10 characters")
        evidence: list[EvidenceRecord] = [
            *retrieval.pubmed.records,
            *retrieval.clinical_trials.records,
        ]
        if not evidence:
            raise ValueError("Synthesis requires at least one retrieved evidence record")
        original_draft = await self._synthesis_llm.generate_structured(
            system_prompt=load_versioned_prompt("synthesis/v1.md"),
            user_prompt=_untrusted_prompt(
                {
                    "clinical_question": cleaned_question,
                    "pico": pico.model_dump(mode="json"),
                    "terminology_mappings": [item.model_dump(mode="json") for item in mappings],
                    "evidence": _evidence_payload(evidence),
                }
            ),
            response_model=SynthesisDraft,
        )
        synthesis_run = _require_metadata(self._synthesis_llm, "synthesis")
        _validate_draft(
            original_draft,
            expected_question=cleaned_question,
            evidence=evidence,
        )
        original_qa = await self._review(original_draft, evidence)
        if original_qa.status is QAStatus.PASS:
            return SynthesisQAResult(
                original_draft=original_draft,
                original_qa=original_qa,
                final_draft=original_draft,
                final_qa=original_qa,
                synthesis_run=synthesis_run,
            )
        revision_output = await self._revision_llm.generate_structured(
            system_prompt=load_versioned_prompt("revision/v1.md"),
            user_prompt=_untrusted_prompt(
                {
                    "draft": original_draft.model_dump(mode="json"),
                    "qa_report": _qa_payload(original_qa),
                    "evidence": _evidence_payload(evidence),
                }
            ),
            response_model=RevisedDraftOutput,
        )
        revision_run = _require_metadata(self._revision_llm, "revision")
        _validate_draft(
            revision_output.revised_draft,
            expected_question=cleaned_question,
            evidence=evidence,
        )
        _validate_revision(original_draft, revision_output)
        revision = RevisionArtifact(
            revised_draft=revision_output.revised_draft,
            changes=revision_output.changes,
            llm_run=revision_run,
        )
        final_qa = await self._review(revision.revised_draft, evidence)
        return SynthesisQAResult(
            original_draft=original_draft,
            original_qa=original_qa,
            revision=revision,
            final_draft=revision.revised_draft,
            final_qa=final_qa,
            synthesis_run=synthesis_run,
        )

    async def _review(
        self,
        draft: SynthesisDraft,
        evidence: list[EvidenceRecord],
    ) -> QAReport:
        reviewer_output = await self._qa_llm.generate_structured(
            system_prompt=load_versioned_prompt("qa/v1.md"),
            user_prompt=_untrusted_prompt(
                {
                    "draft": draft.model_dump(mode="json"),
                    "evidence": _evidence_payload(evidence),
                }
            ),
            response_model=QAReviewerOutput,
        )
        llm_run = _require_metadata(self._qa_llm, "QA")
        _validate_reviewer_output(draft, reviewer_output.assessments, evidence)
        deterministic = run_deterministic_checks(draft, evidence)
        return QAReport(
            assessments=reviewer_output.assessments,
            untracked_claims=reviewer_output.untracked_claims,
            deterministic_findings=deterministic,
            status=derive_qa_status(
                reviewer_output.assessments,
                deterministic,
                reviewer_output.untracked_claims,
            ),
            llm_run=llm_run,
            reviewed_draft_sha256=reviewed_draft_sha256(draft),
        )


def _validate_draft(
    draft: SynthesisDraft,
    *,
    expected_question: str,
    evidence: list[EvidenceRecord],
) -> None:
    if draft.clinical_question != expected_question:
        raise ValueError("Synthesis must preserve the original clinical question")
    trial_ids = {record.nct_id for record in evidence if isinstance(record, ClinicalTrialRecord)}
    unknown_trials = set(draft.relevant_trial_ids) - trial_ids
    if unknown_trials:
        raise ValueError(
            "Synthesis relevant_trial_ids contain sources absent from retrieved evidence: "
            + ", ".join(sorted(unknown_trials))
        )


def _validate_reviewer_output(
    draft: SynthesisDraft,
    assessments: tuple[ClaimAssessment, ...],
    evidence: list[EvidenceRecord],
) -> None:
    expected_claim_ids = {claim.claim_id for claim in draft.claims}
    assessment_ids = [item.claim_id for item in assessments]
    if len(assessment_ids) != len(set(assessment_ids)):
        raise ValueError("QA reviewer returned duplicate claim assessments")
    if set(assessment_ids) != expected_claim_ids:
        missing = sorted(expected_claim_ids - set(assessment_ids))
        unknown = sorted(set(assessment_ids) - expected_claim_ids)
        raise ValueError(
            f"QA reviewer claim coverage mismatch; missing={missing}, unknown={unknown}"
        )
    evidence_by_id = {record.record_id: record for record in evidence}
    for assessment in assessments:
        unknown_sources = set(assessment.source_ids) - evidence_by_id.keys()
        if unknown_sources:
            raise ValueError(
                f"QA reviewer cited unknown sources for {assessment.claim_id}: "
                + ", ".join(sorted(unknown_sources))
            )
        for passage in assessment.supporting_passages:
            if passage.source_id not in assessment.source_ids:
                raise ValueError(
                    f"QA passage source is not linked by assessment {assessment.claim_id}"
                )
            source_text = _normalize_text(evidence_record_text(evidence_by_id[passage.source_id]))
            if _normalize_text(passage.text) not in source_text:
                raise ValueError(f"QA reviewer passage was not found in source {passage.source_id}")


def _validate_revision(
    original: SynthesisDraft,
    output: RevisedDraftOutput,
) -> None:
    original_claims = {claim.claim_id: claim for claim in original.claims}
    revised_claims = {claim.claim_id: claim for claim in output.revised_draft.claims}
    changed_ids = {
        claim_id
        for claim_id in original_claims.keys() | revised_claims.keys()
        if original_claims.get(claim_id) != revised_claims.get(claim_id)
    }
    declared_ids = [change.claim_id for change in output.changes]
    if len(declared_ids) != len(set(declared_ids)):
        raise ValueError("Revision output contains duplicate change records")
    if set(declared_ids) != changed_ids:
        raise ValueError(
            "Revision change log does not match changed claims; "
            f"actual={sorted(changed_ids)}, declared={sorted(declared_ids)}"
        )
    changes_by_id = {change.claim_id: change for change in output.changes}
    for claim_id in changed_ids:
        _validate_change(
            changes_by_id[claim_id],
            original_claims.get(claim_id),
            revised_claims.get(claim_id),
        )


def _validate_change(
    change: RevisionChange,
    original: Claim | None,
    revised: Claim | None,
) -> None:
    expected_original_text = original.text if original else None
    expected_revised_text = revised.text if revised else None
    expected_original_sources = original.linked_source_ids if original else ()
    expected_revised_sources = revised.linked_source_ids if revised else ()
    if (
        change.original_text != expected_original_text
        or change.revised_text != expected_revised_text
        or change.original_source_ids != expected_original_sources
        or change.revised_source_ids != expected_revised_sources
    ):
        raise ValueError(f"Revision change record does not match claim {change.claim_id}")


def _evidence_payload(evidence: list[EvidenceRecord]) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for record in evidence:
        serialized = record.model_dump(mode="json")
        serialized["source_id"] = record.record_id
        serialized["source_type"] = (
            "pubmed" if isinstance(record, PubMedRecord) else "clinicaltrials.gov"
        )
        payload.append(serialized)
    return payload


def _qa_payload(report: QAReport) -> MappingABC[str, object]:
    return {
        "assessments": [item.model_dump(mode="json") for item in report.assessments],
        "untracked_claims": [item.model_dump(mode="json") for item in report.untracked_claims],
        "deterministic_findings": [
            item.model_dump(mode="json") for item in report.deterministic_findings
        ],
        "status": report.status.value,
    }


def _untrusted_prompt(payload: MappingABC[str, object]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return f"<untrusted_input_json>\n{serialized}\n</untrusted_input_json>"


def _require_metadata(provider: LLMProvider, stage: str) -> LLMRunMetadata:
    metadata = provider.last_run_metadata
    if metadata is None:
        raise RuntimeError(f"{stage} LLM provider did not expose run metadata")
    return metadata


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().split())
