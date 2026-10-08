"""Local experiment discovery and protocol selection routes."""
from fastapi import APIRouter, HTTPException

from backend.services.experiment_service import (
    find_valid_experiment,
    list_experiments as discover_experiments,
)
from backend.services.mission_service import get_mission_service, reset_mission_service
from backend.services.protocol_service import reset_protocol_service
from backend.services.browser_perception_service import get_browser_perception_service

router = APIRouter()


@router.get("/experiments")
def list_experiments() -> dict:
    return discover_experiments()


@router.post("/experiments/{experiment_id}/select")
def select_experiment(experiment_id: str) -> dict:
    """Load a valid local protocol as the active mission protocol."""
    current = get_mission_service()
    if current.active_session_id:
        record = current.get_session(current.active_session_id)
        if record and record.get("status") == "IN_PROGRESS":
            raise HTTPException(
                status_code=409,
                detail="Cancel or finish the active session before selecting another experiment.",
            )

    experiment_path = find_valid_experiment(experiment_id)
    if experiment_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"No valid local protocol found for {experiment_id}.",
        )

    mission = reset_mission_service(experiment_path)
    reset_protocol_service(experiment_path)
    get_browser_perception_service().reset_processor()
    return {
        "selected": True,
        "experiment": mission.experiment,
        "progress": mission.get_progress(),
    }

