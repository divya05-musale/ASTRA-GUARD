# ASTRA-GUARD Deployment Guide

## 1. Overview

This document describes how to deploy and run the ASTRA-GUARD prototype on a development or demonstration computer.

The current system is designed as a local prototype.

The primary deployment environment is a Windows computer running Python.

---

## 2. Current Deployment Model

The current deployment architecture is:

```text
Windows Computer
       ↓
Python Runtime
       ↓
ASTRA-GUARD Application
       ↓
YOLO + MediaPipe
       ↓
Webcam
       ↓
Protocol Validation
       ↓
Decision + Guidance
```

The core prototype runs locally.

The current decision engine does not require a cloud service or external LLM.

---

## 3. Deployment Requirements

Recommended requirements:

* Windows 10 or Windows 11
* Python 3.11
* Minimum 8 GB RAM
* Functional webcam for live demonstration
* Internet connection for initial dependency installation
* Sufficient disk space for Python packages and the YOLO model

A dedicated GPU is not required for the current prototype.

CPU-based execution is supported, although performance may vary depending on the computer.

---

## 4. Repository

Obtain the ASTRA-GUARD source repository and open the project directory.

The repository contains the application source code, protocol configuration, tests, documentation, and required model file.

Expected top-level structure:

```text id="w4x7hj"
ASTRA-GUARD/
├── agent/
├── backend/
├── data/
├── deployment/
├── docs/
├── experiments/
├── frontend/
├── models/
├── scripts/
├── simulation/
├── tests/
├── training/
├── video/
├── demo.py
├── run.py
├── run_live.py
├── requirements.txt
└── yolo11n.pt
```

---

## 5. Python Environment

Create a virtual environment from the project root:

```powershell id="r2w4t8"
python -m venv venv
```

Activate it:

```powershell id="9znx4v"
.\venv\Scripts\Activate.ps1
```

Upgrade pip:

```powershell id="j6e3ps"
python -m pip install --upgrade pip
```

---

## 6. Install Dependencies

Install all required Python packages:

```powershell id="3c4d5f"
python -m pip install -r requirements.txt
```

The main runtime dependencies include:

* OpenCV
* NumPy
* Ultralytics
* MediaPipe
* PyYAML
* PyTorch
* Torchvision
* pytest

---

## 7. Verify Installation

Check Python:

```powershell id="r7w6ha"
python --version
```

Recommended:

```text id="7rj0a1"
Python 3.11.x
```

Verify the main packages:

```powershell id="q3k8m2"
python -c "import cv2, numpy, yaml, torch, torchvision, ultralytics, mediapipe; print('ASTRA-GUARD dependencies OK')"
```

Expected:

```text id="6j9xk4"
ASTRA-GUARD dependencies OK
```

---

## 8. Verify the Protocol

The main demonstration protocol is located at:

```text id="x1n4z7"
experiments/EXP001_TARDIGRADE/
```

The directory contains:

```text id="m3q8w2"
activities.yaml
experiment.yaml
objects.yaml
rules.yaml
steps.yaml
```

The protocol is synthetic and intended for academic demonstration.

It is not an official ISRO flight procedure or proprietary operational protocol.

---

## 9. Verify the YOLO Model

The current object-detection model is:

```text id="p8k2s6"
yolo11n.pt
```

It should be available in the project root:

```text id="n5c7r1"
ASTRA-GUARD/
└── yolo11n.pt
```

The model is a pretrained generic object detector.

The current prototype does not use a custom astronaut-specific detection model.

---

## 10. Run Automated Tests

Before deployment, run the complete regression suite:

```powershell id="f3h7k9"
python -m pytest -q
```

Current focused test results and the known SAPI limitation are recorded in `docs/gap-analysis.md`. The historical 124-pass count is not a current full-suite result.

---

## 11. Run Controlled Demonstration

The controlled demonstration does not require a webcam.

Run:

```powershell id="a5r9v3"
python demo.py
```

Select:

```text id="u7m4c2"
2. Controlled Protocol Demo
```

The controlled demo demonstrates:

```text id="z6h8n1"
CORRECT
DEVIATION
UNCERTAIN
```

This is the recommended mode for presentations where reproducible output is required.

---

## 12. Run Live Demonstration

To launch FastAPI, Vite, and the webcam pipeline together, run from the project root with the project virtual environment active:

```powershell
python scripts/start_all.py --live
```

Dashboard: `http://localhost:5173`. API: `http://localhost:8001`. Stop the managed services with `Ctrl+C`.

To run only the standalone webcam window:

For live webcam deployment:

```powershell id="b8v2x5"
python run_live.py
```

The runtime uses:

```text id="c4m7s9"
Webcam
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

Press `Q` inside the webcam window to stop.

---

## 13. Main Application Launcher

The recommended application entry point is:

```powershell id="e2f6j8"
python run.py
```

The launcher provides:

```text id="k3n7p5"
1. Live Webcam Demo
2. Controlled Protocol Demo
3. Exit
```

For a presentation, the controlled mode can be used first to demonstrate the complete decision pipeline, followed by the live webcam mode.

---

## 14. Camera Configuration

The current live runtime uses camera index:

```text id="s9d3h7"
0
```

The webcam resolution is configured for:

```text id="q4w8m1"
1280 × 720
```

If the default camera cannot be opened, verify:

* The webcam is connected.
* Windows camera permissions are enabled.
* Another application is not using the camera.
* The correct camera index is selected.

---

## 15. Local Deployment Architecture

The current prototype can operate entirely on the local computer:

```text id="h7k2m4"
                    LOCAL COMPUTER
