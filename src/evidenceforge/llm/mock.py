"""Deterministic provider for tests and the documented example questions."""

import re
from collections.abc import Callable
from time import perf_counter

from pydantic import BaseModel

from evidenceforge.llm.base import StructuredModel
from evidenceforge.models.llm import LLMRunMetadata
from evidenceforge.models.pico import PICO

_AMD_QUESTION = (
    "In adults with neovascular age-related macular degeneration, how does aflibercept "
    "compare with ranibizumab for improving visual acuity?"
)
_CARDIOMETABOLIC_QUESTION = (
    "In adults with type 2 diabetes mellitus without complications, how does semaglutide "
    "compare with empagliflozin for reducing glycated hemoglobin (HbA1c)?"
)
_RARE_DISEASE_QUESTION = (
    "In adults with myasthenia gravis without acute exacerbation, how does efgartigimod "
    "alfa compare with rozanolixizumab for improving activities of daily living?"
)
FixtureFactory = Callable[[], PICO]


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
        scenario = _scenario_for_prompt(user_prompt)
        if scenario is None:
            raise ValueError(
                "The mock provider supports only the documented AMD, cardiometabolic, and "
                "rare-disease examples; configure a production provider for other questions."
            )
        fixture_factory, model_name = scenario
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


def rare_disease_pico() -> PICO:
    """Return the documented myasthenia gravis comparison fixture."""

    return PICO(
        population="Adults with myasthenia gravis without acute exacerbation",
        condition="myasthenia gravis without acute exacerbation",
        intervention="efgartigimod alfa",
        comparator="rozanolixizumab",
        outcomes=["activities of daily living"],
        ambiguities=[
            "Antibody status, disease severity, dose, background therapy, and follow-up "
            "duration are unspecified."
        ],
        missing_information=[
            "antibody status",
            "baseline disease severity",
            "time horizon",
            "dose and treatment schedule",
            "background therapy",
        ],
        normalized_search_terms=[
            "myasthenia gravis without acute exacerbation",
            "efgartigimod alfa",
            "rozanolixizumab",
            "activities of daily living",
        ],
    )


def _scenario_for_prompt(user_prompt: str) -> tuple[FixtureFactory, str] | None:
    normalized_prompt = _normalize_prompt(user_prompt)
    scenarios = (
        (_AMD_QUESTION, amd_pico, "deterministic-amd-fixture-v1"),
        (
            _CARDIOMETABOLIC_QUESTION,
            cardiometabolic_pico,
            "deterministic-cardiometabolic-fixture-v1",
        ),
        (
            _RARE_DISEASE_QUESTION,
            rare_disease_pico,
            "deterministic-rare-disease-fixture-v1",
        ),
    )
    return next(
        (
            (fixture_factory, model_name)
            for question, fixture_factory, model_name in scenarios
            if _normalize_prompt(question) == normalized_prompt
        ),
        None,
    )


def _normalize_prompt(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))
