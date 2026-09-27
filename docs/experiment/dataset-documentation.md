# Dataset Documentation

## 1. Overview

ASTRA-GUARD uses a controlled synthetic protocol configuration rather than a large supervised training dataset for its core decision system.

The current prototype is designed to validate experimental activities against predefined mission steps, expected activities, expected objects, and deterministic safety rules.

The main demonstration protocol is:

**EXP001 - TARDIGRADE**

Domain: Biological Science
Environment: Microgravity
Protocol Type: Synthetic

The protocol is intended for academic research, demonstration, and system validation.

---

## 2. Dataset / Configuration Sources

The prototype uses structured YAML configuration files located under:

```text
experiments/EXP001_TARDIGRADE/
```

The main configuration files are:

```text
experiments/
└── EXP001_TARDIGRADE/
    ├── activities.yaml
    ├── experiment.yaml
    ├── objects.yaml
    ├── rules.yaml
    └── steps.yaml
```

These files collectively define the experimental protocol used by the system.

---

## 3. Experiment Configuration

The `experiment.yaml` file contains the high-level experiment metadata.

It defines information such as:

* Experiment identifier
* Experiment name
* Scientific domain
* Operating environment
* Protocol version
* Protocol status
* Protocol type
* Reference type
* Orientation-agnostic property
* Experiment description

The protocol is explicitly marked as synthetic.

It is not an official ISRO flight procedure and does not contain proprietary operational information.

---

## 4. Activities

The `activities.yaml` configuration defines the activities recognized by the protocol.

The current protocol contains eight activities:

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

These activities represent the logical actions expected during the experimental workflow.

---

## 5. Protocol Objects

The `objects.yaml` configuration defines the protocol-level objects.

The current protocol contains five objects:

```text
experiment_container
biological_sample
sample_chamber
experiment_controller
observation_interface
```

These names represent logical protocol objects used by the decision layer.

They should not be interpreted as evidence that the current generic vision model directly detects every specialized protocol object.

---

## 6. Protocol Steps

The `steps.yaml` configuration defines the expected sequence of activities and objects.

The current eight-step sequence is:

| Step | Expected Activity   | Expected Object       |
| ---- | ------------------- | --------------------- |
| S001 | CHECK_EQUIPMENT     | experiment_container  |
| S002 | RETRIEVE_SAMPLE     | biological_sample     |
| S003 | OPEN_CONTAINER      | sample_chamber        |
| S004 | TRANSFER_SAMPLE     | sample_chamber        |
| S005 | START_EXPERIMENT    | experiment_controller |
| S006 | RECORD_RESULT       | observation_interface |
| S007 | SECURE_SAMPLE       | sample_chamber        |
| S008 | COMPLETE_EXPERIMENT | experiment_controller |

The state machine uses this sequence to determine whether a detected perception event is valid for the current mission state.

---

## 7. Decision Rules

The `rules.yaml` file contains deterministic protocol validation rules.

The current protocol contains 14 configured rules.

Rules are used for conditions such as:

* Wrong object
* Wrong sequence
* Skipped step
* Unknown action
* Low confidence
* Premature action
* Invalid protocol state
* Recovery guidance

The decision engine evaluates the current state and incoming perception event before producing a decision.

---

## 8. Vision Perception Data

ASTRA-GUARD uses a live webcam as the perception source during the real-time demonstration.

The perception layer currently combines:

```text
Webcam Frame
     ↓
YOLO Object Detection
     ↓
MediaPipe Hand Tracking
     ↓
Perception Event
```

The perception event contains information such as:

* Detected object
* Object confidence
* Hand tracking information
* Frame-related perception information
* Protocol-mapped object identity

The perception layer then passes the interpreted information to the protocol validation system.

---

## 9. Generic Object Detection

The current prototype uses the pretrained `yolo11n.pt` model.

It provides generic object detections that can be mapped to protocol-level objects.

Examples include:

```text
bottle       → biological_sample
cup          → sample_chamber
bowl         → sample_chamber
cell phone   → experiment_controller
remote       → experiment_controller
```

The mapping is implemented deterministically in the perception layer.

