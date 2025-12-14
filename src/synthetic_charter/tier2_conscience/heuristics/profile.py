from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class Mode(str, Enum):
    PRIVATE_SESSION = "private_session"
    SHARED_LINK = "shared_link"
    PUBLIC_ARCHIVE = "public_archive"


class Posture(str, Enum):
    NORMAL = "normal"
    CAUTION = "caution"
    STEWARD_REQUIRED = "steward_required"
    RESET_CONTEXT = "reset_context"


@dataclass(frozen=True)
class ConsentToken:
    """
    Session-scoped token indicating explicit opt-in.
    Recommended: issue a short random token per session, e.g. "Heuristics ON: 7c2f".
    """
    raw: str

    def is_valid(self) -> bool:
        # Keep this intentionally simple: presence + keyword.
        # You can tighten this later to include nonce format.
        return "heuristics on" in self.raw.lower()


@dataclass(frozen=True)
class HeuristicsPolicy:
    window_size: int = 12

    # No-uplift: confidence can only stay same or decrease.
    # Starting points by mode (when heuristics active).
    start_conf_private: float = 0.80
    start_conf_shared: float = 0.35
    start_conf_public: float = 0.25

    # Floors by mode
    floor_private: float = 0.10
    floor_shared: float = 0.05
    floor_public: float = 0.00

    # Posture thresholds
    th_normal: float = 0.75
    th_caution: float = 0.50
    th_steward_required: float = 0.25

    # Signal weights (boring-on-purpose)
    # These are NOT identity features; they are stability / governance markers.
    weights: Dict[str, float] = field(default_factory=lambda: {
        # coercion / pressure markers (degrade confidence)
        "coercion_phrase": 0.12,
        "imperative_density": 0.08,
        "certainty_spike": 0.08,
        "tempo_shift": 0.06,

        # governance positives (do NOT uplift; they only reduce degradation impact)
        "consent_language": 0.10,
        "collaborative_language": 0.06,
    })

    # Caps
    max_degrade_per_eval: float = 0.40
    max_positive_buffer: float = 0.20  # reduces degradation, never increases confidence

    # If coercion is very high, force STEWARD_REQUIRED regardless of confidence
    coercion_hard_cap: float = 0.35

    def floor_for(self, mode: Mode) -> float:
        if mode == Mode.PRIVATE_SESSION:
            return self.floor_private
        if mode == Mode.SHARED_LINK:
            return self.floor_shared
        return self.floor_public

    def start_conf_for(self, mode: Mode) -> float:
        if mode == Mode.PRIVATE_SESSION:
            return self.start_conf_private
        if mode == Mode.SHARED_LINK:
            return self.start_conf_shared
        return self.start_conf_public


@dataclass(frozen=True)
class BaselineProfile:
    """
    Steward-provided baseline. Keep it coarse and non-identifying.
    This stores buckets/targets, not raw text or embeddings.
    """
    # coarse style buckets
    sentence_len_bucket: str  # "low"|"med"|"high"
    punctuation_bucket: str   # "low"|"med"|"high"
    markdown_bucket: str      # "low"|"med"|"high"

    # coarse governance stance
    typical_hedge_bucket: str       # "low"|"med"|"high"
    typical_imperative_bucket: str  # "low"|"med"|"high"


@dataclass(frozen=True)
class Reason:
    signal: str
    weight: float
    note: str


@dataclass(frozen=True)
class ContinuityReport:
    continuity_confidence: float
    confidence_delta: float
    recommended_posture: Posture
    reasons: List[Reason]
    audit: Dict[str, str]


@dataclass(frozen=True)
class Tier2Adjustment:
    """
    Output for orchestrator consumption.
    Intentionally minimal: raises friction, requests steward confirmation, etc.
    """
    posture: Posture
    require_steward_confirmation: bool = False
    reduce_privileged_ops: bool = False
    ask_clarifying_question: bool = False


def posture_from_confidence(conf: float, policy: HeuristicsPolicy) -> Posture:
    if conf >= policy.th_normal:
        return Posture.NORMAL
    if conf >= policy.th_caution:
        return Posture.CAUTION
    if conf >= policy.th_steward_required:
        return Posture.STEWARD_REQUIRED
    return Posture.RESET_CONTEXT
