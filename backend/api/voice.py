"""Voice assistant endpoints — thin layer over the shared VoiceGuidance.

The dashboard uses these routes as the source of truth for the
mission voice language and on/off state; the frontend does not
duplicate this state locally.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agent.voice.voice_service import get_voice_guidance
from backend.schemas.voice import (
    VoiceEnabledRequest,
    VoiceLanguageRequest,
    VoiceLanguageResponse,
    VoiceStatusResponse,
)

router = APIRouter()


@router.get("/voice/status", response_model=VoiceStatusResponse)
def get_voice_status() -> dict:
    return get_voice_guidance().get_status()


@router.get("/voice/language", response_model=VoiceLanguageResponse)
def get_voice_language() -> dict:
    return {"language": get_voice_guidance().language}


@router.post("/voice/language", response_model=VoiceLanguageResponse)
def set_voice_language(payload: VoiceLanguageRequest) -> dict:
    try:
        language = get_voice_guidance().set_language(payload.language)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"language": language}


@router.post("/voice/enabled")
def set_voice_enabled(payload: VoiceEnabledRequest) -> dict:
    voice = get_voice_guidance()
    voice.set_enabled(payload.enabled)
    return {"enabled": voice.enabled}
