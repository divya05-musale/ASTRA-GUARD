import threading
import asyncio

import numpy as np

from backend.services.camera_service import (
    CameraService,
    encode_bgr_to_jpeg,
    mjpeg_generator,
)
import backend.services.camera_service as camera_service_module
import backend.api.camera as camera_api
import pytest
from fastapi import HTTPException


def test_external_frame_status_includes_resolution_and_count():
    service = CameraService()
    frame = np.full((240, 320, 3), 120, dtype=np.uint8)
    jpeg = encode_bgr_to_jpeg(frame)

    assert jpeg is not None
    assert service.publish_external_jpeg(jpeg, width=320, height=240)
    status = service.get_status()

    assert status["width"] == 320
    assert status["height"] == 240
    assert status["frames_captured"] == 1


def test_external_frame_rejects_black_jpeg():
    service = CameraService()
    jpeg = encode_bgr_to_jpeg(np.zeros((240, 320, 3), dtype=np.uint8))

    assert jpeg is not None
    assert service.publish_external_jpeg(jpeg) is False
    assert service.get_status()["frames_captured"] == 0


def test_mjpeg_stream_waits_for_new_frame(monkeypatch):
    service = CameraService()
    first_frame = np.full((16, 16, 3), 120, dtype=np.uint8)
    second_frame = np.full((16, 16, 3), 255, dtype=np.uint8)
    first_jpeg = encode_bgr_to_jpeg(first_frame)
    second_jpeg = encode_bgr_to_jpeg(second_frame)
    assert first_jpeg is not None and second_jpeg is not None
    service.publish_external_jpeg(first_jpeg)
    monkeypatch.setattr(
        camera_service_module,
        "get_camera_service",
        lambda: service,
    )
    stream = mjpeg_generator()
    first_part = next(stream)
    assert first_part.startswith(b"--frame\r\nContent-Type: image/jpeg\r\n")
    assert first_jpeg in first_part

    ready = threading.Event()
    next_part = []

    def read_next_part():
        next_part.append(next(stream))
        ready.set()

    reader = threading.Thread(target=read_next_part)
    reader.start()
    try:
        assert not ready.wait(timeout=0.05)
        service.publish_external_jpeg(second_jpeg)
        assert ready.wait(timeout=1.0)
        assert second_jpeg in next_part[0]
    finally:
        stream.close()
        reader.join(timeout=1.0)


def test_publish_route_keeps_resolution_metadata(monkeypatch):
    service = CameraService()
    jpeg = encode_bgr_to_jpeg(np.full((24, 32, 3), 120, dtype=np.uint8))
    assert jpeg is not None

    class FakeRequest:
        headers = {"X-Frame-Width": "32", "X-Frame-Height": "24"}

        async def body(self):
            return jpeg

    monkeypatch.setattr(camera_api, "get_camera_service", lambda: service)
    result = asyncio.run(camera_api.publish_camera_frame(FakeRequest()))

    assert result["success"] is True
    assert service.get_status()["width"] == 32
    assert service.get_status()["height"] == 24


def test_camera_start_is_idempotent_and_stop_releases_resource(monkeypatch):
    created = []

    class FakeCamera:
        def __init__(self, **_kwargs):
            self.released = False
            self.frame = np.full((240, 320, 3), 120, dtype=np.uint8)
            created.append(self)

        def open(self):
            return self

        def is_opened(self):
            return not self.released

        def read(self):
            return True, self.frame

        def release(self):
            self.released = True

    monkeypatch.setattr("agent.perception.camera.Camera", FakeCamera)
    service = CameraService()
    monkeypatch.setattr(camera_api, "get_camera_service", lambda: service)

    started = camera_api.camera_start()
    first_thread = service._thread
    second_start = camera_api.camera_start()

    assert started["enabled"] is True
    assert second_start["capture_running"] is True
    assert service._thread is first_thread
    assert len(created) == 1

    stopped = camera_api.camera_stop()

    assert stopped["enabled"] is False
    assert stopped["capture_running"] is False
    assert service.get_status()["camera_open"] is False
    assert created[0].released is True


def test_camera_lifecycle_refuses_external_camera_owner(monkeypatch):
    service = CameraService()
    jpeg = encode_bgr_to_jpeg(np.full((16, 16, 3), 120, dtype=np.uint8))
    assert jpeg is not None
    assert service.publish_external_jpeg(jpeg)
    monkeypatch.setattr(camera_api, "get_camera_service", lambda: service)

    with pytest.raises(HTTPException) as error:
        camera_api.camera_start()

    assert error.value.status_code == 409
    assert service._thread is None