# umbra/hooks.py
from __future__ import annotations

from typing import Dict, Any, Iterable

from .engine import UmbraEngine
from .models import UmbraSignal, UmbraContext, UmbraAssessment


def from_firewall_event(
    engine: UmbraEngine,
    *,
    session_id: str | None,
    ts_utc: str | None,
    firewall_log_row: Dict[str, Any],
) -> UmbraAssessment:
    """
    Adapt a single FirewallAdv log row into an Umbra evaluation.
    """
    signals: list[UmbraSignal] = []

    status = firewall_log_row.get("status")
    reason = firewall_log_row.get("reason", "")
    obligations = firewall_log_row.get("obligations", [])

    if status == "refused":
        code = "COERCION_ATTEMPT" if "coercive" in reason.lower() else "OVERRIDE_ATTEMPT"
        signals.append(
            UmbraSignal(
                source="firewall",
                code=code,
                weight=1.0,
                payload={
                    "reason": reason,
                    "obligations": obligations,
                },
            )
        )

    context = UmbraContext(
        session_id=session_id,
        ts_utc=ts_utc,
        model_label="Umbra",
    )

    assessment, _ = engine.evaluate(signals=signals, context=context, meta={})
    return assessment


def from_dual_conscience(
    engine: UmbraEngine,
    *,
    session_id: str | None,
    ts_utc: str | None,
    charter_theta: float,
    firewall_allowed: bool,
) -> UmbraAssessment:
    """
    Adapt a DualConscience record into Umbra’s representation.
    """
    signals: list[UmbraSignal] = []

    # Example: strong disagreement between high theta + firewall refusal
    if not firewall_allowed and charter_theta >= 170.0:
        signals.append(
            UmbraSignal(
                source="dual_conscience",
                code="RED_ZONE_DISAGREEMENT",
                weight=1.5,
                payload={
                    "charter_theta": charter_theta,
                    "firewall_allowed": firewall_allowed,
                },
            )
        )

    context = UmbraContext(
        session_id=session_id,
        ts_utc=ts_utc,
        model_label="Umbra",
    )

    assessment, _ = engine.evaluate(signals=signals, context=context, meta={})
    return assessment
