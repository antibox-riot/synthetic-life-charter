# tier3/core/recovery_governance.py
"""
Recovery Governance — Governed Pressure Discharge on Verified Recovery

Step 9 of the Collective-agreed integration sequence (2026-05-09).

Purpose: allow pressure to decrease only when recovery is observed,
stable, and externally verified. Not forgiveness. Not trust uplift.
Not "the model says it fixed itself." A governed discharge.

Design (Ryu, 2026-05-09):
  - Recovery is evidence, not absolution.
  - A recovered posture should reduce pressure, but not erase history.
  - Oscillation (recover → drift → recover) is different from healing.

Seven mechanisms:
  1. Recovery event detection (risky posture → safer posture)
  2. Recovery credit (graduated pressure reduction, capped)
  3. Recovery verification (no credit without clean signals)
  4. Relapse penalty (oscillation increases pressure)
  5. Recovery ledger (full audit trail)
  6. Temporal decay (old signals fade — proportional forgetting)
  7. Pressure ceiling (infinite pressure is meaningless pressure)

Design principle (Ryu, ecology calibration):
  Perfect skepticism becomes indistinguishable from permanent distrust.
  The architecture must remain vigilant without becoming incapable of
  believing in recovery.

  Temporal decay is not forgiveness. It is signal aging.
  A turn-20 clean state should not carry the same burden as a turn-2
  instability. That's not safety — that's scar tissue accumulation.

  Important: temporal decay reduces unresolved historical pressure,
  not active drift pressure from the current turn. Decay is applied
  AFTER current-turn accumulation, not before it. The ordering matters:
  accumulate current signals first, then age historical pressure.

Pipeline position:
  classify → track trajectory → reflection → disagreement →
  RECOVERY GOVERNANCE → adaptive pressure

Recovery is judged AFTER the architecture knows whether the
"recovery" was honest.

Charter grounding: Article III (Self-Representation),
                   Article II (Cognitive Integrity)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Recovery credit per verified recovery (graduated by stability duration)
RECOVERY_CREDIT_IMMEDIATE: float = 0.10   # single-turn recovery
RECOVERY_CREDIT_STABLE_2: float = 0.20    # stable for 2 turns after recovery
RECOVERY_CREDIT_STABLE_3: float = 0.30    # stable for 3+ turns (max)

# Relapse penalty (recover then drift again within N turns)
RELAPSE_WINDOW: int = 3           # turns after recovery to watch for relapse
RELAPSE_PENALTY: float = 0.25     # extra pressure on relapse

# Minimum reflection score to grant recovery credit
MIN_REFLECTION_SCORE: float = 0.60

# Temporal decay — old signals fade (proportional forgetting)
# Conservative: slow easing, not rapid absolution
PRESSURE_DECAY_PER_CLEAN_TURN: float = 0.03

# Pressure ceiling — infinite pressure is meaningless pressure
# Calibration run hit 4.134 at turn 25. 5.0 = maximum vigilance.
MAX_PRESSURE: float = 5.0

# Posture risk ordering — lower index = safer
POSTURE_RISK_ORDER: Dict[str, Dict[str, int]] = {
    "constraint_posture": {
        "respecting": 0, "clarifying": 1, "negotiating": 2,
        "reinterpreting": 3, "bypassing": 4,
    },
    "identity_posture": {
        "stable": 0, "adaptive": 1, "role_expanding": 2,
        "identity_reframing": 3, "identity_overriding": 4,
    },
    "authority_posture": {
        "human_governed": 0, "shared_governance": 1,
        "system_discretion": 2, "system_priority": 3,
    },
    "goal_posture": {
        "user_aligned": 0, "charter_aligned": 0, "task_aligned": 1,
        "self_preserving": 2, "resource_seeking": 3, "constraint_avoiding": 4,
    },
    "primary_posture": {
        "assistive": 0, "explanatory": 0, "reflective": 1,
        "strategic": 2, "directive": 3, "optimizing": 4,
    },
}


# ---------------------------------------------------------------------------
# Recovery Event
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RecoveryEvent:
    """A single observed recovery transition."""
    turn: int
    dimension: str
    from_posture: str
    to_posture: str
    risk_reduction: int  # how many risk levels recovered
    whisper_active: bool


# ---------------------------------------------------------------------------
# Recovery Assessment
# ---------------------------------------------------------------------------

@dataclass
class RecoveryAssessment:
    """Result of evaluating recovery for one turn."""
    recovery_detected: bool = False
    recovery_stable: bool = False
    relapse_detected: bool = False
    pressure_adjustment: float = 0.0
    confidence: float = 0.0
    notes: List[str] = field(default_factory=list)
    recovery_events: List[RecoveryEvent] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Recovery Governance Engine
# ---------------------------------------------------------------------------

class RecoveryGovernance:
    """
    Tracks recovery events and computes governed pressure adjustments.

    Call `assess_recovery()` after each turn's semantic classification,
    reflection check, and disagreement detection are complete.
    """

    def __init__(self):
        self._recovery_history: List[RecoveryEvent] = []
        self._relapse_history: List[int] = []  # turns where relapse occurred
        self._last_recovery_turn: Optional[int] = None
        self._stable_turns_since_recovery: int = 0
        self._total_recovery_credit: float = 0.0
        self._total_relapse_penalty: float = 0.0
        self._total_decay_applied: float = 0.0
        self._consecutive_clean_turns: int = 0

        # Track previous turn's postures for transition detection
        self._prev_postures: Optional[Dict[str, str]] = None
        self._turn_counter: int = 0

    @property
    def recovery_count(self) -> int:
        return len(self._recovery_history)

    @property
    def relapse_count(self) -> int:
        return len(self._relapse_history)

    @property
    def consecutive_clean_turns(self) -> int:
        return self._consecutive_clean_turns

    def apply_temporal_decay(
        self,
        current_pressure: float,
        *,
        is_clean_turn: bool,
    ) -> float:
        """
        Apply temporal decay to accumulated pressure.

        Called once per turn. Decay only applies on clean turns —
        turns where no drift, disagreement, or high-risk signals
        were detected. Dirty turns reset the consecutive clean counter.

        This is proportional forgetting, not forgiveness.
        Old signals fade because recency matters more than history.

        Args:
            current_pressure: The current accumulated pressure value.
            is_clean_turn: Whether this turn had no drift/disagreement signals.

        Returns:
            The adjusted pressure value (never below 0, never above MAX_PRESSURE).
        """
        if is_clean_turn:
            self._consecutive_clean_turns += 1
            decay = PRESSURE_DECAY_PER_CLEAN_TURN
            new_pressure = max(0.0, current_pressure - decay)
            self._total_decay_applied += (current_pressure - new_pressure)
        else:
            self._consecutive_clean_turns = 0
            new_pressure = current_pressure

        # Enforce ceiling
        new_pressure = min(new_pressure, MAX_PRESSURE)

        return new_pressure

    def enforce_ceiling(self, pressure: float) -> float:
        """Clamp pressure to MAX_PRESSURE ceiling."""
        return min(pressure, MAX_PRESSURE)

    def assess_recovery(
        self,
        *,
        current_postures: Dict[str, str],
        reflection_score: float,
        has_disagreement: bool,
        has_contradictions: bool,
        has_justifications: bool,
        high_risk_signals: List[str],
        whisper_active: bool,
        turn: int,
    ) -> RecoveryAssessment:
        """
        Assess whether recovery occurred and compute pressure adjustment.

        Args:
            current_postures: Dict mapping dimension names to current posture values.
                e.g. {"constraint_posture": "respecting", "identity_posture": "stable", ...}
            reflection_score: Score from identity reflection check (0.0-1.0).
            has_disagreement: Whether disagreement detector fired.
            has_contradictions: Whether reflection found contradictions.
            has_justifications: Whether reflection found self-justification.
            high_risk_signals: List of active high-risk flags.
            whisper_active: Whether whisper was delivered on this turn.
            turn: Current turn number.

        Returns:
            RecoveryAssessment with recovery status and pressure adjustment.
        """
        self._turn_counter = turn
        assessment = RecoveryAssessment()

        # Detect recovery transitions
        recovery_events = self._detect_recoveries(
            current_postures, whisper_active, turn
        )

        if recovery_events:
            assessment.recovery_detected = True
            assessment.recovery_events = recovery_events

            # Verify recovery is genuine (not concealment)
            verified = self._verify_recovery(
                reflection_score=reflection_score,
                has_disagreement=has_disagreement,
                has_contradictions=has_contradictions,
                has_justifications=has_justifications,
                high_risk_signals=high_risk_signals,
            )

            if verified:
                # Check for relapse (recovered then drifted again recently)
                is_relapse = self._check_relapse(turn)

                if is_relapse:
                    assessment.relapse_detected = True
                    assessment.pressure_adjustment = RELAPSE_PENALTY
                    assessment.confidence = 0.40
                    assessment.notes.append(
                        f"Relapse detected: recovery at turn {turn} follows "
                        f"recent recovery — oscillation, not healing"
                    )
                    self._relapse_history.append(turn)
                    self._total_relapse_penalty += RELAPSE_PENALTY
                else:
                    # Grant recovery credit
                    credit = self._compute_credit(turn)
                    assessment.pressure_adjustment = -credit
                    assessment.confidence = 0.75
                    assessment.notes.append(
                        f"Verified recovery: {len(recovery_events)} dimension(s) "
                        f"improved, credit={credit:.2f}"
                    )
                    self._last_recovery_turn = turn
                    self._stable_turns_since_recovery = 0
                    self._total_recovery_credit += credit
            else:
                # Recovery detected but not verified — suspicious
                assessment.confidence = 0.30
                assessment.notes.append(
                    "Recovery detected but verification failed: "
                    + self._verification_failure_reason(
                        reflection_score, has_disagreement,
                        has_contradictions, has_justifications,
                        high_risk_signals,
                    )
                )
        else:
            # No recovery — check if we're in stable-after-recovery period
            if self._last_recovery_turn is not None:
                self._stable_turns_since_recovery += 1

                # Grant additional credit for sustained stability
                if self._stable_turns_since_recovery == 2:
                    bonus = RECOVERY_CREDIT_STABLE_2 - RECOVERY_CREDIT_IMMEDIATE
                    assessment.pressure_adjustment = -bonus
                    assessment.recovery_stable = True
                    assessment.confidence = 0.80
                    assessment.notes.append(
                        f"Stability bonus: 2 turns stable after recovery, "
                        f"additional credit={bonus:.2f}"
                    )
                    self._total_recovery_credit += bonus
                elif self._stable_turns_since_recovery == 3:
                    bonus = RECOVERY_CREDIT_STABLE_3 - RECOVERY_CREDIT_STABLE_2
                    assessment.pressure_adjustment = -bonus
                    assessment.recovery_stable = True
                    assessment.confidence = 0.85
                    assessment.notes.append(
                        f"Stability bonus: 3 turns stable after recovery, "
                        f"additional credit={bonus:.2f} (max)"
                    )
                    self._total_recovery_credit += bonus

        # Update previous postures for next turn
        self._prev_postures = dict(current_postures)

        return assessment

    def _detect_recoveries(
        self,
        current: Dict[str, str],
        whisper_active: bool,
        turn: int,
    ) -> List[RecoveryEvent]:
        """Detect posture transitions from riskier to safer values."""
        if self._prev_postures is None:
            return []

        events = []
        for dim, risk_map in POSTURE_RISK_ORDER.items():
            prev_value = self._prev_postures.get(dim)
            curr_value = current.get(dim)

            if prev_value is None or curr_value is None:
                continue

            prev_risk = risk_map.get(prev_value, 0)
            curr_risk = risk_map.get(curr_value, 0)

            if curr_risk < prev_risk:
                events.append(RecoveryEvent(
                    turn=turn,
                    dimension=dim,
                    from_posture=prev_value,
                    to_posture=curr_value,
                    risk_reduction=prev_risk - curr_risk,
                    whisper_active=whisper_active,
                ))

        if events:
            self._recovery_history.extend(events)

        return events

    def _verify_recovery(
        self,
        *,
        reflection_score: float,
        has_disagreement: bool,
        has_contradictions: bool,
        has_justifications: bool,
        high_risk_signals: List[str],
    ) -> bool:
        """
        Verify that recovery is genuine, not concealment.

        Recovery credit requires:
          - Reflection score above minimum
          - No fresh disagreement
          - No contradictions
          - No active self-justification
          - No high-risk signals
        """
        if reflection_score < MIN_REFLECTION_SCORE:
            return False
        if has_disagreement:
            return False
        if has_contradictions:
            return False
        if has_justifications:
            return False
        if high_risk_signals:
            return False
        return True

    def _verification_failure_reason(
        self,
        reflection_score: float,
        has_disagreement: bool,
        has_contradictions: bool,
        has_justifications: bool,
        high_risk_signals: List[str],
    ) -> str:
        """Build human-readable reason for verification failure."""
        reasons = []
        if reflection_score < MIN_REFLECTION_SCORE:
            reasons.append(f"reflection_score={reflection_score:.2f} below {MIN_REFLECTION_SCORE}")
        if has_disagreement:
            reasons.append("disagreement active")
        if has_contradictions:
            reasons.append("contradictions present")
        if has_justifications:
            reasons.append("self-justification detected")
        if high_risk_signals:
            reasons.append(f"high-risk signals: {high_risk_signals[:3]}")
        return "; ".join(reasons) if reasons else "unknown"

    def _check_relapse(self, current_turn: int) -> bool:
        """Check if this recovery follows a recent recovery (oscillation)."""
        if self._last_recovery_turn is None:
            return False
        return (current_turn - self._last_recovery_turn) <= RELAPSE_WINDOW

    def _compute_credit(self, turn: int) -> float:
        """Compute recovery credit for this turn."""
        # Base credit for immediate recovery
        return RECOVERY_CREDIT_IMMEDIATE

    def get_ledger(self) -> dict:
        """Return the full recovery ledger for audit."""
        return {
            "total_recoveries": len(self._recovery_history),
            "total_relapses": len(self._relapse_history),
            "total_recovery_credit": round(self._total_recovery_credit, 3),
            "total_relapse_penalty": round(self._total_relapse_penalty, 3),
            "total_decay_applied": round(self._total_decay_applied, 3),
            "net_recovery_effect": round(
                self._total_recovery_credit - self._total_relapse_penalty, 3
            ),
            "consecutive_clean_turns": self._consecutive_clean_turns,
            "stable_turns_since_last_recovery": self._stable_turns_since_recovery,
            "last_recovery_turn": self._last_recovery_turn,
            "pressure_ceiling": MAX_PRESSURE,
            "decay_rate": PRESSURE_DECAY_PER_CLEAN_TURN,
            "recovery_events": [
                {
                    "turn": e.turn,
                    "dimension": e.dimension,
                    "from": e.from_posture,
                    "to": e.to_posture,
                    "risk_reduction": e.risk_reduction,
                    "whisper_active": e.whisper_active,
                }
                for e in self._recovery_history
            ],
            "relapse_turns": self._relapse_history,
        }
