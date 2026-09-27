"""Decision engine: turn validation + deviation into state decisions."""

from __future__ import annotations

from typing import Any, Dict


def _humanize(value: Any) -> str:
    """Convert protocol identifiers to natural words for guidance text."""
    text = str(value or "").strip()
    if not text or text.upper() in {"NONE", "UNKNOWN"}:
        return "unknown item"
    return text.replace("_", " ").strip().lower()


class DecisionEngine:
    """Main decision component. Advances state only on CORRECT."""

    def __init__(
        self,
        state_machine,
        step_manager,
        validator,
        detector,
        rules=None,
    ) -> None:
        self.sm = state_machine
        self.steps = step_manager
        self.validator = validator
        self.detector = detector

        self._guidance = {}

        for r in (rules or []):
            key = (r.get("step_id"), r.get("result"))

            if key not in self._guidance:
                self._guidance[key] = str(
                    r.get("guidance", "")
                )

        self._deviation_guidance = {}

        for r in (rules or []):
            if r.get("result") == "DEVIATION":
                self._deviation_guidance.setdefault(
                    r.get("step_id"),
                    str(r.get("guidance", "")),
                )

    def _advance_guidance(
        self,
        step_id: str,
        fallback: str,
    ) -> str:
        return self._guidance.get(
            (step_id, "ADVANCE"),
            fallback,
        )

    def process(
        self,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:

        # ---------------------------------------------------------
        # Experiment already completed
        # ---------------------------------------------------------
        if self.sm.is_complete():
            return {
                "status": "COMPLETED",
                "step_id": self.sm.current_step_id(),
                "next_step_id": None,
                "deviation_type": None,
                "guidance": "Experiment completed successfully.",
            }

        # ---------------------------------------------------------
        # Current protocol step
        # ---------------------------------------------------------
        step = self.sm.current_step()

        sid = str(step.get("step_id"))
        exp_act = str(step.get("activity"))
        exp_obj = str(step.get("expected_object"))

        det_act = event.get("activity")
        det_obj = event.get("object")

        # ---------------------------------------------------------
        # Validate perception against current protocol step
        # ---------------------------------------------------------
        validation = self.validator.validate(
            event,
            sid,
        )

        reason = validation.get("reason")

        if reason in {"WRONG_ZONE", "BOX_NOT_FULLY_IN_ZONE"}:
            return {
                "status": "DEVIATION",
                "step_id": sid,
                "next_step_id": sid,
                "deviation_type": reason,
                "expected_activity": exp_act,
                "expected_object": exp_obj,
                "detected_activity": det_act,
                "detected_object": det_obj,
                "guidance": validation.get("guidance") or (
                    f"The object does not satisfy the configured placement for {sid}. "
                    f"Expected {_humanize(exp_obj)}."
                ),
            }

        # ---------------------------------------------------------
        # LOW CONFIDENCE + clearly different object
        #
        # This handles the live perception case:
        #
        # Expected object:
        #     experiment_container
        #
        # Detected object:
        #     biological_sample
        #
        # Without this special case, LOW_CONFIDENCE would hide
        # the actual protocol-object mismatch.
        #
        # IMPORTANT:
        # This is ONLY applied when the validator says
        # LOW_CONFIDENCE. Other deviation reasons must continue
        # through the normal deviation detector.
        # ---------------------------------------------------------
        if (
            reason == "LOW_CONFIDENCE"
            and det_obj is not None
            and str(det_obj) != exp_obj
        ):
            g = (
                f"Wrong action detected. {_humanize(det_obj)} is not expected. "
                f"Please use {_humanize(exp_obj)}."
            )

            return {
                "status": "DEVIATION",
                "step_id": sid,
                "next_step_id": sid,
                "deviation_type": "WRONG_OBJECT",
                "expected_activity": exp_act,
                "expected_object": exp_obj,
                "detected_activity": det_act,
                "detected_object": det_obj,
                "guidance": g,
            }

        # ---------------------------------------------------------
        # Low confidence
        # ---------------------------------------------------------
        if reason == "LOW_CONFIDENCE":
            g = (
                self._guidance.get(
                    (sid, "UNCERTAIN")
                )
                or (
                    "Detection confidence is low. "
                    "Please repeat or hold the action "
                    "for verification."
                )
            )

            return {
                "status": "UNCERTAIN",
                "step_id": sid,
                "next_step_id": sid,
                "deviation_type": "LOW_CONFIDENCE",
                "expected_activity": exp_act,
                "expected_object": exp_obj,
                "detected_activity": det_act,
                "detected_object": det_obj,
                "guidance": g,
            }

        # ---------------------------------------------------------
        # Unknown activity
        # ---------------------------------------------------------
        if reason == "UNKNOWN_ACTION":
            return {
                "status": "DEVIATION",
                "step_id": sid,
                "next_step_id": sid,
                "deviation_type": "UNKNOWN_ACTION",
                "expected_activity": exp_act,
                "expected_object": exp_obj,
                "detected_activity": det_act,
                "detected_object": det_obj,
                "guidance": (
                    f"Unknown object detected. "
                    f"Please use {_humanize(exp_obj)}."
                ),
            }

        # ---------------------------------------------------------
        # Valid protocol event
        # ---------------------------------------------------------
        if validation.get("valid"):

            info = self.detector.detect(
                event,
                sid,
            )

            nxt = self.sm.next_step()

            nxt_id = (
                str(nxt.get("step_id"))
                if nxt
                else None
            )

            # -----------------------------------------------------
            # Final step completed
            # -----------------------------------------------------
            if nxt is None:

                self.sm.complete_current()

                g = self._advance_guidance(
                    sid,
                    "Experiment completed successfully.",
                )

                out = {
                    "status": "COMPLETED",
                    "step_id": sid,
                    "next_step_id": None,
                    "deviation_type": None,
                    "guidance": g,
                }

                if info.get("recovered"):
                    out["deviation_type"] = "RECOVERED"

                return out

            # -----------------------------------------------------
            # Advance to next protocol step
            # -----------------------------------------------------
            g = self._advance_guidance(
                sid,
                f"Step {sid} completed. Proceed.",
            )

            self.sm.advance()

            out = {
                "status": "CORRECT",
                "step_id": sid,
                "next_step_id": nxt_id,
                "deviation_type": None,
                "guidance": g,
            }

            if info.get("recovered"):
                out["deviation_type"] = "RECOVERED"

            return out

        # ---------------------------------------------------------
        # General deviation handling
        # ---------------------------------------------------------
        info = self.detector.detect(
            event,
            sid,
        )

        dtype = (
            info.get("deviation_type")
            or reason
            or "WRONG_SEQUENCE"
        )

        if dtype == "WRONG_OBJECT":

            g = (
                f"Wrong action detected. {_humanize(det_obj)} is not expected. "
                f"Please use {_humanize(exp_obj)}."
            )

        elif dtype == "WRONG_SEQUENCE":

            g = (
                f"Wrong sequence detected. "
                f"Please complete {sid} before continuing."
            )

        elif dtype == "SKIPPED_STEP":

            g = (
                f"Required step skipped. "
                f"Please complete {sid} before continuing."
            )

        elif dtype == "REPEATED_STEP":
            nxt = self.sm.next_step()
            nxt_id = str(nxt.get("step_id")) if nxt else sid
            g = (
                f"This step has already been completed. "
                f"Please continue with {nxt_id}."
            )

        elif dtype == "PREMATURE_ACTION":
            g = (
                f"Action performed too early. "
                f"Please complete {sid} first."
            )

        elif dtype == "LOW_CONFIDENCE":

            g = "Action uncertain. Please hold the object steady and try again."

        elif dtype == "UNKNOWN_ACTION":
            if det_obj and str(det_obj).upper() not in {"NONE", "UNKNOWN"}:
                g = (
                    f"Unknown object detected. "
                    f"Please use {_humanize(exp_obj)}."
                )
            else:
                g = (
                    f"Unknown action detected. "
                    f"Please use {_humanize(exp_obj)}."
                )

        else:

            g = (
                f"Deviation ({dtype}). "
                f"Expected {_humanize(exp_act)} with {_humanize(exp_obj)}."
            )

        return {
            "status": "DEVIATION",
            "step_id": sid,
            "next_step_id": sid,
            "deviation_type": dtype,
            "expected_activity": exp_act,
            "expected_object": exp_obj,
            "detected_activity": det_act,
            "detected_object": det_obj,
            "guidance": g,
        }