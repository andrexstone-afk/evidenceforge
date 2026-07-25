import pytest

from evidenceforge.core.safety import looks_like_phi


@pytest.mark.parametrize(
    "value",
    (
        "DOB 01/15/1980",
        "date of birth 1980-01-15",
        "DOB: 01/15/1980",
    ),
)
def test_phi_screen_detects_dob_with_separator_or_whitespace(value: str) -> None:
    assert looks_like_phi(value)
