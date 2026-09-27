"""Camera unit tests (mocked VideoCapture; no real webcam required)."""
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from agent.perception.camera import Camera, CameraOpenError


def _fake_cap(opened=True, frame=None, fail_read=False):
    cap = MagicMock()
    cap.isOpened.return_value = opened
    if fail_read:
        cap.read.return_value = (False, None)
    else:
        cap.read.return_value = (True, frame if frame is not None else np.zeros((480, 640, 3), dtype=np.uint8))
    cap.get.side_effect = lambda prop: 0
    return cap


def test_default_configuration():
    cam = Camera()
    assert (cam.camera_index, cam.requested_width, cam.requested_height) == (0, 1280, 720)


def test_custom_configuration():
    cam = Camera(camera_index=1, width=640, height=480, fps=15)
    assert (cam.camera_index, cam.requested_width, cam.requested_height) == (1, 640, 480)


def test_successful_open_with_mock():
    cam = Camera()
    with patch("agent.perception.camera.cv2.VideoCapture", return_value=_fake_cap(True)):
        cam.open()
        assert cam.is_opened()
        cam.release()
        assert not cam.is_opened()


def test_failed_open_raises():
    cam = Camera(camera_index=0)
    with patch("agent.perception.camera.cv2.VideoCapture", return_value=_fake_cap(False)):
        with pytest.raises(CameraOpenError, match="Unable to open camera"):
            cam.open()


def test_successful_frame_read():
    cam = Camera()
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    with patch("agent.perception.camera.cv2.VideoCapture", return_value=_fake_cap(True, frame)):
        cam.open()
        ok, out = cam.read()
        assert ok and out is frame
        cam.release()


def test_failed_frame_read():
    cam = Camera()
    with patch("agent.perception.camera.cv2.VideoCapture", return_value=_fake_cap(True, fail_read=True)):
        cam.open()
        ok, out = cam.read()
        assert ok is False and out is None
        cam.release()


def test_read_without_open_returns_failure():
    cam = Camera()
    ok, out = cam.read()
    assert ok is False and out is None


def test_get_properties():
    cam = Camera(camera_index=2, width=640, height=480, fps=15)
    props = cam.get_properties()
    assert props["camera_index"] == 2 and props["width"] == 640


def test_release_unopened_is_safe():
    Camera().release()
