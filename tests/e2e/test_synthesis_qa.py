import json

import pytest
from pydantic import ValidationError

from evidenceforge.llm import ScriptedLLMProvider
from evidenceforge.llm.mock import amd_pico
from evidenceforge.models.qa import (
    ClaimAssessment,
    ConsistencyAssessment,
    EvidencePassage,
    QAReviewerOutput,
    QASeverity,
    QAStatus,
    RevisionChange,
    SupportClassification,
    SynthesisQAResult,
    UntrackedClaimFinding,
)
from evidenceforge.pipelines import SynthesisQAPipeline
from tests.fixtures.qa import (
    INJECTION_TEXT,
    QUESTION,
    final_qa_output,
    initial_qa_output,
    original_draft,
    retrieval_fixture,
    revision_output,
    supported_assessment,
)


@pytest.mark.asyncio
async def test_synthesis_qa_revision_and_recheck_end_to_end() -> None:
    synthesis = ScriptedLLMProvider(
        [original_draft()],
        model_name="synthetic-synthesis-v1",
    )
    qa = ScriptedLLMProvider(
        [initial_qa_output(), final_qa_output()],
        model_name="synthetic-independent-qa-v1",
    )
    revision = ScriptedLLMProvider(
        [revision_output()],
        model_name="synthetic-revision-v1",
    )
    pipeline = SynthesisQAPipeline(
        synthesis_llm=synthesis,
        qa_llm=qa,
        revision_llm=revision,
    )

    result = await pipeline.run(
        question=QUESTION,
        pico=amd_pico(),
        mappings=[],
        retrieval=retrieval_fixture(),
    )

    assert result.original_qa.status is QAStatus.BLOCKED
    assert result.revision is not None
    assert result.original_draft.claims[1].text.endswith("200 participants.")
    assert result.final_draft.claims[1].text.endswith("120 participants.")
    assert result.final_qa.status is QAStatus.PASS
    assert result.revision.changes[0].claim_id == "CLM-0002"
    assert len(qa.calls) == 2

    for call in (*synthesis.calls, *qa.calls, *revision.calls):
        assert INJECTION_TEXT not in call.system_prompt
        assert INJECTION_TEXT in call.user_prompt

    assert set(_prompt_payload(qa.calls[0].user_prompt)) == {"draft", "evidence"}
    assert set(_prompt_payload(qa.calls[1].user_prompt)) == {"draft", "evidence"}


@pytest.mark.asyncio
async def test_final_qa_report_cannot_be_reused_for_a_different_draft() -> None:
    pipeline = SynthesisQAPipeline(
        synthesis_llm=ScriptedLLMProvider(
            [original_draft()],
            model_name="synthetic-synthesis-v1",
        ),
        qa_llm=ScriptedLLMProvider(
            [initial_qa_output(), final_qa_output()],
            model_name="synthetic-independent-qa-v1",
        ),
        revision_llm=ScriptedLLMProvider(
            [revision_output()],
            model_name="synthetic-revision-v1",
        ),
    )
    result = await pipeline.run(
        question=QUESTION,
        pico=amd_pico(),
        mappings=[],
        retrieval=retrieval_fixture(),
    )
    payload = result.model_dump(mode="json")
    payload["final_qa"] = payload["original_qa"]

    with pytest.raises(ValidationError, match="Final QA report does not match"):
        SynthesisQAResult.model_validate(payload)


@pytest.mark.asyncio
async def test_final_high_severity_issue_remains_blocked() -> None:
    unresolved_final = QAReviewerOutput(
        assessments=[
            supported_assessment(
                claim_id="CLM-0001",
                source_id="11111111",
                passage="At 52 weeks, visual acuity improved in both synthetic groups.",
            ),
            ClaimAssessment(
                claim_id="CLM-0002",
                classification=SupportClassification.UNABLE_TO_VERIFY,
                severity=QASeverity.HIGH,
                explanation="The reviewer could not verify this claim.",
                consistency=ConsistencyAssessment(numeric=None),
                recommended_correction="Do not present the claim as verified.",
            ),
        ]
    )
    pipeline = SynthesisQAPipeline(
        synthesis_llm=ScriptedLLMProvider(
            [original_draft()],
            model_name="synthetic-synthesis-v1",
        ),
        qa_llm=ScriptedLLMProvider(
            [initial_qa_output(), unresolved_final],
            model_name="synthetic-independent-qa-v1",
        ),
        revision_llm=ScriptedLLMProvider(
            [revision_output()],
            model_name="synthetic-revision-v1",
        ),
    )

    result = await pipeline.run(
        question=QUESTION,
        pico=amd_pico(),
        mappings=[],
        retrieval=retrieval_fixture(),
    )

    assert result.final_qa.status is QAStatus.BLOCKED


@pytest.mark.asyncio
async def test_qa_must_assess_every_claim_exactly_once() -> None:
    incomplete = QAReviewerOutput(
        assessments=[
            supported_assessment(
                claim_id="CLM-0001",
                source_id="11111111",
                passage="At 52 weeks, visual acuity improved in both synthetic groups.",
            )
        ]
    )
    pipeline = SynthesisQAPipeline(
        synthesis_llm=ScriptedLLMProvider(
            [original_draft()],
            model_name="synthetic-synthesis-v1",
        ),
        qa_llm=ScriptedLLMProvider(
            [incomplete],
            model_name="synthetic-independent-qa-v1",
        ),
        revision_llm=ScriptedLLMProvider(
            [revision_output()],
            model_name="synthetic-revision-v1",
        ),
    )

    with pytest.raises(ValueError, match="claim coverage mismatch"):
        await pipeline.run(
            question=QUESTION,
            pico=amd_pico(),
            mappings=[],
            retrieval=retrieval_fixture(),
        )


