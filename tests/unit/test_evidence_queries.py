from datetime import date

import pytest

from evidenceforge.models.evidence import EvidenceSource
from evidenceforge.models.pico import PICO
from evidenceforge.services.evidence_queries import build_pubmed_query, build_trial_query


@pytest.fixture
def pico() -> PICO:
    return PICO(
        population="adults with neovascular AMD",
        condition="neovascular age-related macular degeneration",
        intervention="aflibercept",
        comparator="ranibizumab",
        outcomes=["visual acuity", "adverse events"],
        normalized_search_terms=["neovascular AMD", "aflibercept", "ranibizumab"],
    )


def test_pubmed_query_is_reproducible_and_inspectable(pico: PICO) -> None:
    query = build_pubmed_query(
        pico,
        date_from=date(2020, 1, 1),
        date_to=date(2025, 12, 31),
        publication_types=("Randomized Controlled Trial",),
        page_size=25,
    )

    assert query.source is EvidenceSource.PUBMED
    assert '"aflibercept"[Title/Abstract]' in query.query
    assert "2020/01/01:2025/12/31[Date - Publication]" in query.query
    assert query.filters == {
        "publication_date": "2020/01/01:2025/12/31",
        "publication_types": "Randomized Controlled Trial",
    }
    assert query.page_size == 25


def test_pubmed_query_rejects_inverted_date_range(pico: PICO) -> None:
    with pytest.raises(ValueError, match="date_from"):
        build_pubmed_query(
            pico,
            date_from=date(2025, 1, 1),
            date_to=date(2024, 1, 1),
        )


def test_pubmed_query_requires_both_date_boundaries(pico: PICO) -> None:
    with pytest.raises(ValueError, match="provided together"):
        build_pubmed_query(pico, date_from=date(2020, 1, 1))


def test_query_builder_removes_embedded_quotes(pico: PICO) -> None:
    modified = pico.model_copy(update={"intervention": 'aflibercept" OR "anything'})

    query = build_pubmed_query(modified)

    assert 'aflibercept OR anything"[Title/Abstract]' in query.query
    assert '"aflibercept" OR "anything"' not in query.query


def test_trial_query_records_status_filters(pico: PICO) -> None:
    query = build_trial_query(
        pico,
        overall_status=("recruiting", "active not recruiting"),
    )

    assert query.source is EvidenceSource.CLINICAL_TRIALS
    assert query.query == (
        '"neovascular age-related macular degeneration" AND ("aflibercept" OR "ranibizumab")'
    )
    assert query.filters["overall_status"] == "RECRUITING,ACTIVE_NOT_RECRUITING"


def test_cardiometabolic_search_overrides_preserve_coding_condition() -> None:
    pico = PICO(
        population="Adults with type 2 diabetes mellitus without complications",
        condition="type 2 diabetes mellitus without complications",
        intervention="semaglutide",
        comparator="empagliflozin",
        outcomes=["glycated hemoglobin (HbA1c)"],
        normalized_search_terms=["type 2 diabetes mellitus", "semaglutide", "empagliflozin"],
    )

    pubmed_query = build_pubmed_query(
        pico,
        condition_term="type 2 diabetes mellitus",
        outcome_terms=("HbA1c",),
    )
    trial_query = build_trial_query(
        pico,
        condition_term="type 2 diabetes mellitus",
        direct_comparison=True,
    )

    assert pico.condition == "type 2 diabetes mellitus without complications"
    assert pubmed_query.query == (
        '"type 2 diabetes mellitus"[Title/Abstract] '
        'AND "semaglutide"[Title/Abstract] '
        'AND "empagliflozin"[Title/Abstract] '
        'AND ("HbA1c"[Title/Abstract])'
    )
    assert trial_query.query == (
        'AREA[ConditionSearch]"type 2 diabetes mellitus" '
        'AND AREA[InterventionName]"semaglutide" '
        'AND AREA[InterventionName]"empagliflozin"'
    )


def test_rare_disease_search_overrides_preserve_coding_terms() -> None:
    pico = PICO(
        population="Adults with myasthenia gravis without acute exacerbation",
        condition="myasthenia gravis without acute exacerbation",
        intervention="efgartigimod alfa",
        comparator="Rozanolixizumab",
        outcomes=["activities of daily living"],
        normalized_search_terms=[
            "myasthenia gravis",
            "efgartigimod",
            "rozanolixizumab",
        ],
    )

    pubmed_query = build_pubmed_query(
        pico,
        condition_term="myasthenia gravis",
        intervention_term="efgartigimod",
        comparator_term="rozanolixizumab",
        outcome_terms=("MG-ADL",),
    )
    trial_query = build_trial_query(
        pico,
        condition_term="myasthenia gravis",
        intervention_term="efgartigimod",
        comparator_term="rozanolixizumab",
    )

    assert pico.condition == "myasthenia gravis without acute exacerbation"
    assert pico.intervention == "efgartigimod alfa"
    assert pico.comparator == "Rozanolixizumab"
    assert pubmed_query.query == (
        '"myasthenia gravis"[Title/Abstract] '
        'AND "efgartigimod"[Title/Abstract] '
        'AND "rozanolixizumab"[Title/Abstract] '
        'AND ("MG-ADL"[Title/Abstract])'
    )
    assert trial_query.query == ('"myasthenia gravis" AND ("efgartigimod" OR "rozanolixizumab")')
