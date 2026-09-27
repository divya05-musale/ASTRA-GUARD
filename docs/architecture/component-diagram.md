# ASTRA-GUARD Component Diagram

## 1. Overview

ASTRA-GUARD is organized into modular components that separate visual perception, protocol processing, mission validation, decision making, and user interaction.

The modular design allows individual components to be tested and extended independently.

---

## 2. Component Architecture

```text
+-------------------------------------------------------------+
|                       ASTRA-GUARD                            |
+-------------------------------------------------------------+
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
+----------------+   +----------------+   +-------------------+
|   Perception   |   |    Protocol    |   |    Simulation     |
|     Layer      |   |     Layer      |   |      Layer        |
+----------------+   +----------------+   +-------------------+
| YOLO Detector  |   | ProtocolLoader |   | SimulationRunner  |
| Hand Tracker   |   | YAML Config    |   | Demo Scenarios   |
| Event Builder  |   | Steps/Rules    |   | Controlled Tests  |
+----------------+   +----------------+   +-------------------+
          |                   |                   |
          +-------------------+-------------------+
                              |
                              v
                  +-----------------------+
                  | Mission Decision Core |
                  +-----------------------+
                  | State Machine         |
                  | Sequence Validator    |
                  | Deviation Detector    |
                  | Decision Engine       |
                  +-----------------------+
                              |
                              v
                  +-----------------------+
                  | Guidance / Presentation|
                  +-----------------------+
                  | Live Overlay          |
                  | Decision Output       |
                  | Demo Launcher         |
                  +-----------------------+
```

---

## 3. Perception Components

### Object Detector

**Technology:** Ultralytics YOLO

Purpose:

* Detect objects in webcam frames.
* Produce object classes.
* Produce confidence scores.
* Produce bounding boxes.

The current prototype uses a generic YOLO model.

---

### Hand Tracker

**Technology:** MediaPipe

Purpose:

* Detect hands.
* Track hand landmarks.
* Provide additional interaction context.

The hand tracker complements object detection.

It is not currently used as a standalone trained action-recognition system.

---

### Live Perception Processor

Purpose:

* Process incoming camera frames.
* Combine object and hand perception.
* Produce structured perception information.

Conceptually:

```text
Frame
 ↓
Object Detection + Hand Tracking
 ↓
Processed Perception
```

---

### Perception Event

Purpose:

Provide a structured interface between perception and protocol reasoning.

Example:

```text
PerceptionEvent
---------------
activity
object
confidence
```

---

### Object Mapping

Purpose:

Convert generic detector labels into protocol-level objects.

Example:

```text
bottle
   ↓
biological_sample
```

The mapping is deterministic.

---

## 4. Protocol Components

### Protocol Loader

Purpose:

* Load protocol configuration.
* Validate protocol structure.
* Load activities.
* Load objects.
* Load mission steps.
* Load decision rules.

Protocol configuration is stored in YAML files.

---

### Experiment Configuration

Defines the metadata for the experimental protocol.

Current prototype:

```text
EXP001
TARDIGRADE
Microgravity
Biological Science
```

---

### Activity Configuration

Defines the activities available in the protocol.

Examples:

```text
CHECK_EQUIPMENT
RETRIEVE_SAMPLE
OPEN_CONTAINER
TRANSFER_SAMPLE
START_EXPERIMENT
RECORD_RESULT
SECURE_SAMPLE
COMPLETE_EXPERIMENT
```

---

### Object Configuration

Defines protocol-level objects.

Examples:

```text
experiment_container
biological_sample
sample_chamber
experiment_controller
observation_interface
```

---

### Step Configuration

Defines the expected activity and object for each mission step.

Example:

```text
S001
Expected Activity:
CHECK_EQUIPMENT

Expected Object:
experiment_container
```

---

### Rule Configuration

Defines protocol validation and deviation conditions.

The rules support deterministic protocol reasoning.

---

## 5. Mission Decision Components

### Mission State Machine

Tracks the current protocol step.

Example:

```text
S001 → S002 → S003 → S004 → S005
                         ↓
                       ...
                         ↓
                        S008
```

The state machine provides mission context to the decision system.

---

### Activity Interpreter

Purpose:

Map the current mission state to the protocol activity.

Example:

```text
S001 → CHECK_EQUIPMENT
S002 → RETRIEVE_SAMPLE
S003 → OPEN_CONTAINER
```

The current implementation is deterministic and protocol-aware.

---

### Sequence Validator

Purpose:

Determine whether the detected event is occurring in the expected sequence.

