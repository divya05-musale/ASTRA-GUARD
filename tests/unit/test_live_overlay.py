import numpy as np
import pytest

from agent.perception.live_overlay import LiveOverlay


def test_overlay_draws_without_error():
    overlay = LiveOverlay()

    frame = np.zeros(
        (720, 1280, 3),
        dtype=np.uint8,
    )

    result = {
        "status": "CORRECT",
        "step_id": "S001",
        "perception": {
            "activity": "PICK_SAMPLE",
            "object": "biological_sample",
            "confidence": 0.92,
        },
    }

    annotated = overlay.draw(
        frame,
        result,
    )

    assert annotated.shape == frame.shape
    assert annotated.dtype == frame.dtype
    assert np.array_equal(annotated, frame)


def test_overlay_does_not_modify_original_frame():
    overlay = LiveOverlay()

    frame = np.zeros(
        (480, 640, 3),
        dtype=np.uint8,
    )

    original = frame.copy()

    result = {
        "status": "CORRECT",
        "step_id": "S001",
        "perception": {
            "activity": "PICK_SAMPLE",
            "object": "biological_sample",
            "confidence": 0.95,
        },
    }

    overlay.draw(
        frame,
        result,
    )

    assert np.array_equal(
        frame,
        original,
    )


def test_overlay_handles_missing_values():
    overlay = LiveOverlay()

    frame = np.zeros(
        (480, 640, 3),
        dtype=np.uint8,
    )

    result = {}

    annotated = overlay.draw(
        frame,
        result,
    )

    assert annotated.shape == frame.shape


def test_overlay_rejects_invalid_frame():
    overlay = LiveOverlay()

    with pytest.raises(ValueError):
        overlay.draw(
            None,
            {},
        )


def test_overlay_rejects_invalid_result():
    overlay = LiveOverlay()

    frame = np.zeros(
        (480, 640, 3),
        dtype=np.uint8,
    )

    with pytest.raises(TypeError):
        overlay.draw(
            frame,
            None,
        )


def test_confidence_is_clamped():
    overlay = LiveOverlay()

    assert overlay._safe_confidence(1.5) == 1.0
    assert overlay._safe_confidence(-0.5) == 0.0
    assert overlay._safe_confidence("invalid") == 0.0