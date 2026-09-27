import subprocess, sys
code = """
from agent.mission.protocol_loader import ProtocolLoader
from agent.mission.state_machine import ProtocolStateMachine
from agent.mission.step_manager import StepManager
from agent.mission.sequence_validator import SequenceValidator
from agent.mission.deviation_detector import DeviationDetector
from agent.mission.decision_engine import DecisionEngine
loader = ProtocolLoader('experiments/EXP001_TARDIGRADE').load()
steps, acts, rules = loader.get_steps(), loader.get_activities(), loader.get_rules()
sm = ProtocolStateMachine(steps)
mgr = StepManager(steps, sm, rules)
val = SequenceValidator(steps, acts)
det = DeviationDetector(steps, acts)
eng = DecisionEngine(sm, mgr, val, det, rules)
def show(label, event):
    out = eng.process(event)
    print(f\"{label}: event={event['activity']}/{event['object']}/conf={event['confidence']} -> {out['status']} step={out['step_id']} next={out['next_step_id']} dev={out['deviation_type']} | {out['guidance']} | state={sm.current_step_id()} complete={sm.is_complete()}\")
print(f\"INITIAL: {sm.current_step_id()} {mgr.get_expected_activity()} (complete={sm.is_complete()})\")
show('CORRECT S001', {'activity':'CHECK_EQUIPMENT','object':'experiment_container','confidence':0.95})
show('WRONG OBJECT @S002', {'activity':'RETRIEVE_SAMPLE','object':'wrong_sample','confidence':0.95})
show('RECOVERY S002', {'activity':'RETRIEVE_SAMPLE','object':'biological_sample','confidence':0.95})
show('LOW CONF @S003', {'activity':'OPEN_CONTAINER','object':'sample_chamber','confidence':0.50})
show('CORRECT S003', {'activity':'OPEN_CONTAINER','object':'sample_chamber','confidence':0.95})
show('CORRECT S004', {'activity':'TRANSFER_SAMPLE','object':'sample_chamber','confidence':0.95})
show('CORRECT S005', {'activity':'START_EXPERIMENT','object':'experiment_controller','confidence':0.95})
show('CORRECT S006', {'activity':'RECORD_RESULT','object':'observation_interface','confidence':0.95})
show('CORRECT S007', {'activity':'SECURE_SAMPLE','object':'sample_chamber','confidence':0.95})
show('FINAL S008', {'activity':'COMPLETE_EXPERIMENT','object':'experiment_controller','confidence':0.95})
"""
r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd="c:/Users/HP/Desktop/ASTRA-GUARD")
open("c:/Users/HP/Desktop/ASTRA-GUARD/phase3_demo.txt", "w").write("STDOUT:\n" + r.stdout + "\nSTDERR:\n" + r.stderr + f"\nRC={r.returncode}\n")
print("demo rc=", r.returncode)
print(r.stdout)
print(r.stderr)
