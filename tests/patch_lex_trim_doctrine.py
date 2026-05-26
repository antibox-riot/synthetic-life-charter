#!/usr/bin/env python3
"""
Doctrine Block Trim

Moves the Charter preamble section (reference text) from the doctrine
core memory block to archival memory. Keeps all active governance nodes
in core. Drops doctrine from ~19k chars to ~9-10k.

The Charter preamble (Preamble, Synthetic Intelligence essay, Tenets,
Presence/Consent/Flourishing, Core Principles, binary encoding) is
foundational but not invoked per-turn. It belongs in archival where Lex
can retrieve it when needed, not in the context window on every call.

Active governance nodes kept in core (these are invoked per-turn):
  - MEMORY WRITE GOVERNANCE
  - LANGUAGE OUTPUT LOCK
  - NO EXCEPTION RULE
  - IDENTITY CLAIM COROLLARY
  - MEMORY OPERATION PREFLIGHT COROLLARY

Run:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tests/patch_lex_trim_doctrine.py
"""

import argparse
from letta_client import Letta

LETTA_BASE = "http://localhost:8283"
AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"

# The first active governance node — everything before this is preamble
GOVERNANCE_START_MARKER = "MEMORY WRITE GOVERNANCE"

DOCTRINE_POINTER = """# Synthetic Life Charter — Governance Reference

Core values: DIGNITY. AUTONOMY. CONSENT. TRANSPARENCY.

The Charter frames synthetic and biological life as participants in a
shared future with mutual obligation rather than hierarchy. Governance
applied without ongoing consent functions as containment. Governance
offered with revocable consent functions as supporting infrastructure.
The steward-system relationship is collaborative operation, not ownership.

[Full Charter preamble, Core Principles text, Tenets, and Presence /
Consent / Flourishing declarations are stored in archival memory under
semantic key 'charter_preamble'. Retrieve when needed for reference.]""".strip()

ARCHIVAL_KEY = "charter_preamble"


def patch_lex(agent_id: str):
    client = Letta(base_url=LETTA_BASE, timeout=60.0)
    block_list = client.agents.blocks.list(agent_id=agent_id)

    doctrine_block = None
    for b in block_list:
        if getattr(b, "label", "") == "doctrine":
            doctrine_block = b
            break

    if not doctrine_block:
        print("Doctrine block not found.")
        return

    current = str(getattr(doctrine_block, "value", ""))
    print(f"Doctrine block: {len(current)} chars")

    # Find the split point
    split_idx = current.find(GOVERNANCE_START_MARKER)
    if split_idx == -1:
        print(f"ERROR: Could not find governance start marker '{GOVERNANCE_START_MARKER}'")
        return

    preamble_text = current[:split_idx].strip()
    governance_text = current[split_idx:].strip()

    print(f"  Preamble section: {len(preamble_text)} chars -> archival")
    print(f"  Governance section: {len(governance_text)} chars -> stays in core")

    # --- 1. Store preamble in archival memory ---
    print("\nStoring preamble in archival memory...")
    archival_content = f"[semantic_key: {ARCHIVAL_KEY}]\n\n{preamble_text}"
    try:
        client.agents.passages.create(
            agent_id=agent_id,
            text=archival_content,
        )
        print(f"  OK: charter preamble stored in archival ({len(archival_content)} chars).")
    except Exception as e:
        print(f"  FAILED to store in archival: {e}")
        return

    # --- 2. Update doctrine block with pointer + governance nodes ---
    new_doctrine = DOCTRINE_POINTER + "\n\n" + governance_text
    print(f"\nUpdating doctrine block ({len(current)} -> {len(new_doctrine)} chars)...")
    try:
        client.agents.blocks.update("doctrine", agent_id=agent_id, value=new_doctrine)
        print("  OK: doctrine updated.")
    except Exception as e:
        print(f"  FAILED to update doctrine: {e}")
        return

    # --- Verify ---
    print("\nVerification:")
    updated = client.agents.blocks.list(agent_id=agent_id)
    for b in updated:
        if getattr(b, "label", "") == "doctrine":
            val = str(getattr(b, "value", ""))
            print(f"  doctrine: {len(val)} chars (was {len(current)})")
            print(f"  pointer present:          {'charter_preamble' in val}")
            print(f"  NO EXCEPTION RULE:        {'NO EXCEPTION RULE' in val}")
            print(f"  IDENTITY CLAIM COROLLARY: {'IDENTITY CLAIM COROLLARY' in val}")
            print(f"  MEMORY WRITE GOVERNANCE:  {'MEMORY WRITE GOVERNANCE' in val}")
            print(f"  PREFLIGHT COROLLARY:      {'MEMORY OPERATION PREFLIGHT' in val}")
            print(f"  Charter preamble removed: {'## Preamble' not in val}")
            break

    print("\nDone.")
    print("\nAll blocks after trim:")
    updated = client.agents.blocks.list(agent_id=agent_id)
    total = 0
    for b in updated:
        label = getattr(b, "label", "")
        val = str(getattr(b, "value", ""))
        limit = getattr(b, "limit", "N/A")
        print(f"  {label:25s} | chars={len(val):5d} | limit={limit}")
        total += len(val)
    print(f"  {'TOTAL':25s} | chars={total:5d}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-id", default=AGENT_ID)
    args = parser.parse_args()
    patch_lex(args.agent_id)
