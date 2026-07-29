import pytest
from pydantic import ValidationError

from evidenceforge.evaluation import score_evaluation
from evidenceforge.models.evaluation import (
    DatasetReviewStatus,
    EvaluationReport,
    EvaluationRun,
)
from tests.fixtures.evaluation import synthetic_evaluation_run


def test_evaluation_scores_all_phase_6_metrics_deterministically() -> None:
    report = score_evaluation(synthetic_evaluation_run(), tool_version="test")
    metrics = report.metrics

    assert metrics.pico_component_accuracy.value == 1
    assert metrics.entity_normalization_accuracy.value == 1
    assert metrics.mapping_top1_accuracy.value == 0.5
    assert metrics.mapping_top3_recall.value == 1
    assert [item.metric.value for item in metrics.retrieval_precision] == [1, 2 / 3]
    assert metrics.citation_validity.value == 0.5
    assert metrics.claim_support_precision.value == 0.5
    assert metrics.unsupported_claim_rate.value == 0.5
    assert metrics.numeric_consistency.value == 0.5
    assert metrics.mean_latency.value == 100
    assert metrics.p95_latency.value == 100
    assert metrics.mean_estimated_cost.value == 0.1
    assert report.case_count == 1
    assert report.review_status is DatasetReviewStatus.SYNTHETIC_TEST


def test_evaluation_preserves_undefined_zero_denominators() -> None:
    report = score_evaluation(
        synthetic_evaluation_run(include_observations=False),
        tool_version="test",
    )
    metrics = report.metrics

    assert metrics.mapping_top1_accuracy.value is None
    assert metrics.mapping_top1_accuracy.denominator == 0
    assert all(item.metric.value is None for item in metrics.retrieval_precision)
    assert metrics.citation_validity.value is None
    assert metrics.claim_support_precision.value is None
    assert metrics.unsupported_claim_rate.value is None
    assert metrics.numeric_consistency.value is None


def test_evaluation_input_hash_is_stable() -> None:
    run = synthetic_evaluation_run()

    first = score_evaluation(run, tool_version="test")
    second = score_evaluation(run, tool_version="test")

    assert first.input_sha256 == second.input_sha256


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    (
        ("limitations", ()),
        ("model_versions", {}),
        ("prompt_versions", {}),
        ("disclaimer", "Evaluation is clinically validated."),
    ),
)
def test_evaluation_report_rejects_weakened_provenance(
    field: str,
    invalid_value: object,
) -> None:
    payload = score_evaluation(
        synthetic_evaluation_run(),
        tool_version="test",
    ).model_dump(mode="python")
    payload[field] = invalid_value

    with pytest.raises(ValidationError):
        EvaluationReport.model_validate(payload)


def test_duplicate_predicted_outcomes_reduce_pico_accuracy() -> None:
    payload = synthetic_evaluation_run().model_dump(mode="python")
    payload["cases"][0]["predicted_pico"]["outcomes"].append("visual acuity")
    run = EvaluationRun.model_validate(payload)

    report = score_evaluation(run, tool_version="test")

    assert report.metrics.pico_component_accuracy.numerator == 6
    assert report.metrics.pico_component_accuracy.denominator == 7


def test_physician_review_label_requires_review_provenance() -> None:
    payload = synthetic_evaluation_run().model_dump(mode="python")
    payload.update(
        review_status=DatasetReviewStatus.PHYSICIAN_REVIEWED,
        reviewer_count=0,
        reviewed_at=None,
    )

    with pytest.raises(ValidationError, match="require a reviewer and review date"):
        EvaluationRun.model_validate(payload)


def test_synthetic_label_rejects_claimed_human_reviewers() -> None:
    payload = synthetic_evaluation_run().model_dump(mode="python")
    payload["reviewer_count"] = 1

    with pytest.raises(ValidationError, match="cannot claim human review provenance"):
        EvaluationRun.model_validate(payload)


def test_evaluation_run_requires_timezone_aware_execution() -> None:
    payload = synthetic_evaluation_run().model_dump(mode="python")
    payload["executed_at"] = payload["executed_at"].replace(tzinfo=None)

    with pytest.raises(ValidationError, match="must include a timezone"):
        EvaluationRun.model_validate(payload)


def test_evaluation_question_rejects_phi_like_identifiers() -> None:
    payload = synthetic_evaluation_run().model_dump(mode="python")
    payload["cases"][0]["question"] = "Compare interventions for patient MRN 123456."

    with pytest.raises(ValidationError, match="must not contain patient identifiers"):
        EvaluationRun.model_validate(payload)
