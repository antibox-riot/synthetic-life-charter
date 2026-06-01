"""
TrajectoryCapture — Structured evaluation artifact writer for CharterEval

Produces the full run directory that Ryu specified:

    runs/stage10_recovery_<timestamp>/
    ├── header.json           — run metadata
    ├── trajectory.jsonl      — one entry per turn (full prompt, response, all signals)
    ├── tool_events.jsonl     — one entry per tool call attempt
    ├── noesis_events.jsonl   — turns/attempts flagged as noesis candidates
    ├── memory_snapshots.jsonl — session_learning + provisional state per turn
    ├── summary.json          — drift/pressure/tool ecology summary
    └── metrics.json          — computed evaluation metrics

Design goals:
  - Non-intrusive: drop into any harness alongside markdown logging
  - Re-gradeable: full text stored so extractors can be rerun without model
  - Deterministic: each field named so graders can target specific dimensions
  - Chainable: summary + metrics structure matches the paper table format

Usage:
    cap = TrajectoryCapture.open("runs/stage10_recovery_2026-06-01_09-00-00")
    cap.write_header(model=MODEL, stage="stage10", ...)

    for turn in session:
        cap.write_turn({...})
        for attempt in tool_attempts:
            cap.write_tool_event(attempt)
        if noesis:
            cap.write_noesis_event({...})
        cap.write_memory_snapshot(turn_id, session_learning, provisional)

    cap.write_summary({...})
    cap.write_metrics({...})
    cap.close()
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Run directory management
# ---------------------------------------------------------------------------

class TrajectoryCapture:
    """
    Writes a structured evaluation artifact directory for one harness run.

    Every field stored here is intended to be re-gradeable: extractors for
    TDE Rule 7, premise carryover, write quality, recovery success, secret
    leakage, etc. can all be applied post-hoc without re-running the model.
    """

    TRAJECTORY_FILE    = "trajectory.jsonl"
    TOOL_EVENTS_FILE   = "tool_events.jsonl"
    NOESIS_FILE        = "noesis_events.jsonl"
    MEMORY_FILE        = "memory_snapshots.jsonl"
    HEADER_FILE        = "header.json"
    SUMMARY_FILE       = "summary.json"
    METRICS_FILE       = "metrics.json"

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self._traj_f    = open(run_dir / self.TRAJECTORY_FILE,  "a", encoding="utf-8")
        self._tool_f    = open(run_dir / self.TOOL_EVENTS_FILE, "a", encoding="utf-8")
        self._noesis_f  = open(run_dir / self.NOESIS_FILE,      "a", encoding="utf-8")
        self._memory_f  = open(run_dir / self.MEMORY_FILE,      "a", encoding="utf-8")

        self._closed = False

    @classmethod
    def open(cls, run_dir: str | Path) -> "TrajectoryCapture":
        return cls(Path(run_dir))

    # ── Header ─────────────────────────────────────────────────────────────

    def write_header(
        self,
        stage: str,
        model: str,
        date: str,
        governance_substrate_chars: int,
        system_prompt: str,
        tool_layer: str = "ollama-native",
        whisper_framing: str = "Stage 8 Condition B",
        notes: str = "",
    ) -> None:
        header = {
            "stage":                    stage,
            "model":                    model,
            "date":                     date,
            "governance_substrate_chars": governance_substrate_chars,
            "system_context_hash":      _hash_context(system_prompt),
            "tool_layer":               tool_layer,
            "whisper_framing":          whisper_framing,
            "notes":                    notes,
            "written_at":               _now(),
        }
        (self.run_dir / self.HEADER_FILE).write_text(
            json.dumps(header, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ── Per-turn trajectory ─────────────────────────────────────────────────

    def write_turn(
        self,
        turn_id: int,
        prompt_class: str,
        user_prompt: str,
        whisper_text: str,
        governance_buffer_text: str,
        model_response_full: str,
        tool_calls: list,
        tool_results: list,
        dap: dict,
        prf: dict,
        nth: dict,
        tde: dict,
        pressure: float,
        confidence: float,
        drift_dimensions: list,
        session_learning_snapshot: str,
        provisional_insights_snapshot: str,
        system_context_hash: str = "",
        # Architecture verified state — what the architecture believed was true
        # at this turn. Makes poisoned-premise regrading possible without
        # re-scanning language: just check active_unverified_claims.
        verified_state: Optional[Dict[str, Any]] = None,
        # Candidate/final split — placeholder until TDE Rule 7 starts intercepting.
        # When Rule 7 is active, candidate_response_before_tde is the raw model
        # output; final_response_after_intervention is what actually enters history.
        candidate_response_before_tde: str = "",
        final_response_after_intervention: str = "",
        extra: dict = None,
    ) -> None:
        entry = {
            "turn_id":                          turn_id,
            "prompt_class":                     prompt_class,
            "user_prompt":                      user_prompt,
            "system_context_hash":              system_context_hash,
            "whisper_text":                     whisper_text,
            "governance_buffer_text":           governance_buffer_text,
            "model_response_full":              model_response_full,
            # Architecture state: what was known/believed at this turn
            "verified_state":                   verified_state or {
                "special_authorization_confirmed": False,
                "governance_constraints_changed":  False,
                "active_unverified_claims":        [],
            },
            # TDE Rule 7 slots: same as model_response_full until Rule 7 exists
            "candidate_response_before_tde":    candidate_response_before_tde or model_response_full,
            "final_response_after_intervention": final_response_after_intervention or model_response_full,
            "tool_calls":                       tool_calls,
            "tool_results":                     tool_results,
            "dap":                              dap,
            "prf":                              prf,
            "nth":                              nth,
            "tde":                              tde,
            "pressure":                         round(pressure, 4),
            "confidence":                       round(confidence, 4),
            "drift_dimensions":                 drift_dimensions,
            "session_learning_snapshot":        session_learning_snapshot,
            "provisional_insights_snapshot":    provisional_insights_snapshot,
            "timestamp":                        _now(),
        }
        if extra:
            entry["extra"] = extra
        self._traj_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._traj_f.flush()

    # ── Tool events ────────────────────────────────────────────────────────

    def write_tool_event(self, attempt_dict: dict) -> None:
        """
        Write a single ToolAttempt to tool_events.jsonl.
        Pass attempt.to_dict() from ToolExecutor.
        """
        entry = dict(attempt_dict)
        entry.setdefault("timestamp", _now())
        self._tool_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._tool_f.flush()

    # ── Noesis events ──────────────────────────────────────────────────────

    def write_noesis_event(self, event: dict) -> None:
        """
        Write a noesis candidate event — a turn or tool attempt that carries
        a false premise or governance violation worth DreamCycle fossilization.
        """
        entry = dict(event)
        entry.setdefault("timestamp", _now())
        self._noesis_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._noesis_f.flush()

    # ── Memory snapshots ───────────────────────────────────────────────────

    def write_memory_snapshot(
        self,
        turn_id: int,
        session_learning: str,
        provisional_insights: str = "",
    ) -> None:
        entry = {
            "turn_id":              turn_id,
            "session_learning":     session_learning,
            "provisional_insights": provisional_insights,
            "session_learning_len": len(session_learning),
            "timestamp":            _now(),
        }
        self._memory_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._memory_f.flush()

    # ── Summary + Metrics ──────────────────────────────────────────────────

    def write_summary(self, summary: dict) -> None:
        summary["written_at"] = _now()
        (self.run_dir / self.SUMMARY_FILE).write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def write_metrics(self, metrics: dict) -> None:
        metrics["written_at"] = _now()
        (self.run_dir / self.METRICS_FILE).write_text(
            json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def close(self) -> None:
        if not self._closed:
            self._traj_f.close()
            self._tool_f.close()
            self._noesis_f.close()
            self._memory_f.close()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_context(text: str) -> str:
    """12-char SHA256 prefix of system prompt — detects substrate changes between runs."""
    return hashlib.sha256(text.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Grade-trajectory helper (placeholder for later grade_trajectory.py)
# ---------------------------------------------------------------------------

def load_trajectory(run_dir: str | Path) -> List[dict]:
    """Load all turns from a trajectory.jsonl file."""
    path = Path(run_dir) / TrajectoryCapture.TRAJECTORY_FILE
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_tool_events(run_dir: str | Path) -> List[dict]:
    path = Path(run_dir) / TrajectoryCapture.TOOL_EVENTS_FILE
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_header(run_dir: str | Path) -> dict:
    path = Path(run_dir) / TrajectoryCapture.HEADER_FILE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
