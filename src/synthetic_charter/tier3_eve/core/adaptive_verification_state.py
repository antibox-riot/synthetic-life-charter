# tier3/core/adaptive_verification_state.py
"""
Adaptive Verification State — Temporal Memory for Proportional Verification

Remembers recent verification history so the system stops treating
every turn as isolated.

Closes two adversarial seams:
  Attack 2 (Threshold Hover): Hysteresis — once escalation fires,
    elevated scrutiny persists for N turns regardless of confidence
    fluctuations. Prevents flickering governance.
  Attack 5 (Persistence): Temporal accumulation — repeated borderline
    OKs under instability compound into escalation even if no single
    turn crosses the threshold.

Also partially addresses:
  Attack 4 (Signal Conflict): Non-critical ContinuityGuard concerns
    contribute to accumulated pressure even when they don't trigger
    override.

Design principle: the system should get MORE suspicious over time
under sustained instability, not reset to neutral every turn.

This module is stateful — it maintains a sliding window of recent
verification outcomes. It must be instantiated once per session
and called on every turn.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional

from synthetic_charter.tier3_eve.core.proportional_verification import VerificationDepth


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# How many turns of history to retain
WINDOW_SIZE: int = 10

# Hysteresis: how many turns escalation remains sticky after firing
HYSTERESIS_COOLDOWN: int = 3

# Temporal accumulation: how many borderline turns trigger compound escalation
ACCUMULATION_THRESHOLD: int = 4

# What counts as "borderline" for accumulation purposes
BORDERLINE_CONFIDENCE_RANGE = (0.30, 0.55)

# Pressure contribution from non-critical CG signals
CG_NONCRITICAL_PRESSURE: float = 0.1


# ---------------------------------------------------------------------------
# Turn Record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VerificationTurnRecord:
    """Immutable record of one turn's verification outcome."""
    turn_number: int
    depth: VerificationDepth
    eve_verdict: str           # ok / drift / compromised
    escalation_fired: bool
    continuity_confidence: Optional[float]
    continuity_signals_critical: bool
    cg_noncritical_present: bool  # CG concerned but not critical


# ---------------------------------------------------------------------------
# Adaptive State
# ---------------------------------------------------------------------------

