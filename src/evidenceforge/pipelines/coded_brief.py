"""Phase 1 question-to-coded-brief pipeline."""

import asyncio
import re
from importlib.resources import files
from pathlib import Path

from evidenceforge.clients.terminology import ICD10CMClient, RxNormClient
from evidenceforge.core.safety import validate_population_question
from evidenceforge.llm.base import LLMProvider
from evidenceforge.models import PICO, CodedBrief, Mapping, OntologyCandidate, OntologyName

SOURCE_PROMPT_PATH = Path(__file__).parents[3] / "prompts" / "pico" / "v1.md"


def load_pico_prompt() -> str:
    """Load the versioned prompt from a checkout or an installed wheel."""

    if SOURCE_PROMPT_PATH.exists():
        return SOURCE_PROMPT_PATH.read_text(encoding="utf-8")
    return files("evidenceforge").joinpath("prompts/pico/v1.md").read_text()


class CodedBriefPipeline:
    def __init__(
        self,
        *,
        llm: LLMProvider,
        icd10: ICD10CMClient,
        rxnorm: RxNormClient,
    ) -> None:
        self._llm = llm
        self._icd10 = icd10
        self._rxnorm = rxnorm

    async def run(self, question: str, *, confirmed_no_phi: bool = False) -> CodedBrief:
        cleaned = validate_population_question(question, confirmed_no_phi=confirmed_no_phi)
        pico = await self._llm.generate_structured(
            system_prompt=load_pico_prompt(),
            user_prompt=cleaned,
            response_model=PICO,
        )
        condition_candidates, intervention_candidates, comparator_candidates = await asyncio.gather(
            self._icd10.search(pico.condition),
            self._rxnorm.search(pico.intervention),
            self._rxnorm.search(pico.comparator),
        )
        mappings = [
            _condition_mapping(pico.condition, condition_candidates),
            _drug_mapping(pico.intervention, intervention_candidates),
            _drug_mapping(pico.comparator, comparator_candidates),
        ]
        llm_run = self._llm.last_run_metadata
        if llm_run is None:
            raise RuntimeError("LLM provider did not expose run metadata")
        return CodedBrief(question=cleaned, pico=pico, mappings=mappings, llm_run=llm_run)


def _condition_mapping(term: str, candidates: list[OntologyCandidate]) -> Mapping:
    normalized_term = _normalize_label(term)
    amd_candidates = [
        item
        for item in candidates
        if "age-related macular degeneration" in item.preferred_label.lower()
        and "choroidal neovascularization" in item.preferred_label.lower()
    ]
    if amd_candidates:
        laterality = _stated_laterality(normalized_term)
        activity = _stated_activity(normalized_term)
        target_laterality = laterality or "unspecified eye"
        target_activity = activity or "active"
        selected = next(
            (
                item
                for item in amd_candidates
                if target_laterality in item.preferred_label.lower()
                and f"with {target_activity} choroidal neovascularization"
                in item.preferred_label.lower()
            ),
            None,
        )
        missing_axes = [
            name
            for name, value in (("eye laterality", laterality), ("lesion activity", activity))
            if value is None
        ]
        review_reason = (
            f"Confirm provisional mapping because the question omits {', '.join(missing_axes)}."
            if selected and missing_axes
            else None
        )
        if selected is None:
            review_reason = "No candidate matched the stated laterality and lesion activity."
        match_method = "deterministic laterality-and-activity ranking"
        review_required = bool(missing_axes) or selected is None
    else:
        selected = next(
            (
                item
                for item in candidates
                if _normalize_label(item.preferred_label) == normalized_term
            ),
            None,
        )
        review_required = selected is None
        review_reason = None if selected else "No exact normalized ICD-10-CM label match."
        match_method = "exact normalized service-label match"

    return Mapping(
        original_term=term,
        normalized_term=normalized_term,
        ontology=OntologyName.ICD10CM,
        selected=selected,
        candidates=candidates,
        match_method=match_method,
        human_review_required=review_required,
        review_reason=review_reason,
    )


def _drug_mapping(term: str, candidates: list[OntologyCandidate]) -> Mapping:
    normalized_term = _normalize_label(term)
    selected = next(
        (item for item in candidates if _normalize_label(item.preferred_label) == normalized_term),
        None,
    )
    return Mapping(
        original_term=term,
        normalized_term=normalized_term,
        ontology=OntologyName.RXNORM,
        selected=selected,
        candidates=candidates,
        match_method="exact normalized label within RxNorm approximate candidates",
        human_review_required=selected is None,
        review_reason=None if selected else "RxNorm returned no exact normalized label match.",
    )


def _normalize_label(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _stated_laterality(normalized_term: str) -> str | None:
    for laterality in ("bilateral", "right eye", "left eye", "unspecified eye"):
        if laterality in normalized_term:
            return laterality
    return None


def _stated_activity(normalized_term: str) -> str | None:
    if "inactive" in normalized_term:
        return "inactive"
    if "active" in normalized_term:
        return "active"
    return None
