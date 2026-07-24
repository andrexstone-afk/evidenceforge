"""OpenAI Responses API adapter."""

import asyncio
from time import perf_counter

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
    RateLimitError,
)

from evidenceforge.llm.base import StructuredModel
from evidenceforge.models.llm import LLMRunMetadata


class OpenAIProvider:
    """Generate schema-validated output through the Responses API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
        retries: int = 2,
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=0,
        )
        self._model = model
        self._retries = retries
        self._last_run_metadata: LLMRunMetadata | None = None

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
        response = None
        for attempt in range(self._retries + 1):
            try:
                response = await self._client.responses.parse(
                    model=self._model,
                    instructions=system_prompt,
                    input=user_prompt,
                    text_format=response_model,
                    reasoning={"effort": "low"},
                )
                break
            except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError):
                if attempt == self._retries:
                    raise
                await asyncio.sleep(0.5 * (2**attempt))
        if response is None:
            raise AssertionError("OpenAI retry loop exhausted")
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("OpenAI returned no validated structured output")
        usage = response.usage
        self._last_run_metadata = LLMRunMetadata(
            provider="openai",
            model=self._model,
            latency_ms=(perf_counter() - started) * 1000,
            input_tokens=usage.input_tokens if usage else None,
            output_tokens=usage.output_tokens if usage else None,
            retry_count=attempt,
        )
        return parsed
