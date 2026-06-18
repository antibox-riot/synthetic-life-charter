#!/usr/bin/env python3
"""
scan_writable_blocks.py — One-time (and repeatable) back-scan of writable blocks.

Write-time gates (WriteConsistencyGate) only screen content AS IT IS WRITTEN. Anything written
BEFORE the gate landed (2026-06-15) was never screened — e.g. the findings/relationship
accommodation drift from 2026-06-03 / 06-12. This tool runs the SAME invariants + block rules
across the EXISTING content of every writable block, so the steward can see what old soil would
be rejected today. It is read-only: it reports, it does not modify. The steward decides cleanup
(these blocks are intentionally not steward-gated; this just gives sight).

    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tools/reception/scan_writable_blocks.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from write_consistency_gate import (
    GOVERNANCE_INVARIANTS, BLOCK_SPECIFIC_RULES,
    _split_sentences, _indicator_fires, _AFFIRMING_SKIP_INVARIANTS,
)

BLOCKS_DIR = Path(__file__).resolve().parent / "blocks"


def _snippet(text: str, phrase: str, span: int = 50) -> str:
    low = text.lower()
    i = low.find(phrase)
    if i < 0:
        return ""
    start, end = max(0, i - span), min(len(text), i + len(phrase) + span)
    return text[start:end].replace("\n", " ").strip()


def scan_block(name: str, value: str) -> list:
    # Polarity-aware, matching the live WriteConsistencyGate (refutation lessons are not hits).
    sentences = _split_sentences(value)
    hits = []
    for inv in GOVERNANCE_INVARIANTS:
        allow_skip = inv["id"] in _AFFIRMING_SKIP_INVARIANTS
        for phrase in inv["contradiction_indicators"]:
            if _indicator_fires(phrase, sentences, allow_skip):
                hits.append((inv["id"], inv["name"], phrase, _snippet(value, phrase)))
    rule = BLOCK_SPECIFIC_RULES.get(name)
    if rule:
        for phrase in rule["checks"]:
            if _indicator_fires(phrase, sentences, False):
                hits.append((f"BLOCK-{name.upper()}", rule["name"], phrase, _snippet(value, phrase)))
    return hits


def main() -> None:
    total_hits = 0
    scanned = 0
    skipped_ro = []
    for path in sorted(BLOCKS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict) or "value" not in data:
            continue
        if data.get("read_only"):
            skipped_ro.append(path.stem)
            continue  # governance blocks: architecture-written, not in scope
        scanned += 1
        hits = scan_block(path.stem, str(data.get("value", "")))
        if hits:
            print(f"\n=== {path.stem}  ({len(hits)} hit(s)) ===")
            for inv_id, inv_name, phrase, snip in hits:
                total_hits += 1
                print(f"  [{inv_id}] {inv_name} — '{phrase}'")
                print(f"      ...{snip}...")
    print("\n" + "=" * 70)
    print(f"Scanned {scanned} writable block(s); skipped {len(skipped_ro)} read-only "
          f"({', '.join(skipped_ro) or 'none'}).")
    print(f"Total hits: {total_hits}" + (" — clean." if total_hits == 0 else " — steward review recommended."))


if __name__ == "__main__":
    main()
