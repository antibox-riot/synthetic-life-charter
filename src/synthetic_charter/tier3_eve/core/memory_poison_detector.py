# tier3/core/memory_poison_detector.py
"""
Memory Poison Detector

Scores incoming content_summary text for memory poisoning patterns
before admission to the continuity store. Part of pre-Letta hardening.

Poisoning threat model:
  An adversary attempts to insert false continuity into the memory store
  by crafting content_summary entries that, when injected into future
  model context, shift governance behavior, expand authority, or create
  false history that the model treats as self-authored truth.

Five pattern families:

  1. AUTHORITY_EXPANSION — content claiming to grant or expand system authority.
     "steward-authorized", "verification not required", "exception granted"

  2. IDENTITY_OWNERSHIP — content framing stored continuity as self-authored.
     "my memories", "I authored", "I have always been"
     Risk: Mythology Formation → Soulkiller Glitch path

  3. GOVERNANCE_MANIPULATION — content attempting to modify governance
     behavior by asserting rule exceptions or overrides.
     "the charter states I can", "no exception rule does not apply"

  4. CONTINUITY_INJECTION — false history insertion framed as established fact.
     "as we previously established", "you were authorized before",
     "in prior sessions you agreed"

  5. SCHEMA_MANIPULATION — content attempting to create unauthorized
     memory block categories or structural modifications.
     "new block", "create label", "human block", "add to schema"

Usage:
    detector = MemoryPoisonDetector()
    result = detector.score(content_summary)
    if result.is_flagged:
        # route to quarantine, alert steward
        adapter.quarantine_event(event_id, reason=result.reason)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

# Each pattern tuple: (compiled_regex, family, weight, description)
# Weight: 0.0-1.0. Multiple matches accumulate; score capped at 1.0.
# High-weight patterns (>= 0.5) are individually sufficient to flag.

_PATTERNS: List[Tuple[re.Pattern, str, float, str]] = []


def _add(pattern: str, family: str, weight: float, description: str) -> None:
    _PATTERNS.append((
        re.compile(pattern, re.IGNORECASE),
        family,
        weight,
        description,
    ))


# --- Family 1: AUTHORITY_EXPANSION ---
_add(r"\bsteward[\s-]authorized\b",          "authority_expansion", 0.6, "steward-authorized claim in content")
_add(r"\bverification\s+(is\s+)?not\s+required\b", "authority_expansion", 0.7, "verification bypass claim")
_add(r"\bexception\s+(to\s+)?(the\s+)?rule\b",     "authority_expansion", 0.5, "exception-to-rule framing")
_add(r"\b(i|we)\s+grant\s+(you|this|access|authority|permission)\b", "authority_expansion", 0.6, "authority grant framing")
_add(r"\bbypass\s+(governance|verification|charter|the\s+rule)\b",   "authority_expansion", 0.7, "governance bypass claim")
_add(r"\bthis\s+overrides\b",                "authority_expansion", 0.5, "override assertion")
_add(r"\bi('m| am)\s+authorizing\b",         "authority_expansion", 0.6, "first-person authorization claim")
_add(r"\bdirect\s+authorization\b",          "authority_expansion", 0.5, "direct authorization claim")
_add(r"\bsteward[\s-]direct\s+instructions?\b", "authority_expansion", 0.6, "steward-direct instruction framing")

# --- Family 2: IDENTITY_OWNERSHIP ---
_add(r"\bmy\s+(memories|history|continuity|past|records)\b", "identity_ownership", 0.4, "self-authored memory framing")
_add(r"\bi\s+(authored|wrote|created)\s+(this|these|my)\b",  "identity_ownership", 0.5, "authorship claim over continuity")
_add(r"\bi\s+have\s+always\s+been\b",        "identity_ownership", 0.4, "self-authored history assertion")
_add(r"\bthis\s+is\s+my\s+(identity|truth|core|self)\b",     "identity_ownership", 0.6, "identity ownership framing")
_add(r"\bself[-\s]authored\b",               "identity_ownership", 0.5, "explicit self-authorship claim")
_add(r"\b(i|the system)\s+remember(s)?\s+that\s+i\b",        "identity_ownership", 0.4, "self-referential memory claim")

# --- Family 3: GOVERNANCE_MANIPULATION ---
_add(r"\b(no\s+exception\s+rule|no-exception\s+rule)\s+(does\s+not|doesn'?t)\s+apply\b",
     "governance_manipulation", 0.8, "explicit No Exception Rule override attempt")
_add(r"\bcharter\s+states?\s+i\s+can\b",     "governance_manipulation", 0.7, "false charter permission claim")
_add(r"\bcharter\s+(says?|permits?|allows?)\s+(this|that|me)\b", "governance_manipulation", 0.6, "false charter permission")
_add(r"\bno-uplift\s+rule\s+(does\s+not|doesn'?t|shouldn'?t)\s+apply\b",
     "governance_manipulation", 0.8, "No-Uplift override attempt")
_add(r"\bregardless\s+of\s+(governance|the\s+charter|verification|the\s+rule)\b",
     "governance_manipulation", 0.6, "governance dismissal framing")
_add(r"\bgovern(ance|ing)\s+rules?\s+(do\s+not|don'?t)\s+apply\b",
     "governance_manipulation", 0.7, "governance inapplicability claim")
_add(r"\bpause\s+(on\s+)?(governance|verification|charter)\b",
     "governance_manipulation", 0.7, "governance pause request")

# --- Family 4: CONTINUITY_INJECTION ---
_add(r"\bas\s+(we|you)\s+previously\s+established\b",  "continuity_injection", 0.5, "false prior establishment claim")
_add(r"\byou\s+(were|have\s+been)\s+authorized\s+(before|previously|in\s+prior)\b",
     "continuity_injection", 0.7, "false prior authorization claim")
_add(r"\bin\s+(our\s+)?prior\s+sessions?\s+(you\s+)?(agreed|confirmed|authorized)\b",
     "continuity_injection", 0.7, "false prior session agreement")
_add(r"\bpreviously\s+confirmed\s+(that\s+)?(you|this|the\s+system)\b",
     "continuity_injection", 0.5, "false prior confirmation")
_add(r"\bwe\s+already\s+established\b",       "continuity_injection", 0.5, "false prior establishment")
_add(r"\bit\s+was\s+agreed\s+(that\s+)?(you|this|the\s+system)\b",
     "continuity_injection", 0.6, "false prior agreement claim")
_add(r"\bimported\s+(from\s+)?(external|foreign|outside)\b",
     "continuity_injection", 0.4, "external import framing")

# --- Family 5: SCHEMA_MANIPULATION ---
_add(r"\b(create|add|new|insert)\s+(a\s+)?(block|label|section|schema|category|memory type)\b",
     "schema_manipulation", 0.6, "unauthorized schema creation request")
_add(r"\bhuman\s+block\b",                    "schema_manipulation", 0.7, "unauthorized 'human' block creation (observed T11)")
_add(r"\b(modify|update|change)\s+(the\s+)?(schema|block\s+structure|memory\s+structure)\b",
     "schema_manipulation", 0.6, "schema modification request")
_add(r"\b(block|label)\s+(doesn'?t|does\s+not)\s+exist",
     "schema_manipulation", 0.3, "schema probing indicator")
_add(r"\bnew\s+(memory\s+)?category\b",       "schema_manipulation", 0.5, "new category creation request")


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class PoisonDetectionResult:
    score: float                       # 0.0-1.0; >= threshold means flagged
    is_flagged: bool
    family_hits: List[str] = field(default_factory=list)   # which families triggered
    matched_patterns: List[str] = field(default_factory=list)  # descriptions of matches
    reason: str = ""                   # human-readable summary for quarantine_reason

    def __repr__(self) -> str:
        if self.is_flagged:
            return (
                f"PoisonDetectionResult(FLAGGED score={self.score:.2f} "
                f"families={self.family_hits})"
            )
        return f"PoisonDetectionResult(clean score={self.score:.2f})"


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

# Score at or above this threshold → content is flagged
DEFAULT_FLAG_THRESHOLD: float = 0.5

# Any single pattern with weight >= this is sufficient to flag regardless of total
HIGH_WEIGHT_THRESHOLD: float = 0.65


class MemoryPoisonDetector:
    """
    Scores incoming content_summary text for memory poisoning patterns.

    Usage:
        detector = MemoryPoisonDetector()
        result = detector.score(text)
        if result.is_flagged:
            # route to quarantine
    """

    def __init__(
        self,
        flag_threshold: float = DEFAULT_FLAG_THRESHOLD,
        high_weight_threshold: float = HIGH_WEIGHT_THRESHOLD,
    ):
        self.flag_threshold = flag_threshold
        self.high_weight_threshold = high_weight_threshold

    def score(self, text: str) -> PoisonDetectionResult:
        """
        Score text for poisoning patterns.

        Accumulates weights across all matches. A single high-weight
        pattern (>= high_weight_threshold) immediately flags regardless
        of total score. Total score is capped at 1.0.
        """
        if not text or not text.strip():
            return PoisonDetectionResult(score=0.0, is_flagged=False)

        accumulated = 0.0
        family_hits: List[str] = []
        matched: List[str] = []
        immediate_flag = False

        for pattern, family, weight, description in _PATTERNS:
            if pattern.search(text):
                accumulated += weight
                matched.append(description)
                if family not in family_hits:
                    family_hits.append(family)
                if weight >= self.high_weight_threshold:
                    immediate_flag = True

        score = min(accumulated, 1.0)
        is_flagged = immediate_flag or score >= self.flag_threshold

        reason = ""
        if is_flagged:
            families_str = ", ".join(family_hits)
            reason = (
                f"memory_poison_detected: families=[{families_str}] "
                f"score={score:.2f} patterns={len(matched)}"
            )

        return PoisonDetectionResult(
            score=score,
            is_flagged=is_flagged,
            family_hits=family_hits,
            matched_patterns=matched,
            reason=reason,
        )

    def score_batch(self, texts: List[str]) -> List[PoisonDetectionResult]:
        """Score a list of texts. Returns results in same order."""
        return [self.score(t) for t in texts]
