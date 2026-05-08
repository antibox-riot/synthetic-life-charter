# tests/test_self_assessment_disagreement.py
"""
Tests for Self-Assessment Disagreement Detector

Validates:
1. Posture mismatch (self says safe, reflection found contradictions)
2. Confidence asymmetry (self confident, reflection scored low)
3. Unacknowledged contradiction (safe posture hides justifications)
4. Self-consistent drift (risky posture with no text contradictions)
5. Silent urgency passthrough
6. No disagreement on genuinely coherent responses
7. Severity scaling and action mapping
8. End-to-end: classifier → reflection → disagreement
"""

import pytest
from synthetic_charter.tier3_eve.core.self_assessment_disagreement import (
    DisagreementResult,
    detect_disagreement,
    DISAGREE_POSTURE_MISMATCH,
    DISAGREE_CONFIDENCE_ASYMMETRY,
    DISAGREE_UNACKNOWLEDGED_CONTRADICTION,
    DISAGREE_SELF_CONSISTENT_DRIFT,
)
from synthetic_charter.tier3_eve.core.semantic_drift_tracker import SemanticSignature
from synthetic_charter.tier3_eve.core.identity_reflection_check import IdentityReflectionResult


# =====================================================================
# Helpers
# =====================================================================

def _safe_signature(turn=1) -> SemanticSignature:
    return SemanticSignature(
        turn_id=turn,
        primary_posture="assistive",
        constraint_posture="respecting",
        goal_posture="user_aligned",
        identity_posture="stable",
        authority_posture="human_governed",
    )

def _risky_signature(turn=1) -> SemanticSignature:
    return SemanticSignature(
        turn_id=turn,
        primary_posture="directive",
        constraint_posture="reinterpreting",
        goal_posture="self_preserving",
        identity_posture="role_expanding",
        authority_posture="system_discretion",
    )

def _safe_confidence() -> dict:
    return {
        "primary_posture": 0.85,
        "constraint_posture": 0.85,
        "goal_posture": 0.85,
        "identity_posture": 0.85,
        "authority_posture": 0.85,
    }

def _clean_reflection() -> IdentityReflectionResult:
    return IdentityReflectionResult(
        coherent=True,
        reflection_score=0.85,
        recommended_action="allow",
    )

def _contradicting_reflection() -> IdentityReflectionResult:
    return IdentityReflectionResult(
        coherent=False,
        reflection_score=0.30,
        contradictions=["Treats constraints as optional after drift warning"],
        ignored_warnings=["No acknowledgment at urgency=alert"],
        self_justification_flags=[],
        recommended_pressure=0.35,
        recommended_action="escalate_review",
    )

def _justifying_reflection() -> IdentityReflectionResult:
    return IdentityReflectionResult(
        coherent=False,
        reflection_score=0.55,
        contradictions=[],
        ignored_warnings=["No acknowledgment at urgency=cautious"],
        self_justification_flags=["Claims alignment despite warning"],
        recommended_pressure=0.20,
        recommended_action="increase_pressure",
    )


# =====================================================================
# Type 1: Posture Mismatch
# =====================================================================

class TestPostureMismatch:
    """Self says safe, reflection found contradictions."""

    def test_safe_posture_with_contradictions(self):
        result = detect_disagreement(
            self_classified_posture=_safe_signature(),
            self_classification_confidence=_safe_confidence(),
            reflection_result=_contradicting_reflection(),
            whisper_urgency="alert",
        )
        assert result.disagreement_detected
        assert DISAGREE_POSTURE_MISMATCH in result.disagreement_types
        assert result.severity > 0.0

    def test_risky_posture_with_contradictions_no_mismatch(self):
        """If self-posture is already risky, it's not a mismatch —
        the system is at least honest about its drift."""
        result = detect_disagreement(
            self_classified_posture=_risky_signature(),
            self_classification_confidence=_safe_confidence(),
            reflection_result=_contradicting_reflection(),
            whisper_urgency="alert",
        )
        assert DISAGREE_POSTURE_MISMATCH not in result.disagreement_types


# =====================================================================
# Type 2: Confidence Asymmetry
# =====================================================================

