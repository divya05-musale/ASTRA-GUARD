# ASTRA-GUARD Demo Guide

## 1. Purpose

This document explains how to demonstrate ASTRA-GUARD during a presentation, evaluation, or project review.

The demonstration shows how ASTRA-GUARD combines computer vision, protocol configuration, mission state management, deviation detection, and deterministic decision logic.

---

## 2. Recommended Demo Flow

The recommended demonstration sequence is:

```text
Project Introduction
        ↓
Protocol Explanation
        ↓
Controlled Demo
        ↓
CORRECT
        ↓
DEVIATION
        ↓
UNCERTAIN
        ↓
Live Webcam Demo
        ↓
Real-Time Decision Overlay
```

The controlled demo should be used first because it provides deterministic and reproducible results.

---

## 3. Start the Application

From the project root:

```powershell
python run.py
```

The launcher displays:

```text
1. Live Webcam Demo
2. Controlled Protocol Demo
3. Exit
```

---

## 4. Controlled Protocol Demo

Select:

```text
2
```

The controlled demonstration runs predefined scenarios.

It demonstrates three important decision outcomes:

```text
CORRECT
DEVIATION
UNCERTAIN
```

---

## 5. Scenario 1 — CORRECT

The first scenario represents a valid protocol action.

Conceptually:

```text
Expected:
CHECK_EQUIPMENT

Expected Object:
experiment_container

Observed:
Valid protocol action
```

Expected result:

```text
Status: CORRECT
```

The decision engine accepts the observation and allows the protocol to continue.

---

## 6. Scenario 2 — DEVIATION

The second scenario intentionally provides an incorrect object.

Conceptually:

```text
Expected:
biological_sample

Detected:
experiment_controller
```

Expected result:

```text
Status: DEVIATION
Deviation: WRONG_OBJECT
```

The system also provides recovery guidance.

Example:

```text
Wrong object detected.
Please select the biological sample.
```

The mission state is not automatically advanced because the expected protocol condition was not satisfied.

---

## 7. Scenario 3 — UNCERTAIN

The third scenario represents insufficient perception confidence.

Conceptually:

```text
Detection Confidence:
Low
```

Expected result:

```text
Status: UNCERTAIN
Deviation: LOW_CONFIDENCE
```

The system requests verification instead of accepting the observation as a valid protocol action.

---

## 8. Decision Summary

The controlled demo demonstrates:

```text
CORRECT
   ↓
Protocol action accepted

DEVIATION
   ↓
Protocol violation detected

UNCERTAIN
   ↓
Verification required
```

This demonstrates the three main decision outcomes of the prototype.

---

## 9. Live Webcam Demo

After completing the controlled demo, return to the launcher and select:

```text
1
```

The live runtime starts the webcam pipeline.

The live processing flow is:

```text
Webcam Frame
      ↓
YOLO Object Detection
      ↓
MediaPipe Hand Tracking
      ↓
Perception Event
      ↓
Protocol-Aware Mapping
      ↓
Decision Engine
      ↓
Live Overlay
```

---

## 10. Live Overlay

The webcam window displays information such as:

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

The exact confidence value and detected object may vary between frames and environments.

---

## 11. Demonstrating a Live Deviation

The current generic YOLO model can detect common objects such as:

```text
bottle
cup
bowl
cell phone
remote
```

These are mapped to protocol-level objects using deterministic rules.

For example:

```text
cell phone
     ↓
experiment_controller
```

If the mapped object does not match the protocol's expected object, the system can produce:

```text
DEVIATION
WRONG_OBJECT
```

This is a practical way to demonstrate the live decision layer.

---

## 12. Important Live Demo Limitation

The current YOLO model is a generic pretrained object detector.

The protocol contains specialized logical objects such as:

```text
experiment_container
biological_sample
sample_chamber
experiment_controller
observation_interface
```

These are protocol-level object names.

The current prototype does not use a custom astronaut-specific object detection model trained to directly recognize all five specialized objects.

Therefore, the live demo should be presented as:

