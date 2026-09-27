# ASTRA-GUARD Experiment Protocol

## 1. Overview

ASTRA-GUARD uses a structured experimental protocol to demonstrate protocol-aware monitoring and validation.

The primary demonstration protocol is:

```text
Protocol ID:   EXP001
Name:         TARDIGRADE
Domain:       Biological Science
Environment:  Microgravity
Version:      1.0
Status:       Active
```

The protocol is designed as a synthetic academic demonstration.

It is **not an official ISRO flight procedure, NASA procedure, or proprietary operational protocol**.

---

## 2. Experiment Purpose

The purpose of the protocol is to provide a controlled sequence of experimental activities that ASTRA-GUARD can monitor and validate.

The system observes an activity and associated object, compares them with the expected protocol state, and produces a decision.

The main outcomes are:

```text
CORRECT
DEVIATION
UNCERTAIN
```

---

## 3. Protocol Characteristics

The protocol is designed with the following characteristics:

* Structured mission steps
* Explicit expected activities
* Explicit expected objects
* Ordered execution
* Rule-based validation
* Deviation handling
* Confidence-aware decisions
* Recovery guidance
* Orientation-agnostic design

---

## 4. Protocol Steps

The protocol contains eight mission steps.

| Step | Activity            | Expected Object       |
| ---- | ------------------- | --------------------- |
| S001 | CHECK_EQUIPMENT     | experiment_container  |
| S002 | RETRIEVE_SAMPLE     | biological_sample     |
| S003 | OPEN_CONTAINER      | sample_chamber        |
| S004 | TRANSFER_SAMPLE     | sample_chamber        |
| S005 | START_EXPERIMENT    | experiment_controller |
| S006 | RECORD_RESULT       | observation_interface |
| S007 | SECURE_SAMPLE       | sample_chamber        |
| S008 | COMPLETE_EXPERIMENT | experiment_controller |

---

## 5. Step Descriptions

### S001 — CHECK_EQUIPMENT

The mission begins with an equipment check.

Expected activity:

```text
CHECK_EQUIPMENT
```

Expected object:

```text
experiment_container
```

The system validates that the observed event corresponds to the expected equipment-check context.

---

### S002 — RETRIEVE_SAMPLE

The operator retrieves the biological sample.

Expected activity:

```text
RETRIEVE_SAMPLE
```

Expected object:

```text
biological_sample
```

---

### S003 — OPEN_CONTAINER

The sample container is opened.

Expected activity:

```text
OPEN_CONTAINER
```

Expected object:

```text
sample_chamber
```

---

### S004 — TRANSFER_SAMPLE

The biological sample is transferred within the experimental setup.

Expected activity:

```text
TRANSFER_SAMPLE
```

Expected object:

```text
sample_chamber
```

---

### S005 — START_EXPERIMENT

The experiment is started using the experimental controller.

Expected activity:

```text
START_EXPERIMENT
```

Expected object:

```text
experiment_controller
```

---

### S006 — RECORD_RESULT

The experiment result is recorded through the observation interface.

Expected activity:

```text
RECORD_RESULT
```

Expected object:

```text
observation_interface
```

---

### S007 — SECURE_SAMPLE

The sample is secured in the sample chamber.

Expected activity:

```text
SECURE_SAMPLE
```

Expected object:

```text
sample_chamber
```

---

### S008 — COMPLETE_EXPERIMENT

The final protocol step completes the experiment.

Expected activity:

```text
COMPLETE_EXPERIMENT
```

Expected object:

```text
experiment_controller
```

---

## 6. Protocol Execution Model

The protocol follows an ordered state progression:

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
 ↓
COMPLETED
```

The Mission State Machine maintains the current step.

A valid event advances the state to the next expected step.

---

## 7. Expected Event

Each protocol step defines an expected activity and object.

Conceptually:

```text
Current Step
     +
Expected Activity
     +
Expected Object
     |
     v
Validation Conditions
```

The perception pipeline provides the observed event:

```text
Detected Activity
Detected Object
Confidence
```

The Decision Engine compares the observed event against the protocol expectations.

---

## 8. Example Correct Event

For S001:

```text
Expected Activity:
CHECK_EQUIPMENT

Expected Object:
experiment_container
```

If the observed event satisfies these conditions:

```text
Detected Activity:
CHECK_EQUIPMENT

