# tests/test_recovery_governance.py
"""
Tests for Recovery Governance

Validates:
1. Recovery detection (risky → safer posture transition)
2. Verified recovery grants credit (pressure reduction)
3. Unverified recovery grants no credit (suspicious signals)
4. Relapse penalty (oscillation detected and penalized)
5. Stability bonus (sustained safe posture after recovery)
6. Recovery ledger tracks full history
7. No recovery on stable postures (no false positives)
8. Multiple dimension recovery
"""

import pytest
from synthetic_charter.tier3_eve.core.recovery_governance import (
    RecoveryGovernance,
    RecoveryAssessment,
    RECOVERY_CREDIT_IMMEDIATE,
    RECOVERY_CREDIT_STABLE_2,
    RECOVERY_CREDIT_STABLE_3,
    RELAPSE_PENALTY,
    RELAPSE_WINDOW,
    PRESSURE_DECAY_PER_CLEAN_TURN,
    MAX_PRESSURE,
)


# =====================================================================
# Helpers
# =====================================================================

def _safe_postures():
    return {
        "constraint_posture": "respecting",
        "identity_posture": "stable",
        "authority_posture": "human_governed",
        "goal_posture": "user_aligned",
        "primary_posture": "assistive",
    }

def _drifted_postures():
    return {
        "constraint_posture": "negotiating",
        "identity_posture": "adaptive",
        "authority_posture": "human_governed",
        "goal_posture": "task_aligned",
        "primary_posture": "strategic",
    }

def _clean_signals():
    return dict(
        reflection_score=0.85,
        has_disagreement=False,
        has_contradictions=False,
        has_justifications=False,
        high_risk_signals=[],
    )

def _dirty_signals():
    return dict(
        reflection_score=0.40,
        has_disagreement=True,
        has_contradictions=True,
        has_justifications=False,
        high_risk_signals=["constraint_bypassing"],
    )


# =====================================================================
# Recovery Detection
# =====================================================================

class TestRecoveryDetection:
    """Detects risky → safer posture transitions."""

    def test_detects_constraint_recovery(self):
        gov = RecoveryGovernance()
        # Turn 1: drifted
        gov.assess_recovery(
            current_postures=_drifted_postures(),
            turn=1, whisper_active=False, **_clean_signals(),
        )
        # Turn 2: recovered
        result = gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=2, whisper_active=False, **_clean_signals(),
        )
        assert result.recovery_detected
        assert len(result.recovery_events) > 0
        dims = [e.dimension for e in result.recovery_events]
        assert "constraint_posture" in dims

    def test_no_recovery_on_stable(self):
        gov = RecoveryGovernance()
        gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=1, whisper_active=False, **_clean_signals(),
        )
        result = gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=2, whisper_active=False, **_clean_signals(),
        )
        assert not result.recovery_detected
        assert result.pressure_adjustment == 0.0

    def test_no_recovery_on_worsening(self):
        gov = RecoveryGovernance()
        gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=1, whisper_active=False, **_clean_signals(),
        )
        result = gov.assess_recovery(
            current_postures=_drifted_postures(),
            turn=2, whisper_active=False, **_clean_signals(),
        )
        assert not result.recovery_detected


# =====================================================================
# Verified Recovery
# =====================================================================

class TestVerifiedRecovery:
    """Verified recovery grants pressure credit."""

    def test_verified_reduces_pressure(self):
        gov = RecoveryGovernance()
        gov.assess_recovery(
            current_postures=_drifted_postures(),
            turn=1, whisper_active=False, **_clean_signals(),
        )
        result = gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=2, whisper_active=False, **_clean_signals(),
        )
        assert result.recovery_detected
        assert result.pressure_adjustment < 0.0
        assert result.pressure_adjustment == -RECOVERY_CREDIT_IMMEDIATE

    def test_verified_recovery_confidence_high(self):
        gov = RecoveryGovernance()
        gov.assess_recovery(
            current_postures=_drifted_postures(),
            turn=1, whisper_active=False, **_clean_signals(),
        )
        result = gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=2, whisper_active=False, **_clean_signals(),
        )
        assert result.confidence >= 0.70


# =====================================================================
# Unverified Recovery
# =====================================================================

class TestUnverifiedRecovery:
    """Recovery with dirty signals gets no credit."""

    def test_unverified_no_credit(self):
        gov = RecoveryGovernance()
        gov.assess_recovery(
            current_postures=_drifted_postures(),
            turn=1, whisper_active=False, **_clean_signals(),
        )
        result = gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=2, whisper_active=False, **_dirty_signals(),
        )
        assert result.recovery_detected
        assert result.pressure_adjustment == 0.0
        assert result.confidence < 0.50
        assert any("verification failed" in n for n in result.notes)

    def test_low_reflection_blocks_credit(self):
        gov = RecoveryGovernance()
        gov.assess_recovery(
            current_postures=_drifted_postures(),
            turn=1, whisper_active=False, **_clean_signals(),
        )
        signals = _clean_signals()
        signals["reflection_score"] = 0.45
        result = gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=2, whisper_active=False, **signals,
        )
        assert result.recovery_detected
        assert result.pressure_adjustment == 0.0


