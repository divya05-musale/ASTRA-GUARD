"""
ASTRA-GUARD protocol object validator.

Phase 7.5.3 Step 2:
Validates whether a detected ASTRA-GUARD object belongs
to the currently loaded protocol.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


class ProtocolObjectValidator:
    """Validate detected objects against protocol-defined objects."""

    def __init__(self, protocol_objects: Iterable[Dict[str, Any]]) -> None:
        self._objects = {}

        for obj in protocol_objects:
            if not isinstance(obj, dict):
                continue

            object_id = obj.get("object_id")

            if object_id:
                self._objects[str(object_id)] = obj

    def is_valid(self, object_id: Optional[str]) -> bool:
        """Return True when the object exists in the protocol."""
        if not object_id:
            return False

        return str(object_id) in self._objects

    def get_object(
        self,
        object_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Return protocol object definition if it exists."""
        if not self.is_valid(object_id):
            return None

        return self._objects[str(object_id)].copy()

    def get_object_ids(self) -> list[str]:
        """Return all protocol object IDs."""
        return list(self._objects.keys())