Detected Object:
experiment_container
```

The decision is:

```text
CORRECT
```

The mission state then advances.

---

## 9. Example Deviation

Suppose the system is at S002:

```text
Expected Activity:
RETRIEVE_SAMPLE

Expected Object:
biological_sample
```

If the detected object is:

```text
experiment_controller
```

the expected and detected objects do not match.

The system can produce:

```text
Status:
DEVIATION

Reason:
WRONG_OBJECT
```

and provide recovery guidance.

---

## 10. Example Uncertain Event

If the perception confidence is too low to make a reliable decision:

```text
Confidence:
Low
```

the system can produce:

```text
Status:
UNCERTAIN

Reason:
LOW_CONFIDENCE
```

The operator is asked to repeat or verify the observation.

---

## 11. Protocol Objects

The protocol defines five main objects:

```text
experiment_container
biological_sample
sample_chamber
experiment_controller
observation_interface
```

These are protocol-level representations.

The current generic YOLO detector does not directly recognize all of these specialized names.

Instead, supported generic detections can be mapped to protocol-level objects through deterministic object mapping.

---

## 12. Generic-to-Protocol Mapping

Examples used by the current prototype include:

```text
YOLO class        → Protocol object
---------------------------------------
bottle            → biological_sample
cup               → sample_chamber
bowl              → sample_chamber
cell phone        → experiment_controller
remote            → experiment_controller
```

This mapping is part of the prototype's perception integration layer.

It is a deterministic mapping and should not be interpreted as a custom trained detector for specialized experiment equipment.

---

## 13. Protocol Validation

Validation considers the current mission context.

The decision process can be represented as:

```text
Observed Event
      ↓
Current Mission State
      ↓
Expected Activity/Object
      ↓
Sequence Validation
      ↓
Deviation Detection
      ↓
Decision Engine
      ↓
CORRECT / DEVIATION / UNCERTAIN
```

---

## 14. Protocol Deviation Categories

The prototype supports deviation concepts including:

```text
WRONG_OBJECT
WRONG_SEQUENCE
SKIPPED_STEP
UNKNOWN_ACTION
LOW_CONFIDENCE
```

The exact result depends on the current mission state and observed perception event.

---

## 15. Recovery Guidance

A deviation is not only reported; the system can provide guidance.

Example:

```text
DEVIATION
WRONG_OBJECT

Guidance:
Wrong object detected.
Please select the biological sample.
```

For uncertainty:

```text
UNCERTAIN
LOW_CONFIDENCE

Guidance:
Detection confidence is low.
Please repeat or hold the action for verification.
```

---

## 16. Controlled Demonstration

The controlled demonstration mode uses predefined protocol scenarios.

It demonstrates:

```text
Scenario 1 → CORRECT
Scenario 2 → DEVIATION
Scenario 3 → UNCERTAIN
```

This allows the protocol decision core to be demonstrated consistently without depending on live camera conditions.

---

## 17. Configuration Files

The protocol is represented using YAML configuration files:

```text
experiments/EXP001_TARDIGRADE/
├── experiment.yaml
├── activities.yaml
├── objects.yaml
├── steps.yaml
└── rules.yaml
```

The Protocol Loader reads and validates these configuration files before the protocol is used.

---

## 18. Orientation-Agnostic Design

The protocol metadata identifies the demonstration as orientation-agnostic.

The intended design considers that object and hand interactions may appear under different orientations.

However, orientation handling in the current prototype is primarily an architectural/design property rather than a separately trained orientation-specific perception model.

---

## 19. Important Disclaimer

This protocol is a **synthetic academic demonstration protocol**.

It is not:

* An official ISRO flight procedure
* An official NASA procedure
* A certified astronaut operational procedure
* A proprietary mission procedure

The protocol exists to provide a safe and reproducible environment for demonstrating ASTRA-GUARD's monitoring and protocol-validation architecture.

---

## 20. Summary

EXP001 TARDIGRADE provides ASTRA-GUARD with a structured eight-step mission sequence.

Each step defines:

```text
Step
Activity
Expected Object
Validation Context
```

ASTRA-GUARD uses these expectations to determine whether observed perception events are:

```text
CORRECT
DEVIATION
UNCERTAIN
```

The protocol therefore serves as the structured mission context that connects computer vision perception with deterministic protocol validation.