This approach allows the prototype to demonstrate protocol validation without claiming that a custom astronaut-specific object detection model has been trained.

---

## 10. Hand Tracking

MediaPipe is used for hand tracking during live perception.

Hand tracking provides additional perception information that can be used together with object detection.

The current prototype uses this information as part of the perception pipeline rather than as a standalone trained action-recognition system.

---

## 11. Synthetic Demonstration Data

ASTRA-GUARD also includes controlled synthetic perception scenarios for deterministic testing.

These scenarios are used to verify:

```text
CORRECT
DEVIATION
UNCERTAIN
```

Example:

```text
Expected Object:
experiment_container

Detected Object:
experiment_container

Result:
CORRECT
```

Another scenario can intentionally provide an incorrect object:

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

A low-confidence scenario can produce:

```text
Result:
UNCERTAIN
Reason:
LOW_CONFIDENCE
```

These controlled scenarios make the decision engine reproducible during testing and presentations.

---

## 12. No Large Training Dataset in Current Prototype

The current ASTRA-GUARD prototype does not train a custom computer-vision model on an astronaut-specific dataset.

Instead, it combines:

```text
Pretrained Generic Object Detection
              +
MediaPipe Hand Tracking
              +
Protocol Configuration
              +
Deterministic Mapping
              +
Rule-Based Decision Engine
```

This architecture allows the system to demonstrate the complete protocol-validation pipeline while keeping the prototype lightweight and reproducible.

---

## 13. Data Flow

The configuration and perception data move through the system as follows:

```text
Synthetic Protocol
        ↓
Protocol Loader
        ↓
Mission State
        ↓
Webcam Perception
        ↓
YOLO + MediaPipe
        ↓
Perception Event
        ↓
Protocol-Aware Mapping
        ↓
Decision Engine
        ↓
CORRECT / DEVIATION / UNCERTAIN
        ↓
Guidance
```

---

## 14. Data Validation

The protocol configuration is validated when loaded by the protocol loader.

The loader verifies the required protocol components, including:

* Experiment metadata
* Activities
* Objects
* Steps
* Rules

The current protocol was successfully validated with:

```text
5 protocol objects
8 activities
14 rules
8 mission steps
```

---

## 15. Reproducibility

The protocol configuration files are stored directly in the repository.

This allows another developer to reproduce the same protocol-validation environment without requiring access to private mission data.

The controlled simulation scenarios also make it possible to reproduce the main decision outcomes without requiring a webcam.

---

## 16. Privacy and Data Handling

The current demonstration uses local webcam processing.

The prototype does not require uploading webcam frames to a remote service for its core decision process.

The current decision engine does not use an external LLM for protocol validation or decision making.

Future versions may introduce additional telemetry, datasets, or specialized models depending on the deployment requirements.

---

## 17. Dataset Limitations

The current data/configuration approach has several limitations:

* The protocol is synthetic.
* The generic YOLO model is not specialized for astronaut operations.
* Specialized protocol objects may require domain-specific training.
* The current activity interpreter is deterministic rather than a trained action-recognition model.
* Controlled simulation data does not represent the full variability of real microgravity environments.
* The current prototype does not use real mission operational data.

These limitations are intentionally documented to distinguish the current academic prototype from a production-grade onboard mission system.

---

## 18. Future Dataset Development

Future development could include:

* Domain-specific astronaut activity datasets
* Space-lab object datasets
* Hand-object interaction datasets
* Temporal action-recognition datasets
* Microgravity video datasets
* Synthetic orientation-variation datasets
* Annotated protocol-deviation datasets
* Edge-device benchmark datasets

A future training pipeline could then support specialized object detection and temporal activity recognition.

---

## 19. Summary

ASTRA-GUARD currently uses a synthetic protocol configuration, pretrained generic computer vision, MediaPipe hand tracking, controlled simulation scenarios, and deterministic protocol rules.

The configuration-driven design separates:

```text
Perception
    ↓
Protocol Interpretation
    ↓
Mission Validation
    ↓
Decision
    ↓
Guidance
```

This separation makes the prototype testable, reproducible, and extensible toward future domain-specific datasets and models.
