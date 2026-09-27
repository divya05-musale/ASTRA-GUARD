# ASTRA-GUARD

### AI-Powered Onboard Monitoring and Protocol Validation System

ASTRA-GUARD is a prototype system for monitoring experimental activities and validating them against a predefined mission protocol.

It combines computer vision, hand tracking, protocol-aware perception, deterministic decision logic, and real-time guidance.

## Key Capabilities

* Real-time webcam perception
* YOLO object detection
* MediaPipe hand tracking
* Protocol-aware object mapping
* Mission state machine
* Sequence validation
* Deviation detection
* Confidence-based uncertainty handling
* Recovery guidance
* Live decision overlay
* Local experiment selection and durable session records
* Protocol-authorized manual confirmation for uncertain actions
* Sequential processing of local video files
* Local evidence playback and JSON/CSV session exports
* Live pipeline and dashboard performance telemetry
* Controlled demonstration mode
* Automated testing

## System Flow

```text
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
CORRECT / DEVIATION / UNCERTAIN
   ↓
Guidance
```

## Demonstration Protocol

The main prototype uses:

**EXP001 - TARDIGRADE**

Domain: Biological Science
Environment: Microgravity
Protocol Type: Synthetic

The protocol contains eight steps:

```text
S001  CHECK_EQUIPMENT
S002  RETRIEVE_SAMPLE
S003  OPEN_CONTAINER
S004  TRANSFER_SAMPLE
S005  START_EXPERIMENT
S006  RECORD_RESULT
S007  SECURE_SAMPLE
S008  COMPLETE_EXPERIMENT
```

The protocol is synthetic and is not an official ISRO flight procedure or proprietary operational protocol.

## Additional Experiments

* `EXP006` Payload Transfer: eight ordered steps. Red/yellow boxes are segmented locally from HSV pixels and checked against configurable normalized Zone A/B rectangles for a one-second source-time hold. Rack open/closed defaults use ArUco IDs 13/14; calibrate the IDs, zones, and HSV ranges in `experiments/EXP006_PAYLOAD_TRANSFER/experiment.yaml` for the physical setup.
* `EXP007` Plant Monitoring and Watering: nine ordered steps. Local ArUco markers 10/11/12 identify the tray, plant, and watering tool. A simulated watering interaction requires markers 11 and 12 near one another and a MediaPipe hand near the tool. Water quantity is not measured.

These experiment-specific detections use local OpenCV/MediaPipe results; generic YOLO classes are not claimed to recognize the custom payload boxes. No-marker/low-purity observations remain uncertain, and the protocol engine still controls progression.

## Additional Experiments

The Experiments view also discovers these protocol packages from their YAML definitions:

* `EXP006` Payload Transfer: eight ordered steps. Open/closed rack state uses local ArUco markers (defaults 13 and 14); red/yellow boxes use OpenCV HSV segmentation; Zone A/B rectangles, color ranges, purity, contour area, frame-gap, and one-second hold are configurable in `experiments/EXP006_PAYLOAD_TRANSFER/experiment.yaml`.
* `EXP007` Plant Monitoring and Watering: nine ordered steps. ArUco IDs 10, 11, and 12 identify tray, plant, and watering tool. Simulated watering requires marker proximity and a tracked MediaPipe hand; specified steps permit manual confirmation. Water quantity is not measured.

Before Payload Transfer operation, calibrate `color_detection.zones` to the camera framing and set `rack_state_markers` to the actual fiducials used by the physical rack. Detection uses these local image capabilities, not generic YOLO classification of custom boxes. Low-purity/no-marker cases are UNCERTAIN; boxes not fully in their assigned zone are rejected.

Two configurable experiment workflows are also available:

* `EXP006` Payload Transfer: red/yellow HSV segmentation, configurable normalized zones, a one-second source-time hold, and configurable ArUco rack-state markers (defaults 13=open, 14=closed).
* `EXP007` Plant Monitoring and Watering: ArUco IDs 10/11/12 for tray/plant/watering tool, hand-plus-marker proximity for a simulated action, protocol-gated manual confirmations, local image evidence, and a local observation report. Water quantity is not measured.

Calibrate the Payload Transfer `perception.color_detection.zones` for the camera framing and set `rack_state_markers` to the fiducials physically used by the setup before operating it. HSV ranges and thresholds are in the same experiment YAML. Object detections use local pixel segmentation/ArUco results; generic YOLO classes are not treated as red/yellow payload boxes.

## Decision Outcomes

### CORRECT

The observation matches the expected protocol condition.

### DEVIATION

The observation violates the expected protocol condition.

Examples include:

* Wrong object
* Wrong sequence
* Skipped step
* Premature action
* Unknown action

### UNCERTAIN

The system does not have sufficient confidence for a reliable decision and requests verification.

## Technology Stack

| Technology       | Purpose                     |
| ---------------- | --------------------------- |
| Python           | Core application            |
| OpenCV           | Camera and image processing |
| Ultralytics YOLO | Object detection            |
| MediaPipe        | Hand tracking               |
| PyYAML           | Protocol configuration      |
| PyTorch          | ML runtime                  |
| pytest           | Automated testing           |

## Running the Project

### Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

### Dashboard, Backend, and Live Camera

```powershell
.\.venv\Scripts\Activate.ps1
python scripts\start_all.py --live
```

Open `http://localhost:5173`. The API runs at `http://localhost:8001`. Use the Experiments view to select a valid protocol, start a webcam session, or process a local video; use Memory to review sessions and export records. Stop all services with `Ctrl+C`.

