"""
Test 10 from the voice integration spec: running the existing
controlled mission end-to-end must still reach S008 COMPLETED with
the bilingual voice assistant wired into LivePerceptionSession.
"""

from __future__ import annotations

from simulation.controlled_mission import (
    DEMO_STEPS,
    build_session,
    create_event,
)


def test_controlled_mission_still_reaches_completion_with_voice():
    session = build_session()

    last_result = None

    for _label, object_name, confidence, hand_interaction in DEMO_STEPS:
        event = create_event(object_name, confidence, hand_interaction)
        last_result = session.process_event(event)

    assert last_result is not None
    assert last_result["status"] == "COMPLETED"
    assert last_result["step_id"] == "S008"


def test_controlled_mission_reset_allows_voice_to_speak_again():
    session = build_session()

    for _label, object_name, confidence, hand_interaction in DEMO_STEPS:
        event = create_event(object_name, confidence, hand_interaction)
        session.process_event(event)

    assert session.get_last_result()["status"] == "COMPLETED"

    session.reset()

    assert session.voice_guidance.get_status()["last_guidance"] is None

    first_event = create_event(*DEMO_STEPS[0][1:])
    result = session.process_event(first_event)

    assert result["status"] == "CORRECT"
    assert result["step_id"] == "S001"
