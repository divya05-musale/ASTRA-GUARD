"""Detection/experiment schema placeholders (kept minimal)."""
from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel


class Detection(BaseModel):
    activity: Optional[str] = None
    object: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = {}

