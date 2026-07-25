"""Synthetic validated aggregate for repository and API tests."""

from datetime import UTC, datetime

from evidenceforge.db.schemas import BriefPersistenceInput
from evidenceforge.llm import ScriptedLLMProvider
from evidenceforge.llm.mock import amd_pico
from evidenceforge.models.ontology import Mapping, OntologyCandidate, OntologyName
from evidenceforge.pipelines import SynthesisQAPipeline
from tests.fixtures.qa import (
    QUESTION,
    final_qa_output,
    initial_qa_output,
    original_draft,
    retrieval_fixture,
    revision_output,
)


async def persistence_input() -> BriefPersistenceInput:
    """Build one deterministic Phase 3 aggregate without network calls."""

    result = await SynthesisQAPipeline(
        synthesis_llm=ScriptedLLMProvider(
            [original_draft()],
            model_name="synthetic-synthesis-v1",
        ),
        qa_llm=ScriptedLLMProvider(
            [initial_qa_output(), final_qa_output()],
            model_name="synthetic-independent-qa-v1",
        ),
        revision_llm=ScriptedLLMProvider(
            [revision_output()],
            model_name="synthetic-revision-v1",
        ),
    ).run(
        question=QUESTION,
        pico=amd_pico(),
        mappings=[],
        retrieval=retrieval_fixture(),
    )
    candidate = OntologyCandidate(
        ontology=OntologyName.ICD10CM,
        code="H35.3291",
        preferred_label=(
            "Exudative age-related macular degeneration, unspecified eye, "
            "with active choroidal neovascularization"
        ),
        source_url="https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search",
        source_rank=1,
    )
    mapping = Mapping(
        original_term="neovascular age-related macular degeneration",
        normalized_term="neovascular age-related macular degeneration",
        ontology=OntologyName.ICD10CM,
        selected=candidate,
        candidates=[candidate],
        match_method="synthetic-service-candidate",
        human_review_required=True,
        review_reason="Laterality is unspecified in the population-level question.",
    )
    return BriefPersistenceInput(
        question=QUESTION,
        pico=amd_pico(),
        mappings=(mapping,),
        retrieval=retrieval_fixture(),
        synthesis_qa=result,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
