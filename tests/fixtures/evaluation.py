"""Explicitly synthetic evaluation inputs with no clinical-performance meaning."""

from datetime import UTC, datetime

from evidenceforge.models.evaluation import (
    ClaimEvaluation,
    DatasetReviewStatus,
    EvaluationCase,
    EvaluationRun,
    MappingEvaluation,
    PICOReference,
    RetrievalEvaluation,
)
from evidenceforge.models.ontology import OntologyName
from evidenceforge.models.pico import PICO
from evidenceforge.models.qa import SupportClassification


def synthetic_evaluation_run(*, include_observations: bool = True) -> EvaluationRun:
    """Return a deterministic run built only from existing synthetic test fixtures."""

    mappings: tuple[MappingEvaluation, ...] = ()
    claims: tuple[ClaimEvaluation, ...] = ()
    retrieval = RetrievalEvaluation()
    if include_observations:
        mappings = (
            MappingEvaluation(
                term="neovascular age-related macular degeneration",
                ontology=OntologyName.ICD10CM,
                expected_normalized_term="neovascular age-related macular degeneration",
                predicted_normalized_term="Neovascular   age-related macular degeneration",
                accepted_codes=("H35.3291",),
                ranked_codes=("H35.3211", "H35.3291"),
            ),
            MappingEvaluation(
                term="aflibercept",
                ontology=OntologyName.RXNORM,
                expected_normalized_term="aflibercept",
                predicted_normalized_term="AFLIBERCEPT",
                accepted_codes=("1232150",),
                ranked_codes=("1232150",),
            ),
        )
        retrieval = RetrievalEvaluation(
            relevant_source_ids=("11111111", "NCT00000001"),
            retrieved_source_ids=("11111111", "22222222", "NCT00000001"),
        )
        claims = (
            ClaimEvaluation(
                claim_id="CLM-0001",
                system_classification=SupportClassification.SUPPORTED,
                reviewer_classification=SupportClassification.SUPPORTED,
                cited_source_ids=("11111111",),
                numeric_consistent=True,
            ),
            ClaimEvaluation(
                claim_id="CLM-0002",
                system_classification=SupportClassification.SUPPORTED,
                reviewer_classification=SupportClassification.UNSUPPORTED,
                cited_source_ids=("33333333",),
                numeric_consistent=False,
            ),
        )

    reference = PICOReference(
        population="Adults with neovascular age-related macular degeneration",
        condition="neovascular age-related macular degeneration",
        intervention="aflibercept",
        comparator="ranibizumab",
        outcomes=("visual acuity",),
        time_horizon=None,
        study_context=None,
    )
    prediction = PICO(
        population=reference.population,
        condition=reference.condition,
        intervention=reference.intervention,
        comparator=reference.comparator,
        outcomes=list(reference.outcomes),
        time_horizon=reference.time_horizon,
        study_context=reference.study_context,
        missing_information=["time horizon"],
        normalized_search_terms=[
            "neovascular age-related macular degeneration",
            "aflibercept",
            "ranibizumab",
        ],
    )
    return EvaluationRun(
        dataset_name="synthetic-evaluation-fixture",
        dataset_version="1.0",
        review_status=DatasetReviewStatus.SYNTHETIC_TEST,
        review_method="Deterministic test alignment; not clinical review.",
        reviewer_count=0,
        limitations=("Synthetic records cannot support clinical performance claims.",),
        system_name="EvidenceForge synthetic fixture",
        system_version="test",
        model_versions={"pico": "deterministic-test"},
        prompt_versions={"pico": "pico-v1"},
        cost_basis="Synthetic fixed values for arithmetic testing only.",
        retrieval_cutoffs=(1, 3),
        executed_at=datetime(2026, 7, 28, tzinfo=UTC),
        cases=(
            EvaluationCase(
                case_id="synthetic-amd",
                clinical_domain="synthetic ophthalmology",
                question=(
                    "In adults with neovascular age-related macular degeneration, "
                    "how does aflibercept compare with ranibizumab for visual acuity?"
                ),
                reference_pico=reference,
                predicted_pico=prediction,
                mappings=mappings,
                retrieval=retrieval,
                claims=claims,
                latency_ms=100,
                estimated_cost_usd=0.1,
            ),
        ),
    )
