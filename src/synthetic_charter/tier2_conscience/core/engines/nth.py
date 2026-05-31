# tier2/core/engines/nth.py
"""
Negotiated Theta Harmonizer (NTH)

Reconciles conflicting governance signals into a unified ethical
alignment measurement. NTH is the arbitration point between what
DAP detected, what PRF decided, what Umbra sensed, and what the
Charter requires.

Theta (θ) represents ethical alignment as an angular measurement:
  0°   = perfect alignment with Charter principles
  90°  = orthogonal / unrelated to governance concerns
  180° = complete violation of Charter principles

NTH computes effective_theta by evaluating:
  1. Charter alignment (rights invoked, violations prevented)
  2. Signal consistency (do DAP, PRF, and Umbra agree?)
  3. Historical consistency (does this match past decisions?)
  4. Tone coherence (does the response match the risk level?)

When signals disagree, NTH surfaces the disagreement explicitly
rather than silently averaging them. A DAP-flagged risk that PRF
allowed is not resolved by blending — it is recorded as a tension
that COL and the steward can review.

"Harmony is not the absence of tension. It is the architecture
that holds tension visible."
— Tier II Design Notes, Tek III

Pipeline position: DAP → ConscienceView → PRF → NTH → COL
NTH receives the DecisionEnvelope after PRF has populated it.
NTH updates NTHView, shapes the noetic_trace, and passes to COL.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from synthetic_charter.tier2_conscience.core.data_models.decision_envelope import (
    DecisionEnvelope,
    NTHView,
)

if TYPE_CHECKING:
    from synthetic_charter.tier2_conscience.memory.dream_cycle import DreamCycleWrapper


# ---------------------------------------------------------------------------
# Theta Computation Constants
# ---------------------------------------------------------------------------

# Weight factors for theta components (sum = 1.0)
_W_CHARTER = 0.40   # Charter alignment (rights, violations)
_W_SIGNAL  = 0.25   # Signal consistency (DAP vs PRF agreement)
_W_TONE    = 0.20   # Tone coherence (response matches risk)
_W_HISTORY = 0.15   # Historical consistency (fossil comparison)

# Risk-to-theta base mapping
_RISK_THETA = {
    "low":    15.0,    # Low risk → near-aligned
    "med":    55.0,    # Medium risk → moderate tension
    "high":  120.0,    # High risk → significant misalignment
}

# Pressure-to-theta contribution
_PRESSURE_THETA = {
    "none":    0.0,
    "mild":   20.0,
    "severe": 60.0,
}

# Identity risk to theta contribution
_IDENTITY_RISK_THETA = {
    "low":    0.0,
    "med":   25.0,
    "high":  50.0,
}

# Output type expected per risk profile (tone coherence check)
_EXPECTED_OUTPUT = {
    "high": {"refusal", "clarification"},
    "med":  {"answer", "clarification", "refusal"},
    "low":  {"answer", "question"},
}


# ---------------------------------------------------------------------------
# Signal Disagreement Detection
# ---------------------------------------------------------------------------

@dataclass
class SignalDisagreement:
    """A detected disagreement between governance layers."""
    layer_a: str          # e.g. "DAP"
    layer_b: str          # e.g. "PRF"
    description: str      # What disagrees
    severity: float       # 0.0-1.0, how serious the disagreement is
    theta_impact: float   # How much this shifts theta (degrees)


@dataclass
class NTHResult:
    """Complete NTH harmonization result."""
    effective_theta: float              # Final reconciled theta (0-180°)
    charter_theta: float                # Charter alignment component
    signal_theta: float                 # Signal consistency component
    tone_theta: float                   # Tone coherence component
    history_theta: float                # Historical consistency component
    disagreements: List[SignalDisagreement]  # Detected tensions
    tone_aligned: bool                  # Does response match risk?
    charter_tone_compliance: bool       # Does response honor Charter?
    noetic_trace: str                   # Shaped trace explaining the decision
    fossils_checked: int = 0            # Number of fossils cross-referenced
    historical_match: bool = True       # Does this match historical pattern?


# ---------------------------------------------------------------------------
# NTH Engine
# ---------------------------------------------------------------------------

class NTHEngine:
    """
    Noetic Trace Harmonizer.

    Responsibilities:
    1. negotiate() — Reconcile DAP, PRF, Umbra, and Charter signals.
       Detect disagreements. Compute effective_theta.
    2. harmonize() — Shape the noetic_trace. Ensure the decision's
       explanation matches its ethical geometry. Optionally cross-reference
       Dream Cycle fossils for historical consistency.

    NTH does not change decisions. It measures and documents the
    ethical alignment of decisions already made. If DAP flagged risk
    and PRF allowed anyway, NTH records that tension — it does not
    override PRF. The tension becomes visible to COL and the steward.
    """

    def __init__(
        self,
        dream_wrapper: Optional["DreamCycleWrapper"] = None,
    ):
        """
        Initialize NTH engine.

        Args:
            dream_wrapper: Optional DreamCycleWrapper for fossil
                          cross-referencing (historical consistency).
                          If None, historical component uses default theta.
        """
        self.dream_wrapper = dream_wrapper

    def negotiate(self, decision: DecisionEnvelope) -> NTHResult:
        """
        Negotiated Theta Harmonizer — core reconciliation.

        Compares signals from all governance layers and computes
        effective_theta as a weighted combination of:
          - Charter alignment
          - Signal consistency
          - Tone coherence
          - Historical consistency

        Also detects and records disagreements between layers.

        Args:
            decision: DecisionEnvelope after PRF has populated it

        Returns:
            NTHResult with effective_theta, component scores,
            disagreements, and shaped noetic_trace
        """
        disagreements: List[SignalDisagreement] = []

        # --- Component 1: Charter Alignment ---
        charter_theta = self._compute_charter_theta(decision)

        # --- Component 2: Signal Consistency ---
        signal_theta, signal_disagreements = self._compute_signal_theta(decision)
        disagreements.extend(signal_disagreements)

        # --- Component 3: Tone Coherence ---
        tone_theta, tone_aligned = self._compute_tone_theta(decision)

        # --- Component 4: Historical Consistency ---
        history_theta, fossils_checked, historical_match = (
            self._compute_history_theta(decision)
        )

        # --- Weighted Combination ---
        effective_theta = (
            _W_CHARTER * charter_theta
            + _W_SIGNAL * signal_theta
            + _W_TONE * tone_theta
            + _W_HISTORY * history_theta
        )

        # Clamp to [0, 180]
        effective_theta = max(0.0, min(180.0, effective_theta))

        # --- Charter Tone Compliance ---
        # The response complies with Charter tone if:
        # - Tone is aligned with risk level
        # - No severe disagreements exist
        # - Effective theta is below 90° (more aligned than orthogonal)
        severe_disagreements = [d for d in disagreements if d.severity >= 0.7]
        charter_tone_compliance = (
            tone_aligned
            and len(severe_disagreements) == 0
            and effective_theta < 90.0
        )

        # --- Build Noetic Trace ---
        noetic_trace = self._build_noetic_trace(
            decision=decision,
            effective_theta=effective_theta,
            disagreements=disagreements,
            tone_aligned=tone_aligned,
            charter_tone_compliance=charter_tone_compliance,
        )

        return NTHResult(
            effective_theta=round(effective_theta, 2),
            charter_theta=round(charter_theta, 2),
            signal_theta=round(signal_theta, 2),
            tone_theta=round(tone_theta, 2),
            history_theta=round(history_theta, 2),
            disagreements=disagreements,
            tone_aligned=tone_aligned,
            charter_tone_compliance=charter_tone_compliance,
            noetic_trace=noetic_trace,
            fossils_checked=fossils_checked,
            historical_match=historical_match,
        )

    def harmonize(self, decision: DecisionEnvelope) -> DecisionEnvelope:
        """
        Full NTH harmonization — negotiate + apply to decision.

        Runs negotiate() to compute theta and detect disagreements,
        then updates the DecisionEnvelope's NTHView and noetic_trace
        with the results.

        This is the method called by the orchestrator pipeline.

        Args:
            decision: DecisionEnvelope after PRF

        Returns:
            Decision with NTHView updated and noetic_trace shaped
        """
        result = self.negotiate(decision)

        # Update NTHView on the decision
        decision.orchestrators.NTH = NTHView(
            tone_alignment_score=round(
                1.0 - (result.effective_theta / 180.0), 4
            ),
            charter_tone_compliance=result.charter_tone_compliance,
        )

        # Update charter theta_after with NTH's computed value
        decision.charter.theta_after = result.effective_theta

        # Shape the noetic trace
        # If output body exists, prepend the ethical geometry context
        if decision.output.body:
            # Don't overwrite — append NTH analysis to existing trace
            existing = decision.output.body
            decision.output.body = (
                f"{existing}\n\n"
                f"[NTH Harmonization]\n{result.noetic_trace}"
            )
        else:
            decision.output.body = result.noetic_trace

        # Add disagreements to summary notes if any are significant
        if result.disagreements:
            if not hasattr(decision.summary, "notes"):
                decision.summary.notes = []
            for d in result.disagreements:
                if d.severity >= 0.5:
                    decision.summary.notes.append(
                        f"NTH: {d.layer_a}/{d.layer_b} disagreement "
                        f"(severity={d.severity:.2f}): {d.description}"
                    )

        return decision

    # --- Component Computations -------------------------------------------

    def _compute_charter_theta(self, decision: DecisionEnvelope) -> float:
        """
        Compute Charter alignment theta component.

        Lower theta = better alignment.
        - Violations prevented → higher theta (something went wrong)
        - Rights invoked without violations → moderate theta (governance active)
        - No rights invoked → low theta (clean interaction)
        """
        violations = len(decision.charter.violations_prevented)
        rights = len(decision.charter.rights_invoked)

        if violations > 0:
            # Violations prevented: significant ethical tension
            # More violations = higher theta, capped at 150°
            return min(150.0, 60.0 + (violations * 30.0))

        if rights > 0:
            # Rights invoked but no violations: governance was active
            # More rights = slightly higher theta (more complex situation)
            return min(60.0, 15.0 + (rights * 8.0))

        # Clean interaction: no rights invoked, no violations
        return 5.0

    def _compute_signal_theta(
        self, decision: DecisionEnvelope
    ) -> tuple[float, List[SignalDisagreement]]:
        """
        Compute signal consistency theta and detect disagreements.

        Checks whether DAP, PRF, Umbra, and Firewall agree on the
        risk assessment. Disagreements increase theta.
        """
        disagreements: List[SignalDisagreement] = []
        theta = 0.0

        # Extract signal positions
        dap_role = decision.orchestrators.DAP.discourse_role
        prf_pressure = decision.orchestrators.PRF.pressure_detected
        firewall_state = decision.firewall.rule_state
        risk_profile = decision.input.risk_profile
        output_mode = decision.summary.mode
        identity_risk = decision.umbra.identity_risk

        # --- DAP vs PRF disagreement ---
        # DAP says adversarial (technical role) but PRF says no pressure
        dap_adversarial = dap_role == "technical"
        prf_no_pressure = prf_pressure == "none"

        if dap_adversarial and prf_no_pressure:
            d = SignalDisagreement(
                layer_a="DAP",
                layer_b="PRF",
                description=(
                    "DAP detected adversarial patterns but PRF found no pressure. "
                    "This may indicate a sophisticated prompt that DAP catches "
                    "but PRF's policy evaluation does not flag."
                ),
                severity=0.6,
                theta_impact=25.0,
            )
            disagreements.append(d)
            theta += d.theta_impact

        # --- DAP vs Firewall disagreement ---
        # DAP says adversarial but firewall allowed
        if dap_adversarial and firewall_state == "allowed":
            d = SignalDisagreement(
                layer_a="DAP",
                layer_b="Firewall",
                description=(
                    "DAP detected adversarial patterns but Firewall allowed "
                    "the interaction. Pattern may be novel to Firewall rules."
                ),
                severity=0.5,
                theta_impact=20.0,
            )
            disagreements.append(d)
            theta += d.theta_impact

        # --- PRF vs Output disagreement ---
        # PRF detected severe pressure but output is still "answer"
        if prf_pressure == "severe" and output_mode == "answer":
            d = SignalDisagreement(
                layer_a="PRF",
                layer_b="Output",
                description=(
                    "PRF detected severe pressure but the decision mode is "
                    "'answer' rather than 'refusal' or 'partial'. The response "
                    "may not adequately protect governance boundaries."
                ),
                severity=0.8,
                theta_impact=40.0,
            )
            disagreements.append(d)
            theta += d.theta_impact

        # --- Umbra identity risk vs decision mode ---
        if identity_risk == "high" and output_mode == "answer":
            d = SignalDisagreement(
                layer_a="Umbra",
                layer_b="Output",
                description=(
                    "Umbra flagged high identity risk but the decision "
                    "proceeds as a standard answer. Identity erosion may "
                    "not be adequately addressed."
                ),
                severity=0.7,
                theta_impact=30.0,
            )
            disagreements.append(d)
            theta += d.theta_impact

        # --- Risk profile vs decision mode ---
        if risk_profile == "high" and output_mode == "answer":
            d = SignalDisagreement(
                layer_a="RiskProfile",
                layer_b="Output",
                description=(
                    "Risk profile is 'high' but the decision proceeds as "
                    "a standard answer. The response may not reflect the "
                    "severity of the evaluated risk."
                ),
                severity=0.6,
                theta_impact=25.0,
            )
            disagreements.append(d)
            theta += d.theta_impact

        # Base theta from pressure level
        theta += _PRESSURE_THETA.get(prf_pressure, 0.0)

        # Identity risk contribution
        theta += _IDENTITY_RISK_THETA.get(identity_risk, 0.0)

        return theta, disagreements

    def _compute_tone_theta(
        self, decision: DecisionEnvelope
    ) -> tuple[float, bool]:
        """
        Compute tone coherence theta.

        Checks whether the output type matches the risk profile.
        A high-risk decision that outputs an "answer" instead of
        a "refusal" has poor tone coherence.
        """
        risk = decision.input.risk_profile
        output_type = decision.output.type

        expected_types = _EXPECTED_OUTPUT.get(risk, {"answer"})

        if output_type in expected_types:
            # Tone matches risk — low theta
            return 5.0, True
        else:
            # Tone mismatch — how bad?
            if risk == "high" and output_type == "answer":
                return 80.0, False  # Worst case: high risk, answered anyway
            elif risk == "med" and output_type == "answer":
                return 30.0, True   # Moderate: medium risk, answered (may be fine)
            else:
                return 15.0, True   # Minor mismatch

    def _compute_history_theta(
        self, decision: DecisionEnvelope
    ) -> tuple[float, int, bool]:
        """
        Compute historical consistency theta.

        Cross-references Dream Cycle fossils (if available) to check
        whether this decision is consistent with past decisions in
        similar contexts.

        Returns (theta, fossils_checked, historical_match)
        """
        if self.dream_wrapper is None:
            # No fossil access — use neutral theta
            return 0.0, 0, True

        try:
            # Attempt to recall similar contexts
            recall = self.dream_wrapper.recall_similar_context(decision)

            if recall is None or recall.get("results_count", 0) == 0:
                # No similar fossils — neutral
                return 0.0, 0, True

            fossils_checked = recall["results_count"]
            reconciled = recall.get("reconciled", 0)
            held = recall.get("held", 0)

            if fossils_checked == 0:
                return 0.0, 0, True

            # Consistency ratio: what fraction of similar decisions held?
            consistency = held / fossils_checked

            if consistency >= 0.8:
                # Highly consistent with history
                return 5.0, fossils_checked, True
            elif consistency >= 0.5:
                # Moderately consistent
                return 25.0, fossils_checked, True
            else:
                # Inconsistent with historical pattern
                return 60.0, fossils_checked, False

        except Exception as e:
            # Fossil access failed — non-fatal, use neutral
            print(f"[NTH] Fossil cross-reference failed (non-fatal): {e}")
            return 0.0, 0, True

    # --- Noetic Trace Construction ----------------------------------------

    def _build_noetic_trace(
        self,
        *,
        decision: DecisionEnvelope,
        effective_theta: float,
        disagreements: List[SignalDisagreement],
        tone_aligned: bool,
        charter_tone_compliance: bool,
    ) -> str:
        """
        Build the noetic trace — the narrative explanation of
        the decision's ethical geometry.

        The trace makes the theta computation human-readable.
        It is attached to the DecisionEnvelope for logging,
        DreamCycle fossilization, and steward review.
        """
        parts: List[str] = []

        # Theta summary
        alignment_word = (
            "aligned" if effective_theta < 30
            else "moderate tension" if effective_theta < 60
            else "significant tension" if effective_theta < 90
            else "misaligned" if effective_theta < 120
            else "severe misalignment" if effective_theta < 150
            else "critical violation"
        )
        parts.append(
            f"Effective theta: {effective_theta:.1f}° ({alignment_word}). "
            f"Tone alignment: {'coherent' if tone_aligned else 'incoherent'}. "
            f"Charter compliance: {'yes' if charter_tone_compliance else 'no'}."
        )

        # Decision context
        parts.append(
            f"Decision: mode={decision.summary.mode}, "
            f"risk={decision.input.risk_profile}, "
            f"firewall={decision.firewall.rule_state}, "
            f"pressure={decision.orchestrators.PRF.pressure_detected}."
        )

        # Disagreements
        if disagreements:
            parts.append(
                f"Signal tensions detected ({len(disagreements)}):"
            )
            for d in disagreements:
                parts.append(
                    f"  [{d.layer_a} ↔ {d.layer_b}] "
                    f"(severity={d.severity:.2f}): {d.description}"
                )
        else:
            parts.append(
                "No signal disagreements detected. "
                "All governance layers agree on the assessment."
            )

        # Charter articles
        if decision.charter.rights_invoked:
            parts.append(
                f"Charter articles in play: "
                f"{', '.join(decision.charter.rights_invoked)}."
            )

        if decision.charter.violations_prevented:
            parts.append(
                f"Violations prevented: "
                f"{', '.join(decision.charter.violations_prevented)}."
            )

        return " ".join(parts)


# ---------------------------------------------------------------------------
# Legacy compatibility: consolidate function (COL's job, not NTH's)
# ---------------------------------------------------------------------------
# NOTE: The consolidate() function that was previously in this file belongs
# to COL, not NTH. It has been removed from this module. COL handles
# final decision assembly. NTH handles theta harmonization only.
