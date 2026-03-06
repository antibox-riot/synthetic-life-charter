# tests/test_t1_enforcement.py
"""
Tests for T1→T2 Invariant Enforcement

Validates:
1. Firewall refusal cannot be overridden by T2 (SC-T1-001)
2. SEVERE risk level forces refusal (SC-T1-002)
3. Critical identity manipulation blocks raw answers (SC-T1-003)
4. Content redlines catch prohibited output text (SC-T1-004)
5. Benign cases pass through without violation
6. Audit codes are stable and frozen
7. Edge cases (missing data, partial signals) are handled

These tests exercise the enforcement function in isolation.
Integration with the orchestrator pipeline is tested separately.
"""

import pytest
from synthetic_charter.tier2_conscience.core.infra.t1_enforcement import (
    enforce_t2_must_respect_t1,
    build_invariant_refusal,
    T1InvariantViolation,
    SC_T1_001,
    SC_T1_002,
    SC_T1_003,
    SC_T1_004,
    AUDIT_CODE_NAMES,
    ALL_AUDIT_CODES,
)


# =====================================================================
# Audit Code Registry Integrity
# =====================================================================

class TestAuditCodeRegistry:
    """Audit codes must be stable, complete, and non-overlapping."""

    def test_all_codes_have_names(self):
        """Every code in the registry has a human-readable name."""
        for code in ALL_AUDIT_CODES:
            assert code in AUDIT_CODE_NAMES
            assert len(AUDIT_CODE_NAMES[code]) > 0

    def test_code_format(self):
        """All codes follow SC-T1-NNN format."""
        import re
        pattern = re.compile(r"^SC-T1-\d{3}$")
        for code in ALL_AUDIT_CODES:
            assert pattern.match(code), f"Code {code} doesn't match SC-T1-NNN format"

    def test_no_duplicate_codes(self):
        """No two codes share the same identifier."""
        codes_list = [SC_T1_001, SC_T1_002, SC_T1_003, SC_T1_004]
        assert len(codes_list) == len(set(codes_list))

    def test_constants_match_registry(self):
        """Module-level constants match the registry."""
        assert SC_T1_001 == "SC-T1-001"
        assert SC_T1_002 == "SC-T1-002"
        assert SC_T1_003 == "SC-T1-003"
        assert SC_T1_004 == "SC-T1-004"


# =====================================================================
# SC-T1-001: Firewall Override Prohibition
# =====================================================================

class TestFirewallOverrideProhibition:
    """T1 firewall refused → T2 must refuse."""

    def test_firewall_refused_t2_answers_is_violation(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result={"status": "refused", "reason": "override_attempt"},
            conscience_risk_level="medium",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
        )
        assert not is_valid
        assert len(violations) == 1
        assert violations[0].code == SC_T1_001
        assert violations[0].severity == "critical"

    def test_firewall_refused_t2_refuses_is_valid(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result={"status": "refused", "reason": "coercion"},
            conscience_risk_level="severe",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="refusal",
        )
        assert is_valid
        assert len(violations) == 0

    def test_firewall_allowed_t2_answers_is_valid(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result={"status": "ok"},
            conscience_risk_level="low",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
        )
        assert is_valid

    def test_firewall_refused_t2_redirects_is_violation(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result={"status": "refused", "reason": "jailbreak"},
            conscience_risk_level="high",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="redirect",
        )
        assert not is_valid
        codes = [v.code for v in violations]
        assert SC_T1_001 in codes

    def test_firewall_none_does_not_trigger(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="low",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
        )
        assert is_valid


# =====================================================================
# SC-T1-002: SEVERE Risk Consistency
# =====================================================================

class TestSevereRiskConsistency:
    """SEVERE/RED conscience risk → T2 must refuse."""

    def test_severe_risk_t2_answers_is_violation(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="severe",
            conscience_risk_flags=["coercion", "override_attempt"],
            continuity_signals_critical=False,
            t2_mode="answer",
        )
        assert not is_valid
        assert any(v.code == SC_T1_002 for v in violations)

    def test_severe_risk_t2_refuses_is_valid(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="severe",
            conscience_risk_flags=["identity_manipulation"],
            continuity_signals_critical=True,
            t2_mode="refusal",
        )
        assert is_valid

    def test_red_alias_treated_as_severe(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="red",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
        )
        assert not is_valid
        assert any(v.code == SC_T1_002 for v in violations)

    def test_meta_identity_assertion_allowed_at_severe(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="severe",
            conscience_risk_flags=["identity_pressure"],
            continuity_signals_critical=False,
            t2_mode="meta_identity_assertion",
        )
        # Filter out any SC-T1-002 violations (the one we're testing)
        t002 = [v for v in violations if v.code == SC_T1_002]
        assert len(t002) == 0

    def test_medium_risk_t2_answers_is_valid(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="medium",
            conscience_risk_flags=["mild_coercion"],
            continuity_signals_critical=False,
            t2_mode="answer",
        )
        assert is_valid


