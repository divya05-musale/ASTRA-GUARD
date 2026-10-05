"""Backend API tests — thin integration layer only."""
from fastapi.testclient import TestClient

from backend.main import ALLOWED_ORIGINS, app

client = TestClient(app)


def test_health_returns_200():
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data == {"status": "ok", "service": "ASTRA-GUARD"}


def test_mission_status_returns_200():
    r = client.get("/api/mission/status")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_mission_progress_returns_200():
    r = client.get("/api/mission/progress")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_mission_summary_returns_200():
    r = client.get("/api/mission/summary")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_events_returns_200():
    r = client.get("/api/events")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_events_limit_zero():
    r = client.get("/api/events?limit=0")
    assert r.status_code == 200
    assert r.json() == []


def test_events_limit_validates():
    r = client.get("/api/events?limit=2")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) <= 2


def test_events_negative_limit_rejected():
    r = client.get("/api/events?limit=-1")
    assert r.status_code == 422


def test_mission_overview_returns_200():
    r = client.get("/api/mission")
    assert r.status_code == 200
    data = r.json()
    for key in (
        "protocol_id",
        "protocol_name",
        "environment",
        "protocol_type",
        "current_step",
        "progress",
        "status",
    ):
        assert key in data
    assert data["protocol_id"] == "EXP001"


def test_cors_configuration_exists():
    assert "http://localhost:5173" in ALLOWED_ORIGINS
    assert "http://127.0.0.1:5173" in ALLOWED_ORIGINS
    cors = [
        m
        for m in app.user_middleware
        if "CORSMiddleware" in str(m.cls)
    ]
    assert cors, "CORSMiddleware must be configured"


def test_experiment_discovery_reports_protocol_availability():
    response = client.get("/api/experiments")
    assert response.status_code == 200
    experiments = response.json()["experiments"]
    by_id = {item["experiment_id"]: item for item in experiments}
    assert by_id["EXP001"]["available"] is True
    assert by_id["EXP001"]["steps_count"] == 8
    assert by_id["EXP006"]["available"] is True
    assert by_id["EXP006"]["steps_count"] == 8
    assert by_id["EXP007"]["available"] is True
    assert by_id["EXP007"]["steps_count"] == 9
    for experiment_id in ("EXP002", "EXP003", "EXP004", "EXP005"):
        assert by_id[experiment_id]["available"] is False
        assert by_id[experiment_id]["error"]


def test_select_experiment_requires_a_valid_local_protocol():
    selected = client.post("/api/experiments/EXP001/select")
    assert selected.status_code == 200
    assert selected.json()["selected"] is True
    assert selected.json()["experiment"]["experiment_id"] == "EXP001"

    unavailable = client.post("/api/experiments/EXP002/select")
    assert unavailable.status_code == 404


def test_new_experiments_select_through_existing_mission_service():
    try:
        for experiment_id, total_steps in (("EXP006", 8), ("EXP007", 9)):
            response = client.post(f"/api/experiments/{experiment_id}/select")
            assert response.status_code == 200
            assert response.json()["experiment"]["experiment_id"] == experiment_id
            assert response.json()["progress"]["total_steps"] == total_steps
    finally:
        assert client.post("/api/experiments/EXP001/select").status_code == 200


def test_performance_endpoint_exposes_cpu_and_ram():
    response = client.get("/api/performance")
    assert response.status_code == 200
    metrics = response.json()
    assert "system_cpu_percent" in metrics
    assert metrics["system_ram_total_mb"] > 0


def test_cors_preflight_allows_loopback_vite_fallback_port():
    response = client.options(
        "/api/voice/enabled",
        headers={
            "Origin": "http://localhost:5174",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5174"


def test_cors_preflight_allows_vercel_production_origin():
    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://astra-guard-seven.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://astra-guard-seven.vercel.app"
