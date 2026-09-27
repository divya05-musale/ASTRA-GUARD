"""Live perception demo: YOLO objects + MediaPipe hands (Phase 6, local only)."""
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
from agent.perception.object_detector import ObjectDetector, ModelNotAvailableError
from agent.perception.hand_tracker import HandTracker, HandTrackerInitError
from agent.perception.perception_event import PerceptionEvent

WINDOW = "ASTRA-GUARD Perception Test"
logging.basicConfig(level=logging.INFO)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ASTRA-GUARD Phase 6 perception test (local only)")
    p.add_argument("--camera-index", type=int, default=0)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--model", type=str, default="yolo11n.pt")
    p.add_argument("--conf", type=float, default=0.40)
    p.add_argument("--display-width", type=int, default=960)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    camera = Camera(camera_index=args.camera_index, width=args.width, height=args.height)
    try:
        camera.open()
    except CameraOpenError as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Camera properties: {camera.get_properties()}")
    try:
        detector = ObjectDetector(model_path=args.model, confidence_threshold=args.conf)
    except ModelNotAvailableError as exc:
        print(f"ERROR: {exc}")
        camera.release()
        return 2
    print(f"YOLO model info: {detector.get_model_info()}")
    print("NOTE: pretrained YOLO detects generic objects (bottle, cup, ...), "
          "NOT biological_sample/sample_chamber/experiment_controller.")
    try:
        tracker = HandTracker()
    except HandTrackerInitError as exc:
        print(f"ERROR: {exc}")
        camera.release()
        return 3
    processor = FrameProcessor()
    print("Press Q to quit.")
    prev, fps, failures = time.time(), 0.0, 0
    try:
        while True:
            ok, frame = camera.read()
            if not ok or frame is None:
                failures += 1
                print(f"WARNING: frame read failed ({failures}).")
                if failures >= 30:
                    break
                continue
            failures = 0
            try:
                objects = detector.detect(frame)
            except Exception as exc:
                print(f"WARNING: detection failed: {exc}")
                objects = []
            try:
                hands = tracker.process(frame)
            except Exception as exc:
                print(f"WARNING: hand tracking failed: {exc}")
                hands = []
            event = PerceptionEvent(objects=objects, hands=hands)
            shown = detector.draw_detections(frame, objects)
            shown = tracker.draw_landmarks(shown, hands)
            shown = processor.resize(shown, width=args.display_width)
            now = time.time()
            dt = now - prev
            prev = now
            if dt > 0:
                fps = fps * 0.9 + (1.0 / dt) * 0.1 if fps else (1.0 / dt)
            cv2.putText(shown, f"FPS: {fps:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(shown, f"Objects: {len(event.objects)}  Hands: {len(event.hands)}",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(shown, "Press Q to quit", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow(WINDOW, shown)
            if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
                break
    finally:
        camera.release()
        try:
            tracker.close()
        except Exception:
            pass
        cv2.destroyAllWindows()
    print("Perception test closed cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
