"""Deterministic queued provider for multi-stage pipeline tests."""

from dataclasses import dataclass
from time import perf_counter

from pydantic import BaseModel

from evidenceforge.llm.base import StructuredModel
from evidenceforge.models.llm import LLMRunMetadata


@dataclass(frozen=True)
class ScriptedCall:
    """Captured prompt boundary for one deterministic provider call."""

    system_prompt: str
    user_prompt: str
    response_model_name: str


class ScriptedLLMProvider:
    """Return queued validated models while capturing prompt boundaries."""

    def __init__(self, responses: list[BaseModel], *, model_name: str) -> None:
        if not responses:
            raise ValueError("Scripted provider requires at least one response")
        self._responses = list(responses)
        self._model_name = model_name
        self._index = 0
        self._last_run_metadata: LLMRunMetadata | None = None
        self._calls: list[ScriptedCall] = []

    @property
    def calls(self) -> tuple[ScriptedCall, ...]:
        """Return immutable captured call history."""

        return tuple(self._calls)

    @property
    def last_run_metadata(self) -> LLMRunMetadata | None:
        return self._last_run_metadata

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        started = perf_counter()
        if self._index >= len(self._responses):
            raise RuntimeError("Scripted provider response queue is exhausted")
        self._calls.append(
            ScriptedCall(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model_name=response_model.__name__,
            )
        )
        queued = self._responses[self._index]
        self._index += 1
        response = response_model.model_validate(queued.model_dump())
        self._last_run_metadata = LLMRunMetadata(
            provider="scripted",
            model=self._model_name,
            latency_ms=(perf_counter() - started) * 1000,
        )
        return response

    async def aclose(self) -> None:
        """No-op lifecycle hook matching network-backed providers."""
