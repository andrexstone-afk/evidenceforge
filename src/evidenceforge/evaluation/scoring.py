"""Deterministic scoring for aligned EvidenceForge evaluation runs."""

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Iterable

from evidenceforge.models.evaluation import (
    EvaluationMetrics,
    EvaluationReport,
    EvaluationRun,
    MeanMetric,
    PICOReference,
    RatioMetric,
    RetrievalPrecisionMetric,
)
from evidenceforge.models.pico import PICO
from evidenceforge.models.qa import SupportClassification

_SUPPORTED = {
    SupportClassification.SUPPORTED,
    SupportClassification.PARTIALLY_SUPPORTED,
}
_UNSUPPORTED = {
    SupportClassification.UNSUPPORTED,
    SupportClassification.CONTRADICTED,
    SupportClassification.UNABLE_TO_VERIFY,
}


def score_evaluation(run: EvaluationRun, *, tool_version: str) -> EvaluationReport:
    """Score one validated run without network or model calls."""

    pico_matches = 0
    pico_total = 0
    normalized_matches = 0
    mapping_total = 0
    top1_matches = 0
    top3_matches = 0
    valid_citations = 0
    citation_total = 0
    support_true_positives = 0
    support_predictions = 0
    unsupported_claims = 0
    claim_total = 0
    numeric_consistent = 0
    numeric_total = 0
    retrieval_counts = {cutoff: [0, 0] for cutoff in run.retrieval_cutoffs}

    for case in run.cases:
        matches, total = _score_pico(case.reference_pico, case.predicted_pico)
        pico_matches += matches
        pico_total += total

        for mapping in case.mappings:
            mapping_total += 1
            normalized_matches += _normalize(mapping.expected_normalized_term) == _normalize(
                mapping.predicted_normalized_term
            )
            accepted = set(mapping.accepted_codes)
            top1_matches += mapping.ranked_codes[0] in accepted
            top3_matches += bool(accepted.intersection(mapping.ranked_codes[:3]))

        relevant = set(case.retrieval.relevant_source_ids)
        retrieved = case.retrieval.retrieved_source_ids
        retrieved_set = set(retrieved)
        for cutoff in run.retrieval_cutoffs:
            selected = retrieved[:cutoff]
            retrieval_counts[cutoff][0] += sum(item in relevant for item in selected)
            retrieval_counts[cutoff][1] += len(selected)

        for claim in case.claims:
            claim_total += 1
            unsupported_claims += claim.reviewer_classification in _UNSUPPORTED
            if claim.system_classification in _SUPPORTED:
                support_predictions += 1
                support_true_positives += claim.reviewer_classification in _SUPPORTED
            for source_id in claim.cited_source_ids:
                citation_total += 1
                valid_citations += source_id in retrieved_set
            if claim.numeric_consistent is not None:
                numeric_total += 1
                numeric_consistent += claim.numeric_consistent

    latencies = [case.latency_ms for case in run.cases]
    costs = [case.estimated_cost_usd for case in run.cases]
    metrics = EvaluationMetrics(
        pico_component_accuracy=_ratio(
            pico_matches,
            pico_total,
            "Exact normalized agreement across population, condition, intervention, "
            "comparator, outcomes, time horizon, and study context.",
        ),
        entity_normalization_accuracy=_ratio(
            normalized_matches,
            mapping_total,
            "Exact normalized-term agreement for reviewer-aligned terminology entities.",
        ),
        mapping_top1_accuracy=_ratio(
            top1_matches,
            mapping_total,
            "Mappings whose first predicted service code is reviewer accepted.",
        ),
        mapping_top3_recall=_ratio(
            top3_matches,
            mapping_total,
            "Mappings with any reviewer-accepted service code in the first three predictions.",
        ),
        retrieval_precision=tuple(
            RetrievalPrecisionMetric(
                cutoff=cutoff,
                metric=_ratio(
                    retrieval_counts[cutoff][0],
                    retrieval_counts[cutoff][1],
                    definition=(
                        f"Micro-averaged relevant records among up to the first {cutoff} "
                        "retrieved records per case."
                    ),
                ),
            )
            for cutoff in run.retrieval_cutoffs
        ),
        citation_validity=_ratio(
            valid_citations,
            citation_total,
            "Claim citations whose identifiers occur in the case's retrieved evidence set.",
        ),
        claim_support_precision=_ratio(
            support_true_positives,
            support_predictions,
            "System-supported or partially supported claims independently classified the same.",
        ),
        unsupported_claim_rate=_ratio(
            unsupported_claims,
            claim_total,
            "Claims independently classified unsupported, contradicted, or unable to verify.",
        ),
        numeric_consistency=_ratio(
            numeric_consistent,
            numeric_total,
            "Reviewer-assessed numeric claims whose values and context are consistent.",
        ),
        mean_latency=_mean(
            latencies,
            unit="ms",
            definition="Arithmetic mean end-to-end latency per evaluated brief.",
        ),
        p95_latency=MeanMetric(
            value=_nearest_rank_percentile(latencies, 0.95),
            count=len(latencies),
            unit="ms",
            definition="Nearest-rank 95th percentile end-to-end latency per evaluated brief.",
        ),
        mean_estimated_cost=_mean(
            costs,
            unit="USD/brief",
            definition=f"Arithmetic mean estimated cost per brief; basis: {run.cost_basis}",
        ),
    )
    return EvaluationReport(
        input_sha256=_run_sha256(run),
        dataset_name=run.dataset_name,
        dataset_version=run.dataset_version,
        review_status=run.review_status,
        review_method=run.review_method,
        reviewer_count=run.reviewer_count,
        reviewed_at=run.reviewed_at,
        case_count=len(run.cases),
        limitations=run.limitations,
        system_name=run.system_name,
        system_version=run.system_version,
        model_versions=dict(run.model_versions),
        prompt_versions=dict(run.prompt_versions),
        cost_basis=run.cost_basis,
        run_executed_at=run.executed_at,
        tool_version=tool_version,
        metrics=metrics,
    )


def _score_pico(reference: PICOReference, prediction: PICO) -> tuple[int, int]:
    scalar_pairs = (
        (reference.population, prediction.population),
        (reference.condition, prediction.condition),
        (reference.intervention, prediction.intervention),
        (reference.comparator, prediction.comparator),
        (reference.time_horizon, prediction.time_horizon),
        (reference.study_context, prediction.study_context),
    )
    matches = sum(
        _normalize_optional(expected) == _normalize_optional(actual)
        for expected, actual in scalar_pairs
    )
    expected_outcomes = Counter(_normalize(item) for item in reference.outcomes)
    actual_outcomes = Counter(_normalize(item) for item in prediction.outcomes)
    matches += int(expected_outcomes == actual_outcomes)
    return matches, 7


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _normalize_optional(value: str | None) -> str | None:
    return _normalize(value) if value is not None else None


def _ratio(numerator: int, denominator: int, definition: str) -> RatioMetric:
    value = numerator / denominator if denominator else None
    return RatioMetric(
        value=value,
        numerator=numerator,
        denominator=denominator,
        definition=definition,
    )


def _mean(values: Iterable[float], *, unit: str, definition: str) -> MeanMetric:
    observations = list(values)
    return MeanMetric(
        value=math.fsum(observations) / len(observations) if observations else None,
        count=len(observations),
        unit=unit,
        definition=definition,
    )


def _nearest_rank_percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = math.ceil(percentile * len(ordered))
    return ordered[rank - 1]


def _run_sha256(run: EvaluationRun) -> str:
    canonical = json.dumps(
        run.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
