"""Manual webcam test: local OpenCV preview with FPS overlay (Phase 5)."""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.perception.camera import Camera, CameraOpenError
from agent.perception.frame_processor import FrameProcessor

WINDOW = "ASTRA-GUARD Camera Test"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ASTRA-GUARD Phase 5 camera test (local only)")
    p.add_argument("--camera-index", type=int, default=0)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--display-width", type=int, default=960)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    camera = Camera(camera_index=args.camera_index, width=args.width,
                    height=args.height, fps=args.fps)
    try:
        camera.open()
    except CameraOpenError as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Camera properties: {camera.get_properties()}")
    print("Press Q to quit.")
    processor = FrameProcessor()
    failures = 0
    prev = time.time()
    fps_display = 0.0
    try:
        while True:
            success, frame = camera.read()
            if not success or frame is None:
                failures += 1
                print(f"WARNING: frame read failed ({failures}).")
                if failures >= 30:
                    print("Too many consecutive frame failures. Exiting.")
                    break
                continue
            failures = 0
            shown = processor.resize(frame, width=args.display_width)
            now = time.time()
            dt = now - prev
            prev = now
            if dt > 0:
                fps_display = fps_display * 0.9 + (1.0 / dt) * 0.1 if fps_display else (1.0 / dt)
            info = processor.calculate_frame_info(shown)
            cv2.putText(shown, f"FPS: {fps_display:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(shown, f"Resolution: {info['width']}x{info['height']}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(shown, f"Camera: {args.camera_index}", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(shown, "Press Q to quit", (10, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow(WINDOW, shown)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q")):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()
    print("Camera test closed cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
