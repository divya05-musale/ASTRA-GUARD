# ASTRA-GUARD Development Setup

## 1. Overview

This document explains how to set up the ASTRA-GUARD development environment on a Windows system.

The project is implemented primarily in Python and uses computer-vision, machine-learning, configuration, and testing libraries.

---

## 2. System Requirements

Recommended environment:

* Windows 10 or Windows 11
* Python 3.11
* Git
* Visual Studio Code
* Functional webcam
* Internet connection for initial dependency installation

The prototype can run on a standard development laptop without requiring a dedicated GPU.

---

## 3. Clone the Repository

Clone the project repository:

```powershell
git clone <repository-url>
cd ASTRA-GUARD
```

If the repository has already been cloned, open the project directory directly in VS Code.

---

## 4. Create a Virtual Environment

Create a Python virtual environment:

```powershell
python -m venv venv
```

Activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

After activation, the terminal should show:

```text
(venv)
```

before the current directory.

If PowerShell prevents activation because of execution policy, the following command can be used for the current user:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate the environment again.

---

## 5. Upgrade pip

Upgrade the Python package installer:

```powershell
python -m pip install --upgrade pip
```

---

## 6. Install Dependencies

Install the project dependencies:

```powershell
python -m pip install -r requirements.txt
```

The main dependencies include:

* OpenCV
* NumPy
* Ultralytics YOLO
* MediaPipe
* PyYAML
* PyTorch
* Torchvision
* pytest

---

## 7. Verify Python Environment

Check the Python version:

```powershell
python --version
```

The recommended version is:

```text
Python 3.11.x
```

Verify that Python is using the virtual environment:

```powershell
where python
```

The first Python path should point to the project's:

```text
ASTRA-GUARD\venv\Scripts\python.exe
```

---

## 8. Verify Core Packages

The following command can be used to verify the major packages:

```powershell
python -c "import cv2, numpy, yaml, pytest, torch, torchvision, ultralytics, mediapipe; print('Core packages imported successfully')"
```

Expected result:

```text
Core packages imported successfully
```

---

## 9. Verify Project Compilation

Before running the complete application, compile the main Python entry points:

```powershell
python -m py_compile run.py demo.py run_live.py
```

No output indicates that the files compiled successfully.

---

## 10. Run Automated Tests

Run the configured maintained test suite:

```powershell
python -m pytest tests -q
```

See `docs/gap-analysis.md` for current focused test results and the known Windows SAPI test limitation. Do not treat the historical 124-pass count as a current complete-suite result.

---

## 11. Run the Controlled Demo

The controlled demo does not require a webcam.

Run:

```powershell
python demo.py
```

Select:

```text
2. Controlled Protocol Demo
```

The demonstration validates three important outcomes:

```text
CORRECT
DEVIATION
UNCERTAIN
```

This mode is recommended for presentations because its scenarios are deterministic.

---

## 12. Run the Live Webcam Demo

Connect a webcam and run:

```powershell
python run_live.py
```

The system initializes:

```text
Webcam
   ↓
YOLO Object Detection
   ↓
MediaPipe Hand Tracking
   ↓
Perception Processing
   ↓
Protocol Mapping
   ↓
Decision Engine
   ↓
Live Overlay
```

Press:

```text
Q
```

inside the webcam window to stop the application.

---

## 13. Run the Full Local Dashboard

From the project root with the project virtual environment active:

```powershell
python scripts/start_all.py --live
```

The dashboard is at `http://localhost:5173`; the API is at `http://localhost:8001`. `Ctrl+C` in the launcher terminal stops the services.

Use the Experiments view for protocol selection and webcam/local-video session start. Use Memory for saved-session review, local video playback, and JSON/CSV export.

## 14. Run the Main Launcher

The complete demonstration launcher can be started with:

```powershell
python run.py
```

The launcher provides:

```text
1. Live Webcam Demo
2. Controlled Protocol Demo
3. Exit
```

This is the recommended entry point for demonstrations.

---

## 14. YOLO Model

The current repository includes:

```text
yolo11n.pt
```

This is the pretrained YOLO model used by the object-detection layer.

The prototype uses generic object detection and maps detected generic objects to protocol-level objects through deterministic mapping.

It is not a custom astronaut-specific model.

---

## 15. Protocol Configuration

The main synthetic experiment is located at:

```text
experiments/EXP001_TARDIGRADE/
```

Important files:

```text
activities.yaml
experiment.yaml
objects.yaml
rules.yaml
steps.yaml
```

These files define the experiment metadata, activities, objects, validation rules, and mission sequence.

---

## 16. Project Structure

The main project structure is:

```text
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

## 17. Development Workflow

A typical development workflow is:

```text
1. Activate virtual environment
        ↓
2. Modify source/configuration
        ↓
3. Run targeted tests
        ↓
4. Run complete test suite
        ↓
5. Run controlled demo
        ↓
6. Run live webcam demo when required
        ↓
7. Review Git changes
        ↓
8. Commit changes
```

Recommended commands:

```powershell
.\venv\Scripts\Activate.ps1
python -m pytest -q
python demo.py
git status
```

---

## 18. Testing Before Commit

Before committing code changes, run:

```powershell
python -m pytest -q
```

For the current implementation, the expected regression baseline is:

```text
124 passed
```

If tests fail after a change, investigate the failure before committing.

---

## 19. Git Development Workflow

Check the current repository state:

```powershell
git status
```

Review changes:

```powershell
git diff
```

Stage changes:

```powershell
git add .
```

Create a commit:

```powershell
git commit -m "Describe the change"
```

Push the current branch:

```powershell
git push
```

The project currently uses the `master` branch.

---

## 20. Troubleshooting

### Python command not found

Verify Python installation:

```powershell
python --version
```

If Python is unavailable, install Python 3.11 and ensure it is available from the command line.

---

### Virtual environment is not active

Run:

```powershell
.\venv\Scripts\Activate.ps1
```

Then verify:

```powershell
where python
```

---

### Dependencies are missing

Run:

```powershell
python -m pip install -r requirements.txt
```

---

### Webcam does not open

Check that:

* The webcam is connected.
* Another application is not using the webcam.
* Windows camera permissions allow desktop applications to access the camera.
* The correct camera index is configured.

The default runtime uses camera index:

```text
0
```

---

### YOLO model is not found

Verify that:

```text
yolo11n.pt
```

exists in the project root.

Expected location:

```text
ASTRA-GUARD/
└── yolo11n.pt
```

---

### Tests fail after a code change

Run the failing test with more detail:

```powershell
python -m pytest -vv
```

Then run the complete suite again after fixing the issue:

```powershell
python -m pytest -q
```

---

## 21. Development Notes

The current prototype is intentionally deterministic at the protocol-validation layer.

The system does not use an external LLM for its core protocol decision process.

The activity interpreter is protocol-state based rather than a trained human-action recognition model.

Generic YOLO detections are mapped to protocol-level objects using deterministic rules.

These boundaries should be maintained in project documentation and presentations to accurately describe the current implementation.

---

## 22. Reproducibility

A fresh development environment should be able to reproduce the core prototype using:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python run.py
```

The controlled demonstration provide
