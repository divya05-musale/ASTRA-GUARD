"""Run all synthetic scenarios and write CSV execution records."""
from __future__ import annotations
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulation.simulator import SimulationRunner

SESSION_FIELDS = ["session_id", "experiment_id", "experiment_name", "scenario",
                  "start_time", "end_time", "status", "total_events",
                  "normal_events", "deviation_events", "orientation", "source"]
NORMAL_FIELDS = ["session_id", "event_id", "timestamp", "step_id", "activity",
                 "object", "confidence", "orientation", "status", "source", "guidance"]
DEV_FIELDS = ["session_id", "event_id", "timestamp", "step_id", "activity", "object",
              "confidence", "orientation", "deviation_type", "status",
              "expected_activity", "expected_object", "source", "guidance"]


def _write(path: Path, fields, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def main() -> int:
    print("ASTRA-GUARD Synthetic Protocol Simulator")
    print("Experiment: EXP001 - Tardigrade Sample Observation")
    print("")
    runner = SimulationRunner("experiments/EXP001_TARDIGRADE")
    results = runner.run_all()
    data = runner.get_results()
    print("Scenario Results")
    print("---------------------------------------------")
    for name in ["correct_sequence", "wrong_object", "wrong_sequence", "skipped_step",
                 "repeated_step", "premature_action", "timeout", "low_confidence",
                 "invalid_branch", "recovery"]:
        statuses = sorted({r["session"]["status"] for r in results[name]["runs"]})
        print(f"{name:20s} {'/'.join(statuses)}")
    print("")
    _write(Path("data/execution/sessions.csv"), SESSION_FIELDS, data["sessions"])
    _write(Path("data/execution/normal_events.csv"), NORMAL_FIELDS, data["normal_events"])
    _write(Path("data/execution/deviation_events.csv"), DEV_FIELDS, data["deviation_events"])
    print(f"Sessions generated: {len(data['sessions'])}")
    print(f"Normal events: {len(data['normal_events'])}")
    print(f"Deviation events: {len(data['deviation_events'])}")
    print("")
    print("Synthetic simulation completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

