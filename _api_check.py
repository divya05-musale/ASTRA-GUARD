import subprocess, sys
base = "c:/Users/HP/Desktop/ASTRA-GUARD"
out = ""
for pkg in ["ultralytics", "mediapipe", "torch"]:
    r = subprocess.run([sys.executable, "-m", "pip", "show", pkg],
                       capture_output=True, text=True, cwd=base)
    out += f"== {pkg}: RC={r.returncode}\n{r.stdout[-1500:]}\n"
r = subprocess.run([sys.executable, "-c",
                    "import ultralytics, mediapipe, cv2; "
                    "print('ultra', ultralytics.__version__); "
                    "print('mp', mediapipe.__version__); "
                    "print('cv', cv2.__version__)"],
                   capture_output=True, text=True, cwd=base)
out += f"== import: RC={r.returncode}\nOUT:{r.stdout[-2000:]}\nERR:{r.stderr[-2000:]}\n"
open(base + "/_api_check.txt", "w").write(out)
print("done")
