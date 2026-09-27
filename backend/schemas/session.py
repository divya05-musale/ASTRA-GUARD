"""Request schemas for local experiment session management."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SessionStartRequest(BaseModel):
    experiment_id: str = Field(min_length=1, max_length=64)
    input_source: Literal["webcam"] = "webcam"
    evidence_path: Optional[str] = None


class SessionEndRequest(BaseModel):
    status: Literal["COMPLETED", "CANCELLED"]


class ManualConfirmationRequest(BaseModel):
    operator: str = Field(min_length=1, max_length=120)


class SessionActionRequest(BaseModel):
    action: Literal["capture_evidence", "save_observation"]
    operator: str = Field(default="not_provided", min_length=1, max_length=120)