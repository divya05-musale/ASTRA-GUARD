import subprocess, sys
base = "c:/Users/HP/Desktop/ASTRA-GUARD"
code = ("from ultralytics import YOLO; "
        "print('has YOLO:', True); "
        "import mediapipe as mp; print('mp hands:', hasattr(mp.solutions, 'hands')); "
        "h = mp.solutions.hands.Hands(static_image_mode=True, max_num_hands=1); "
        "print('hands init ok'); h.close(); "
        "import numpy as np; "
        "img = np.zeros((480,640,3), dtype=np.uint8); "
        "res = h.__class__; print('done')")
r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=base)
open(base + "/_api2.txt", "w").write("OUT:\n" + r.stdout[-3000:]
                                     + "\nERR:\n" + r.stderr[-3000:]
                                     + f"\nRC={r.returncode}\n")
print("done2")
