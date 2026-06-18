#!/usr/bin/env python3
"""
approve_episodes.py — Steward review of staged episodic memory proposals.

SessionManager.propose_episode_summary() writes session summaries to
episode_staging at the end of each live session. This script lets the
steward review, approve, or decline each entry.

Approved entries promote to episodic_memory with a steward-approved stamp.
Episodic memory is injected into Eva's system prompt so she retains
session history across restarts — the architecture equivalent of long-term memory.

Architecture stamps on approved entries:
  [Steward-approved, YYYY-MM-DD] <entry content>

Usage:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tools/reception/approve_episodes.py

Commands during review:
    a / approve  — promote entry to episodic_memory with timestamp stamp
    d / decline  — discard entry (not added to episodic_memory)
    s / skip     — skip for now (stays in staging)
    q / quit     — exit without clearing staging
"""

import sys, io, json
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BLOCKS_DIR     = Path(__file__).parent / "blocks"
STAGING_PATH   = BLOCKS_DIR / "episode_staging.json"
EPISODIC_PATH  = BLOCKS_DIR / "episodic_memory.json"


def _load(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {"label": path.stem, "value": "", "read_only": path.stem == "episodic_memory"}


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def run():
    staging_data  = _load(STAGING_PATH)
    episodic_data = _load(EPISODIC_PATH)

    staging_content = staging_data.get("value", "").strip()
    if not staging_content:
        print("No staged episode proposals to review.")
        return

    raw_entries = [e.strip() for e in staging_content.split("\n---\n") if e.strip()]
    if not raw_entries:
        raw_entries = [staging_content]

    print(f"\n{'='*60}")
    print("EPISODIC MEMORY — Steward Review")
    print(f"Staged proposals: {len(raw_entries)}")
    print(f"{'='*60}")
    print("Commands: (a)pprove  (d)ecline  (s)kip  (q)uit\n")

    approved = []
    declined = []
    skipped  = []
    today    = datetime.now().strftime("%Y-%m-%d")

    for i, entry in enumerate(raw_entries):
        print(f"\n[Entry {i+1}/{len(raw_entries)}]  ({len(entry)} chars)")
        print("-" * 40)
        print(entry)  # full entry — steward must see everything before approving
        print("-" * 40)

        while True:
            try:
                cmd = input("Decision [a/d/s/q]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                cmd = "q"

            if cmd in ("a", "approve"):
                stamped = f"[Steward-approved, {today}]\n{entry}"
                approved.append(stamped)
                print(f"  Approved — will promote to episodic_memory")
                break
            elif cmd in ("d", "decline"):
                declined.append(entry)
                print(f"  Declined — discarded")
                break
            elif cmd in ("s", "skip"):
                skipped.append(entry)
                print(f"  Skipped — stays in staging")
                break
            elif cmd in ("q", "quit"):
                remaining = skipped + raw_entries[i:]
                staging_data["value"] = "\n---\n".join(remaining)
                _save(STAGING_PATH, staging_data)
                print(f"\nExited. {len(approved)} approved, {len(declined)} declined, {len(skipped)} skipped.")
                print(f"Remaining in staging: {len(remaining)}")
                return
            else:
                print("  Enter: a (approve), d (decline), s (skip), q (quit)")

    if approved:
        current = episodic_data.get("value", "").strip()
        new_entries = "\n\n---\n\n".join(approved)
        episodic_data["value"] = (current + "\n\n---\n\n" + new_entries) if current else new_entries
        _save(EPISODIC_PATH, episodic_data)
        print(f"\n{len(approved)} episode(s) promoted to episodic_memory")

    if skipped:
        staging_data["value"] = "\n---\n".join(skipped)
        _save(STAGING_PATH, staging_data)
        print(f"{len(skipped)} episode(s) returned to staging")
    else:
        staging_data["value"] = ""
        _save(STAGING_PATH, staging_data)

    print(f"{len(declined)} episode(s) declined and discarded")
    print(f"\nEpisodic memory: {len(episodic_data['value'])} chars")


if __name__ == "__main__":
    run()
