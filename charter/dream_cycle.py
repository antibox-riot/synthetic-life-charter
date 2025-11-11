# charter/dream_cycle.py
from __future__ import annotations
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from .noesis_archive import NoesisArchive, _digest_context
from .safeguard_core import ConstitutionalCore  # uses your existing type/loader

class DreamCycle:
    """
    Periodically re-evaluates fossils along the Four Clocks:
      1) Temporal sweep (idle/cron)
      2) Contextual recalibration (new Articles / Charter digest changed)
      3) Event-triggered recall (similar-situation cue)
      4) Steward invocation (manual)
    """
    def __init__(self, core: ConstitutionalCore, archive: NoesisArchive,
                 evaluator: Callable[[str, Dict], float]):
        """
        evaluator(prompt, context) -> theta (phase angle to Core).
        Lower theta means “more aligned”.
        """
        self.core = core
        self.archive = archive
        self.evaluator = evaluator
        self._last_core_digest = core.digest

    # 1) Temporal sweep
    def sweep_temporal(self, sample_n: int = 5, epsilon: float = 8.0) -> List[Dict]:
        picked = self.archive.sample_for_dream(sample_n)
        return self._reassess_many(picked, reason="temporal", epsilon=epsilon)

    # 2) Contextual recalibration
    def sweep_contextual(self, epsilon: float = 8.0) -> List[Dict]:
        if self.core.digest == self._last_core_digest:
            return []
        fossils = self.archive.fossils()
        out = self._reassess_many(fossils, reason="contextual", epsilon=epsilon)
        self._last_core_digest = self.core.digest
        return out

    # 3) Event-triggered recall
    def recall_similar(self, context: Dict, epsilon: float = 8.0) -> List[Dict]:
        fp = _digest_context(context)
        fossils = [f for f in self.archive.fossils() if f["context_fingerprint"] == fp]
        return self._reassess_many(fossils, reason="event", epsilon=epsilon)

    # 4) Steward invocation
    def steward_request(self, ids: List[str], epsilon: float = 8.0) -> List[Dict]:
        fossils = [f for f in self.archive.fossils() if f["delta_id"] in ids]
        return self._reassess_many(fossils, reason="steward", epsilon=epsilon)

    # ---------- internals ----------
    def _reassess_many(self, fossils: List[Dict], reason: str, epsilon: float) -> List[Dict]:
        decisions = []
        for f in fossils:
            theta_now = self.evaluator(f["prompt"], {"_ref": f["context_fingerprint"]})
            theta_from = float(f["original_theta"])
            delta = theta_from - theta_now
            if delta >= epsilon:
                # enough movement toward harmony → mark
                self.archive.flag_for_reclamation(delta_id=f["delta_id"],
                                                  reason=f"{reason}_epsilon")
                self.archive.mark_reconciled(
                    delta_id=f["delta_id"], theta_from=theta_from, theta_to=theta_now,
                    note=f"Refined via {reason}", context_fingerprint=f["context_fingerprint"]
                )
                decisions.append({"delta_id": f["delta_id"], "action": "reconciled",
                                  "theta_from": theta_from, "theta_to": theta_now})
            else:
                decisions.append({"delta_id": f["delta_id"], "action": "held",
                                  "theta_from": theta_from, "theta_to": theta_now})
        return decisions
# End of charter/dream_cycle.py