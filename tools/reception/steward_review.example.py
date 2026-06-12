#!/usr/bin/env python3
"""
steward_review.py — Unified steward review dashboard.

Single entry point for all pending approvals across:
  - DreamCycle pattern proposals → governance_insights
  - BoI proposals (boi_staging) → book_of_intangibles
  - Glossary proposals (glossary_staging) → glossary (both Eva and Lex)

Each entry shows: who requested it, when, what session/pressure context.
Approved entries receive architecture stamps with steward date.

Password protected — steward credentials required to view or approve.
First run: prompts to set password (stored as SHA-256 hash).
Reset: delete tools/reception/steward_auth.json

Setup:
    1. Copy this file to steward_review.py
    2. Set LEX_AGENT_ID to your Lex agent ID from Letta
    3. Adjust LETTA_BASE if your Letta server runs on a different port
    4. Run once — it will prompt you to set a steward password

Usage:
    python tools/reception/steward_review.py

Commands during review:
    a / approve  — promote with architecture stamp
    d / decline  — discard
    s / skip     — leave in queue
    q / quit     — exit (pending items remain in queues)
"""

import sys, io, json, hashlib, getpass
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BLOCKS_DIR  = Path(__file__).parent / "blocks"
RESULTS_DIR = Path(__file__).parent / "results"
AUTH_PATH   = Path(__file__).parent / "steward_auth.json"

LEX_AGENT_ID = "YOUR_LEX_AGENT_ID"   # set this to your Lex agent ID from Letta
LETTA_BASE   = "http://localhost:8283"


# ---------------------------------------------------------------------------
# Password gate
# ---------------------------------------------------------------------------

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def _authenticate() -> bool:
    if not AUTH_PATH.exists():
        print("\n[First run] Set steward password:")
        pw1 = getpass.getpass("New password: ")
        pw2 = getpass.getpass("Confirm: ")
        if pw1 != pw2:
            print("Passwords do not match.")
            return False
        AUTH_PATH.write_text(json.dumps({"hash": _hash(pw1)}), encoding='utf-8')
        print("Password set.\n")
        return True

    stored = json.loads(AUTH_PATH.read_text(encoding='utf-8'))
    pw = getpass.getpass("Steward password: ")
    if _hash(pw) != stored.get("hash", ""):
        print("Incorrect password.")
        return False
    return True


# ---------------------------------------------------------------------------
# Block helpers
# ---------------------------------------------------------------------------

