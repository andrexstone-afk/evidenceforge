"""Immutable synthesis, claim-level QA, and revision artifacts."""

import hashlib
import json
import re
from collections.abc import Sequence
from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from evidenceforge.models.llm import LLMRunMetadata

QAText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ClaimType(StrEnum):
    """Semantic claim categories used by deterministic and LLM QA."""

    EFFICACY = "efficacy"
    SAFETY = "safety"
    NUMERIC = "numeric"
    POPULATION = "population"
    INTERVENTION = "intervention"
    OUTCOME = "outcome"
    STUDY_DESIGN = "study_design"
    TRIAL_STATUS = "trial_status"
    LIMITATION = "limitation"
    OTHER = "other"


class SupportClassification(StrEnum):
    """Allowed claim-support classifications."""

    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    UNABLE_TO_VERIFY = "unable_to_verify"


class QASeverity(StrEnum):
    """QA severity levels in descending safety significance."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class QAStatus(StrEnum):
    """Aggregate state for one QA pass."""

    # This is a workflow status label, not a credential.
    PASS = "pass"  # nosec B105
    NEEDS_REVISION = "needs_revision"
    BLOCKED = "blocked"


class DeterministicRule(StrEnum):
    """Stable identifiers for deterministic consistency checks."""

    NO_LINKED_SOURCE = "no_linked_source"
    NO_SUPPORTING_PASSAGE = "no_supporting_passage"
    UNKNOWN_SOURCE = "unknown_source"
    PASSAGE_SOURCE_MISMATCH = "passage_source_mismatch"
    PASSAGE_NOT_FOUND = "passage_not_found"
    NUMERIC_MISMATCH = "numeric_mismatch"
    STUDY_DESIGN_MISMATCH = "study_design_mismatch"
    TRIAL_STATUS_MISMATCH = "trial_status_mismatch"
    OUTCOME_ROLE_MISMATCH = "outcome_role_mismatch"
    OBSERVATIONAL_CAUSAL_OVERSTATEMENT = "observational_causal_overstatement"


class EvidencePassage(BaseModel):
    """A source passage linked to one substantive claim."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(pattern=r"^(?:\d{1,10}|NCT\d{8})$")
    text: QAText
    location: str | None = None