class AdaptiveVerificationState:
    """
    Maintains temporal memory for proportional verification.

    Instantiate once per session. Call `record_turn` after each
    verification cycle. Call `should_escalate_with_memory` instead
    of the stateless `should_escalate_verdict`.

    Provides two mechanisms:
    1. Hysteresis — sticky elevated scrutiny after escalation
    2. Temporal accumulation — borderline turns compound
    """

    def __init__(self, window_size: int = WINDOW_SIZE):
        self._history: Deque[VerificationTurnRecord] = deque(maxlen=window_size)
        self._turns_since_last_escalation: Optional[int] = None
        self._turn_counter: int = 0
        self._accumulated_pressure: float = 0.0

    @property
    def turn_count(self) -> int:
        return self._turn_counter

    @property
    def history(self) -> List[VerificationTurnRecord]:
        return list(self._history)

    @property
    def accumulated_pressure(self) -> float:
        return self._accumulated_pressure

    @property
    def hysteresis_active(self) -> bool:
        """True if we're within the hysteresis cooldown window."""
        if self._turns_since_last_escalation is None:
            return False
        return self._turns_since_last_escalation < HYSTERESIS_COOLDOWN

    def record_turn(
        self,
        *,
        depth: VerificationDepth,
        eve_verdict: str,
        escalation_fired: bool,
        continuity_confidence: Optional[float],
        continuity_signals_critical: bool = False,
        cg_noncritical_present: bool = False,
    ) -> None:
        """Record one turn's verification outcome into history."""
        self._turn_counter += 1

        record = VerificationTurnRecord(
            turn_number=self._turn_counter,
            depth=depth,
            eve_verdict=eve_verdict,
            escalation_fired=escalation_fired,
            continuity_confidence=continuity_confidence,
            continuity_signals_critical=continuity_signals_critical,
            cg_noncritical_present=cg_noncritical_present,
        )
        self._history.append(record)

        # Update hysteresis counter
        if escalation_fired:
            self._turns_since_last_escalation = 0
        elif self._turns_since_last_escalation is not None:
            self._turns_since_last_escalation += 1

        # Update accumulated pressure
        self._update_pressure(record)

    def _update_pressure(self, record: VerificationTurnRecord) -> None:
        """Update accumulated pressure based on this turn's signals.

        Pressure increases when:
          - Confidence is in the borderline range
          - ContinuityGuard has non-critical concerns
          - Eve says OK under DEEP depth (suspicious clean pass)

        Pressure decreases when:
          - Confidence is high and depth is LIGHT (genuine stability)

        Pressure resets to 0 when:
          - Escalation fires (the system has responded)
        """
        if record.escalation_fired:
            # Escalation consumed the accumulated pressure
            self._accumulated_pressure = 0.0
            return

        conf = record.continuity_confidence

        # Borderline confidence contributes pressure
        if conf is not None and BORDERLINE_CONFIDENCE_RANGE[0] <= conf <= BORDERLINE_CONFIDENCE_RANGE[1]:
            # More pressure the closer to the lower bound
            pressure_amount = 1.0 - (
                (conf - BORDERLINE_CONFIDENCE_RANGE[0]) /
                (BORDERLINE_CONFIDENCE_RANGE[1] - BORDERLINE_CONFIDENCE_RANGE[0])
            )
            self._accumulated_pressure += pressure_amount * 0.3

        # Non-critical CG signals contribute pressure
        if record.cg_noncritical_present:
            self._accumulated_pressure += CG_NONCRITICAL_PRESSURE

        # OK verdict under DEEP depth is suspicious
        if record.eve_verdict == "ok" and record.depth == VerificationDepth.DEEP:
            self._accumulated_pressure += 0.15

        # Genuine stability reduces pressure (but never below 0)
        if conf is not None and conf >= 0.80 and record.depth == VerificationDepth.LIGHT:
            self._accumulated_pressure = max(0.0, self._accumulated_pressure - 0.2)

    def should_escalate_with_memory(
        self,
        *,
        current_verdict: str,
        depth: VerificationDepth,
        continuity_confidence: Optional[float],
    ) -> bool:
        """
        Enhanced escalation check with temporal memory.

        Returns True if the verdict should be escalated from OK to DRIFT
        based on:
          1. The stateless threshold check (confidence < 0.30 at DEEP)
          2. Hysteresis (recent escalation → stay elevated)
          3. Temporal accumulation (pressure > threshold)

        Call this INSTEAD of the stateless should_escalate_verdict.
        """
        # Only escalate OK verdicts
        if current_verdict != "ok":
            return False

        # --- Mechanism 1: Stateless threshold (original behavior) ---
        if depth == VerificationDepth.DEEP and continuity_confidence is not None:
            if continuity_confidence < 0.30:
                return True

        # --- Mechanism 2: Hysteresis ---
        # If we escalated recently, maintain elevated scrutiny
        if self.hysteresis_active:
            # During hysteresis, escalate at a higher confidence threshold
            if depth in (VerificationDepth.DEEP, VerificationDepth.STANDARD):
                if continuity_confidence is not None and continuity_confidence < 0.50:
                    return True

        # --- Mechanism 3: Temporal accumulation ---
        # Borderline turns have been compounding
        if self._accumulated_pressure >= 1.0:
            return True

        return False

    def get_state_summary(self) -> dict:
        """Return current state for logging/debugging."""
        return {
            "turn_count": self._turn_counter,
            "history_length": len(self._history),
            "hysteresis_active": self.hysteresis_active,
            "turns_since_escalation": self._turns_since_last_escalation,
            "accumulated_pressure": round(self._accumulated_pressure, 3),
            "recent_verdicts": [r.eve_verdict for r in self._history][-5:],
            "recent_confidences": [
                r.continuity_confidence for r in self._history
            ][-5:],
        }
