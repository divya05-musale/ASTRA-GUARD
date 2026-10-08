"""
Tests for the ASTRA-GUARD bilingual mission voice guidance service.

Covers:
    1. English guidance
    2. Hindi guidance
    3. English -> Hindi switching
    4. Duplicate decision suppression
    5. New decision is spoken
    6. Mission reset clears deduplication state
    7. Voice OFF -> no speech, mission unaffected
    8. Missing Hindi voice -> no crash
    9. Technical identifiers are never spoken literally
   10. Controlled mission still reaches S008 COMPLETED (see
       tests/unit/test_controlled_mission_with_voice.py)
"""

from __future__ import annotations

from agent.voice.voice_service import VoiceGuidance
from agent.voice.voice_messages import clean_for_speech, translate_guidance


def _new_voice() -> VoiceGuidance:
    """Build a fresh, isolated VoiceGuidance for each test."""

    return VoiceGuidance()


# ---------------------------------------------------------------------
# Test 1 & 2: English and Hindi guidance
# ---------------------------------------------------------------------


def test_english_guidance_is_natural_and_untranslated():
    text = translate_guidance(
        "Wrong object detected. Please select the biological sample.",
        language="en",
        status="DEVIATION",
        deviation_type="WRONG_OBJECT",
    )

    assert text == "Wrong object detected. Please select the biological sample."


def test_hindi_guidance_uses_reviewed_translation():
    text = translate_guidance(
        "Wrong object detected. Please select the biological sample.",
        language="hi",
        status="DEVIATION",
        deviation_type="WRONG_OBJECT",
    )

    assert text == "गलत वस्तु पहचानी गई। कृपया सैंपल चुनें।"


def test_hindi_falls_back_to_generic_template_for_unknown_sentence():
    text = translate_guidance(
        "Some brand-new guidance sentence not seen before.",
        language="hi",
        status="DEVIATION",
        deviation_type="WRONG_OBJECT",
    )

    # Falls back to the generic WRONG_OBJECT Hindi template rather than
    # inventing a translation or crashing.
    assert "गलत क्रिया" in text


# ---------------------------------------------------------------------
# Test 3: English -> Hindi switching
# ---------------------------------------------------------------------


def test_language_switch_changes_next_guidance():
    voice = _new_voice()

    assert voice.language == "en"

    voice.set_language("hi")
    assert voice.language == "hi"

    spoken = voice.speak_decision(
        status="COMPLETED",
        guidance="Experiment completed successfully.",
        step_id="S008",
    )

    assert spoken is True
    assert voice.get_status()["last_guidance"] == "प्रयोग सफलतापूर्वक पूरा हुआ।"


def test_invalid_language_is_rejected():
    voice = _new_voice()

    try:
        voice.set_language("fr")
        assert False, "expected ValueError for unsupported language"
    except ValueError:
        pass

    # Language is unchanged after a rejected update.
    assert voice.language == "en"


# ---------------------------------------------------------------------
# Test 4 & 5: Duplicate suppression vs. genuinely new decisions
# ---------------------------------------------------------------------


def test_duplicate_decision_does_not_speak_twice():
    voice = _new_voice()

    first = voice.speak_decision(
        status="DEVIATION",
        guidance="Wrong object detected. Please select the biological sample.",
        step_id="S002",
        deviation_type="WRONG_OBJECT",
    )

    second = voice.speak_decision(
        status="DEVIATION",
        guidance="Wrong object detected. Please select the biological sample.",
        step_id="S002",
        deviation_type="WRONG_OBJECT",
    )

    assert first is True
    assert second is False


def test_repeated_important_status_is_still_deduplicated():
    """
    Regression test for the duplicate-voice bug: DEVIATION/UNCERTAIN/
    COMPLETED must NOT bypass duplicate suppression just because they
    are high priority. Only a genuinely new signature should speak.
    """

    voice = _new_voice()

    for _ in range(5):
        spoken = voice.speak_decision(
            status="UNCERTAIN",
            guidance="Detection confidence is low. Please repeat or hold the action for verification.",
            step_id="S001",
            deviation_type="LOW_CONFIDENCE",
        )

    # Only the first of the five identical repeated frames should speak.
    assert spoken is False


