"""Deterministic provider for tests and the documented example questions."""

from time import perf_counter

from pydantic import BaseModel

from evidenceforge.llm.base import StructuredModel
from evidenceforge.models.llm import LLMRunMetadata
from evidenceforge.models.pico import PICO


class MockLLMProvider:
    """Return a validated documented fixture without network or paid API access."""

    def __init__(self, response: BaseModel | None = None) -> None:
        self._response = response
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
        normalized_prompt = user_prompt.lower()
        scenario = next(
            (
                item
                for item in (
                    (
                        {"neovascular", "aflibercept", "ranibizumab", "visual acuity"},
                        amd_pico,
                        "deterministic-amd-fixture-v1",
                    ),
                    (
                        {
                            "type 2 diabetes mellitus without complications",
                            "semaglutide",
                            "empagliflozin",
                            "glycated hemoglobin",
                        },
                        cardiometabolic_pico,
                        "deterministic-cardiometabolic-fixture-v1",
                    ),
                )
                if all(term in normalized_prompt for term in item[0])
            ),
            None,
        )
        if scenario is None:
            raise ValueError(
                "The mock provider supports only the documented AMD and cardiometabolic "
                "examples; configure a production provider for other questions."
            )
        _, fixture_factory, model_name = scenario
        fixture = self._response or fixture_factory()
        response = response_model.model_validate(fixture.model_dump())
        self._last_run_metadata = LLMRunMetadata(
            provider="mock",
            model=model_name,
            latency_ms=(perf_counter() - started) * 1000,
        )
        return response

    async def aclose(self) -> None:
        """No-op lifecycle hook matching network-backed providers."""


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


def cardiometabolic_pico() -> PICO:
    """Return the documented type 2 diabetes comparison fixture."""

    return PICO(
        population="Adults with type 2 diabetes mellitus without complications",
        condition="type 2 diabetes mellitus without complications",
        intervention="semaglutide",
        comparator="empagliflozin",
        outcomes=["glycated hemoglobin (HbA1c)"],
        ambiguities=[
            "Dose, formulation, background glucose-lowering therapy, and follow-up "
            "duration are unspecified."
        ],
        missing_information=[
            "time horizon",
            "dose and formulation",
            "background glucose-lowering therapy",
        ],
        normalized_search_terms=[
            "type 2 diabetes mellitus without complications",
            "semaglutide",
            "empagliflozin",
            "glycated hemoglobin",
            "HbA1c",
        ],
    )
