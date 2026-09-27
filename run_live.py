"""
ASTRA-GUARD live webcam demo.

Phase 7.5.3 Step 4:
Connects the real webcam with:

Webcam
    ↓
YOLO + MediaPipe
    ↓
PerceptionEvent
    ↓
Protocol Object Mapping
    ↓
Protocol Object Validation
    ↓
Protocol Bridge
    ↓
Decision Engine
    ↓
Mission Status
    ↓
Live Visualization
    ↓
Mission Summary
"""

from __future__ import annotations

import cv2
import os

from agent.mission.protocol_loader import ProtocolLoader
from agent.mission.decision_engine import DecisionEngine
from agent.mission.deviation_detector import DeviationDetector
from agent.mission.live_perception_session import LivePerceptionSession
from agent.mission.mission_status import MissionStatus
from agent.mission.perception_decision import PerceptionDecisionAdapter
from agent.mission.perception_bridge import PerceptionProtocolBridge
from agent.mission.sequence_validator import SequenceValidator
from agent.mission.state_machine import ProtocolStateMachine
from agent.mission.step_manager import StepManager

from agent.perception.backend_client import MissionBackendClient
from agent.perception.hand_tracker import HandTracker
from agent.perception.experiment_object_detector import ExperimentObjectDetector
from agent.perception.live_frame_publisher import LatestFramePublisher
from agent.perception.live_processor import LivePerceptionProcessor
from agent.perception.object_detector import ObjectDetector
from agent.perception.webcam_runtime import WebcamRuntime


def build_mission_session() -> LivePerceptionSession:
    """Build the ASTRA-GUARD mission using EXP001_TARDIGRADE."""

    protocol_path = "experiments/EXP001_TARDIGRADE"

    print(f"Loading protocol: {protocol_path}")

    protocol = ProtocolLoader(protocol_path).load()

    steps = protocol.get_steps()
    activities = protocol.get_activities()
    objects = protocol.get_objects()
    rules = protocol.get_rules()

    print(
        f"Protocol loaded: "
        f"{protocol.get_experiment().get('experiment_id')} - "
        f"{protocol.get_experiment().get('experiment_name')}"
    )

    print(f"Steps loaded: {len(steps)}")
    print(f"Activities loaded: {len(activities)}")
    print(f"Objects loaded: {len(objects)}")
    print(f"Rules loaded: {len(rules)}")

    # ---------------------------------------------------------
    # Protocol state
    # ---------------------------------------------------------

    state_machine = ProtocolStateMachine(
        steps
    )

    # ---------------------------------------------------------
    # Step management
    # ---------------------------------------------------------

    step_manager = StepManager(
        steps,
        state_machine,
        rules,
    )

    # ---------------------------------------------------------
    # Sequence validation
    # ---------------------------------------------------------

    validator = SequenceValidator(
        steps,
        activities,
    )

    # ---------------------------------------------------------
    # Deviation detection
    # ---------------------------------------------------------

    deviation_detector = DeviationDetector(
        steps,
        activities,
    )

    # ---------------------------------------------------------
    # Decision engine
    # ---------------------------------------------------------

    decision_engine = DecisionEngine(
        state_machine,
        step_manager,
        validator,
        deviation_detector,
        rules=rules,
    )

    # ---------------------------------------------------------
    # Connect protocol objects to perception bridge
    # ---------------------------------------------------------

    bridge = PerceptionProtocolBridge(
        protocol_objects=objects
    )

    # ---------------------------------------------------------
    # Perception → Decision adapter
    # ---------------------------------------------------------

    adapter = PerceptionDecisionAdapter(
        decision_engine,
        bridge=bridge,
        protocol_aware=True,
    )

    # ---------------------------------------------------------
    # Live perception session
    # ---------------------------------------------------------

    return LivePerceptionSession(
        adapter
    )


