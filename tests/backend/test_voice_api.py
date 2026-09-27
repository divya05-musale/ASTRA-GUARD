"""Backend voice API tests — thin integration layer only."""
import pytest
from fastapi.testclient import TestClient

from agent.voice.voice_service import reset_voice_guidance
from backend.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_voice_singleton():
    reset_voice_guidance()
    yield
    reset_voice_guidance()


def test_voice_status_returns_200():
    r = client.get("/api/voice/status")
    assert r.status_code == 200
    data = r.json()
    assert data["language"] == "en"
    assert data["enabled"] is True


def test_get_voice_language_defaults_to_english():
    r = client.get("/api/voice/language")
    assert r.status_code == 200
    assert r.json() == {"language": "en"}


def test_set_voice_language_to_hindi():
    r = client.post("/api/voice/language", json={"language": "hi"})
    assert r.status_code == 200
    assert r.json() == {"language": "hi"}

    r = client.get("/api/voice/language")
    assert r.json() == {"language": "hi"}


def test_set_voice_language_rejects_unsupported_language():
    r = client.post("/api/voice/language", json={"language": "fr"})
    assert r.status_code == 422


def test_set_voice_enabled_toggle():
    r = client.post("/api/voice/enabled", json={"enabled": False})
    assert r.status_code == 200
    assert r.json() == {"enabled": False}

    r = client.get("/api/voice/status")
    assert r.json()["enabled"] is False
