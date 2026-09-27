import io
import subprocess
import sys

from scripts import start_all


class ExitedProcess:
    returncode = 0

    def poll(self):
        return self.returncode


class FakeManagedProcess:
    started = []

    def __init__(self, name, args, cwd=None, env=None):
        self.name = name
        self.args = args
        self.cwd = cwd
        self.env = env or {}
        self.proc = ExitedProcess()
        self.started.append(self)

    def start(self):
        pass

    def stop(self):
        self.proc = None


def _prepare_launcher(monkeypatch, argv):
    FakeManagedProcess.started = []
    monkeypatch.setattr(sys, "argv", ["start_all.py", *argv])
    monkeypatch.setattr(start_all, "_acquire_instance_lock", lambda: io.BytesIO())
    monkeypatch.setattr(start_all, "ManagedProcess", FakeManagedProcess)
    monkeypatch.setattr(start_all, "_wait_for_http", lambda _url: True)
    monkeypatch.setattr(start_all.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(start_all, "_MANAGED", [])


def test_no_live_starts_dashboard_services_without_perception_worker(monkeypatch):
    _prepare_launcher(monkeypatch, ["--no-live"])

    assert start_all.main() == 0

    assert [process.name for process in FakeManagedProcess.started] == [
        "backend-fastapi",
        "frontend-vite",
    ]
    assert FakeManagedProcess.started[0].env["ASTRA_GUARD_LIVE_ENABLED"] == "0"


def test_live_starts_one_perception_worker_and_enables_backend_frames(monkeypatch):
    _prepare_launcher(monkeypatch, ["--live"])

    assert start_all.main() == 0

    assert [process.name for process in FakeManagedProcess.started] == [
        "backend-fastapi",
        "frontend-vite",
        "live-pipeline",
    ]
    assert FakeManagedProcess.started[0].env["ASTRA_GUARD_LIVE_ENABLED"] == "1"


def test_second_launcher_exits_without_starting_services(monkeypatch):
    FakeManagedProcess.started = []
    monkeypatch.setattr(sys, "argv", ["start_all.py"])
    monkeypatch.setattr(start_all, "_acquire_instance_lock", lambda: None)

    assert start_all.main() == 1
    assert FakeManagedProcess.started == []


def test_instance_lock_blocks_another_process_and_releases():
    code = (
        "from scripts.start_all import _acquire_instance_lock; "
        "lock = _acquire_instance_lock(); "
        "raise SystemExit(0 if lock is None else 1)"
    )
    lock = start_all._acquire_instance_lock()
    assert lock is not None
    try:
        blocked = subprocess.run(
            [sys.executable, "-c", code],
            cwd=start_all.ROOT,
            capture_output=True,
            text=True,
        )
        assert blocked.returncode == 0
    finally:
        lock.close()

    released = subprocess.run(
        [sys.executable, "-c", code],
        cwd=start_all.ROOT,
        capture_output=True,
        text=True,
    )
    assert released.returncode == 1