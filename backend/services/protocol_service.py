"""Protocol service: load EXP001 protocol, track step-level metadata."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from agent.mission.protocol_loader import ProtocolLoader


_DEFAULT_EXPERIMENT_DIR = Path("experiments/EXP001_TARDIGRADE")


class ProtocolService:
    """Read-only access to a loaded experiment protocol plus live metadata."""

    def __init__(self, experiment_dir: str | Path = _DEFAULT_EXPERIMENT_DIR) -> None:
        self.experiment_dir = Path(experiment_dir)
        self._loader: Optional[ProtocolLoader] = None
        self._loaded_at: Optional[str] = None

    def _ensure_loaded(self) -> ProtocolLoader:
        if self._loader is None:
            loader = ProtocolLoader(self.experiment_dir).load()
            self._loader = loader
            self._loaded_at = datetime.now().isoformat()
        return self._loader

    def reload(self) -> Dict[str, Any]:
        self._loader = None
        loader = self._ensure_loaded()
        return {
            "reloaded": True,
            "experiment_id": loader.get_experiment().get("experiment_id"),
            "steps": len(loader.get_steps()),
            "activities": len(loader.get_activities()),
            "objects": len(loader.get_objects()),
            "rules": len(loader.get_rules()),
            "loaded_at": self._loaded_at,
        }

    def summary(self) -> Dict[str, Any]:
        loader = self._ensure_loaded()
        exp = loader.get_experiment()
        return {
            "experiment": exp,
            "steps_count": len(loader.get_steps()),
            "activities_count": len(loader.get_activities()),
            "objects_count": len(loader.get_objects()),
            "rules_count": len(loader.get_rules()),
            "loaded_at": self._loaded_at,
        }

    def steps(self) -> List[Dict[str, Any]]:
        return list(self._ensure_loaded().get_steps())

    def activities(self) -> List[Dict[str, Any]]:
        return list(self._ensure_loaded().get_activities())

    def objects(self) -> List[Dict[str, Any]]:
        return list(self._ensure_loaded().get_objects())

    def rules(self) -> List[Dict[str, Any]]:
        return list(self._ensure_loaded().get_rules())

    def get_step(self, step_id: str) -> Optional[Dict[str, Any]]:
        for step in self.steps():
            if str(step.get("step_id")) == str(step_id):
                return step
        return None

    def validate(self) -> Dict[str, Any]:
        loader = self._ensure_loaded()
        try:
            ok = loader.validate()
            return {"valid": bool(ok), "error": None}
        except ValueError as exc:
            return {"valid": False, "error": str(exc)}


_PROTOCOL_SERVICE: Optional[ProtocolService] = None


def get_protocol_service() -> ProtocolService:
    global _PROTOCOL_SERVICE
    if _PROTOCOL_SERVICE is None:
        _PROTOCOL_SERVICE = ProtocolService()
    return _PROTOCOL_SERVICE


def reset_protocol_service(
    experiment_dir: str | Path,
) -> ProtocolService:
    """Rebuild the protocol view for the selected experiment."""
    global _PROTOCOL_SERVICE
    _PROTOCOL_SERVICE = ProtocolService(experiment_dir)
    return _PROTOCOL_SERVICE