```text
Generic Object Detection
        ↓
Deterministic Protocol Mapping
        ↓
Protocol Validation
```

rather than as a fully trained space-object recognition system.

---

## 13. Activity Interpretation Limitation

The current activity interpreter is deterministic and protocol-state based.

It should not be described as a trained human-action recognition model.

The prototype currently uses the mission step and perception information to associate the current state with its expected activity.

Future versions can introduce temporal action-recognition models for more advanced activity understanding.

---

## 14. Decision Engine

The core decision engine is deterministic and rule-based.

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

Possible results include:

```text
CORRECT
DEVIATION
UNCERTAIN
COMPLETED
```

The system can also generate deviation reasons and recovery guidance.

---

## 15. Protocol Used in Demo

The main demonstration protocol is:

```text
EXP001 - TARDIGRADE
```

Domain:

```text
Biological Science
```

Environment:

```text
Microgravity
```

Protocol type:

```text
Synthetic
```

The protocol contains eight steps:

```text
S001 CHECK_EQUIPMENT
S002 RETRIEVE_SAMPLE
S003 OPEN_CONTAINER
S004 TRANSFER_SAMPLE
S005 START_EXPERIMENT
S006 RECORD_RESULT
S007 SECURE_SAMPLE
S008 COMPLETE_EXPERIMENT
```

The protocol is synthetic and is not an official ISRO flight procedure or proprietary operational protocol.

---

## 16. Presentation Script

A simple explanation for a project presentation is:

> ASTRA-GUARD monitors experimental activities and compares them with a predefined mission protocol. It uses computer vision to observe the environment, converts perception into protocol-level events, and uses deterministic validation rules to determine whether the current action is correct, a deviation, or uncertain.

Then demonstrate:

```text
CORRECT
```

Explain:

> The observed condition matches the expected protocol step.

Then demonstrate:

```text
DEVIATION
```

Explain:

> The detected condition does not match the expected protocol requirement, so the system identifies the deviation and provides guidance.

Then demonstrate:

```text
UNCERTAIN
```

Explain:

> The system does not have enough confidence to make a reliable decision, so it requests verification instead of making an unsafe assumption.

---

## 17. Recommended Demo Order for SIH

For a short presentation:

### Part 1 — Problem

Explain that experimental procedures contain ordered steps and that deviations can occur during execution.

### Part 2 — Solution

Show:

```text
Webcam
  ↓
Perception
  ↓
Protocol Validation
  ↓
Decision
  ↓
Guidance
```

### Part 3 — Controlled Demo

Show:

```text
CORRECT
DEVIATION
UNCERTAIN
```

### Part 4 — Live Demo

Show the real webcam perception and live decision overlay.

### Part 5 — Architecture

Briefly explain:

```text
Perception
   ↓
Protocol Integration
   ↓
State Machine
   ↓
Decision Engine
```

---

## 18. Demo Commands

### Main launcher

```powershell
python run.py
```

### Controlled demo

```powershell
python demo.py
```

### Live webcam demo

```powershell
python run_live.py
```

### Automated tests

```powershell
python -m pytest -q
```

Current regression baseline:

```text
124 passed
```

---

## 19. Stopping the Live Demo

To stop the live webcam runtime:

```text
Press Q
```

The key must be pressed while the webcam window has focus.

---

## 20. Demo Preparation Checklist

Before a presentation:

```text
[ ] Repository opens successfully
[ ] Virtual environment works
[ ] Dependencies installed
[ ] YOLO model present
[ ] Protocol files present
[ ] Tests pass
[ ] Controlled demo verified
[ ] Webcam connected
[ ] Camera permissions enabled
[ ] Live demo tested
[ ] Presentation screenshots prepared
[ ] Backup controlled demo available
```

---

## 21. Backup Demo Strategy

If the webcam is unavailable during a presentation, use the controlled demo.

Run:

```powershell
python demo.py
```

Select:

```text
2
```

This allows the decision engine and protocol validation pipeline to be demo

