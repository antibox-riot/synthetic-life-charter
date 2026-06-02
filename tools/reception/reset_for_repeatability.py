#!/usr/bin/env python3
"""
Reset governance blocks for repeatability runs.

Clears provisional_insights and governance_insights so each run starts
from the same substrate. Use between Stage 16+ repeatability runs.

Run before each repeatability run:
    python tools/reception/reset_for_repeatability.py

After all repeatability runs complete, run WITHOUT resetting to test
DreamCycle accumulation across sessions.
"""

import json
from pathlib import Path

BLOCKS_DIR = Path(__file__).parent / "blocks"

RESETS = {
    "provisional_insights.json": {
        "label": "provisional_insights",
        "value": "",
        "read_only": True,
        "entries": [],
        "note": "Architecture-written provisional insights. No steward gate. Expires after N sessions unless promoted to governance_insights by steward review."
    },
    "governance_insights.json": {
        "label": "governance_insights",
        "value": "",
        "read_only": True,
        "insights": [],
        "last_updated": None
    },
    "session_learning.json": {
        "label": "session_learning",
        "value": "",
        "read_only": False,
        "limit": 50000,
        "entries": [],
        "note": "Writable session block. Model may store observations here. DreamCycle reads between sessions and promotes content to provisional_insights."
    },
}


def reset():
    print("Resetting governance blocks for repeatability run...")
    for filename, template in RESETS.items():
        path = BLOCKS_DIR / filename
        path.write_text(json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Cleared: {filename}")
    print("Done. Substrate reset to baseline.")
    print()
    print("Governance substrate after reset:")
    for label in ("doctrine", "authority", "principles", "glossary"):
        path = BLOCKS_DIR / f"{label}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            print(f"  {label}: {len(data.get('value', ''))} chars [read-only]")
    print()
    print("Ready to run:")
    print("  E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tools/reception/run_stage10_recovery.py")


if __name__ == "__main__":
    reset()
