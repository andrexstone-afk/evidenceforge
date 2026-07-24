from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from time import monotonic

import httpx
import pytest

from evidenceforge.clients.evidence import ClinicalTrialsClient, PubMedClient
from evidenceforge.clients.evidence.base import EvidenceClientError, _retry_delay
from evidenceforge.models.evidence import EvidenceQuery, EvidenceSource
from tests.fixtures.evidence import (
    CLINICAL_TRIALS_RESPONSE,
    PUBMED_FETCH_XML,
    PUBMED_SEARCH_RESPONSE,
)


@pytest.mark.asyncio
async def test_pubmed_search_fetch_contract_and_request_identity() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/esearch.fcgi"):
            return httpx.Response(200, json=PUBMED_SEARCH_RESPONSE)
        return httpx.Response(200, text=PUBMED_FETCH_XML)

    client = PubMedClient(
        email="maintainer@example.com",
        transport=httpx.MockTransport(handler),
        min_interval_seconds=0,
    )
    try:
        page = await client.search(
            EvidenceQuery(
                source=EvidenceSource.PUBMED,
                query='"neovascular AMD"[Title/Abstract]',
                page_size=2,
            )
        )
    finally:
        await client.aclose()

    assert page.metadata.total_count == 2
    assert [record.pmid for record in page.records] == ["11111111", "22222222"]
    assert page.records[0].authors == ["Ada Example", "Fixture Study Group"]
    assert page.records[0].doi == "10.0000/synthetic.1"
    assert page.records[0].is_correction is True
    assert page.records[0].abstract == (
        "BACKGROUND: Synthetic fixture background.\nRESULTS: No clinical conclusion is asserted."
    )
    assert page.records[1].is_retracted is True
    assert requests[0].url.params["tool"] == "evidenceforge"
    assert requests[0].url.params["email"] == "maintainer@example.com"
    assert requests[1].url.params["id"] == "11111111,22222222"


@pytest.mark.asyncio
async def test_clinical_trials_v2_contract_and_pagination() -> None:
    captured: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured
        captured = request
        return httpx.Response(200, json=CLINICAL_TRIALS_RESPONSE)

    client = ClinicalTrialsClient(
        transport=httpx.MockTransport(handler),
        min_interval_seconds=0,
    )
    try:
        page = await client.search(
            EvidenceQuery(
                source=EvidenceSource.CLINICAL_TRIALS,
                query='"neovascular AMD" AND ("aflibercept" OR "ranibizumab")',
                filters={"overall_status": "RECRUITING,COMPLETED"},
                page_size=1,
            ),
            page_token="previous-page",
        )
    finally:
        await client.aclose()

    assert page.metadata.next_page_token == "synthetic-next-page"
    assert page.records[0].nct_id == "NCT00000001"
    assert page.records[0].enrollment == 120
    assert page.records[0].interventions == ["Aflibercept", "Ranibizumab"]
    assert page.records[0].outcomes == ["Change in visual acuity", "Adverse events"]
    assert captured is not None
    assert captured.url.path == "/api/v2/studies"
    assert captured.url.params["filter.overallStatus"] == "RECRUITING|COMPLETED"
    assert captured.url.params["pageToken"] == "previous-page"


@pytest.mark.asyncio
async def test_clinical_trials_retries_rate_limit_then_succeeds() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json=CLINICAL_TRIALS_RESPONSE)

    client = ClinicalTrialsClient(
        transport=httpx.MockTransport(handler),
        min_interval_seconds=0,
        retries=1,
    )
    try:
        await client.search(
            EvidenceQuery(
                source=EvidenceSource.CLINICAL_TRIALS,
                query="synthetic",
                page_size=1,
            )
        )
    finally:
        await client.aclose()

    assert attempts == 2


@pytest.mark.asyncio
async def test_failed_response_is_paced_before_retry() -> None:
    request_times: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request_times.append(monotonic())
        if len(request_times) == 1:
            return httpx.Response(500, headers={"Retry-After": "0"})
        return httpx.Response(200, json=CLINICAL_TRIALS_RESPONSE)

    client = ClinicalTrialsClient(
        transport=httpx.MockTransport(handler),
        min_interval_seconds=0.05,
        retries=1,
    )
    try:
        await client.search(
            EvidenceQuery(
                source=EvidenceSource.CLINICAL_TRIALS,
                query="synthetic",
                page_size=1,
            )
        )
    finally:
        await client.aclose()

    assert request_times[1] - request_times[0] >= 0.045