┌──────────────────────────────────────────────┐
│                                              │
│  Webcam                                      │
│    ↓                                         │
│  YOLO + MediaPipe                            │
│    ↓                                         │
│  Perception Processing                       │
│    ↓                                         │
│  Protocol Integration                        │
│    ↓                                         │
│  Mission State Machine                       │
│    ↓                                         │
│  Decision Engine                             │
│    ↓                                         │
│  Guidance / Overlay                          │
│                                              │
└──────────────────────────────────────────────┘
```

No cloud inference service is required for the core decision path.

---

## 16. Offline Capability

After the required Python packages and model files have been installed locally, the core prototype can operate without an external LLM or cloud decision service.

The current design therefore supports local processing for the main perception and protocol-validation workflow.

Network access may still be required for:

* Initial package installation
* Repository cloning
* Dependency updates
* Model acquisition if the model is not already present

---

## 17. Performance Considerations

The current prototype is intended for demonstration and research rather than production deployment.

Performance depends on:

* CPU performance
* Available RAM
* Camera resolution
* YOLO inference speed
* Number of processed frames
* Operating-system load

For resource-constrained systems, future optimization may include:

* Smaller perception models
* Frame skipping
* Resolution reduction
* Model quantization
* Hardware acceleration
* Edge-device optimization

---

## 18. Resource Usage

The application may consume significant CPU and memory during live inference because computer vision models process camera frames continuously.

If the computer becomes slow:

1. Close unnecessary applications.
2. Reduce camera resolution if required.
3. Stop background processes.
4. Run the controlled demonstration instead of live inference when a webcam is not required.
5. Consider a smaller or optimized model for future deployments.

---

## 19. Deployment Verification Checklist

Before a demonstration:

```text id="j4n8s2"
[ ] Python environment activated
[ ] Dependencies installed
[ ] YOLO model present
[ ] Protocol files present
[ ] Automated tests pass
[ ] Controlled demo works
[ ] Webcam available
[ ] Live demo tested
[ ] Q key successfully stops webcam runtime
[ ] Git working tree reviewed
```

---

## 20. Demonstration Procedure

Recommended presentation sequence:

### Step 1 — Start Application

```powershell id="p6s3v9"
python run.py
```

### Step 2 — Run Controlled Demo

Select:

```text id="y8k2d5"
2
```

Demonstrate:

```text
CORRECT
DEVIATION
UNCERTAIN
```

### Step 3 — Run Live Demo

Return to the launcher and select:

```text id="t5m9c1"
1
```

Show the live perception overlay.

### Step 4 — Demonstrate Deviation

Use a detectable object that does not match the current protocol expectation.

The system should show a deviation such as:

```text id="a3r7n2"
Status: DEVIATION
Deviation: WRONG_OBJECT
```

### Step 5 — Stop Runtime

Press:

```text id="q"
```

inside the webcam window.

---

## 21. Deployment Troubleshooting

### Application does not start

Check:

```powershell id="m8v4c6"
python --version
```

Then verify dependencies:

```powershell id="g2x7n5"
python -c "import cv2, numpy, yaml, torch, torchvision, ultralytics, mediapipe; print('OK')"
```

---

### Protocol cannot be loaded

Verify that:

```text id="v9c3k7"
experiments/EXP001_TARDIGRADE/
```

exists and contains all required YAML files.

---

### YOLO model cannot be loaded

Verify:

```text id="d5h8m2"
yolo11n.pt
```

exists in the project root.

---

### Webcam cannot be opened

Check Windows camera permissions and verify that another application is not using the camera.

The current default camera index is `0`.

---

### Live demo is slow

Possible causes include high CPU usage or insufficient system resources.

Try:

* Closing unnecessary applications.
* Lowering camera resolution.
* Using controlled mode for presentations.
* Optimizing the perception model in future development.

---

### Automated tests fail

Run:

```powershell id="k7p2r4"
python -m pytest -vv
```

Identify the failing test before making deployment changes.

---

## 22. Security and Privacy Considerations

The current prototype is designed for local academic demonstration.

The webcam processing pipeline operates locally and does not require sending camera frames to an external LLM for protocol decisions.

Future production deployments would require additional security controls for:

* Camera data
* Mission telemetry
* Authentication
* Access control
* Data retention
* Audit logging
* Secure communications
* Model integrity

These controls are outside the scope of the current prototype.

---

## 23. Production Deployment Boundary

ASTRA-GUARD is currently a prototype.

It should not be deployed as an actual spacecraft operational or safety-critical system without substantial additional validation.

A production-grade system would require, among other things:

* Domain-specific datasets
* Specialized perception models
* Extensive hardware testing
* Fault-tolerance mechanisms
* Real-
