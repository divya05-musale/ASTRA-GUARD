import subprocess, sys
base = "c:/Users/HP/Desktop/ASTRA-GUARD"
r = subprocess.run([sys.executable, "-m", "pip", "install", "ultralytics", "mediapipe"],
                   capture_output=True, text=True, cwd=base, timeout=600)
open(base + "/_install_p6.txt", "w").write("STDOUT:\n" + r.stdout[-6000:]
                                           + "\nSTDERR:\n" + r.stderr[-6000:]
                                           + f"\nRC={r.returncode}\n")
print("rc=", r.returncode)
