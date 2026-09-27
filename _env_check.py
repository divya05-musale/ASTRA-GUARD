import subprocess, sys
base = "c:/Users/HP/Desktop/ASTRA-GUARD"
def sh(args):
    r = subprocess.run(args, capture_output=True, text=True, cwd=base)
    return f"$ {' '.join(args)}\nRC={r.returncode}\nOUT:\n{r.stdout[-4000:]}\nERR:\n{r.stderr[-4000:]}\n"
out = ""
out += sh([sys.executable, "--version"])
out += sh([sys.executable, "-m", "pip", "show", "ultralytics"])
out += sh([sys.executable, "-m", "pip", "show", "mediapipe"])
out += sh([sys.executable, "-m", "pip", "show", "opencv-python"])
out += sh([sys.executable, "-m", "pip", "show", "numpy"])
open(base + "/_env_check.txt", "w").write(out)
print("done")
