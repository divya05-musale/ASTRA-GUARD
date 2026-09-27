"""Atomic local JSON storage for experiment session records."""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SESSION_DIR = PROJECT_ROOT / "data" / "execution" / "session_records"
_SESSION_ID = re.compile(r"^[0-9a-f]{32}$")


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SessionStore:
    """Persist one JSON document per session, keeping media files external."""

    def __init__(self, directory: str | Path = DEFAULT_SESSION_DIR) -> None:
        self.directory = Path(directory)
        self._lock = threading.RLock()

    def _path(self, session_id: str) -> Path:
        if not _SESSION_ID.fullmatch(str(session_id)):
            raise ValueError("Invalid session ID")
        return self.directory / f"{session_id}.json"

    def _read_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(session_id)
        if not path.is_file():
            return None
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream)
        return value if isinstance(value, dict) else None

    def _read(self, session_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(session_id)
        value = self._read_metadata(session_id)
        if value is None:
            return None
        events = []
        journal = path.with_suffix(".jsonl")
        if journal.is_file():
            with journal.open("r", encoding="utf-8") as stream:
                for line in stream:
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(event, dict):
                        continue
                    if event.get("_kind") == "repeat_update":
                        for stored in reversed(events):
                            if stored.get("timestamp") == event.get("timestamp"):
                                stored["repeat_count"] = int(event.get("repeat_count", 1))
                                break
                    else:
                        events.append(event)
        value["events"] = events
        return value

    def _write(self, record: Dict[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self._path(str(record["session_id"]))
        temporary = target.with_suffix(".tmp")
        metadata = {key: value for key, value in record.items() if key != "events"}
        metadata["event_count"] = (
            len(record["events"])
            if "events" in record
            else int(record.get("event_count", 0))
        )
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(metadata, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        temporary.replace(target)

    def create(self, record: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            value = dict(record)
            value["session_id"] = uuid4().hex
            value.setdefault("started_at", utc_timestamp())
            value.setdefault("completed_at", None)
            value.setdefault("status", "IN_PROGRESS")
            value.setdefault("events", [])
            value.setdefault("evidence", [])
            self._write(value)
            self._path(value["session_id"]).with_suffix(".jsonl").touch()
            return value

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._read(session_id)

    def get_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._read_metadata(session_id)

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            if not self.directory.is_dir():
                return []
            records = []
            for path in self.directory.glob("*.json"):
                try:
                    with path.open("r", encoding="utf-8") as stream:
                        record = json.load(stream)
                    if isinstance(record, dict):
                        record["events"] = []
                        records.append(record)
                except (OSError, json.JSONDecodeError):
                    continue
            return sorted(
                records,
                key=lambda item: str(item.get("started_at", "")),
                reverse=True,
            )

    def interrupt_in_progress(self) -> int:
        """Close records left active by a previous backend process."""
        interrupted = 0
        with self._lock:
            if not self.directory.is_dir():
                return interrupted
            for path in self.directory.glob("*.json"):
                try:
                    record = self._read_metadata(path.stem)
                except (OSError, ValueError, json.JSONDecodeError):
                    continue
                if record and record.get("status") == "IN_PROGRESS":
                    record.update({
                        "status": "INTERRUPTED",
                        "completed_at": utc_timestamp(),
                        "interruption_reason": "backend_restarted",
                    })
                    self._write(record)
                    interrupted += 1
        return interrupted

    def update(self, session_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            record = self._read(session_id)
            if record is None:
                return None
            record.update(fields)
            self._write(record)
            return record

    def append_event(
        self,
        session_id: str,
        event: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            record = self._read_metadata(session_id)
            if record is None:
                return None
            journal = self._path(session_id).with_suffix(".jsonl")
            with journal.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + "\n")
                stream.flush()
            record["event_count"] = int(record.get("event_count", 0)) + 1
            self._write(record)
            return record

    def append_repeat_update(
        self,
        session_id: str,
        timestamp: str,
        repeat_count: int,
    ) -> bool:
        """Append a compact aggregate update for one coalesced event."""
        with self._lock:
            if self._read_metadata(session_id) is None:
                return False
            marker = {
                "_kind": "repeat_update",
                "timestamp": timestamp,
                "repeat_count": max(1, int(repeat_count)),
            }
            journal = self._path(session_id).with_suffix(".jsonl")
            with journal.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(marker) + "\n")
                stream.flush()
            return True

    def update_processing(self, session_id: str, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update lightweight video progress without rewriting event history."""
        with self._lock:
            record = self._read_metadata(session_id)
            if record is None:
                return None
            record["video_processing"] = dict(state)
            self._write(record)
            return record