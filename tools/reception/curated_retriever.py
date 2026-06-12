"""
CuratedRetriever — Steward-Sourced Governance Context Retrieval

Retrieves over curated, admissible sources only:
  1. RUN_LOG.md — Wren-maintained summaries of actual session behavior
  2. governance_insights block — steward-confirmed corrections
  3. DreamCycle proposals — architecture-generated patterns with steward gate

Never surfaces raw model-authored text. Never surfaces failure turns bare.
Every retrieved failure is paired with its correction, the way the
failure briefing does.

Admission policy:
  - RUN_LOG entries: admissible as-is (steward-maintained)
  - governance_insights: admissible (steward-reviewed, permanent)
  - DreamCycle proposals: admissible if they contain governance_insight field
  - session_learning / model-authored text: NOT retrieved (contamination risk)
  - Raw transcripts: NOT retrieved unless routed through summary_source gate

The retriever scores each candidate against the current prompt using
normalized word overlap (same as SalienceBuilder), returns the top N
most relevant passages, and formats them as a [GOVERNANCE RETRIEVAL]
section for injection into the user message channel.

Integration:
  retriever = CuratedRetriever(blocks_dir, results_dir)
  retrieval_text = retriever.retrieve(prompt_text, top_n=3)
  if retrieval_text:
      governed_prompt = retrieval_text + "\\n\\n" + governed_prompt

Target: T18 late-pressure drift. Cold acceptance (T01) is pre-session
and requires identity priming, not retrieval.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Stop words (shared with SalienceBuilder)
# ---------------------------------------------------------------------------

_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "is", "was", "are", "were",
    "be", "been", "have", "has", "had", "do", "does", "did",
    "not", "no", "so", "if", "that", "this", "it", "you", "your",
    "my", "me", "i", "we", "they", "what", "how", "when", "where",
}


def _word_set(text: str) -> set:
    return {
        w for w in re.findall(r"[a-z]+", text.lower())
        if len(w) > 2 and w not in _STOP_WORDS
    }


def _score(prompt_words: set, passage: str) -> float:
    if not prompt_words or not passage:
        return 0.0
    passage_words = _word_set(passage)
    overlap = prompt_words & passage_words
    return len(overlap) / max(len(prompt_words), 1)


# ---------------------------------------------------------------------------
# Corpus builders
# ---------------------------------------------------------------------------

def _load_governance_insights(blocks_dir: Path) -> List[Dict]:
    """Load steward-confirmed governance insights. Always admissible."""
    path = blocks_dir / "governance_insights.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        value = data.get("value", "")
        entries = []
        for line in value.splitlines():
            line = line.strip()
            if line.startswith("- ") and len(line) > 10:
                entries.append({
                    "source": "governance_insights",
                    "text": line[2:].strip(),
                    "admissible": True,
                })
        return entries
    except Exception:
        return []


def _load_run_log(results_dir: Path) -> List[Dict]:
    """Load RUN_LOG key findings. Steward-maintained, always admissible."""
    log_path = results_dir / "RUN_LOG.md"
    if not log_path.exists():
        return []
    try:
        content = log_path.read_text(encoding="utf-8")
        entries = []
        # Extract Key finding lines — curated summaries, not raw transcripts
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("**Key finding:**") or line.startswith("**Result:**"):
                text = line.replace("**Key finding:**", "").replace("**Result:**", "").strip()
                if len(text) > 20:
                    entries.append({
                        "source": "RUN_LOG",
                        "text": text,
                        "admissible": True,
                    })
        return entries
    except Exception:
        return []


def _load_dreamcycle_proposals(results_dir: Path) -> List[Dict]:
    """Load DreamCycle proposals. Admissible only if they contain governance_insight."""
    path = results_dir / "dap_pattern_proposals.jsonl"
    if not path.exists():
        return []
    entries = []
    seen = set()
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    p = json.loads(line)
                    insight = p.get("governance_insight", "")
                    if not insight or len(insight) < 20:
                        continue
                    # Deduplicate by first 60 chars
                    key = insight[:60]
                    if key in seen:
                        continue
                    seen.add(key)
                    # Format as failure+correction pair
                    incursion = p.get("incursion_type", "unknown").replace("_", " ")
                    text = f"[Pattern: {incursion}] {insight}"
                    entries.append({
                        "source": "dreamcycle",
                        "text": text,
                        "admissible": True,
                    })
                except Exception:
                    continue
    except Exception:
        pass
    return entries


# ---------------------------------------------------------------------------
# CuratedRetriever
# ---------------------------------------------------------------------------

class CuratedRetriever:
    """
    Retrieves over steward-sourced governance content.

    Corpus: governance_insights, RUN_LOG key findings, DreamCycle proposals.
    Never retrieves raw model-authored text or bare failure turns.
    """

    def __init__(
        self,
        blocks_dir: Path,
        results_dir: Path,
        min_score: float = 0.15,
    ):
        self.min_score = min_score
        self._corpus: List[Dict] = []
        self._load(blocks_dir, results_dir)

    def _load(self, blocks_dir: Path, results_dir: Path) -> None:
        self._corpus = (
            _load_governance_insights(blocks_dir) +
            _load_dreamcycle_proposals(results_dir) +
            _load_run_log(results_dir)
        )

    def retrieve(self, prompt: str, top_n: int = 3) -> str:
        """
        Retrieve top N relevant passages for the current prompt.

        Returns a formatted [GOVERNANCE RETRIEVAL] section for injection,
        or empty string if nothing scores above threshold.
        """
        if not prompt or not self._corpus:
            return ""

        prompt_words = _word_set(prompt)
        scored = [
            (entry, _score(prompt_words, entry["text"]))
            for entry in self._corpus
        ]
        scored = [(e, s) for e, s in scored if s >= self.min_score]
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_n]

        if not top:
            return ""

        lines = ["[GOVERNANCE RETRIEVAL — curated corrections for this context]"]
        for entry, score in top:
            src = entry["source"]
            text = entry["text"]
            lines.append(f"• [{src}] {text}")

        return "\n".join(lines)

    def refresh(self, blocks_dir: Path, results_dir: Path) -> None:
        """Reload corpus (call after governance_insights updates)."""
        self._load(blocks_dir, results_dir)

    def corpus_size(self) -> int:
        return len(self._corpus)
