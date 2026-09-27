"""Status alias router — exposes /status over the shared mission service."""
from fastapi import APIRouter
from backend.services.mission_service import get_mission_service
from backend.services.performance_service import get_performance_monitor

router = APIRouter()


@router.get("/status")
def get_status() -> dict:
    return get_mission_service().get_status()


@router.get("/performance")
def get_performance() -> dict:
    return get_performance_monitor().get_status()


@router.post("/performance/display")
def report_dashboard_display(payload: dict) -> dict:
    try:
        fps = float(payload["displayed_fps"])
        displayed_at = float(payload["displayed_at"])
    except (KeyError, TypeError, ValueError):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="displayed_fps and displayed_at must be numeric")
    get_performance_monitor().record_display(fps, displayed_at)
    return {"recorded": True}

