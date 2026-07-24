"""PICO extraction models."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PICO(BaseModel):
    """Structured clinical question with explicit missing information."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    population: NonBlankText
    condition: NonBlankText
    intervention: NonBlankText
    comparator: NonBlankText
    outcomes: list[NonBlankText] = Field(min_length=1)
    time_horizon: NonBlankText | None = None
    study_context: NonBlankText | None = None
    ambiguities: list[NonBlankText] = Field(default_factory=list)
    missing_information: list[NonBlankText] = Field(default_factory=list)
    normalized_search_terms: list[NonBlankText] = Field(min_length=1)
