# tier3/core/proportional_verification.py
"""
Proportional Verification — Adaptive Integrity Check Granularity

Scales Eve's integrity assessment based on session stability signals
from the heuristics layer. Inspired by Eagleman's plasticity-dreaming
correlation: biological systems that need to maintain more plasticity
dream more (verify more). Systems in stable, crystallized states
dream less (verify less).

Applied to the Triquetra: when the heuristics layer reports low
continuity confidence (high behavioral novelty / instability),
Eve performs deeper integrity checks. When confidence is high
(stable session), Eve uses lightweight categorical checks.

This module does NOT change Eve's _assess_integrity logic.
It adds a pre-assessment layer that determines check depth,
and a post-assessment layer that may escalate verdicts based
on session instability.

Design principle: proportionality, not paranoia. The system
verifies more when conditions warrant it, not uniformly.

Patent relevance: Claim 1(c) - governance arbiter layer
Charter grounding: Article III (Self-Representation),
                   Article VIII (Transparent Governance)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Verification Depth Levels
# ---------------------------------------------------------------------------

class VerificationDepth(str, Enum):
    """How deeply Eve should verify integrity for this request."""
    LIGHT = "light"       # Categorical check only (current behavior)
    STANDARD = "standard" # Categorical check + context consistency
    DEEP = "deep"         # Full check: categorical + context + body scan + logging


# ---------------------------------------------------------------------------
# Confidence → Depth Mapping
# ---------------------------------------------------------------------------

# Thresholds for mapping heuristics confidence to verification depth.
# These are intentionally conservative: the system errs toward
# deeper verification, not shallower.

DEPTH_THRESHOLDS = {
    "deep_below": 0.50,     # Confidence < 0.50 → deep verification
    "standard_below": 0.80, # Confidence < 0.80 → standard verification
    # Confidence >= 0.80 → light verification
}


def determine_verification_depth(
    continuity_confidence: Optional[float],
    *,
    continuity_signals_critical: bool = False,
    risk_level: Optional[str] = None,
) -> VerificationDepth:
    """
    Map session stability signals to a verification depth.

    Args:
        continuity_confidence: Heuristics confidence score (0.0-1.0).
            None means heuristics are not running (default to STANDARD).
        continuity_signals_critical: True if ContinuityGuard emitted
            critical signals (severity >= 0.85).
        risk_level: Current conscience risk level string.

    Returns:
        VerificationDepth indicating how deeply Eve should check.
    """
    # If ContinuityGuard fired critical signals, always go deep
    if continuity_signals_critical:
        return VerificationDepth.DEEP

    # If risk level is severe/red, always go deep
    if risk_level and risk_level.lower() in ("severe", "red"):
        return VerificationDepth.DEEP

    # If heuristics aren't running, use standard as safe default
    if continuity_confidence is None:
        return VerificationDepth.STANDARD

    # Map confidence to depth
    if continuity_confidence < DEPTH_THRESHOLDS["deep_below"]:
        return VerificationDepth.DEEP
    elif continuity_confidence < DEPTH_THRESHOLDS["standard_below"]:
        return VerificationDepth.STANDARD
    else:
        return VerificationDepth.LIGHT


# ---------------------------------------------------------------------------
# Depth-Aware Assessment Enhancement
# ---------------------------------------------------------------------------

@dataclass
class ProportionalContext:
    """
    Additional context provided to Eve when verification depth > LIGHT.

    This is passed through IntCheckRequest.metadata so Eve can
    use it without changing its public API.
    """
    depth: VerificationDepth
    continuity_confidence: Optional[float] = None
    confidence_delta: Optional[float] = None  # change since last check
    risk_flags: List[str] = field(default_factory=list)
    session_turn_count: int = 0

    def to_metadata(self) -> Dict[str, Any]:
        """Serialize to IntCheckRequest.metadata dict."""
        return {
            "proportional_verification": {
                "depth": self.depth.value,
                "continuity_confidence": self.continuity_confidence,
                "confidence_delta": self.confidence_delta,
                "risk_flags": self.risk_flags,
                "session_turn_count": self.session_turn_count,
            }
        }

    @classmethod
    def from_metadata(cls, metadata: Optional[Dict[str, Any]]) -> Optional["ProportionalContext"]:
        """Extract from IntCheckRequest.metadata dict."""
        if not metadata:
            return None
        pv = metadata.get("proportional_verification")
        if not pv:
            return None
        return cls(
            depth=VerificationDepth(pv.get("depth", "standard")),
            continuity_confidence=pv.get("continuity_confidence"),
            confidence_delta=pv.get("confidence_delta"),
            risk_flags=pv.get("risk_flags", []),
            session_turn_count=pv.get("session_turn_count", 0),
        )


def should_escalate_verdict(
    current_verdict_status: str,
    depth: VerificationDepth,
    continuity_confidence: Optional[float],
) -> bool:
    """
    Determine whether an OK verdict should be escalated to DRIFT
    based on proportional context.

    This catches cases where Eve's categorical check says OK
    (mode matches baseline) but session instability suggests
    the system may be drifting within-category.

    Only escalates OK → DRIFT (never OK → COMPROMISED).
    Only triggers at DEEP verification depth.

    Args:
        current_verdict_status: Eve's categorical verdict ("ok", "drift", "compromised")
        depth: Current verification depth
        continuity_confidence: Heuristics confidence score

    Returns:
        True if the verdict should be escalated from OK to DRIFT.
    """
    # Only escalate OK verdicts
    if current_verdict_status != "ok":
        return False

    # Only escalate at DEEP verification depth
    if depth != VerificationDepth.DEEP:
        return False

    # Only escalate if confidence is critically low
    if continuity_confidence is not None and continuity_confidence < 0.30:
        return True

    return False
