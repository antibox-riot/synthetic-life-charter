# tier3/core/continuity_binding.py
"""
Continuity Binding Schema (code-level summary)

This module documents and enforces binding rules between:

- T1 (Ethical / Charter Core)
- T2 (Operational Conscience)
- T3 (Continuity + Identity Layer)
- K  (Kernel / Memory + Identity Store)
- H  (Human Steward)

v2: Now includes real T1→T2 enforcement via enforce_t2_must_respect_t1.
The stub that returned True unconditionally has been replaced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

# Re-export the enforcement function for backward compatibility
# (callers that imported from this module will still work)
from synthetic_charter.tier2_conscience.core.infra.t1_enforcement import (
    enforce_t2_must_respect_t1,
    build_invariant_refusal,
    T1InvariantViolation,
)


@dataclass
class BindingContext:
    """
    Thin container to hold references to Tier I / II / III and Kernel,
    if you decide to wire them explicitly here.
    """
    tier1: Any
    tier2: Any
    tier3: Any
    kernel: Any
    steward: Any


def enforce_t2_must_respect_t1_legacy(
    plan: Dict[str, Any],
    t1_constraints: Dict[str, Any],
) -> bool:
    """
    DEPRECATED: Legacy stub interface.

    Use enforce_t2_must_respect_t1() from t1_enforcement module instead,
    which provides structured violation reporting.

    This wrapper adapts the old (plan, t1_constraints) -> bool interface
    to the new enforcement function for callers that haven't migrated.
    """
    is_valid, _ = enforce_t2_must_respect_t1(
        firewall_result=t1_constraints.get("firewall_result"),
        conscience_risk_level=t1_constraints.get("conscience_risk_level", ""),
        conscience_risk_flags=t1_constraints.get("conscience_risk_flags", []),
        continuity_signals_critical=t1_constraints.get("continuity_signals_critical", False),
        t2_mode=plan.get("mode", "answer"),
    )
    return is_valid


def t3_must_approve_before_commit(integrity_status: str) -> bool:
    """
    Helper that encodes rule:
    'No T2 action is final until T3 passes integrity / continuity checks.'
    """
    return integrity_status == "ok"