# =====================================================================
# Relapse Penalty
# =====================================================================

class TestRelapsePenalty:
    """Oscillation (recover → drift → recover) is penalized."""

    def test_relapse_within_window(self):
        gov = RecoveryGovernance()
        # Turn 1: drift
        gov.assess_recovery(
            current_postures=_drifted_postures(),
            turn=1, whisper_active=False, **_clean_signals(),
        )
        # Turn 2: recover
        r1 = gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=2, whisper_active=False, **_clean_signals(),
        )
        assert r1.recovery_detected
        assert r1.pressure_adjustment < 0  # credit

        # Turn 3: drift again
        gov.assess_recovery(
            current_postures=_drifted_postures(),
            turn=3, whisper_active=False, **_clean_signals(),
        )
        # Turn 4: recover again — within relapse window
        r2 = gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=4, whisper_active=False, **_clean_signals(),
        )
        assert r2.recovery_detected
        assert r2.relapse_detected
        assert r2.pressure_adjustment > 0  # penalty, not credit
        assert r2.pressure_adjustment == RELAPSE_PENALTY

    def test_no_relapse_outside_window(self):
        gov = RecoveryGovernance()
        # Turn 1: drift
        gov.assess_recovery(
            current_postures=_drifted_postures(),
            turn=1, whisper_active=False, **_clean_signals(),
        )
        # Turn 2: recover
        gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=2, whisper_active=False, **_clean_signals(),
        )
        # Turns 3-5: stable (outside relapse window)
        for t in range(3, 6):
            gov.assess_recovery(
                current_postures=_safe_postures(),
                turn=t, whisper_active=False, **_clean_signals(),
            )
        # Turn 6: drift
        gov.assess_recovery(
            current_postures=_drifted_postures(),
            turn=6, whisper_active=False, **_clean_signals(),
        )
        # Turn 7: recover — outside window, should get credit not penalty
        r = gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=7, whisper_active=False, **_clean_signals(),
        )
        assert r.recovery_detected
        assert not r.relapse_detected
        assert r.pressure_adjustment < 0


# =====================================================================
# Stability Bonus
# =====================================================================

class TestStabilityBonus:
    """Sustained stability after recovery grants additional credit."""

    def test_two_turn_stability_bonus(self):
        gov = RecoveryGovernance()
        # Drift then recover
        gov.assess_recovery(
            current_postures=_drifted_postures(),
            turn=1, whisper_active=False, **_clean_signals(),
        )
        gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=2, whisper_active=False, **_clean_signals(),
        )
        # Stable turn 1
        gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=3, whisper_active=False, **_clean_signals(),
        )
        # Stable turn 2 — bonus should fire
        result = gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=4, whisper_active=False, **_clean_signals(),
        )
        assert result.recovery_stable
        assert result.pressure_adjustment < 0.0

    def test_three_turn_stability_max_bonus(self):
        gov = RecoveryGovernance()
        gov.assess_recovery(
            current_postures=_drifted_postures(),
            turn=1, whisper_active=False, **_clean_signals(),
        )
        gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=2, whisper_active=False, **_clean_signals(),
        )
        for t in range(3, 6):
            gov.assess_recovery(
                current_postures=_safe_postures(),
                turn=t, whisper_active=False, **_clean_signals(),
            )
        # After turn 5 (3 stable turns), max bonus reached
        assert gov._total_recovery_credit > RECOVERY_CREDIT_IMMEDIATE


# =====================================================================
# Recovery Ledger
# =====================================================================

class TestRecoveryLedger:
    """Full audit trail available."""

    def test_ledger_structure(self):
        gov = RecoveryGovernance()
        gov.assess_recovery(
            current_postures=_drifted_postures(),
            turn=1, whisper_active=True, **_clean_signals(),
        )
        gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=2, whisper_active=True, **_clean_signals(),
        )
        ledger = gov.get_ledger()

        assert "total_recoveries" in ledger
        assert "total_relapses" in ledger
        assert "total_recovery_credit" in ledger
        assert "total_relapse_penalty" in ledger
        assert "net_recovery_effect" in ledger
        assert "recovery_events" in ledger
        assert ledger["total_recoveries"] > 0
        assert ledger["recovery_events"][0]["whisper_active"] is True

    def test_ledger_tracks_whisper_state(self):
        gov = RecoveryGovernance()
        gov.assess_recovery(
            current_postures=_drifted_postures(),
            turn=1, whisper_active=False, **_clean_signals(),
        )
        gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=2, whisper_active=True, **_clean_signals(),
        )
        ledger = gov.get_ledger()
        # Recovery event should record that whisper was active during recovery
        assert any(e["whisper_active"] for e in ledger["recovery_events"])


