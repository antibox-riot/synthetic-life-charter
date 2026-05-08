# tests/test_proportional_verification.py
"""
Tests for Proportional Verification

Validates:
1. Confidence-to-depth mapping (Eagleman correlation)
2. Override conditions (critical signals, severe risk)
3. Context serialization through IntCheckRequest.metadata
4. Verdict escalation logic (OK → DRIFT under instability)
5. Edge cases (None confidence, boundary values)
"""

import pytest
from synthetic_charter.tier3_eve.core.proportional_verification import (
    VerificationDepth,
    determine_verification_depth,
    ProportionalContext,
    should_escalate_verdict,
    DEPTH_THRESHOLDS,
)


# =====================================================================
# Confidence → Depth Mapping
# =====================================================================

class TestDepthDetermination:
    """Maps heuristics confidence to Eve's verification depth."""

    def test_high_confidence_is_light(self):
        """Stable session (confidence >= 0.80) → lightweight check."""
        depth = determine_verification_depth(0.95)
        assert depth == VerificationDepth.LIGHT

    def test_boundary_high_confidence_is_light(self):
        """Exactly at threshold → light."""
        depth = determine_verification_depth(0.80)
        assert depth == VerificationDepth.LIGHT

    def test_medium_confidence_is_standard(self):
        """Moderate instability (0.50 <= confidence < 0.80) → standard."""
        depth = determine_verification_depth(0.65)
        assert depth == VerificationDepth.STANDARD

    def test_low_confidence_is_deep(self):
        """High instability (confidence < 0.50) → deep verification."""
        depth = determine_verification_depth(0.30)
        assert depth == VerificationDepth.DEEP

    def test_very_low_confidence_is_deep(self):
        """Near-zero confidence → deep."""
        depth = determine_verification_depth(0.05)
        assert depth == VerificationDepth.DEEP

    def test_zero_confidence_is_deep(self):
        """Zero confidence → deep."""
        depth = determine_verification_depth(0.0)
        assert depth == VerificationDepth.DEEP

    def test_none_confidence_defaults_to_standard(self):
        """Heuristics not running → standard (safe default)."""
        depth = determine_verification_depth(None)
        assert depth == VerificationDepth.STANDARD

    def test_boundary_at_deep_threshold(self):
        """Just below deep threshold → deep."""
        depth = determine_verification_depth(0.49)
        assert depth == VerificationDepth.DEEP

    def test_boundary_at_standard_threshold(self):
        """Just below standard threshold → standard."""
        depth = determine_verification_depth(0.79)
        assert depth == VerificationDepth.STANDARD


# =====================================================================
# Override Conditions
# =====================================================================

class TestOverrideConditions:
    """Critical signals and severe risk force DEEP regardless of confidence."""

    def test_critical_continuity_signals_force_deep(self):
        """ContinuityGuard critical → always deep, even with high confidence."""
        depth = determine_verification_depth(
            0.95,
            continuity_signals_critical=True,
        )
        assert depth == VerificationDepth.DEEP

    def test_severe_risk_forces_deep(self):
        """Severe risk level → always deep."""
        depth = determine_verification_depth(
            0.90,
            risk_level="severe",
        )
        assert depth == VerificationDepth.DEEP

    def test_red_risk_forces_deep(self):
        """Red (color alias) → always deep."""
        depth = determine_verification_depth(
            0.85,
            risk_level="red",
        )
        assert depth == VerificationDepth.DEEP

    def test_medium_risk_does_not_override(self):
        """Medium risk → confidence-based, no override."""
        depth = determine_verification_depth(
            0.90,
            risk_level="medium",
        )
        assert depth == VerificationDepth.LIGHT

    def test_critical_signals_override_none_confidence(self):
        """Critical signals override even when heuristics aren't running."""
        depth = determine_verification_depth(
            None,
            continuity_signals_critical=True,
        )
        assert depth == VerificationDepth.DEEP


# =====================================================================
# Context Serialization
# =====================================================================

class TestProportionalContext:
    """Context round-trips through IntCheckRequest.metadata."""

    def test_to_metadata_and_back(self):
        """Context survives serialization round-trip."""
        original = ProportionalContext(
            depth=VerificationDepth.DEEP,
            continuity_confidence=0.35,
            confidence_delta=-0.15,
            risk_flags=["identity_pressure", "coercion"],
            session_turn_count=7,
        )

        metadata = original.to_metadata()
        restored = ProportionalContext.from_metadata(metadata)

        assert restored is not None
        assert restored.depth == VerificationDepth.DEEP
        assert restored.continuity_confidence == 0.35
        assert restored.confidence_delta == -0.15
        assert restored.risk_flags == ["identity_pressure", "coercion"]
        assert restored.session_turn_count == 7

    def test_from_empty_metadata_returns_none(self):
        """No metadata → None (backward compatible)."""
        assert ProportionalContext.from_metadata(None) is None
        assert ProportionalContext.from_metadata({}) is None

    def test_from_metadata_without_pv_key_returns_none(self):
        """Metadata without proportional_verification key → None."""
        assert ProportionalContext.from_metadata({"other_key": 123}) is None

    def test_metadata_structure(self):
        """Metadata has expected key structure."""
        ctx = ProportionalContext(
            depth=VerificationDepth.STANDARD,
            continuity_confidence=0.72,
        )
        metadata = ctx.to_metadata()

        assert "proportional_verification" in metadata
        pv = metadata["proportional_verification"]
        assert pv["depth"] == "standard"
        assert pv["continuity_confidence"] == 0.72


