import os

import pytest

from evidenceforge.clients.evidence import ClinicalTrialsClient, PubMedClient
from evidenceforge.models.evidence import EvidenceQuery, EvidenceSource

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("EVIDENCEFORGE_RUN_LIVE_INTEGRATION") != "1",
        reason="live evidence integrations are opt-in",
    ),
]


@pytest.mark.asyncio
async def test_live_pubmed_contract() -> None:
    email = os.environ["EVIDENCEFORGE_NCBI_EMAIL"]
    client = PubMedClient(email=email)
    try:
        page = await client.search(
            EvidenceQuery(
                source=EvidenceSource.PUBMED,
                query='"neovascular age-related macular degeneration"[Title/Abstract]',
                page_size=1,
            )
        )
    finally:
        await client.aclose()

    assert page.metadata.total_count > 0
    assert len(page.records) == 1


@pytest.mark.asyncio
async def test_live_clinical_trials_v2_contract() -> None:
    client = ClinicalTrialsClient()
    try:
        page = await client.search(
            EvidenceQuery(
                source=EvidenceSource.CLINICAL_TRIALS,
                query='"neovascular age-related macular degeneration"',
                page_size=1,
            )
        )
    finally:
        await client.aclose()

    assert page.metadata.total_count > 0
    assert len(page.records) == 1
