"""Environment-based configuration for ASTRA-GUARD backend."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    PROJECT_NAME: str = "ASTRA-GUARD"
    PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
    BACKEND_HOST: str = os.environ.get("ASTRA_GUARD_HOST", "127.0.0.1")
    BACKEND_PORT: int = _env_int("ASTRA_GUARD_PORT", 8000)
    BACKEND_CORS_ORIGINS: list[str] = None  # type: ignore[assignment]
    FRONTEND_VITE_PORT: int = _env_int("VITE_PORT", 5173)
    MODE: str = os.environ.get("ASTRA_GUARD_MODE", "standalone").lower()
    LOG_LEVEL: str = os.environ.get("ASTRA_GUARD_LOG_LEVEL", "INFO").upper()
    EXPERIMENTS_DIR: Path = PROJECT_ROOT / "experiments"
    DEFAULT_EXPERIMENT: str = "EXP001_TARDIGRADE"
    CAMERA_INDEX: int = _env_int("ASTRA_GUARD_CAMERA_INDEX", 0)
    CAMERA_WIDTH: int = _env_int("ASTRA_GUARD_CAMERA_WIDTH", 1280)
    CAMERA_HEIGHT: int = _env_int("ASTRA_GUARD_CAMERA_HEIGHT", 720)
    JPEG_QUALITY: int = _env_int("ASTRA_GUARD_JPEG_QUALITY", 80)
    YOLO_MODEL: str = os.environ.get("ASTRA_GUARD_YOLO_MODEL", "yolo11n.pt")
    YOLO_CONFIDENCE: float = float(os.environ.get("ASTRA_GUARD_YOLO_CONF", "0.40"))
    MAX_EVENTS_STORED: int = _env_int("ASTRA_GUARD_MAX_EVENTS", 4096)
    ENABLE_MEDIAPIPE: bool = _env_bool("ASTRA_GUARD_ENABLE_HANDS", True)
    ENABLE_LIVE_PROCESSOR: bool = _env_bool("ASTRA_GUARD_ENABLE_LIVE_PERCEPTION", True)

    def __post_init__(self) -> None:
        if self.BACKEND_CORS_ORIGINS is None:
            ports = [self.BACKEND_PORT, self.FRONTEND_VITE_PORT, 3000, 8080, 8000]
            origins = []
            for port in sorted(set(ports)):
                origins.extend([
                    f"http://localhost:{port}",
                    f"http://127.0.0.1:{port}",
                ])
            self.BACKEND_CORS_ORIGINS = origins


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