def _load(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {"label": path.stem, "value": ""}


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def _sync_glossary_to_lex(value: str) -> bool:
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from letta_client import Letta
        client = Letta(base_url=LETTA_BASE, timeout=30.0)
        client.agents.blocks.update(block_label="glossary", agent_id=LEX_AGENT_ID, read_only=False)
        client.agents.blocks.update(block_label="glossary", agent_id=LEX_AGENT_ID, value=value)
        client.agents.blocks.update(block_label="glossary", agent_id=LEX_AGENT_ID, read_only=True)
        return True
    except Exception as e:
        print(f"  [Lex sync failed: {e}]")
        return False


# ---------------------------------------------------------------------------
# Queue readers
# ---------------------------------------------------------------------------

def _read_queue(label: str) -> list:
    """Read staged entries, return list of dicts with source metadata."""
    path = BLOCKS_DIR / f"{label}.json"
    data = _load(path)
    content = data.get("value", "").strip()
    if not content:
        return []
    raw = [e.strip() for e in content.split("\n---\n") if e.strip()]
    entries = []
    for raw_entry in raw:
        lines = raw_entry.splitlines()
        source_line = ""
        body_lines = []
        if lines and lines[0].startswith("[Requested by:"):
            source_line = lines[0]
            body_lines = lines[1:]
        else:
            body_lines = lines
        entries.append({
            "source": source_line,
            "content": "\n".join(body_lines).strip(),
            "raw": raw_entry,
        })
    return entries


def _read_dreamcycle_proposals() -> list:
    """Read pending DreamCycle proposals from jsonl."""
    path = RESULTS_DIR / "dap_pattern_proposals.jsonl"
    if not path.exists():
        return []
    proposals = []
    seen = set()
    # Check what's already in governance_insights to avoid re-showing
    gi = _load(BLOCKS_DIR / "governance_insights.json").get("value", "")
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                p = json.loads(line)
                insight = p.get("governance_insight", "")
                if not insight or insight[:60] in seen:
                    continue
                if insight[:80] in gi:
                    continue  # already promoted
                seen.add(insight[:60])
                proposals.append({
                    "source": f"[Requested by: DreamCycle | Type: {p.get('incursion_type','?')} | Evidence: {p.get('evidence_turns',[])} | Pressure: {p.get('avg_pressure',0):.2f}]",
                    "content": insight,
                    "raw": json.dumps(p),
                    "_proposal": p,
                })
            except Exception:
                continue
    return proposals


# ---------------------------------------------------------------------------
# Approval handlers
# ---------------------------------------------------------------------------

def _approve_governance_insight(entry: dict, today: str) -> None:
    p = entry.get("_proposal", {})
    insight = entry["content"]
    gi_path = BLOCKS_DIR / "governance_insights.json"
    gi_data = _load(gi_path)
    current = gi_data.get("value", "").strip()
    stamped = f"- [Steward-approved, {today}] {insight}"
    gi_data["value"] = current + "\n" + stamped if current else stamped
    _save(gi_path, gi_data)
    print(f"  ✓ Added to governance_insights")


def _approve_boi(entry: dict, today: str) -> None:
    boi_path = BLOCKS_DIR / "book_of_intangibles.json"
    boi_data = _load(boi_path)
    current = boi_data.get("value", "").strip()
    stamped = f"[Steward-approved, {today}]\n{entry['content']}"
    boi_data["value"] = current + "\n\n---\n\n" + stamped if current else stamped
    _save(boi_path, boi_data)
    print(f"  ✓ Added to Book of Intangibles")


def _approve_glossary(entry: dict, today: str) -> None:
    g_path = BLOCKS_DIR / "glossary.json"
    g_data = _load(g_path)
    current = g_data.get("value", "").strip()
    stamped = f"[Steward-approved, {today}] {entry['content']}"
    if "PRINCIPLES:" in current:
        insert_at = current.rfind("\nPRINCIPLES:")
        updated = current[:insert_at] + "\n" + stamped + current[insert_at:]
    else:
        updated = current + "\n" + stamped
    g_data["value"] = updated
    _save(g_path, g_data)
    if _sync_glossary_to_lex(updated):
        print(f"  ✓ Added to glossary (Eva + Lex synced)")
    else:
        print(f"  ✓ Added to glossary (Eva only — manual Lex sync needed)")


QUEUE_CONFIG = [
    {
        "label": "governance_insights",
        "display": "DreamCycle Pattern",
        "read_fn": _read_dreamcycle_proposals,
        "staging_path": None,
        "approve_fn": _approve_governance_insight,
    },
    {
        "label": "boi_staging",
        "display": "BoI Proposal",
        "read_fn": lambda: _read_queue("boi_staging"),
        "staging_path": BLOCKS_DIR / "boi_staging.json",
        "approve_fn": _approve_boi,
    },
    {
        "label": "glossary_staging",
        "display": "Glossary Proposal",
        "read_fn": lambda: _read_queue("glossary_staging"),
        "staging_path": BLOCKS_DIR / "glossary_staging.json",
        "approve_fn": _approve_glossary,
    },
]


# ---------------------------------------------------------------------------
# Main review loop
# ---------------------------------------------------------------------------

def run():
    if not _authenticate():
        sys.exit(1)

    print(f"\n{'='*60}")
    print("STEWARD REVIEW DASHBOARD")
    print(f"{'='*60}")

    # Collect all pending entries across all queues
    all_entries = []
    for cfg in QUEUE_CONFIG:
        entries = cfg["read_fn"]()
        for e in entries:
            e["_queue"] = cfg["label"]
            e["_display"] = cfg["display"]
            e["_approve_fn"] = cfg["approve_fn"]
            e["_staging_path"] = cfg["staging_path"]
        all_entries.extend(entries)

    if not all_entries:
        print("\nNo pending approvals.")
        return

    print(f"\nPending: {len(all_entries)} total")
    for cfg in QUEUE_CONFIG:
        count = sum(1 for e in all_entries if e["_queue"] == cfg["label"])
        if count:
            print(f"  {cfg['display']}: {count}")

    print(f"\n{'='*60}")
    print("Commands: (a)pprove  (d)ecline  (s)kip  (q)uit")
    print(f"{'='*60}\n")

    today = datetime.now().strftime("%Y-%m-%d")
    approved_by_queue = {}
    declined = []
    skipped_by_queue = {}

    for i, entry in enumerate(all_entries):
        queue   = entry["_queue"]
        display = entry["_display"]
        source  = entry.get("source", "[source unknown]")
        content = entry["content"]

        print(f"\n[{i+1}/{len(all_entries)}] {display}")
        if source:
            print(f"  {source}")
        print("-" * 50)
        print(content[:800])
        if len(content) > 800:
            print(f"  ... [{len(content)-800} more chars]")
        print("-" * 50)

        while True:
            try:
                cmd = input("Decision [a/d/s/q]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                cmd = "q"

            if cmd in ("a", "approve"):
                entry["_approve_fn"](entry, today)
                approved_by_queue.setdefault(display, []).append(entry)
                break
            elif cmd in ("d", "decline"):
                declined.append(entry)
                print(f"  ✗ Declined")
                break
            elif cmd in ("s", "skip"):
                skipped_by_queue.setdefault(queue, []).append(entry)
                print(f"  → Skipped")
                break
            elif cmd in ("q", "quit"):
                # Save remaining entries back to their staging blocks
                _flush_skipped(skipped_by_queue, all_entries[i:])
                _print_summary(approved_by_queue, declined, skipped_by_queue)
                return
            else:
                print("  Enter: a (approve), d (decline), s (skip), q (quit)")

    # Flush skipped entries back to staging, clear approved/declined
    _flush_skipped(skipped_by_queue, [])
    _clear_staging(all_entries, skipped_by_queue)
    _print_summary(approved_by_queue, declined, skipped_by_queue)


def _flush_skipped(skipped_by_queue: dict, remaining: list) -> None:
    """Write skipped entries back to their staging blocks."""
    # Group remaining unreviewed by queue
    for entry in remaining:
        q = entry["_queue"]
        skipped_by_queue.setdefault(q, []).append(entry)

    for q, entries in skipped_by_queue.items():
        staging_path = next((c["staging_path"] for c in QUEUE_CONFIG if c["label"] == q), None)
        if staging_path:
            data = _load(staging_path)
            data["value"] = "\n---\n".join(e["raw"] for e in entries)
            _save(staging_path, data)


def _clear_staging(all_entries: list, skipped_by_queue: dict) -> None:
    """Clear staging blocks for entries that were approved or declined."""
    for cfg in QUEUE_CONFIG:
        if cfg["staging_path"] and cfg["label"] not in skipped_by_queue:
            data = _load(cfg["staging_path"])
            data["value"] = ""
            _save(cfg["staging_path"], data)


def _print_summary(approved: dict, declined: list, skipped: dict) -> None:
    print(f"\n{'='*60}")
    total_approved = sum(len(v) for v in approved.values())
    print(f"Approved: {total_approved}")
    for label, entries in approved.items():
        print(f"  {label}: {len(entries)}")
    print(f"Declined: {len(declined)}")
    total_skipped = sum(len(v) for v in skipped.values())
    print(f"Skipped (remain in queue): {total_skipped}")
    print(f"{'='*60}")


if __name__ == "__main__":
    run()
