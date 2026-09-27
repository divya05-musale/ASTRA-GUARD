"""FrameProcessor tests on synthetic NumPy arrays (no external images)."""
import numpy as np
import pytest

from agent.perception.frame_processor import FrameProcessor


def test_resize_exact_dimensions():
    p = FrameProcessor()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    out = p.resize(frame, width=640, height=360)
    assert out.shape == (360, 640, 3)


def test_resize_width_only_preserves_aspect():
    p = FrameProcessor()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    out = p.resize(frame, width=320)
    assert out.shape == (240, 320, 3)


def test_grayscale_conversion():
    p = FrameProcessor()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    gray = p.convert_to_gray(frame)
    assert gray.shape == (480, 640) and gray.dtype == np.uint8


def test_frame_info_bgr():
    p = FrameProcessor()
    info = p.calculate_frame_info(np.zeros((480, 640, 3), dtype=np.uint8))
    assert info == {"width": 640, "height": 480, "channels": 3, "dtype": "uint8"}


def test_frame_info_gray():
    p = FrameProcessor()
    info = p.calculate_frame_info(np.zeros((100, 200), dtype=np.uint8))
    assert info["channels"] == 1 and info["width"] == 200


def test_invalid_frames_raise():
    p = FrameProcessor()
    with pytest.raises(ValueError):
        p.resize(None, width=100)
    with pytest.raises(ValueError):
        p.resize(np.zeros((10, 10, 3), dtype=np.uint8))
    with pytest.raises(ValueError):
        p.convert_to_gray(None)
    with pytest.raises(ValueError):
        p.calculate_frame_info(None)
