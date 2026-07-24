import pytest
from pydantic import ValidationError

from evidenceforge.models.llm import LLMRunMetadata
from evidenceforge.models.qa import (
    ClaimAssessment,
    ConsistencyAssessment,
    QAReport,
    QASeverity,
    QAStatus,
    RevisionChange,
    SupportClassification,
    SynthesisDraft,
    UntrackedClaimFinding,
    derive_qa_status,
    reviewed_draft_sha256,
)
from tests.fixtures.qa import initial_qa_output, original_draft


def _metadata() -> LLMRunMetadata:
    return LLMRunMetadata(provider="scripted", model="qa-fixture", latency_ms=0)


def test_high_severity_assessment_cannot_auto_pass() -> None:
    assessments = initial_qa_output().assessments

    with pytest.raises(ValidationError, match="QA status must be blocked"):
        QAReport(
            assessments=assessments,
            status=QAStatus.PASS,
            llm_run=_metadata(),
            reviewed_draft_sha256=reviewed_draft_sha256(original_draft()),
        )


def test_high_untracked_narrative_claim_blocks_pass() -> None:
    baseline_assessments = [initial_qa_output().assessments[0]]
    untracked = UntrackedClaimFinding(
        text="An uncaptured efficacy statement.",
        location="executive_answer",
        severity=QASeverity.HIGH,
        explanation="The statement is not represented in the claims collection.",
        recommended_correction="Add and assess the claim or remove the statement.",
    )

    assert derive_qa_status(baseline_assessments, []) is QAStatus.PASS
    status = derive_qa_status(baseline_assessments, [], [untracked])

    assert status is QAStatus.BLOCKED


def test_qa_report_rejects_empty_assessments() -> None:
    with pytest.raises(ValidationError) as error:
        QAReport(
            assessments=[],
            status=QAStatus.PASS,
            llm_run=_metadata(),
            reviewed_draft_sha256=reviewed_draft_sha256(original_draft()),
        )

    assert any(
        detail["loc"] == ("assessments",) and detail["type"] == "too_short"
        for detail in error.value.errors()
    )


def test_qa_artifact_collections_are_deeply_immutable() -> None:
    claim = original_draft().claims[0]

    assert isinstance(claim.linked_source_ids, tuple)
    with pytest.raises(AttributeError):
        claim.linked_source_ids.append("99999999")  # type: ignore[attr-defined]


def test_relevant_trial_ids_require_complete_nct_format() -> None:
    payload = original_draft().model_dump(mode="json")
    payload["relevant_trial_ids"] = ["NCTinvalid"]

    with pytest.raises(ValidationError, match="NCT identifiers"):
        SynthesisDraft.model_validate(payload)


def test_contradiction_flag_and_classification_must_agree() -> None:
    with pytest.raises(ValidationError, match="contradiction=true"):
        ClaimAssessment(
            claim_id="CLM-0001",
            classification=SupportClassification.UNSUPPORTED,
            contradiction=True,
            severity=QASeverity.HIGH,
            explanation="Synthetic contradiction.",
            consistency=ConsistencyAssessment(),
        )


def test_revision_change_can_record_citation_only_change() -> None:
    change = RevisionChange(
        claim_id="CLM-0001",
        original_text="Unchanged text.",
        revised_text="Unchanged text.",
        original_source_ids=["11111111"],
        revised_source_ids=["22222222"],
        reason="Corrected the source link.",
    )

    assert change.original_text == change.revised_text