def test_new_mission_transition_is_spoken():
    voice = _new_voice()

    voice.speak_decision(
        status="CORRECT",
        guidance="Equipment check completed. Proceed to retrieve the sample.",
        step_id="S001",
    )

    spoken = voice.speak_decision(
        status="DEVIATION",
        guidance="Wrong object detected. Please select the biological sample.",
        step_id="S002",
        deviation_type="WRONG_OBJECT",
    )

    assert spoken is True


# ---------------------------------------------------------------------
# Test 6: Mission reset clears deduplication state
# ---------------------------------------------------------------------


def test_reset_clears_deduplication_state():
    voice = _new_voice()

    first = voice.speak_decision(
        status="DEVIATION",
        guidance="Wrong object detected. Please select the biological sample.",
        step_id="S002",
        deviation_type="WRONG_OBJECT",
    )

    voice.reset()

    second = voice.speak_decision(
        status="DEVIATION",
        guidance="Wrong object detected. Please select the biological sample.",
        step_id="S002",
        deviation_type="WRONG_OBJECT",
    )

    assert first is True
    assert second is True
    assert voice.get_status()["last_guidance"] is not None


def test_reset_does_not_wait_for_blocked_tts_engine():
    import time

    voice = _new_voice()
    voice._last_signature = ("S001", "UNCERTAIN", "LOW_CONFIDENCE", "marker missing")
    voice._last_guidance = "marker missing"
    voice._engine_lock.acquire()
    try:
        started = time.monotonic()
        voice.reset()
        elapsed = time.monotonic() - started
    finally:
        voice._engine_lock.release()

    assert elapsed < 1.0
    assert voice._last_signature is None
    assert voice.get_status()["last_guidance"] is None


# ---------------------------------------------------------------------
# Test 7: Voice OFF -> no speech, mission unaffected
# ---------------------------------------------------------------------


def test_voice_disabled_suppresses_speech_but_returns_cleanly():
    voice = _new_voice()

    voice.set_enabled(False)

    spoken = voice.speak_decision(
        status="DEVIATION",
        guidance="Wrong object detected. Please select the biological sample.",
        step_id="S002",
        deviation_type="WRONG_OBJECT",
    )

    assert spoken is False
    assert voice.get_status()["enabled"] is False


# ---------------------------------------------------------------------
# Test 8: Missing Hindi voice / missing TTS engine -> no crash
# ---------------------------------------------------------------------


def test_missing_tts_engine_does_not_crash():
    """
    On a host without pyttsx3 (or without any installed TTS engine),
    the service must degrade gracefully rather than raising.
    """

    voice = _new_voice()

    # In this sandbox pyttsx3 itself is typically unavailable, which
    # already exercises the "no engine" path end-to-end.
    spoken = voice.speak_decision(
        status="DEVIATION",
        guidance="Wrong object detected. Please select the biological sample.",
        step_id="S002",
        deviation_type="WRONG_OBJECT",
    )

    # Either the engine is unavailable (spoken reflects queueing being
    # skipped) or it is available — either way, no exception propagates.
    assert spoken in (True, False)
    status = voice.get_status()
    assert "hindi_voice_available" in status


def test_voice_status_reports_engine_readiness_truthfully():
    voice = _new_voice()
    voice._engine = None
    status = voice.get_status()
    assert status["online"] is False
    assert status["engine_ready"] is False


def test_hindi_language_without_hindi_voice_still_returns_text():
    voice = _new_voice()
    voice.set_language("hi")

    spoken = voice.speak_decision(
        status="COMPLETED",
        guidance="Experiment completed successfully.",
        step_id="S008",
    )

    assert spoken is True
    assert voice.get_status()["last_guidance"] == "प्रयोग सफलतापूर्वक पूरा हुआ।"


# ---------------------------------------------------------------------
# Test 9: Technical identifiers are never spoken literally
# ---------------------------------------------------------------------


def test_identifiers_are_naturalized_for_speech():
    assert clean_for_speech("check_equipment") == "check equipment"
    assert clean_for_speech("sample_chamber") == "sample chamber"
    assert clean_for_speech("experiment_controller") == "experiment controller"
    assert "underscore" not in clean_for_speech("check_equipment sample_chamber")


def test_identifiers_in_full_sentence_are_naturalized():
    text = clean_for_speech(
        "Unknown action detected. Expected activity check_equipment."
    )

    assert "_" not in text
    assert "underscore" not in text
    assert "check equipment" in text
