"""Experiment schema placeholder (kept minimal)."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class Experiment(BaseModel):
    experiment_id: Optional[str] = None
    experiment_name: Optional[str] = None

