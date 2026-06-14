from fastapi.testclient import TestClient

from api import create_app


def test_health_route_returns_ok_payload():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ai-health-agent-api",
    }
