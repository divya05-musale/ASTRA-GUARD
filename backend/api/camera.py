"""ASTRA-GUARD camera API routes."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from backend.services.camera_service import (
    _placeholder_jpeg,
    encode_bgr_to_jpeg,
    get_camera_service,
    mjpeg_generator,
)
from backend.services.performance_service import get_performance_monitor

router = APIRouter()


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

    success = service.publish_external_jpeg(
        jpeg,
        width=width,
        height=height,
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


# ---------------------------------------------------------
# CAMERA STATUS
# ---------------------------------------------------------

@router.get("/camera/status")
def camera_status():
    """Return the current camera service status."""

    service = get_camera_service()

    return service.get_status()


@router.post("/camera/start")
def camera_start():
    """Start the local shared camera capture loop without touching mission state."""
    service = get_camera_service()
    if service.get_status()["external_stream"]:
        raise HTTPException(
            status_code=409,
            detail="The external perception pipeline currently owns the camera.",
        )
    service.ensure_started()
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