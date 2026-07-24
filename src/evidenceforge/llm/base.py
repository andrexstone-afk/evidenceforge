"""LLM provider contract."""

from typing import Protocol, TypeVar

from pydantic import BaseModel

from evidenceforge.models.llm import LLMRunMetadata

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class LLMProvider(Protocol):
    @property
    def last_run_metadata(self) -> LLMRunMetadata | None: ...

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel: ...

    async def aclose(self) -> None: ...