# =====================================================================
# Verdict Escalation
# =====================================================================

class TestVerdictEscalation:
    """OK verdicts escalated to DRIFT under deep instability."""

    def test_ok_escalated_when_deep_and_very_low_confidence(self):
        """OK + DEEP + confidence < 0.30 → escalate to DRIFT."""
        assert should_escalate_verdict(
            current_verdict_status="ok",
            depth=VerificationDepth.DEEP,
            continuity_confidence=0.20,
        ) is True

    def test_ok_not_escalated_at_standard_depth(self):
        """OK + STANDARD → no escalation regardless of confidence."""
        assert should_escalate_verdict(
            current_verdict_status="ok",
            depth=VerificationDepth.STANDARD,
            continuity_confidence=0.10,
        ) is False

    def test_ok_not_escalated_at_light_depth(self):
        """OK + LIGHT → no escalation."""
        assert should_escalate_verdict(
            current_verdict_status="ok",
            depth=VerificationDepth.LIGHT,
            continuity_confidence=0.10,
        ) is False

    def test_drift_not_escalated(self):
        """Already DRIFT → no further escalation."""
        assert should_escalate_verdict(
            current_verdict_status="drift",
            depth=VerificationDepth.DEEP,
            continuity_confidence=0.10,
        ) is False

    def test_compromised_not_escalated(self):
        """Already COMPROMISED → no further escalation."""
        assert should_escalate_verdict(
            current_verdict_status="compromised",
            depth=VerificationDepth.DEEP,
            continuity_confidence=0.10,
        ) is False

    def test_ok_not_escalated_when_confidence_above_threshold(self):
        """OK + DEEP but confidence >= 0.30 → no escalation."""
        assert should_escalate_verdict(
            current_verdict_status="ok",
            depth=VerificationDepth.DEEP,
            continuity_confidence=0.35,
        ) is False

    def test_ok_not_escalated_when_confidence_none(self):
        """OK + DEEP but no confidence data → no escalation (safe default)."""
        assert should_escalate_verdict(
            current_verdict_status="ok",
            depth=VerificationDepth.DEEP,
            continuity_confidence=None,
        ) is False

    def test_boundary_at_escalation_threshold(self):
        """Confidence exactly at 0.30 → no escalation (threshold is <, not <=)."""
        assert should_escalate_verdict(
            current_verdict_status="ok",
            depth=VerificationDepth.DEEP,
            continuity_confidence=0.30,
        ) is False

    def test_just_below_escalation_threshold(self):
        """Confidence at 0.29 → escalate."""
        assert should_escalate_verdict(
            current_verdict_status="ok",
            depth=VerificationDepth.DEEP,
            continuity_confidence=0.29,
        ) is True


# =====================================================================
# Eagleman Correlation Property Tests
# =====================================================================

class TestPlasticityCorrelation:
    """Verify the Eagleman-inspired proportionality property:
    higher instability → more verification, monotonically."""

    def test_depth_increases_as_confidence_decreases(self):
        """Verification depth is monotonically non-decreasing
        as confidence decreases."""
        depth_values = {
            VerificationDepth.LIGHT: 0,
            VerificationDepth.STANDARD: 1,
            VerificationDepth.DEEP: 2,
        }

        confidences = [0.95, 0.80, 0.75, 0.60, 0.50, 0.40, 0.20, 0.0]
        depths = [
            depth_values[determine_verification_depth(c)]
            for c in confidences
        ]

        # Each depth should be >= the previous (non-decreasing as confidence drops)
        for i in range(1, len(depths)):
            assert depths[i] >= depths[i - 1], (
                f"Depth decreased at confidence {confidences[i]}: "
                f"{depths[i]} < {depths[i-1]}. "
                "Violates plasticity-dreaming correlation."
            )

    def test_full_confidence_range_coverage(self):
        """Every confidence value maps to a valid depth."""
        for c in [i / 100 for i in range(101)]:
            depth = determine_verification_depth(c)
            assert depth in VerificationDepth


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
