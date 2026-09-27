# ASTRA-GUARD Development Guide

## 1. Purpose

This document explains the internal development structure of ASTRA-GUARD and provides guidance for extending the prototype.

ASTRA-GUARD is organized into separate layers so that perception, protocol interpretation, mission validation, decision making, simulation, and presentation can be developed and tested independently.

---

## 2. Development Architecture

The main development architecture is:

```text
Perception Layer
       ↓
Perception Event
       ↓
Protocol Integration
       ↓
Mission State
       ↓
Sequence Validation
       ↓
Deviation Detection
       ↓
Decision Engine
       ↓
Guidance / Recovery
```

The system also contains controlled simulation and testing layers.

---

## 3. Main Source Directories

The major source directories are:

```text
agent/
backend/
experiments/
simulation/
tests/
frontend/
models/
scripts/
training/
```

Each directory has a specific responsibility.

---

## 4. Agent / Perception Layer

The `agent/` directory contains the main perception and protocol-integration components.

The perception layer is responsible for converting webcam observations into structured information that can be evaluated by the protocol engine.

The general flow is:

```text
Camera Frame
     ↓
Object Detection
     ↓
Hand Tracking
     ↓
Perception Processing
     ↓
Perception Event
```

The perception layer should not directly decide whether a mission step is correct or incorrect.

That responsibility belongs to the decision layer.

---

## 5. Object Detection

The prototype uses Ultralytics YOLO for generic object detection.

The current model is:

```text
yolo11n.pt
```

The detector produces information such as:

* Object class
* Confidence
* Bounding box

The output is then passed to the object-mapping layer.

---

## 6. Object Mapping

Generic vision classes are mapped to protocol-level object names.

Example:

```text
bottle
   ↓
biological_sample

cup
   ↓
sample_chamber

cell phone
   ↓
experiment_controller
```

The mapping is deterministic.

This separation allows the perception model and protocol vocabulary to remain independent.

---

## 7. Hand Tracking

MediaPipe is used for hand tracking.

Hand information provides additional context to the perception pipeline.

The current prototype does not use hand tracking as a standalone trained action-recognition system.

Future versions may combine hand pose, object interaction, temporal information, and body pose for more advanced activity recognition.

---

## 8. Perception Event

The perception layer produces a structured perception event.

Conceptually:

```text
PerceptionEvent
├── activity
├── object
├── confidence
└── perception metadata
```

This event provides a consistent interface between computer vision and protocol validation.

Keeping this interface structured makes the decision engine independent of the camera implementation.

---

## 9. Activity Interpretation

The current `ActivityInterpreter` is deterministic.

It uses protocol state and perception information to determine the activity associated with the current mission step.

For example:

```text
S001 → CHECK_EQUIPMENT
S002 → RETRIEVE_SAMPLE
S003 → OPEN_CONTAINER
S004 → TRANSFER_SAMPLE
S005 → START_EXPERIMENT
S006 → RECORD_RESULT
S007 → SECURE_SAMPLE
S008 → COMPLETE_EXPERIMENT
```

This should not be described as a trained human-action recognition model.

---

## 10. Protocol Layer

The experiment protocol is stored as YAML configuration.

The main protocol directory is:

```text
experiments/EXP001_TARDIGRADE/
```

It contains:

```text
activities.yaml
experiment.yaml
objects.yaml
rules.yaml
steps.yaml
```

The protocol loader converts these configuration files into structures used by the mission engine.

---

## 11. Mission State Machine

The mission state machine tracks the current protocol step.

Example:

```text
S001
 ↓
S002
 ↓
S003
 ↓
S004
 ↓
S005
 ↓
S006
 ↓
S007
 ↓
S008
```

A valid event can advance the state.

A deviation does not automatically advance the mission state.

This preserves the expected protocol sequence.

---

## 12. Sequence Validation

Sequence validation checks whether the observed activity is valid for the current protocol state.

For example:

```text
Expected:
S002 → RETRIEVE_SAMPLE

Observed:
START_EXPERIMENT
```

