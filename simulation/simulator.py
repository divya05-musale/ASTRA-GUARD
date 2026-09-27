"""Simulation runner: run scenarios, collect session/event records."""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any, Dict, List
from simulation.event_generator import EventGenerator, BASE_TIME
from simulation.protocol_simulator import ProtocolSimulator

SCENARIO_ORDER = ["correct_sequence", "wrong_object", "wrong_sequence", "skipped_step",
                  "repeated_step", "premature_action", "timeout", "low_confidence",
                  "invalid_branch", "recovery"]

_ORIENTATION_PLAN = {"correct_sequence": [0, 90, 180, 270]}


class SimulationRunner:
    """Run each scenario with a fresh engine; deterministic IDs/timestamps."""

    def __init__(self, experiment_path: str = "experiments/EXP001_TARDIGRADE") -> None:
        self.experiment_path = experiment_path
        self.sessions: List[Dict[str, Any]] = []
        self.normal_events: List[Dict[str, Any]] = []
        self.deviation_events: List[Dict[str, Any]] = []
        self._sim_counter = 0

    def _load_scenario(self, name: str):
        module = __import__(f"simulation.scenarios.{name}", fromlist=["build_events"])
        return module.build_events

    def _orientations(self, name: str) -> List[int]:
        return list(_ORIENTATION_PLAN.get(name, [0]))

    def run_scenario(self, scenario_name: str) -> Dict[str, Any]:
        build = self._load_scenario(scenario_name)
        results = []
        for orientation in self._orientations(scenario_name):
            self._sim_counter += 1
            sid = f"SIM-{self._sim_counter:03d}"
            gen = EventGenerator()
            events = build(gen, orientation=orientation)
            sim = ProtocolSimulator(self.experiment_path)
            outcome = sim.run(events)
            start = BASE_TIME + timedelta(seconds=(self._sim_counter - 1) * 1000)
            end = start + timedelta(seconds=len(events))
            normal = sum(1 for r in outcome["records"] if r["decision"]["status"] in ("CORRECT", "COMPLETED"))
            dev = sum(1 for r in outcome["records"] if r["decision"]["status"] in ("DEVIATION", "UNCERTAIN"))
            session = {"session_id": sid, "experiment_id": sim.experiment.get("experiment_id"),
                       "experiment_name": sim.experiment.get("experiment_name"),
                       "scenario": scenario_name, "start_time": start.isoformat(),
                       "end_time": end.isoformat(), "status": outcome["status"],
                       "total_events": len(outcome["records"]), "normal_events": normal,
                       "deviation_events": dev, "orientation": orientation, "source": "synthetic"}
            self.sessions.append(session)
            for i, rec in enumerate(outcome["records"], start=1):
                evt, dec = rec["event"], rec["decision"]
                ts = (start + timedelta(seconds=i)).isoformat()
                eid = f"EVT-{i:03d}"
                if dec["status"] in ("CORRECT", "COMPLETED"):
                    self.normal_events.append({"session_id": sid, "event_id": eid, "timestamp": ts,
                                               "step_id": dec.get("step_id"), "activity": evt.get("activity"),
                                               "object": evt.get("object"), "confidence": evt.get("confidence"),
                                               "orientation": evt.get("orientation", orientation),
                                               "status": dec.get("status"), "source": "synthetic",
                                               "guidance": dec.get("guidance", "")})
                else:
                    self.deviation_events.append({"session_id": sid, "event_id": eid, "timestamp": ts,
                                                  "step_id": dec.get("step_id"), "activity": evt.get("activity"),
                                                  "object": evt.get("object"), "confidence": evt.get("confidence"),
                                                  "orientation": evt.get("orientation", orientation),
                                                  "deviation_type": dec.get("deviation_type"),
                                                  "status": dec.get("status"),
                                                  "expected_activity": dec.get("expected_activity", ""),
                                                  "expected_object": dec.get("expected_object", ""),
                                                  "source": "synthetic",
                                                  "guidance": dec.get("guidance", "")})
            results.append({"session": session, "outcome": outcome})
        return {"scenario": scenario_name, "runs": results}

    def run_all(self) -> Dict[str, Any]:
        out = {}
        for name in SCENARIO_ORDER:
            out[name] = self.run_scenario(name)
        return out

    def get_results(self) -> Dict[str, List[Dict[str, Any]]]:
        return {"sessions": self.sessions, "normal_events": self.normal_events,
                "deviation_events": self.deviation_events}

