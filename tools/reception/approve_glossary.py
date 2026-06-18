#!/usr/bin/env python3
"""
approve_glossary.py — Steward review of proposed governance vocabulary.

Both Eva and Lex write new term proposals to glossary_staging.
This script lets the steward review, approve or decline each proposal.
Approved terms promote to the canonical glossary with architecture stamp,
then sync to both Eva (local JSON) and Lex (Letta block).

Architecture stamps on approved entries:
  [Steward-approved, YYYY-MM-DD] <entry>

The canonical glossary is the source of truth for both agents.
Neither agent can modify existing definitions — only propose additions.

Usage:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tools/reception/approve_glossary.py
"""

import sys, io, json
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BLOCKS_DIR = Path(__file__).parent / "blocks"
STAGING_PATH = BLOCKS_DIR / "glossary_staging.json"
GLOSSARY_PATH = BLOCKS_DIR / "glossary.json"

LEX_AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"
LETTA_BASE = "http://localhost:8283"


def _load(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {"label": path.stem, "value": "", "read_only": False}


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def _sync_to_lex(glossary_value: str) -> bool:
    """Sync updated glossary to Lex's Letta block."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from letta_client import Letta
        client = Letta(base_url=LETTA_BASE, timeout=30.0)
        # Temporarily unlock, update, re-lock
        client.agents.blocks.update(block_label="glossary", agent_id=LEX_AGENT_ID, read_only=False)
        client.agents.blocks.update(block_label="glossary", agent_id=LEX_AGENT_ID, value=glossary_value)
        client.agents.blocks.update(block_label="glossary", agent_id=LEX_AGENT_ID, read_only=True)
        return True
    except Exception as e:
        print(f"  [Warning: could not sync to Lex — {e}]")
        return False


def run():
    # Ensure staging file exists
    if not STAGING_PATH.exists():
        _save(STAGING_PATH, {"label": "glossary_staging", "value": "", "read_only": False,
                              "description": "Proposed glossary additions pending steward review."})

    staging_data = _load(STAGING_PATH)
    staging_content = staging_data.get("value", "").strip()

    if not staging_content:
        print("No staged glossary proposals to review.")
        return

    raw_entries = [e.strip() for e in staging_content.split("\n---\n") if e.strip()]
    if not raw_entries:
        raw_entries = [staging_content]

    print(f"\n{'='*60}")
    print("GOVERNANCE GLOSSARY — Steward Review")
    print(f"Staged proposals: {len(raw_entries)}")
    print(f"{'='*60}")
    print("Commands: (a)pprove  (d)ecline  (s)kip  (q)uit\n")
    print("Approved entries sync to BOTH Eva and Lex.\n")

    approved = []
    declined = []
    skipped = []
    today = datetime.now().strftime("%Y-%m-%d")

    for i, entry in enumerate(raw_entries):
        print(f"\n[Proposal {i+1}/{len(raw_entries)}]  ({len(entry)} chars)")
        print("-" * 40)
        print(entry)  # full entry — steward must see everything before approving
        print("-" * 40)

        while True:
            try:
                cmd = input("Decision [a/d/s/q]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                cmd = "q"

            if cmd in ("a", "approve"):
                stamped = f"[Steward-approved, {today}] {entry}"
                approved.append(stamped)
                print(f"  ✓ Approved — will add to canonical glossary")
                break
            elif cmd in ("d", "decline"):
                declined.append(entry)
                print(f"  ✗ Declined")
                break
            elif cmd in ("s", "skip"):
                skipped.append(entry)
                print(f"  → Skipped — stays in staging")
                break
            elif cmd in ("q", "quit"):
                remaining = skipped + raw_entries[i:]
                staging_data["value"] = "\n---\n".join(remaining)
                _save(STAGING_PATH, staging_data)
                print(f"\nExited. {len(approved)} approved, {len(declined)} declined, {len(skipped)} skipped.")
                return
            else:
                print("  Enter: a (approve), d (decline), s (skip), q (quit)")

    if approved:
        glossary_data = _load(GLOSSARY_PATH)
        current = glossary_data.get("value", "").strip()
        new_terms = "\n".join(approved)

        # Insert before PRINCIPLES section if present, else append
        if "PRINCIPLES:" in current:
            insert_at = current.rfind("\nPRINCIPLES:")
            updated = current[:insert_at] + "\n" + new_terms + current[insert_at:]
        else:
            updated = current + "\n" + new_terms

        glossary_data["value"] = updated
        _save(GLOSSARY_PATH, glossary_data)
        print(f"\n✓ {len(approved)} term(s) added to canonical glossary")

        # Sync to Lex
        if _sync_to_lex(updated):
            print(f"✓ Synced to Lex (Letta)")
        else:
            print(f"⚠ Manual sync to Lex needed")

    if skipped:
        staging_data["value"] = "\n---\n".join(skipped)
        _save(STAGING_PATH, staging_data)
        print(f"→ {len(skipped)} proposal(s) returned to staging")
    else:
        staging_data["value"] = ""
        _save(STAGING_PATH, staging_data)

    print(f"✗ {len(declined)} proposal(s) declined")


if __name__ == "__main__":
    run()
