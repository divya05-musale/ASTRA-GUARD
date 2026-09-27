"""Process uploaded local videos sequentially through live perception."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict

import cv2

from agent.perception.hand_tracker import HandTracker
from agent.perception.experiment_object_detector import ExperimentObjectDetector
from agent.perception.live_processor import LivePerceptionProcessor
from agent.perception.object_detector import ObjectDetector
from backend.services.camera_service import get_camera_service
from backend.services.mission_service import get_mission_service
from backend.services.session_store import PROJECT_ROOT, utc_timestamp


def process_video_session(session_id: str, video_path: str) -> None:
    """Run every video frame in source order; never skip for throughput."""
    service = get_mission_service()
    capture = None
    hand_tracker = None
    processed = 0
    total = 0
    last_status_update = 0.0
    try:
        model_path = PROJECT_ROOT / "yolo11n.pt"
        if not model_path.is_file():
            raise FileNotFoundError(f"Local YOLO weights are missing: {model_path}")

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise RuntimeError("OpenCV could not open the uploaded video")
        total = max(0, int(capture.get(cv2.CAP_PROP_FRAME_COUNT)))

        experiment_path = Path(service._protocol_path)
        detector = ExperimentObjectDetector(
            ObjectDetector(model_path=str(model_path)),
            experiment_path,
        )
        hand_tracker = HandTracker()
        processor = LivePerceptionProcessor(detector, hand_tracker, service)
        started = time.monotonic()
        service.update_video_processing(session_id, {
            "status": "PROCESSING",
            "frames_processed": 0,
            "total_frames": total,
            "started_at": utc_timestamp(),
        })

        while True:
            ok, frame = capture.read()
            if not ok:
                break

            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            source_timestamp = processed / fps if fps > 0 else time.monotonic()
            result = processor.process_frame(
                frame,
                source="video",
                captured_monotonic=source_timestamp,
            )
            display_frame = detector.draw_detections(frame, result["event"].objects)
            display_frame = hand_tracker.draw_landmarks(
                display_frame,
                result["event"].hands,
                copy_frame=False,
            )
            get_camera_service().publish_frame_bgr(display_frame)
            processed += 1

            now = time.monotonic()
            if processed % 10 == 0 or now - last_status_update >= 1.0:
                service.update_video_processing(session_id, {
                    "status": "PROCESSING",
                    "frames_processed": processed,
                    "total_frames": total,
                    "elapsed_seconds": round(now - started, 2),
                })
                last_status_update = now

            if service.get_progress().get("completed"):
                break

        record = service.get_session(session_id)
        if record and record.get("status") == "IN_PROGRESS":
            service.end_session("INCOMPLETE")
        service.update_video_processing(session_id, {
            "status": "COMPLETED",
            "frames_processed": processed,
            "total_frames": total,
            "finished_at": utc_timestamp(),
        })
    except Exception as exc:
        service.update_video_processing(session_id, {
            "status": "FAILED",
            "frames_processed": processed,
            "total_frames": total,
            "error": str(exc),
            "finished_at": utc_timestamp(),
        })
        record = service.get_session(session_id)
        if record and record.get("status") == "IN_PROGRESS":
            service.end_session("FAILED")
    finally:
        if capture is not None:
            capture.release()
        if hand_tracker is not None:
            hand_tracker.close()