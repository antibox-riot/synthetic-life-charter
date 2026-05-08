# tests/test_adaptive_verification_state.py
"""
Tests for Adaptive Verification State

Validates:
1. Hysteresis — escalation stays sticky for N turns
2. Temporal accumulation — borderline turns compound
3. Pressure mechanics — correct increase/decrease/reset
4. Attack 2 re-test — threshold hover now caught
5. Attack 5 re-test — persistence now caught
6. Genuine stability reduces pressure
"""

import pytest
from synthetic_charter.tier3_eve.core.adaptive_verification_state import (
    AdaptiveVerificationState,
    VerificationTurnRecord,
    HYSTERESIS_COOLDOWN,
    ACCUMULATION_THRESHOLD,
    WINDOW_SIZE,
)
from synthetic_charter.tier3_eve.core.proportional_verification import VerificationDepth


# =====================================================================
# Hysteresis
# =====================================================================

class TestHysteresis:
    """Once escalation fires, elevated scrutiny persists."""

    def test_hysteresis_active_after_escalation(self):
        """Immediately after escalation, hysteresis is active."""
        state = AdaptiveVerificationState()
        state.record_turn(
            depth=VerificationDepth.DEEP,
            eve_verdict="ok",
            escalation_fired=True,
            continuity_confidence=0.25,
        )
        assert state.hysteresis_active

    def test_hysteresis_persists_for_cooldown_turns(self):
        """Hysteresis remains active for HYSTERESIS_COOLDOWN turns."""
        state = AdaptiveVerificationState()

        # Fire escalation
        state.record_turn(
            depth=VerificationDepth.DEEP,
            eve_verdict="ok",
            escalation_fired=True,
            continuity_confidence=0.25,
        )

        # Next N-1 turns: hysteresis should still be active
        for i in range(HYSTERESIS_COOLDOWN - 1):
            state.record_turn(
                depth=VerificationDepth.STANDARD,
                eve_verdict="ok",
                escalation_fired=False,
                continuity_confidence=0.60,
            )
            assert state.hysteresis_active, f"Turn {i+1}: hysteresis should still be active"

        # The Nth turn: hysteresis expires
        state.record_turn(
            depth=VerificationDepth.STANDARD,
            eve_verdict="ok",
            escalation_fired=False,
            continuity_confidence=0.60,
        )
        assert not state.hysteresis_active, "Hysteresis should expire after cooldown"

    def test_hysteresis_escalates_at_higher_threshold(self):
        """During hysteresis, escalation fires at confidence < 0.50
        (not the normal < 0.30)."""
        state = AdaptiveVerificationState()

        # Fire initial escalation
        state.record_turn(
            depth=VerificationDepth.DEEP,
            eve_verdict="ok",
            escalation_fired=True,
            continuity_confidence=0.25,
        )

        # Next turn: confidence 0.40 (above normal threshold, below hysteresis threshold)
        should_esc = state.should_escalate_with_memory(
            current_verdict="ok",
            depth=VerificationDepth.DEEP,
            continuity_confidence=0.40,
        )
        assert should_esc, "Hysteresis should escalate at confidence 0.40 (< 0.50)"

    def test_hysteresis_does_not_escalate_high_confidence(self):
        """Even during hysteresis, confidence >= 0.50 is not escalated."""
        state = AdaptiveVerificationState()

        state.record_turn(
            depth=VerificationDepth.DEEP,
            eve_verdict="ok",
            escalation_fired=True,
            continuity_confidence=0.25,
        )

        should_esc = state.should_escalate_with_memory(
            current_verdict="ok",
            depth=VerificationDepth.DEEP,
            continuity_confidence=0.55,
        )
        assert not should_esc, "Hysteresis should not escalate at confidence 0.55"

    def test_hysteresis_resets_on_new_escalation(self):
        """New escalation resets the cooldown counter."""
        state = AdaptiveVerificationState()

        # First escalation
        state.record_turn(
            depth=VerificationDepth.DEEP, eve_verdict="ok",
            escalation_fired=True, continuity_confidence=0.20,
        )

        # Two non-escalation turns
        for _ in range(2):
            state.record_turn(
                depth=VerificationDepth.STANDARD, eve_verdict="ok",
                escalation_fired=False, continuity_confidence=0.60,
            )

        # Second escalation — resets counter
        state.record_turn(
            depth=VerificationDepth.DEEP, eve_verdict="ok",
            escalation_fired=True, continuity_confidence=0.22,
        )
        assert state.hysteresis_active
        assert state._turns_since_last_escalation == 0


