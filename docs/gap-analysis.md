# ASTRA-GUARD Workflow Gap Analysis

## Scope and Evidence

The initial audit covered the root README, architecture/deployment documentation, experiment YAML packages, protocol and decision engine, FastAPI services/routes, React dashboard, perception and camera path, voice service, local storage/video modules, dependency manifests, model files, and tests. The implementation status and verification below reflect the incremental changes made after that audit.

The supplied YouTube page could not be retrieved (HTTP 401); its public English timed-text endpoint returned an empty response. This analysis therefore uses the workflow requirements in the task as the available functional reference. No reference branding, source, or UI was copied.

## Current State

| Area | Existing capability | Gap / finding | Priority |
| --- | --- | --- | --- |
| Protocol validation | YAML `ProtocolLoader`, ordered state machine, activity/object/confidence validation, and deterministic CORRECT/DEVIATION/UNCERTAIN outcomes exist. Activity interpretation uses the selected YAML's step/activity mapping. | EXP001, EXP006 Payload Transfer (8 steps), and EXP007 Plant Monitoring (9 steps) are selectable. EXP002–EXP005 remain unavailable because their five YAML files are empty; no procedures were invented for them. | Partial |
| Experiment/session lifecycle | Mission singleton exposes protocol progress and events. | Added local validated protocol discovery/selection, session IDs, start/cancel/complete, source type, restart interruption status, protocol snapshot, and local JSON/JSONL persistence. `ExperimentManager` remains empty/unused. | Partial |
| Manual confirmation | UNCERTAIN outcomes and corrective text guidance exist. | Confirmation requires a current UNCERTAIN decision and a global or step-level opt-in. EXP006 completion and EXP007 tray, plant, watering, and final-observation steps are opted in. Operator/time remain separate from automatic detections. | Partial |
| Live webcam | Single camera wrapper, capture thread/latest-frame slot, worker-based JPEG publisher, backend latest-JPEG storage, and new-frame MJPEG streaming exist. YOLO and MediaPipe remain enabled. | Added stage timings, capture/publish/stream/display FPS, capture-to-backend and capture-to-display delay, and CPU/RAM metrics. Mission-event HTTP remains synchronous before frame submission, and YOLO/MediaPipe are sequential. No active-camera measurement was possible, so these are instrumentation and code-level risks, not an identified lag cause. | Partial |
| Prerecorded video | Local video data directory exists. | Added bounded local upload, source-ordered processing through experiment-aware HSV/ArUco plus existing YOLO/MediaPipe and mission validation, progress, session association, local playback, and exports. Webcam frames are rejected from a video session. Real video/model playback with an operator file remains unverified; no real-time speed claim is made. | Partial |
| Voice guidance | Local `pyttsx3` worker, English/Hindi selection, enable/disable API, duplicate speech suppression, and written guidance exist. | UI/status now reports voice unavailable unless the local engine initialized. This machine has no Hindi-compatible voice. Combined tests invoking Windows SAPI stalled with `run loop already started`; real voice output still needs a dedicated fix/verification. | Partial |
| Persistence/evidence/reports | In-memory event history and short-term memory existed; `data/execution/sessions.csv` is synthetic simulation output. | Added atomic JSON session metadata, JSONL event journal, local image/video evidence endpoints, restart recovery, JSON/CSV exports with manual provenance/evidence fields, local observation reports, and bounded in-memory history. No SQL database was present or replaced. | Partial |
| Session review/dashboard | Existing Mission, Live Feed, Memory, Analytics, Protocol, Events, Experiments, and Settings areas show live data and voice controls. | Extended existing Experiments and Memory views with selection, session start, review, cancellation, manual confirmation, local-video upload/progress/playback, and exports without replacing the dashboard structure/styles. | Partial |
| Offline dependencies | Dashboard/backend and perception communications target loopback. `pyttsx3` is local. YOLO/MediaPipe model files and OpenCV ArUco support are present; required package imports work. | Missing local YOLO weights fail explicitly. Package/model provisioning is setup-time. Disconnected-network startup and operation have not been tested; complete offline readiness is not claimed. | Partial |
| External services | No cloud API, online authentication, cloud storage, or remote database use was found in the active application path. | Local loopback HTTP is required while the dashboard/backend are separate processes. The one explicit model URL is in a manual download script; local model presence avoids it in this workspace. | Medium |
| Tests | Existing tests cover decision outcomes, protocol validation, mocked camera behavior, latest-frame publishing/MJPEG, backend bridge, and voice decision deduplication. | No frontend test script; no tests for manual confirmation, persistent sessions/restart, report exports, local video, or disconnected-network operation. `pytest -q` from the project root auto-collects binary `test_out.txt` and fails with `UnicodeDecodeError`; `pytest tests -q` stalled after 16 progress dots and was stopped without a result. | High |

