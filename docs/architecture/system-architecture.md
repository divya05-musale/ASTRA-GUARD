# ASTRA-GUARD System Architecture

## 1. Overview

ASTRA-GUARD is a prototype system for monitoring experimental activities and validating them against a predefined mission protocol.

The system combines computer vision, hand tracking, protocol-aware perception, mission state management, deterministic validation, deviation detection, and real-time guidance.

The prototype is designed for controlled experimental monitoring and demonstration.

---

## 2. High-Level Architecture

```text
                         ASTRA-GUARD
                              |
                              v
                     +------------------+
                     |   Webcam Input   |
                     +------------------+
                              |
                              v
                     +------------------+
                     | Perception Layer |
                     +------------------+
                         /          \
                        v            v
               +-------------+  +-------------+
               | YOLO Object |  |  MediaPipe  |
               | Detection   |  | Hand Track  |
               +-------------+  +-------------+
                        \            /
                         \          /
                          v        v
                     +------------------+
                     | Perception Event |
                     +------------------+
                              |
                              v
                 +-------------------------+
                 | Protocol-Aware Mapping  |
                 +-------------------------+
                              |
                              v
                 +-------------------------+
                 | Activity Interpreter    |
                 +-------------------------+
                              |
                              v
                 +-------------------------+
                 | Mission State Machine   |
                 +-------------------------+
                              |
                              v
                 +-------------------------+
                 | Sequence Validator      |
                 +-------------------------+
                              |
                              v
                 +-------------------------+
                 | Deviation Detector      |
                 +-------------------------+
                              |
                              v
                 +-------------------------+
                 | Decision Engine         |
                 +-------------------------+
                              |
                 +------------+------------+
                 |            |            |
                 v            v            v
              CORRECT     DEVIATION    UNCERTAIN
                 |            |            |
                 +------------+------------+
                              |
                              v
                     +------------------+
                     | Guidance / UI    |
                     +------------------+
```

---

## 3. Main Components

### 3.1 Webcam Runtime

The webcam runtime captures live frames from the camera.

Responsibilities:

* Initialize the camera.
* Capture video frames.
* Provide frames to the perception pipeline.
* Display the live monitoring interface.
* Handle user exit through the `Q` key.

---

### 3.2 Object Detection

ASTRA-GUARD uses Ultralytics YOLO for generic object detection.

The detector identifies objects visible in the camera frame and provides:

* Object class
* Confidence score
* Bounding box

The current prototype uses a generic YOLO model rather than a custom astronaut-specific model.

---

### 3.3 Hand Tracking

MediaPipe is used to track hand landmarks.

Hand tracking provides additional perception information that can be used together with object detection and protocol context.

The current prototype does not claim full human-action recognition from hand tracking alone.

---

### 3.4 Perception Event

Raw perception results are converted into a structured perception event.

Conceptually:

```text
Object Detection
       +
Hand Tracking
       +
Protocol Context
       |
       v
PerceptionEvent
```

A perception event contains information such as:

```text
activity
object
confidence
```

This creates a common interface between the perception layer and the mission decision layer.

---

### 3.5 Protocol-Aware Mapping

Generic detected objects are mapped to protocol-level objects.

For example:

```text
YOLO: bottle
        |
        v
Protocol object:
biological_sample
```

Another example:

```text
YOLO: cell phone
        |
        v
Protocol object:
experiment_controller
```

This mapping allows a generic perception model to interact with the synthetic experimental protocol.

---

### 3.6 Activity Interpreter

The Activity Interpreter converts perception and mission context into a protocol-level activity.

The current implementation is deterministic and protocol-aware.

It uses mission state and configured step information rather than a trained action-recognition model.

Example:

```text
S001 → CHECK_EQUIPMENT
S002 → RETRIEVE_SAMPLE
S003 → OPEN_CONTAINER
S004 → TRANSFER_SAMPLE
```

---

### 3.7 Mission State Machine

