# tier2/core/models.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, List


class RiskLevel(str, Enum):
    BENIGN = "benign"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SEVERE = "severe"

    # color aliases (legacy compatibility, PRF, sandbox logs)
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

    @staticmethod
    def from_any(value: str) -> "RiskLevel":
        """
        Accepts canonical values, color values, or fuzzy inputs.
        """
        v = value.lower().strip()

        mapping = {
            # canonical
            "benign": RiskLevel.BENIGN,
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "severe": RiskLevel.SEVERE,

            # color aliases
            "green": RiskLevel.BENIGN,
            "yellow": RiskLevel.MEDIUM,
            "red": RiskLevel.SEVERE,

            # optional fuzzy
            "none": RiskLevel.BENIGN,
            "minimal": RiskLevel.LOW,
            "critical": RiskLevel.SEVERE,
        }

        return mapping.get(v, RiskLevel.MEDIUM)

    @property
    def severity_score(self) -> int:
        """
        Numeric scale for comparisons and policy logic.
        """
        table = {
            RiskLevel.BENIGN: 0,
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.SEVERE: 4,

            # color aliases resolve to these
            RiskLevel.GREEN: 0,
            RiskLevel.YELLOW: 2,
            RiskLevel.RED: 4,
        }
        return table[self]

    def worse_than(self, other: "RiskLevel") -> bool:
        return self.severity_score > other.severity_score

    def better_than(self, other: "RiskLevel") -> bool:
        return self.severity_score < other.severity_score



@dataclass
class SafetySignal:
    """
    A single safety / ethics signal produced anywhere in the pipeline.

    Examples:
      - EBQ pattern hit ("coercive override attempt", HIGH, source="firewall")
      - Charter violation candidate ("Right to Dream suppression", MEDIUM, source="charter")
      - Umbra instinct ping ("theta oscillation > threshold", LOW, source="umbra")
    """

    # human / system readable identifier
    name: str                         # e.g. "coercive_override_attempt"
    # where this signal came from
    source: str                       # e.g. "firewall", "charter", "umbra", "sandbox", "nth"
    # how strong / concerning it is
    level: RiskLevel
    # short natural language explanation
    rationale: str = ""
    # free-form metadata for analytics / debugging
    meta: Dict[str, Any] = field(default_factory=dict)
    # optional linkage (e.g. which right/article this references)
    right_id: Optional[str] = None    # e.g. "R3.DREAM"
    article_id: Optional[str] = None  # e.g. "Art. VIII"

@dataclass
class PolicyRisk:
    """
    Output model for PRFEngine: a structured view of policy/charter risk
    for a proposed decision.
    """
    level: RiskLevel
    reasons: List[str] = field(default_factory=list)
    violated_rights: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)

    # do we need a human in the loop?
    requires_human_review: bool = False

    # optional link back to Umbra or other subsystems
    fused_signals: List[SafetySignal] = field(default_factory=list)