@pytest.mark.asyncio
async def test_qa_rejects_fabricated_reviewer_source() -> None:
    fabricated = QAReviewerOutput(
        assessments=[
            supported_assessment(
                claim_id="CLM-0001",
                source_id="99999999",
                passage="A fabricated supporting passage.",
            ),
            supported_assessment(
                claim_id="CLM-0002",
                source_id="NCT00000001",
                passage="The synthetic trial enrolled 120 participants.",
            ),
        ]
    )
    pipeline = SynthesisQAPipeline(
        synthesis_llm=ScriptedLLMProvider(
            [original_draft()],
            model_name="synthetic-synthesis-v1",
        ),
        qa_llm=ScriptedLLMProvider(
            [fabricated],
            model_name="synthetic-independent-qa-v1",
        ),
        revision_llm=ScriptedLLMProvider(
            [revision_output()],
            model_name="synthetic-revision-v1",
        ),
    )

    with pytest.raises(ValueError, match="cited unknown sources"):
        await pipeline.run(
            question=QUESTION,
            pico=amd_pico(),
            mappings=[],
            retrieval=retrieval_fixture(),
        )


@pytest.mark.asyncio
async def test_qa_rejects_fabricated_reviewer_passage() -> None:
    fabricated = QAReviewerOutput(
        assessments=[
            ClaimAssessment(
                claim_id="CLM-0001",
                classification=SupportClassification.SUPPORTED,
                severity=QASeverity.LOW,
                explanation="Synthetic fixture.",
                source_ids=["11111111"],
                supporting_passages=[
                    EvidencePassage(
                        source_id="11111111",
                        text="This fabricated passage is absent from the source.",
                    )
                ],
                consistency=ConsistencyAssessment(),
            ),
            supported_assessment(
                claim_id="CLM-0002",
                source_id="NCT00000001",
                passage="The synthetic trial enrolled 120 participants.",
            ),
        ]
    )
    pipeline = SynthesisQAPipeline(
        synthesis_llm=ScriptedLLMProvider(
            [original_draft()],
            model_name="synthetic-synthesis-v1",
        ),
        qa_llm=ScriptedLLMProvider(
            [fabricated],
            model_name="synthetic-independent-qa-v1",
        ),
        revision_llm=ScriptedLLMProvider(
            [revision_output()],
            model_name="synthetic-revision-v1",
        ),
    )

    with pytest.raises(ValueError, match="passage was not found"):
        await pipeline.run(
            question=QUESTION,
            pico=amd_pico(),
            mappings=[],
            retrieval=retrieval_fixture(),
        )


@pytest.mark.asyncio
async def test_high_untracked_narrative_claim_triggers_revision() -> None:
    untracked = initial_qa_output().model_copy(
        update={
            "untracked_claims": (
                UntrackedClaimFinding(
                    text="An uncaptured efficacy statement.",
                    location="executive_answer",
                    severity=QASeverity.HIGH,
                    explanation="The narrative statement has no explicit claim record.",
                    recommended_correction="Add and assess the claim or remove it.",
                ),
            )
        }
    )
    pipeline = SynthesisQAPipeline(
        synthesis_llm=ScriptedLLMProvider(
            [original_draft()],
            model_name="synthetic-synthesis-v1",
        ),
        qa_llm=ScriptedLLMProvider(
            [untracked, final_qa_output()],
            model_name="synthetic-independent-qa-v1",
        ),
        revision_llm=ScriptedLLMProvider(
            [revision_output()],
            model_name="synthetic-revision-v1",
        ),
    )

    result = await pipeline.run(
        question=QUESTION,
        pico=amd_pico(),
        mappings=[],
        retrieval=retrieval_fixture(),
    )

    assert result.original_qa.status is QAStatus.BLOCKED
    assert result.revision is not None


@pytest.mark.asyncio
async def test_revision_change_log_must_match_actual_claim_change() -> None:
    dishonest_revision = revision_output().model_copy(
        update={
            "changes": (
                RevisionChange(
                    claim_id="CLM-0002",
                    original_text="The synthetic trial enrolled 999 participants.",
                    revised_text="The synthetic trial enrolled 120 participants.",
                    original_source_ids=["NCT00000001"],
                    revised_source_ids=["NCT00000001"],
                    reason="Synthetic correction.",
                ),
            )
        }
    )
    pipeline = SynthesisQAPipeline(
        synthesis_llm=ScriptedLLMProvider(
            [original_draft()],
            model_name="synthetic-synthesis-v1",
        ),
        qa_llm=ScriptedLLMProvider(
            [initial_qa_output()],
            model_name="synthetic-independent-qa-v1",
        ),
        revision_llm=ScriptedLLMProvider(
            [dishonest_revision],
            model_name="synthetic-revision-v1",
        ),
    )

    with pytest.raises(ValueError, match="does not match claim"):
        await pipeline.run(
            question=QUESTION,
            pico=amd_pico(),
            mappings=[],
            retrieval=retrieval_fixture(),
        )


def _prompt_payload(prompt: str) -> dict[str, object]:
    prefix = "<untrusted_input_json>\n"
    suffix = "\n</untrusted_input_json>"
    assert prompt.startswith(prefix)
    assert prompt.endswith(suffix)
    value = json.loads(prompt.removeprefix(prefix).removesuffix(suffix))
    assert isinstance(value, dict)
    return value