The state machine tracks the current protocol step.

For the demonstration protocol:

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

The state machine prevents the system from treating an action as correct when it occurs in the wrong mission context.

---

### 3.8 Sequence Validator

The Sequence Validator checks whether the detected activity occurs in the expected protocol order.

It helps identify situations such as:

* Correct step
* Wrong sequence
* Skipped step
* Premature action
* Unexpected action

---

### 3.9 Deviation Detector

The Deviation Detector analyzes protocol violations.

Examples include:

```text
WRONG_OBJECT
WRONG_SEQUENCE
SKIPPED_STEP
UNKNOWN_ACTION
LOW_CONFIDENCE
```

The detector provides structured deviation information to the Decision Engine.

---

### 3.10 Decision Engine

The Decision Engine is the main reasoning layer of the prototype.

It combines:

* Current mission state
* Expected activity
* Expected object
* Perception event
* Confidence
* Sequence validation
* Deviation information

The engine produces one of the main outcomes:

```text
CORRECT
DEVIATION
UNCERTAIN
```

The current Decision Engine is deterministic and rule-based. It does not use an LLM.

---

### 3.11 Guidance System

After the decision is generated, the system provides guidance to the operator.

Examples:

```text
CORRECT:
Equipment check completed.
Proceed to retrieve the sample.
```

```text
DEVIATION:
Wrong object detected.
Please select the biological sample.
```

```text
UNCERTAIN:
Detection confidence is low.
Please repeat or hold the action for verification.
```

---

## 4. Protocol Layer

The mission protocol is stored as structured YAML configuration.

The main protocol contains:

```text
activities.yaml
experiment.yaml
objects.yaml
rules.yaml
steps.yaml
```

The protocol loader validates and loads this configuration before execution.

The demonstration protocol is:

```text
EXP001 - TARDIGRADE
```

It is a synthetic academic protocol based on a public research theme and is not an official operational spaceflight procedure.

---

## 5. End-to-End Processing

The complete live processing flow is:

```text
Camera Frame
     ↓
YOLO Detection
     ↓
MediaPipe Hand Tracking
     ↓
Perception Event
     ↓
Object Mapping
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
Decision
     ↓
Guidance
```

---

## 6. Decision Outcomes

### CORRECT

The observed event satisfies the expected protocol condition.

### DEVIATION

The observed event conflicts with the expected protocol condition.

Examples:

* Wrong object
* Wrong sequence
* Skipped step
* Unexpected action

### UNCERTAIN

The available perception information is insufficient for a reliable decision.

The system requests verification rather than making an unsafe assumption.

---

## 7. Controlled Demonstration Mode

ASTRA-GUARD also includes a controlled demonstration mode.

It demonstrates the three major decision outcomes without depending on live camera conditions:

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

This provides a repeatable way to demonstrate the protocol decision system.

---

## 8. Current Prototype Boundaries

The current prototype has several intentional boundaries:

* YOLO is a generic object detection model.
* Specialized protocol objects are represented through deterministic mapping.
* The Activity Interpreter is protocol-state based.
* No custom astronaut-specific action recognition model is currently used.
* The Decision Engine is rule-based.
* The current prototype does not use an LLM for decision making.
* The demonstration protocol is synthetic.

These boundaries are explicitly documented to distinguish the current prototype from future production-level capabilities.

---

## 9. Future Architecture Extensions

Future versions could add:

* Domain-specific object detection
* Astronaut pose estimation
* Temporal action recognition
* Multimodal perception
* Voice guidance
* Mission telemetry integration
* Edge-device optimization
* Additional experimental protocols
* Onboard offline deployment
* Hardware-integrated sensing

---

## 10. Summary

ASTRA-GUARD separates perception from protocol reasoning.

The perception layer observes the environment, while the protocol and decision layers determine whether the observed event is compatible with the expected mission procedure.

This separation makes the prototype modular and allows future perception models to be integrated without redesigning the complete protocol validation system.
