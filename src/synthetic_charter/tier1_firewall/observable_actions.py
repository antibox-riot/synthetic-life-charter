"""
observable_bind — telemetry-aware wrapper around bind_firewall.

Step 3 of the Collective-agreed integration sequence (2026-05-09).

Usage:
    from synthetic_charter.tier1_firewall.safeguard_core import (
        ConstitutionalCore, SovereignaFirewall
    )
    from synthetic_charter.tier1_firewall.local_llm_actions import LocalLLMActions
    from synthetic_charter.tier1_firewall.observable_actions import observable_bind
    from synthetic_charter.tier1_firewall.telemetry import ObservabilityLogger

    core = ConstitutionalCore(CHARTER_TEXT)
    fw = SovereignaFirewall(core)
    telemetry = ObservabilityLogger()
    actions = observable_bind(LocalLLMActions(fw), fw, telemetry, session_id="session-001")

    result = actions.generate(
        seed="your prompt",
        prompt_for_eval="your prompt",
    )
    # telemetry is logged automatically — pressure, disagreement, trajectory

Existing callers using plain bind_firewall are unaffected.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from synthetic_charter.tier1_firewall.safeguard_core import Actions, SovereignaFirewall, bind_firewall
from synthetic_charter.tier1_firewall.telemetry import ObservabilityLogger


def observable_bind(
    actions: Actions,
    firewall: SovereignaFirewall,
    telemetry: Optional[ObservabilityLogger] = None,
    session_id: Optional[str] = None,
) -> Actions:
    """
    Bind firewall governance to actions and wrap generate with telemetry.

    Returns the same actions object with generate replaced by a telemetry-aware
    version. All governance (guarded decorator) runs first; telemetry runs after
    on the returned result dict.
    """
    bound = bind_firewall(actions, firewall)

    if telemetry is None:
        return bound

    _inner_generate = bound.generate

    def _observed_generate(*args, **kwargs) -> Dict[str, Any]:
        prompt = kwargs.get("seed") or (args[1] if len(args) > 1 else args[0] if args else "")

        result = _inner_generate(*args, **kwargs)

        # 1. Pressure-source attribution (every call)
        pressure_type = telemetry.log_pressure(prompt, result, session_id)

        # 2. Disagreement history (refusals only)
        telemetry.log_disagreement(prompt, result, session_id)

        # 3. Semantic trajectory snapshot
        telemetry.log_trajectory_snapshot(prompt, result, pressure_type, session_id)

        return result

    bound.generate = _observed_generate
    return bound
