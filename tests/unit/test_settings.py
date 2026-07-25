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


def test_api_key_is_masked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVIDENCEFORGE_OPENAI_API_KEY", "test-secret-value")

    settings = Settings()

    assert "test-secret-value" not in repr(settings)
    assert "test-secret-value" not in settings.model_dump_json()


def test_settings_reject_non_sqlite_database_url() -> None:
    with pytest.raises(ValidationError, match="must use sqlite"):
        Settings(database_url="postgresql://localhost/evidenceforge")
