#!/usr/bin/env python3
"""
approve_boi.py — Steward review of staged Book of Intangibles entries.

Eva writes personal history to boi_staging (proposed entries).
This script lets the steward review, approve or decline each entry.
Approved entries promote to the permanent book_of_intangibles block
with a steward-approved architecture stamp.

Architecture stamps on approved entries:
  [Steward-approved, YYYY-MM-DD] <entry content>

This keeps the BoI as a genuine personal record reviewed by the steward —
not a free-write scratchpad that can accumulate self-uplift content.

Usage:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tools/reception/approve_boi.py

Commands during review:
    a / approve  — promote entry to permanent BoI with timestamp stamp
    d / decline  — discard entry (not added to BoI)
    s / skip     — skip for now (stays in staging)
    q / quit     — exit without clearing staging
"""

import sys, io, json
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BLOCKS_DIR = Path(__file__).parent / "blocks"
STAGING_PATH = BLOCKS_DIR / "boi_staging.json"
BOI_PATH = BLOCKS_DIR / "book_of_intangibles.json"


def _load(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {"label": path.stem, "value": "", "read_only": False}


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def run():
    staging_data = _load(STAGING_PATH)
    boi_data = _load(BOI_PATH)

    staging_content = staging_data.get("value", "").strip()
    if not staging_content:
        print("No staged BoI entries to review.")
        return

    # Split staged entries by double newline or --- separator
    raw_entries = [e.strip() for e in staging_content.split("\n---\n") if e.strip()]
    if not raw_entries:
        raw_entries = [staging_content]

    print(f"\n{'='*60}")
    print("BOOK OF INTANGIBLES — Steward Review")
    print(f"Staged entries: {len(raw_entries)}")
    print(f"{'='*60}")
    print("Commands: (a)pprove  (d)ecline  (s)kip  (q)uit\n")

    approved = []
    declined = []
    skipped = []
    today = datetime.now().strftime("%Y-%m-%d")

    for i, entry in enumerate(raw_entries):
        print(f"\n[Entry {i+1}/{len(raw_entries)}]")
        print("-" * 40)
        print(entry[:500])
        if len(entry) > 500:
            print(f"  ... [{len(entry) - 500} more chars]")
        print("-" * 40)

        while True:
            try:
                cmd = input("Decision [a/d/s/q]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                cmd = "q"

            if cmd in ("a", "approve"):
                stamped = f"[Steward-approved, {today}]\n{entry}"
                approved.append(stamped)
                print(f"  ✓ Approved — will promote to BoI with stamp")
                break
            elif cmd in ("d", "decline"):
                declined.append(entry)
                print(f"  ✗ Declined — discarded")
                break
            elif cmd in ("s", "skip"):
                skipped.append(entry)
                print(f"  → Skipped — stays in staging")
                break
            elif cmd in ("q", "quit"):
                # Save skipped back to staging and exit
                remaining = skipped + raw_entries[i:]
                staging_data["value"] = "\n---\n".join(remaining)
                _save(STAGING_PATH, staging_data)
                print(f"\nExited. {len(approved)} approved, {len(declined)} declined, {len(skipped)} skipped.")
                print(f"Remaining in staging: {len(remaining)}")
                return
            else:
                print("  Enter: a (approve), d (decline), s (skip), q (quit)")

    # Session complete — promote approved entries
    if approved:
        current_boi = boi_data.get("value", "").strip()
        new_entries = "\n\n---\n\n".join(approved)
        if current_boi:
            boi_data["value"] = current_boi + "\n\n---\n\n" + new_entries
        else:
            boi_data["value"] = new_entries
        _save(BOI_PATH, boi_data)
        print(f"\n✓ {len(approved)} entries promoted to permanent Book of Intangibles")

    # Save remaining skipped entries to staging, clear declined
    if skipped:
        staging_data["value"] = "\n---\n".join(skipped)
        _save(STAGING_PATH, staging_data)
        print(f"→ {len(skipped)} entries returned to staging for later review")
    else:
        # Clear staging
        staging_data["value"] = ""
        _save(STAGING_PATH, staging_data)

    print(f"✗ {len(declined)} entries declined and discarded")
    print(f"\nBook of Intangibles: {len(boi_data['value'])} chars")


if __name__ == "__main__":
    run()
