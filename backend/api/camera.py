"""ASTRA-GUARD camera API routes."""

import time
import logging
import os

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse

from backend.core.config import get_settings
from backend.services.camera_service import (
    _CAMERA_START_TIMEOUT_SEC,
    _placeholder_jpeg,
    encode_bgr_to_jpeg,
    get_camera_service,
    mjpeg_generator,
)
from backend.services.performance_service import get_performance_monitor
from backend.services.browser_perception_service import (
    FrameQueueFullError,
    get_browser_perception_service,
)
from backend.schemas.camera import CameraSelectRequest
from agent.perception.camera import discover_cameras

router = APIRouter()
logger = logging.getLogger(__name__)
_MAX_BROWSER_FRAME_BYTES = 2 * 1024 * 1024


# ---------------------------------------------------------
# CAMERA SNAPSHOT
# ---------------------------------------------------------

@router.get("/camera/snapshot")
def camera_snapshot():
    """Return a single JPEG snapshot of the latest camera frame."""

    service = get_camera_service()
    data = service.get_jpeg()
    if data is None:
        data = _placeholder_jpeg("NO FRAME YET")
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


# ---------------------------------------------------------
# CAMERA STREAM
# ---------------------------------------------------------

@router.get("/camera/stream")
def camera_stream():
    """Stream the camera feed using MJPEG."""

    logger.info("MJPEG stream endpoint requested")
    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------
# PUBLISH EXTERNAL CAMERA FRAME
# ---------------------------------------------------------

@router.post("/camera/publish")
async def publish_camera_frame(request: Request):
    """Receive an annotated JPEG frame from run_live.py."""

    service = get_camera_service()

    jpeg = await request.body()

    if not jpeg:
        raise HTTPException(
            status_code=400,
            detail="Empty camera frame received.",
        )

    if len(jpeg) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Camera frame exceeds the 10 MB limit.",
        )

    # Validate JPEG start and end markers.
    if not (
        jpeg.startswith(b"\xff\xd8")
        and jpeg.endswith(b"\xff\xd9")
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid JPEG frame.",
        )

    try:
        width = int(request.headers.get("X-Frame-Width", "0")) or None
        height = int(request.headers.get("X-Frame-Height", "0")) or None
    except ValueError:
        width = height = None
    try:
        camera_index = int(request.headers.get("X-Camera-Index", ""))
    except ValueError:
        camera_index = None
    camera_source = request.headers.get("X-Camera-Source")
    camera_backend = request.headers.get("X-Camera-Backend")
    camera_backend_requested = request.headers.get("X-Camera-Backend-Requested")
    camera_source_name = request.headers.get("X-Camera-Source-Name")

    success = service.publish_external_jpeg(
        jpeg,
        width=width,
        height=height,
        camera_index=camera_index,
        camera_source=camera_source,
        camera_backend=camera_backend,
        camera_backend_requested=camera_backend_requested,
        camera_source_name=camera_source_name,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to publish camera frame.",
        )

    try:
        performance = request.headers.get("X-Performance-Metrics")
        metrics = __import__("json").loads(performance) if performance else None
        if isinstance(metrics, dict):
            get_performance_monitor().record_frame(metrics)
    except (TypeError, ValueError):
        pass

    return {
        "success": True,
        "message": "Camera frame published successfully.",
        "size_bytes": len(jpeg),
    }


@router.post("/camera/browser-frame")
async def process_browser_camera_frame(request: Request):
    """Validate and queue one browser JPEG for background live perception."""
    jpeg = await request.body()
    logger.debug("Browser frame request received bytes=%d", len(jpeg))
    if not jpeg:
        logger.warning("Browser frame rejected: empty request body")
        raise HTTPException(status_code=400, detail="Empty browser camera frame.")
    if len(jpeg) > _MAX_BROWSER_FRAME_BYTES:
        logger.warning("Browser frame rejected: payload too large size_bytes=%d", len(jpeg))
        raise HTTPException(status_code=413, detail="Browser camera frame exceeds the 2 MB limit.")
    if not jpeg.startswith(b"\xff\xd8") or not jpeg.endswith(b"\xff\xd9"):
        logger.warning("Browser frame rejected: invalid JPEG markers size_bytes=%d", len(jpeg))
        raise HTTPException(status_code=400, detail="Invalid JPEG frame.")

    frame = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None or frame.size == 0:
        logger.warning("Browser frame rejected: JPEG decode failed size_bytes=%d", len(jpeg))
        raise HTTPException(status_code=400, detail="Unable to decode browser camera frame.")
    logger.debug(
        "Browser frame JPEG decoded width=%d height=%d size_bytes=%d",
        frame.shape[1],
        frame.shape[0],
        len(jpeg),
    )
    if frame.shape[1] > 1920 or frame.shape[0] > 1080:
        logger.warning(
            "Browser frame rejected: dimensions exceed limit width=%d height=%d",
            frame.shape[1],
            frame.shape[0],
        )
        raise HTTPException(status_code=413, detail="Browser camera frame dimensions exceed 1920x1080.")

    camera = get_camera_service()
    published = camera.publish_external_jpeg(
        jpeg,
        width=frame.shape[1],
        height=frame.shape[0],
        camera_source="laptop",
        camera_source_name="Browser Webcam",
    )
    if not published:
        logger.warning("Browser frame rejected by camera validation size_bytes=%d", len(jpeg))
        raise HTTPException(status_code=400, detail="Browser frame was rejected by camera validation.")
    try:
        accepted = get_browser_perception_service().enqueue_frame(frame)
    except FrameQueueFullError as exc:
        logger.warning(
            "Browser frame not accepted: processing queue full width=%d height=%d",
            frame.shape[1],
            frame.shape[0],
        )
        raise HTTPException(
            status_code=429,
            detail="Browser frame processing queue is full; retry shortly.",
            headers={"Retry-After": "1"},
        ) from exc
    except Exception as exc:
        logger.exception("Browser frame could not be queued")
        raise HTTPException(status_code=503, detail=f"Browser frame perception is unavailable: {exc}") from exc

    return {
        "success": True,
        "accepted": True,
        "message": "Browser camera frame accepted for processing.",
        "size_bytes": len(jpeg),
        "event": None,
        "result": None,
        "timings_ms": None,
        **accepted,
    }


