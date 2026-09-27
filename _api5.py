import subprocess, sys
base = "c:/Users/HP/Desktop/ASTRA-GUARD"
code = ("from mediapipe.tasks import python as P; print(dir(P)); "
        "from mediapipe.tasks.python import vision; "
        "print([x for x in dir(vision) if 'and' in x.lower()]); ")
r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=base)
open(base + "/_api5.txt", "w").write("OUT:\n" + r.stdout[-4000:]
                                     + "\nERR:\n" + r.stderr[-4000:]
                                     + f"\nRC={r.returncode}\n")
print("done5")
