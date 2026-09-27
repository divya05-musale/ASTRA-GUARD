import numpy as np
import pytest
import threading

from agent.perception.webcam_runtime import WebcamRuntime


class FakeProcessor:
    def __init__(self):
        self.received_frames = []

    def process_frame(self, frame):
        self.received_frames.append(frame)

        return {
            "event": "fake_event",
            "result": {
                "status": "CORRECT",
            },
        }


def test_runtime_requires_processor():
    with pytest.raises(TypeError):
        WebcamRuntime(object())


def test_runtime_initial_state():
    processor = FakeProcessor()

    runtime = WebcamRuntime(
        processor,
        camera_index=0,
        width=1280,
        height=720,
    )

    assert runtime.camera_index == 0
    assert runtime.width == 1280
    assert runtime.height == 720
    assert runtime.capture is None


def test_read_frame_requires_open_camera():
    processor = FakeProcessor()

    runtime = WebcamRuntime(processor)

    with pytest.raises(RuntimeError):
        runtime.read_frame()


def test_process_once_sends_frame_to_processor(monkeypatch):
    processor = FakeProcessor()

    runtime = WebcamRuntime(processor)

    fake_frame = np.zeros(
        (720, 1280, 3),
        dtype=np.uint8,
    )

    class FakeCapture:
        def read(self):
            return True, fake_frame

    runtime.capture = FakeCapture()

    result = runtime.process_once()

    assert result["result"]["status"] == "CORRECT"

    assert len(
        processor.received_frames
    ) == 1

    assert (
        processor.received_frames[0] is fake_frame
    )


def test_failed_camera_read_is_rejected():
    processor = FakeProcessor()

    runtime = WebcamRuntime(processor)

    class FakeCapture:
        def read(self):
            return False, None

    runtime.capture = FakeCapture()

    with pytest.raises(RuntimeError):
        runtime.read_frame()


def test_release_clears_capture():
    processor = FakeProcessor()

    runtime = WebcamRuntime(processor)

    class FakeCapture:
        def __init__(self):
            self.released = False

        def release(self):
            self.released = True

    capture = FakeCapture()

    runtime.capture = capture

    runtime.release()

    assert capture.released is True
    assert runtime.capture is None


def test_capture_reader_processes_latest_unseen_frame(monkeypatch):
    frames = [
        np.full((2, 2, 3), value, dtype=np.uint8)
        for value in (1, 2, 3)
    ]
    ready = threading.Event()

    class FakeCapture:
        def __init__(self, **kwargs):
            self.index = 0

        def open(self):
            return self

        def read(self):
            if self.index < len(frames):
                frame = frames[self.index]
                self.index += 1
                if self.index == len(frames):
                    ready.set()
                return True, frame
            threading.Event().wait(0.005)
            return False, None

        def release(self):
            pass

    monkeypatch.setattr(
        "agent.perception.webcam_runtime.Camera",
        FakeCapture,
    )
    runtime = WebcamRuntime(FakeProcessor())
    runtime.open()
    try:
        assert ready.wait(timeout=1.0)
        latest = runtime.read_frame()
        assert latest is frames[-1]
        assert runtime._capture_sequence == 3
    finally:
        runtime.release()