"""Deterministic provider for tests and the documented AMD example."""

from time import perf_counter

from pydantic import BaseModel

from evidenceforge.llm.base import StructuredModel
from evidenceforge.models.llm import LLMRunMetadata
from evidenceforge.models.pico import PICO


class MockLLMProvider:
    """Return a validated fixture without network or paid API access."""

    def __init__(self, response: BaseModel | None = None) -> None:
        self._response = response or amd_pico()
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
        del system_prompt
        required_terms = {"neovascular", "aflibercept", "ranibizumab", "visual acuity"}
        if not all(term in user_prompt.lower() for term in required_terms):
            raise ValueError(
                "The mock provider supports only the documented neovascular AMD example; "
                "configure a production provider for other questions."
            )
        response = response_model.model_validate(self._response.model_dump())
        self._last_run_metadata = LLMRunMetadata(
            provider="mock",
            model="deterministic-amd-fixture-v1",
            latency_ms=(perf_counter() - started) * 1000,
        )
        return response


def amd_pico() -> PICO:
    return PICO(
        population="Adults with neovascular age-related macular degeneration",
        condition="neovascular age-related macular degeneration",
        intervention="aflibercept",
        comparator="ranibizumab",
        outcomes=["visual acuity"],
        ambiguities=["Treatment regimen and prior-treatment status are unspecified."],
        missing_information=["time horizon", "eye laterality"],
        normalized_search_terms=[
            "neovascular age-related macular degeneration",
            "aflibercept",
            "ranibizumab",
            "visual acuity",
        ],
    )
