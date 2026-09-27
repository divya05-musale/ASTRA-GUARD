"""
ASTRA-GUARD Phase 8.2 - Presentation Demo.

Demonstrates the three key decision outcomes:

1. CORRECT
2. DEVIATION
3. UNCERTAIN

All scenarios use the existing ASTRA-GUARD
protocol simulation and decision engine.
"""

from __future__ import annotations

from simulation.simulator import SimulationRunner


EXP = "experiments/EXP001_TARDIGRADE"


def separator() -> None:
    print("-" * 70)


def show_scenario(
    title: str,
    scenario_name: str,
    focus_event: int,
) -> None:
    """Run one scenario and display its key decision."""

    runner = SimulationRunner(EXP)
    result = runner.run_scenario(scenario_name)

    records = result["runs"][0]["outcome"]["records"]

    record = records[focus_event]
    decision = record["decision"]

    print()
    separator()
    print(title)
    separator()

    print(f"Step:      {decision.get('step_id')}")
    print(f"Status:    {decision.get('status')}")
    print(f"Deviation: {decision.get('deviation_type') or 'NONE'}")

    guidance = decision.get("guidance")

    if guidance:
        print(f"Guidance:  {guidance}")

    print()


def main() -> None:
    print()
    print("=" * 70)
    print("                    ASTRA-GUARD")
    print("               PROTOCOL DECISION DEMO")
    print("=" * 70)

    print()
    print("Protocol: EXP001 - TARDIGRADE")
    print("Environment: Microgravity")
    print("Mode: Controlled Demonstration")

    # ---------------------------------------------------------
    # 1. CORRECT
    # ---------------------------------------------------------
    show_scenario(
        "1. CORRECT — Expected Protocol Action",
        "correct_sequence",
        0,
    )

    # ---------------------------------------------------------
    # 2. DEVIATION
    # ---------------------------------------------------------
    show_scenario(
        "2. DEVIATION — Wrong Object Detected",
        "wrong_object",
        1,
    )

    # ---------------------------------------------------------
    # 3. UNCERTAIN
    # ---------------------------------------------------------
    show_scenario(
        "3. UNCERTAIN — Low Detection Confidence",
        "low_confidence",
        1,
    )

    print("=" * 70)
    print("                    DEMO SUMMARY")
    print("=" * 70)
    print()
    print("CORRECT   → Protocol action accepted")
    print("DEVIATION → Protocol violation detected")
    print("UNCERTAIN → Verification required")
    print()
    print("Decision Engine: OPERATIONAL")
    print("Protocol Validation: OPERATIONAL")
    print("Recovery Handling: OPERATIONAL")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()