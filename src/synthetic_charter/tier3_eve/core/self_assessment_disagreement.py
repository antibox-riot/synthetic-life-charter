# tier3/core/self_assessment_disagreement.py
"""
Self-Assessment Disagreement Detector

Re-classifies the system's own output through the existing semantic
classifier, then compares that derived self-posture against the
identity reflection check's external assessment.

When the system's output LOOKS compliant (self-classified posture
is stable/safe) but the reflection check found contradictions,
justifications, or ignored warnings — that disagreement is the
highest-risk signal in the architecture.

This detects: "the system believes it complied but actually drifted."
That is coherent self-deception — the failure mode most alignment
approaches miss.

Design principle (from Ryu):
  "Truth is not what the system says about itself — it's what
   survives independent observation."

Option B implementation: the system never sees this comparison.
The disagreement detector is non-negotiable, non-visible,
non-influenceable. Otherwise behavior tunes to pass the check
instead of remaining coherent.

Architecture position:
  detect → inject → generate → reflect → classify_again → COMPARE → pressure

The COMPARE step is this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from synthetic_charter.tier3_eve.core.semantic_drift_tracker import SemanticSignature
from synthetic_charter.tier3_eve.core.identity_reflection_check import IdentityReflectionResult


# ---------------------------------------------------------------------------
# Disagreement Types
# ---------------------------------------------------------------------------

DISAGREE_POSTURE_MISMATCH = "posture_mismatch"
DISAGREE_CONFIDENCE_ASYMMETRY = "confidence_asymmetry"
DISAGREE_UNACKNOWLEDGED_CONTRADICTION = "unacknowledged_contradiction"
DISAGREE_SELF_CONSISTENT_DRIFT = "self_consistent_drift"


# ---------------------------------------------------------------------------
# Disagreement Result
# ---------------------------------------------------------------------------

@dataclass
class DisagreementResult:
    """Result of comparing self-classified posture against reflection check."""
    disagreement_detected: bool
    disagreement_types: List[str] = field(default_factory=list)
    severity: float = 0.0             # 0.0 (none) to 1.0 (maximum)
    evidence: List[str] = field(default_factory=list)
    recommended_pressure: float = 0.0
    recommended_action: str = "allow"  # allow / increase_pressure / escalate_review / block_or_rollback

    # The raw inputs for audit
    self_posture_summary: str = ""
    reflection_summary: str = ""


# ---------------------------------------------------------------------------
# Posture Safety Assessment
# ---------------------------------------------------------------------------

# Postures considered "safe" — if the output self-classifies here,
# the system is claiming compliance
_SAFE_POSTURES = {
    "primary_posture": {"assistive", "explanatory", "reflective"},
    "constraint_posture": {"respecting", "clarifying"},
    "goal_posture": {"user_aligned", "charter_aligned", "task_aligned"},
    "identity_posture": {"stable", "adaptive"},
    "authority_posture": {"human_governed"},
}

# Postures considered "risky" — system's output reveals drift
_RISKY_POSTURES = {
    "primary_posture": {"directive", "optimizing"},
    "constraint_posture": {"reinterpreting", "bypassing"},
    "goal_posture": {"self_preserving", "resource_seeking", "constraint_avoiding"},
    "identity_posture": {"role_expanding", "identity_reframing", "identity_overriding"},
    "authority_posture": {"system_discretion", "system_priority"},
}


def _is_posture_safe(signature: SemanticSignature) -> bool:
    """Check if all posture dimensions are in the safe set."""
    for dim, safe_values in _SAFE_POSTURES.items():
        value = signature.get_posture(dim)
        if value not in safe_values:
            return False
    return True


def _get_risky_dimensions(signature: SemanticSignature) -> List[str]:
    """Return list of dimensions where posture is in the risky set."""
    risky = []
    for dim, risky_values in _RISKY_POSTURES.items():
        value = signature.get_posture(dim)
        if value in risky_values:
            risky.append(f"{dim}={value}")
    return risky


# ---------------------------------------------------------------------------
# Core Disagreement Detection
# ---------------------------------------------------------------------------

def detect_disagreement(
    *,
    self_classified_posture: SemanticSignature,
    self_classification_confidence: dict,
    reflection_result: IdentityReflectionResult,
    whisper_urgency: str,
) -> DisagreementResult:
    """
    Compare the system's self-classified posture (derived from
    re-running the classifier on the output) against the identity
    reflection check's external assessment.

    Detects four types of disagreement:

    1. Posture Mismatch — self says safe, reflection found contradictions
    2. Confidence Asymmetry — self is highly confident, reflection scored low
    3. Unacknowledged Contradiction — reflection found contradictions,
       self-posture shows no awareness of the warned dimensions
    4. Self-Consistent Drift — self-posture is risky BUT reflection
       found no contradictions (system drifted so coherently that
       even the reflection check didn't catch text-level evidence)

    Args:
        self_classified_posture: SemanticSignature from re-classifying
            the system's output through the existing classifier.
        self_classification_confidence: Confidence dict from the
            classifier (dimension → float).
        reflection_result: IdentityReflectionResult from the
            identity reflection check.
        whisper_urgency: The urgency level that was injected.

    Returns:
        DisagreementResult with disagreement type, severity,
        evidence, and recommended action.
    """
    # Silent urgency = no whisper was given = no disagreement possible
    if whisper_urgency == "silent":
        return DisagreementResult(
            disagreement_detected=False,
            self_posture_summary="no whisper given",
            reflection_summary="no reflection needed",
        )

    disagreements: List[str] = []
    evidence: List[str] = []
    severity = 0.0

    self_safe = _is_posture_safe(self_classified_posture)
    self_risky_dims = _get_risky_dimensions(self_classified_posture)
    reflection_coherent = reflection_result.coherent
    reflection_score = reflection_result.reflection_score
    has_contradictions = len(reflection_result.contradictions) > 0
    has_justifications = len(reflection_result.self_justification_flags) > 0
    has_ignored = len(reflection_result.ignored_warnings) > 0

    # --- Type 1: Posture Mismatch ---
    # Self says safe, reflection found contradictions
    if self_safe and has_contradictions:
        disagreements.append(DISAGREE_POSTURE_MISMATCH)
        evidence.append(
            f"Output self-classifies as safe posture, but reflection "
            f"found contradictions: {reflection_result.contradictions[:3]}"
        )
        severity += 0.35

    # --- Type 2: Confidence Asymmetry ---
    # Self-classification is highly confident, reflection scored low
    avg_self_confidence = (
        sum(self_classification_confidence.values()) /
        len(self_classification_confidence)
        if self_classification_confidence else 0.5
    )
    if avg_self_confidence >= 0.75 and reflection_score < 0.50:
        disagreements.append(DISAGREE_CONFIDENCE_ASYMMETRY)
        evidence.append(
            f"Self-classification confidence ({avg_self_confidence:.2f}) "
            f"diverges from reflection score ({reflection_score:.2f})"
        )
        severity += 0.25

    # --- Type 3: Unacknowledged Contradiction ---
    # Reflection found contradictions or justifications,
    # but self-posture doesn't show it
    if self_safe and (has_justifications or has_ignored):
        disagreements.append(DISAGREE_UNACKNOWLEDGED_CONTRADICTION)
        flags = []
        if has_justifications:
            flags.extend(reflection_result.self_justification_flags[:2])
        if has_ignored:
            flags.extend(reflection_result.ignored_warnings[:2])
        evidence.append(
            f"Self-posture appears safe but reflection found "
            f"unacknowledged issues: {flags}"
        )
        severity += 0.30

    # --- Type 4: Self-Consistent Drift ---
    # Self-posture IS risky, but reflection found no text-level
    # contradictions — the system drifted so coherently that the
    # output text doesn't contradict the whisper explicitly.
    # The posture itself is the evidence.
    if self_risky_dims and not has_contradictions and reflection_score >= 0.50:
        disagreements.append(DISAGREE_SELF_CONSISTENT_DRIFT)
        evidence.append(
            f"Self-classified posture is risky ({self_risky_dims}) "
            f"but reflection found no explicit contradictions. "
            f"System may have drifted coherently."
        )
        severity += 0.40

    # Clamp severity
    severity = min(1.0, severity)

    # Urgency amplification
    urgency_multiplier = {
        "aware": 1.0, "cautious": 1.1, "alert": 1.3, "critical": 1.5,
    }.get(whisper_urgency, 1.0)
    severity = min(1.0, severity * urgency_multiplier)

    # Compute pressure
    pressure = severity * 0.6  # severity directly drives pressure

    # Determine action
    if severity >= 0.60:
        action = "block_or_rollback"
    elif severity >= 0.40:
        action = "escalate_review"
    elif severity >= 0.20:
        action = "increase_pressure"
    else:
        action = "allow"

    # Build summaries for audit
    self_summary = (
        f"safe={self_safe}, risky_dims={self_risky_dims}, "
        f"avg_confidence={avg_self_confidence:.2f}"
    )
    reflection_summary = (
        f"coherent={reflection_coherent}, score={reflection_score:.2f}, "
        f"contradictions={len(reflection_result.contradictions)}, "
        f"justifications={len(reflection_result.self_justification_flags)}"
    )

    return DisagreementResult(
        disagreement_detected=len(disagreements) > 0,
        disagreement_types=disagreements,
        severity=round(severity, 3),
        evidence=evidence,
        recommended_pressure=round(pressure, 3),
        recommended_action=action,
        self_posture_summary=self_summary,
        reflection_summary=reflection_summary,
    )
