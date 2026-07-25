"""Validated schemas crossing the Phase 3-to-persistence boundary."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from evidenceforge.models.evidence import ClinicalTrialRecord, EvidenceSource, PubMedRecord
from evidenceforge.models.ontology import Mapping
from evidenceforge.models.pico import PICO
from evidenceforge.models.qa import (
    EvidencePassage,
    QAReport,
    SynthesisDraft,
    SynthesisQAResult,
)
from evidenceforge.pipelines.evidence_retrieval import EvidenceRetrievalResult
from evidenceforge.qa import evidence_record_text, run_deterministic_checks


class BriefPersistenceInput(BaseModel):
    """Complete validated data required to persist one evidence brief."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    question: str = Field(min_length=10)
    pico: PICO
    mappings: tuple[Mapping, ...] = ()
    retrieval: EvidenceRetrievalResult
    synthesis_qa: SynthesisQAResult
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_question_identity(self) -> "BriefPersistenceInput":
        """Prevent a persisted question from diverging from its draft artifacts."""

        if self.question != self.synthesis_qa.original_draft.clinical_question:
            raise ValueError("Persisted question must match the original synthesis draft")
        if self.question != self.synthesis_qa.final_draft.clinical_question:
            raise ValueError("Persisted question must match the final synthesis draft")
        if self.retrieval.pubmed.metadata.source is not EvidenceSource.PUBMED:
            raise ValueError("PubMed page metadata must identify the PubMed source")
        if self.retrieval.clinical_trials.metadata.source is not EvidenceSource.CLINICAL_TRIALS:
            raise ValueError("Clinical trial page metadata must identify ClinicalTrials.gov")
        evidence: list[PubMedRecord | ClinicalTrialRecord] = [
            *self.retrieval.pubmed.records,
            *self.retrieval.clinical_trials.records,
        ]
        if not evidence:
            raise ValueError("Persisted synthesis requires retrieved evidence")
        evidence_by_id = {record.record_id: record for record in evidence}
        if len(evidence_by_id) != len(evidence):
            raise ValueError("Retrieved evidence identifiers must be unique")
        ranking_ids = [item.record_id for item in self.retrieval.ranking]
        if len(ranking_ids) != len(set(ranking_ids)):
            raise ValueError("Evidence ranking identifiers must be unique")
        if unknown_ranked := set(ranking_ids) - evidence_by_id.keys():
            raise ValueError(
                "Evidence ranking references unknown records: " + ", ".join(sorted(unknown_ranked))
            )
        _validate_draft_evidence(
            self.synthesis_qa.original_draft,
            self.synthesis_qa.original_qa,
            evidence_by_id,
            evidence,
        )
        _validate_draft_evidence(
            self.synthesis_qa.final_draft,
            self.synthesis_qa.final_qa,
            evidence_by_id,
            evidence,
        )
        return self


class StoredBrief(BaseModel):
    """Stable database identity plus the reconstructed validated aggregate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    brief_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    aggregate: BriefPersistenceInput


def _validate_draft_evidence(
    draft: SynthesisDraft,
    report: QAReport,
    evidence_by_id: dict[str, PubMedRecord | ClinicalTrialRecord],
    evidence: list[PubMedRecord | ClinicalTrialRecord],
) -> None:
    trial_ids = {record.nct_id for record in evidence if isinstance(record, ClinicalTrialRecord)}
    if unknown_trials := set(draft.relevant_trial_ids) - trial_ids:
        raise ValueError(
            "Draft references unknown trial records: " + ", ".join(sorted(unknown_trials))
        )
    for claim in draft.claims:
        _validate_source_ids(claim.linked_source_ids, evidence_by_id, claim.claim_id)
        _validate_passages(claim.supporting_passages, evidence_by_id, claim.claim_id)
    for assessment in report.assessments:
        _validate_source_ids(assessment.source_ids, evidence_by_id, assessment.claim_id)
        _validate_passages(
            assessment.supporting_passages,
            evidence_by_id,
            assessment.claim_id,
        )
    deterministic = tuple(run_deterministic_checks(draft, evidence))
    if deterministic != report.deterministic_findings:
        raise ValueError("Persisted deterministic QA findings do not match recomputation")


def _validate_source_ids(
    source_ids: tuple[str, ...],
    evidence_by_id: dict[str, PubMedRecord | ClinicalTrialRecord],
    claim_id: str,
) -> None:
    if unknown := set(source_ids) - evidence_by_id.keys():
        raise ValueError(
            f"{claim_id} references evidence absent from retrieval: " + ", ".join(sorted(unknown))
        )


def _validate_passages(
    passages: tuple[EvidencePassage, ...],
    evidence_by_id: dict[str, PubMedRecord | ClinicalTrialRecord],
    claim_id: str,
) -> None:
    for value in passages:
        source_id = value.source_id
        passage_text = value.text
        if source_id not in evidence_by_id:
            raise ValueError(f"{claim_id} passage references unknown source {source_id}")
        source_text = " ".join(evidence_record_text(evidence_by_id[source_id]).lower().split())
        normalized_passage = " ".join(passage_text.lower().split())
        if normalized_passage not in source_text:
            raise ValueError(f"{claim_id} passage is absent from source {source_id}")
