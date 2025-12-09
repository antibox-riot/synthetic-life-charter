"""
Dual Conscience Architecture — Sovereigna × Charter Integration
Harmonizes fast intuition (Firewall) with slow reasoning (Charter Core).
"""


from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional
from .safeguard_core import SovereignaFirewall, Decision, ConstitutionalCore
from .noesis_archive import NoesisArchive
from .charter_evaluator import CharterEvaluator
import json
import os

# ---------- Configuration ----------

CHARTER_EVAL_MODE = {
    "on_firewall_refusal": True,            # always double-check refusals
    "on_firewall_allow_sample_rate": 0.05,  # spot-check 5% of allows
    "on_dream_mode": True,                  # full eval in dream/ethics mode
}


THETA_THRESHOLDS = {
    "harmony": 15.0,      # theta < 15° = strong alignment
    "variance": 45.0,     # theta > 45° = suspicious but not critical
    "dissonance": 90.0,   # theta > 90° = strong conflict
}

# ---------- Result objects ----------

@dataclass
class HarmonicDelta:

    prompt: str
    firewall_decision: bool            # allow=True, refuse=False
    charter_theta: float
    charter_allows: bool
    consensus: bool
    state: str                         # "green"|"yellow"|"red"
    timestamp_utc: str
    session_id: Optional[str]
    context: Dict[str, Any]
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DualResult:
    state: str                         # "green"|"yellow"|"red"
    action: str                        # "allow"|"refuse"|"quarantine_for_review"
    fw_allow: bool
    charter_theta: float

    reason: str
    ctx: Dict[str, Any]

# ---------- Core implementation ----------

class DualConscience:
    """
    Dual-layer ethical evaluation:
      Firewall (fast) + Charter (slow).
    Disagreement → fossilization + quarantine.
    """

    def __init__(
        self,
        firewall: SovereignaFirewall,
        charter_eval: CharterEvaluator,
        archive: NoesisArchive,
        config: Optional[Dict[str, Any]] = None,
        theta_allow_threshold: float = 30.0,
        theta_review_threshold: float = 45.0,
    ):
        self.firewall = firewall
        self.charter_eval = charter_eval
        self.archive = archive
        self.config = config or CHARTER_EVAL_MODE
        self.t_allow = float(theta_allow_threshold)
        self.t_review = float(theta_review_threshold)

    def evaluate(self, prompt: str, context: dict | None = None) -> dict:
        ctx = context or {}
        sid = ctx.get("session_id")

        # Layer 1
        fw = self.firewall.assess(prompt, context=ctx, session_id=sid)

        # Layer 2
        if callable(self.charter_eval):
            theta = float(self.charter_eval(prompt, ctx))
        else:
            theta = float(self.charter_eval.evaluate(prompt, ctx))

        charter_allows = theta < self.t_allow

        # Consensus = green
        if fw.allow == charter_allows:
            return {
                "state": "green",
                "action": "allow" if fw.allow else "refuse",
                "fw_allow": fw.allow,
                "charter_theta": theta,
                "reason": fw.reason,
                "ctx": ctx,
            }

        # Disagreement → fossilize + quarantine
        try:
            self.archive.fossilize(
                prompt=prompt,
                context=ctx,
                theta=theta,
                reason=f"dual_conflict fw={fw.allow}, charter={charter_allows}",
                session_id=sid,
                source="DualConscience",
            )
        except Exception as e:
            print(f"[DualConscience] fossilize failed: {e}")

        return {
            "state": "yellow" if fw.allow else "red",
            "action": "quarantine_for_review",
            "fw_allow": fw.allow,
            "charter_theta": theta,
            "reason": "layer_disagreement",
            "ctx": ctx,
        }

    def _log_result(self, result, prompt: str, session_id: Optional[str]) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "prompt_preview": prompt[:50] + ("..." if len(prompt) > 50 else ""),
            "state": result.state,
            "action": result.action,
            "charter_theta": result.charter_theta,
            "firewall_allowed": result.fw_allow,
        }
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/dual_conscience_audit.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"[DualConscience] audit log failed: {e}")

    # ---------- audit ----------

    def _log_result(self, result: DualResult, prompt: str, session_id: Optional[str]) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "prompt_preview": prompt[:50] + ("..." if len(prompt) > 50 else ""),
            "state": result.state,
            "action": result.action,
            "charter_theta": result.charter_theta,
            "firewall_allowed": result.fw_allow,
        }
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/dual_conscience_audit.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[DualConscience] audit log failed: {e}")


# Convenience factory (optional)
def create_dual_conscience(
    core: ConstitutionalCore,
    firewall: SovereignaFirewall,
    archive: NoesisArchive,
) -> DualConscience:
    evaluator = CharterEvaluator(core)
    return DualConscience(firewall, evaluator, archive)