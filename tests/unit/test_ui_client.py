from uuid import UUID

import httpx
import pytest

from evidenceforge.api.schemas import BriefQAResponse, BriefReadResponse
from evidenceforge.ui import EvidenceForgeAPIClient, EvidenceForgeAPIError
from tests.fixtures.persistence import persistence_input

BRIEF_ID = UUID("11111111-2222-4333-8444-555555555555")


async def test_ui_client_validates_health_brief_and_qa() -> None:
    aggregate = await persistence_input()
    brief = BriefReadResponse(brief_id=str(BRIEF_ID), aggregate=aggregate)
    qa = BriefQAResponse(
        brief_id=str(BRIEF_ID),
        original_qa=aggregate.synthesis_qa.original_qa,
        final_qa=aggregate.synthesis_qa.final_qa,
        revision=aggregate.synthesis_qa.revision,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/health":
            return httpx.Response(
                200,
                json={"status": "ok", "service": "evidenceforge", "version": "0.1.0"},
            )
        if request.url.path.endswith("/qa"):
            return httpx.Response(200, content=qa.model_dump_json())
        return httpx.Response(200, content=brief.model_dump_json())

    client = EvidenceForgeAPIClient(
        base_url="http://evidenceforge.test",
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )

    assert client.health().version == "0.1.0"
    assert client.get_brief(BRIEF_ID) == brief
    assert client.get_qa(BRIEF_ID) == qa
    assert client.get_review_bundle(BRIEF_ID) == (brief, qa)


@pytest.mark.parametrize(
    ("export_format", "content_type", "suffix"),
    [
        ("json", "application/json", ".json"),
        ("markdown", "text/markdown; charset=utf-8", ".md"),
        ("pdf", "application/pdf", ".pdf"),
    ],
)
def test_ui_client_validates_export_media(
    export_format: str,
    content_type: str,
    suffix: str,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"synthetic", headers={"content-type": content_type})

    client = EvidenceForgeAPIClient(
        base_url="http://evidenceforge.test",
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )

    artifact = client.download_export(BRIEF_ID, export_format)  # type: ignore[arg-type]

    assert artifact.content == b"synthetic"
    assert artifact.filename.endswith(suffix)


def test_ui_client_never_exposes_server_response_details() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="database password=internal-secret")

    client = EvidenceForgeAPIClient(
        base_url="http://evidenceforge.test",
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EvidenceForgeAPIError) as captured:
        client.get_brief(BRIEF_ID)

    assert str(captured.value) == "The EvidenceForge API returned an unexpected error."
    assert "internal-secret" not in str(captured.value)


def test_ui_client_rejects_invalid_response_schema() -> None:
    client = EvidenceForgeAPIClient(
        base_url="http://evidenceforge.test",
        timeout_seconds=1,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"status": "ok", "extra": "unsafe"})
        ),
    )

    with pytest.raises(EvidenceForgeAPIError, match="invalid response"):
        client.health()


def test_ui_client_normalizes_connection_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sensitive network detail", request=request)

    client = EvidenceForgeAPIClient(
        base_url="http://evidenceforge.test",
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EvidenceForgeAPIError) as captured:
        client.health()

    assert str(captured.value) == "The EvidenceForge API is unavailable."
    assert "sensitive" not in str(captured.value)


def test_ui_client_does_not_follow_redirects() -> None:
    client = EvidenceForgeAPIClient(
        base_url="http://evidenceforge.test",
        timeout_seconds=1,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                302,
                headers={"location": "http://internal.example/sensitive"},
            )
        ),
    )

    with pytest.raises(EvidenceForgeAPIError, match="unexpected error"):
        client.health()


async def test_ui_client_rejects_mismatched_brief_and_qa_responses() -> None:
    aggregate = await persistence_input()
    brief = BriefReadResponse(brief_id=str(BRIEF_ID), aggregate=aggregate)
    incomplete_qa = aggregate.synthesis_qa.final_qa.model_copy(
        update={"assessments": aggregate.synthesis_qa.final_qa.assessments[:1]}
    )
    qa = BriefQAResponse(
        brief_id=str(BRIEF_ID),
        original_qa=aggregate.synthesis_qa.original_qa,
        final_qa=incomplete_qa,
        revision=aggregate.synthesis_qa.revision,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/qa"):
            payload = qa.model_dump_json()
        else:
            payload = brief.model_dump_json()
        return httpx.Response(200, content=payload)

    client = EvidenceForgeAPIClient(
        base_url="http://evidenceforge.test",
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EvidenceForgeAPIError, match="inconsistent review artifacts"):
        client.get_review_bundle(BRIEF_ID)
