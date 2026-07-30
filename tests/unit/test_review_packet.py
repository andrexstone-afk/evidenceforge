from datetime import date
from pathlib import Path

import pytest

from evidenceforge.evaluation import render_question_review_packet
from evidenceforge.models.evaluation import BenchmarkQuestionSet

QUESTION_SET_PATH = (
    Path(__file__).parents[2] / "examples" / "evaluation" / "benchmark-question-set-v0.1.json"
)
REVIEW_PACKET_PATH = (
    Path(__file__).parents[2]
    / "examples"
    / "evaluation"
    / "benchmark-question-review-packet-v0.1.md"
)


def test_review_packet_is_deterministic_and_contains_no_gold_labels() -> None:
    question_set = BenchmarkQuestionSet.model_validate_json(
        QUESTION_SET_PATH.read_text(encoding="utf-8")
    )

    first = render_question_review_packet(question_set)
    second = render_question_review_packet(question_set)

    assert first == second
    assert first.endswith("\n")
    assert "DRAFT — NOT PHYSICIAN REVIEWED" in first
    assert "review_scope: question_selection_only" in first
    assert "annotation_status: no_gold_labels" in first
    assert first.count("- [ ] Include as written") == 3
    assert first.count("- [ ] Revise") == 3
    assert first.count("- [ ] Exclude") == 3
    assert "Do not enter patient-identifiable information." in first
    assert "`examples/rare_disease/myasthenia-gravis-coded-brief.md`" in first
    assert "accepted_codes" not in first
    assert "relevant_source_ids" not in first


def test_committed_review_packet_matches_validated_source() -> None:
    question_set = BenchmarkQuestionSet.model_validate_json(
        QUESTION_SET_PATH.read_text(encoding="utf-8")
    )

    assert REVIEW_PACKET_PATH.read_text(encoding="utf-8") == render_question_review_packet(
        question_set
    )


def test_review_packet_escapes_untrusted_markdown_and_html() -> None:
    payload = BenchmarkQuestionSet.model_validate_json(
        QUESTION_SET_PATH.read_text(encoding="utf-8")
    ).model_dump(mode="python")
    payload["dataset_name"] = "Draft *set* <script>"
    question_set = BenchmarkQuestionSet.model_validate(payload)

    packet = render_question_review_packet(question_set)

    assert "Draft \\*set\\* &lt;script&gt;" in packet
    assert "<script>" not in packet


def test_review_packet_rejects_already_reviewed_question_set() -> None:
    payload = BenchmarkQuestionSet.model_validate_json(
        QUESTION_SET_PATH.read_text(encoding="utf-8")
    ).model_dump(mode="python")
    payload.update(
        {
            "review_status": "physician_reviewed",
            "reviewer_count": 1,
            "reviewed_at": date(2026, 7, 29),
        }
    )
    question_set = BenchmarkQuestionSet.model_validate(payload)

    with pytest.raises(ValueError, match="only be generated from draft"):
        render_question_review_packet(question_set)