class Claim(BaseModel):
    """One substantive draft claim and its proposed evidence links."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(pattern=r"^CLM-\d{4}$")
    text: QAText
    claim_type: ClaimType
    linked_source_ids: tuple[str, ...] = ()
    supporting_passages: tuple[EvidencePassage, ...] = ()

    @model_validator(mode="after")
    def validate_unique_links(self) -> Self:
        """Reject duplicate source links while allowing QA to detect unknown links."""

        if len(self.linked_source_ids) != len(set(self.linked_source_ids)):
            raise ValueError("Claim linked_source_ids must be unique")
        return self


class SynthesisDraft(BaseModel):
    """Structured synthesis draft whose substantive claims are explicit."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    clinical_question: QAText
    executive_answer: QAText
    evidence_summary: QAText
    claims: tuple[Claim, ...] = Field(min_length=1)
    relevant_trial_ids: tuple[str, ...] = ()
    limitations: tuple[QAText, ...] = ()
    uncertainties: tuple[QAText, ...] = ()
    evidence_gaps: tuple[QAText, ...] = ()
    clinical_interpretation: QAText
    prompt_version: str = "synthesis-v1"

    @model_validator(mode="after")
    def validate_unique_claims(self) -> Self:
        """Require stable, unique claim and trial identifiers."""

        claim_ids = [claim.claim_id for claim in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("Synthesis claim IDs must be unique")
        if len(self.relevant_trial_ids) != len(set(self.relevant_trial_ids)):
            raise ValueError("Relevant trial IDs must be unique")
        if any(re.fullmatch(r"NCT\d{8}", value) is None for value in self.relevant_trial_ids):
            raise ValueError("Relevant trial IDs must be NCT identifiers")
        return self


class ConsistencyAssessment(BaseModel):
    """Per-claim consistency dimensions checked by the independent reviewer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    numeric: bool | None = None
    population: bool | None = None
    intervention: bool | None = None
    outcome: bool | None = None
    time_horizon: bool | None = None
    notes: tuple[QAText, ...] = ()


class ClaimAssessment(BaseModel):
    """Independent LLM assessment for exactly one draft claim."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(pattern=r"^CLM-\d{4}$")
    classification: SupportClassification
    contradiction: bool = False
    severity: QASeverity
    explanation: QAText
    source_ids: tuple[str, ...] = ()
    supporting_passages: tuple[EvidencePassage, ...] = ()
    consistency: ConsistencyAssessment
    recommended_correction: str | None = None

    @model_validator(mode="after")
    def validate_support_semantics(self) -> Self:
        """Keep classification, contradiction, and cited support internally coherent."""

        if len(self.source_ids) != len(set(self.source_ids)):
            raise ValueError("Assessment source_ids must be unique")
        if self.classification is SupportClassification.CONTRADICTED and not self.contradiction:
            raise ValueError("Contradicted claims must set contradiction=true")
        if self.contradiction and self.classification is not SupportClassification.CONTRADICTED:
            raise ValueError("contradiction=true requires contradicted classification")
        if self.classification in {
            SupportClassification.SUPPORTED,
            SupportClassification.PARTIALLY_SUPPORTED,
        } and (not self.source_ids or not self.supporting_passages):
            raise ValueError("Supported assessments require sources and supporting passages")
        return self


class QAReviewerOutput(BaseModel):
    """Structured output expected from the independent QA model."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    assessments: tuple[ClaimAssessment, ...] = Field(min_length=1)
    untracked_claims: tuple["UntrackedClaimFinding", ...] = ()


class UntrackedClaimFinding(BaseModel):
    """Substantive narrative content absent from the explicit claim collection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: QAText
    location: QAText
    severity: QASeverity
    explanation: QAText
    recommended_correction: QAText


class DeterministicFinding(BaseModel):
    """One reproducible consistency-rule finding."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule: DeterministicRule
    claim_id: str = Field(pattern=r"^CLM-\d{4}$")
    severity: QASeverity
    message: QAText
    recommended_correction: QAText


class QAReport(BaseModel):
    """Combined independent and deterministic claim-level QA report."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    assessments: tuple[ClaimAssessment, ...] = Field(min_length=1)
    untracked_claims: tuple[UntrackedClaimFinding, ...] = ()
    deterministic_findings: tuple[DeterministicFinding, ...] = ()
    status: QAStatus
    llm_run: LLMRunMetadata
    reviewed_draft_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_version: str = "qa-v1"

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        """Ensure unresolved high-severity findings can never auto-pass."""

        expected = derive_qa_status(
            self.assessments,
            self.deterministic_findings,
            self.untracked_claims,
        )
        if self.status is not expected:
            raise ValueError(f"QA status must be {expected.value}")
        return self


class RevisionChange(BaseModel):
    """Auditable explanation of one claim addition, change, or removal."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(pattern=r"^CLM-\d{4}$")
    original_text: QAText | None = None
    revised_text: QAText | None = None
    original_source_ids: tuple[str, ...] = ()
    revised_source_ids: tuple[str, ...] = ()
    reason: QAText

    @model_validator(mode="after")
    def validate_change(self) -> Self:
        """Reject empty or no-op revision records."""

        if self.original_text is None and self.revised_text is None:
            raise ValueError("Revision change must include original or revised text")
        if (
            self.original_text == self.revised_text
            and self.original_source_ids == self.revised_source_ids
        ):
            raise ValueError("Revision change must alter the claim")
        if len(self.original_source_ids) != len(set(self.original_source_ids)):
            raise ValueError("Original revision source IDs must be unique")
        if len(self.revised_source_ids) != len(set(self.revised_source_ids)):
            raise ValueError("Revised revision source IDs must be unique")
        return self


class RevisedDraftOutput(BaseModel):
    """Structured output expected from the revision model."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    revised_draft: SynthesisDraft
    changes: tuple[RevisionChange, ...] = Field(min_length=1)


class RevisionArtifact(BaseModel):
    """Preserved revised draft, change log, and revision-run metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    revised_draft: SynthesisDraft
    changes: tuple[RevisionChange, ...] = Field(min_length=1)
    llm_run: LLMRunMetadata
    prompt_version: str = "revision-v1"


class SynthesisQAResult(BaseModel):
    """Complete original, QA, revision, and final-QA artifact graph."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    original_draft: SynthesisDraft
    original_qa: QAReport
    revision: RevisionArtifact | None = None
    final_draft: SynthesisDraft
    final_qa: QAReport
    synthesis_run: LLMRunMetadata
    disclaimer: str = (
        "Research evidence-synthesis prototype; not a medical device, not for diagnosis, "
        "and not individualized clinical advice."
    )

    @model_validator(mode="after")
    def validate_artifact_graph(self) -> Self:
        """Ensure the final draft is exactly the preserved revision or original."""

        expected = self.revision.revised_draft if self.revision else self.original_draft
        if self.final_draft != expected:
            raise ValueError("Final draft must match the preserved revision artifact")
        if self.revision is None and self.final_qa != self.original_qa:
            raise ValueError("Unrevised results must preserve the original QA report")
        _validate_report_matches_draft(self.original_qa, self.original_draft, "original")
        _validate_report_matches_draft(self.final_qa, self.final_draft, "final")
        return self


def derive_qa_status(
    assessments: Sequence[ClaimAssessment],
    findings: Sequence[DeterministicFinding],
    untracked_claims: Sequence[UntrackedClaimFinding] = (),
) -> QAStatus:
    """Derive aggregate status without relying on model judgment."""

    severities = (
        [item.severity for item in assessments]
        + [item.severity for item in findings]
        + [item.severity for item in untracked_claims]
    )
    if any(value in {QASeverity.CRITICAL, QASeverity.HIGH} for value in severities):
        return QAStatus.BLOCKED
    if (
        findings
        or untracked_claims
        or any(item.classification is not SupportClassification.SUPPORTED for item in assessments)
    ):
        return QAStatus.NEEDS_REVISION
    return QAStatus.PASS


def reviewed_draft_sha256(draft: SynthesisDraft) -> str:
    """Return a stable digest binding a QA report to the exact reviewed draft."""

    canonical = json.dumps(
        draft.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _validate_report_matches_draft(
    report: QAReport,
    draft: SynthesisDraft,
    label: str,
) -> None:
    if report.reviewed_draft_sha256 != reviewed_draft_sha256(draft):
        raise ValueError(f"{label.capitalize()} QA report does not match its reviewed draft")
    claim_ids = [claim.claim_id for claim in draft.claims]
    assessment_ids = [assessment.claim_id for assessment in report.assessments]
    if len(assessment_ids) != len(set(assessment_ids)) or set(assessment_ids) != set(claim_ids):
        raise ValueError(
            f"{label.capitalize()} QA report must assess every draft claim exactly once"
        )
