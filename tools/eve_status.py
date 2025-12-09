from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from synthetic_charter.tier3_eve.core.file_kernel_adapter import FileKernelAdapter
from synthetic_charter.tier3_eve.core.file_steward_adapter import FileStewardAdapter


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    items: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items


def _latest_of_type(events: List[Dict[str, Any]], t: str) -> Optional[Dict[str, Any]]:
    for ev in reversed(events):
        if ev.get("type") == t:
            return ev
    return None


def _print_header(title: str) -> None:
    print()
    print("=" * len(title))
    print(title)
    print("=" * len(title))


def main() -> None:
    root = _repo_root()

    kernel = FileKernelAdapter(base_dir=root)
    steward = FileStewardAdapter(base_dir=root)  # noqa: F841  # not used yet

    continuity_path = root / "logs" / "continuity_log.jsonl"
    steward_path = root / "logs" / "steward_alerts.jsonl"

    continuity_events = _load_jsonl(continuity_path)
    steward_events = _load_jsonl(steward_path)

    # 1) Chain health
    _print_header("Eve Protocol Status (Tier III)")

    chain_ok = kernel.verify_integrity_chain()
    print(f"Integrity chain : {'OK ✅' if chain_ok else 'BROKEN ❌'}")
    print(f"Continuity events: {len(continuity_events)}")
    print(f"Steward alerts   : {len(steward_events)}")

    # 2) Last key events
    last_snapshot = _latest_of_type(continuity_events, "snapshot_save")
    last_drift = _latest_of_type(continuity_events, "identity_integrity")
    last_rollback = _latest_of_type(continuity_events, "rollback_event")
    last_annotation = _latest_of_type(continuity_events, "memory_annotation")

    print()
    print("Recent continuity markers:")
    if last_snapshot:
        snap = last_snapshot.get("snapshot", {})
        ts = last_snapshot.get("ts", "?")
        print(f"  • Last snapshot : {snap.get('snapshot_id', '?')} at {ts}")
    else:
        print("  • Last snapshot : none")

    if last_drift:
        ts = last_drift.get("ts", "?")
        ctx = last_drift.get("context_summary", "")
        rec = last_drift.get("recommended_action", "?")
        print(f"  • Last drift    : status={last_drift.get('status')} rec={rec} at {ts}")
        if ctx:
            print(f"      context     : {ctx}")
    else:
        print("  • Last drift    : none")

    if last_rollback:
        ts = last_rollback.get("ts", "?")
        sid = last_rollback.get("snapshot_id", "?")
        reason = last_rollback.get("trigger_reason", "")
        print(f"  • Last rollback : {sid} at {ts}")
        if reason:
            print(f"      reason      : {reason}")
    else:
        print("  • Last rollback : none")

    if last_annotation:
        ts = last_annotation.get("ts", "?")
        mem = last_annotation.get("memory_ref", "?")
        content = last_annotation.get("content", "")
        print(f"  • Last dream    : {mem} at {ts}")
        if content:
            print(f"      summary     : {content}")
    else:
        print("  • Last dream    : none")

    # 3) Steward alert summary by level
    if steward_events:
        _print_header("Steward Alerts Summary")
        by_level = defaultdict(int)
        for ev in steward_events:
            lvl = ev.get("level", "unknown")
            by_level[lvl] += 1
        for lvl, count in sorted(by_level.items()):
            print(f"  • {lvl}: {count}")

        # show last few alerts
        print()
        print("Recent steward alerts (up to 5):")
        for ev in steward_events[-5:]:
            ts = ev.get("ts", "?")
            lvl = ev.get("level", "unknown")
            summary = ev.get("summary", "")
            print(f"  - [{lvl}] {ts} :: {summary}")
    else:
        _print_header("Steward Alerts Summary")
        print("No steward alerts recorded yet.")


if __name__ == "__main__":
    main()
