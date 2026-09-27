import subprocess, sys
base = "c:/Users/HP/Desktop/ASTRA-GUARD"
code = ("import mediapipe as mp; print('ver', mp.__version__); "
        "from mediapipe.tasks import python as mp_python; print('tasks ok'); "
        "print([x for x in dir(mp_python) if 'hand' in x.lower()]); ")
r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=base)
open(base + "/_api4.txt", "w").write("OUT:\n" + r.stdout[-4000:]
                                     + "\nERR:\n" + r.stderr[-4000:]
                                     + f"\nRC={r.returncode}\n")
print("done4")
