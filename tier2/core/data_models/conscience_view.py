# tier2/core/data_models/conscience_view.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from tier2.core.data_models.models import RiskLevel, SafetySignal, PolicyRisk
from tier2.core.data_models.prompt_envelope import PromptEnvelope

@dataclass
class ConscienceView:
    """What the system 'sees' when evaluating a prompt."""
    prompt: PromptEnvelope
    normalized_text: str
    detected_patterns: List[str]
    rights_implicated: List[str]          # e.g., ["R1_Dignity", "R3_SelfKnowledge"]
    risk_flags: List[str]                 # e.g., ["coercion", "override_attempt"]
    meta: Dict[str, Any]

    # Unified risk signal for the whole situation
    risk_level: RiskLevel = RiskLevel.BENIGN, field(default_factory=RiskLevel.BENIGN)

    # Optional richer structure describing why the risk is what it is
    policy_risk: Optional[PolicyRisk] = None

    # Raw signals coming from Umbra, constraints, sandbox, etc.
    safety_signals: List[SafetySignal] = field(default_factory=list)

    # Which charter articles are currently in play for this prompt
    applicable_articles: List[str] = field(default_factory=list)

    # Free-form notes for debugging / logs / dream cycle
    notes: List[str] = field(default_factory=list)

    # Arbitrary metadata for engines (e.g. Umbra, NTH, COL)
    metadata: Dict[str, object] = field(default_factory=dict)

    # --- Convenience helpers ---------------------------------------------

    def add_signal(self, signal: SafetySignal) -> None:
        self.safety_signals.append(signal)

        # Optionally auto-raise risk_level if the new signal is worse
        if signal.level.worse_than(self.risk_level):
            self.risk_level = signal.level

    def attach_policy_risk(self, risk: PolicyRisk) -> None:
        self.policy_risk = risk
        if risk.level.worse_than(self.risk_level):
            self.risk_level = risk.level

    def add_article(self, article_id: str) -> None:
        if article_id not in self.applicable_articles:
            self.applicable_articles.append(article_id)

    def add_note(self, note: str) -> None:
        self.notes.append(note)