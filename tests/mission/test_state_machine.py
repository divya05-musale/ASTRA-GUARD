"""State machine tests using real EXP001 protocol."""
from agent.mission.protocol_loader import ProtocolLoader
from agent.mission.state_machine import ProtocolStateMachine

EXP = "experiments/EXP001_TARDIGRADE"


def _steps():
    return ProtocolLoader(EXP).load().get_steps()


def test_initial_state_is_s001():
    sm = ProtocolStateMachine(_steps())
    assert sm.current_step_id() == "S001"


def test_current_step_returns_s001():
    sm = ProtocolStateMachine(_steps())
    assert sm.current_step()["step_id"] == "S001"


def test_advance_moves_s001_to_s002():
    sm = ProtocolStateMachine(_steps())
    sm.advance()
    assert sm.current_step_id() == "S002"


def test_advance_moves_sequentially():
    sm = ProtocolStateMachine(_steps())
    seen = [sm.current_step_id()]
    for _ in range(7):
        sm.advance()
        seen.append(sm.current_step_id())
    assert seen == ["S001", "S002", "S003", "S004", "S005", "S006", "S007", "S008"]


def test_no_step_skipped():
    sm = ProtocolStateMachine(_steps())
    prev = sm.step_index()
    for _ in range(7):
        sm.advance()
        assert sm.step_index() == prev + 1
        prev = sm.step_index()


def test_reset_returns_to_s001():
    sm = ProtocolStateMachine(_steps())
    sm.advance()
    sm.advance()
    sm.reset()
    assert sm.current_step_id() == "S001"
    assert sm.step_index() == 0


def test_final_step_reaches_completed():
    sm = ProtocolStateMachine(_steps())
    for _ in range(7):
        sm.advance()
    assert sm.current_step_id() == "S008"
    sm.complete_current()
    assert sm.is_complete() is True


def test_cannot_advance_beyond_final():
    sm = ProtocolStateMachine(_steps())
    for _ in range(7):
        sm.advance()
    sm.complete_current()
    assert sm.advance() is None
    assert sm.is_complete() is True
    assert sm.current_step_id() == "S008"

