"""Deterministic table projections for the Streamlit interface."""

from typing import Any

from evidenceforge.db.schemas import BriefPersistenceInput
from evidenceforge.models.evidence import ClinicalTrialRecord, PubMedRecord
from evidenceforge.models.qa import ClaimAssessment, QAReport


def mapping_rows(aggregate: BriefPersistenceInput) -> list[dict[str, Any]]:
    """Return one safe display row per ontology mapping."""

    return [
        {
            "term": item.original_term,
            "normalized": item.normalized_term,
            "ontology": item.ontology.value,
            "selected_code": item.selected.code if item.selected else None,
            "selected_label": item.selected.preferred_label if item.selected else None,
            "method": item.match_method,
            "human_review": item.human_review_required,
        }
        for item in aggregate.mappings
    ]


def ranking_rows(aggregate: BriefPersistenceInput) -> list[dict[str, Any]]:
    """Return transparent ranking components without implying clinical validation."""

    return [
        {
            "record_id": item.record_id,
            "source": item.source.value,
            "score": item.score,
            "PICO overlap": item.components.pico_overlap,
            "design/status": item.components.design_or_status,
            "recency": item.components.recency,
            "availability": item.components.evidence_availability,
            "safety penalty": item.components.safety_penalty,
            "method": item.method,
        }
        for item in aggregate.retrieval.ranking
    ]


def evidence_by_id(
    aggregate: BriefPersistenceInput,
) -> dict[str, PubMedRecord | ClinicalTrialRecord]:
    """Index validated evidence records by their source identifier."""

    records: list[PubMedRecord | ClinicalTrialRecord] = [
        *aggregate.retrieval.pubmed.records,
        *aggregate.retrieval.clinical_trials.records,
    ]
    return {record.record_id: record for record in records}


def assessment_by_claim(report: QAReport) -> dict[str, ClaimAssessment]:
    """Index final claim assessments for display beside their claims."""

    return {item.claim_id: item for item in report.assessments}
