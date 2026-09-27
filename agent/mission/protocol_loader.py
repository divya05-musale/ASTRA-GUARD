"""Protocol loader for ASTRA-GUARD synthetic experiments."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


class ProtocolLoader:
    """Load and validate an experiment protocol from YAML files."""

    def __init__(self, experiment_path: str | Path) -> None:
        self.experiment_path = Path(experiment_path)
        self._experiment: Optional[Dict[str, Any]] = None
        self._steps: Optional[List[Dict[str, Any]]] = None
        self._activities: Optional[List[Dict[str, Any]]] = None
        self._objects: Optional[List[Dict[str, Any]]] = None
        self._rules: Optional[List[Dict[str, Any]]] = None

    def _load_yaml(self, filename: str) -> Any:
        path = self.experiment_path / filename
        if not path.exists():
            raise ValueError(f"Missing protocol file: {filename}")
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if data is None:
            raise ValueError(f"Protocol file is empty: {filename}")
        return data

    def load(self) -> "ProtocolLoader":
        experiment = self._load_yaml("experiment.yaml")
        steps_doc = self._load_yaml("steps.yaml")
        activities_doc = self._load_yaml("activities.yaml")
        objects_doc = self._load_yaml("objects.yaml")
        rules_doc = self._load_yaml("rules.yaml")
        if isinstance(experiment, dict) and "experiment" in experiment:
            experiment = experiment["experiment"]
        steps = steps_doc.get("steps") if isinstance(steps_doc, dict) else None
        acts = activities_doc.get("activities") if isinstance(activities_doc, dict) else None
        objs = objects_doc.get("objects") if isinstance(objects_doc, dict) else None
        rules = rules_doc.get("rules") if isinstance(rules_doc, dict) else None
        if not isinstance(experiment, dict):
            raise ValueError("Protocol must contain experiment definition")
        if not steps:
            raise ValueError("Protocol must contain steps")
        if not acts:
            raise ValueError("Protocol must contain activities")
        if not objs:
            raise ValueError("Protocol must contain objects")
        if not rules:
            raise ValueError("Protocol must contain rules")
        self._experiment = experiment
        self._steps = sorted(list(steps), key=lambda s: s.get("order", 0))
        self._activities = list(acts)
        self._objects = list(objs)
        self._rules = list(rules)
        self.validate()
        return self

    def validate(self) -> bool:
        if self._experiment is None or self._steps is None:
            raise ValueError("Protocol not loaded. Call load() first.")
        exp_id = self._experiment.get("experiment_id")
        if not exp_id:
            raise ValueError("Protocol must contain experiment_id")
        step_ids = [s.get("step_id") for s in self._steps]
        if any(not sid for sid in step_ids):
            raise ValueError("Every step must contain step_id")
        if len(set(step_ids)) != len(step_ids):
            raise ValueError("Step IDs must be unique")
        orders = [s.get("order") for s in self._steps]
        if sorted(orders) != list(range(1, len(self._steps) + 1)):
            raise ValueError("Step order must be 1..N without gaps")
        act_ids = {a.get("activity_id") for a in (self._activities or [])}
        obj_ids = {o.get("object_id") for o in (self._objects or [])}
        for step in self._steps:
            sid = step.get("step_id")
            act = step.get("activity")
            obj = step.get("expected_object")
            if not act:
                raise ValueError(f"Step {sid} must contain activity")
            if act not in act_ids:
                raise ValueError(f"Unknown activity referenced by step {sid}")
            if not obj:
                raise ValueError(f"Step {sid} must contain expected_object")
            if obj not in obj_ids:
                raise ValueError(f"Unknown object referenced by step {sid}")
        rule_ids = [r.get("rule_id") for r in (self._rules or [])]
        if len(set(rule_ids)) != len(rule_ids):
            raise ValueError("Rule IDs must be unique")
        step_set = set(step_ids)
        for rule in (self._rules or []):
            rid = rule.get("rule_id")
            if rule.get("experiment_id") != exp_id:
                raise ValueError(f"Rule {rid} references wrong experiment_id")
            if rule.get("step_id") not in step_set:
                raise ValueError(f"Rule {rid} references unknown step")
        return True

    def get_experiment(self) -> Dict[str, Any]:
        if self._experiment is None:
            raise ValueError("Protocol not loaded. Call load() first.")
        return self._experiment

    def get_steps(self) -> List[Dict[str, Any]]:
        if self._steps is None:
            raise ValueError("Protocol not loaded. Call load() first.")
        return self._steps

    def get_activities(self) -> List[Dict[str, Any]]:
        if self._activities is None:
            raise ValueError("Protocol not loaded. Call load() first.")
        return self._activities

    def get_objects(self) -> List[Dict[str, Any]]:
        if self._objects is None:
            raise ValueError("Protocol not loaded. Call load() first.")
        return self._objects

    def get_rules(self) -> List[Dict[str, Any]]:
        if self._rules is None:
            raise ValueError("Protocol not loaded. Call load() first.")
        return self._rules

