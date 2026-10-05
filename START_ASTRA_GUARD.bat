@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [START_ASTRA_GUARD] ERROR: Missing virtual environment at .venv\Scripts\python.exe
    echo [START_ASTRA_GUARD] Create the environment first or repair the project setup.
    pause
    exit /b 1
)

python -c "import sys; print(sys.executable)" >NUL 2>&1
if errorlevel 1 (
    echo [START_ASTRA_GUARD] ERROR: Python is not available in PATH.
    pause
    exit /b 1
)

REM --- Camera selection (verified working device on this machine) -----------
REM Index 1 is a phantom/occupied Windows capture device: MSMF reports it as
REM open but returns all-black frames. Index 0 delivers real pixels.
REM AUTO_DETECT=1 makes the pipeline skip any device that opens but emits black.
set ASTRA_GUARD_CAMERA_INDEX=0
set ASTRA_GUARD_CAMERA_BACKEND=dshow
set ASTRA_GUARD_CAMERA_AUTO_DETECT=1

python .\scripts\start_all.py --live
if errorlevel 1 (
    echo [START_ASTRA_GUARD] ERROR: ASTRA-GUARD startup failed.
    pause
    exit /b 1
)
