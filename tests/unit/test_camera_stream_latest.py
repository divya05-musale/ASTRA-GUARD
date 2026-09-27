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


def test_external_frame_status_includes_resolution_and_count():
    service = CameraService()
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    jpeg = encode_bgr_to_jpeg(frame)

    assert jpeg is not None
    assert service.publish_external_jpeg(jpeg, width=320, height=240)
    status = service.get_status()

    assert status["width"] == 320
    assert status["height"] == 240
    assert status["frames_captured"] == 1


def test_mjpeg_stream_waits_for_new_frame(monkeypatch):
    service = CameraService()
    first_frame = np.zeros((16, 16, 3), dtype=np.uint8)
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
    jpeg = encode_bgr_to_jpeg(np.zeros((24, 32, 3), dtype=np.uint8))
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