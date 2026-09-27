"""
ASTRA-GUARD Mission Voice Assistant — language configuration.

Centralizes the set of supported voice languages so no other module
needs to hardcode language codes or validate them independently.

Supported languages:
    en  -> English
    hi  -> Hindi
"""

from __future__ import annotations

from typing import Dict

ENGLISH = "en"
HINDI = "hi"

DEFAULT_LANGUAGE = ENGLISH

SUPPORTED_LANGUAGES = (ENGLISH, HINDI)

# Human-readable display names, used by the dashboard/API.
LANGUAGE_LABELS: Dict[str, str] = {
    ENGLISH: "English",
    HINDI: "हिंदी",
}


def normalize_language(language: str | None) -> str:
    """
    Validate and normalize a language code.

    Falls back to ``DEFAULT_LANGUAGE`` for empty input and raises
    ``ValueError`` for anything that is not a supported language, so
    callers (API routes, voice service) can surface a clear error
    instead of silently mis-selecting a voice.
    """

    if not language:
        return DEFAULT_LANGUAGE

    code = str(language).strip().lower()

    if code not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported voice language: {language!r}. "
            f"Supported languages: {', '.join(SUPPORTED_LANGUAGES)}"
        )

    return code


def language_label(language: str) -> str:
    """Return the human-readable label for a language code."""

    return LANGUAGE_LABELS.get(language, language)
