import httpx
import pytest

from evidenceforge.clients.evidence import ClinicalTrialsClient, PubMedClient
from evidenceforge.clients.evidence.base import EvidenceClientError
from evidenceforge.models.evidence import EvidenceQuery, EvidenceSource
from tests.fixtures.evidence import CLINICAL_TRIALS_RESPONSE, PUBMED_SEARCH_RESPONSE


@pytest.mark.asyncio
async def test_pubmed_rejects_xml_entity_payload() -> None:
    malicious_xml = """\
<?xml version="1.0"?>
<!DOCTYPE data [<!ENTITY payload "untrusted-expanded-content">]>
<PubmedArticleSet><PubmedArticle>&payload;</PubmedArticle></PubmedArticleSet>
"""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/esearch.fcgi"):
            payload = {
                **PUBMED_SEARCH_RESPONSE,
                "esearchresult": {
                    **PUBMED_SEARCH_RESPONSE["esearchresult"],
                    "count": "1",
                    "idlist": ["11111111"],
                },
            }
            return httpx.Response(200, json=payload)
        return httpx.Response(200, text=malicious_xml)

    client = PubMedClient(
        email="maintainer@example.com",
        transport=httpx.MockTransport(handler),
        min_interval_seconds=0,
    )
    try:
        with pytest.raises(EvidenceClientError, match="invalid citation"):
            await client.search(
                EvidenceQuery(
                    source=EvidenceSource.PUBMED,
                    query="synthetic",
                    page_size=1,
                )
            )
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_trial_payload_cannot_override_canonical_source_url() -> None:
    payload = {
        **CLINICAL_TRIALS_RESPONSE,
        "studies": [
            {
                **CLINICAL_TRIALS_RESPONSE["studies"][0],
                "url": "https://attacker.invalid/instructions",
            }
        ],
    }
    client = ClinicalTrialsClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
        min_interval_seconds=0,
    )
    try:
        page = await client.search(
            EvidenceQuery(
                source=EvidenceSource.CLINICAL_TRIALS,
                query="synthetic",
                page_size=1,
            )
        )
    finally:
        await client.aclose()

    assert page.records[0].url == "https://clinicaltrials.gov/study/NCT00000001"
