"""Camera + voice verification tests (offline, no real webcam required)."""
from __future__ import annotations

import numpy as np

from agent.voice.voice_messages import (
    clean_for_speech,
    format_mission_guidance,
    translate_guidance,
)
from agent.voice.voice_service import VoiceGuidance
from backend.services.camera_service import (
    encode_bgr_to_jpeg,
    get_camera_service,
)


def test_camera_service_publish_and_jpeg():
    svc = get_camera_service()
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    assert svc.publish_frame_bgr(frame) is True
    jpeg = svc.get_jpeg()
    assert jpeg is not None and jpeg[:2] == b"\xff\xd8"
    assert encode_bgr_to_jpeg(frame) is not None
    status = svc.get_status()
    assert status["has_frame"] is True
    assert status["connected"] is True


def test_camera_api_routes_registered():
    from backend.main import app

    paths = [getattr(r, "path", "") for r in app.routes]
    assert "/api/camera/stream" in paths
    assert "/api/camera/snapshot" in paths
    assert "/api/camera/status" in paths
    assert "/api/camera/publish" in paths

    # Verify media type without consuming the infinite MJPEG body.
    stream_route = next(r for r in app.routes
                        if getattr(r, "path", "") == "/api/camera/stream")
    endpoint = getattr(stream_route, "endpoint", None)
    assert endpoint is not None
    import inspect

    src = inspect.getsource(endpoint)
    assert "multipart/x-mixed-replace; boundary=frame" in src


def test_camera_publish_roundtrip():
    import numpy as np

    from backend.services.camera_service import (
        encode_bgr_to_jpeg, get_camera_service)
    from backend.api.camera import camera_publish
    import asyncio

    jpeg = encode_bgr_to_jpeg(np.zeros((120, 160, 3), dtype=np.uint8))
    assert jpeg is not None

    class FakeRequest:
        def __init__(self, body: bytes):
            self._body = body

        async def body(self) -> bytes:
            return self._body

    out = asyncio.run(camera_publish(FakeRequest(jpeg)))
    assert out.get("ok") is True
    assert get_camera_service().get_jpeg() is not None


def test_camera_no_second_capture_site():
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[2]
    hits = []
    for path in list((root / "backend").rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "cv2.VideoCapture" in text:
            hits.append(str(path))
    assert hits == [], f"backend must not own cv2.VideoCapture: {hits}"


def test_wrong_object_guidance_contains_both_objects():
    text = format_mission_guidance(
        status="DEVIATION",
        deviation_type="WRONG_OBJECT",
        detected_object="experiment_controller",
        expected_object="sample_chamber",
    )
    assert "experiment controller" in text
    assert "sample chamber" in text
    assert "_" not in text


def test_wrong_sequence_guidance():
    text = format_mission_guidance(
        status="DEVIATION", deviation_type="WRONG_SEQUENCE", step_id="S003")
    assert "S003" in text


def test_low_confidence_guidance():
    text = format_mission_guidance(
        status="UNCERTAIN", deviation_type="LOW_CONFIDENCE")
    assert "steady" in text


def test_unknown_object_guidance():
    text = format_mission_guidance(
        status="DEVIATION", deviation_type="UNKNOWN_OBJECT",
        expected_object="sample_chamber")
    assert "sample chamber" in text


def test_hindi_wrong_object_uses_real_objects():
    text = translate_guidance(
        "Wrong action detected. experiment controller is not expected. "
        "Please use sample chamber.",
        language="hi", status="DEVIATION", deviation_type="WRONG_OBJECT",
        detected_object="experiment_controller",
        expected_object="sample_chamber", step_id="S003",
    )
    assert "एक्सपेरिमेंट कंट्रोलर" in text
    assert "सैंपल चैंबर" in text


def test_identifiers_naturalized():
    assert clean_for_speech("experiment_controller") == "experiment controller"
    assert clean_for_speech("sample_chamber") == "sample chamber"


def test_duplicate_wrong_object_spoken_once():
    voice = VoiceGuidance()
    first = voice.speak_decision(
        status="DEVIATION",
        guidance="Wrong action detected. experiment controller is not "
                 "expected. Please use sample chamber.",
        step_id="S003", deviation_type="WRONG_OBJECT",
        detected_object="experiment_controller",
        expected_object="sample_chamber")
    second = voice.speak_decision(
        status="DEVIATION",
        guidance="Wrong action detected. experiment controller is not "
                 "expected. Please use sample chamber.",
        step_id="S003", deviation_type="WRONG_OBJECT",
        detected_object="experiment_controller",
        expected_object="sample_chamber")
    assert first is True and second is False


def test_wrong_object_then_correct_speaks_again():
    voice = VoiceGuidance()
    voice.speak_decision(
        status="DEVIATION",
        guidance="Wrong action detected. experiment controller is not "
                 "expected. Please use sample chamber.",
        step_id="S003", deviation_type="WRONG_OBJECT",
        detected_object="experiment_controller",
        expected_object="sample_chamber")
    spoken = voice.speak_decision(
        status="CORRECT",
        guidance="Sample chamber opened. Proceed to transfer the sample.",
        step_id="S003")
    assert spoken is True


def test_controlled_mission_reaches_s008():
    from simulation.controlled_mission import (
        DEMO_STEPS, build_session, create_event)

    session = build_session()
    last = None
    for _label, obj, conf, hand in DEMO_STEPS:
        last = session.process_event(create_event(obj, conf, hand))
    assert last is not None and last["step_id"] == "S008"
    assert last["status"] == "COMPLETED"


def test_controlled_s003_wrong_object_message():
    from simulation.controlled_mission import build_session, create_event

    session = build_session()
    session.process_event(create_event("experiment_container", 0.98, True))
    session.process_event(create_event("biological_sample", 0.98, True))
    result = session.process_event(
        create_event("experiment_controller", 0.98, True))
    assert result["step_id"] == "S003"
    assert result["status"] == "DEVIATION"
    assert result["deviation_type"] == "WRONG_OBJECT"
    assert "experiment controller" in result["guidance"]
    assert "sample chamber" in result["guidance"]
