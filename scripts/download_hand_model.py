"""Download the MediaPipe Hand Landmarker model for ASTRA-GUARD."""

from pathlib import Path
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_DIR = PROJECT_ROOT / "models" / "hand_tracking"
MODEL_PATH = MODEL_DIR / "hand_landmarker.task"

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/"
    "hand_landmarker.task"
)


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    if MODEL_PATH.exists():
        size_mb = MODEL_PATH.stat().st_size / (1024 * 1024)
        print(f"Model already exists: {MODEL_PATH}")
        print(f"Size: {size_mb:.2f} MB")
        return

    print("Downloading MediaPipe Hand Landmarker model...")
    print(MODEL_URL)
    print()

    try:
        with urlopen(MODEL_URL, timeout=60) as response:
            data = response.read()

        MODEL_PATH.write_bytes(data)

    except Exception as exc:
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()

        raise RuntimeError(
            f"Model download failed: {exc}"
        ) from exc

    size_mb = MODEL_PATH.stat().st_size / (1024 * 1024)

    print()
    print("Download complete.")
    print(f"Model: {MODEL_PATH}")
    print(f"Size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()