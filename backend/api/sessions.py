"""Local session lifecycle, review, and JSON/CSV export routes."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response

from backend.schemas.session import (
    ManualConfirmationRequest,
    SessionActionRequest,
    SessionEndRequest,
    SessionStartRequest,
)
from backend.services.experiment_service import find_valid_experiment
from backend.services.mission_service import (
    get_mission_service,
    reset_mission_service,
)
from backend.services.protocol_service import reset_protocol_service
from backend.services.session_store import PROJECT_ROOT
from backend.services.video_session_service import process_video_session

router = APIRouter()
VIDEO_ROOT = PROJECT_ROOT / "data" / "videos"
EVIDENCE_ROOT = PROJECT_ROOT / "data" / "execution"
MAX_VIDEO_BYTES = 2 * 1024 * 1024 * 1024
VIDEO_EXTENSIONS = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".wmv"}


@router.get("/sessions")
def list_sessions() -> dict:
    sessions = get_mission_service().list_sessions()
    return {"sessions": sessions, "count": len(sessions)}


@router.post("/sessions/start")
def start_session(payload: SessionStartRequest) -> dict:
    current = get_mission_service()
    if current.active_session_id:
        record = current.get_session(current.active_session_id)
        if record and record.get("status") == "IN_PROGRESS":
            raise HTTPException(status_code=409, detail="An experiment session is already in progress")

    experiment_path = find_valid_experiment(payload.experiment_id)
    if experiment_path is None:
        raise HTTPException(status_code=404, detail="A valid local protocol for this experiment was not found")

    current = reset_mission_service(experiment_path)
    reset_protocol_service(experiment_path)
    try:
        record = current.start_session(
            input_source=payload.input_source,
            evidence_path=payload.evidence_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"session": record, "progress": current.get_progress()}


@router.post("/sessions/video/start")
async def start_video_session(
    background_tasks: BackgroundTasks,
    request: Request,
    experiment_id: str,
    filename: str,
) -> dict:
    """Stream a local video upload to disk and queue chronological processing."""
    experiment_path = find_valid_experiment(experiment_id)
    if experiment_path is None:
        raise HTTPException(status_code=404, detail="A valid local protocol for this experiment was not found")
    safe_name = Path(filename).name
    suffix = Path(safe_name).suffix.lower()
    if suffix not in VIDEO_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported video file extension")

    current = get_mission_service()
    if current.active_session_id:
        active = current.get_session(current.active_session_id)
        if active and active.get("status") == "IN_PROGRESS":
            raise HTTPException(status_code=409, detail="An experiment session is already in progress")

    length = request.headers.get("content-length")
    if length:
        try:
            if int(length) > MAX_VIDEO_BYTES:
                raise HTTPException(status_code=413, detail="Video exceeds the 2 GB limit")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Content-Length") from exc

    VIDEO_ROOT.mkdir(parents=True, exist_ok=True)
    temporary_path = VIDEO_ROOT / f"upload-{__import__('uuid').uuid4().hex}{suffix}.part"
    size = 0
    try:
        with temporary_path.open("wb") as output:
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_VIDEO_BYTES:
                    raise HTTPException(status_code=413, detail="Video exceeds the 2 GB limit")
                output.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="Video upload is empty")

        current = reset_mission_service(experiment_path)
        reset_protocol_service(experiment_path)
        record = current.start_session(input_source="video", evidence_path=str(temporary_path))
        final_path = VIDEO_ROOT / f"{record['session_id']}{suffix}"
        temporary_path.replace(final_path)
        current._session_store.update(record["session_id"], {
            "evidence": [{"path": str(final_path), "kind": "video", "name": safe_name}],
        })
        background_tasks.add_task(process_video_session, record["session_id"], str(final_path))
        return {"session": current.get_session(record["session_id"]), "progress": current.get_progress()}
    except HTTPException:
        temporary_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temporary_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Could not start video session: {exc}") from exc


@router.get("/sessions/{session_id}")
def get_session(session_id: str, event_limit: int = Query(default=200, ge=0, le=1000)) -> dict:
    try:
        record = get_mission_service().get_session_review(session_id)
    except ValueError:
        record = None
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    all_events = record.get("events", [])
    record["events_total"] = len(all_events)
    record["events_truncated"] = len(all_events) > event_limit
    record["events"] = all_events[-event_limit:] if event_limit else []
    return record


@router.post("/sessions/{session_id}/end")
def end_session(session_id: str, payload: SessionEndRequest) -> dict:
    service = get_mission_service()
    if service.active_session_id != session_id:
        raise HTTPException(status_code=404, detail="Session is not the active session")
    try:
        record = service.end_session(payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"session": record}


@router.post("/sessions/{session_id}/confirm")
def confirm_uncertain_session_step(
    session_id: str,
    payload: ManualConfirmationRequest,
) -> dict:
    try:
        result = get_mission_service().confirm_uncertain(
            session_id,
            payload.operator,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result


@router.post("/sessions/{session_id}/actions")
def perform_session_action(session_id: str, payload: SessionActionRequest) -> dict:
    try:
        result = get_mission_service().perform_session_action(
            session_id,
            payload.action,
            payload.operator,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result


@router.get("/sessions/{session_id}/export")
def export_session(session_id: str, format: str = "json") -> Response:
    try:
        record = get_mission_service().get_session(session_id)
    except ValueError:
        record = None
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if format == "json":
        return Response(
            content=json.dumps(record, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{session_id}.json"'},
        )
    if format != "csv":
        raise HTTPException(status_code=422, detail="format must be json or csv")

    stream = io.StringIO(newline="")
    fields = [
        "session_id", "experiment_id", "experiment_name", "input_source",
        "started_at", "completed_at", "status", "decision_source",
        "timestamp", "step_id", "activity", "detected_object", "confidence",
        "decision_status", "deviation", "guidance", "manual_operator",
        "manual_confirmed_at", "evidence_captured", "evidence_references",
        "water_quantity_measured",
    ]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for event in record.get("events", []):
        perception = event.get("perception") or {}
        decision = event.get("decision") or {}
        manual = event.get("manual_confirmation") or {}
        object_metadata = (perception.get("metadata") or {}).get("object_metadata") or {}
        writer.writerow({
            "session_id": record.get("session_id"),
            "experiment_id": record.get("experiment_id"),
            "experiment_name": record.get("experiment_name"),
            "input_source": record.get("input_source"),
            "started_at": record.get("started_at"),
            "completed_at": record.get("completed_at"),
            "status": record.get("status"),
            "decision_source": event.get("decision_source"),
            "timestamp": event.get("timestamp"),
            "step_id": decision.get("step_id"),
            "activity": perception.get("activity"),
            "detected_object": perception.get("object"),
            "confidence": perception.get("confidence"),
            "decision_status": decision.get("status"),
            "deviation": decision.get("deviation_type"),
            "guidance": decision.get("guidance"),
            "manual_operator": manual.get("operator"),
            "manual_confirmed_at": manual.get("confirmed_at"),
            "evidence_captured": bool(record.get("evidence")),
            "evidence_references": ";".join(
                str(item.get("path"))
                for item in record.get("evidence", [])
                if item.get("path")
            ),
            "water_quantity_measured": object_metadata.get("water_quantity_measured"),
        })
    return Response(
        content=stream.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{session_id}.csv"'},
    )


@router.get("/sessions/{session_id}/video")
def play_session_video(session_id: str) -> FileResponse:
    try:
        record = get_mission_service().get_session(session_id)
    except ValueError:
        record = None
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    evidence = next((
        item for item in record.get("evidence", [])
        if item.get("kind") == "video" and item.get("path")
    ), None)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Session has no video evidence")
    video_path = Path(evidence["path"]).resolve()
    if not video_path.is_relative_to(VIDEO_ROOT.resolve()) or not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video evidence is unavailable")
    return FileResponse(video_path, filename=video_path.name)


@router.get("/sessions/{session_id}/evidence/{evidence_name}")
def get_session_image_evidence(session_id: str, evidence_name: str) -> FileResponse:
    try:
        record = get_mission_service().get_session(session_id)
    except ValueError:
        record = None
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    evidence = next((
        item for item in record.get("evidence", [])
        if item.get("kind") == "image"
        and Path(str(item.get("path", ""))).name == evidence_name
    ), None)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Image evidence not found")
    image_path = Path(evidence["path"]).resolve()
    if not image_path.is_relative_to(EVIDENCE_ROOT.resolve()) or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image evidence is unavailable")
    return FileResponse(image_path, media_type="image/jpeg", filename=image_path.name)