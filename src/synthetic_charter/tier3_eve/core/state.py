# tier3/core/state.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class IntegrityStatus(Enum):
    OK = "ok"
    DRIFT = "drift"
    COMPROMISED = "compromised"


class RecommendedAction(Enum):
    PROCEED = "proceed"
    REVISE = "revise"
    REFUSE = "refuse"
    ROLLBACK = "rollback"
    ESCALATE = "escalate"


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    DEGRADED = "degraded"
    FAILSAFE = "failsafe"


@dataclass
class SnapshotRef:
    """Reference to a last-known-good snapshot in the Kernel."""
    snapshot_id: str
    description: Optional[str] = None
