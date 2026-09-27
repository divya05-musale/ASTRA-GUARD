"""Mission endpoints — thin layer over MissionService/MissionStatus."""
from fastapi import APIRouter
from backend.services.mission_service import get_mission_service

router = APIRouter()


@router.get("/mission/status")
def mission_status() -> dict:
    return get_mission_service().get_status()


@router.get("/mission/progress")
def mission_progress() -> dict:
    return get_mission_service().get_progress()


@router.get("/mission/summary")
def mission_summary() -> dict:
    return get_mission_service().get_summary()


@router.get("/mission")
def mission_overview() -> dict:
    return get_mission_service().get_overview()


@router.get("/mission/protocol")
def mission_protocol() -> dict:
    """Read-only protocol definition for the dashboard timeline."""
    return get_mission_service().get_protocol()


@router.post("/mission/reset")
def mission_reset() -> dict:
    """Reset the mission session to the protocol's initial state.

    Clears the singleton session (events + protocol state machine) so
    the next mission starts fresh at the first protocol step. Reuses
    the existing reset path — no duplicated decision logic.
    """
    service = get_mission_service()
    service.reset()
    return {
        "reset": True,
        "status": service.get_status(),
        "progress": service.get_progress(),
    }

