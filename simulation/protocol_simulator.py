"""Protocol simulator: connect synthetic events to Phase 3 engine."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List
from agent.mission.protocol_loader import ProtocolLoader
from agent.mission.state_machine import ProtocolStateMachine
from agent.mission.step_manager import StepManager
from agent.mission.sequence_validator import SequenceValidator
from agent.mission.deviation_detector import DeviationDetector
from agent.mission.decision_engine import DecisionEngine


class ProtocolSimulator:
    """Drive a fresh Phase 3 DecisionEngine with synthetic events."""

    def __init__(self, experiment_path: str = "experiments/EXP001_TARDIGRADE") -> None:
        loader = ProtocolLoader(experiment_path).load()
        self.experiment = loader.get_experiment()
        steps, acts, rules = loader.get_steps(), loader.get_activities(), loader.get_rules()
        self.sm = ProtocolStateMachine(steps)
        self.manager = StepManager(steps, self.sm, rules)
        self.validator = SequenceValidator(steps, acts)
        self.detector = DeviationDetector(steps, acts)
        self.engine = DecisionEngine(self.sm, self.manager, self.validator, self.detector, rules)
        self.records: List[Dict[str, Any]] = []
        self.event_seq = 0

    @property
    def current_step_id(self) -> str:
        return self.sm.current_step_id()

    def _timeout_decision(self, event: Dict[str, Any], step: Dict[str, Any]) -> Dict[str, Any] | None:
        if event.get("branch_id") == "INVALID_BRANCH" or event.get("branch") == "INVALID_BRANCH":
            sid = str(step.get("step_id"))
            return {"status": "DEVIATION", "step_id": sid, "next_step_id": sid,
                    "deviation_type": "INVALID_BRANCH",
                    "expected_activity": str(step.get("activity")),
                    "expected_object": str(step.get("expected_object")),
                    "detected_activity": event.get("activity"), "detected_object": event.get("object"),
                    "guidance": "Invalid branch detected. Please follow the expected protocol sequence."}
        if "elapsed_sec" in event:
            info = self.detector.check_timeout(float(event["elapsed_sec"]), str(step.get("step_id")))
            if info.get("deviation_type") == "TIMEOUT":
                sid = str(step.get("step_id"))
                return {"status": "DEVIATION", "step_id": sid, "next_step_id": sid,
                        "deviation_type": "TIMEOUT",
                        "expected_activity": str(step.get("activity")),
                        "expected_object": str(step.get("expected_object")),
                        "detected_activity": event.get("activity"), "detected_object": event.get("object"),
                        "guidance": "Step timeout exceeded. Please repeat the current step."}
        return None

    def step(self, event: Dict[str, Any]) -> Dict[str, Any]:
        step = self.sm.current_step()
        forced = self._timeout_decision(event, step)
        decision = forced if forced else self.engine.process(event)
        self.event_seq += 1
        record = {"event_seq": self.event_seq, "event": dict(event),
                  "decision": decision, "state_after": self.sm.current_step_id(),
                  "complete": self.sm.is_complete()}
        self.records.append(record)
        return record

    def run(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        for evt in events:
            self.step(evt)
            if self.sm.is_complete():
                break
        statuses = [r["decision"]["status"] for r in self.records]
        if self.sm.is_complete():
            final = "COMPLETED"
        elif "DEVIATION" in statuses:
            final = "DEVIATION"
        elif "UNCERTAIN" in statuses:
            final = "UNCERTAIN"
        else:
            final = "FAILED"
        return {"status": final, "records": list(self.records),
                "current_step": self.sm.current_step_id(),
                "complete": self.sm.is_complete()}

