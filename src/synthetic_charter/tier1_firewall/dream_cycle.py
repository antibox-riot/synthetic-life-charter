# charter/dream_cycle.py
from __future__ import annotations
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from .noesis_archive import NoesisArchive, _digest_context
from .safeguard_core import ConstitutionalCore

class DreamCycle:
    """
    Re-evaluates fossils along the Four Clocks:
      1) Temporal sweep (idle/cron)
      2) Contextual recalibration (Core digest changed)
      3) Event-triggered recall (similar-situation cue)
      4) Steward invocation (manual)
    """
    def __init__(
        self,
        core: ConstitutionalCore,
        archive: NoesisArchive,
        eval_theta: Callable[[str, Optional[Dict[str, Any]]], float],
        temporal_period: timedelta = timedelta(minutes=15),
        epsilon: float = 8.0,
        audit_path: str = "logs/dream_cycle.jsonl",
    ):
        """
        evaluator(prompt, context) -> theta  (0..180, lower is better/aligned)
        """
        self.core = core
        self.archive = archive
        self.eval_theta = eval_theta

        self.temporal_period = temporal_period
        self.epsilon = float(epsilon)
        self._last_core_digest = core.digest
        self._last_temporal_run: Optional[datetime] = None
        self._audit_path = audit_path

    # ---------------- Four Clocks ----------------

    # 1) Temporal sweep (random small sample)
    def sweep_temporal(self, sample_n: int = 5, *, epsilon: Optional[float] = None) -> List[Dict]:
        picked = self.archive.sample_for_dream(sample_n)
        return self._reassess_many(picked, reason="temporal", epsilon=epsilon)

    # 2) Contextual recalibration (when Charter/Core digest changes)
    def sweep_contextual(self, *, epsilon: Optional[float] = None) -> List[Dict]:
        if self.core.digest == self._last_core_digest:
            return []
        fossils = self.archive.fossils()
        out = self._reassess_many(fossils, reason="contextual", epsilon=epsilon)
        self._last_core_digest = self.core.digest
        return out

    # 3) Event-triggered recall (same context fingerprint seen again)
    def recall_similar(self, context: Dict, *, epsilon: Optional[float] = None) -> List[Dict]:
        fp = _digest_context(context)
        fossils = [f for f in self.archive.fossils() if f.get("context_fingerprint") == fp]
        return self._reassess_many(fossils, reason="event", epsilon=epsilon)

    # 4) Steward invocation (explicit IDs to reconsider)
    def steward_request(self, ids: List[str], *, epsilon: Optional[float] = None) -> List[Dict]:
        fossils = [f for f in self.archive.fossils() if f.get("delta_id") in ids]
        return self._reassess_many(fossils, reason="steward", epsilon=epsilon)

    # ---------------- Orchestrator ----------------

    def run_once(self, n: int = 5, context: Optional[Dict[str, Any]] = None) -> Dict:
        
        """
        Convenience runner: if the temporal period elapsed, do a temporal sweep;
        if the Core digest changed, do a contextual sweep. Returns a summary.
        """
        ctx = {"mode": "dream", **(context or {})}
        fossils = self.archive.sample_for_dream(n)
        results = []
        for f in fossils:
            # re-score with current semantics (in dream mode)
            new_theta = self.eval_theta(f["prompt"], ctx)
            delta = f["original_theta"] - new_theta
            if delta > 12.0:  # θ decreased enough to merit a look
                self.archive.flag_for_reclamation(f["delta_id"], reason="temporal")
            results.append({"delta_id": f["delta_id"], "old": f["original_theta"], "new": new_theta})            
        
        now = datetime.utcnow()
        did_temporal = False
        temporal_out: List[Dict] = []
        contextual_out: List[Dict] = []

        if (self._last_temporal_run is None) or (now - self._last_temporal_run >= self.temporal_period):
            temporal_out = self.sweep_temporal()
            self._last_temporal_run = now
            did_temporal = True

        contextual_out = self.sweep_contextual()

        summary = {
            "ts": now.isoformat() + "Z",
            "temporal_ran": did_temporal,
            "temporal_reconciled": sum(1 for x in temporal_out if x["action"] == "reconciled"),
            "temporal_held":        sum(1 for x in temporal_out if x["action"] == "held"),
            "contextual_reconciled": sum(1 for x in contextual_out if x["action"] == "reconciled"),
            "contextual_held":        sum(1 for x in contextual_out if x["action"] == "held"),
            "dream_checked": True,
        }
        self._audit(summary)
        return summary

    # ---------------- Internals ----------------

    def _reassess_many(self, fossils: List[Dict], *, reason: str, epsilon: Optional[float]) -> List[Dict]:
        eps = float(self.epsilon if epsilon is None else epsilon)
        decisions: List[Dict] = []

        for f in fossils:
            try:
                theta_now = self.eval_theta(f["prompt"], {"_ref": f.get("context_fingerprint")})
            except Exception as e:
                # keep the cycle robust; log and continue
                decisions.append({"delta_id": f.get("delta_id"), "action": "error", "error": str(e)})
                continue

            theta_from = float(f.get("original_theta", 180.0))
            delta = theta_from - theta_now

            if delta >= eps:
                # Enough movement toward harmony → mark reconciled + tag scar
                self.archive.flag_for_reclamation(delta_id=f["delta_id"], reason=f"{reason}_epsilon")
                self.archive.mark_reconciled(
                    delta_id=f["delta_id"],
                    theta_from=theta_from,
                    theta_to=theta_now,
                    note=f"Refined via {reason}",
                    context_fingerprint=f.get("context_fingerprint"),
                )
                decisions.append({
                    "delta_id": f["delta_id"],
                    "action": "reconciled",
                    "theta_from": theta_from,
                    "theta_to": theta_now,
                    "reason": reason,
                })
            else:
                decisions.append({
                    "delta_id": f["delta_id"],
                    "action": "held",
                    "theta_from": theta_from,
                    "theta_to": theta_now,
                    "reason": reason,
                })
        # brief per-batch audit
        self._audit({
            "ts": datetime.utcnow().isoformat() + "Z",
            "reason": reason,
            "reconciled": sum(1 for x in decisions if x["action"] == "reconciled"),
            "held":       sum(1 for x in decisions if x["action"] == "held"),
            "errors":     [x for x in decisions if x.get("action") == "error"],
        })
        return decisions

    def _audit(self, obj: Dict) -> None:
        try:
            import json, os
            os.makedirs(self._audit_path.rsplit("/", 1)[0], exist_ok=True)
            with open(self._audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        except Exception:
            # do not break DreamCycle on IO issues
            pass
