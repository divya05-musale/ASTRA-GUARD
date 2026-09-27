"""Keep mission-session tests isolated from workspace session records."""

import pytest

from backend.services import mission_service
from backend.services.session_store import SessionStore


@pytest.fixture(autouse=True)
def isolate_mission_session_store(monkeypatch, tmp_path):
    class TemporarySessionStore(SessionStore):
        def __init__(self):
            super().__init__(tmp_path / "session_records")

    monkeypatch.setattr(mission_service, "SessionStore", TemporarySessionStore)
    mission_service.reset_mission_service()
    yield
    mission_service.reset_mission_service()