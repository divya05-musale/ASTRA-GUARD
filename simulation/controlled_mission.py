
"""
ASTRA-GUARD Controlled Mission Demonstration.

Uses the real ASTRA-GUARD perception-to-decision pipeline
with controlled perception events.

Demonstrates:
- CORRECT
- DEVIATION
- UNCERTAIN
- Recovery
- Complete protocol progression

Modes:
- LOCAL (default): events go through the local LivePerceptionSession.
- BACKEND: the same events are POSTed to FastAPI /api/mission/event,
  which is authoritative when the dashboard backend is running.
  Select with --mode, or $ASTRA_GUARD_MODE.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from agent.mission.protocol_loader import ProtocolLoader
from agent.mission.decision_engine import DecisionEngine
from agent.mission.deviation_detector import DeviationDetector
from agent.mission.live_perception_session import LivePerceptionSession
from agent.mission.perception_bridge import PerceptionProtocolBridge
from agent.mission.perception_decision import PerceptionDecisionAdapter
from agent.mission.sequence_validator import SequenceValidator
from agent.mission.state_machine import ProtocolStateMachine
from agent.mission.step_manager import StepManager
from agent.perception.backend_client import (
    DEFAULT_BASE_URL,
    MissionBackendClient,
)
from agent.perception.perception_event import PerceptionEvent



PROTOCOL_PATH = "experiments/EXP001_TARDIGRADE"

DEMO_MODE_LOCAL = "local"
DEMO_MODE_BACKEND = "backend"

# Controlled demo event sequence:
# (label, object_name, confidence, hand_interaction).
DEMO_STEPS: list[tuple[str, str, float, bool]] = [
    ("[1] CORRECT — Equipment Check", "experiment_container", 0.98, True),
    ("[2] CORRECT — Retrieve Sample", "biological_sample", 0.98, True),
    ("[3] DEVIATION — Wrong Object", "experiment_controller", 0.98, True),
    ("[4] UNCERTAIN — Low Confidence", "sample_chamber", 0.45, False),
    ("[5] CORRECT — Recovery", "sample_chamber", 0.98, True),
    ("[6] CORRECT — Transfer Sample", "sample_chamber", 0.98, True),
    ("[7] CORRECT — Start Experiment", "experiment_controller", 0.98, True),
    ("[8] CORRECT — Record Result", "observation_interface", 0.98, True),
    ("[9] CORRECT — Secure Sample", "sample_chamber", 0.98, True),
    (
        "[10] COMPLETED — Complete Experiment",
        "experiment_controller",
        0.98,
        True,
    ),
]


def get_demo_mode(explicit: Optional[str] = None) -> str:
    """Resolve the controlled-demo mode (local or backend)."""

    if explicit is not None:
        mode = str(explicit).strip().lower()

        if mode not in (DEMO_MODE_LOCAL, DEMO_MODE_BACKEND):
            raise ValueError(f"Unknown demo mode: {explicit!r}")

        return mode

    mode = os.environ.get(
        "ASTRA_GUARD_MODE",
        DEMO_MODE_LOCAL,
    ).strip().lower()

    if mode in (DEMO_MODE_BACKEND, "remote", "api"):
        return DEMO_MODE_BACKEND

    return DEMO_MODE_LOCAL


def get_backend_base_url(explicit: Optional[str] = None) -> str:
    """Resolve the FastAPI base URL used in backend mode."""

    if explicit:
        return str(explicit)

    return os.environ.get(
        "ASTRA_GUARD_BACKEND_URL",
        DEFAULT_BASE_URL,
    )


def build_backend_client(
    base_url: Optional[str] = None,
) -> MissionBackendClient:
    """Build the HTTP bridge to FastAPI /api/mission/event."""

    return MissionBackendClient(
        base_url=get_backend_base_url(base_url)
    )


def process_demo_event(
    session: LivePerceptionSession,
    event: PerceptionEvent,
    backend_client: Optional[MissionBackendClient] = None,
) -> Dict[str, Any]:
    """Process one controlled event locally or via the backend."""

    if backend_client is not None:
        return backend_client.post_event(event)

    return session.process_event(event)


def reset_backend_mission(
    backend_client: MissionBackendClient,
) -> Dict[str, Any]:
    """Reset the backend mission so a demo starts from a fresh state."""

    return backend_client.reset_mission()


def build_session() -> LivePerceptionSession:
    """Build the real ASTRA-GUARD mission stack."""

    protocol = ProtocolLoader(PROTOCOL_PATH).load()

    steps = protocol.get_steps()
    activities = protocol.get_activities()
    objects = protocol.get_objects()
    rules = protocol.get_rules()

    state_machine = ProtocolStateMachine(steps)

    step_manager = StepManager(
        steps,
        state_machine,
        rules,
    )

    validator = SequenceValidator(
        steps,
        activities,
    )

    deviation_detector = DeviationDetector(
        steps,
        activities,
    )

    decision_engine = DecisionEngine(
        state_machine,
        step_manager,
        validator,
        deviation_detector,
        rules=rules,
    )

    bridge = PerceptionProtocolBridge(
        protocol_objects=objects
    )

    adapter = PerceptionDecisionAdapter(
        decision_engine,
        bridge=bridge,
        protocol_aware=True,
    )

    return LivePerceptionSession(adapter)


def create_event(
    object_name: str,
    confidence: float = 0.95,
    hand_interaction: bool = True,
) -> PerceptionEvent:
    """Create a controlled perception event."""

    objects = [
        {
            "class_name": object_name,
            "confidence": confidence,
            "bbox": [300, 200, 500, 400],
        }
    ]

    hands = []

    if hand_interaction:
        hands = [
            {
                "confidence": 0.98,
                "center": [400, 300],
            }
        ]

    return PerceptionEvent(
        timestamp="controlled-demo",
        source="camera",
        objects=objects,
        hands=hands,
    )


def fetch_backend_json(
    base_url: str,
    path: str,
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """GET one JSON object from the FastAPI backend."""

    url = base_url.rstrip("/") + path

    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(
            f"Cannot read {url}: {exc}. "
            "Is FastAPI running (uvicorn backend.main:app)?"
        ) from exc


def print_backend_summary(
    backend_client: MissionBackendClient,
) -> None:
    """Print the summary from the authoritative backend mission state."""

    base_url = backend_client.base_url
    timeout = backend_client.timeout

    summary = fetch_backend_json(base_url, "/api/mission/summary", timeout)
    progress = fetch_backend_json(base_url, "/api/mission/progress", timeout)
    status = fetch_backend_json(base_url, "/api/mission/status", timeout)

    print()
    print()
    print("=" * 70)
    print("                   MISSION SUMMARY (BACKEND)")
    print("=" * 70)
    print()

    print(f"Total Events:       {summary.get('total_events')}")
    print(f"Correct:            {summary.get('correct')}")
    print(f"Deviations:         {summary.get('deviations')}")
    print(f"Uncertain:          {summary.get('uncertain')}")
    print(f"Completed Events:   {summary.get('completed')}")

    print()

    if progress.get("completed"):
        print("Mission Status:     COMPLETED")
        print(
            "Protocol Progress:  "
            f"{progress.get('completed_steps')}/"
            f"{progress.get('total_steps')} steps"
        )
    else:
        print("Mission Status:     INCOMPLETE")
        print(f"Backend Status:     {status.get('status')}")


def _parse_args(argv=None):
    """Parse CLI flags for the controlled demo."""

    parser = argparse.ArgumentParser(
        description="ASTRA-GUARD controlled mission demo.",
    )
    parser.add_argument(
        "--mode",
        choices=[DEMO_MODE_LOCAL, DEMO_MODE_BACKEND],
        default=None,
    )
    parser.add_argument("--backend-url", default=None)
    parser.add_argument(
        "--pace-sec",
        type=float,
        default=0.0,
        help=(
            "Seconds to wait between backend events so the React "
            "dashboard (750ms poll) can visibly step through "
            "S001→S008. Use e.g. --pace-sec 1.5 for live demos."
        ),
    )
    return parser.parse_args(argv)


def print_local_summary(session: LivePerceptionSession) -> None:
    """Print the mission summary from the local session."""

    events = session.get_event_history()

    correct = sum(
        event.status == "CORRECT"
        for event in events
    )

    deviations = sum(
        event.status == "DEVIATION"
        for event in events
    )

    uncertain = sum(
        event.status == "UNCERTAIN"
        for event in events
    )

    completed = sum(
        event.status == "COMPLETED"
        for event in events
    )

    mission_completed = (
        session.adapter.engine.sm.is_complete()
    )

    print()
    print()
    print("=" * 70)
    print("                    MISSION SUMMARY (LOCAL)")
    print("=" * 70)
    print()

    print(f"Total Events:       {len(events)}")
    print(f"Correct:            {correct}")
    print(f"Deviations:         {deviations}")
    print(f"Uncertain:          {uncertain}")
    print(f"Completed Events:   {completed}")

    print()

    if mission_completed:
        print("Mission Status:     COMPLETED")
        print("Protocol Progress:  8/8 steps")
    else:
        print("Mission Status:     INCOMPLETE")


def print_result(
    label: str,
    result: dict,
) -> None:
    """Print one controlled mission decision."""

    print()
    print("-" * 70)
    print(label)
    print("-" * 70)

    print(f"Step:              {result.get('step_id')}")
    print(f"Expected Activity: {result.get('expected_activity')}")
    print(f"Detected Activity: {result.get('detected_activity')}")
    print(f"Expected Object:   {result.get('expected_object')}")
    print(f"Detected Object:   {result.get('detected_object')}")

    perception = result.get("perception") or {}

    print(
        f"Confidence:        "
        f"{perception.get('confidence', 0.0):.2f}"
    )

    print(f"Status:             {result.get('status')}")
    print(
        f"Deviation:          "
        f"{result.get('deviation_type')}"
    )
    print(
        f"Guidance:           "
        f"{result.get('guidance')}"
    )


def run_demo(
    mode: Optional[str] = None,
    backend_url: Optional[str] = None,
    pace_sec: float = 0.0,
) -> None:
    """Run the complete controlled mission.

    MODE A (local, default): events go through the local
    LivePerceptionSession (onboard/offline operation).
    MODE B (backend): the same PerceptionEvents are POSTed to the
    FastAPI backend (/api/mission/event), which is authoritative
    when the dashboard backend is running.
    """

    resolved_mode = get_demo_mode(mode)
    resolved_backend_url = get_backend_base_url(backend_url)

    print()
    print("=" * 70)
    print("                    ASTRA-GUARD")
    print("               CONTROLLED MISSION DEMO")
    print("=" * 70)

    session = build_session()

    backend_client: Optional[MissionBackendClient] = None

    if resolved_mode == DEMO_MODE_BACKEND:
        backend_client = build_backend_client(
            resolved_backend_url
        )

        # Start each backend demo from a fresh protocol state so events
        # never accumulate on top of a previous COMPLETED mission.
        reset_backend_mission(backend_client)

    print()
    print("Protocol: EXP001 - Tardigrade Sample Observation")
    print("Environment: Microgravity")
    print("Protocol Type: Synthetic")

    if backend_client is not None:
        print(
            "Mode: Controlled Demonstration "
            f"(BACKEND → {backend_client.event_url})"
        )
    else:
        print("Mode: Controlled Demonstration (LOCAL)")

    print()

    for label, object_name, confidence, hand_interaction in DEMO_STEPS:
        event = create_event(
            object_name,
            confidence=confidence,
            hand_interaction=hand_interaction,
        )

        result = process_demo_event(
            session,
            event,
            backend_client=backend_client,
        )

        print_result(
            label,
            result,
        )

        # Paced backend demos let the dashboard (750ms poll) visibly
        # walk S001→S008 instead of flashing only the final COMPLETED.
        if pace_sec and pace_sec > 0:
            import time as _time

            _time.sleep(float(pace_sec))

    # =========================================================
    # SUMMARY
    # =========================================================

    if backend_client is not None:
        print_backend_summary(backend_client)
    else:
        print_local_summary(session)

    print()
    print("=" * 70)
    print("              ASTRA-GUARD DEMO FINISHED")
    print("=" * 70)


if __name__ == "__main__":
    _args = _parse_args()
    run_demo(
        mode=_args.mode,
        backend_url=_args.backend_url,
        pace_sec=getattr(_args, "pace_sec", 0.0) or 0.0,
    )

