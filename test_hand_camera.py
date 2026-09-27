import cv2

from agent.perception.camera import Camera
from agent.perception.hand_tracker import HandTracker


def main():
    tracker = HandTracker()

    # Single camera owner: reuse the shared Camera wrapper, the ONE
    # place that owns cv2.VideoCapture in the live pipeline.
    camera = Camera(camera_index=0)
    try:
        camera.open()
    except Exception:
        print("ERROR: Could not open webcam.")
        return

    print("Hand detection test started.")
    print("Show your hand clearly to the camera.")
    print("Press Q to quit.")

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("ERROR: Could not read frame.")
                break

            hands = tracker.process(frame)

            # Draw hand landmarks.
            display = tracker.draw_landmarks(frame, hands)

            # Display detection count.
            text = f"Hands detected: {len(hands)}"

            cv2.putText(
                display,
                text,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow("ASTRA-GUARD - Hand Detection Test", display)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

    finally:
        camera.release()
        tracker.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()