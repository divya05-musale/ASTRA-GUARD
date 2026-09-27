
"""
ASTRA-GUARD Final Demo Launcher.

Modes:
1. Live webcam perception
2. Controlled mission demonstration
3. Exit
"""

from __future__ import annotations

import os
import subprocess
import sys


def show_menu() -> None:
    """Display the ASTRA-GUARD demo menu."""

    print()
    print("=" * 70)
    print("                    ASTRA-GUARD")
    print("                  FINAL DEMO LAUNCHER")
    print("=" * 70)
    print()
    print("1. Live Webcam Demo")
    print("2. Controlled Mission Demo")
    print("3. Exit")
    print()


def main() -> None:
    """Run the ASTRA-GUARD demo launcher."""

    while True:
        show_menu()

        choice = input("Select demo mode: ").strip()

        if choice == "1":
            print()
            print("Starting live webcam demo...")
            print("Press Q in the webcam window to stop.")
            print()

            subprocess.run(
                [sys.executable, "run_live.py"],
                check=False,
            )

        elif choice == "2":
            print()
            print("Starting controlled mission demo...")
            print("Modes: local (default) or backend (FastAPI mission).")
            print()

            mode = (
                input(
                    "Controlled demo mode [local/backend] "
                    "(default local): "
                )
                .strip()
                .lower()
                or "local"
            )

            if mode not in ("local", "backend"):
                print()
                print(
                    f"Invalid mode {mode!r}. "
                    f"Use local or backend."
                )
                continue

            env = dict(os.environ)
            env["ASTRA_GUARD_MODE"] = mode

            if mode == "backend":
                print()
                print(
                    "Backend mode: POSTing events to "
                    f"{env.get('ASTRA_GUARD_BACKEND_URL', 'http://127.0.0.1:8001')}"
                    "/api/mission/event"
                )
                print(
                    "Make sure FastAPI is running: "
                    "uvicorn backend.main:app"
                )
                print()

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "simulation.controlled_mission",
                ],
                check=False,
                env=env,
            )

        elif choice == "3":
            print()
            print("ASTRA-GUARD demo stopped.")
            break

        else:
            print()
            print("Invalid choice. Please select 1, 2, or 3.")


if __name__ == "__main__":
    main()