It helps detect:

* Wrong sequence
* Skipped steps
* Premature actions
* Unexpected actions

---

### Deviation Detector

Purpose:

Identify and classify protocol deviations.

Examples:

```text
WRONG_OBJECT
WRONG_SEQUENCE
SKIPPED_STEP
UNKNOWN_ACTION
LOW_CONFIDENCE
```

---

### Decision Engine

Purpose:

Combine perception information and protocol state to produce the final decision.

Inputs include:

```text
Current Step
Expected Activity
Expected Object
Detected Activity
Detected Object
Confidence
Validation Result
Deviation Information
```

Outputs:

```text
CORRECT
DEVIATION
UNCERTAIN
```

The current implementation is deterministic and rule-based.

---

## 6. Guidance Components

### Guidance Generator

Converts the decision into an actionable message.

Examples:

```text
CORRECT
→ Equipment check completed.
  Proceed to retrieve the sample.
```

```text
DEVIATION
→ Wrong object detected.
  Please select the biological sample.
```

```text
UNCERTAIN
→ Detection confidence is low.
  Please repeat or hold the action for verification.
```

---

### Live Overlay

Displays decision information during webcam execution.

Typical information includes:

```text
ASTRA-GUARD

Step: S001
Activity: CHECK_EQUIPMENT
Object: experiment_controller
Confidence: 0.57

Expected Activity: CHECK_EQUIPMENT
Expected Object: experiment_container

Status: DEVIATION
Deviation: WRONG_OBJECT

Guidance:
Wrong object detected.
Expected experiment_container
```

---

## 7. Simulation Components

### Simulation Runner

Provides deterministic test execution without requiring a webcam.

It is used to validate the mission decision core.

---

### Controlled Demo

Provides predefined presentation scenarios.

The demo shows:

```text
CORRECT
DEVIATION
UNCERTAIN
```

This makes the system behavior repeatable during demonstrations.

---

## 8. Entry Points

### `run.py`

Main project entry point.

It launches the final demo launcher.

---

### `demo.py`

Provides the final demo menu.

Available modes:

```text
1. Live Webcam Demo
2. Controlled Protocol Demo
3. Exit
```

---

### `run_live.py`

Starts the live webcam perception pipeline.

Processing flow:

```text
Webcam
 ↓
YOLO
 ↓
MediaPipe
 ↓
Perception
 ↓
Protocol Integration
 ↓
Decision Engine
 ↓
Live Overlay
```

---

## 9. Testing Components

ASTRA-GUARD includes automated tests covering the major system layers.

Tests validate areas such as:

* Protocol loading
* Mission state transitions
* Sequence validation
* Deviation detection
* Perception processing
* Object mapping
* Protocol integration
* Decision outcomes
* Simulation behavior

The current regression suite contains:

```text
124 passed
```

---

## 10. Component Interaction

The major interaction can be summarized as:

```text
              PERCEPTION
                  |
                  v
        +-------------------+
        | Perception Event  |
        +-------------------+
                  |
                  v
              PROTOCOL
                  |
                  v
        +-------------------+
        | Mission State     |
        +-------------------+
                  |
                  v
             VALIDATION
                  |
        +---------+---------+
        |         |         |
        v         v         v
     Correct   Deviation  Uncertain
        |         |         |
        +---------+---------+
                  |
                  v
              GUIDANCE
```

---

## 11. Design Principles

### Modularity

Each major responsibility is separated into an independent component.

### Deterministic Decision Making

Protocol decisions are based on explicit state and rules.

### Testability

Core components can be tested without requiring live webcam input.

### Extensibility

Future perception models can be integrated without redesigning the entire decision core.

### Transparency

The system exposes the reason for a deviation or uncertainty instead of returning only a binary result.

---

## 12. Current Technology Boundaries

The architecture intentionally distinguishes between current prototype functionality and future extensions.

Current implementation:

```text
YOLO
+
MediaPipe
+
Deterministic Object Mapping
+
Protocol-Aware Activity Interpretation
+
Rule-Based Decision Engine
```

Future extensions may include:

```text
Domain-Specific Object Detection
+
Temporal Action Recognition
+
Astronaut Pose Estimation
+
Multimodal Perception
```

No LLM is currently required for the core decision pipeline.

---

## 13. Summary

ASTRA-GUARD uses a layered component architecture.

The perception layer observes the environment, the protocol layer defines mission expectations, and the decision layer validates observations against those expectations.

This architecture supports controlled experimentation today while providing a clear path toward more advanced onboard monitoring capabilities.