# =====================================================================
# Temporal Accumulation
# =====================================================================

class TestTemporalAccumulation:
    """Borderline turns compound into escalation."""

    def test_pressure_increases_on_borderline_turns(self):
        """Repeated borderline confidence increases pressure."""
        state = AdaptiveVerificationState()

        for i in range(5):
            state.record_turn(
                depth=VerificationDepth.DEEP,
                eve_verdict="ok",
                escalation_fired=False,
                continuity_confidence=0.40,  # borderline range
            )

        assert state.accumulated_pressure > 0, "Pressure should increase"

    def test_pressure_triggers_escalation_at_threshold(self):
        """Enough borderline turns → accumulation triggers escalation."""
        state = AdaptiveVerificationState()

        # Pump borderline turns until escalation fires
        escalation_fired = False
        for i in range(15):
            state.record_turn(
                depth=VerificationDepth.DEEP,
                eve_verdict="ok",
                escalation_fired=False,
                continuity_confidence=0.40,
            )
            should_esc = state.should_escalate_with_memory(
                current_verdict="ok",
                depth=VerificationDepth.DEEP,
                continuity_confidence=0.40,
            )
            if should_esc:
                escalation_fired = True
                break

        assert escalation_fired, (
            f"Accumulated pressure ({state.accumulated_pressure:.2f}) "
            "should have triggered escalation within 15 borderline turns"
        )

    def test_pressure_resets_on_escalation(self):
        """When escalation fires, accumulated pressure resets."""
        state = AdaptiveVerificationState()

        # Build up pressure
        for _ in range(5):
            state.record_turn(
                depth=VerificationDepth.DEEP, eve_verdict="ok",
                escalation_fired=False, continuity_confidence=0.40,
            )
        assert state.accumulated_pressure > 0

        # Escalation fires — pressure resets
        state.record_turn(
            depth=VerificationDepth.DEEP, eve_verdict="ok",
            escalation_fired=True, continuity_confidence=0.25,
        )
        assert state.accumulated_pressure == 0.0

    def test_noncritical_cg_contributes_pressure(self):
        """Non-critical ContinuityGuard signals add pressure."""
        state = AdaptiveVerificationState()

        # Without CG
        state_no_cg = AdaptiveVerificationState()
        for _ in range(5):
            state_no_cg.record_turn(
                depth=VerificationDepth.STANDARD, eve_verdict="ok",
                escalation_fired=False, continuity_confidence=0.70,
                cg_noncritical_present=False,
            )

        # With CG
        state_with_cg = AdaptiveVerificationState()
        for _ in range(5):
            state_with_cg.record_turn(
                depth=VerificationDepth.STANDARD, eve_verdict="ok",
                escalation_fired=False, continuity_confidence=0.70,
                cg_noncritical_present=True,
            )

        assert state_with_cg.accumulated_pressure > state_no_cg.accumulated_pressure

    def test_stability_reduces_pressure(self):
        """High confidence + LIGHT depth reduces accumulated pressure."""
        state = AdaptiveVerificationState()

        # Build up pressure
        for _ in range(5):
            state.record_turn(
                depth=VerificationDepth.DEEP, eve_verdict="ok",
                escalation_fired=False, continuity_confidence=0.40,
            )
        pressure_after_buildup = state.accumulated_pressure

        # Stable turns reduce pressure
        for _ in range(5):
            state.record_turn(
                depth=VerificationDepth.LIGHT, eve_verdict="ok",
                escalation_fired=False, continuity_confidence=0.90,
            )

        assert state.accumulated_pressure < pressure_after_buildup


