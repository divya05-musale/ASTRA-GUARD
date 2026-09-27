"""Backend test isolation — reset singleton mission service per test."""
import pytest

from backend.services.mission_service import reset_mission_service


@pytest.fixture(autouse=True)
def _reset_mission_singleton():
    reset_mission_service()
    yield
    reset_mission_service()
