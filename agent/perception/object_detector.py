"""YOLO generic object detector (Phase 6). Pretrained COCO-style classes only.

Does NOT recognize ASTRA-GUARD domain objects (biological_sample,
sample_chamber, ...). No protocol-activity inference. Local only.
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import cv2
import numpy as np

logger = logging.getLogger(__name__)
DOMAIN_OBJECTS = ("biological_sample", "sample_chamber",
                  "experiment_controller", "experiment_container")


class ModelNotAvailableError(RuntimeError):
    """Raised when YOLO weights cannot be loaded (e.g. offline first run)."""


class ObjectDetector:
    """Wrapper around Ultralytics YOLO returning structured detection dicts."""

    def __init__(self, model_path: str = "yolo11n.pt",
                 confidence_threshold: float = 0.40,
                 device: Optional[str] = None) -> None:
        self.model_path = str(model_path)
        self.confidence_threshold = float(confidence_threshold)
        self.device = device
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0 and 1")
        self._model = self._load_model(self.model_path)

    def _load_model(self, model_path: str):
        local_model = Path(model_path)
        if not local_model.is_file():
            raise ModelNotAvailableError(
                f"Local YOLO weights are missing: {local_model.resolve()}. "
                "Runtime model downloads are disabled; install the model before offline use."
            )
        try:
            from ultralytics import YOLO
        except Exception as exc:
            raise ModelNotAvailableError(f"Ultralytics not installed: {exc}") from exc
        try:
            return YOLO(str(local_model.resolve()))
        except Exception as exc:
            raise ModelNotAvailableError(
                f"Unable to load local YOLO weights '{model_path}': {exc}") from exc

    def _validate_frame(self, frame: np.ndarray) -> None:
        if frame is None:
            raise ValueError("detect received None frame")
        if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("detect expects an OpenCV BGR frame")

    def _parse_results(self, results, frame_shape) -> List[Dict[str, Any]]:
        height, width = frame_shape[:2]
        detections: List[Dict[str, Any]] = []
        names: Dict[int, str] = getattr(self._model, "names", {}) or {}
        for result in results or []:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                try:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
                except Exception:
                    continue
                if conf < self.confidence_threshold:
                    continue
                x1 = max(0.0, min(float(width), x1))
                y1 = max(0.0, min(float(height), y1))
                x2 = max(0.0, min(float(width), x2))
                y2 = max(0.0, min(float(height), y2))
                if x2 < x1 or y2 < y1:
                    continue
                name = str(names.get(cls_id, str(cls_id)))
                detections.append({"class_id": cls_id, "class_name": name,
                                   "confidence": conf,
                                   "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                                   "center": {"x": (x1 + x2) / 2.0, "y": (y1 + y2) / 2.0}})
        return detections

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Run inference on BGR frame; [] when nothing detected."""
        self._validate_frame(frame)
        try:
            kwargs: Dict[str, Any] = {"conf": self.confidence_threshold, "verbose": False}
            if self.device:
                kwargs["device"] = self.device
            results = self._model(frame, **kwargs)
        except Exception as exc:
            raise RuntimeError(f"YOLO inference failed: {exc}") from exc
        return self._parse_results(results, frame.shape)

    def draw_detections(self, frame: np.ndarray,
                        detections: List[Dict[str, Any]]) -> np.ndarray:
        """Return annotated COPY; input frame never modified."""
        if frame is None:
            raise ValueError("draw_detections received None frame")
        annotated = frame.copy()
        for det in detections or []:
            bbox = det.get("bbox", {})
            try:
                x1, y1, x2, y2 = (int(bbox[k]) for k in ("x1", "y1", "x2", "y2"))
            except Exception:
                continue
            label = f"{det.get('class_name', '?')} {float(det.get('confidence', 0.0)):.2f}"
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(annotated, label, (x1, max(0, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
        return annotated

    def get_model_info(self) -> Dict[str, Any]:
        names = getattr(self._model, "names", {}) or {}
        return {"model_path": self.model_path,
                "confidence_threshold": self.confidence_threshold,
                "device": self.device or "default(cpu)",
                "num_classes": len(names)}

