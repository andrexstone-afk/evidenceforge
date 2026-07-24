import pytest
from pydantic import ValidationError

from evidenceforge.settings import Settings


def test_settings_use_evidenceforge_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EVIDENCEFORGE_ENVIRONMENT", raising=False)
    monkeypatch.setenv("EVIDENCEFORGE_API_PORT", "8123")

    settings = Settings()

    assert settings.api_port == 8123
    assert settings.environment == "development"


def test_settings_are_immutable() -> None:
    settings = Settings()

    with pytest.raises(ValidationError, match="Instance is frozen"):
        settings.api_port = 9000