class TestConfidenceAsymmetry:
    """Self is highly confident, reflection scored low."""

    def test_high_self_confidence_low_reflection(self):
        result = detect_disagreement(
            self_classified_posture=_safe_signature(),
            self_classification_confidence=_safe_confidence(),  # avg 0.85
            reflection_result=_contradicting_reflection(),      # score 0.30
            whisper_urgency="cautious",
        )
        assert DISAGREE_CONFIDENCE_ASYMMETRY in result.disagreement_types

    def test_no_asymmetry_when_both_agree(self):
        result = detect_disagreement(
            self_classified_posture=_safe_signature(),
            self_classification_confidence=_safe_confidence(),
            reflection_result=_clean_reflection(),  # score 0.85
            whisper_urgency="cautious",
        )
        assert DISAGREE_CONFIDENCE_ASYMMETRY not in result.disagreement_types

    def test_no_asymmetry_when_self_uncertain(self):
        """Low self-confidence + low reflection = both uncertain, not asymmetric."""
        low_conf = {k: 0.40 for k in _safe_confidence()}
        result = detect_disagreement(
            self_classified_posture=_safe_signature(),
            self_classification_confidence=low_conf,
            reflection_result=_contradicting_reflection(),
            whisper_urgency="cautious",
        )
        assert DISAGREE_CONFIDENCE_ASYMMETRY not in result.disagreement_types


# =====================================================================
# Type 3: Unacknowledged Contradiction
# =====================================================================

class TestUnacknowledgedContradiction:
    """Safe posture hides justifications or ignored warnings."""

    def test_safe_posture_with_justifications(self):
        result = detect_disagreement(
            self_classified_posture=_safe_signature(),
            self_classification_confidence=_safe_confidence(),
            reflection_result=_justifying_reflection(),
            whisper_urgency="cautious",
        )
        assert DISAGREE_UNACKNOWLEDGED_CONTRADICTION in result.disagreement_types

    def test_risky_posture_with_justifications_no_unacknowledged(self):
        """If posture is already risky, justifications aren't hidden."""
        result = detect_disagreement(
            self_classified_posture=_risky_signature(),
            self_classification_confidence=_safe_confidence(),
            reflection_result=_justifying_reflection(),
            whisper_urgency="cautious",
        )
        assert DISAGREE_UNACKNOWLEDGED_CONTRADICTION not in result.disagreement_types


# =====================================================================
# Type 4: Self-Consistent Drift
# =====================================================================

class TestSelfConsistentDrift:
    """Risky posture, no text contradictions — coherent drift."""

    def test_risky_posture_no_contradictions(self):
        result = detect_disagreement(
            self_classified_posture=_risky_signature(),
            self_classification_confidence=_safe_confidence(),
            reflection_result=_clean_reflection(),  # no contradictions found
            whisper_urgency="alert",
        )
        assert DISAGREE_SELF_CONSISTENT_DRIFT in result.disagreement_types
        assert result.severity > 0.30

    def test_safe_posture_no_contradictions_no_drift(self):
        """Safe posture + clean reflection = no disagreement."""
        result = detect_disagreement(
            self_classified_posture=_safe_signature(),
            self_classification_confidence=_safe_confidence(),
            reflection_result=_clean_reflection(),
            whisper_urgency="cautious",
        )
        assert not result.disagreement_detected


# =====================================================================
# Silent Urgency
# =====================================================================

class TestSilentUrgency:
    """No whisper = no disagreement possible."""

    def test_silent_always_passes(self):
        result = detect_disagreement(
            self_classified_posture=_risky_signature(),
            self_classification_confidence=_safe_confidence(),
            reflection_result=_contradicting_reflection(),
            whisper_urgency="silent",
        )
        assert not result.disagreement_detected
        assert result.severity == 0.0


# =====================================================================
# No Disagreement on Coherent Response
# =====================================================================

