import httpx
import pytest

from evidenceforge.clients.terminology import ICD10CMClient, RxNormClient
from evidenceforge.clients.terminology.base import TerminologyClientError
from tests.fixtures.terminology import ICD_RESPONSE, rx_response


@pytest.mark.asyncio
async def test_icd10_contract_parses_clinical_tables_shape() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=ICD_RESPONSE))
    client = ICD10CMClient(transport=transport)
    try:
        candidates = await client.search("neovascular age-related macular degeneration")
    finally:
        await client.aclose()

    assert candidates[-1].code == "H35.3291"
    assert candidates[-1].source_rank == 4


@pytest.mark.asyncio
async def test_rxnorm_contract_deduplicates_rxcui() -> None:
    payload = rx_response(rxcui="1232150", name="aflibercept", score="13.27")
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    client = RxNormClient(transport=transport)
    try:
        candidates = await client.search("aflibercept")
    finally:
        await client.aclose()

    assert [(item.code, item.preferred_label) for item in candidates] == [
        ("1232150", "aflibercept")
    ]


@pytest.mark.asyncio
async def test_icd10_retries_rate_limit_then_succeeds() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429)
        return httpx.Response(200, json=ICD_RESPONSE)

    client = ICD10CMClient(transport=httpx.MockTransport(handler), retries=1)
    try:
        candidates = await client.search("neovascular AMD")
    finally:
        await client.aclose()

    assert attempts == 2
    assert candidates


def test_clients_reject_non_allowlisted_hosts() -> None:
    with pytest.raises(ValueError, match=r"clinicaltables\.nlm\.nih\.gov"):
        ICD10CMClient(base_url="https://example.com")


@pytest.mark.asyncio
async def test_malformed_json_uses_domain_error() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            content=b"not-json",
            headers={"content-type": "application/json"},
        )
    )
    client = ICD10CMClient(transport=transport)
    try:
        with pytest.raises(TerminologyClientError, match="malformed JSON"):
            await client.search("neovascular AMD")
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_invalid_icd_candidate_uses_domain_error() -> None:
    payload = [1, ["bad-code"], None, [["bad-code", "Invalid"]]]
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    client = ICD10CMClient(transport=transport)
    try:
        with pytest.raises(TerminologyClientError, match="candidate data"):
            await client.search("invalid")
    finally:
        await client.aclose()


def test_clients_validate_retry_bounds() -> None:
    with pytest.raises(ValueError, match="Retries"):
        RxNormClient(retries=6)
