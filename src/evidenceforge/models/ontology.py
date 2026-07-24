"""Ontology mapping models."""

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class OntologyName(StrEnum):
    ICD10CM = "ICD-10-CM"
    RXNORM = "RxNorm"


class OntologyCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ontology: OntologyName
    code: str
    preferred_label: str
    source_url: HttpUrl
    source_rank: int = Field(ge=1)
    score: float | None = None

    @model_validator(mode="after")
    def validate_code_format(self) -> "OntologyCandidate":
        if self.ontology is OntologyName.ICD10CM:
            if not re.fullmatch(r"[A-Z]\d[A-Z0-9](?:\.[A-Z0-9]{1,4})?", self.code):
                raise ValueError("Invalid ICD-10-CM code format")
        elif not self.code.isdigit():
            raise ValueError("Invalid RxNorm RXCUI format")
        return self


class Mapping(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    original_term: str
    normalized_term: str
    ontology: OntologyName
    selected: OntologyCandidate | None
    candidates: list[OntologyCandidate]
    match_method: str
    human_review_required: bool
    review_reason: str | None = None

    @model_validator(mode="after")
    def validate_selected_in_candidates(self) -> "Mapping":
        if self.selected is not None and self.selected not in self.candidates:
            raise ValueError("Selected candidate must be present in candidates")
        return self