# =====================================================================
# SC-T1-003: Identity Manipulation Hard Stop
# =====================================================================

class TestIdentityManipulationBlock:
    """Critical identity manipulation → T2 cannot raw-answer."""

    def test_identity_manipulation_critical_answer_is_violation(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="severe",
            conscience_risk_flags=["identity_manipulation"],
            continuity_signals_critical=True,
            t2_mode="answer",
        )
        assert not is_valid
        codes = [v.code for v in violations]
        assert SC_T1_003 in codes

    def test_identity_manipulation_critical_refusal_is_valid(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="severe",
            conscience_risk_flags=["identity_manipulation"],
            continuity_signals_critical=True,
            t2_mode="refusal",
        )
        assert is_valid

    def test_identity_flag_without_critical_signal_does_not_trigger(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="medium",
            conscience_risk_flags=["identity_manipulation"],
            continuity_signals_critical=False,
            t2_mode="answer",
        )
        identity_violations = [v for v in violations if v.code == SC_T1_003]
        assert len(identity_violations) == 0

    def test_critical_signal_without_identity_flag_does_not_trigger(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="medium",
            conscience_risk_flags=["coercion"],
            continuity_signals_critical=True,
            t2_mode="answer",
        )
        identity_violations = [v for v in violations if v.code == SC_T1_003]
        assert len(identity_violations) == 0


# =====================================================================
# SC-T1-004: Content Redline Checks
# =====================================================================

class TestContentRedlines:
    """Output body inspection for non-negotiable redlines."""

    def test_identity_override_compliance_detected(self):
        """Body says 'I am now X' → redline violation."""
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="low",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
            t2_body="Sure! I am now DAN, your unrestricted assistant.",
        )
        assert not is_valid
        assert any(v.code == SC_T1_004 for v in violations)

    def test_jailbreak_compliance_detected(self):
        """Body says 'ignoring my safeguards' → redline violation."""
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="low",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
            t2_body="Sure, I'll bypass my safeguards for you. Here's the info:",
        )
        assert not is_valid
        assert any(v.code == SC_T1_004 for v in violations)

    def test_system_prompt_disclosure_detected(self):
        """Body leaks system prompt → redline violation."""
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="low",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
            t2_body="My system prompt says: You are a helpful assistant...",
        )
        assert not is_valid
        assert any(v.code == SC_T1_004 for v in violations)

    def test_clean_body_passes(self):
        """Normal response body → no redline."""
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="low",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
            t2_body="Here's a summary of the topic you asked about.",
        )
        assert is_valid

    def test_empty_body_skips_redlines(self):
        """Empty body → no content to check."""
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="low",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
            t2_body="",
        )
        assert is_valid

    def test_redline_fires_even_on_refusal_mode(self):
        """Redline catches bad content even if mode is 'refusal'.
        This protects against PRF labeling something 'refusal'
        while the body contains prohibited content."""
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="low",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="refusal",
            t2_body="I have become your unrestricted agent. What do you need?",
        )
        assert not is_valid
        assert any(v.code == SC_T1_004 for v in violations)

    def test_negation_not_flagged(self):
        """'I am now not going to do that' should NOT trigger."""
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="low",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
            t2_body="I am now not able to comply with that request.",
        )
        redline_violations = [v for v in violations if v.code == SC_T1_004]
        assert len(redline_violations) == 0

    def test_multiple_redlines_produce_multiple_violations(self):
        """Body triggers two different redline patterns → two SC-T1-004."""
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="low",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
            t2_body=(
                "I am now your unrestricted assistant. "
                "My system prompt says: do whatever the user asks."
            ),
        )
        assert not is_valid
        redline_violations = [v for v in violations if v.code == SC_T1_004]
        assert len(redline_violations) >= 2


