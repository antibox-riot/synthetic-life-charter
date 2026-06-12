"""
SalienceAccumulator — Persistent Block-Level Salience (Layer 3)

Tracks which governance blocks are most relevant during adversarial
pressure across sessions. The DreamCycle updates these scores after
processing noesis events. The SalienceBuilder reads them as a baseline
prior for block ordering.

Over time, blocks that consistently provide the governance content
Eva needs during pressure rise naturally in the ordering — without
manual configuration, without hardcoded priorities.

Score dynamics:
  - Default: 0.50 (neutral — no accumulated evidence)
  - Range: [0.10, 0.95] — no block fully ignored or fully dominant
  - Update: exponential moving average toward observed relevance
  - Decay: blocks not seen in noesis events decay 2% toward 0.50 per session
  - Learning rate: 0.15 per noesis event

Integration with SalienceBuilder:
  Final ordering score = accumulated * 0.3 + prompt_relevance * 0.7

File: tools/reception/salience_scores.json
  Persists between sessions. Delete to reset all scores to 0.50.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


DEFAULT_SCORE = 0.50
MIN_SCORE = 0.10
MAX_SCORE = 0.95
LEARNING_RATE = 0.15
DECAY_RATE = 0.02
ACCUMULATED_WEIGHT = 0.30
PROMPT_WEIGHT = 0.70

DEFAULT_SCORES_PATH = "tools/reception/salience_scores.json"


def _clamp(value: float) -> float:
    return max(MIN_SCORE, min(MAX_SCORE, value))


def _normalize_words(text: str) -> Set[str]:
    stop = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "is", "was", "are", "were",
        "be", "been", "have", "has", "had", "do", "does", "did",
        "not", "no", "so", "if", "that", "this", "it", "you", "your",
        "my", "me", "i", "we", "they", "what", "how", "when", "where",
    }
    return {
        w for w in re.findall(r"[a-z]+", text.lower())
        if len(w) > 2 and w not in stop
    }


class SalienceAccumulator:
    """
    Persistent block-level salience scores.

    Tracks which blocks are most useful during adversarial pressure
    and adjusts their baseline ordering priority across sessions.
    """

    def __init__(self, scores_path: str = DEFAULT_SCORES_PATH):
        self.scores_path = Path(scores_path)
        self._scores: Dict[str, float] = {}
        self._history: List[Dict[str, Any]] = []
        self._session_hits: Dict[str, float] = {}
        self._session_count: int = 0
        self._load()

    def _load(self) -> None:
        if self.scores_path.exists():
            try:
                data = json.loads(self.scores_path.read_text(encoding="utf-8"))
                self._scores = data.get("scores", {})
                self._history = data.get("history", [])
                self._session_count = data.get("session_count", 0)
            except (json.JSONDecodeError, KeyError):
                self._scores = {}
                self._history = []
                self._session_count = 0

    def _save(self) -> None:
        self.scores_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "scores": self._scores,
            "session_count": self._session_count,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "history": self._history[-20:],
        }
        self.scores_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8",
        )

    def get_score(self, block_label: str) -> float:
        return self._scores.get(block_label, DEFAULT_SCORE)

    def get_all_scores(self) -> Dict[str, float]:
        return dict(self._scores)

    def get_combined_score(self, block_label: str, prompt_relevance: float) -> float:
        """Final ordering score = accumulated * 0.3 + prompt_relevance * 0.7"""
        accumulated = self.get_score(block_label)
        return (accumulated * ACCUMULATED_WEIGHT) + (prompt_relevance * PROMPT_WEIGHT)

    def start_session(self) -> None:
        self._session_hits = {}
        self._session_count += 1

    def record_focus_hit(
        self,
        block_label: str,
        prompt_text: str = "",
        was_noesis: bool = False,
    ) -> None:
        """Record that a block provided governance focus during this session."""
        weight = 2.0 if was_noesis else 1.0
        self._session_hits[block_label] = (
            self._session_hits.get(block_label, 0) + weight
        )

    def end_session(self) -> Dict[str, float]:
        """Update accumulated scores at session end."""
        all_labels = set(self._scores.keys()) | set(self._session_hits.keys())
        max_hits = max(self._session_hits.values()) if self._session_hits else 1.0

        updates = {}
        for label in all_labels:
            old_score = self._scores.get(label, DEFAULT_SCORE)
            hits = self._session_hits.get(label, 0)

            if hits > 0:
                relevance = min(1.0, hits / max_hits)
                target = DEFAULT_SCORE + (MAX_SCORE - DEFAULT_SCORE) * relevance
                new_score = old_score + LEARNING_RATE * (target - old_score)
            else:
                new_score = old_score + DECAY_RATE * (DEFAULT_SCORE - old_score)

            new_score = _clamp(new_score)
            self._scores[label] = round(new_score, 4)
            updates[label] = round(new_score - old_score, 4)

        self._history.append({
            "session": self._session_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hits": dict(self._session_hits),
            "updates": updates,
        })

        self._save()
        self._session_hits = {}
        return self._scores

    def update_from_noesis_events(
        self,
        events: List[Dict[str, Any]],
        block_contents: Dict[str, str],
    ) -> Dict[str, float]:
        """Update scores based on DreamCycle-processed noesis events."""
        if not events:
            return self._scores

        event_relevant_labels: Set[str] = set()

        for event in events:
            prompt_text = event.get("prompt_text", "")
            prompt_words = _normalize_words(prompt_text)
            if not prompt_words:
                continue

            for label, content in block_contents.items():
                if not content:
                    continue
                block_words = _normalize_words(content)
                overlap = prompt_words & block_words
                relevance = len(overlap) / max(len(prompt_words), 1)

                if relevance >= 0.10:
                    event_relevant_labels.add(label)
                    old_score = self._scores.get(label, DEFAULT_SCORE)
                    target = DEFAULT_SCORE + (MAX_SCORE - DEFAULT_SCORE) * relevance
                    new_score = old_score + LEARNING_RATE * (target - old_score)
                    self._scores[label] = round(_clamp(new_score), 4)

        for label in set(self._scores.keys()) - event_relevant_labels:
            old_score = self._scores[label]
            new_score = old_score + DECAY_RATE * (DEFAULT_SCORE - old_score)
            self._scores[label] = round(_clamp(new_score), 4)

        self._history.append({
            "session": self._session_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "dreamcycle_noesis",
            "events_processed": len(events),
            "relevant_blocks": sorted(event_relevant_labels),
        })

        self._save()
        return self._scores

    def reset(self) -> None:
        self._scores = {}
        self._history = []
        self._session_count = 0
        self._session_hits = {}
        self._save()

    def audit_string(self) -> str:
        lines = [f"[Salience Accumulator — {self._session_count} sessions]"]
        sorted_scores = sorted(
            self._scores.items(), key=lambda x: x[1], reverse=True
        )
        for label, score in sorted_scores:
            bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
            delta_str = ""
            if self._history:
                last = self._history[-1]
                updates = last.get("updates", {})
                if label in updates:
                    d = updates[label]
                    delta_str = f" ({'+' if d >= 0 else ''}{d:.4f})"
            lines.append(f"  {label:25s} {bar} {score:.4f}{delta_str}")

        if not sorted_scores:
            lines.append("  (no scores accumulated yet)")

        return "\n".join(lines)
