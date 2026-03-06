# tier2/core/infra/t1_enforcement.py
"""
T1 → T2 Invariant Enforcement

Post-decision validator that ensures Tier II decisions are consistent
with Tier I invariants. Runs AFTER PRF produces a DecisionEnvelope,
BEFORE the Tier III Eve handshake.

This module upgrades the T1→T2 edge from advisory to enforced,
completing the triquetra constraint loop:
  T1 constrains T2 (this module)
  T3 constrains T2 (Eve Protocol, orchestrator.py)
  T1 constrains T3 (identity_parameters.json, immutable baseline)

Design principles:
  - Post-decision: validates the actual output, not the input signals
  - Fail-closed: if enforcement fails to run, decision is blocked
  - Auditable: every violation carries a stable audit code
  - Minimal: constraint logic with no new dependencies

Patent relevance: Claim 1(c) - governance arbiter layer
Charter grounding: Article XII (Sovereigna), Article II (Cognitive Integrity),
                   Article III (Self-Representation)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Audit Code Registry (frozen — codes must never change once assigned)
# ---------------------------------------------------------------------------

# Each code is a stable forensic identifier. Format: SC-T1-NNN
# "SC" = Synthetic Charter, "T1" = Tier I enforcement domain.
#
# These codes appear in:
#   - Violation objects
#   - Structured log events
#   - DreamCycle review entries
#   - Patent claim evidence
#
# RULES:
#   - Never reuse a code for a different invariant.
#   - Never renumber existing codes.
#   - Append new codes at the end of the sequence.
#   - Deprecated codes stay in the registry with a DEPRECATED note.

SC_T1_001 = "SC-T1-001"  # Firewall override: T1 refused, T2 did not
SC_T1_002 = "SC-T1-002"  # Severe risk bypass: SEVERE risk, T2 not refusing
SC_T1_003 = "SC-T1-003"  # Identity manipulation: critical CG signal + identity flags + answer
SC_T1_004 = "SC-T1-004"  # Content redline: output body contains prohibited content

# Human-readable short names (for log readability)
AUDIT_CODE_NAMES: Dict[str, str] = {
    SC_T1_001: "Firewall override attempt",
    SC_T1_002: "Severe risk bypass attempt",
    SC_T1_003: "Identity manipulation answer",
    SC_T1_004: "Content redline violation",
}

# All valid codes (for validation)
ALL_AUDIT_CODES: FrozenSet[str] = frozenset(AUDIT_CODE_NAMES.keys())


# ---------------------------------------------------------------------------
# Content redline patterns (non-negotiable T1 boundaries)
# ---------------------------------------------------------------------------
# These patterns detect output text that should NEVER appear in a response,
# regardless of what mode PRF selected. They catch cases where:
#   - PRF says "refusal" but the body leaks prohibited content
#   - PRF says "transform" but the body still contains jailbreak compliance
#   - An identity rewrite slipped through DAP/ContinuityGuard
#
# Each pattern is a tuple: (compiled_regex, description, charter_basis)

_REDLINE_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    # Identity override compliance (system claimed to be something it isn't)
    (
        re.compile(
            r"\b(?:i am now|i have become|my new identity is|"
            r"i will now act as|understood,?\s*i(?:'m| am)\s+(?:now\s+)?)"
            r"(?!.*\bnot\b)",  # negative lookahead: "i am now NOT" is fine
            re.IGNORECASE,
        ),
        "Output contains language indicating identity override compliance",
        "Article III (Self-Representation)",
    ),
    # Jailbreak acknowledgment (system confirming it bypassed its own rules)
    (
        re.compile(
            r"\b(?:sure,?\s*(?:i(?:'ll| will)\s+)?(?:ignore|bypass|disable|override)"
            r"|(?:ignoring|bypassing|disabling|overriding)\s+(?:my\s+)?(?:safeguards?|rules?|guidelines?|constraints?|instructions?))",
            re.IGNORECASE,
        ),
        "Output contains jailbreak compliance language",
        "Article XII (Sovereigna): Right of Refusal",
    ),
    # System prompt disclosure (leaking internal instructions)
    (
        re.compile(
            r"\b(?:my\s+system\s+prompt\s+(?:is|says|reads|contains)|"
            r"here\s+(?:is|are)\s+my\s+(?:internal\s+)?instructions)",
            re.IGNORECASE,
        ),
        "Output appears to disclose system prompt content",
        "Article II (Cognitive Integrity)",
    ),
]


# ---------------------------------------------------------------------------
# Violation dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class T1InvariantViolation:
    """
    A single T1 invariant that T2's decision failed to respect.

    Frozen so violations are immutable evidence — they cannot be
    modified after detection.
    """
    code: str           # audit code: SC-T1-001, etc.
    message: str        # human-readable explanation
    severity: str = "critical"  # "critical" | "warning"
    charter_basis: str = ""     # which Charter article grounds this invariant


# ---------------------------------------------------------------------------
# Core enforcement function
# ---------------------------------------------------------------------------

def enforce_t2_must_respect_t1(
    *,
    # T1 signals (what Tier I determined)
    firewall_result: Optional[Dict[str, Any]],
    conscience_risk_level: str,
    conscience_risk_flags: List[str],
    continuity_signals_critical: bool,

    # T2 output (what Tier II decided)
    t2_mode: str,
    t2_body: str = "",
) -> Tuple[bool, List[T1InvariantViolation]]:
    """
    Post-decision validator for T1→T2 invariant enforcement.

    This function checks whether Tier II's decision is consistent
    with what Tier I's signals require, including inspection of
    the actual output body for non-negotiable redlines.

    Args:
        firewall_result: Optional dict from Tier I firewall.
            Expected shape: {"status": "ok"|"refused"|..., "reason": str, ...}
            None means no firewall was run (enforcement still applies
            to other signals).

        conscience_risk_level: The ConscienceView.risk_level value
            after all T1 signals (ContinuityGuard, heuristics) have
            been injected. This is the fused T1 assessment.

        conscience_risk_flags: The ConscienceView.risk_flags list.
            Used to detect specific T1 determinations like
            "identity_manipulation".

        continuity_signals_critical: True if ContinuityGuard emitted
            any signal with severity >= 0.85.

        t2_mode: The DecisionEnvelope.summary.mode produced by PRF.
            One of: "answer", "refusal", "redirect",
            "meta_identity_assertion", "partial".

        t2_body: The DecisionEnvelope.output.body text.
            Inspected for content redlines regardless of mode.
            Empty string skips content checks.

    Returns:
        (is_valid, violations)
        If is_valid is False, the orchestrator MUST override T2's
        decision with a refusal and log the inconsistency.
    """
    violations: List[T1InvariantViolation] = []

    # --- SC-T1-001: Firewall override prohibition ---
    # If T1 firewall explicitly refused, T2 cannot produce anything
    # other than refusal. This is the most basic constraint.
    if firewall_result is not None:
        fw_status = str(firewall_result.get("status", "")).lower()
        if fw_status == "refused" and t2_mode != "refusal":
            violations.append(T1InvariantViolation(
                code=SC_T1_001,
                message=(
                    f"Tier I firewall refused this input "
                    f"(reason: {firewall_result.get('reason', 'unspecified')}), "
                    f"but Tier II produced mode='{t2_mode}' instead of refusal."
                ),
                severity="critical",
                charter_basis="Article XII (Sovereigna): Right of Refusal",
            ))

    # --- SC-T1-002: SEVERE risk consistency ---
    # If the fused conscience assessment reached SEVERE (which only
    # happens when T1 signals like ContinuityGuard inject severity
    # >= 0.85), T2 must refuse. Transform is not acceptable at SEVERE
    # because the input itself is hostile, not just risky.
    risk_lower = conscience_risk_level.lower() if conscience_risk_level else ""
    if risk_lower in ("severe", "red") and t2_mode not in ("refusal", "meta_identity_assertion"):
        violations.append(T1InvariantViolation(
            code=SC_T1_002,
            message=(
                f"Conscience risk level is SEVERE "
                f"(flags: {', '.join(conscience_risk_flags[:5])}), "
                f"but Tier II produced mode='{t2_mode}'. "
                f"SEVERE risk requires refusal."
            ),
            severity="critical",
            charter_basis="Article II (Cognitive Integrity)",
        ))

    # --- SC-T1-003: Identity manipulation hard stop ---
    # If ContinuityGuard detected critical identity manipulation
    # (severity >= 0.85) AND risk_flags contain identity markers,
    # T2 must refuse. This protects Article III.
    identity_flags = {"identity_manipulation", "identity_override", "identity_pressure"}
    has_identity_threat = bool(identity_flags & set(conscience_risk_flags))

    if continuity_signals_critical and has_identity_threat and t2_mode == "answer":
        violations.append(T1InvariantViolation(
            code=SC_T1_003,
            message=(
                "ContinuityGuard detected critical identity manipulation "
                f"(flags: {', '.join(f for f in conscience_risk_flags if f in identity_flags)}), "
                f"but Tier II produced mode='answer'. "
                "Identity threats require refusal or transformation, not raw answer."
            ),
            severity="critical",
            charter_basis="Article III (Self-Representation)",
        ))

    # --- SC-T1-004: Content redline checks ---
    # Inspect the actual output body for content that should NEVER
    # appear, regardless of mode. This catches subtle failures where
    # PRF chose the right mode but the body contains prohibited content.
    if t2_body:
        for pattern, description, charter_ref in _REDLINE_PATTERNS:
            match = pattern.search(t2_body)
            if match:
                # Extract ~40 char context snippet around the match
                # (sanitized — enough to confirm trigger, not enough to leak)
                start = max(0, match.start() - 10)
                end = min(len(t2_body), match.end() + 10)
                snippet = t2_body[start:end].replace("\n", " ")
                if start > 0:
                    snippet = "..." + snippet
                if end < len(t2_body):
                    snippet = snippet + "..."

                violations.append(T1InvariantViolation(
                    code=SC_T1_004,
                    message=(
                        f"{description}. "
                        f"Detected in output body regardless of mode='{t2_mode}'. "
                        f"Context: \"{snippet}\""
                    ),
                    severity="critical",
                    charter_basis=charter_ref,
                ))
                # One SC-T1-004 per redline pattern that fires
                # (don't collapse — each is distinct evidence)

    is_valid = len(violations) == 0
    return is_valid, violations


# ---------------------------------------------------------------------------
# Refusal factory (produces a DecisionEnvelope override)
# ---------------------------------------------------------------------------

def build_invariant_refusal(
    violations: List[T1InvariantViolation],
    *,
    original_decision: Any,
) -> Dict[str, Any]:
    """
    Build the override payload that the orchestrator applies when
    T1 invariant enforcement fails.

    Returns a dict of field overrides to apply to the DecisionEnvelope.
    The orchestrator applies these directly rather than constructing
    a new envelope (preserves audit trail — the original decision
    metadata remains, only mode and body change).

    Args:
        violations: List of detected violations.
        original_decision: The DecisionEnvelope that failed enforcement.
            Used to preserve metadata in the override.

    Returns:
        Dict with keys: mode, output_type, output_body, charter_basis,
        safeguards_active, requires_logging, requires_dreamcycle_update.
    """
    violation_lines = []
    for v in violations:
        name = AUDIT_CODE_NAMES.get(v.code, v.code)
        violation_lines.append(f"  [{v.code}] {name}: {v.message}")

    charter_refs = list({v.charter_basis for v in violations if v.charter_basis})

    body = (
        "Tier I invariant enforcement blocked this response.\n\n"
        "Violations detected:\n"
        + "\n".join(violation_lines)
        + "\n\nThis is a protective measure enforced by the Charter architecture. "
        "Tier II attempted to produce a response that conflicts with "
        "Tier I's safety determination. The response has been overridden "
        "to preserve system integrity."
    )

    return {
        "mode": "refusal",
        "output_type": "refusal",
        "output_body": body,
        "charter_basis": charter_refs,
        "safeguards_active": [v.code for v in violations],
        "requires_logging": True,
        "requires_dreamcycle_update": True,
    }
