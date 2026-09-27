# ASTRA-GUARD Deviation Rules

## 1. Overview

ASTRA-GUARD validates observed experimental events against the expected mission protocol.

When an observation does not satisfy the expected protocol condition, the system identifies a deviation or requests verification.

The main decision outcomes are:

```text
CORRECT
DEVIATION
UNCERTAIN
```

---

## 2. Validation Context

Every observation is evaluated using the current mission state.

The validation context contains:

```text
Current Step
Expected Activity
Expected Object
Detected Activity
Detected Object
Confidence
Sequence State
```

Conceptually:

```text
Observed Event
      +
Mission State
      +
Protocol Rules
      ↓
Validation
      ↓
Decision
```

---

## 3. CORRECT Condition

An observation is considered correct when it satisfies the expected protocol conditions.

Conceptually:

```text
Detected Activity = Expected Activity
          AND
Detected Object = Expected Object
          AND
Sequence is Valid
          ↓
       CORRECT
```

When a valid event is accepted, the mission state can advance to the next protocol step.

---

## 4. DEVIATION Condition

A deviation occurs when the observed event conflicts with the expected protocol state.

Examples include:

* Wrong object
* Wrong sequence
* Skipped step
* Unknown action
* Premature action

The deviation detector identifies the reason where possible.

---

# 5. Wrong Object

## Definition

A `WRONG_OBJECT` deviation occurs when the detected protocol object does not match the object expected for the current step.

Example:

```text
Current Step:
S002

Expected Object:
biological_sample

Detected Object:
experiment_controller
```

Result:

```text
DEVIATION
WRONG_OBJECT
```

Example guidance:

```text
Wrong object detected.
Please select the biological sample.
```

---

# 6. Wrong Sequence

## Definition

A `WRONG_SEQUENCE` deviation occurs when an activity is detected outside its expected mission sequence.

Example:

```text
Current Step:
S002

Expected Activity:
RETRIEVE_SAMPLE

Detected Activity:
START_EXPERIMENT
```

The activity belongs to a later protocol stage.

Result:

```text
DEVIATION
WRONG_SEQUENCE
```

The system should not advance the mission state for an invalid sequence.

---

# 7. Skipped Step

## Definition

A `SKIPPED_STEP` deviation represents a protocol progression where an expected mission step has been bypassed.

Example:

```text
Expected:
S002 → S003

Observed progression:
S002 → S004
```

The missing step is:

```text
S003
```

The system can identify the skipped protocol stage and request recovery.

---

# 8. Unknown Action

## Definition

An `UNKNOWN_ACTION` deviation occurs when the observed event cannot be mapped to a valid protocol activity.

Example:

```text
Detected Activity:
UNKNOWN_ACTION
```

If the current protocol expects a known activity, the observation cannot be accepted as a valid protocol action.

Result:

```text
DEVIATION
UNKNOWN_ACTION
```

---

# 9. Low Confidence

## Definition

`LOW_CONFIDENCE` represents insufficient perception confidence.

This condition requires special handling.

Conceptually:

```text
Detection Confidence
        ↓
Below Reliable Threshold
        ↓
Verification Required
```

The normal result is:

```text
UNCERTAIN
LOW_CONFIDENCE
```

Example guidance:

```text
Detection confidence is low.
Please repeat or hold the action for verification.
```

---

# 10. Wrong Object with Low Confidence

The live perception pipeline contains an additional safety-oriented case.

If:

```text
Detected Object exists
AND
Detected Object != Expected Object
AND
Detection confidence is low
```

the system can still identify the observation as a wrong-object deviation rather than treating it only as uncertainty.

Example:

```text
Expected Object:
experiment_container

Detected Object:
experiment_controller

Confidence:
0.57
```

Result:

```text
DEVIATION
WRONG_OBJECT
```

This allows an identifiable object mismatch to remain visible to the operator even when confidence is not high.

---

# 11. Decision Priority

The Decision Engine evaluates protocol conditions in a controlled order.

A simplified representation is:

```text
Completed?
    |
    +-- Yes → COMPLETED
    |
    No
    ↓
Validate Current Event
    |
    +-- Invalid Action → DEVIATION
    |
    ↓
Check Confidence
    |
    +-- Low Confidence + Identifiable Wrong Object
    |          ↓
    |     WRONG_OBJECT
    |
    +-- Low Confidence
    |          ↓
    |      UNCERTAIN
    |
    ↓
Check Expected Conditions
    |
    +-- Valid → CORRECT
    |
    +-- Invalid → DEVIATION
```

