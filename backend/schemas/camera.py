"""Camera route Pydantic schemas."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FramePublishRequest(BaseModel):
    jpeg: Optional[str] = None
    frame_bgr_hex: Optional[str] = None
    source: str = "external"


class CameraStatusResponse(BaseModel):
    connected: bool = False
    camera_open: bool = False
    external_stream: bool = False
    has_frame: bool = False
    frames_captured: int = 0
    camera_index: int = 0
    error: Optional[str] = None


class CameraDiscoveryResponse(BaseModel):
    cameras: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0
