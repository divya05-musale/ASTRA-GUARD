import subprocess, sys
base = "c:/Users/HP/Desktop/ASTRA-GUARD"
code = ("import mediapipe as mp; print(dir(mp)); "
        "import importlib; "
        "m = importlib.import_module('mediapipe.python.solutions.hands'); "
        "print('hands mod ok:', m); ")
r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=base)
open(base + "/_api3.txt", "w").write("OUT:\n" + r.stdout[-4000:]
                                     + "\nERR:\n" + r.stderr[-4000:]
                                     + f"\nRC={r.returncode}\n")
print("done3")
