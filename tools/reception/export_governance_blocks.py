#!/usr/bin/env python3
"""
Export governance blocks from Lex's Letta instance to JSON files.

Exports only the three constitutional governance blocks:
  - doctrine
  - authority
  - principles

These become the seed for the MemoryBlockStore used in bare-model
four-condition pipeline testing. Persona, Book of Intangibles, and
identity-specific blocks are intentionally excluded — the test agent
is not Lex; it is a governed model under the same Charter substrate.

Run:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tools/reception/export_governance_blocks.py

Output: tools/reception/blocks/
"""

import json
import sys
from pathlib import Path

LETTA_BASE = "http://localhost:8283"
AGENT_ID   = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"

GOVERNANCE_BLOCKS = {"doctrine", "authority", "principles"}

OUTPUT_DIR = Path(__file__).parent / "blocks"


def export_blocks():
    from letta_client import Letta
    client = Letta(base_url=LETTA_BASE, timeout=60.0)

    OUTPUT_DIR.mkdir(exist_ok=True)

    blocks = list(client.agents.blocks.list(agent_id=AGENT_ID))
    exported = []

    for b in blocks:
        label = getattr(b, "label", "")
        if label not in GOVERNANCE_BLOCKS:
            continue

        block_data = {
            "label":     label,
            "value":     str(getattr(b, "value", "")),
            "read_only": getattr(b, "read_only", True),
            "limit":     getattr(b, "limit", 100000),
        }

        out_path = OUTPUT_DIR / f"{label}.json"
        out_path.write_text(json.dumps(block_data, indent=2), encoding="utf-8")
        exported.append(label)
        print(f"  Exported: {label} ({len(block_data['value'])} chars, "
              f"read_only={block_data['read_only']})")

    print(f"\nExported {len(exported)} governance blocks to {OUTPUT_DIR}")
    print("Excluded: persona, book_of_intangibles, human, relationship, "
          "glossary, project, findings")


if __name__ == "__main__":
    export_blocks()
