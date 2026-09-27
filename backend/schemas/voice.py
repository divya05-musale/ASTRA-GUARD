"""Voice assistant schemas (minimal)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class VoiceLanguageRequest(BaseModel):
    """Request body for POST /api/voice/language."""

    language: str


class VoiceLanguageResponse(BaseModel):
    language: str


class VoiceEnabledRequest(BaseModel):
    """Request body for POST /api/voice/enabled."""

    enabled: bool


class VoiceStatusResponse(BaseModel):
    online: bool = False
    engine_ready: bool = False
    language: str = "en"
    enabled: bool = True
    hindi_voice_available: bool = False
    last_guidance: Optional[str] = None
    last_guidance_en: Optional[str] = None
