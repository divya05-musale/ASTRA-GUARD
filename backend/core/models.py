"""Pydantic domain models shared across backend routes."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CameraStatusResponse(BaseModel):
    connected: bool = False
    camera_open: bool = False
    external_stream: bool = False
    has_frame: bool = False
    frames_captured: int = 0
    camera_index: int = 0
    error: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None


class CameraDiscoveryResponse(BaseModel):
    cameras: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class ProtocolSummaryResponse(BaseModel):
    experiment: Dict[str, Any] = Field(default_factory=dict)
    steps_count: int = 0
    activities_count: int = 0
    objects_count: int = 0
    rules_count: int = 0
    loaded_at: Optional[str] = None


class StepDetail(BaseModel):
    step_id: str
    order: int = 0
    activity: str = ""
    expected_object: str = ""
    description: str = ""
    timeout_sec: int = 0
    guidance: Optional[str] = None


class ProtocolValidationResponse(BaseModel):
    valid: bool = False
    error: Optional[str] = None


class ProtocolReloadResponse(BaseModel):
    reloaded: bool = False
    experiment_id: Optional[str] = None
    steps: int = 0
    activities: int = 0
    objects: int = 0
    rules: int = 0
    loaded_at: Optional[str] = None
