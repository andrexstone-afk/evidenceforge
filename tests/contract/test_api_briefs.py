from uuid import UUID

from fastapi.testclient import TestClient

from evidenceforge.api.app import create_app
from evidenceforge.db.base import Base
from evidenceforge.db.repository import BriefRepository
from evidenceforge.db.session import create_engine_for_url, create_session_factory
from evidenceforge.settings import Settings
from tests.fixtures.persistence import persistence_input
from tests.fixtures.qa import QUESTION


def _client(tmp_path) -> TestClient:
    database_url = f"sqlite:///{tmp_path / 'api.sqlite'}"
    engine = create_engine_for_url(database_url)
    Base.metadata.create_all(engine)
    repository = BriefRepository(create_session_factory(engine))
    return TestClient(
        create_app(
            repository=repository,
            settings=Settings(environment="test", database_url=database_url),
        )
    )


def _unmigrated_client(tmp_path) -> TestClient:
    database_url = f"sqlite:///{tmp_path / 'unmigrated.sqlite'}"
    engine = create_engine_for_url(database_url)
    repository = BriefRepository(create_session_factory(engine))
    return TestClient(
        create_app(
            repository=repository,
            settings=Settings(environment="test", database_url=database_url),
        )
    )


class _FailingRepository:
    def get(self, _brief_id: str) -> None:
        raise RuntimeError("sensitive internal detail")


async def _request_payload() -> dict[str, object]:
    aggregate = await persistence_input()
    payload = aggregate.model_dump(mode="json")
    payload.pop("created_at")
    payload["confirm_no_phi"] = True
    return payload


async def test_brief_api_round_trip_contract(tmp_path) -> None:
    client = _client(tmp_path)
    payload = await _request_payload()

    created = client.post(
        "/api/v1/briefs",
        json=payload,
        headers={"X-Correlation-ID": "phase4-contract-test"},
    )

    assert created.status_code == 201
    assert created.headers["X-Correlation-ID"] == "phase4-contract-test"
    body = created.json()
    assert body["processing_status"] == "completed"
    assert body["qa_status"] == "pass"
    assert body["correlation_id"] == "phase4-contract-test"
    brief_id = body["brief_id"]
    assert body["links"] == {
        "result": f"/api/v1/briefs/{brief_id}",
        "qa": f"/api/v1/briefs/{brief_id}/qa",
        "export": f"/api/v1/briefs/{brief_id}/export",
    }

    read = client.get(body["links"]["result"])
    assert read.status_code == 200
    assert read.json()["aggregate"]["question"] == QUESTION
    assert read.json()["aggregate"]["synthesis_qa"]["final_qa"]["status"] == "pass"

    qa = client.get(body["links"]["qa"])
    assert qa.status_code == 200
    assert qa.json()["original_qa"]["status"] == "blocked"
    assert qa.json()["final_qa"]["status"] == "pass"
    assert qa.json()["revision"]["changes"][0]["claim_id"] == "CLM-0002"

    exported = client.get(body["links"]["export"], params={"format": "json"})
    assert exported.status_code == 200
    assert exported.json()["format"] == "json"
    assert exported.json()["content"]["question"] == QUESTION


async def test_brief_api_returns_consistent_not_found_error(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.get(
        "/api/v1/briefs/00000000-0000-0000-0000-000000000000",
        headers={"X-Correlation-ID": "missing-brief-test"},
    )

    assert response.status_code == 404
    assert response.headers["X-Correlation-ID"] == "missing-brief-test"
    assert response.json() == {
        "error": {
            "code": "brief_not_found",
            "message": "The requested brief does not exist.",
            "correlation_id": "missing-brief-test",
            "details": [],
        }
    }


async def test_brief_api_rejects_phi_before_persistence(tmp_path) -> None:
    client = _client(tmp_path)
    payload = await _request_payload()
    payload["question"] = f"{QUESTION} Patient MRN: 123456."

    response = client.post("/api/v1/briefs", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsafe_clinical_question"


async def test_brief_api_rejects_phi_nested_in_artifact(tmp_path) -> None:
    client = _client(tmp_path)
    payload = await _request_payload()
    payload["pico"]["missing_information"].append("Patient MRN: 123456")

    response = client.post("/api/v1/briefs", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsafe_clinical_question"


async def test_brief_api_requires_explicit_no_phi_confirmation(tmp_path) -> None:
    client = _client(tmp_path)
    payload = await _request_payload()
    payload["confirm_no_phi"] = False

    response = client.post("/api/v1/briefs", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["loc"][-1] == "confirm_no_phi"


def test_brief_api_rejects_non_uuid_lookup_without_querying_database(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.get("/api/v1/briefs/not-a-uuid%27%20OR%201%3D1")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["loc"][-1] == "brief_id"


def test_brief_api_replaces_untrusted_correlation_id(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.get(
        "/api/v1/briefs/00000000-0000-0000-0000-000000000000",
        headers={"X-Correlation-ID": "unsafe correlation: forged"},
    )

    correlation_id = response.headers["X-Correlation-ID"]
    assert response.status_code == 404
    assert correlation_id != "unsafe correlation: forged"
    assert str(UUID(correlation_id)) == correlation_id
    assert response.json()["error"]["correlation_id"] == correlation_id


def test_brief_api_wraps_unexpected_errors_with_correlation_id(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'unexpected.sqlite'}"
    client = TestClient(
        create_app(
            repository=_FailingRepository(),  # type: ignore[arg-type]
            settings=Settings(environment="test", database_url=database_url),
        )
    )

    response = client.get(
        "/api/v1/briefs/00000000-0000-0000-0000-000000000000",
        headers={"X-Correlation-ID": "unexpected-error-test"},
    )

    assert response.status_code == 500
    assert response.headers["X-Correlation-ID"] == "unexpected-error-test"
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "An unexpected error occurred.",
            "correlation_id": "unexpected-error-test",
            "details": [],
        }
    }
    assert "sensitive internal detail" not in response.text


async def test_brief_api_rejects_evidence_set_tampering(tmp_path) -> None:
    client = _client(tmp_path)
    payload = await _request_payload()
    payload["retrieval"]["pubmed"]["records"] = []

    response = client.post("/api/v1/briefs", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "absent from retrieval" in response.json()["error"]["details"][0]["msg"]


async def test_brief_api_recomputes_deterministic_findings(tmp_path) -> None:
    client = _client(tmp_path)
    payload = await _request_payload()
    payload["synthesis_qa"]["original_qa"]["deterministic_findings"] = []

    response = client.post("/api/v1/briefs", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "do not match recomputation" in response.json()["error"]["details"][0]["msg"]


async def test_brief_api_reports_unavailable_persistence(tmp_path) -> None:
    payload = await _request_payload()

    response = _unmigrated_client(tmp_path).post("/api/v1/briefs", json=payload)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "persistence_unavailable"
    assert response.headers["X-Correlation-ID"]


def test_openapi_exposes_required_versioned_brief_routes(tmp_path) -> None:
    schema = _client(tmp_path).get("/openapi.json").json()
    paths = schema["paths"]

    assert "/api/v1/briefs" in paths
    assert "/api/v1/briefs/{brief_id}" in paths
    assert "/api/v1/briefs/{brief_id}/qa" in paths
    assert "/api/v1/briefs/{brief_id}/export" in paths
    assert paths["/api/v1/briefs"]["post"]["responses"]["422"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/ErrorResponse")
