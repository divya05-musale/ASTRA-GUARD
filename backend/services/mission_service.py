"""ASTRA-GUARD mission service.

Thin integration layer over the existing mission stack.
Reuses ProtocolLoader + DecisionEngine + LivePerceptionSession
+ MissionStatus. Does NOT duplicate decision logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.mission.decision_engine import DecisionEngine
from agent.mission.activity_interpreter import ActivityInterpreter
from agent.mission.deviation_detector import DeviationDetector
from agent.mission.live_perception_session import LivePerceptionSession
from agent.mission.mission_status import MissionStatus
from agent.mission.perception_bridge import PerceptionProtocolBridge
from agent.mission.perception_decision import PerceptionDecisionAdapter
from agent.mission.protocol_loader import ProtocolLoader
from agent.mission.sequence_validator import SequenceValidator
from agent.mission.state_machine import ProtocolStateMachine
from agent.mission.step_manager import StepManager
from backend.services.session_store import SessionStore, utc_timestamp


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL_PATH = PROJECT_ROOT / "experiments" / "EXP001_TARDIGRADE"


def build_session(
    protocol_path: str | Path = DEFAULT_PROTOCOL_PATH,
) -> tuple[LivePerceptionSession, Dict[str, Any]]:
    """Build the real mission stack for the given protocol path."""
    protocol = ProtocolLoader(str(protocol_path)).load()

    steps = protocol.get_steps()
    activities = protocol.get_activities()
    objects = protocol.get_objects()
    rules = protocol.get_rules()
    experiment = protocol.get_experiment()

    state_machine = ProtocolStateMachine(steps)
    step_manager = StepManager(steps, state_machine, rules)
    validator = SequenceValidator(steps, activities)
    deviation_detector = DeviationDetector(steps, activities)
    decision_engine = DecisionEngine(
        state_machine,
        step_manager,
        validator,
        deviation_detector,
        rules=rules,
    )
    bridge = PerceptionProtocolBridge(
        protocol_objects=objects,
        activity_interpreter=ActivityInterpreter({
            str(step["step_id"]): str(step["activity"])
            for step in steps
        }),
        expected_object_by_step={
            str(step["step_id"]): str(step["expected_object"])
            for step in steps
        },
    )
    adapter = PerceptionDecisionAdapter(
        decision_engine,
        bridge=bridge,
        protocol_aware=True,
    )
    session = LivePerceptionSession(adapter)
    return session, experiment


class MissionService:
    """Expose the existing MissionStatus API to HTTP routers."""

    def __init__(
        self,
        protocol_path: str | Path = DEFAULT_PROTOCOL_PATH,
    ) -> None:
        self._protocol_path = Path(protocol_path)
        session, experiment = build_session(protocol_path)
        self._session = session
        self._experiment = experiment
        self._status = MissionStatus(session)
        self._session_store = SessionStore()
        self._session_store.interrupt_in_progress()
        self._active_session_id: Optional[str] = None
        self._last_persisted_signature: Optional[tuple] = None
        self._last_persisted_timestamp: Optional[str] = None
        self._repeat_count = 0
        self._saved_repeat_count = 0

    @property
    def session(self) -> LivePerceptionSession:
        return self._session

    @property
    def status_api(self) -> MissionStatus:
        return self._status

    @property
    def experiment(self) -> Dict[str, Any]:
        return dict(self._experiment)

    def get_status(self) -> Dict[str, Any]:
        status = self._status.get_current_status()
        status["session_id"] = self._active_session_id
        current_step_id = self.get_progress().get("current_step")
        status["manual_confirmation_allowed"] = self._manual_confirmation_allowed(current_step_id)
        return status

    def _manual_confirmation_allowed(self, step_id: Optional[str]) -> bool:
        if self._experiment.get("manual_confirmation_allowed"):
            return True
        if step_id and step_id in set(self._experiment.get("manual_confirmation_steps", [])):
            return True
        step = self._session.adapter.engine.sm.current_step()
        return bool(step and step.get("step_id") == step_id and step.get("manual_confirmation_allowed"))

    def get_progress(self) -> Dict[str, Any]:
        return self._status.get_progress()

    def get_summary(self) -> Dict[str, Any]:
        return self._status.get_summary()

    def get_recent_events(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        events = self._status.get_recent_events()
        collapsed: List[Dict[str, Any]] = []
        last_signature = None
        for event in events:
            signature = (
                event.get("status"),
                event.get("step_id"),
                event.get("deviation"),
                event.get("activity"),
                event.get("detected_object"),
                event.get("guidance"),
            )
            if event.get("status") in {"DEVIATION", "UNCERTAIN"} and signature == last_signature:
                collapsed[-1]["repeat_count"] += 1
                collapsed[-1]["last_seen"] = event.get("timestamp")
                continue
            item = dict(event)
            item["repeat_count"] = 1
            collapsed.append(item)
            last_signature = signature if event.get("status") in {"DEVIATION", "UNCERTAIN"} else None
        if limit is None:
            return collapsed
        if limit == 0:
            return []
        return collapsed[-limit:]

    def get_overview(self) -> Dict[str, Any]:
        current = self.get_status()
        progress = self.get_progress()
        return {
            "protocol_id": self._experiment.get("experiment_id"),
            "protocol_name": self._experiment.get("experiment_name"),
            "environment": self._experiment.get("environment"),
            "protocol_type": self._experiment.get("protocol_type"),
            "current_step": progress.get("current_step"),
            "progress": progress,
            "status": current.get("status"),
        }

    def get_protocol(self) -> Dict[str, Any]:
        """Return read-only protocol definition for the dashboard timeline.

        Exposes experiment metadata + ordered steps/activities. No decision
        logic; purely descriptive data already loaded in memory.
        """
        sm = self._status._get_state_machine()
        steps = [dict(s) for s in getattr(sm, "_steps", [])]
        return {
            "experiment": dict(self._experiment),
            "steps": steps,
        }

    @property
    def active_session_id(self) -> Optional[str]:
        return self._active_session_id

    def start_session(
        self,
        input_source: str = "webcam",
        evidence_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start a persistent session for the currently loaded protocol."""
        active = self._session_store.get_metadata(self._active_session_id) if self._active_session_id else None
        if active and active.get("status") == "IN_PROGRESS":
            raise ValueError("An experiment session is already in progress")

        protocol = self.get_protocol()
        record = self._session_store.create({
            "experiment_id": self._experiment.get("experiment_id"),
            "experiment_name": self._experiment.get("experiment_name"),
            "input_source": input_source,
            "protocol": protocol,
            "evidence": ([{"path": evidence_path, "kind": "video"}]
                         if evidence_path else []),
        })
        self._active_session_id = str(record["session_id"])
        self._last_persisted_signature = None
        self._last_persisted_timestamp = None
        self._repeat_count = 0
        self._saved_repeat_count = 0
        if self._experiment.get("start_action_completes_first_step"):
            self._record_protocol_action(
                source="session_start",
                operator="not_provided",
            )
        return record

    def process_event(self, event: Any) -> Dict[str, Any]:
        """Run the existing decision engine and persist its result."""
        if self._active_session_id is None:
            source = "webcam" if getattr(event, "source", "camera") == "camera" else str(event.source)
            self.start_session(input_source=source)
        else:
            active = self._session_store.get_metadata(self._active_session_id)
            if not active or active.get("status") != "IN_PROGRESS":
                terminal_status = (active or {}).get("status")
                return {
                    "status": "COMPLETED" if terminal_status == "COMPLETED" else "SESSION_CLOSED",
                    "step_id": self.get_progress().get("current_step"),
                    "next_step_id": None,
                    "guidance": "Start a new experiment session to continue.",
                }
            expected_source = str(active.get("input_source", "webcam"))
            detected_source = "video" if getattr(event, "source", "camera") == "video" else "webcam"
            if expected_source != detected_source:
                return {
                    "status": "SESSION_SOURCE_MISMATCH",
                    "step_id": self.get_progress().get("current_step"),
                    "next_step_id": self.get_progress().get("current_step"),
                    "guidance": f"This session is using {expected_source} input; {detected_source} frames are ignored.",
                }

        result = self._session.process_event(event)
        if self._active_session_id:
            perception = result.get("perception") or {}
            signature = None
            if result.get("status") in {"DEVIATION", "UNCERTAIN"}:
                signature = (
                    result.get("status"),
                    result.get("step_id"),
                    result.get("deviation_type"),
                    result.get("detected_activity") or perception.get("activity"),
                    result.get("detected_object") or perception.get("object"),
                    result.get("expected_object"),
                    result.get("guidance"),
                )

            if signature is not None and signature == self._last_persisted_signature:
                self._repeat_count += 1
                if self._repeat_count % 10 == 0:
                    self._session_store.append_repeat_update(
                        self._active_session_id,
                        self._last_persisted_timestamp or "",
                        self._repeat_count,
                    )
                    self._saved_repeat_count = self._repeat_count
            else:
                self._flush_repeat_count()
                timestamp = perception.get("timestamp") or utc_timestamp()
                self._last_persisted_signature = signature
                self._last_persisted_timestamp = timestamp if signature is not None else None
                self._repeat_count = 1 if signature is not None else 0
                self._saved_repeat_count = 1 if signature is not None else 0
                self._session_store.append_event(self._active_session_id, {
                    "timestamp": timestamp,
                    "decision_source": "automatic",
                    "repeat_count": 1,
                    "perception": perception,
                    "decision": result,
                })
            if result.get("status") == "COMPLETED":
                self.end_session("COMPLETED")
        return result

    def _flush_repeat_count(self) -> None:
        if (
            self._active_session_id
            and self._last_persisted_timestamp
            and self._repeat_count > self._saved_repeat_count
        ):
            self._session_store.append_repeat_update(
                self._active_session_id,
                self._last_persisted_timestamp,
                self._repeat_count,
            )
            self._saved_repeat_count = self._repeat_count

    def end_session(self, status: str) -> Dict[str, Any]:
        """Complete or cancel the current persistent session."""
        if status not in {"COMPLETED", "CANCELLED", "INCOMPLETE", "FAILED"}:
            raise ValueError("Unsupported session status")
        if status == "COMPLETED" and not self.get_progress().get("completed"):
            raise ValueError("Protocol steps are not complete")
        if not self._active_session_id:
            raise ValueError("No active session")
        self._flush_repeat_count()
        record = self._session_store.update(self._active_session_id, {
            "status": status,
            "completed_at": utc_timestamp(),
        })
        if record is None:
            raise ValueError("Session record was not found")
        return record

    def list_sessions(self) -> List[Dict[str, Any]]:
        return self._session_store.list()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._session_store.get(session_id)

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._session_store.get_metadata(session_id)

    def get_session_review(self, session_id: str) -> Optional[Dict[str, Any]]:
        record = self._session_store.get(session_id)
        if record is None:
            return None
        if session_id == self._active_session_id:
            record["current_step"] = self.get_progress().get("current_step")
            record["progress"] = self.get_progress()
        return record

    def update_video_processing(
        self,
        session_id: str,
        state: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        return self._session_store.update_processing(session_id, state)

    def confirm_uncertain(self, session_id: str, operator: str) -> Dict[str, Any]:
        """Advance only a protocol-authorized uncertain step by explicit confirmation."""
        step_id = self.get_progress().get("current_step")
        if not self._manual_confirmation_allowed(step_id):
            raise ValueError("Manual confirmation is not enabled for this protocol")
        if session_id != self._active_session_id:
            raise ValueError("Session is not the active session")

        record = self._session_store.get(session_id)
        if record is None or record.get("status") != "IN_PROGRESS":
            raise ValueError("Session is not in progress")
        if not self.get_progress().get("current_step"):
            raise ValueError("There is no current protocol step to confirm")

        events = record.get("events", [])
        uncertain_event = next((
            item for item in reversed(events)
            if (item.get("decision") or {}).get("status") == "UNCERTAIN"
            and (item.get("decision") or {}).get("step_id") == self.get_progress().get("current_step")
        ), None)
        if uncertain_event is None:
            raise ValueError("No uncertain observation is awaiting confirmation")

        step = self._session.adapter.engine.sm.current_step()
        decision = self._session.adapter.engine.process({
            "activity": step.get("activity"),
            "object": step.get("expected_object"),
            "confidence": 1.0,
            "source": "manual",
        })
        if decision.get("status") not in {"CORRECT", "COMPLETED"}:
            raise ValueError("The protocol engine did not accept the confirmed step")

        confirmed_at = utc_timestamp()
        confirmation = {
            "operator": operator,
            "confirmed_at": confirmed_at,
            "source_uncertain_event": uncertain_event.get("timestamp"),
        }
        perception = {
            "timestamp": confirmed_at,
            "activity": step.get("activity"),
            "object": step.get("expected_object"),
            "confidence": None,
            "source": "manual",
        }
        result = {
            **decision,
            "expected_activity": step.get("activity"),
            "expected_object": step.get("expected_object"),
            "detected_activity": step.get("activity"),
            "detected_object": step.get("expected_object"),
            "decision_source": "manual_confirmation",
            "manual_confirmation": confirmation,
            "perception": perception,
        }
        self._session.last_result = result
        self._session.event_count += 1
        mission_event = self._session.event_store.record(
            step_id=result.get("step_id"),
            activity=step.get("activity"),
            detected_object=step.get("expected_object"),
            confidence=None,
            status=str(result.get("status")),
            deviation=None,
            guidance=result.get("guidance"),
        )
        self._session.short_term_memory.add(mission_event)
        self._session.voice_guidance.speak_decision(
            status=result.get("status"),
            guidance=result.get("guidance"),
            step_id=result.get("step_id"),
            next_step_id=result.get("next_step_id"),
        )
        self._session_store.append_event(session_id, {
            "timestamp": confirmed_at,
            "decision_source": "manual_confirmation",
            "manual_confirmation": confirmation,
            "perception": perception,
            "decision": result,
        })
        if result.get("status") == "COMPLETED":
            self.end_session("COMPLETED")
        return result

    def _record_protocol_action(self, source: str, operator: str) -> Dict[str, Any]:
        step = self._session.adapter.engine.sm.current_step()
        if not step:
            raise ValueError("There is no current protocol step")
        decision = self._session.adapter.engine.process({
            "activity": step.get("activity"),
            "object": step.get("expected_object"),
            "confidence": 1.0,
            "source": source,
        })
        timestamp = utc_timestamp()
        result = {
            **decision,
            "expected_activity": step.get("activity"),
            "expected_object": step.get("expected_object"),
            "detected_activity": step.get("activity"),
            "detected_object": step.get("expected_object"),
            "decision_source": source,
            "perception": {
                "timestamp": timestamp,
                "activity": step.get("activity"),
                "object": step.get("expected_object"),
                "confidence": None,
                "source": source,
            },
        }
        self._session.last_result = result
        self._session.event_count += 1
        event = self._session.event_store.record(
            step_id=result.get("step_id"),
            activity=step.get("activity"),
            detected_object=step.get("expected_object"),
            confidence=None,
            status=str(result.get("status")),
            guidance=result.get("guidance"),
        )
        self._session.short_term_memory.add(event)
        if self._active_session_id:
            self._session_store.append_event(self._active_session_id, {
                "timestamp": timestamp,
                "decision_source": source,
                "operator": operator,
                "perception": result["perception"],
                "decision": result,
            })
        return result

    def perform_session_action(
        self,
        session_id: str,
        action: str,
        operator: str = "not_provided",
    ) -> Dict[str, Any]:
        if session_id != self._active_session_id:
            raise ValueError("Session is not the active session")
        record = self._session_store.get_metadata(session_id)
        if not record or record.get("status") != "IN_PROGRESS":
            raise ValueError("Session is not in progress")
        step = self._session.adapter.engine.sm.current_step()
        if not step or step.get("session_action") != action:
            raise ValueError("Action does not match the current protocol step")

        evidence: Dict[str, Any] | None = None
        if action == "capture_evidence":
            from backend.services.camera_service import get_camera_service

            jpeg = get_camera_service().get_jpeg()
            if not jpeg:
                raise ValueError("No local camera frame is available to capture")
            evidence_dir = self._session_store.directory.parent / "evidence" / session_id
            evidence_dir.mkdir(parents=True, exist_ok=True)
            evidence_path = evidence_dir / f"{step['step_id']}.jpg"
            evidence_path.write_bytes(jpeg)
            evidence = {"path": str(evidence_path), "kind": "image", "step_id": step["step_id"]}
        elif action != "save_observation":
            raise ValueError("Unsupported configured session action")

        result = self._record_protocol_action(source="operator_action", operator=operator)
        if evidence:
            current_record = self._session_store.get(session_id) or {}
            self._session_store.update(session_id, {
                "evidence": [*current_record.get("evidence", []), evidence],
            })
        if action == "save_observation":
            current_record = self._session_store.get(session_id) or {}
            reports_dir = self._session_store.directory.parent / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            report_path = reports_dir / f"{session_id}.json"
            report_path.write_text(
                __import__("json").dumps(current_record, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._session_store.update(session_id, {
                "report_path": str(report_path),
            })
        return result

    def reset(self) -> "MissionService":
        """Reset the mission session to the protocol's initial state.

        Clears event/session state AND the protocol state machine via
        the existing LivePerceptionSession.reset(), so the next event
        starts from the first protocol step. Generic: no hardcoded
        steps, works with whatever protocol is currently loaded.
        """
        active = self._session_store.get_metadata(self._active_session_id) if self._active_session_id else None
        if active and active.get("status") == "IN_PROGRESS":
            self.end_session("CANCELLED")
        self._active_session_id = None
        self._last_persisted_signature = None
        self._last_persisted_timestamp = None
        self._repeat_count = 0
        self._saved_repeat_count = 0
        self._session.reset()
        return self


_service: Optional[MissionService] = None


def get_mission_service() -> MissionService:
    """Return the process-wide singleton mission service."""
    global _service
    if _service is None:
        _service = MissionService()
    return _service


def get_mission_status() -> MissionStatus:
    """Return the shared MissionStatus instance."""
    return get_mission_service().status_api


def reset_mission_service(
    protocol_path: str | Path = DEFAULT_PROTOCOL_PATH,
) -> MissionService:
    """Rebuild the singleton (mainly useful for tests)."""
    global _service
    _service = MissionService(protocol_path=protocol_path)
    return _service