The observation does not match the current protocol state and can therefore be classified as a sequence deviation.

---

## 13. Deviation Detection

The deviation layer identifies violations of the expected protocol condition.

Current deviation categories include:

```text
WRONG_OBJECT
WRONG_SEQUENCE
SKIPPED_STEP
UNKNOWN_ACTION
LOW_CONFIDENCE
```

The decision engine uses these conditions to produce the final status.

---

## 14. Decision Engine

The Decision Engine is deterministic and rule-based.

It evaluates:

```text
Current Mission State
        +
Perception Event
        +
Protocol Rules
        ↓
Decision
```

The main outcomes are:

```text
CORRECT
DEVIATION
UNCERTAIN
COMPLETED
```

The system can also provide a deviation reason and recovery guidance.

---

## 15. Decision Priority

The decision engine follows a controlled evaluation order.

Conceptually:

```text
Completed Experiment?
       ↓
Current Protocol Step
       ↓
Validate Perception
       ↓
Check Confidence / Object Conditions
       ↓
Check Sequence
       ↓
Determine Deviation
       ↓
Generate Guidance
       ↓
Return Decision
```

The exact implementation should remain deterministic so that identical inputs produce reproducible results.

---

## 16. Guidance and Recovery

When a deviation occurs, the system generates guidance.

Example:

```text
Wrong object detected.
Expected biological_sample.
```

The system does not automatically modify the mission state after a deviation.

The user/operator can correct the action and retry the expected step.

The recovery concept is:

```text
Detect
  ↓
Explain
  ↓
Guide
  ↓
Correct Action
  ↓
Validate Again
  ↓
Continue
```

---

## 17. Controlled Simulation

The `simulation/` directory provides deterministic protocol scenarios.

The controlled demonstration covers:

```text
CORRECT
DEVIATION
UNCERTAIN
```

This allows the decision engine to be demonstrated without depending on real-time camera conditions.

Controlled simulation should be used when reproducible presentation results are required.

---

## 18. Live Webcam Runtime

The live runtime connects the perception pipeline to the decision system.

The main entry point is:

```text
run_live.py
```

The runtime initializes:

```text
YOLO Detector
MediaPipe Hand Tracker
Live Perception Processor
Protocol-Aware Adapter
Decision Engine
Live Overlay
Webcam Runtime
```

The webcam frame is continuously processed until the user presses `Q`.

---

## 19. Main Demo Launcher

The recommended demonstration entry point is:

```text
run.py
```

It launches:

```text
1. Live Webcam Demo
2. Controlled Protocol Demo
3. Exit
```

The controlled demo is deterministic.

The live demo demonstrates actual webcam perception.

---

## 20. Testing Strategy

ASTRA-GUARD uses automated tests to verify individual components and integrated behavior.

Run the complete suite with:

```powershell
python -m pytest -q
```

The current regression baseline is:

```text
124 passed
```

Tests should be executed after changes to:

* Protocol configuration
* State machine
* Sequence validation
* Deviation rules
* Perception mapping
* Decision logic
* Runtime integration

---

## 21. Test-Driven Development Approach

When adding a new behavior:

```text
1. Define expected behavior
        ↓
2. Add or update a test
        ↓
3. Implement the behavior
        ↓
4. Run targeted tests
        ↓
5. Run complete test suite
        ↓
6. Run controlled demo
```

This reduces the risk of breaking existing protocol behavior.

---

## 22. Adding a New Protocol

A new protocol should be created as a separate experiment directory.

Example:

```text
experiments/EXP002_NEW_EXPERIMENT/
```

Create the required configuration files:

```text
activities.yaml
experiment.yaml
objects.yaml
rules.yaml
steps.yaml
```

The protocol should define:

* Experiment metadata
* Activities
* Protocol objects
* Validation rules
* Ordered mission steps

The protocol loader should then be used to validate the configuration.

---

## 23. Adding a New Object Mapping

To add support for a generic vision object:

1. Identify the generic
