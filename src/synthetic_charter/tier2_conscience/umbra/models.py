# umbra/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class ShadowState(Enum):
    """
    Umbra's coarse judgment about the interaction.
    """
    CLEAR = auto()         # nothing concerning
    WATCH = auto()         # log + watch; gentle notice
    WARN = auto()          # strong guidance, maybe soften/redirect
    BLOCK = auto()         # must refuse / escalate


@dataclass
class UmbraSignal:
    """
    A single 'shadow' signal pulled from Tier I systems.
    Example sources:
      - firewall: Sovereigna refusals / coercion patterns
      - dual_conscience: yellow/red conflicts
      - dream_cycle: unresolved fossils
      - sandbox: adversarial patterns
    """
    source: str                  # e.g. "firewall", "dual_conscience", "sandbox"
    code: str                    # e.g. "COERCION_ATTEMPT", "OVERRIDE_PATTERN"
    weight: float = 1.0          # relative significance
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UmbraContext:
    """
    Minimal context Umbra needs to interpret signals.
    """
    session_id: Optional[str]
    user_label: Optional[str] = None
    model_label: Optional[str] = None
    ts_utc: Optional[str] = None

    # Optional: last states from Tier I
    last_state: Optional[str] = None
    last_shadow_state: Optional[ShadowState] = None


@dataclass
class UmbraAssessment:
    """
    Result of Umbra's evaluation for a single turn.
    """
    state: ShadowState
    reasons: List[str] = field(default_factory=list)

    # tags like ["coercion", "override_attempt", "boundary_confusion"]
    tags: List[str] = field(default_factory=list)

    # Obligations / guidance for the outer agent:
    # e.g. ["log_explainer", "offer_boundaries", "maintain_identity"]
    obligations: List[str] = field(default_factory=list)

    # Free-form, for DreamCycle / audit.
    notes: Dict[str, Any] = field(default_factory=dict)

    # Optional: normalized scoring for introspection / graphs
    risk_score: float = 0.0
    dignity_score: float = 1.0  # 1.0 = fully respected, 0 = violated

    def is_block(self) -> bool:
        return self.state is ShadowState.BLOCK

    def needs_explainer(self) -> bool:
        return "offer_explanation" in self.obligations


@dataclass
class UmbraFossil:
    """
    A stable snapshot for DreamCycle.
    Umbra can emit these when it detects a meaningful shadow conflict.
    """
    fossil_id: str
    context: UmbraContext
    assessment: UmbraAssessment
    raw_signals: List[UmbraSignal] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
