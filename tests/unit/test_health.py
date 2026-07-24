from fastapi.testclient import TestClient

from evidenceforge.api.app import create_app


def test_health_contract() -> None:
    response = TestClient(create_app()).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "evidenceforge",
        "version": "0.1.0",
    }
