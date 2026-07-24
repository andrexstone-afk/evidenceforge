import pytest
from pydantic import ValidationError

from evidenceforge.models import OntologyCandidate, OntologyName
from evidenceforge.pipelines.coded_brief import _condition_mapping, _drug_mapping
from tests.fixtures.terminology import ICD_RESPONSE


def _icd_candidates() -> list[OntologyCandidate]:
    return [
        OntologyCandidate(
            ontology=OntologyName.ICD10CM,
            code=row[0],
            preferred_label=row[1],
            source_url="https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search",
            source_rank=index,
        )
        for index, row in enumerate(ICD_RESPONSE[3], start=1)
    ]


def test_icd_mapping_respects_stated_right_eye_and_activity() -> None:
    mapping = _condition_mapping(
        "active neovascular age-related macular degeneration, right eye",
        _icd_candidates(),
    )

    assert mapping.selected
    assert mapping.selected.code == "H35.3211"
    assert mapping.human_review_required is False


def test_rxnorm_rejects_non_exact_fuzzy_candidate() -> None:
    candidate = OntologyCandidate(
        ontology=OntologyName.RXNORM,
        code="1232150",
        preferred_label="different drug",
        source_url="https://rxnav.nlm.nih.gov/REST/approximateTerm.json",
        source_rank=1,
        score=4.2,
    )

    mapping = _drug_mapping("aflibercept", [candidate])

    assert mapping.selected is None
    assert mapping.human_review_required is True


@pytest.mark.parametrize(
    ("ontology", "code"),
    [
        (OntologyName.ICD10CM, "not-a-code"),
        (OntologyName.RXNORM, "RX-123"),
    ],
)
def test_ontology_candidate_rejects_invalid_identifier(
    ontology: OntologyName,
    code: str,
) -> None:
    with pytest.raises(ValidationError):
        OntologyCandidate(
            ontology=ontology,
            code=code,
            preferred_label="invalid",
            source_url="https://clinicaltables.nlm.nih.gov",
            source_rank=1,
        )
