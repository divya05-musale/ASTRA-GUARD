"""Protocol router: exposes experiment steps, activities, rules, validation."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.services.protocol_service import get_protocol_service

router = APIRouter(prefix="/api/protocol", tags=["protocol"])


@router.get("/summary")
def protocol_summary() -> dict:
    svc = get_protocol_service()
    return svc.summary()


@router.get("/steps")
def protocol_steps() -> dict:
    svc = get_protocol_service()
    steps = svc.steps()
    return {"steps": steps, "count": len(steps)}


@router.get("/steps/{step_id}")
def protocol_step_detail(step_id: str) -> dict:
    svc = get_protocol_service()
    step = svc.get_step(step_id)
    if step is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Step {step_id} not found")
    return {"step": step}


@router.get("/activities")
def protocol_activities() -> dict:
    svc = get_protocol_service()
    acts = svc.activities()
    return {"activities": acts, "count": len(acts)}


@router.get("/objects")
def protocol_objects() -> dict:
    svc = get_protocol_service()
    objs = svc.objects()
    return {"objects": objs, "count": len(objs)}


@router.get("/rules")
def protocol_rules() -> dict:
    svc = get_protocol_service()
    rules = svc.rules()
    return {"rules": rules, "count": len(rules)}


@router.get("/validate")
def protocol_validate() -> dict:
    svc = get_protocol_service()
    return svc.validate()


@router.post("/reload")
def protocol_reload() -> dict:
    svc = get_protocol_service()
    return svc.reload()
