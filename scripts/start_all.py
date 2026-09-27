"""ASTRA-GUARD orchestrator: starts backend, frontend, and optional live pipeline.

Usage examples
--------------
# Start everything (backend + frontend)
python scripts/start_all.py

# Also launch the real-time perception pipeline with webcam
python scripts/start_all.py --live

# Only backend + frontend (no live pipeline)
python scripts/start_all.py --no-live

# Custom ports / backend URL
set ASTRA_GUARD_PORT=8001
set VITE_PORT=5173
python scripts/start_all.py

Terminate with Ctrl+C. All subprocesses are cleaned up on exit.
"""
from __future__ import annotations

import argparse
import atexit
import hashlib
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
BACKEND_PORT = int(os.environ.get("ASTRA_GUARD_PORT", "8001"))
FRONTEND_PORT = int(os.environ.get("VITE_PORT", "5173"))
BACKEND_URL = os.environ.get("ASTRA_GUARD_BACKEND_URL", f"http://127.0.0.1:{BACKEND_PORT}")


def _acquire_instance_lock():
    project_key = hashlib.sha256(str(ROOT.resolve()).casefold().encode()).hexdigest()[:16]
    lock_path = Path(tempfile.gettempdir()) / f"astra-guard-{project_key}.lock"
    handle = lock_path.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


class ManagedProcess:
    def __init__(self, name: str, args: List[str], cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None) -> None:
        self.name = name
        self.args = args
        self.cwd = Path(cwd) if cwd else ROOT
        merged = os.environ.copy()
        if env:
            merged.update(env)
        self.env = merged
        self.proc: Optional[subprocess.Popen] = None

    def start(self) -> None:
        print(f"[start_all] Starting {self.name}:\n    {' '.join(self.args)}  (cwd={self.cwd})")
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        self.proc = subprocess.Popen(
            self.args,
            cwd=str(self.cwd),
            env=self.env,
            stdout=sys.stdout,
            stderr=sys.stderr,
            creationflags=creationflags,
        )

    def stop(self, timeout: float = 6.0) -> None:
        if self.proc is None:
            return
        if self.proc.poll() is not None:
            print(f"[start_all] {self.name} already exited (code={self.proc.returncode}).")
            self.proc = None
            return
        print(f"[start_all] Stopping {self.name} (PID {self.proc.pid})...")
        try:
            if sys.platform == "win32":
                try:
                    self.proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
                except Exception:
                    self.proc.terminate()
            else:
                self.proc.terminate()
            try:
                self.proc.wait(timeout=timeout)
                print(f"[start_all] {self.name} stopped (code={self.proc.returncode}).")
                self.proc = None
                return
            except subprocess.TimeoutExpired:
                print(f"[start_all] {self.name} did not exit in time. Killing.")
                self.proc.kill()
                self.proc.wait(timeout=2.0)
        except Exception as exc:
            print(f"[start_all] Error stopping {self.name}: {exc}")
        finally:
            self.proc = None


_MANAGED: List[ManagedProcess] = []


def _shutdown() -> None:
    print("\n[start_all] Shutting down all processes...")
    for p in reversed(_MANAGED):
        p.stop()
    print("[start_all] Done.")


atexit.register(_shutdown)


def _cmd_python(script: str) -> List[str]:
    return [sys.executable, script]


def _wait_for_http(url: str, timeout: float = 45.0) -> bool:
    import urllib.request
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if 200 <= int(resp.status) < 500:
                    return True
        except Exception:
            time.sleep(0.75)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="ASTRA-GUARD orchestrator.")
    parser.add_argument("--live", dest="live", action="store_true", default=False,
                        help="Also launch the real webcam perception pipeline (run_live.py) in backend mode.")
    parser.add_argument("--no-live", dest="live", action="store_false", help="Do not launch the live pipeline (default).")
    parser.add_argument("--no-frontend", dest="frontend", action="store_false", default=True, help="Skip Vite dev server.")
    parser.add_argument("--no-backend", dest="backend", action="store_false", default=True, help="Skip FastAPI backend.")
    parser.add_argument("--wait", dest="wait", action="store_true", default=True, help="Wait after starting all services.")
    args = parser.parse_args()

    instance_lock = _acquire_instance_lock()
    if instance_lock is None:
        print("[start_all] Another ASTRA-GUARD launcher is already running for this project.")
        return 1
    atexit.register(instance_lock.close)

    print("=" * 68)
    print("  ASTRA-GUARD ORCHESTRATOR")
    print("=" * 68)
    print(f"  Project root : {ROOT}")
    print(f"  Backend URL   : {BACKEND_URL}")
    print(f"  Frontend URL  : http://127.0.0.1:{FRONTEND_PORT}")
    print(f"  Live pipeline : {'yes' if args.live else 'no'}")
    print("=" * 68)

    if args.backend:
        backend_env = {
            "ASTRA_GUARD_MODE": "backend",
            "ASTRA_GUARD_LIVE_ENABLED": "1" if args.live else "0",
            "PYTHONPATH": str(ROOT),
            "ASTRA_GUARD_PORT": str(BACKEND_PORT),
        }
        backend_cmd = [
            sys.executable, "-m", "uvicorn",
            "backend.main:app",
            "--host", "127.0.0.1",
            "--port", str(BACKEND_PORT),
            "--reload",
        ]
        backend = ManagedProcess("backend-fastapi", backend_cmd, cwd=ROOT, env=backend_env)
        backend.start()
        _MANAGED.append(backend)
        health_url = f"{BACKEND_URL.rstrip('/')}/api/health"
        print(f"[start_all] Waiting for backend health endpoint at {health_url} ...")
        if _wait_for_http(health_url):
            print("[start_all] Backend is UP.")
        else:
            print("[start_all] WARNING: Backend did not become healthy within timeout. Continuing anyway.")

    if args.frontend:
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        frontend = ManagedProcess(
            "frontend-vite",
            [npm_cmd, "run", "dev"],
            cwd=FRONTEND_DIR,
            env={"VITE_PORT": str(FRONTEND_PORT), "PYTHONPATH": str(ROOT)},
        )
        frontend.start()
        _MANAGED.append(frontend)

    if args.live:
        live_env = {
            "ASTRA_GUARD_MODE": "backend",
            "ASTRA_GUARD_BACKEND_URL": BACKEND_URL,
            "PYTHONPATH": str(ROOT),
        }
        live = ManagedProcess(
            "live-pipeline",
            _cmd_python(str(ROOT / "run_live.py")),
            cwd=ROOT,
            env=live_env,
        )
        # Give the backend a moment to be ready.
        time.sleep(2.0)
        live.start()
        _MANAGED.append(live)

    print("\n" + "=" * 68)
    print("  All requested services launched.")
    print(f"  Dashboard: http://127.0.0.1:{FRONTEND_PORT}")
    print(f"  API docs: {BACKEND_URL.rstrip('/')}/docs")
    print("  Press Ctrl+C to stop everything.")
    print("=" * 68)

    if not args.wait:
        return 0

    try:
        while True:
            dead = [p for p in _MANAGED if p.proc is not None and p.proc.poll() is not None]
            if dead:
                for p in dead:
                    code = p.proc.returncode if p.proc else None
                    print(f"[start_all] {p.name} exited with code {code}.")
                    p.proc = None
            if all(p.proc is None for p in _MANAGED):
                print("[start_all] All services have exited.")
                break
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[start_all] Ctrl+C received.")
    finally:
        _shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
