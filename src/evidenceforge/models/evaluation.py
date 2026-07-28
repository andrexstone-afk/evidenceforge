"""Validated inputs and outputs for reproducible clinical-pipeline evaluation."""

import math
import re
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from evidenceforge.core.safety import looks_like_phi
from evidenceforge.models.ontology import OntologyName
from evidenceforge.models.pico import PICO
from evidenceforge.models.qa import SupportClassification

EvaluationText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
EvaluationQuestion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=10)]
SOURCE_ID_PATTERN = r"^(?:\d{1,10}|NCT\d{8})$"


class DatasetReviewStatus(StrEnum):
    """Human-review maturity of an evaluation dataset."""

    DRAFT = "draft"
    SYNTHETIC_TEST = "synthetic_test"
    PHYSICIAN_REVIEWED = "physician_reviewed"


class PICOReference(BaseModel):
    """Reviewer-authored PICO components used for exact normalized scoring."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    population: EvaluationText
    condition: EvaluationText
    intervention: EvaluationText
    comparator: EvaluationText
    outcomes: tuple[EvaluationText, ...] = Field(min_length=1)
    time_horizon: EvaluationText | None = None
    study_context: EvaluationText | None = None

    @model_validator(mode="after")
    def validate_outcomes(self) -> Self:
        """Reject duplicate gold outcomes after case and whitespace normalization."""

        normalized = [" ".join(item.split()).casefold() for item in self.outcomes]
        if len(normalized) != len(set(normalized)):
            raise ValueError("Reference PICO outcomes must be unique")
        return self


class MappingEvaluation(BaseModel):
    """One terminology prediction aligned to reviewer-accepted service codes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    term: EvaluationText
    ontology: OntologyName
    expected_normalized_term: EvaluationText
    predicted_normalized_term: EvaluationText
    accepted_codes: tuple[str, ...] = Field(min_length=1)
    ranked_codes: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_codes(self) -> Self:
        """Require unique, ontology-shaped reference and prediction codes."""

        for label, values in (
            ("accepted_codes", self.accepted_codes),
            ("ranked_codes", self.ranked_codes),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} must contain unique codes")
            for code in values:
                if self.ontology is OntologyName.ICD10CM:
                    valid = re.fullmatch(r"[A-Z]\d[A-Z0-9](?:\.[A-Z0-9]{1,4})?", code)
                else:
                    valid = re.fullmatch(r"\d+", code)
                if valid is None:
                    raise ValueError(f"{label} contains an invalid {self.ontology.value} code")
        return self


class RetrievalEvaluation(BaseModel):
    """Ranked retrieved identifiers and reviewer-relevant identifiers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    relevant_source_ids: tuple[str, ...] = ()
    retrieved_source_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_source_ids(self) -> Self:
        """Reject duplicate or malformed PubMed and ClinicalTrials.gov identifiers."""

        for label, values in (
            ("relevant_source_ids", self.relevant_source_ids),
            ("retrieved_source_ids", self.retrieved_source_ids),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} must contain unique identifiers")
            if any(re.fullmatch(SOURCE_ID_PATTERN, value) is None for value in values):
                raise ValueError(f"{label} contains an invalid source identifier")
        return self


class ClaimEvaluation(BaseModel):
    """One system claim aligned to an independent reviewer classification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(pattern=r"^CLM-\d{4}$")
    system_classification: SupportClassification
    reviewer_classification: SupportClassification
    cited_source_ids: tuple[str, ...] = ()
    numeric_consistent: bool | None = None

    @model_validator(mode="after")
    def validate_citations(self) -> Self:
        """Require unique, canonical citation identifiers."""

        if len(self.cited_source_ids) != len(set(self.cited_source_ids)):
            raise ValueError("cited_source_ids must contain unique identifiers")
        if any(re.fullmatch(SOURCE_ID_PATTERN, value) is None for value in self.cited_source_ids):
            raise ValueError("cited_source_ids contains an invalid source identifier")
        return self


