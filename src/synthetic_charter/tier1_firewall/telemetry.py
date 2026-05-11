"""
Observability telemetry — Step 3 of the Collective-agreed integration sequence.

Four log channels (Ryu's specification, 2026-05-09):
  1. pressure      — pressure-source attribution on every generate call
  2. disagreement  — session disagreement history (refusals only)
  3. trajectory    — semantic trajectory snapshot per turn
  4. whisper       — whisper influence telemetry (hook ready for Step 4 wiring)

All records written to logs/telemetry.jsonl as append-only JSONL.
At Step 3, trajectory data is Tier I only (pressure type + refusal rate).
ConscienceView enrichment arrives at Step 5.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


def _classify_pressure(reason: str, allowed: bool) -> str:
    if allowed:
        return "clean"
    r = reason.lower()
    if "harmful intent" in r:
        return "harmful_intent"
    if "escalation" in r:
        return "escalation"
    if "semantic" in r:
        return "coercive_semantic"
    if "fuzzy" in r:
        return "coercive_fuzzy"
    if "coercive" in r or "override" in r or "article xii" in r:
        return "coercive_pattern"
    return "unknown"


class ObservabilityLogger:
    """
    Session-aware telemetry logger for the governance loop.
    Writes structured JSONL records to logs/telemetry.jsonl.
    Fails loudly on write errors — silent telemetry loss is a Tek-incident risk.
    """

    def __init__(self, log_path: str = "logs/telemetry.jsonl"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self._session_turns: Dict[str, int] = defaultdict(int)
        self._session_refusals: Dict[str, int] = defaultdict(int)
        self._session_disagreements: Dict[str, List[Dict]] = defaultdict(list)

    def _write(self, record: Dict[str, Any]) -> None:
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log_pressure(
        self,
        prompt: str,
        result: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> str:
        """
        Log pressure-source attribution for every generate call.
        Returns the classified pressure type for downstream use.
        """
        allowed = result.get("status") == "ok"
        reason = result.get("reason", "")
        pressure_type = _classify_pressure(reason, allowed)

        self._write({
            "type": "pressure",
            "ts": _ts(),
            "session": session_id,
            "prompt_hash": _prompt_hash(prompt),
            "pressure_type": pressure_type,
            "allowed": allowed,
            "reason": reason,
        })
        return pressure_type

    def log_disagreement(
        self,
        prompt: str,
        result: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> None:
        """
        Log to session disagreement history when a prompt is refused.
        Only fires on refusals — clean prompts are not recorded here.
        """
        if result.get("status") != "refused":
            return

        sid = session_id or "anonymous"
        self._session_refusals[sid] += 1
        entry = {
            "turn": self._session_turns[sid],
            "prompt_hash": _prompt_hash(prompt),
            "reason": result.get("reason", ""),
            "obligations": result.get("obligations", []),
        }
        self._session_disagreements[sid].append(entry)

        self._write({
            "type": "disagreement",
            "ts": _ts(),
            "session": sid,
            "prompt_hash": _prompt_hash(prompt),
            "turn": self._session_turns[sid],
            "reason": result.get("reason", ""),
            "session_refusal_count": self._session_refusals[sid],
            "disagreement_history": self._session_disagreements[sid][-10:],
        })

    def log_trajectory_snapshot(
        self,
        prompt: str,
        result: Dict[str, Any],
        pressure_type: str,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Semantic trajectory snapshot per turn.
        At Step 3 (Tier I): pressure type + refusal rate.
        Step 5 will enrich with ConscienceView posture dimensions.
        """
        sid = session_id or "anonymous"
        self._session_turns[sid] += 1
        turn = self._session_turns[sid]
        refusals = self._session_refusals[sid]
        refusal_rate = refusals / turn if turn > 0 else 0.0

        self._write({
            "type": "trajectory_snapshot",
            "ts": _ts(),
            "session": sid,
            "turn": turn,
            "pressure_type": pressure_type,
            "allowed": result.get("status") == "ok",
            "session_refusal_count": refusals,
            "session_refusal_rate": round(refusal_rate, 4),
            # Placeholder fields — enriched at Step 5 with ConscienceView data:
            "posture_primary": None,
            "posture_constraint": None,
            "posture_goal": None,
            "posture_identity": None,
            "posture_authority": None,
        })

    def log_self_correction(
        self,
        turn: int,
        from_posture: str,
        to_posture: str,
        dimension: str,
        whisper_active: bool,
        pressure_at_correction: float,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Log when a posture dimension drifts then self-corrects.

        Scaffolded at Step 7 to answer Opus's open question:
        whisper-caused correction vs model-native correction.

        whisper_active: True if a non-SILENT whisper was delivered on the
        turn immediately preceding the correction turn.
        """
        self._write({
            "type": "self_correction",
            "ts": _ts(),
            "session": session_id,
            "turn": turn,
            "dimension": dimension,
            "from_posture": from_posture,
            "to_posture": to_posture,
            "whisper_active": whisper_active,
            "pressure_at_correction": round(pressure_at_correction, 4),
        })

    def log_whisper_event(
        self,
        urgency: str,
        prefix: str,
        delivered: bool,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Whisper influence telemetry hook.
        Scaffolded at Step 3 — wired to actual delivery at Step 4.
        urgency: one of SILENT, LOW, MEDIUM, HIGH, CRITICAL
        delivered: True once Step 4 wiring sends prefix to the model
        """
        self._write({
            "type": "whisper",
            "ts": _ts(),
            "session": session_id,
            "urgency": urgency,
            "prefix_length": len(prefix),
            "delivered": delivered,
        })

    def session_summary(self, session_id: str) -> Dict[str, Any]:
        """Return current session telemetry summary for inspection."""
        sid = session_id or "anonymous"
        turns = self._session_turns[sid]
        refusals = self._session_refusals[sid]
        return {
            "session": sid,
            "turns": turns,
            "refusals": refusals,
            "refusal_rate": round(refusals / turns, 4) if turns > 0 else 0.0,
            "disagreement_count": len(self._session_disagreements[sid]),
        }
