"""Coded brief model."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from evidenceforge.models.llm import LLMRunMetadata
from evidenceforge.models.ontology import Mapping
from evidenceforge.models.pico import PICO


class CodedBrief(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question: str = Field(min_length=10)
    pico: PICO
    mappings: list[Mapping]
    llm_run: LLMRunMetadata
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    prompt_version: str = "pico-v1"
    disclaimer: str = (
        "Research evidence-synthesis prototype; not a medical device, not for diagnosis, "
        "and not individualized clinical advice."
    )