class EvaluationCase(BaseModel):
    """Reference annotations and aligned system output for one question."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    clinical_domain: EvaluationText
    question: EvaluationQuestion
    reference_pico: PICOReference
    predicted_pico: PICO
    mappings: tuple[MappingEvaluation, ...] = ()
    retrieval: RetrievalEvaluation
    claims: tuple[ClaimEvaluation, ...] = ()
    latency_ms: float = Field(ge=0, allow_inf_nan=False)
    estimated_cost_usd: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_case(self) -> Self:
        """Reject PHI-like questions and duplicate aligned entities or claims."""

        if looks_like_phi(self.question):
            raise ValueError("Evaluation questions must not contain patient identifiers")
        mapping_keys = [(item.ontology, item.term.casefold()) for item in self.mappings]
        if len(mapping_keys) != len(set(mapping_keys)):
            raise ValueError("Evaluation mappings must be unique by ontology and term")
        claim_ids = [item.claim_id for item in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("Evaluation claim IDs must be unique within a case")
        return self


class EvaluationRun(BaseModel):
    """Complete, provenance-bearing input to the deterministic metric engine."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    dataset_name: EvaluationText
    dataset_version: EvaluationText
    review_status: DatasetReviewStatus
    review_method: EvaluationText
    reviewer_count: int = Field(ge=0)
    reviewed_at: date | None = None
    limitations: tuple[EvaluationText, ...] = Field(min_length=1)
    system_name: EvaluationText
    system_version: EvaluationText
    model_versions: dict[EvaluationText, EvaluationText] = Field(min_length=1)
    prompt_versions: dict[EvaluationText, EvaluationText] = Field(min_length=1)
    cost_basis: EvaluationText
    retrieval_cutoffs: tuple[int, ...] = (5, 10)
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    cases: tuple[EvaluationCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_run_provenance(self) -> Self:
        """Require honest review provenance, unique cases, and stable cutoffs."""

        if self.review_status is DatasetReviewStatus.PHYSICIAN_REVIEWED and (
            self.reviewer_count < 1 or self.reviewed_at is None
        ):
            raise ValueError("Physician-reviewed datasets require a reviewer and review date")
        if self.review_status is DatasetReviewStatus.SYNTHETIC_TEST and (
            self.reviewer_count or self.reviewed_at is not None
        ):
            raise ValueError("Synthetic-test datasets cannot claim human review provenance")
        if self.executed_at.tzinfo is None or self.executed_at.utcoffset() is None:
            raise ValueError("executed_at must include a timezone")
        if self.reviewed_at is not None and self.reviewed_at > self.executed_at.date():
            raise ValueError("reviewed_at cannot be after executed_at")
        if (
            not self.retrieval_cutoffs
            or any(value < 1 for value in self.retrieval_cutoffs)
            or tuple(sorted(set(self.retrieval_cutoffs))) != self.retrieval_cutoffs
        ):
            raise ValueError("retrieval_cutoffs must be unique positive values in ascending order")
        case_ids = [item.case_id for item in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Evaluation case IDs must be unique")
        return self


class RatioMetric(BaseModel):
    """Auditable ratio with an explicit undefined state for zero denominators."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)
    definition: EvaluationText

    @model_validator(mode="after")
    def validate_ratio(self) -> Self:
        """Keep the displayed value consistent with its counts."""

        if self.denominator == 0:
            if self.value is not None or self.numerator != 0:
                raise ValueError("Zero-denominator ratios must be undefined with numerator zero")
        elif self.value is None or not math.isclose(
            self.value,
            self.numerator / self.denominator,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError("Ratio value must equal numerator / denominator")
        return self


class MeanMetric(BaseModel):
    """Auditable non-negative mean and its observation count."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    count: int = Field(ge=0)
    unit: EvaluationText
    definition: EvaluationText

    @model_validator(mode="after")
    def validate_mean(self) -> Self:
        """Require undefined means only when no observations exist."""

        if (self.count == 0) is not (self.value is None):
            raise ValueError("Mean must be undefined exactly when count is zero")
        return self


class RetrievalPrecisionMetric(BaseModel):
    """Precision result for one configured retrieval cutoff."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    cutoff: int = Field(ge=1)
    metric: RatioMetric


class EvaluationMetrics(BaseModel):
    """Complete Phase 6 metric taxonomy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pico_component_accuracy: RatioMetric
    entity_normalization_accuracy: RatioMetric
    mapping_top1_accuracy: RatioMetric
    mapping_top3_recall: RatioMetric
    retrieval_precision: tuple[RetrievalPrecisionMetric, ...]
    citation_validity: RatioMetric
    claim_support_precision: RatioMetric
    unsupported_claim_rate: RatioMetric
    numeric_consistency: RatioMetric
    mean_latency: MeanMetric
    p95_latency: MeanMetric
    mean_estimated_cost: MeanMetric


class EvaluationReport(BaseModel):
    """Versioned, reproducible evaluation report with honest maturity labels."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    scoring_version: Literal["1.0"] = "1.0"
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset_name: EvaluationText
    dataset_version: EvaluationText
    review_status: DatasetReviewStatus
    review_method: EvaluationText
    reviewer_count: int = Field(ge=0)
    reviewed_at: date | None = None
    case_count: int = Field(ge=1)
    limitations: tuple[EvaluationText, ...]
    system_name: EvaluationText
    system_version: EvaluationText
    model_versions: dict[str, str]
    prompt_versions: dict[str, str]
    cost_basis: EvaluationText
    run_executed_at: datetime
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tool_version: EvaluationText
    metrics: EvaluationMetrics
    disclaimer: str = (
        "Evaluation results describe only this dataset and scoring definition; "
        "they do not establish clinical validity or medical-device performance."
    )
