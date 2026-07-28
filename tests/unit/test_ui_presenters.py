from evidenceforge.ranking import rank_evidence
from evidenceforge.ui.presenters import (
    assessment_by_claim,
    evidence_by_id,
    mapping_rows,
    ranking_rows,
)
from tests.fixtures.persistence import persistence_input


async def test_ui_presenters_keep_review_artifacts_inspectable() -> None:
    aggregate = await persistence_input()

    mappings = mapping_rows(aggregate)
    evidence = evidence_by_id(aggregate)
    assessments = assessment_by_claim(aggregate.synthesis_qa.final_qa)

    assert mappings[0]["selected_code"] == "H35.3291"
    assert mappings[0]["human_review"] is True
    assert set(evidence) == {"11111111", "NCT00000001"}
    assert assessments["CLM-0002"].classification.value == "supported"
    retrieval = aggregate.retrieval.model_copy(
        update={
            "ranking": rank_evidence(
                [
                    *aggregate.retrieval.pubmed.records,
                    *aggregate.retrieval.clinical_trials.records,
                ],
                aggregate.pico,
                current_year=2026,
            )
        }
    )
    ranked_aggregate = aggregate.model_copy(update={"retrieval": retrieval})
    ranked = ranking_rows(ranked_aggregate)
    assert {row["record_id"] for row in ranked} == {"11111111", "NCT00000001"}
    assert all("PICO overlap" in row and "safety penalty" in row for row in ranked)
