"""PICO extraction models."""

from pydantic import BaseModel, ConfigDict, Field


class PICO(BaseModel):
    """Structured clinical question with explicit missing information."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    population: str = Field(min_length=1)
    condition: str = Field(min_length=1)
    intervention: str = Field(min_length=1)
    comparator: str = Field(min_length=1)
    outcomes: list[str] = Field(min_length=1)
    time_horizon: str | None = None
    study_context: str | None = None
    ambiguities: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    normalized_search_terms: list[str] = Field(min_length=1)
