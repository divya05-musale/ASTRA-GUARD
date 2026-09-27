import cv2
import numpy as np
from pathlib import Path

from backend.services import video_session_service


def test_video_frames_use_perception_and_publish_in_order(monkeypatch, tmp_path):
    (tmp_path / "yolo11n.pt").write_bytes(b"local model placeholder")
    monkeypatch.setattr(video_session_service, "PROJECT_ROOT", tmp_path)

    class Capture:
        def __init__(self, _path):
            self.index = 0

        def isOpened(self):
            return True

        def get(self, prop):
            return 3 if prop == cv2.CAP_PROP_FRAME_COUNT else 30

        def read(self):
            if self.index == 3:
                return False, None
            frame = np.full((8, 8, 3), self.index, dtype=np.uint8)
            self.index += 1
            return True, frame

        def release(self):
            pass

    class Detector:
        def __init__(self, model_path):
            assert model_path.endswith("yolo11n.pt")

        def detect(self, frame):
            return [{"name": str(int(frame[0, 0, 0]))}]

        def draw_detections(self, frame, _objects):
            return frame.copy()

    class Hands:
        def process(self, _frame):
            return []

        def draw_landmarks(self, frame, _hands, copy_frame=False):
            return frame

        def close(self):
            pass

    class Mission:
        def __init__(self):
            self._protocol_path = Path(__file__).resolve().parents[2] / "experiments" / "EXP001_TARDIGRADE"
            self.events = []
            self.video_state = None

        def process_event(self, event):
            self.events.append(event)
            return {"status": "CORRECT"}

        def get_progress(self):
            return {"completed": False}

        def get_session(self, _session_id):
            return {"status": "IN_PROGRESS"}

        def end_session(self, status):
            self.ended_as = status

        def update_video_processing(self, _session_id, state):
            self.video_state = state

    mission = Mission()
    published = []
    monkeypatch.setattr(video_session_service.cv2, "VideoCapture", Capture)
    monkeypatch.setattr(video_session_service, "ObjectDetector", Detector)
    monkeypatch.setattr(video_session_service, "HandTracker", Hands)
    monkeypatch.setattr(video_session_service, "get_mission_service", lambda: mission)
    monkeypatch.setattr(
        video_session_service,
        "get_camera_service",
        lambda: type("CameraService", (), {"publish_frame_bgr": lambda _self, frame: published.append(int(frame[0, 0, 0]) )})(),
    )

    video_session_service.process_video_session("session-id", "local-video.mp4")

    assert [event.objects[0]["name"] for event in mission.events] == ["0", "1", "2"]
    assert all(event.source == "video" for event in mission.events)
    assert published == [0, 1, 2]
    assert mission.ended_as == "INCOMPLETE"
    assert mission.video_state["frames_processed"] == 3