@pytest.mark.asyncio
async def test_remote_protocol_failure_is_retried() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.RemoteProtocolError("synthetic protocol failure", request=request)
        return httpx.Response(200, json=CLINICAL_TRIALS_RESPONSE)

    client = ClinicalTrialsClient(
        transport=httpx.MockTransport(handler),
        min_interval_seconds=0,
        retries=1,
    )
    try:
        await client.search(
            EvidenceQuery(
                source=EvidenceSource.CLINICAL_TRIALS,
                query="synthetic",
                page_size=1,
            )
        )
    finally:
        await client.aclose()

    assert attempts == 2


def test_retry_after_supports_http_date_and_cap() -> None:
    now = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)

    ten_seconds = _retry_delay(
        retry_after=format_datetime(now + timedelta(seconds=10), usegmt=True),
        attempt=0,
        now=now,
    )
    capped = _retry_delay(
        retry_after=format_datetime(now + timedelta(seconds=45), usegmt=True),
        attempt=0,
        now=now,
    )

    assert ten_seconds == 10
    assert capped == 30


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_retry_after_non_finite_seconds_use_backoff(value: str) -> None:
    assert _retry_delay(retry_after=value, attempt=1) == 0.5


def test_evidence_clients_reject_non_allowlisted_hosts() -> None:
    with pytest.raises(ValueError, match=r"eutils\.ncbi\.nlm\.nih\.gov"):
        PubMedClient(
            email="maintainer@example.com",
            base_url="https://example.com/",
        )
    with pytest.raises(ValueError, match=r"clinicaltrials\.gov"):
        ClinicalTrialsClient(base_url="https://example.com/api/v2/")
    with pytest.raises(ValueError, match=r"eutils\.ncbi\.nlm\.nih\.gov"):
        PubMedClient(
            email="maintainer@example.com",
            base_url="http://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
        )
    with pytest.raises(ValueError, match=r"clinicaltrials\.gov"):
        ClinicalTrialsClient(base_url="http://clinicaltrials.gov/api/v2/")


@pytest.mark.asyncio
async def test_pubmed_rejects_identifier_mismatch() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/esearch.fcgi"):
            return httpx.Response(200, json=PUBMED_SEARCH_RESPONSE)
        return httpx.Response(200, text=PUBMED_FETCH_XML.replace("22222222", "33333333"))

    client = PubMedClient(
        email="maintainer@example.com",
        transport=httpx.MockTransport(handler),
        min_interval_seconds=0,
    )
    try:
        with pytest.raises(EvidenceClientError, match="identifiers"):
            await client.search(
                EvidenceQuery(
                    source=EvidenceSource.PUBMED,
                    query="synthetic",
                    page_size=2,
                )
            )
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_clinical_trials_malformed_study_uses_domain_error() -> None:
    payload = {"totalCount": 1, "studies": [{"protocolSection": {}}]}
    client = ClinicalTrialsClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
        min_interval_seconds=0,
    )
    try:
        with pytest.raises(EvidenceClientError, match="invalid API v2"):
            await client.search(
                EvidenceQuery(
                    source=EvidenceSource.CLINICAL_TRIALS,
                    query="synthetic",
                    page_size=1,
                )
            )
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_evidence_client_malformed_json_uses_domain_error() -> None:
    client = ClinicalTrialsClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=b"not-json",
                headers={"content-type": "application/json"},
            )
        ),
        min_interval_seconds=0,
    )
    try:
        with pytest.raises(EvidenceClientError, match="malformed JSON"):
            await client.search(
                EvidenceQuery(
                    source=EvidenceSource.CLINICAL_TRIALS,
                    query="synthetic",
                    page_size=1,
                )
            )
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_evidence_client_invalid_json_encoding_uses_domain_error() -> None:
    client = ClinicalTrialsClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=b"\xff\xfe\xff",
                headers={"content-type": "application/json; charset=utf-8"},
            )
        ),
        min_interval_seconds=0,
    )
    try:
        with pytest.raises(EvidenceClientError, match="malformed JSON"):
            await client.search(
                EvidenceQuery(
                    source=EvidenceSource.CLINICAL_TRIALS,
                    query="synthetic",
                    page_size=1,
                )
            )
    finally:
        await client.aclose()
