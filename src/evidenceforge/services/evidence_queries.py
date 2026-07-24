"""Deterministic, inspectable evidence-query builders."""

from datetime import date

from evidenceforge.models.evidence import EvidenceQuery, EvidenceSource
from evidenceforge.models.pico import PICO


def build_pubmed_query(
    pico: PICO,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    publication_types: tuple[str, ...] = (),
    page_size: int = 20,
) -> EvidenceQuery:
    """Build a PubMed ESearch expression without hidden source calls."""

    concepts = [
        _pubmed_phrase(pico.condition),
        _pubmed_phrase(pico.intervention),
        _pubmed_phrase(pico.comparator),
    ]
    if pico.outcomes:
        concepts.append(f"({' OR '.join(_pubmed_phrase(item) for item in pico.outcomes)})")
    filters: dict[str, str] = {}
    if date_from or date_to:
        start = (date_from or date(1900, 1, 1)).strftime("%Y/%m/%d")
        end = (date_to or date.today()).strftime("%Y/%m/%d")
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
    overall_status: tuple[str, ...] = (),
    page_size: int = 20,
) -> EvidenceQuery:
    """Build a ClinicalTrials.gov v2 query.term expression."""

    intervention_group = " OR ".join(
        (f'"{_clean_term(pico.intervention)}"', f'"{_clean_term(pico.comparator)}"')
    )
    filters: dict[str, str] = {}
    cleaned_statuses = tuple(_clean_term(item).upper().replace(" ", "_") for item in overall_status)
    if cleaned_statuses:
        filters["overall_status"] = ",".join(cleaned_statuses)
    return EvidenceQuery(
        source=EvidenceSource.CLINICAL_TRIALS,
        query=f'"{_clean_term(pico.condition)}" AND ({intervention_group})',
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
