"""
ASTRA-GUARD Mission Voice Assistant — centralized bilingual messages.

This module is the single place where mission guidance is turned into
natural, spoken English or Hindi. It does not make mission decisions —
the protocol/decision engine remains the source of truth. It only
translates the guidance text that engine already produced.

Two translation layers are used, in order:

1. ``STEP_GUIDANCE_HI`` — exact Hindi translations for the guidance
   sentences already authored in the current protocol's rules
   (``experiments/EXP001_TARDIGRADE/rules.yaml`` and the equivalent
   fallback sentences produced by ``DecisionEngine``). These are
   natural, human-reviewed translations, not machine transliteration.

2. ``MESSAGES`` — generic per-status/deviation-type templates, used as
   a safe fallback for guidance text that does not exactly match a
   known sentence (e.g. a different protocol, or a dynamically built
   sentence). This keeps the system usable without ever inventing new
   mission states.

Technical identifiers (``sample_chamber``, ``experiment_controller``,
...) are converted into natural spoken phrases via ``TERM_PHRASES``
and ``clean_for_speech`` so the voice never reads an underscore aloud.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

from agent.voice.voice_language import ENGLISH, HINDI

# ---------------------------------------------------------------------
# 1. Technical identifiers -> natural spoken phrases.
#
# These are the object/activity identifiers that appear in the current
# ASTRA-GUARD protocol (EXP001_TARDIGRADE). Keys are lowercase with
# underscores, matching the identifiers used by the protocol engine.
# ---------------------------------------------------------------------

TERM_PHRASES: Dict[str, Dict[str, str]] = {
    "experiment_container": {"en": "experiment container", "hi": "एक्सपेरिमेंट कंटेनर"},
    "biological_sample": {"en": "biological sample", "hi": "सैंपल"},
    "sample_chamber": {"en": "sample chamber", "hi": "सैंपल चैंबर"},
    "experiment_controller": {"en": "experiment controller", "hi": "एक्सपेरिमेंट कंट्रोलर"},
    "observation_interface": {"en": "observation interface", "hi": "ऑब्ज़र्वेशन इंटरफ़ेस"},
    "check_equipment": {"en": "check equipment", "hi": "उपकरण की जाँच करें"},
    "retrieve_sample": {"en": "retrieve the sample", "hi": "सैंपल लें"},
    "open_container": {"en": "open the container", "hi": "कंटेनर खोलें"},
    "transfer_sample": {"en": "transfer the sample", "hi": "सैंपल ट्रांसफर करें"},
    "start_experiment": {"en": "start the experiment", "hi": "एक्सपेरिमेंट शुरू करें"},
    "record_result": {"en": "record the result", "hi": "परिणाम रिकॉर्ड करें"},
    "secure_sample": {"en": "secure the sample", "hi": "सैंपल सुरक्षित करें"},
    "complete_experiment": {"en": "complete the experiment", "hi": "एक्सपेरिमेंट पूरा करें"},
}

# Sorted longest-first so multi-word identifiers are matched before any
# shorter identifier that happens to be a substring of them.
_IDENTIFIER_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(TERM_PHRASES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def clean_for_speech(message: str, language: str = ENGLISH) -> str:
    """
    Convert technical identifiers into natural spoken language.

    Example:
        check_equipment      -> "check equipment"
        sample_chamber       -> "sample chamber" / "सैंपल चैंबर"

    Any identifier not found in ``TERM_PHRASES`` simply has its
    underscores replaced with spaces, so the voice never reads
    "underscore" aloud even for protocols this module does not know
    about in advance.
    """

    if not message:
        return ""

    def _replace(match: "re.Match[str]") -> str:
        key = match.group(1).lower()
        phrase = TERM_PHRASES.get(key)

        if phrase is None:
            return match.group(1).replace("_", " ")

        return phrase.get(language, phrase[ENGLISH])

    message = _IDENTIFIER_PATTERN.sub(_replace, message)

    # Any remaining identifier-like tokens (unknown to TERM_PHRASES)
    # still lose their underscores instead of being spoken literally.
    message = message.replace("_", " ")

    return " ".join(message.split()).strip()


# ---------------------------------------------------------------------
# 2. Exact guidance translations.
#
# These are the literal English guidance sentences already produced by
# the protocol engine for EXP001_TARDIGRADE (see rules.yaml and
# DecisionEngine fallbacks), paired with natural, reviewed Hindi.
# Astronaut-relevant terminology (sample, chamber, controller) stays
# transliterated rather than being forced into an unnatural Hindi word.
# ---------------------------------------------------------------------

STEP_GUIDANCE_HI: Dict[str, str] = {
    # ADVANCE guidance (rules.yaml)
    "Equipment check completed. Proceed to retrieve the sample.":
        "उपकरण जाँच पूरी हुई। कृपया सैंपल लें।",
    "Sample retrieved. Proceed to open the sample chamber.":
        "सैंपल प्राप्त हुआ। कृपया सैंपल चैंबर खोलें।",
    "Sample chamber opened. Proceed to transfer the sample.":
        "सैंपल चैंबर खोला गया। कृपया सैंपल ट्रांसफर करें।",
    "Sample transferred. Proceed to start the experiment.":
        "सैंपल ट्रांसफर हो गया। कृपया एक्सपेरिमेंट शुरू करें।",
    "Experiment started. Proceed to record the result.":
        "एक्सपेरिमेंट शुरू हो गया। कृपया परिणाम रिकॉर्ड करें।",
    "Result recorded. Proceed to secure the sample.":
        "परिणाम रिकॉर्ड हो गया। कृपया सैंपल सुरक्षित करें।",
    "Sample secured. Proceed to complete the experiment.":
        "सैंपल सुरक्षित कर दिया गया। कृपया एक्सपेरिमेंट पूरा करें।",
    "Experiment completed successfully.":
        "प्रयोग सफलतापूर्वक पूरा हुआ।",
    # DEVIATION guidance (rules.yaml)
    "Wrong object detected. Please select the biological sample.":
        "गलत वस्तु पहचानी गई। कृपया सैंपल चुनें।",
    "Wrong sequence. Open the sample chamber before starting the experiment.":
        "गलत क्रम। एक्सपेरिमेंट शुरू करने से पहले सैंपल चैंबर खोलें।",
    "A required step was skipped. Complete the current step first.":
        "एक आवश्यक चरण छूट गया। कृपया पहले मौजूदा चरण पूरा करें।",
    "This action is premature. Complete the required previous steps first.":
        "यह क्रिया समय से पहले है। कृपया पहले आवश्यक पिछले चरण पूरे करें।",
    # UNCERTAIN guidance (rules.yaml)
    "Detection confidence is low. Please repeat or hold the action for verification.":
        "पहचान का विश्वास स्तर कम है। कृपया क्रिया को दोहराएँ या स्थिर रखें।",
    # RECOVERY guidance (rules.yaml)
    "Correct sample detected. Deviation recovered. Continue the protocol.":
        "सही सैंपल पहचाना गया। विचलन ठीक हो गया। प्रोटोकॉल जारी रखें।",
}


# ---------------------------------------------------------------------
# 3. Generic per-status / per-deviation-type fallback templates.
#
# Used only when a guidance sentence does not exactly match
# ``STEP_GUIDANCE_HI`` above (e.g. a different protocol, or a
# dynamically generated sentence with values this module has not
# seen before). These never invent a mission state: they only give
# a natural-sounding Hindi rendering of the status the decision
# engine already reported.
# ---------------------------------------------------------------------

MESSAGES: Dict[str, Dict[str, str]] = {
    "WRONG_OBJECT": {
        "en": "Wrong action detected. {detected} is not expected. Please use {expected}.",
        "hi": "गलत क्रिया का पता चला। {detected} अपेक्षित नहीं है। कृपया {expected} का उपयोग करें।",
    },
    "WRONG_SEQUENCE": {
        "en": "Wrong sequence detected. Please complete {expected_step} before continuing.",
        "hi": "गलत क्रम का पता चला। कृपया आगे बढ़ने से पहले {expected_step} पूरा करें।",
    },
    "SKIPPED_STEP": {
        "en": "Required step skipped. Please complete {expected_step} before continuing.",
        "hi": "आवश्यक चरण छूट गया। कृपया आगे बढ़ने से पहले {expected_step} पूरा करें।",
    },
    "REPEATED_STEP": {
        "en": "This step has already been completed. Please continue with {next_step}.",
        "hi": "यह चरण पहले ही पूरा हो चुका है। कृपया {next_step} के साथ आगे बढ़ें।",
    },
    "PREMATURE_ACTION": {
        "en": "Action performed too early. Please complete {required_step} first.",
        "hi": "क्रिया समय से पहले की गई। कृपया पहले {required_step} पूरा करें।",
    },
    "LOW_CONFIDENCE": {
        "en": "Action uncertain. Please hold the object steady and try again.",
        "hi": "क्रिया अनिश्चित है। कृपया वस्तु को स्थिर रखें और पुनः प्रयास करें।",
    },
    "UNKNOWN_OBJECT": {
        "en": "Unknown object detected. Please use {expected}.",
        "hi": "अज्ञात वस्तु का पता चला। कृपया {expected} का उपयोग करें।",
    },
    "UNKNOWN_ACTION": {
        "en": "Unknown object detected. Please use {expected}.",
        "hi": "अज्ञात वस्तु का पता चला। कृपया {expected} का उपयोग करें।",
    },
    "RECOVERED": {
        "en": "Correct action detected. You may continue.",
        "hi": "सही क्रिया पहचानी गई। आप आगे बढ़ सकते हैं।",
    },
    "COMPLETED": {
        "en": "Experiment completed successfully.",
        "hi": "प्रयोग सफलतापूर्वक पूरा हुआ।",
    },
    "CORRECT": {
        "en": "Step completed. Proceed.",
        "hi": "चरण पूरा हुआ। आगे बढ़ें।",
    },
}


def _has_placeholders(template: str) -> bool:
    return isinstance(template, str) and ("{" in template) and ("}" in template)


def format_mission_guidance(
    status: Optional[str] = None,
    deviation_type: Optional[str] = None,
    detected_object: Optional[str] = None,
    expected_object: Optional[str] = None,
    step_id: Optional[str] = None,
    next_step_id: Optional[str] = None,
    language: str = ENGLISH,
) -> str:
    """Build mission-aware guidance with real runtime values (offline).

    Uses actual detected/expected objects and step ids; never invents
    values. Falls back to naturalized plain text when values are missing.
    """
    key = str(deviation_type or status or "").upper()
    template = MESSAGES.get(key, {}).get(language, "")
    if not template:
        template = MESSAGES.get(key, {}).get(ENGLISH, "")
    detected_en = clean_for_speech(str(detected_object or "unknown item"), language=ENGLISH)
    expected_en = clean_for_speech(str(expected_object or "expected item"), language=ENGLISH)
    detected_hi = clean_for_speech(str(detected_object or "unknown item"), language=HINDI)
    expected_hi = clean_for_speech(str(expected_object or "expected item"), language=HINDI)
    mapping = {
        "detected": detected_hi if language == HINDI else detected_en,
        "expected": expected_hi if language == HINDI else expected_en,
        "expected_step": str(step_id or "current step"),
        "next_step": str(next_step_id or step_id or "next step"),
        "required_step": str(step_id or "required step"),
    }
    if _has_placeholders(template):
        try:
            return template.format(**mapping)
        except Exception:
            pass
    # Fallback without placeholders: append real values when available.
    base = clean_for_speech(template or "Please continue.", language=language)
    return base


def translate_guidance(
    guidance: Optional[str],
    language: str,
    status: Optional[str] = None,
    deviation_type: Optional[str] = None,
    detected_object: Optional[str] = None,
    expected_object: Optional[str] = None,
    step_id: Optional[str] = None,
    next_step_id: Optional[str] = None,
) -> str:
    """
    Return the natural spoken guidance for the requested language.

    Resolution order:
        1. Exact sentence match in ``STEP_GUIDANCE_HI`` (Hindi only).
        2. Generic template keyed by ``deviation_type`` or ``status``.
        3. The original guidance text, with identifiers naturalized.

    English always falls through to (3) with identifiers naturalized,
    since the protocol engine already writes natural English
    sentences — this module only needs to strip technical identifiers
    for speech.
    """

    guidance = (guidance or "").strip()

    if language == HINDI:
        exact = STEP_GUIDANCE_HI.get(guidance)

        if exact:
            return clean_for_speech(exact, language=HINDI)

        # Mission-aware dynamic Hindi: fill real detected/expected objects
        # and step ids into the reviewed template (offline, no APIs).
        key = str(deviation_type or status or "").upper()
        if key in MESSAGES and _has_placeholders(MESSAGES[key].get("hi", "")):
            return format_mission_guidance(
                status=status, deviation_type=deviation_type,
                detected_object=detected_object, expected_object=expected_object,
                step_id=step_id, next_step_id=next_step_id, language=HINDI,
            )

        template = MESSAGES.get(key)

        if template and "hi" in template and not _has_placeholders(template["hi"]):
            return clean_for_speech(template["hi"], language=HINDI)

        # Last resort: never invent Hindi text for an unknown
        # sentence. Fall back to the cleaned English guidance so the
        # mission is still communicated rather than staying silent.
        return clean_for_speech(guidance, language=ENGLISH)

    return clean_for_speech(guidance, language=ENGLISH)