## Verification Snapshot

- Protocol loader/API selection: EXP001 valid (8 steps), EXP006 valid/selectable (8), EXP007 valid/selectable (9); EXP002–EXP005 remain invalid because their protocol YAML files are empty.
- Synthetic perception tests verify red/yellow HSV segmentation, configured-zone classification, outside/wrong-zone rejection, one-second dwell, ArUco IDs 10–14, and hand-gated simulated watering. Physical calibration and live-camera recognition remain unverified.
- Python environment: `ASTRA-GUARD/.venv/Scripts/python.exe` is Python 3.13; imports for OpenCV, NumPy, PyYAML, Torch/Torchvision, Ultralytics, MediaPipe, FastAPI/Uvicorn, and pyttsx3 succeeded.
- Models: root YOLO weights and `models/hand_tracking/hand_landmarker.task` exist.
- Frontend: `npm run build` succeeded (Vite production build).
- Tests: a combined focused suite passed (103); later focused detector, experiment service, media/export API, and experiment selection tests passed. Python compileall and frontend production build passed. A combined Windows SAPI run stalled (`run loop already started`) and was stopped. `pytest --collect-only -q` collected 243 tests; the full suite has no verified pass count.
- Live performance: repeated event/frame POSTs were observed in terminal logs, but backend snapshots timed out while duplicate launch trees existed; no trustworthy FPS/timing/CPU/RAM report was captured.
- Worktree: this workspace folder is not a Git repository, so Git status/diff could not be used to establish baseline changes.

## Remaining Work

1. Calibrate EXP006 normalized zones, HSV ranges, and rack-state ArUco IDs (defaults 13/14) for the physical setup. Red/yellow boxes are detected by local color segmentation, not generic YOLO.
2. Run exactly one backend, one frontend, `run_live.py`, and a usable webcam together; use telemetry to measure stage time, FPS, latency, CPU, and RAM. Duplicate `start_all` trees and API timeouts prevented trustworthy live readings in this pass.
3. Fix and verify the Windows SAPI lifecycle (`run loop already started`); confirm real voice output and Hindi voice availability.
4. Obtain a complete maintained-suite result; current collection is fixed, but SAPI-backed tests can still stall.
5. Obtain actual experiment/activity/object/rule/step definitions for EXP002–EXP005; their current files are empty.
6. Perform physically disconnected-network verification for startup, camera/models, protocol decisions, save/reopen, exports, video playback, and voice.

## Open Inputs

- EXP002–EXP005 require their actual experiment/activity/object/rule/step definitions before they can be enabled.
- Payload rack-state marker IDs are configurable defaults, not supplied physical calibration; change them to match the lab setup.
- Color-segmentation thresholds/zones are configurable but require operator calibration and controlled colors/lighting.
- Plant watering is a marker/hand proximity simulation; water volume is not measured.
- Live-camera performance cannot be diagnosed or certified until backend, frontend, `run_live.py`, and a usable camera are running together.
- Reference-video-specific details remain unverified until its transcript or an accessible video page is provided.
