"""
ASTRA-GUARD Mission-Aware Offline Bilingual Voice Guidance.

Speaks mission guidance produced by the existing protocol/decision
engine using local, offline text-to-speech (pyttsx3 / Windows SAPI5).
No internet connection or API key is required.

This module NEVER decides whether an astronaut is correct or
incorrect — it only converts a decision the protocol engine already
made into natural, bilingual (English/Hindi) speech.

Design summary
---------------
* A single background worker thread drains a small speech queue, so
  concurrent mission events never spawn overlapping TTS threads and
  never block the perception/camera loop.
* Duplicate speech is prevented using a mission-decision signature
  (step_id, status, deviation_type, guidance) rather than a fixed
  timer — a genuinely new mission transition is always spoken, a
  repeated identical decision is spoken once.
* Voice language (English/Hindi) and enabled/disabled state are
  runtime-toggleable and safe to change from the dashboard.
* Any TTS failure (including a missing Hindi voice or a missing TTS
  engine entirely) is caught and logged; the mission keeps running.
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Dict, List, Optional, Tuple

from agent.voice.voice_language import (
    DEFAULT_LANGUAGE,
    ENGLISH,
    HINDI,
    normalize_language,
)
from agent.voice.voice_messages import clean_for_speech, translate_guidance

try:
    import pyttsx3
except ImportError:  # pragma: no cover - exercised on hosts without pyttsx3
    pyttsx3 = None


# A mission-decision "signature" used for duplicate suppression.
Signature = Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]

_SENTINEL = object()


class VoiceGuidance:
    """Mission-aware, offline, bilingual text-to-speech service."""

    def __init__(
        self,
        rate: int = 165,
        volume: float = 1.0,
    ) -> None:
        self.rate = rate
        self.volume = volume

        self.language: str = DEFAULT_LANGUAGE
        self.enabled: bool = True

        self._state_lock = threading.Lock()
        self._engine_lock = threading.Lock()

        self._last_signature: Optional[Signature] = None
        self._last_guidance: Optional[str] = None
        self._last_guidance_en: Optional[str] = None

        self._voices_by_language: Dict[str, Optional[str]] = {}
        self.hindi_voice_available = False

        self._engine = self._init_engine()

        # Single persistent worker: guarantees speech is serialized
        # and that camera/perception processing is never blocked
        # waiting for speech to finish.
        self._queue: "queue.Queue[Any]" = queue.Queue()
        self._worker = threading.Thread(
            target=self._run_worker,
            daemon=True,
        )
        self._worker.start()

    # ------------------------------------------------------------
    # Engine / voice setup
    # ------------------------------------------------------------

    def _init_engine(self):
        """Initialize the local TTS engine. Never raises."""

        if pyttsx3 is None:
            print(
                "[VOICE] pyttsx3 is not installed. "
                "Voice guidance is disabled; the mission continues normally."
            )
            return None

        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)
            self._discover_voices(engine)
            return engine
        except Exception as exc:  # pragma: no cover - platform dependent
            print(f"[VOICE] Failed to initialize TTS engine: {exc}")
            return None

    def _discover_voices(self, engine) -> None:
        """
        Discover installed voices and pick a safe voice per language.

        Never hardcodes a Windows voice ID. If no Hindi-compatible
        voice is installed, ``hindi_voice_available`` is set to False
        and Hindi guidance falls back to the engine's default voice
        instead of crashing.
        """

        try:
            voices = engine.getProperty("voices") or []
        except Exception as exc:  # pragma: no cover - platform dependent
            print(f"[VOICE] Could not read installed voices: {exc}")
            voices = []

        english_voice = None
        hindi_voice = None

        for voice in voices:
            haystack = " ".join(
                str(part).lower()
                for part in (
                    getattr(voice, "id", "") or "",
                    getattr(voice, "name", "") or "",
                    " ".join(
                        str(lang) for lang in (getattr(voice, "languages", None) or [])
                    ),
                )
            )

            if hindi_voice is None and (
                "hindi" in haystack or "hi_in" in haystack or "hi-in" in haystack
            ):
                hindi_voice = voice.id

            if english_voice is None and (
                "english" in haystack or "en_" in haystack or "en-" in haystack
            ):
                english_voice = voice.id

        if english_voice is None and voices:
            # Fall back to whatever the engine considers its first
            # installed voice rather than leaving English silent.
            english_voice = voices[0].id

        self._voices_by_language[ENGLISH] = english_voice
        self._voices_by_language[HINDI] = hindi_voice
        self.hindi_voice_available = hindi_voice is not None

        if not self.hindi_voice_available:
            print(
                "[VOICE] No Hindi-compatible voice was found on this system. "
                "Hindi guidance will use the default installed voice. "
                "English voice guidance is unaffected."
            )

    def _apply_voice_for_language(self, language: str) -> None:
        if self._engine is None:
            return

        voice_id = self._voices_by_language.get(language)

        if voice_id is None:
            return

        try:
            self._engine.setProperty("voice", voice_id)
        except Exception as exc:  # pragma: no cover - platform dependent
            print(f"[VOICE] Could not select voice for '{language}': {exc}")

    # ------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------

    def set_language(self, language: str) -> str:
        """Set the active mission voice language ('en' or 'hi')."""

        normalized = normalize_language(language)

        with self._state_lock:
            self.language = normalized

        return normalized

    def set_enabled(self, enabled: bool) -> None:
        """
        Enable or disable spoken guidance.

        Mission processing, the dashboard, and event history are
        never affected by this flag — only speech output is.
        """

        with self._state_lock:
            self.enabled = bool(enabled)

        if not self.enabled:
            self.stop()

    def get_status(self) -> Dict[str, Any]:
        """Return a snapshot of voice state for the dashboard/API."""

        with self._state_lock:
            return {
                "online": self._engine is not None,
                "engine_ready": self._engine is not None,
                "language": self.language,
                "enabled": self.enabled,
                "hindi_voice_available": self.hindi_voice_available,
                "last_guidance": self._last_guidance,
                "last_guidance_en": self._last_guidance_en,
            }

    # ------------------------------------------------------------
    # Speaking
    # ------------------------------------------------------------

    def speak(
        self,
        message: str,
        language: Optional[str] = None,
        force: bool = True,
    ) -> bool:
        """
        Speak arbitrary text immediately (bypassing decision dedup).

        Intended for direct/manual use. Mission guidance should go
        through ``speak_decision`` instead, which applies mission-aware
        duplicate suppression.
        """

        if not message:
            return False

        with self._state_lock:
            enabled = self.enabled
            active_language = language or self.language

        if not enabled:
            return False

        speech_text = clean_for_speech(str(message).strip(), language=active_language)

        if not speech_text:
            return False

        with self._state_lock:
            self._last_guidance = speech_text
            self._last_guidance_en = clean_for_speech(str(message).strip(), language=ENGLISH)

        self._enqueue(speech_text, active_language)

        return True

    def speak_decision(
        self,
        status: str,
        guidance: str,
        step_id: Optional[str] = None,
        deviation_type: Optional[str] = None,
        force: bool = False,
        detected_object: Optional[str] = None,
        expected_object: Optional[str] = None,
        next_step_id: Optional[str] = None,
    ) -> bool:
        """
        Speak mission guidance for one protocol decision.

        Duplicate suppression is mission/event-aware: a decision is
        only spoken when its signature (step_id, status,
        deviation_type, guidance) differs from the last spoken
        decision, or when ``force`` is explicitly requested. This
        applies uniformly to every status — DEVIATION and UNCERTAIN
        are not exempt — so five identical repeated-frame deviations
        are spoken once, while a genuinely new transition (e.g.
        DEVIATION -> UNCERTAIN -> RECOVERY) is always spoken.
        """

        if not guidance:
            return False

        status = str(status or "").upper().strip()

        with self._state_lock:
            enabled = self.enabled
            active_language = self.language

        if not enabled:
            return False

        signature: Signature = (
            str(step_id) if step_id is not None else None,
            status or None,
            str(deviation_type) if deviation_type is not None else None,
            str(guidance).strip() or None,
        )

        with self._state_lock:
            is_duplicate = (not force) and (signature == self._last_signature)

            if is_duplicate:
                return False

            self._last_signature = signature

        localized = translate_guidance(
            guidance,
            language=active_language,
            status=status,
            deviation_type=deviation_type,
            detected_object=detected_object,
            expected_object=expected_object,
            step_id=step_id,
            next_step_id=next_step_id,
        )

        if not localized:
            return False

        with self._state_lock:
            self._last_guidance = localized
            self._last_guidance_en = clean_for_speech(guidance, language=ENGLISH)

        self._enqueue(localized, active_language)

        return True

    def _enqueue(self, speech_text: str, language: str) -> None:
        """Queue text for the background speech worker."""

        if self._engine is None:
            # No TTS engine available on this host. The mission still
            # continues; guidance remains visible on the dashboard.
            return

        self._queue.put((speech_text, language))

    def _run_worker(self) -> None:
        """Background worker: speaks queued text one at a time."""

        while True:
            item = self._queue.get()

            if item is _SENTINEL:
                self._queue.task_done()
                return

            speech_text, language = item

            try:
                with self._engine_lock:
                    if self._engine is None:
                        continue

                    self._apply_voice_for_language(language)
                    self._engine.say(speech_text)
                    self._engine.runAndWait()
            except Exception as exc:
                # TTS must never crash perception, the protocol engine,
                # FastAPI, or the dashboard.
                print(f"[VOICE] Speech error: {exc}")
            finally:
                self._queue.task_done()

    # ------------------------------------------------------------
    # Control
    # ------------------------------------------------------------

    def stop(self) -> None:
        """Stop any speech currently playing and clear the queue."""

        # Drop anything still waiting to be spoken.
        try:
            while True:
                self._queue.get_nowait()
                self._queue.task_done()
        except queue.Empty:
            pass

        if self._engine is None:
            return

        if not self._engine_lock.acquire(timeout=0.1):
            return
        try:
            self._engine.stop()
        except Exception as exc:  # pragma: no cover - platform dependent
            print(f"[VOICE] Failed to stop speech: {exc}")
        finally:
            self._engine_lock.release()

    def reset(self) -> None:
        """
        Reset per-mission voice state.

        Called on ``POST /api/mission/reset`` so the same guidance can
        be spoken again in a new mission instead of staying suppressed
        by stale deduplication state from the previous mission.
        """

        self.stop()

        with self._state_lock:
            self._last_signature = None
            self._last_guidance = None
            self._last_guidance_en = None


_voice_guidance: Optional[VoiceGuidance] = None
_voice_guidance_lock = threading.Lock()


def get_voice_guidance() -> VoiceGuidance:
    """Return the shared, process-wide voice guidance instance."""

    global _voice_guidance

    if _voice_guidance is None:
        with _voice_guidance_lock:
            if _voice_guidance is None:
                _voice_guidance = VoiceGuidance()

    return _voice_guidance


def reset_voice_guidance() -> VoiceGuidance:
    """Rebuild the singleton (mainly useful for tests)."""

    global _voice_guidance

    with _voice_guidance_lock:
        _voice_guidance = VoiceGuidance()

    return _voice_guidance
