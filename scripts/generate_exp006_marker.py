"""Generate the configured EXP006 open-rack ArUco marker for physical tests."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def generate_marker(size: int, quiet_zone: int) -> np.ndarray:
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(dictionary, 13, size, borderBits=1)
    canvas = np.full((size + quiet_zone * 2, size + quiet_zone * 2), 255, dtype=np.uint8)
    canvas[quiet_zone:quiet_zone + size, quiet_zone:quiet_zone + size] = marker

    detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
    _corners, marker_ids, _rejected = detector.detectMarkers(canvas)
    if marker_ids is None or 13 not in marker_ids.flatten():
        raise RuntimeError("Generated image did not verify as DICT_4X4_50 marker ID 13")
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="PNG output path")
    parser.add_argument("--size", default=800, type=int, help="marker side length in pixels")
    parser.add_argument("--quiet-zone", default=120, type=int, help="white margin around the marker")
    args = parser.parse_args()
    if args.size < 64 or args.quiet_zone < 0:
        parser.error("--size must be at least 64 and --quiet-zone cannot be negative")

    image = generate_marker(args.size, args.quiet_zone)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.output), image):
        raise OSError(f"Could not write marker image to {args.output}")
    print(f"Verified DICT_4X4_50 marker ID 13: {args.output} ({image.shape[1]}x{image.shape[0]} px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())