from pathlib import Path

import pytest
from pydantic import ValidationError

from evidenceforge.models.evaluation import BenchmarkQuestionSet, QuestionSetReviewStatus

QUESTION_SET_PATH = (
    Path(__file__).parents[2] / "examples" / "evaluation" / "benchmark-question-set-v0.1.json"
)
REPOSITORY_ROOT = Path(__file__).parents[2]


def test_starter_question_set_is_explicitly_unreviewed() -> None:
    question_set = BenchmarkQuestionSet.model_validate_json(
        QUESTION_SET_PATH.read_text(encoding="utf-8")
    )

    assert question_set.review_status is QuestionSetReviewStatus.DRAFT
    assert question_set.reviewer_count == 0
    assert question_set.reviewed_at is None
    assert question_set.annotation_status == "no_gold_labels"
    assert len(question_set.questions) == 3
    assert {question.evidence_density_expectation for question in question_set.questions} == {
        "unknown"
    }
    assert all(
        (REPOSITORY_ROOT / question.coded_brief_path).is_file()
        for question in question_set.questions
    )


def test_draft_question_set_cannot_claim_a_reviewer() -> None:
    payload = _question_set_payload()
    payload["reviewer_count"] = 1

    with pytest.raises(ValidationError, match="cannot claim physician review"):
        BenchmarkQuestionSet.model_validate(payload)


def test_physician_reviewed_question_set_requires_provenance() -> None:
    payload = _question_set_payload()
    payload["review_status"] = "physician_reviewed"

    with pytest.raises(ValidationError, match="require a reviewer and review date"):
        BenchmarkQuestionSet.model_validate(payload)


def test_question_set_rejects_duplicate_cases_and_phi() -> None:
    payload = _question_set_payload()
    duplicate = dict(payload["questions"][0])
    payload["questions"] = (*payload["questions"], duplicate)

    with pytest.raises(ValidationError, match="case IDs must be unique"):
        BenchmarkQuestionSet.model_validate(payload)

    payload = _question_set_payload()
    payload["questions"][0]["question"] = "Compare treatments for patient MRN 123456."

    with pytest.raises(ValidationError, match="must not contain patient identifiers"):
        BenchmarkQuestionSet.model_validate(payload)


def _question_set_payload() -> dict[str, object]:
    return BenchmarkQuestionSet.model_validate_json(
        QUESTION_SET_PATH.read_text(encoding="utf-8")
    ).model_dump(mode="python")