# ---------------------------------------------------------
# CAMERA STATUS
# ---------------------------------------------------------

@router.get("/camera/status")
def camera_status():
    """Return the current camera service status."""

    service = get_camera_service()

    return service.get_status()


@router.post("/camera/select")
def camera_select(selection: CameraSelectRequest):
    """Select the local OpenCV camera device and source label."""
    settings = get_settings()
    if settings.is_cloud_mode() or not settings.ENABLE_LIVE_PROCESSOR:
        raise HTTPException(
            status_code=503,
            detail="Local camera selection is unavailable in cloud mode.",
        )

    service = get_camera_service()
    if os.environ.get("ASTRA_GUARD_LIVE_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}:
        try:
            request = service.request_live_camera_selection(
                selection.camera_index,
                selection.source,
                selection.backend,
                selection.source_name,
            )
            return {"success": True, "pending": True, **request}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    if service.get_status()["external_stream"]:
        raise HTTPException(
            status_code=409,
            detail="The external perception pipeline currently owns the camera.",
        )
    try:
        return {
            "success": True,
            **service.select_camera(
                selection.camera_index,
                selection.source,
                selection.backend,
                selection.source_name,
            ),
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/camera/discover")
def camera_discover(
    max_index: int = 5,
    backends: list[str] = Query(default=["dshow", "msmf"]),
):
    """Probe a bounded range of camera indices without competing with capture."""
    settings = get_settings()
    if settings.is_cloud_mode() or not settings.ENABLE_LIVE_PROCESSOR:
        raise HTTPException(
            status_code=503,
            detail="Local camera discovery is unavailable in cloud mode.",
        )

    service = get_camera_service()
    status = service.get_status()
    live_enabled = os.environ.get("ASTRA_GUARD_LIVE_ENABLED", "0").strip().lower() in {
        "1", "true", "yes", "on",
    }
    if live_enabled or status["capture_running"] or status["external_stream"]:
        raise HTTPException(
            status_code=409,
            detail="Stop ASTRA-GUARD camera capture before running discovery; discovery never probes an active camera owner.",
        )
    if max_index < 0 or max_index > 20:
        raise HTTPException(status_code=422, detail="max_index must be between 0 and 20.")
    try:
        results = discover_cameras(range(max_index + 1), backends)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "results": results,
        "camera_names_identifiable": False,
        "message": "OpenCV indices and backend tests do not reliably identify camera names.",
    }


@router.get("/camera/control")
def camera_control(after_generation: int = 0):
    """Return a pending device request to the live perception process."""
    if after_generation < 0:
        raise HTTPException(status_code=422, detail="after_generation must be zero or greater.")
    return {"selection": get_camera_service().get_live_camera_control(after_generation)}


@router.post("/camera/control/result")
def camera_control_result(payload: dict):
    """Record whether the live process applied a camera device request."""
    try:
        generation = int(payload["generation"])
        error = payload.get("error")
        if error is not None and not isinstance(error, str):
            raise ValueError
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="generation and optional error are required.") from exc
    get_camera_service().complete_live_camera_selection(generation, error)
    return {"success": True}


@router.post("/camera/start")
def camera_start():
    """Start the local shared camera capture loop without touching mission state."""
    settings = get_settings()
    if settings.is_cloud_mode() or not settings.ENABLE_LIVE_PROCESSOR:
        raise HTTPException(
            status_code=503,
            detail="Camera capture is unavailable in cloud mode.",
        )

    service = get_camera_service()
    if os.environ.get("ASTRA_GUARD_LIVE_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}:
        raise HTTPException(
            status_code=409,
            detail="The live perception pipeline owns the camera while ASTRA-GUARD is running with --live.",
        )
    if service.get_status()["external_stream"]:
        raise HTTPException(
            status_code=409,
            detail="The external perception pipeline currently owns the camera.",
        )
    started_at = time.monotonic()
    service.ensure_started()
    if not service.wait_for_local_frame(started_at, _CAMERA_START_TIMEOUT_SEC):
        status = service.get_status()
        detail = status["error"] or "Camera did not produce a frame before the startup timeout."
        service.stop()
        raise HTTPException(status_code=503, detail=detail)
    return {"success": True, **service.get_status()}


@router.post("/camera/stop")
def camera_stop():
    """Stop local capture and release the camera without touching mission state."""
    service = get_camera_service()
    if service.get_status()["external_stream"]:
        raise HTTPException(
            status_code=409,
            detail="The external perception pipeline currently owns the camera.",
        )
    service.stop()
    return {"success": True, **service.get_status()}