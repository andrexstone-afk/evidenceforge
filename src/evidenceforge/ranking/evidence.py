"""Deterministic evidence ranking with inspectable component scores."""

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from evidenceforge.models.evidence import ClinicalTrialRecord, EvidenceSource, PubMedRecord
from evidenceforge.models.pico import PICO

ComponentScore = Annotated[float, Field(ge=-10.0, le=10.0)]


class RankingComponents(BaseModel):
    """Individual ranking factors; these are heuristics, not a validated hierarchy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pico_overlap: ComponentScore
    design_or_status: ComponentScore
    recency: ComponentScore
    evidence_availability: ComponentScore
    safety_penalty: ComponentScore = 0.0

    @property
    def total(self) -> float:
        """Return the unrounded sum used for ordering."""

        return sum(
            (
                self.pico_overlap,
                self.design_or_status,
                self.recency,
                self.evidence_availability,
                self.safety_penalty,
            )
        )


class RankedEvidence(BaseModel):
    """Stable record identity plus transparent heuristic ranking factors."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    record_id: str
    source: EvidenceSource
    score: float
    components: RankingComponents
    method: str = "evidenceforge-heuristic-v1-not-clinically-validated"


def rank_evidence(
    records: list[PubMedRecord | ClinicalTrialRecord],
    pico: PICO,
    *,
    current_year: int,
) -> list[RankedEvidence]:
    """Rank records deterministically while exposing every contributing factor."""

    if current_year < 1900 or current_year > 9999:
        raise ValueError("current_year must be between 1900 and 9999")
    ranked = [_rank_record(record, pico, current_year=current_year) for record in records]
    return sorted(ranked, key=lambda item: (-item.score, item.source, item.record_id))


def _rank_record(
    record: PubMedRecord | ClinicalTrialRecord,
    pico: PICO,
    *,
    current_year: int,
) -> RankedEvidence:
    target_tokens = _tokens(
        " ".join(
            (
                pico.population,
                pico.condition,
                pico.intervention,
                pico.comparator,
                *pico.outcomes,
            )
        )
    )
    if isinstance(record, PubMedRecord):
        record_text = " ".join(
            (
                record.title,
                record.abstract or "",
                " ".join(record.mesh_terms),
                " ".join(record.publication_types),
            )
        )
        publication_types = {item.lower() for item in record.publication_types}
        if "randomized controlled trial" in publication_types:
            design_or_status = 2.0
        elif "systematic review" in publication_types or "meta-analysis" in publication_types:
            design_or_status = 1.5
        else:
            design_or_status = 0.5
        publication_year = _leading_year(record.publication_date)
        availability = 1.0 if record.abstract else 0.0
        safety_penalty = -10.0 if record.is_retracted else 0.0
        source = EvidenceSource.PUBMED
    else:
        record_text = " ".join(
            (
                record.title,
                record.summary or "",
                " ".join(record.conditions),
                " ".join(record.interventions),
                " ".join(record.outcomes),
            )
        )
        status = record.overall_status.upper()
        design_or_status = (
            1.5
            if status == "COMPLETED"
            else 1.0
            if status in {"RECRUITING", "ACTIVE_NOT_RECRUITING"}
            else 0.0
        )
        publication_year = _leading_year(record.last_update_date)
        availability = 1.0 if record.has_results else 0.25
        safety_penalty = 0.0
        source = EvidenceSource.CLINICAL_TRIALS
    overlap = len(target_tokens & _tokens(record_text)) / max(len(target_tokens), 1)
    components = RankingComponents(
        pico_overlap=round(overlap * 5.0, 4),
        design_or_status=design_or_status,
        recency=_recency_score(publication_year, current_year),
        evidence_availability=availability,
        safety_penalty=safety_penalty,
    )
    return RankedEvidence(
        record_id=record.record_id,
        source=source,
        score=round(components.total, 4),
        components=components,
    )


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _leading_year(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.match(r"^(\d{4})", value)
    return int(match.group(1)) if match else None


def _recency_score(record_year: int | None, current_year: int) -> float:
    if record_year is None:
        return 0.0
    age = max(current_year - record_year, 0)
    return round(max(0.0, 2.0 - age * 0.1), 4)