---

# 12. Deviation Categories

The prototype uses the following deviation concepts:

| Deviation        | Meaning                                        |
| ---------------- | ---------------------------------------------- |
| `WRONG_OBJECT`   | Detected object does not match expected object |
| `WRONG_SEQUENCE` | Activity occurs in an invalid sequence         |
| `SKIPPED_STEP`   | Expected protocol step was bypassed            |
| `UNKNOWN_ACTION` | Activity cannot be mapped to the protocol      |
| `LOW_CONFIDENCE` | Perception confidence is insufficient          |

---

# 13. Guidance Rules

ASTRA-GUARD converts decision results into guidance.

### Correct

```text
Equipment check completed.
Proceed to retrieve the sample.
```

### Wrong Object

```text
Wrong object detected.
Expected biological_sample.
```

### Low Confidence

```text
Detection confidence is low.
Please repeat or hold the action for verification.
```

The guidance is intended to make the system output understandable to the operator.

---

# 14. Example Rule Scenarios

## Scenario A — Correct

```text
Current Step:
S001

Expected:
CHECK_EQUIPMENT
experiment_container

Detected:
CHECK_EQUIPMENT
experiment_container
```

Result:

```text
CORRECT
```

---

## Scenario B — Wrong Object

```text
Current Step:
S002

Expected:
RETRIEVE_SAMPLE
biological_sample

Detected:
RETRIEVE_SAMPLE
experiment_controller
```

Result:

```text
DEVIATION
WRONG_OBJECT
```

---

## Scenario C — Wrong Sequence

```text
Current Step:
S002

Expected:
RETRIEVE_SAMPLE

Detected:
START_EXPERIMENT
```

Result:

```text
DEVIATION
WRONG_SEQUENCE
```

---

## Scenario D — Low Confidence

```text
Current Step:
S002

Expected:
RETRIEVE_SAMPLE

Confidence:
Low
```

Result:

```text
UNCERTAIN
LOW_CONFIDENCE
```

---

## Scenario E — Unknown Action

```text
Current Step:
S002

Detected Activity:
UNKNOWN_ACTION
```

Result:

```text
DEVIATION
UNKNOWN_ACTION
```

---

# 15. State Preservation

A protocol deviation should not automatically advance the mission state.

For example:

```text
Current Step:
S002

Wrong Object
    ↓
DEVIATION
    ↓
Mission remains at S002
```

The operator can then correct the action and attempt the expected step again.

This supports recovery rather than silently progressing after an invalid observation.

---

# 16. Recovery Flow

The general recovery flow is:

```text
Protocol Violation
       ↓
Deviation Classification
       ↓
Guidance Message
       ↓
Operator Correction
       ↓
Repeat Current Step
       ↓
Validation
       ↓
CORRECT
       ↓
Advance Mission
```

This provides a basic closed-loop monitoring behavior.

---

# 17. Controlled Demonstration Rules

The controlled demo intentionally demonstrates three representative outcomes:

```text
Expected Action
      ↓
   CORRECT
```

```text
Wrong Object
      ↓
  DEVIATION
```

```text
Low Confidence
      ↓
  UNCERTAIN
```

These scenarios provide deterministic demonstrations of the decision engine.

---

# 18. Rule Configuration

The protocol's detailed rules are stored in:

```text
experiments/EXP001_TARDIGRADE/rules.yaml
```

The Protocol Loader loads and validates the rule configuration together with the other experiment files.

---

# 19. Deterministic Decision Model

The current ASTRA-GUARD decision process is deterministic.

It does not depend on:

* An LLM
* Generative AI
* External cloud reasoning
* Human subjective interpretation during execution

The decision is based on explicit protocol state, perception information, confidence, and configured validation logic.

---

# 20. Current Prototype Boundary

The deviation system validates the information available from the current perception pipeline.

Because the prototype uses a generic YOLO model and deterministic mapping, the quality of the final decision depends on the quality and relevance of the detected perception information.

The current prototype should therefore be understood as a protocol-validation demonstration rather than a certified operational safety system.

---

# 21. Summary

ASTRA-GUARD converts perception mismatches into structured protocol outcomes.

The core logic is:

```text
Observation
    ↓
Protocol Comparison
    ↓
Validation
    ↓
Deviation Detection
    ↓
Decision
    ↓
Guidance / Recovery
```

This allows the system to identify protocol violations while maintaining mission state and providing actionable feedback.
