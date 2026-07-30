"""Deterministic, inspectable evidence-query builders."""

from datetime import date

from evidenceforge.models.evidence import EvidenceQuery, EvidenceSource
from evidenceforge.models.pico import PICO


def build_pubmed_query(
    pico: PICO,
    *,
    condition_term: str | None = None,
    intervention_term: str | None = None,
    comparator_term: str | None = None,
    outcome_terms: tuple[str, ...] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    publication_types: tuple[str, ...] = (),
    page_size: int = 20,
) -> EvidenceQuery:
    """Build a PubMed ESearch expression without hidden source calls."""

    condition = pico.condition if condition_term is None else condition_term
    intervention = pico.intervention if intervention_term is None else intervention_term
    comparator = pico.comparator if comparator_term is None else comparator_term
    outcomes = tuple(pico.outcomes) if outcome_terms is None else outcome_terms
    concepts = [
        _pubmed_phrase(condition),
        _pubmed_phrase(intervention),
        _pubmed_phrase(comparator),
    ]
    if outcomes:
        concepts.append(f"({' OR '.join(_pubmed_phrase(item) for item in outcomes)})")
    filters: dict[str, str] = {}
    if (date_from is None) != (date_to is None):
        raise ValueError("date_from and date_to must be provided together")
    if date_from is not None and date_to is not None:
        start = date_from.strftime("%Y/%m/%d")
        end = date_to.strftime("%Y/%m/%d")
        if start > end:
            raise ValueError("date_from must not be after date_to")
        filters["publication_date"] = f"{start}:{end}"
        concepts.append(f"{start}:{end}[Date - Publication]")
    normalized_types = tuple(_clean_term(item) for item in publication_types)
    if normalized_types:
        filters["publication_types"] = ",".join(normalized_types)
        concepts.append(
            f"({' OR '.join(f'{item}[Publication Type]' for item in normalized_types)})"
        )
    return EvidenceQuery(
        source=EvidenceSource.PUBMED,
        query=" AND ".join(concepts),
        filters=filters,
        page_size=page_size,
    )


def build_trial_query(
    pico: PICO,
    *,
    condition_term: str | None = None,
    intervention_term: str | None = None,
    comparator_term: str | None = None,
    direct_comparison: bool = False,
    overall_status: tuple[str, ...] = (),
    page_size: int = 20,
) -> EvidenceQuery:
    """Build a ClinicalTrials.gov v2 query.term expression."""

    condition = _clean_term(pico.condition if condition_term is None else condition_term)
    intervention = _clean_term(
        pico.intervention if intervention_term is None else intervention_term
    )
    comparator = _clean_term(pico.comparator if comparator_term is None else comparator_term)
    if direct_comparison:
        query_text = (
            f'AREA[ConditionSearch]"{condition}" '
            f'AND AREA[InterventionName]"{intervention}" '
            f'AND AREA[InterventionName]"{comparator}"'
        )
    else:
        query_text = f'"{condition}" AND ("{intervention}" OR "{comparator}")'
    filters: dict[str, str] = {}
    cleaned_statuses = tuple(_clean_term(item).upper().replace(" ", "_") for item in overall_status)
    if cleaned_statuses:
        filters["overall_status"] = ",".join(cleaned_statuses)
    return EvidenceQuery(
        source=EvidenceSource.CLINICAL_TRIALS,
        query=query_text,
        filters=filters,
        page_size=page_size,
    )


def _pubmed_phrase(value: str) -> str:
    return f'"{_clean_term(value)}"[Title/Abstract]'


def _clean_term(value: str) -> str:
    cleaned = " ".join(value.replace('"', " ").split())
    if not cleaned:
        raise ValueError("Evidence query terms must not be blank")
    return cleaned
