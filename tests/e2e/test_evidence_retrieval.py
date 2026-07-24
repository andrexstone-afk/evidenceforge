import httpx
import pytest

from evidenceforge.clients.evidence import ClinicalTrialsClient, PubMedClient
from evidenceforge.models.evidence import EvidenceSource
from evidenceforge.models.pico import PICO
from evidenceforge.pipelines import EvidenceRetrievalPipeline
from tests.fixtures.evidence import (
    CLINICAL_TRIALS_RESPONSE,
    PUBMED_FETCH_XML,
    PUBMED_SEARCH_RESPONSE,
)


@pytest.mark.asyncio
async def test_pico_retrieves_normalizes_and_ranks_both_sources() -> None:
    def pubmed_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/esearch.fcgi"):
            return httpx.Response(200, json=PUBMED_SEARCH_RESPONSE)
        return httpx.Response(200, text=PUBMED_FETCH_XML)

    pubmed = PubMedClient(
        email="maintainer@example.com",
        transport=httpx.MockTransport(pubmed_handler),
        min_interval_seconds=0,
    )
    trials = ClinicalTrialsClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=CLINICAL_TRIALS_RESPONSE)
        ),
        min_interval_seconds=0,
    )
    pipeline = EvidenceRetrievalPipeline(pubmed=pubmed, clinical_trials=trials)
    try:
        result = await pipeline.run(
            PICO(
                population="adults with neovascular AMD",
                condition="neovascular age-related macular degeneration",
                intervention="aflibercept",
                comparator="ranibizumab",
                outcomes=["visual acuity", "adverse events"],
                normalized_search_terms=[
                    "neovascular AMD",
                    "aflibercept",
                    "ranibizumab",
                ],
            ),
            current_year=2026,
            page_size=2,
        )
    finally:
        await pubmed.aclose()
        await trials.aclose()

    assert len(result.pubmed.records) == 2
    assert len(result.clinical_trials.records) == 1
    assert result.ranking_year == 2026
    assert {item.source for item in result.ranking} == {
        EvidenceSource.PUBMED,
        EvidenceSource.CLINICAL_TRIALS,
    }
    assert result.ranking[-1].record_id == "22222222"


@pytest.mark.asyncio
async def test_invalid_ranking_year_fails_before_source_requests() -> None:
    def unexpected_request(request: httpx.Request) -> httpx.Response:
        pytest.fail(f"unexpected external request: {request.url}")

    pubmed = PubMedClient(
        email="maintainer@example.com",
        transport=httpx.MockTransport(unexpected_request),
        min_interval_seconds=0,
    )
    trials = ClinicalTrialsClient(
        transport=httpx.MockTransport(unexpected_request),
        min_interval_seconds=0,
    )
    pipeline = EvidenceRetrievalPipeline(pubmed=pubmed, clinical_trials=trials)
    try:
        with pytest.raises(ValueError, match="current_year"):
            await pipeline.run(
                PICO(
                    population="synthetic population",
                    condition="synthetic condition",
                    intervention="synthetic intervention",
                    comparator="synthetic comparator",
                    outcomes=["synthetic outcome"],
                    normalized_search_terms=["synthetic"],
                ),
                current_year=1899,
            )
    finally:
        await pubmed.aclose()
        await trials.aclose()
