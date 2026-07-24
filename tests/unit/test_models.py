import pytest
from pydantic import ValidationError

from evidenceforge.models import PICO, ClinicalTrialRecord, PubMedRecord


@pytest.mark.parametrize(
    "overrides",
    [
        {"population": "   "},
        {"outcomes": ["visual acuity", " "]},
        {"normalized_search_terms": [" "]},
    ],
)
def test_pico_rejects_blank_values(overrides: dict[str, object]) -> None:
    values: dict[str, object] = {
        "population": "Adults with neovascular AMD",
        "condition": "neovascular AMD",
        "intervention": "aflibercept",
        "comparator": "ranibizumab",
        "outcomes": ["visual acuity"],
        "normalized_search_terms": ["neovascular AMD"],
    }
    values.update(overrides)

    with pytest.raises(ValidationError):
        PICO.model_validate(values)


def test_pubmed_url_must_match_pmid() -> None:
    with pytest.raises(ValidationError, match="URL must match PMID"):
        PubMedRecord(
            pmid="11111111",
            title="Synthetic title",
            journal="Synthetic journal",
            url="https://pubmed.ncbi.nlm.nih.gov/22222222/",
        )


def test_trial_url_must_match_nct_id() -> None:
    with pytest.raises(ValidationError, match="URL must match NCT ID"):
        ClinicalTrialRecord(
            nct_id="NCT00000001",
            title="Synthetic title",
            study_type="INTERVENTIONAL",
            overall_status="COMPLETED",
            url="https://clinicaltrials.gov/study/NCT00000002",
        )
