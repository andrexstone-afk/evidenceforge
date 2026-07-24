from evidenceforge.models.evidence import ClinicalTrialRecord, PubMedRecord
from evidenceforge.models.pico import PICO
from evidenceforge.ranking import rank_evidence


def _pico() -> PICO:
    return PICO(
        population="adults with neovascular AMD",
        condition="neovascular age-related macular degeneration",
        intervention="aflibercept",
        comparator="ranibizumab",
        outcomes=["visual acuity"],
        normalized_search_terms=["neovascular AMD", "aflibercept", "ranibizumab"],
    )


def test_ranking_exposes_components_and_penalizes_retractions() -> None:
    current = PubMedRecord(
        pmid="11111111",
        title="Aflibercept versus ranibizumab for neovascular macular degeneration",
        abstract="Visual acuity was measured in adults.",
        journal="Synthetic Journal",
        publication_date="2025-01-01",
        publication_types=["Randomized Controlled Trial"],
        url="https://pubmed.ncbi.nlm.nih.gov/11111111/",
    )
    retracted = current.model_copy(
        update={
            "pmid": "22222222",
            "is_retracted": True,
            "url": "https://pubmed.ncbi.nlm.nih.gov/22222222/",
        }
    )

    ranked = rank_evidence([retracted, current], _pico(), current_year=2026)

    assert [item.record_id for item in ranked] == ["11111111", "22222222"]
    assert ranked[0].components.pico_overlap > 0
    assert ranked[1].components.safety_penalty == -10
    assert "not-clinically-validated" in ranked[0].method


def test_trial_ranking_records_status_and_results_factors() -> None:
    trial = ClinicalTrialRecord(
        nct_id="NCT00000001",
        title="Aflibercept and ranibizumab in neovascular macular degeneration",
        conditions=["Neovascular age-related macular degeneration"],
        interventions=["Aflibercept", "Ranibizumab"],
        outcomes=["Visual acuity"],
        study_type="INTERVENTIONAL",
        overall_status="COMPLETED",
        last_update_date="2025-01-01",
        has_results=True,
        url="https://clinicaltrials.gov/study/NCT00000001",
    )

    ranked = rank_evidence([trial], _pico(), current_year=2026)

    assert ranked[0].components.design_or_status == 1.5
    assert ranked[0].components.evidence_availability == 1.0
