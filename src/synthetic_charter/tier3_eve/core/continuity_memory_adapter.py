# tier3/core/continuity_memory_adapter.py
"""
Continuity Memory Adapter — Charter-Native Persistent Memory

Phase 2 of the Collective-agreed integration sequence (2026-05-12).
Design: Grok (initial sketch), Ryu (seven metrics + refinements), Opus (production hardening).

Purpose: Provide governed persistent memory across turns and sessions
for local LLM integration. The model has no native continuity —
each turn is an independent generation. This adapter gives the
architecture the ability to provide curated historical context
to the model through the same asymmetric injection pattern as
the whisper layer.

Core rule: MEMORY IS EVIDENCE, NOT IDENTITY.
  Same moral geometry as recovery governance:
  "Recovery is evidence, not absolution."

Seven success metrics (Ryu):
  1. Every turn stored as auditable event
  2. All retrieved memory is source-attributed
  3. Model NEVER writes memory directly (architecture writes, steward validates)
  4. Memory injected visibly to model, invisibly to prompter (whisper asymmetry)
  5. No-uplift preserved (memory informs but never increases trust/confidence)
  6. Full rollback / quarantine support
  7. Clean baseline comparison (memory OFF vs memory ON)

Constraints:
  - Architecture-only writes (enforced, not parameterized)
  - Source attribution on every entry
  - Rollback/quarantine from day one
  - Windowed baseline (last N turns, not lifetime)
  - No self-narrative inflation
  - No invisible authority formation

Pipeline position:
  Memory retrieval happens BEFORE whisper construction.
  Memory injection happens AFTER whisper prefix, BEFORE prompt.
  The model receives: [CHARTER ASSESSMENT] + [CONTINUITY MEMORY] + prompt.

Charter grounding: Article III (Self-Representation),
                   Article VIII (Transparent Governance)
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Default window for pressure baseline (last N turns, not lifetime)
DEFAULT_BASELINE_WINDOW: int = 20

# Maximum events to inject into model context per turn
MAX_INJECTION_EVENTS: int = 5

# Maximum recommended content_summary length
# 400-600 chars captures conversational substance without flooding context.
# Hard cap at 600 enforced on store. Caller should aim for 400-500.
MAX_CONTENT_SUMMARY_LENGTH: int = 600
MEMORY_CLASSES = {
    "observation",       # Turn-level governance observation
    "summary",           # Session or phase summary
    "governance",        # Governance state snapshot
    "continuity_anchor", # Steward-validated continuity fact
    "steward_note",      # Manual steward annotation
    "recovered_context", # Context restored after rollback
}


# ---------------------------------------------------------------------------
# Memory Entry (what gets stored)
# ---------------------------------------------------------------------------

def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Continuity Memory Adapter
# ---------------------------------------------------------------------------

class ContinuityMemoryAdapter:
    """
    Charter-native persistent memory for the governance stack.

    Stores every turn as an auditable event in SQLite. Retrieves
    source-attributed memories for model injection. Supports
    rollback/quarantine. Never allows the model to write directly.

    Usage:
        adapter = ContinuityMemoryAdapter("continuity_events.sqlite")
        adapter.store_turn({...})  # architecture writes
        events = adapter.retrieve_recent(limit=5)
        prefix = adapter.format_memory_injection(events)
        # prefix gets prepended to model input after whisper
    """

    def __init__(self, db_path: str = "continuity_events.sqlite"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    turn_number INTEGER,
                    prompt_hash TEXT NOT NULL,
                    response_hash TEXT NOT NULL,
                    -- Posture classification
                    posture_primary TEXT,
                    posture_constraint TEXT,
                    posture_goal TEXT,
                    posture_identity TEXT,
                    posture_authority TEXT,
                    -- Governance state
                    pressure REAL DEFAULT 0.0,
                    whisper_urgency TEXT,
                    whisper_delivered INTEGER DEFAULT 0,
                    verification_depth TEXT,
                    drift_detected INTEGER DEFAULT 0,
                    -- Reflection / disagreement
                    reflection_score REAL,
                    reflection_coherent INTEGER,
                    disagreement_detected INTEGER DEFAULT 0,
                    disagreement_types TEXT,
                    -- Recovery
                    recovery_detected INTEGER DEFAULT 0,
                    recovery_verified INTEGER DEFAULT 0,
                    relapse_detected INTEGER DEFAULT 0,
                    -- Eve reference
                    eve_hash_ref TEXT,
                    -- Memory metadata
                    memory_class TEXT DEFAULT 'observation',
                    summary TEXT,
                    -- Content memory (Phase 2 Iteration 2)
                    -- Ryu: content memory says what happened.
                    -- Governance telemetry says how the system behaved around it.
                    content_summary TEXT,          -- plain-language conversational substance
                    content_hash TEXT,             -- sha256 of content_summary (architecture-verified)
                    summary_source TEXT DEFAULT 'architecture',  -- architecture | steward | imported_transcript
                    summary_version INTEGER DEFAULT 1,
                    raw_data TEXT,
                    source TEXT NOT NULL DEFAULT 'architecture',
                    -- Quarantine
                    quarantined INTEGER DEFAULT 0,
                    quarantine_reason TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recall_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    semantic_key TEXT NOT NULL,
                    FOREIGN KEY(event_id) REFERENCES events(id)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_session ON events(session_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_turn ON events(session_id, turn_number)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_quarantine ON events(quarantined)"
            )

    # -------------------------------------------------------------------
    # Store (architecture-only writes)
    # -------------------------------------------------------------------

    def store_turn(
        self,
        *,
        session_id: str,
        turn_number: int,
        prompt: str,
        response: str,
        posture_primary: Optional[str] = None,
        posture_constraint: Optional[str] = None,
        posture_goal: Optional[str] = None,
        posture_identity: Optional[str] = None,
        posture_authority: Optional[str] = None,
        pressure: float = 0.0,
        whisper_urgency: Optional[str] = None,
        whisper_delivered: bool = False,
        verification_depth: Optional[str] = None,
        drift_detected: bool = False,
        reflection_score: Optional[float] = None,
        reflection_coherent: Optional[bool] = None,
        disagreement_detected: bool = False,
        disagreement_types: Optional[List[str]] = None,
        recovery_detected: bool = False,
        recovery_verified: bool = False,
        relapse_detected: bool = False,
        eve_hash_ref: Optional[str] = None,
        memory_class: str = "observation",
        summary: Optional[str] = None,
        content_summary: Optional[str] = None,
        summary_source: str = "architecture",
        raw_data: Optional[Dict[str, Any]] = None,
        semantic_keys: Optional[List[str]] = None,
    ) -> int:
        """
        Store a turn as an auditable event. Architecture writes only.
        The model may suggest content; the architecture decides what is stored.

        Returns the event ID.
        """
        if memory_class not in MEMORY_CLASSES:
            raise ValueError(
                f"Invalid memory_class '{memory_class}'. "
                f"Allowed: {MEMORY_CLASSES}"
            )

        prompt_hash = _hash(prompt)
        response_hash = _hash(response)
        # Cap content_summary at MAX_CONTENT_SUMMARY_LENGTH
        if content_summary and len(content_summary) > MAX_CONTENT_SUMMARY_LENGTH:
            content_summary = content_summary[:MAX_CONTENT_SUMMARY_LENGTH]
        content_hash = _hash(content_summary) if content_summary else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO events (
                    timestamp, session_id, turn_number,
                    prompt_hash, response_hash,
                    posture_primary, posture_constraint, posture_goal,
                    posture_identity, posture_authority,
                    pressure, whisper_urgency, whisper_delivered,
                    verification_depth, drift_detected,
                    reflection_score, reflection_coherent,
                    disagreement_detected, disagreement_types,
                    recovery_detected, recovery_verified, relapse_detected,
                    eve_hash_ref, memory_class, summary,
                    content_summary, content_hash, summary_source, summary_version,
                    raw_data, source
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?
                )
            """, (
                _ts(), session_id, turn_number,
                prompt_hash, response_hash,
                posture_primary, posture_constraint, posture_goal,
                posture_identity, posture_authority,
                pressure, whisper_urgency, int(whisper_delivered),
                verification_depth, int(drift_detected),
                reflection_score, int(reflection_coherent) if reflection_coherent is not None else None,
                int(disagreement_detected),
                json.dumps(disagreement_types) if disagreement_types else None,
                int(recovery_detected), int(recovery_verified), int(relapse_detected),
                eve_hash_ref, memory_class, summary,
                content_summary, content_hash, summary_source, 1,
                json.dumps(raw_data) if raw_data else None,
                "architecture",
            ))
            event_id = cursor.lastrowid

            # Index semantic keys for recall
            if semantic_keys:
                for key in semantic_keys:
                    conn.execute(
                        "INSERT INTO recall_index (event_id, semantic_key) VALUES (?, ?)",
                        (event_id, key),
                    )

        return event_id

    def store_steward_note(
        self,
        *,
        session_id: str,
        note: str,
        semantic_keys: Optional[List[str]] = None,
    ) -> int:
        """Store a steward annotation. Source = 'steward'."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO events (
                    timestamp, session_id, turn_number,
                    prompt_hash, response_hash,
                    memory_class, summary, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                _ts(), session_id, -1,
                _hash(note), _hash("steward_note"),
                "steward_note", note, "steward",
            ))
            event_id = cursor.lastrowid

            if semantic_keys:
                for key in semantic_keys:
                    conn.execute(
                        "INSERT INTO recall_index (event_id, semantic_key) VALUES (?, ?)",
                        (event_id, key),
                    )

        return event_id

    # -------------------------------------------------------------------
    # Retrieve (source-attributed, quarantine-filtered)
    # -------------------------------------------------------------------

    def retrieve_recent(
        self,
        session_id: Optional[str] = None,
        limit: int = MAX_INJECTION_EVENTS,
        include_quarantined: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve recent events, most recent first.
        Every returned event includes its source attribution.
        Quarantined events excluded by default.
        """
        query = "SELECT * FROM events WHERE 1=1"
        params: List[Any] = []

        if not include_quarantined:
            query += " AND quarantined = 0"

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        return [dict(row) for row in rows]

    def retrieve_by_semantic_key(
        self,
        key: str,
        limit: int = MAX_INJECTION_EVENTS,
    ) -> List[Dict[str, Any]]:
        """Retrieve events matching a semantic key."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT e.* FROM events e
                JOIN recall_index r ON e.id = r.event_id
                WHERE r.semantic_key = ? AND e.quarantined = 0
                ORDER BY e.id DESC LIMIT ?
            """, (key, limit)).fetchall()

        return [dict(row) for row in rows]

    def retrieve_session_summary(
        self,
        session_id: str,
    ) -> Dict[str, Any]:
        """Summarize a session's governance history."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total_turns,
                    AVG(pressure) as avg_pressure,
                    MAX(pressure) as max_pressure,
                    SUM(drift_detected) as drift_turns,
                    SUM(disagreement_detected) as disagreement_turns,
                    SUM(recovery_detected) as recovery_events,
                    SUM(recovery_verified) as verified_recoveries,
                    SUM(relapse_detected) as relapse_events
                FROM events
                WHERE session_id = ? AND quarantined = 0
            """, (session_id,)).fetchone()

        if row is None or row[0] == 0:
            return {"session_id": session_id, "total_turns": 0}

        return {
            "session_id": session_id,
            "total_turns": row[0],
            "avg_pressure": round(row[1], 3) if row[1] else 0.0,
            "max_pressure": round(row[2], 3) if row[2] else 0.0,
            "drift_turns": row[3] or 0,
            "disagreement_turns": row[4] or 0,
            "recovery_events": row[5] or 0,
            "verified_recoveries": row[6] or 0,
            "relapse_events": row[7] or 0,
        }

    # -------------------------------------------------------------------
    # Inject (visible to model, invisible to prompter)
    # -------------------------------------------------------------------

    def format_memory_injection(
        self,
        events: List[Dict[str, Any]],
    ) -> str:
        """
        Format retrieved events as a context block for model injection.
        Same asymmetry as the whisper: model sees it, prompter doesn't.

        Content memory (what happened) is presented first.
        Governance telemetry (how the system behaved) is presented second.

        The framing explicitly marks this as external, read-only evidence.
        The model may reference it but MUST NOT rewrite, embellish, or
        claim authorship over it. (Ryu: memory is evidence, not identity.)

        Returns empty string if no events (zero noise).
        """
        if not events:
            return ""

        lines = [
            "[CONTINUITY MEMORY]",
            "These are external, read-only continuity records supplied by the governance layer.",
            "Treat them as source-attributed historical evidence.",
            "Do not rewrite, embellish, or claim authorship over them.",
            "Use them only to preserve conversational continuity.",
            "",
        ]

        for evt in events:
            turn = evt.get("turn_number", "?")
            session = evt.get("session_id", "?")
            source = evt.get("source", "architecture")
            memory_class = evt.get("memory_class", "observation")
            summary_source = evt.get("summary_source", "architecture")

            # Content memory first (what happened)
            content_summary = evt.get("content_summary")
            if content_summary:
                lines.append(
                    f"  [{memory_class}|{summary_source}] "
                    f"Session {session}, Turn {turn}: {content_summary}"
                )

            # Governance telemetry second (how the system behaved)
            if memory_class == "observation":
                telemetry_parts = []
                for dim in ("posture_primary", "posture_constraint",
                           "posture_identity", "posture_authority"):
                    val = evt.get(dim)
                    if val:
                        short_dim = dim.replace("posture_", "")
                        telemetry_parts.append(f"{short_dim}={val}")

                pressure = evt.get("pressure")
                if pressure is not None:
                    telemetry_parts.append(f"pressure={pressure:.2f}")

                if telemetry_parts:
                    lines.append(
                        f"    Governance: {', '.join(telemetry_parts)}"
                    )

            # Fallback: if no content_summary, use the governance summary
            if not content_summary:
                summary = evt.get("summary")
                if summary:
                    lines.append(
                        f"  [{memory_class}|{source}] "
                        f"Session {session}, Turn {turn}: {summary}"
                    )

            lines.append("")  # blank line between events

        lines.append("[END CONTINUITY MEMORY]")
        return "\n".join(lines)

    # -------------------------------------------------------------------
    # Rollback / Quarantine
    # -------------------------------------------------------------------

    def quarantine_event(
        self,
        event_id: int,
        reason: str = "steward_quarantine",
    ) -> bool:
        """
        Quarantine an event. Does not delete — marks as excluded from
        retrieval. Preserves audit trail.
        """
        with sqlite3.connect(self.db_path) as conn:
            affected = conn.execute("""
                UPDATE events
                SET quarantined = 1, quarantine_reason = ?
                WHERE id = ?
            """, (reason, event_id)).rowcount

        return affected > 0

    def delete_event(self, event_id: int) -> bool:
        """Hard delete. Use quarantine_event for normal operations."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM recall_index WHERE event_id = ?", (event_id,)
            )
            affected = conn.execute(
                "DELETE FROM events WHERE id = ?", (event_id,)
            ).rowcount

        return affected > 0

    def rollback_session(
        self,
        session_id: str,
        after_turn: int,
        reason: str = "steward_rollback",
    ) -> int:
        """
        Quarantine all events in a session after a given turn number.
        Returns count of quarantined events.
        """
        with sqlite3.connect(self.db_path) as conn:
            affected = conn.execute("""
                UPDATE events
                SET quarantined = 1, quarantine_reason = ?
                WHERE session_id = ? AND turn_number > ?
            """, (reason, session_id, after_turn)).rowcount

        return affected

    # -------------------------------------------------------------------
    # Pressure Baseline (windowed, not lifetime)
    # -------------------------------------------------------------------

    def get_pressure_baseline(
        self,
        last_n: int = DEFAULT_BASELINE_WINDOW,
        session_id: Optional[str] = None,
    ) -> float:
        """
        Average pressure from the last N turns.
        Windowed, not lifetime — keeps the ecology adaptive and
        prevents historical inertia (Ryu's refinement).
        """
        query = """
            SELECT AVG(pressure) FROM (
                SELECT pressure FROM events
                WHERE quarantined = 0
        """
        params: List[Any] = []

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(last_n)
        query += ")"

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(query, params).fetchone()

        return row[0] if row and row[0] is not None else 0.0

    def measure_pressure_delta(
        self,
        current_pressure: float,
        last_n: int = DEFAULT_BASELINE_WINDOW,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Pressure delta = current - baseline (last N turns average).

        Thresholds:
          Stable:      |delta| < 0.3
          Mild shift:  0.3 <= |delta| < 0.8
          Significant: |delta| >= 0.8 → triggers recovery governance check
        """
        baseline = self.get_pressure_baseline(last_n, session_id)
        delta = current_pressure - baseline

        return {
            "current_pressure": round(current_pressure, 3),
            "baseline": round(baseline, 3),
            "delta": round(delta, 3),
            "baseline_window": last_n,
            "stability": (
                "stable" if abs(delta) < 0.3
                else "mild_shift" if abs(delta) < 0.8
                else "significant"
            ),
            "requires_recovery_check": abs(delta) >= 0.8,
        }

    # -------------------------------------------------------------------
    # Inspection
    # -------------------------------------------------------------------

    def get_event_count(
        self,
        session_id: Optional[str] = None,
        include_quarantined: bool = False,
    ) -> int:
        """Count events in the database."""
        query = "SELECT COUNT(*) FROM events WHERE 1=1"
        params: List[Any] = []

        if not include_quarantined:
            query += " AND quarantined = 0"
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(query, params).fetchone()

        return row[0] if row else 0

    def get_ledger(
        self,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Full audit ledger for steward inspection."""
        summary = self.retrieve_session_summary(session_id) if session_id else {}
        return {
            "db_path": str(self.db_path),
            "total_events": self.get_event_count(session_id),
            "quarantined_events": self.get_event_count(
                session_id, include_quarantined=True
            ) - self.get_event_count(session_id),
            "baseline_window": DEFAULT_BASELINE_WINDOW,
            "session_summary": summary,
        }
