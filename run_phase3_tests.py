import subprocess, sys
r = subprocess.run([sys.executable, "-m", "pytest", "tests/mission", "-v", "--tb=short"],
                   capture_output=True, text=True, cwd="c:/Users/HP/Desktop/ASTRA-GUARD")
open("c:/Users/HP/Desktop/ASTRA-GUARD/phase3_pytest.txt", "w").write("STDOUT:\n" + r.stdout + "\nSTDERR:\n" + r.stderr + f"\nRC={r.returncode}\n")
print("wrote file rc=", r.returncode)