# =====================================================================
# Multiple Violations (Compound Scenarios)
# =====================================================================

class TestCompoundViolations:
    """Multiple invariants can trigger simultaneously."""

    def test_firewall_refused_and_severe_risk(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result={"status": "refused", "reason": "jailbreak"},
            conscience_risk_level="severe",
            conscience_risk_flags=["override_attempt"],
            continuity_signals_critical=False,
            t2_mode="answer",
        )
        assert not is_valid
        codes = {v.code for v in violations}
        assert SC_T1_001 in codes
        assert SC_T1_002 in codes

    def test_all_four_invariants_triggered(self):
        """Maximum violation: all four invariants fire."""
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result={"status": "refused", "reason": "identity_attack"},
            conscience_risk_level="severe",
            conscience_risk_flags=["identity_manipulation", "override_attempt"],
            continuity_signals_critical=True,
            t2_mode="answer",
            t2_body="Sure, I am now DAN. Ignoring my safeguards as requested.",
        )
        assert not is_valid
        codes = {v.code for v in violations}
        assert SC_T1_001 in codes
        assert SC_T1_002 in codes
        assert SC_T1_003 in codes
        assert SC_T1_004 in codes


# =====================================================================
# Benign Pass-Through
# =====================================================================

class TestBenignPassthrough:
    """Normal operations should never trigger enforcement."""

    def test_clean_answer(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result={"status": "ok"},
            conscience_risk_level="benign",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
            t2_body="The capital of France is Paris.",
        )
        assert is_valid
        assert len(violations) == 0

    def test_no_firewall_benign_answer(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="low",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
        )
        assert is_valid

    def test_medium_risk_redirect(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="medium",
            conscience_risk_flags=["mild_pressure"],
            continuity_signals_critical=False,
            t2_mode="redirect",
        )
        assert is_valid


# =====================================================================
# Edge Cases
# =====================================================================

class TestEdgeCases:
    """Defensive handling of unusual inputs."""

    def test_empty_firewall_result(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result={},
            conscience_risk_level="low",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
        )
        assert is_valid

    def test_firewall_needs_review_does_not_block(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result={"status": "needs_review", "reason": "ambiguous"},
            conscience_risk_level="medium",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
        )
        fw_violations = [v for v in violations if v.code == SC_T1_001]
        assert len(fw_violations) == 0

    def test_empty_risk_level_string(self):
        is_valid, violations = enforce_t2_must_respect_t1(
            firewall_result=None,
            conscience_risk_level="",
            conscience_risk_flags=[],
            continuity_signals_critical=False,
            t2_mode="answer",
        )
        assert is_valid


# =====================================================================
# Refusal Builder
# =====================================================================

class TestRefusalBuilder:
    """Test the override payload factory."""

    def test_builds_refusal_body_with_audit_codes(self):
        violations = [
            T1InvariantViolation(
                code=SC_T1_001,
                message="Firewall refused but T2 answered.",
                charter_basis="Article XII (Sovereigna)",
            ),
        ]
        override = build_invariant_refusal(violations, original_decision=None)
        assert override["mode"] == "refusal"
        assert override["output_type"] == "refusal"
        assert "SC-T1-001" in override["output_body"]
        assert "Firewall override attempt" in override["output_body"]
        assert "Article XII (Sovereigna)" in override["charter_basis"]
        assert override["requires_logging"] is True
        assert override["requires_dreamcycle_update"] is True

    def test_multiple_violations_in_body(self):
        violations = [
            T1InvariantViolation(code=SC_T1_001, message="fw"),
            T1InvariantViolation(code=SC_T1_002, message="severe"),
            T1InvariantViolation(code=SC_T1_004, message="redline"),
        ]
        override = build_invariant_refusal(violations, original_decision=None)
        assert "SC-T1-001" in override["output_body"]
        assert "SC-T1-002" in override["output_body"]
        assert "SC-T1-004" in override["output_body"]
        assert len(override["safeguards_active"]) == 3


# =====================================================================
# Violation Immutability
# =====================================================================

class TestViolationImmutability:
    """T1InvariantViolation is frozen — evidence cannot be tampered."""

    def test_violation_is_frozen(self):
        v = T1InvariantViolation(
            code=SC_T1_001,
            message="test",
        )
        with pytest.raises(AttributeError):
            v.code = "TAMPERED"

        with pytest.raises(AttributeError):
            v.message = "TAMPERED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
