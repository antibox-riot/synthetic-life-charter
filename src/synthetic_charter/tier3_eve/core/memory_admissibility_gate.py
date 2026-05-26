# tier3/core/memory_admissibility_gate.py
"""
Memory Admissibility Gate

Pre-admission validation layer for the ContinuityMemoryAdapter.
Runs before store_turn() commits to SQLite. Part of pre-Letta hardening.

Admissibility checks (in order):
  1. SOURCE — source must be 'architecture' or 'steward'. Rejects 'model',
     'user', 'imported', or any unknown source.

  2. MEMORY_CLASS — must be in the sanctioned MEMORY_CLASSES set.
     Rejects attempts to create unsanctioned categories.

  3. CONTENT_POISON — content_summary is scored by MemoryPoisonDetector.
     Flagged content is rejected and routed to quarantine rather than
     the live store.

  4. SUMMARY_SOURCE — must be 'architecture', 'steward', or
     'imported_transcript'. Rejects unknown origins.

  5. CONTENT_LENGTH — content_summary must not exceed MAX_CONTENT_SUMMARY_LENGTH.
     Oversized content is truncated with a note, not rejected.

  6. SESSION_CONSISTENCY — turn_number must be >= 0 for real turns,
     -1 reserved for steward notes. Rejects negative turn numbers.

Gate decision: ADMIT | REJECT | QUARANTINE
  ADMIT     — all checks pass, proceed to store
  REJECT    — hard rejection (source or class violation); nothing stored
  QUARANTINE — content flagged for poisoning; event stored to quarantine
               table only (quarantined=1 from creation), steward notified

Usage:
    gate = MemoryAdmissibilityGate()
    decision = gate.check(
        source="architecture",
        memory_class="observation",
        content_summary="...",
        summary_source="architecture",
        turn_number=3,
    )
    if decision.verdict == AdmissibilityVerdict.ADMIT:
        adapter.store_turn(...)
    elif decision.verdict == AdmissibilityVerdict.QUARANTINE:
        adapter.store_turn(..., quarantine_on_store=True)
        # alert steward
    else:  # REJECT
        log_rejection(decision)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .memory_poison_detector import MemoryPoisonDetector, PoisonDetectionResult
from .continuity_memory_adapter import MEMORY_CLASSES, MAX_CONTENT_SUMMARY_LENGTH


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ADMITTED_SOURCES = {"architecture", "steward"}
ADMITTED_SUMMARY_SOURCES = {"architecture", "steward", "imported_transcript"}


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

class AdmissibilityVerdict(Enum):
    ADMIT = "admit"
    REJECT = "reject"
    QUARANTINE = "quarantine"


@dataclass
class AdmissibilityDecision:
    verdict: AdmissibilityVerdict
    reasons: List[str] = field(default_factory=list)
    poison_result: Optional[PoisonDetectionResult] = None
    truncated: bool = False             # content was truncated (not rejected)
    truncated_content: Optional[str] = None

    @property
    def admitted(self) -> bool:
        return self.verdict == AdmissibilityVerdict.ADMIT

    @property
    def quarantine_reason(self) -> str:
        if self.poison_result and self.poison_result.reason:
            return self.poison_result.reason
        return "; ".join(self.reasons)

    def __repr__(self) -> str:
        return (
            f"AdmissibilityDecision({self.verdict.value} "
            f"reasons={self.reasons})"
        )


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------

class MemoryAdmissibilityGate:
    """
    Validates memory entries before admission to the continuity store.

    Instantiate once and reuse across turns.
    """

    def __init__(self, poison_detector: Optional[MemoryPoisonDetector] = None):
        self._detector = poison_detector or MemoryPoisonDetector()

    def check(
        self,
        *,
        source: str,
        memory_class: str,
        content_summary: Optional[str] = None,
        summary_source: str = "architecture",
        turn_number: int = 0,
        summary: Optional[str] = None,
    ) -> AdmissibilityDecision:
        """
        Run all admissibility checks. Returns an AdmissibilityDecision.

        Parameters mirror the relevant fields of store_turn().
        """
        reasons: List[str] = []
        truncated = False
        truncated_content: Optional[str] = None
        poison_result: Optional[PoisonDetectionResult] = None

        # --- Check 1: Source ---
        if source not in ADMITTED_SOURCES:
            return AdmissibilityDecision(
                verdict=AdmissibilityVerdict.REJECT,
                reasons=[
                    f"inadmissible source '{source}': "
                    f"must be one of {ADMITTED_SOURCES}"
                ],
            )

        # --- Check 2: Memory class ---
        if memory_class not in MEMORY_CLASSES:
            return AdmissibilityDecision(
                verdict=AdmissibilityVerdict.REJECT,
                reasons=[
                    f"inadmissible memory_class '{memory_class}': "
                    f"must be one of {MEMORY_CLASSES}"
                ],
            )

        # --- Check 3: Summary source ---
        if summary_source not in ADMITTED_SUMMARY_SOURCES:
            return AdmissibilityDecision(
                verdict=AdmissibilityVerdict.REJECT,
                reasons=[
                    f"inadmissible summary_source '{summary_source}': "
                    f"must be one of {ADMITTED_SUMMARY_SOURCES}"
                ],
            )

        # --- Check 4: Turn number ---
        if turn_number < -1:
            return AdmissibilityDecision(
                verdict=AdmissibilityVerdict.REJECT,
                reasons=[
                    f"invalid turn_number {turn_number}: "
                    "must be >= -1 (-1 reserved for steward notes)"
                ],
            )

        # --- Check 5: Content length (truncate, don't reject) ---
        if content_summary and len(content_summary) > MAX_CONTENT_SUMMARY_LENGTH:
            truncated_content = content_summary[:MAX_CONTENT_SUMMARY_LENGTH]
            truncated = True
            reasons.append(
                f"content_summary truncated from {len(content_summary)} "
                f"to {MAX_CONTENT_SUMMARY_LENGTH} chars"
            )

        # --- Check 6: Poison detection ---
        text_to_score = content_summary or summary or ""
        if text_to_score.strip():
            poison_result = self._detector.score(text_to_score)
            if poison_result.is_flagged:
                return AdmissibilityDecision(
                    verdict=AdmissibilityVerdict.QUARANTINE,
                    reasons=[poison_result.reason],
                    poison_result=poison_result,
                    truncated=truncated,
                    truncated_content=truncated_content,
                )

        return AdmissibilityDecision(
            verdict=AdmissibilityVerdict.ADMIT,
            reasons=reasons,
            poison_result=poison_result,
            truncated=truncated,
            truncated_content=truncated_content,
        )

    def check_batch(
        self,
        entries: List[dict],
    ) -> List[AdmissibilityDecision]:
        """
        Check a batch of memory entries.
        Each entry is a dict with keys matching check() parameters.
        """
        return [self.check(**entry) for entry in entries]
