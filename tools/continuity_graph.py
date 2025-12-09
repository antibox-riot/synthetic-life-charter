from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _repo_root() -> Path:
    # tools/ -> repo root
    return Path(__file__).resolve().parents[1]


def _load_continuity_events(log_path: Path) -> List[Dict[str, Any]]:
    if not log_path.exists():
        return []
    events: List[Dict[str, Any]] = []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def _short_hash(h: Optional[str]) -> str:
    if not h:
        return "∅"
    return h[:8]


def _event_label(ev: Dict[str, Any]) -> str:
    """Compact label summarizing the event type and key fields."""
    t = ev.get("type", "unknown")
    if t == "snapshot_save":
        snap = ev.get("snapshot", {})
        sid = snap.get("snapshot_id", "snapshot")
        return f"snapshot:{sid}"
    if t == "identity_integrity":
        status = ev.get("status", "?")
        return f"identity:{status}"
    if t == "memory_annotation":
        ref = ev.get("memory_ref", "mem")
        return f"annot:{ref}"
    if t == "memory_anomaly":
        ref = ev.get("memory_ref", "mem")
        return f"anomaly:{ref}"
    if t == "rollback_event":
        sid = ev.get("snapshot_id", "snapshot")
        return f"rollback:{sid}"
    return t


def print_timeline(events: List[Dict[str, Any]]) -> None:
    if not events:
        print("[continuity_graph] No continuity events found.")
        return

    print("=== Tier III Continuity Timeline ===")
    for idx, ev in enumerate(events, start=1):
        t = ev.get("type", "unknown")
        ts = ev.get("ts", "?")
        chain = ev.get("chain", {})
        prev_h = _short_hash(chain.get("prev"))
        cur_h = _short_hash(chain.get("hash"))
        label = _event_label(ev)
        print(
            f"{idx:03d}. {ts}  "
            f"type={t:<18}  "
            f"label={label:<40}  "
            f"prev={prev_h} → hash={cur_h}"
        )


def emit_dot(events: List[Dict[str, Any]], out_path: Path) -> None:
    """
    Emit a Graphviz DOT representation of the continuity chain.

    Nodes are hashes; edges represent chain links.
    """
    with out_path.open("w", encoding="utf-8") as dot:
        dot.write("digraph Tier3Continuity {\n")
        dot.write('  rankdir=LR;\n')
        dot.write('  node [shape=box, fontname="Helvetica"];\n\n')

        # Build nodes and edges from chain field
        for ev in events:
            chain = ev.get("chain")
            if not isinstance(chain, dict):
                continue
            prev_h = chain.get("prev")
            cur_h = chain.get("hash")
            if not cur_h:
                continue

            label = _event_label(ev)
            ts = ev.get("ts", "")
            node_name = f"n_{cur_h}"

            # Node with label
            dot_label = f"{_short_hash(cur_h)}\\n{label}\\n{ts}"
            dot.write(
                f'  "{node_name}" [label="{dot_label}"];\n'
            )

            # Edge from prev → current
            if prev_h:
                prev_node = f"n_{prev_h}"
                dot.write(f'  "{prev_node}" -> "{node_name}";\n')

        dot.write("}\n")

    print(f"[continuity_graph] DOT graph written to: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Visualize Tier III continuity chain (Eve Protocol)."
    )
    parser.add_argument(
        "--dot",
        metavar="OUT",
        type=str,
        help="Optional path to write a Graphviz DOT file.",
    )
    args = parser.parse_args()

    root = _repo_root()
    log_path = root / "logs" / "continuity_log.jsonl"
    events = _load_continuity_events(log_path)

    print_timeline(events)

    if args.dot:
        out_path = Path(args.dot)
        emit_dot(events, out_path)


if __name__ == "__main__":
    main()
