import pytest
from pydantic import ValidationError

from evidenceforge.models import PICO


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
