from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["message"] is not None


def test_health():
    """Health endpoint should return status (redis may be False locally)."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "redis" in data
