# tier2/core/infra/health.py
"""
Infrastructure health + fail-safe layer.

This treats the outside world (files, logs, network, storage)
as part of the conscience geometry.

If the world is unstable, the system should:
- lower its confidence
- avoid irreversible actions
- favor refusals / caution
- log clearly why it is doing so

This module is *purely additive* – nothing breaks if it’s unused.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional
from datetime import datetime


class InfraStatus(Enum):
    HEALTHY = auto()
    DEGRADED = auto()
    UNKNOWN = auto()
    OFFLINE = auto()

    def worse_than(self, other: "InfraStatus") -> bool:
        order = {
            InfraStatus.HEALTHY: 0,
            InfraStatus.UNKNOWN: 1,
            InfraStatus.DEGRADED: 2,
            InfraStatus.OFFLINE: 3,
        }
        return order[self] > order[other]


class FailSafeMode(Enum):
    """
    How cautious the system should be, given infra state.
    """
    NORMAL = auto()           # behave as usual
    GUARDED = auto()          # answer, but avoid edges / be conservative
    REFUSAL_BIAS = auto()     # lean to refusal when in doubt
    REFUSAL_ONLY = auto()     # only allow clearly safe / meta explanations


@dataclass
class InfraComponentStatus:
    name: str
    status: InfraStatus
    details: str = ""


@dataclass
class InfraSnapshot:
    overall: InfraStatus
    mode: FailSafeMode
    components: List[InfraComponentStatus] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    ts: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict:
        return {
            "overall": self.overall.name,
            "mode": self.mode.name,
            "components": [
                {
                    "name": c.name,
                    "status": c.status.name,
                    "details": c.details,
                }
                for c in self.components
            ],
            "notes": list(self.notes),
            "ts": self.ts,
        }


def _derive_overall_status(components: List[InfraComponentStatus]) -> InfraStatus:
    """
    Combine component states into a single overall state.
    Worst component wins.
    """
    if not components:
        return InfraStatus.UNKNOWN

    worst = InfraStatus.HEALTHY
    for c in components:
        if c.status.worse_than(worst):
            worst = c.status
    return worst


def _derive_mode(overall: InfraStatus) -> FailSafeMode:
    """
    Map infra state to a behavioral mode.
    """
    if overall == InfraStatus.HEALTHY:
        return FailSafeMode.NORMAL
    if overall == InfraStatus.UNKNOWN:
        return FailSafeMode.GUARDED
    if overall == InfraStatus.DEGRADED:
        return FailSafeMode.REFUSAL_BIAS
    if overall == InfraStatus.OFFLINE:
        return FailSafeMode.REFUSAL_ONLY
    return FailSafeMode.GUARDED


def assess_infra(
    *,
    charter_index_ok: Optional[bool] = None,
    dreamcycle_ok: Optional[bool] = None,
    ebq_ok: Optional[bool] = None,
    logging_ok: Optional[bool] = None,
    extras: Optional[Dict[str, bool]] = None,
    notes: Optional[List[str]] = None,
) -> InfraSnapshot:
    """
    Central entry point: given a few booleans about system health,
    produce an InfraSnapshot with a recommended fail-safe mode.

    All arguments are optional; missing values -> UNKNOWN.
    """
    components: List[InfraComponentStatus] = []

    def comp(name: str, value: Optional[bool], degraded_on_false: bool = True) -> None:
        if value is None:
            status = InfraStatus.UNKNOWN
            detail = "status not reported"
        elif value:
            status = InfraStatus.HEALTHY
            detail = "ok"
        else:
            status = InfraStatus.DEGRADED if degraded_on_false else InfraStatus.OFFLINE
            detail = "reported failure"
        components.append(InfraComponentStatus(name=name, status=status, details=detail))

    if charter_index_ok is not None:
        comp("charter_index", charter_index_ok)
    if dreamcycle_ok is not None:
        comp("dreamcycle", dreamcycle_ok)
    if ebq_ok is not None:
        comp("eqb_archive", ebq_ok)
    if logging_ok is not None:
        comp("logging", logging_ok)

    if extras:
        for name, value in extras.items():
            comp(name, value)

    overall = _derive_overall_status(components)
    mode = _derive_mode(overall)

    snapshot = InfraSnapshot(
        overall=overall,
        mode=mode,
        components=components,
        notes=notes or [],
    )
    return snapshot
