"""Phase 13 → Phase 16 HTTP bridge client.

Sends the existing ``PerceptionEvent`` to the authoritative FastAPI
endpoint::

    POST {base_url}/api/mission/event

No decision logic lives here. The client only serializes the event
(using the existing ``PerceptionEvent.to_dict()`` when available) and
returns the parsed JSON decision from the backend, which itself runs
``LivePerceptionSession.process_event()``.

Uses only the Python standard library (``urllib``) so no new
dependency is required.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict

DEFAULT_BASE_URL = "http://127.0.0.1:8001"
MISSION_EVENT_PATH = "/api/mission/event"
DEFAULT_TIMEOUT = 5.0


class BackendConnectionError(RuntimeError):
    """Raised when the FastAPI backend cannot be reached or fails."""


class MissionBackendClient:
    """Small HTTP client for the ASTRA-GUARD mission backend."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("base_url must be a non-empty string")
        try:
            timeout_value = float(timeout)
        except (TypeError, ValueError) as exc:
            raise ValueError("timeout must be a number") from exc
        if timeout_value <= 0:
            raise ValueError("timeout must be positive")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_value

    @property
    def event_url(self) -> str:
        """Return the full mission-event endpoint URL."""
        return f"{self.base_url}{MISSION_EVENT_PATH}"

    @staticmethod
    def serialize_event(event: Any) -> Dict[str, Any]:
        """Serialize a PerceptionEvent (or plain dict) to JSON-ready dict."""
        if isinstance(event, dict):
            return dict(event)
        to_dict = getattr(event, "to_dict", None)
        if callable(to_dict):
            payload = to_dict()
            if not isinstance(payload, dict):
                raise TypeError("event.to_dict() must return a dict")
            return payload
        raise TypeError(
            "event must be a PerceptionEvent (with to_dict()) or a dict"
        )

    def request_json(
        self,
        method: str,
        path: str,
        payload: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Send one JSON request to the backend and return parsed JSON."""
        url = f"{self.base_url}{path}"
        body = None
        headers = {}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers = {"Content-Type": "application/json"}
        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8")
            except Exception:  # noqa: BLE001 - best-effort error detail
                detail = ""
            raise BackendConnectionError(
                f"Backend rejected request: HTTP {exc.code} {detail}".strip()
            ) from exc
        except urllib.error.URLError as exc:
            raise BackendConnectionError(
                f"Cannot reach mission backend at {url}: "
                f"{exc.reason}. Is FastAPI running "
                f"(uvicorn backend.main:app)?"
            ) from exc
        except TimeoutError as exc:
            raise BackendConnectionError(
                f"Mission backend at {url} timed out "
                f"after {self.timeout}s"
            ) from exc
        try:
            result = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise BackendConnectionError(
                f"Backend returned non-JSON response: {raw!r}"
            ) from exc
        if not isinstance(result, dict):
            raise BackendConnectionError(
                f"Backend returned unexpected payload: {raw!r}"
            )
        return result

    def post_event(self, event: Any) -> Dict[str, Any]:
        """POST one perception event and return the backend decision dict."""
        return self.request_json(
            "POST",
            MISSION_EVENT_PATH,
            self.serialize_event(event),
        )

    def get_protocol(self) -> Dict[str, Any]:
        """Read the active local protocol for experiment-specific perception."""
        return self.request_json("GET", "/api/mission/protocol")

    def reset_mission(self) -> Dict[str, Any]:
        """Reset the backend mission to the protocol's initial state."""
        return self.request_json("POST", "/api/mission/reset")