def main() -> None:
    """Start the ASTRA-GUARD live webcam demo."""

    print()
    print("=" * 60)
    print("ASTRA-GUARD LIVE DEMO")
    print("=" * 60)
    print()

    # ---------------------------------------------------------
    # Initialize mission system
    # ---------------------------------------------------------

    print("Initializing mission system...")

    session = build_mission_session()

    # Phase 11:
    # MissionStatus provides mission monitoring information.
    mission_status = MissionStatus(session)

    # ---------------------------------------------------------
    # Initialize YOLO
    # ---------------------------------------------------------

    print("Loading YOLO...")

    object_detector = ObjectDetector(
        model_path="yolo11n.pt",
        confidence_threshold=0.40,
    )

    # ---------------------------------------------------------
    # Initialize MediaPipe
    # ---------------------------------------------------------

    print("Loading MediaPipe hand tracker...")

    hand_tracker = HandTracker()

    # ---------------------------------------------------------
    # Live perception processor
    #
    # MODE A (local/offline, default): session.process_event(event).
    # MODE B (backend): POST to FastAPI /api/mission/event when
    # ASTRA_GUARD_MODE=backend. The backend is then authoritative.
    # ---------------------------------------------------------

    backend_client = None

    if os.environ.get("ASTRA_GUARD_MODE", "local").strip().lower() in (
        "backend",
        "remote",
        "api",
    ):
        backend_client = MissionBackendClient(
            base_url=os.environ.get(
                "ASTRA_GUARD_BACKEND_URL",
                "http://127.0.0.1:8001",
            ),
        )

        print(f"Backend mode: {backend_client.event_url}")

    project_root = os.path.dirname(os.path.abspath(__file__))
    default_experiment_path = os.path.join(
        project_root, "experiments", "EXP001_TARDIGRADE"
    )
    object_detector = ExperimentObjectDetector(
        object_detector,
        default_experiment_path,
        protocol_client=backend_client,
    )

    processor = LivePerceptionProcessor(
        object_detector,
        hand_tracker,
        session,
        backend_client,
    )

    # ---------------------------------------------------------
    # Webcam runtime
    # ---------------------------------------------------------

    backend_mode = os.environ.get(
        "ASTRA_GUARD_MODE",
        "local",
    ).strip().lower() in {"backend", "remote", "api"}
    backend_url = os.environ.get(
        "ASTRA_GUARD_BACKEND_URL",
        "http://127.0.0.1:8001",
    ).rstrip("/")
    frame_publisher = (
        LatestFramePublisher(backend_url + "/api/camera/publish")
        if backend_mode
        else None
    )

    runtime = WebcamRuntime(
        processor,
        camera_index=0,
        width=int(os.environ.get("ASTRA_GUARD_CAMERA_WIDTH", "640")),
        height=int(os.environ.get("ASTRA_GUARD_CAMERA_HEIGHT", "480")),
        publish_to_backend=False,
    )

    print()
    print("ASTRA-GUARD is ready.")
    print("Press Q in the webcam window to exit.")
    print()

    try:
        runtime.open()

        while True:

            # -------------------------------------------------
            # Process one webcam frame
            # -------------------------------------------------

            result = runtime.process_once()

            # Original frame
            frame = result["frame"]

            # Perception event
            event = result["event"]

            # Protocol decision
            decision = result["result"]

            # -------------------------------------------------
            # 1. Draw YOLO object detections
            # -------------------------------------------------

            display_frame = object_detector.draw_detections(
                frame,
                event.objects,
            )

            # -------------------------------------------------
            # 2. Draw MediaPipe hand landmarks
            # -------------------------------------------------

            display_frame = hand_tracker.draw_landmarks(
                display_frame,
                event.hands,
                copy_frame=False,
            )

            # -------------------------------------------------
            # 3. Submit the latest annotated frame without waiting for HTTP.
            if frame_publisher is not None:
                frame_publisher.submit(
                    display_frame,
                    metrics={
                        **result.get("timings_ms", {}),
                        "capture_fps": result.get("capture_fps", 0.0),
                        "captured_monotonic": result.get("capture_monotonic", 0.0),
                    },
                )

            # -------------------------------------------------
            # 5. Display final annotated frame
            # -------------------------------------------------

            cv2.imshow(
                "ASTRA-GUARD",
                display_frame,
            )

            # -------------------------------------------------
            # 5. Terminal mission status
            # -------------------------------------------------

            print(
                f"\r"
                f"Step: {decision.get('step_id', 'UNKNOWN')} | "
                f"Status: {decision.get('status', 'UNKNOWN')} | "
                f"Activity: {decision.get('detected_activity', 'UNKNOWN')} | "
                f"Object: {decision.get('detected_object', 'NONE')} | "
                f"Progress: "
                f"{mission_status.get_progress().get('progress_percent', 0) if not backend_mode else 'backend'}",
                end="",
                flush=True,
            )

            # -------------------------------------------------
            # 6. Check keyboard input
            # -------------------------------------------------

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

    except KeyboardInterrupt:
        print()
        print()
        print("Stopping ASTRA-GUARD...")

    finally:
        # -----------------------------------------------------
        # Release webcam and perception resources
        # -----------------------------------------------------

        if frame_publisher is not None:
            frame_publisher.close()
        runtime.release()
        processor.close()
        cv2.destroyAllWindows()

        # -----------------------------------------------------
        # Phase 11 Step 6:
        # Display mission summary
        # -----------------------------------------------------

        summary = mission_status.get_summary()
        progress = mission_status.get_progress()

        print()
        print()
        print("=" * 60)
        print("              ASTRA-GUARD MISSION SUMMARY")
        print("=" * 60)
        print()

        print(
            f"Total Events: {summary['total_events']}"
        )

        print(
            f"Correct:      {summary['correct']}"
        )

        print(
            f"Deviations:   {summary['deviations']}"
        )

        print(
            f"Uncertain:    {summary['uncertain']}"
        )

        print(
            f"Completed:    {summary['completed']}"
        )

        print()

        print(
            f"Progress:     "
            f"{progress['completed_steps']}/"
            f"{progress['total_steps']} steps "
            f"({progress['progress_percent']:.1f}%)"
        )

        print()

        if progress["completed"]:
            print("Mission Status: COMPLETED")
        else:
            print("Mission Status: INCOMPLETE")

        print()
        print("=" * 60)
        print("ASTRA-GUARD stopped.")
        print("=" * 60)


if __name__ == "__main__":
    main()