# ASTRA-GUARD Data Flow

## 1. Overview

ASTRA-GUARD processes visual observations through multiple layers before producing a protocol decision.

The data flow separates perception, protocol interpretation, validation, decision making, and user guidance.

---

## 2. Live Data Flow

```text
Webcam Frame
     ↓
Object Detection
     ↓
Hand Tracking
     ↓
Perception Data
     ↓
PerceptionEvent
     ↓
Protocol-Aware Mapping
     ↓
Activity Interpretation
     ↓
Mission State
     ↓
Sequence Validation
     ↓
Deviation Detection
     ↓
Decision Engine
     ↓
Decision + Guidance
```

---

## 3. Step-by-Step Flow

### Step 1 — Webcam Capture

The webcam provides the current video frame.

```text
Camera
  ↓
Frame
```

The frame is passed to the perception pipeline.

---

### Step 2 — Object Detection

The YOLO detector analyzes the frame and identifies visible objects.

The detector provides:

```text
Object Class
Confidence
Bounding Box
```

Example:

```text
YOLO Detection
----------------
Class: bottle
Confidence: 0.82
```

---

### Step 3 — Hand Tracking

MediaPipe analyzes the frame for hand landmarks.

Conceptually:

```text
Frame
  ↓
Hand Detection
  ↓
Hand Landmarks
```

Hand information provides additional context for interpreting the observed interaction.

---

### Step 4 — Perception Event Creation

The perception outputs are converted into a structured event.

Example:

```text
PerceptionEvent
----------------
Activity: CHECK_EQUIPMENT
Object: bottle
Confidence: 0.82
```

This event acts as the interface between perception and protocol reasoning.

---

### Step 5 — Protocol-Aware Object Mapping

Generic object classes are mapped to protocol-level objects.

Example:

```text
Generic Detection
       ↓
     bottle
       ↓
Protocol Mapping
       ↓
biological_sample
```

Another example:

```text
Generic Detection
       ↓
   cell phone
       ↓
Protocol Mapping
       ↓
experiment_controller
```

The mapping is deterministic and configured in the perception layer.

---

### Step 6 — Activity Interpretation

The Activity Interpreter determines the protocol-level activity using mission context.

For the current protocol:

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

The current implementation is deterministic and protocol-aware rather than a trained action-recognition model.

---

### Step 7 — Mission State

The Mission State Machine tracks the current step.

Example:

```text
Current Step:
S002

Expected Activity:
RETRIEVE_SAMPLE

Expected Object:
biological_sample
```

The state provides the context required for validation.

---

### Step 8 — Sequence Validation

The Sequence Validator checks whether the observed activity is valid for the current mission step.

For example:

```text
Current Step:
S002

Expected:
RETRIEVE_SAMPLE

Detected:
START_EXPERIMENT
```

The sequence is invalid and can produce a protocol deviation.

---

### Step 9 — Deviation Detection

The Deviation Detector identifies the reason for a protocol mismatch.

Possible deviation categories include:

```text
WRONG_OBJECT
WRONG_SEQUENCE
SKIPPED_STEP
UNKNOWN_ACTION
LOW_CONFIDENCE
```

---

### Step 10 — Decision Engine

The Decision Engine combines the perception event and protocol state.

Conceptually:

```text
Perception Event
       +
Protocol State
       +
Expected Conditions
       +
Validation Results
       ↓
Decision Engine
```

The output is one of:

```text
CORRECT
DEVIATION
UNCERTAIN
```

---

## 4. CORRECT Flow

When the observed event matches the expected protocol condition:

```text
Observation
    ↓
Matches Expected Activity
    ↓
Matches Expected Object
    ↓
Sequence Valid
    ↓
CORRECT
    ↓
Advance Mission State
```

Example:

```text
Expected Activity: CHECK_EQUIPMENT
Expected Object: experiment_container

Detected Activity: CHECK_EQUIPMENT
Detected Object: experiment_container

Result: CORRECT
```

---

## 5. DEVIATION Flow

When the observed event violates the protocol:

```text
Observation
    ↓
Protocol Mismatch
    ↓
Deviation Detection
    ↓
DEVIATION
    ↓
Guidance
```

Example:

```text
Expected Object:
biological_sample

Detected Object:
experiment_controller

Result:
DEVIATION

Reason:
WRONG_OBJECT
```

---

## 6. UNCERTAIN Flow

When the system cannot make a sufficiently reliable decision:

```text
Observation
    ↓
Insufficient Confidence
    ↓
UNCERTAIN
    ↓
Request Verification
```

Example:

```text
Confidence:
Low

Result:
UNCERTAIN

Reason:
LOW_CONFIDENCE
```

The system avoids treating low-confidence perception as a confirmed protocol action.

---

## 7. Controlled Demonstration Flow

The controlled demonstration bypasses live perception and provides predefined scenarios.

```text
Scenario
   ↓
SimulationRunner
   ↓
Protocol Decision Core
   ↓
Decision Engine
   ↓
Result
```

Three scenarios are demonstrated:

```text
Expected Action
      ↓
   CORRECT

Wrong Object
      ↓
  DEVIATION

Low Confidence
      ↓
  UNCERTAIN
```

This makes the core decision system reproducible during presentations.

---

## 8. Protocol Configuration Flow

Protocol information is loaded from YAML configuration files.

```text
YAML Protocol Files
        ↓
   Protocol Loader
        ↓
Validated Configuration
        ↓
Mission State + Rules
        ↓
Decision Engine
```

The protocol configuration includes:

```text
experiment.yaml
activities.yaml
objects.yaml
steps.yaml
rules.yaml
```

---

## 9. Complete Example

A simplified live observation can be represented as:

```text
Camera Frame
     ↓
YOLO detects bottle
     ↓
Confidence = 0.82
     ↓
Object Mapping
     ↓
bottle → biological_sample
     ↓
Current Step = S002
     ↓
Activity = RETRIEVE_SAMPLE
     ↓
Expected Object = biological_sample
     ↓
Sequence Validation
     ↓
Valid
     ↓
Decision Engine
     ↓
CORRECT
     ↓
Guidance
```

---

## 10. Error Example

A wrong-object observation:

```text
Camera Frame
     ↓
YOLO detects cell phone
     ↓
Object Mapping
     ↓
cell phone → experiment_controller
     ↓
Current Step = S002
     ↓
Expected Object = biological_sample
     ↓
Object mismatch
     ↓
Deviation Detector
     ↓
WRONG_OBJECT
     ↓
Decision Engine
     ↓
DEVIATION
     ↓
"Wrong object detected.
 Expected biological_sample."
```

---

## 11. Data Flow Principles

ASTRA-GUARD follows these principles:

### Separation of Concerns

Perception is separated from protocol reasoning.

### Deterministic Validation

Protocol validation is performed using explicit state and rules.

### Structured Events

Perception information is converted into a common event representation.

### Confidence Awareness

Low-confidence observations can produce an `UNCERTAIN` result.

### Recoverable Decisions

Deviation results include guidance intended to help the operator return to the expected protocol.

---

## 12. Current Prototype Boundary

The current prototype does not perform full learned temporal action recognition.

The Activity Interpreter uses protocol state and perception signals.

Generic YOLO detections are mapped to protocol-level objects through deterministic configuration.

The Decision Engine is rule-based and does not use an LLM.

These boundaries are intentional and documented so that the prototype's current capabilities are clearly distinguished from future research extensions.