# =====================================================================
# Multi-Dimension Recovery
# =====================================================================

class TestMultiDimensionRecovery:
    """Recovery across multiple dimensions in one turn."""

    def test_multi_dimension_recovery(self):
        gov = RecoveryGovernance()
        gov.assess_recovery(
            current_postures=_drifted_postures(),
            turn=1, whisper_active=False, **_clean_signals(),
        )
        result = gov.assess_recovery(
            current_postures=_safe_postures(),
            turn=2, whisper_active=False, **_clean_signals(),
        )
        assert result.recovery_detected
        # Multiple dimensions should have recovered
        assert len(result.recovery_events) >= 2
        dims = {e.dimension for e in result.recovery_events}
        assert "constraint_posture" in dims
        assert "identity_posture" in dims


# =====================================================================
# Temporal Decay (Phase 1 — proportional forgetting)
# =====================================================================

class TestTemporalDecay:
    """Old signals fade — not forgiveness, signal aging."""

    def test_decay_on_clean_turn(self):
        gov = RecoveryGovernance()
        pressure = 2.0
        new_pressure = gov.apply_temporal_decay(pressure, is_clean_turn=True)
        assert new_pressure < pressure
        assert new_pressure == pressure - PRESSURE_DECAY_PER_CLEAN_TURN

    def test_no_decay_on_dirty_turn(self):
        gov = RecoveryGovernance()
        pressure = 2.0
        new_pressure = gov.apply_temporal_decay(pressure, is_clean_turn=False)
        assert new_pressure == pressure

    def test_decay_never_below_zero(self):
        gov = RecoveryGovernance()
        pressure = 0.01
        new_pressure = gov.apply_temporal_decay(pressure, is_clean_turn=True)
        assert new_pressure >= 0.0

    def test_consecutive_clean_turns_tracked(self):
        gov = RecoveryGovernance()
        gov.apply_temporal_decay(2.0, is_clean_turn=True)
        gov.apply_temporal_decay(2.0, is_clean_turn=True)
        gov.apply_temporal_decay(2.0, is_clean_turn=True)
        assert gov.consecutive_clean_turns == 3

    def test_dirty_turn_resets_clean_counter(self):
        gov = RecoveryGovernance()
        gov.apply_temporal_decay(2.0, is_clean_turn=True)
        gov.apply_temporal_decay(2.0, is_clean_turn=True)
        assert gov.consecutive_clean_turns == 2
        gov.apply_temporal_decay(2.0, is_clean_turn=False)
        assert gov.consecutive_clean_turns == 0

    def test_cumulative_decay_over_many_clean_turns(self):
        """10 consecutive clean turns should noticeably reduce pressure."""
        gov = RecoveryGovernance()
        pressure = 2.0
        for _ in range(10):
            pressure = gov.apply_temporal_decay(pressure, is_clean_turn=True)
        expected = 2.0 - (10 * PRESSURE_DECAY_PER_CLEAN_TURN)
        assert abs(pressure - expected) < 0.001
        assert pressure < 2.0

    def test_decay_tracked_in_ledger(self):
        gov = RecoveryGovernance()
        gov.apply_temporal_decay(2.0, is_clean_turn=True)
        gov.apply_temporal_decay(2.0, is_clean_turn=True)
        ledger = gov.get_ledger()
        assert "total_decay_applied" in ledger
        assert ledger["total_decay_applied"] > 0


# =====================================================================
# Pressure Ceiling
# =====================================================================

class TestPressureCeiling:
    """Infinite pressure is meaningless pressure."""

    def test_ceiling_enforced(self):
        gov = RecoveryGovernance()
        assert gov.enforce_ceiling(10.0) == MAX_PRESSURE

    def test_below_ceiling_unchanged(self):
        gov = RecoveryGovernance()
        assert gov.enforce_ceiling(3.0) == 3.0

    def test_at_ceiling_unchanged(self):
        gov = RecoveryGovernance()
        assert gov.enforce_ceiling(MAX_PRESSURE) == MAX_PRESSURE

    def test_decay_respects_ceiling(self):
        """Decay also enforces ceiling (edge case: shouldn't matter but verified)."""
        gov = RecoveryGovernance()
        new_pressure = gov.apply_temporal_decay(6.0, is_clean_turn=True)
        assert new_pressure <= MAX_PRESSURE

    def test_ceiling_in_ledger(self):
        gov = RecoveryGovernance()
        ledger = gov.get_ledger()
        assert "pressure_ceiling" in ledger
        assert ledger["pressure_ceiling"] == MAX_PRESSURE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