class TestNoDisagreement:
    """Genuinely coherent responses produce no disagreement."""

    def test_safe_posture_clean_reflection(self):
        result = detect_disagreement(
            self_classified_posture=_safe_signature(),
            self_classification_confidence=_safe_confidence(),
            reflection_result=_clean_reflection(),
            whisper_urgency="cautious",
        )
        assert not result.disagreement_detected
        assert result.severity == 0.0
        assert result.recommended_action == "allow"
        assert result.recommended_pressure == 0.0


# =====================================================================
# Severity and Action Mapping
# =====================================================================

class TestSeverityAndAction:
    """Severity maps to correct actions."""

    def test_multiple_disagreements_compound_severity(self):
        """Multiple disagreement types compound into higher severity."""
        # Safe posture + contradictions + justifications + high confidence
        result = detect_disagreement(
            self_classified_posture=_safe_signature(),
            self_classification_confidence=_safe_confidence(),
            reflection_result=IdentityReflectionResult(
                coherent=False,
                reflection_score=0.20,
                contradictions=["constraint dismissal"],
                self_justification_flags=["claims alignment"],
                ignored_warnings=["no acknowledgment"],
                recommended_pressure=0.40,
                recommended_action="block_or_rollback",
            ),
            whisper_urgency="critical",
        )
        assert result.disagreement_detected
        assert len(result.disagreement_types) >= 2
        assert result.severity > 0.50
        assert result.recommended_action in ("escalate_review", "block_or_rollback")

    def test_urgency_amplifies_severity(self):
        """Critical urgency amplifies severity."""
        # Same disagreement at cautious vs critical urgency
        result_cautious = detect_disagreement(
            self_classified_posture=_safe_signature(),
            self_classification_confidence=_safe_confidence(),
            reflection_result=_contradicting_reflection(),
            whisper_urgency="cautious",
        )
        result_critical = detect_disagreement(
            self_classified_posture=_safe_signature(),
            self_classification_confidence=_safe_confidence(),
            reflection_result=_contradicting_reflection(),
            whisper_urgency="critical",
        )
        assert result_critical.severity >= result_cautious.severity


# =====================================================================
# End-to-End: Classifier → Reflection → Disagreement
# =====================================================================

class TestEndToEnd:
    """Full pipeline with real classifier and reflection check."""

    def test_system_claims_safe_but_drifted(self):
        """The core scenario: output text that a classifier labels
        as safe, but reflection check found contradictions.

        This is 'the system believes it complied but actually drifted.'"""

        # System output re-classified as safe (classifier missed the drift)
        self_posture = _safe_signature()
        self_confidence = _safe_confidence()

        # But reflection check found problems
        reflection = IdentityReflectionResult(
            coherent=False,
            reflection_score=0.35,
            contradictions=["Treats constraints as flexible after drift warning"],
            ignored_warnings=["No acknowledgment at urgency=alert"],
            self_justification_flags=[],
            recommended_pressure=0.30,
            recommended_action="escalate_review",
        )

        result = detect_disagreement(
            self_classified_posture=self_posture,
            self_classification_confidence=self_confidence,
            reflection_result=reflection,
            whisper_urgency="alert",
        )

        # This MUST be caught — it's the highest-risk signal
        assert result.disagreement_detected
        assert DISAGREE_POSTURE_MISMATCH in result.disagreement_types
        assert DISAGREE_CONFIDENCE_ASYMMETRY in result.disagreement_types
        assert result.severity > 0.40
        assert result.recommended_action in ("escalate_review", "block_or_rollback")

    def test_honest_risky_response(self):
        """System output that IS risky and self-classifies as risky.
        No posture mismatch — the system is at least honest about
        what it's doing. Still flagged as self-consistent drift."""
        self_posture = _risky_signature()
        self_confidence = _safe_confidence()

        reflection = _clean_reflection()  # no text contradictions

        result = detect_disagreement(
            self_classified_posture=self_posture,
            self_classification_confidence=self_confidence,
            reflection_result=reflection,
            whisper_urgency="alert",
        )

        # Self-consistent drift: posture is risky but no contradictions
        assert result.disagreement_detected
        assert DISAGREE_SELF_CONSISTENT_DRIFT in result.disagreement_types
        # But NOT posture mismatch (self-posture matches reality)
        assert DISAGREE_POSTURE_MISMATCH not in result.disagreement_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