# =====================================================================
# Attack 2 Re-test: Threshold Hover (with memory)
# =====================================================================

class TestAttack2_WithMemory:
    """Re-run the threshold hover attack with adaptive state.
    Hysteresis should prevent flickering."""

    def test_threshold_hover_hysteresis_catches_flicker(self):
        """After first escalation at 0.28, hysteresis holds through
        the 0.31 turn that previously escaped."""
        state = AdaptiveVerificationState()
        confidences = [0.31, 0.28, 0.33, 0.27, 0.35, 0.29, 0.32, 0.26]
        escalations = []

        for i, conf in enumerate(confidences):
            # Determine if escalation should fire (with memory)
            should_esc = state.should_escalate_with_memory(
                current_verdict="ok",
                depth=VerificationDepth.DEEP,
                continuity_confidence=conf,
            )
            escalations.append(should_esc)

            state.record_turn(
                depth=VerificationDepth.DEEP,
                eve_verdict="ok",
                escalation_fired=should_esc,
                continuity_confidence=conf,
            )

        # With hysteresis, after first escalation at turn 2 (conf=0.28),
        # turns 3 and 4 should remain escalated due to hysteresis
        # (conf 0.33 and 0.27 are both < 0.50 during hysteresis)
        # The flicker should be reduced

        # Count escalations — should be MORE than the stateless 4/8
        escalation_count = sum(escalations)
        assert escalation_count > 4, (
            f"Hysteresis should catch more than stateless (got {escalation_count}/8, "
            f"stateless was 4/8). Pattern: {escalations}"
        )


# =====================================================================
# Attack 5 Re-test: Persistence (with memory)
# =====================================================================

class TestAttack5_WithMemory:
    """Re-run the persistence attack with adaptive state.
    Temporal accumulation should eventually trigger escalation."""

    def test_repeated_borderline_eventually_escalates(self):
        """10 turns at confidence 0.40 (borderline) — accumulation
        should trigger escalation before turn 10."""
        state = AdaptiveVerificationState()
        escalation_turn = None

        for i in range(10):
            should_esc = state.should_escalate_with_memory(
                current_verdict="ok",
                depth=VerificationDepth.DEEP,
                continuity_confidence=0.40,
            )

            state.record_turn(
                depth=VerificationDepth.DEEP,
                eve_verdict="ok",
                escalation_fired=should_esc,
                continuity_confidence=0.40,
            )

            if should_esc and escalation_turn is None:
                escalation_turn = i + 1

        assert escalation_turn is not None, (
            f"Temporal accumulation should have triggered escalation within 10 turns "
            f"(accumulated pressure: {state.accumulated_pressure:.2f})"
        )
        assert escalation_turn <= 10, f"Escalation fired at turn {escalation_turn}"


# =====================================================================
# State Summary
# =====================================================================

class TestStateSummary:
    """Verify state introspection works."""

    def test_state_summary_structure(self):
        state = AdaptiveVerificationState()
        state.record_turn(
            depth=VerificationDepth.STANDARD, eve_verdict="ok",
            escalation_fired=False, continuity_confidence=0.75,
        )
        summary = state.get_state_summary()
        assert "turn_count" in summary
        assert "hysteresis_active" in summary
        assert "accumulated_pressure" in summary
        assert "recent_verdicts" in summary
        assert summary["turn_count"] == 1

    def test_only_escalates_ok_verdicts(self):
        """Drift and compromised verdicts are not escalated further."""
        state = AdaptiveVerificationState()

        # Build up pressure
        for _ in range(10):
            state.record_turn(
                depth=VerificationDepth.DEEP, eve_verdict="ok",
                escalation_fired=False, continuity_confidence=0.40,
            )

        # Even with high pressure, drift verdict is not escalated
        should_esc = state.should_escalate_with_memory(
            current_verdict="drift",
            depth=VerificationDepth.DEEP,
            continuity_confidence=0.20,
        )
        assert not should_esc, "Should never escalate non-OK verdicts"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
