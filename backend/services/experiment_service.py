"""Discover experiment protocols stored in the local experiments folder."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.mission.protocol_loader import ProtocolLoader


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS_ROOT = PROJECT_ROOT / "experiments"


def list_experiments() -> Dict[str, Any]:
    """Return configured protocols and identify incomplete packages."""
    experiments: List[Dict[str, Any]] = []
    if not EXPERIMENTS_ROOT.is_dir():
        return {"experiments": experiments, "count": 0}

    for directory in sorted(EXPERIMENTS_ROOT.iterdir()):
        if not directory.is_dir() or not directory.name.startswith("EXP"):
            continue

        experiment_id = directory.name.split("_", 1)[0]
        item: Dict[str, Any] = {
            "experiment_id": experiment_id,
            "name": directory.name,
            "available": False,
            "error": None,
        }
        try:
            protocol = ProtocolLoader(directory).load()
            metadata = protocol.get_experiment()
            item.update({
                "experiment_id": str(metadata["experiment_id"]),
                "name": str(metadata.get("experiment_name") or directory.name),
                "available": True,
                "steps_count": len(protocol.get_steps()),
            })
        except (OSError, KeyError, TypeError, ValueError) as exc:
            item["error"] = str(exc)
        experiments.append(item)

    return {"experiments": experiments, "count": len(experiments)}


def find_valid_experiment(experiment_id: str) -> Optional[Path]:
    """Resolve an ID only when its local protocol validates successfully."""
    for item in list_experiments()["experiments"]:
        if item["experiment_id"] != experiment_id or not item["available"]:
            continue
        for directory in sorted(EXPERIMENTS_ROOT.iterdir()):
            if not directory.is_dir() or not directory.name.startswith("EXP"):
                continue
            try:
                protocol = ProtocolLoader(directory).load()
            except (OSError, KeyError, TypeError, ValueError):
                continue
            if str(protocol.get_experiment().get("experiment_id")) == experiment_id:
                return directory
    return None


def get_telemetry() -> Dict[str, Any]:
    return {}