YOLO weights and the MediaPipe hand-landmarker model must be present locally before disconnected operation. Missing YOLO weights now produce an explicit startup error instead of an implicit download. Offline operation has not been verified with networking disconnected.

Select EXP006 or EXP007 in the Experiments view. Begin webcam sessions there; for local video, select the file and choose **Process local video**. Use Memory to review protocol decisions, image/video evidence, local reports, and CSV/JSON exports. EXP002–EXP005 remain incomplete placeholders and are not selectable.

Offline operation has not been verified with networking physically disconnected. Live camera FPS/timing and CPU/RAM have not been measured in a confirmed single-backend live session; consult [docs/gap-analysis.md](docs/gap-analysis.md) for current test evidence and limits.

### Controlled Protocol Demo

```powershell
python demo.py
```

This demonstrates:

```text
CORRECT
DEVIATION
UNCERTAIN
```

without requiring a webcam.

### Live Webcam Demo

```powershell
python run_live.py
```

Press `Q` in the webcam window to exit.

## Testing

Run focused maintained tests:

```powershell
python -m pytest tests\backend\test_api.py tests\backend\test_session_store.py tests\backend\test_mission_service_sessions.py tests\backend\test_sessions_api.py tests\backend\test_video_session_service.py tests\backend\test_performance_service.py -q
```

See [docs/gap-analysis.md](docs/gap-analysis.md) for verified test counts and remaining limitations. Pytest discovery now excludes root artifacts; a complete-suite pass is not claimed because a combined Windows SAPI test run stalled.

## Architecture

```text
Perception Layer
      ↓
Object + Hand Detection
      ↓
Perception Event
      ↓
Protocol Integration
      ↓
Mission State Machine
      ↓
Sequence Validation
      ↓
Deviation Detection
      ↓
Decision Engine
      ↓
Guidance / Recovery
```

## Project Structure

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

## Protocol Configuration

The main synthetic protocol is located at:

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

These files define the experiment metadata, activities, protocol objects, validation rules, and ordered mission steps.
The EXP002–EXP005 folders currently contain empty protocol files and are reported unavailable until actual definitions are supplied.

## Prototype Limitations

The current prototype uses a generic YOLO model with deterministic mapping to protocol-level objects.

It is **not** a custom astronaut-specific object detection model.

The current activity interpreter uses protocol state and perception signals rather than a trained human-action recognition model.

The system should therefore be understood as a protocol-aware prototype combining generic visual perception with deterministic interpretation and validation.

The decision engine is deterministic and rule-based.

The current prototype does **not** use an LLM for activity interpretation or decision making.

## Vision and Object Mapping

The prototype uses a generic YOLO model for object detection.

Detected generic objects are mapped to protocol-level objects where applicable.

```text
Generic Detection
      ↓
Object Mapping
      ↓
Protocol Object
```

This allows the prototype to demonstrate protocol validation without claiming a specialized mission-trained vision model.

## Controlled Demonstration

The controlled demonstration is designed to show three decision outcomes:

```text
Expected Action
      ↓
   CORRECT
```

```text
Wrong Object / Sequence
      ↓
   DEVIATION
```

```text
Low Confidence
      ↓
   UNCERTAIN
```

This provides a deterministic presentation path even when specialized protocol objects are not directly detectable by the generic YOLO model.

## Live Demonstration

The live webcam pipeline follows:

```text
Webcam
   ↓
YOLO + MediaPipe
   ↓
Perception Processing
   ↓
Protocol-Aware Mapping
   ↓
Decision Adapter
   ↓
Decision Engine
   ↓
Live Overlay
```

The overlay displays information such as:

* Current protocol step
* Detected activity
* Detected object
* Confidence
* Expected activity
* Expected object
* Decision status
* Deviation reason
* Guidance

## Documentation

Detailed project documentation is available in:

```text
docs/
```

Documentation includes:

```text
docs/
├── README.md
├── architecture/
├── development/
├── experiment/
├── deployment/
├── demo/
└── images/
```

See `docs/README.md` for the documentation index and recommended reading order.

## Development and Deployment

Development setup:

```text
docs/development/setup.md
```

Development guide:

```text
docs/development/development-guide.md
```

Deployment guide:

```text
docs/deployment/deployment-guide.md
```

Demo guide:

```text
docs/demo/demo-guide.md
```

## Future Development

Potential future improvements include:

* Domain-specific object detection
* Advanced action recognition
* Astronaut pose estimation
* Temporal activity recognition
* Edge-device optimization
* Voice guidance
* Mission telemetry integration
* Additional experimental protocols
* Onboard/offline deployment
* Specialized space-environment datasets

## Project Status

**Prototype: Operational**

The implemented prototype includes:

* Protocol loading
* Mission state management
* Sequence validation
* Deviation detection
* Rule-based decision making
* Synthetic protocol simulation
* Generic object perception
* Hand tracking
* Perception-to-protocol integration
* Live webcam processing
* Decision overlay
* Controlled demonstration
* Automated testing

Current automated regression:

```text
124 passed
```

## Academic / Prototype Disclaimer

ASTRA-GUARD is an academic research and demonstration prototype.

The included `EXP001 - TARDIGRADE` protocol is synthetic and is not an official ISRO flight procedure, operational mission procedure, or proprietary protocol.

The system is intended to demonstrate the concept of protocol-aware monitoring and validation.

## License

This repository is intended for academic, educational, and demonstration purposes.

Add an explicit open-source license such as MIT only if the project team has decided to release the code under that license.
