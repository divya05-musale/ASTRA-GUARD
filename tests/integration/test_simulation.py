"""Integration tests for Phase 4 synthetic simulation (no webcam/AI)."""
from simulation.simulator import SimulationRunner, SCENARIO_ORDER
from simulation.event_generator import EventGenerator

EXP = "experiments/EXP001_TARDIGRADE"


def _run(name):
    runner = SimulationRunner(EXP)
    result = runner.run_scenario(name)
    return runner, result


def test_all_10_scenarios_can_run():
    runner = SimulationRunner(EXP)
    results = runner.run_all()
    assert sorted(results.keys()) == sorted(SCENARIO_ORDER)
    assert len(runner.sessions) == 13  # 4 orientations for correct_sequence + 9 others


def test_unique_session_ids():
    runner = SimulationRunner(EXP)
    runner.run_all()
    ids = [s["session_id"] for s in runner.sessions]
    assert len(ids) == len(set(ids))


def test_correct_sequence_reaches_completed():
    runner, result = _run("correct_sequence")
    for run in result["runs"]:
        assert run["outcome"]["status"] == "COMPLETED"
        assert run["outcome"]["complete"] is True


def test_wrong_object_produces_wrong_object():
    runner, result = _run("wrong_object")
    types = [r["decision"]["deviation_type"] for r in result["runs"][0]["outcome"]["records"]]
    assert "WRONG_OBJECT" in types


def test_wrong_sequence_produces_sequence_deviation():
    runner, result = _run("wrong_sequence")
    types = [r["decision"]["deviation_type"] for r in result["runs"][0]["outcome"]["records"]]
    assert any(t in ("PREMATURE_ACTION", "WRONG_SEQUENCE", "SKIPPED_STEP") for t in types)


def test_skipped_step_produces_skipped_step():
    runner, result = _run("skipped_step")
    types = [r["decision"]["deviation_type"] for r in result["runs"][0]["outcome"]["records"]]
    assert "SKIPPED_STEP" in types


def test_repeated_step_produces_repeated_step():
    runner, result = _run("repeated_step")
    types = [r["decision"]["deviation_type"] for r in result["runs"][0]["outcome"]["records"]]
    assert "REPEATED_STEP" in types


def test_premature_action_produces_premature_action():
    runner, result = _run("premature_action")
    types = [r["decision"]["deviation_type"] for r in result["runs"][0]["outcome"]["records"]]
    assert "PREMATURE_ACTION" in types


def test_timeout_produces_timeout():
    runner, result = _run("timeout")
    types = [r["decision"]["deviation_type"] for r in result["runs"][0]["outcome"]["records"]]
    assert "TIMEOUT" in types


def test_low_confidence_produces_low_confidence():
    runner, result = _run("low_confidence")
    types = [r["decision"]["deviation_type"] for r in result["runs"][0]["outcome"]["records"]]
    assert "LOW_CONFIDENCE" in types


def test_invalid_branch_produces_invalid_branch():
    runner, result = _run("invalid_branch")
    types = [r["decision"]["deviation_type"] for r in result["runs"][0]["outcome"]["records"]]
    assert "INVALID_BRANCH" in types


def test_recovery_reaches_completed():
    runner, result = _run("recovery")
    assert result["runs"][0]["outcome"]["status"] == "COMPLETED"


def test_deviations_do_not_advance_state():
    runner = SimulationRunner(EXP)
    result = runner.run_scenario("wrong_object")
    recs = result["runs"][0]["outcome"]["records"]
    assert recs[1]["decision"]["status"] == "DEVIATION"
    assert recs[1]["state_after"] == "S002"
    assert recs[2]["decision"]["status"] == "CORRECT"


def test_low_confidence_does_not_advance():
    runner = SimulationRunner(EXP)
    result = runner.run_scenario("low_confidence")
    recs = result["runs"][0]["outcome"]["records"]
    assert recs[1]["decision"]["status"] == "UNCERTAIN"
    assert recs[1]["state_after"] == "S002"


def test_orientation_and_source():
    runner = SimulationRunner(EXP)
    runner.run_all()
    orients = {s["orientation"] for s in runner.sessions}
    assert {0, 90, 180, 270} <= orients
    assert all(s["source"] == "synthetic" for s in runner.sessions)
    assert all(e["source"] == "synthetic" for e in runner.normal_events)
    assert all(e["source"] == "synthetic" for e in runner.deviation_events)
    for s in runner.sessions:
        assert s["experiment_id"] == "EXP001"
    gen = EventGenerator()
    evt = gen.generate_event(activity="RETRIEVE_SAMPLE", object="biological_sample",
                             confidence=0.95, orientation=90)
    for key in ("activity", "object", "confidence", "orientation", "timestamp", "source"):
        assert key in evt
    assert evt["source"] == "synthetic"
