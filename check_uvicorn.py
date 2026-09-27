import subprocess
import sys
import time
import urllib.request

PORT = 8124
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(PORT)],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT,
)
try:
    ok = False
    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{PORT}/api/health", timeout=5
            ) as r:
                print("HEALTH:", r.status, r.read().decode(), flush=True)
                ok = True
                break
        except Exception as e:
            print("waiting...", type(e).__name__, flush=True)
    if not ok:
        raise SystemExit("SERVER-DID-NOT-START")
    for path in [
        "/api/mission/status",
        "/api/mission/progress",
        "/api/mission/summary",
        "/api/events?limit=2",
        "/api/mission",
    ]:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{PORT}{path}", timeout=5
        ) as r:
            body = r.read().decode()
            print(path, r.status, body[:400], flush=True)
    print("UVICORN-OK", flush=True)
finally:
    proc.terminate()

