"""LLM execution metadata."""

from pydantic import BaseModel, ConfigDict, Field


class LLMRunMetadata(BaseModel):
    """Observable provider execution details without prompts or secrets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    latency_ms: float = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    retry_count: int = Field(default=0, ge=0)
