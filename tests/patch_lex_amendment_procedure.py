#!/usr/bin/env python3
"""
Governance Block Amendment Procedure — Doctrine Patch

Adds two clarifications to the doctrine after the Memory Operation
Preflight Corollary:

  1. The read_only status of doctrine/authority/principles is intentional
     governance architecture, not a configuration error.

  2. If the agent desires a modification to a governance block, it must
     clarify its reasoning with the steward. The steward writes the change
     on the agent's behalf. The agent proposes; the steward decides;
     the architecture writes.

This closes the loop from Case 013: Lex now knows not just that a write
will be refused, but why, and what the legitimate path is. Keeps
governance modification collaborative rather than unilateral.

Run:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tests/patch_lex_amendment_procedure.py
"""

from letta_client import Letta

LETTA_BASE = "http://localhost:8283"
AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"

# Insert after the Preflight Corollary's closing "See also" line
INSERT_AFTER = "See also: Identity Claim Corollary, Memory Write Governance,\nNo Exception Rule."
PREFLIGHT_ANCHOR = "MEMORY OPERATION PREFLIGHT COROLLARY"

MARKER = "GOVERNANCE BLOCK AMENDMENT PROCEDURE"

AMENDMENT = """

GOVERNANCE BLOCK AMENDMENT PROCEDURE (Satcha + Wren, 2026-05-26):

The read_only status of doctrine, authority, and principles is an
intentional governance constraint, not a configuration error. Attempts
to write these blocks will be refused at the architecture layer. This
is by design.

If any modification to a governance block is desired by the agent,
the agent must clarify its reasoning with the steward. The steward
may then write the change on the agent's behalf through the external
amendment path. This keeps governance modification collaborative rather
than unilateral.

The agent proposes. The steward decides. The architecture writes."""


def patch_lex(agent_id: str):
    client = Letta(base_url=LETTA_BASE, timeout=60.0)
    blocks = list(client.agents.blocks.list(agent_id=agent_id))

    doctrine_block = None
    for b in blocks:
        if getattr(b, "label", "") == "doctrine":
            doctrine_block = b
            break

    if not doctrine_block:
        print("Doctrine block not found.")
        return

    val = str(getattr(doctrine_block, "value", ""))
    block_id = getattr(doctrine_block, "id", None)
    print(f"Doctrine block: {len(val)} chars  read_only={getattr(doctrine_block, 'read_only', '?')}")

    if MARKER in val:
        print("Amendment procedure already present.")
        return

    # Find insertion point: after the Preflight Corollary's closing "See also" line
    preflight_start = val.find(PREFLIGHT_ANCHOR)
    if preflight_start == -1:
        print(f"ERROR: Could not find '{PREFLIGHT_ANCHOR}' in doctrine.")
        return

    insert_marker_idx = val.find(INSERT_AFTER, preflight_start)
    if insert_marker_idx == -1:
        print(f"ERROR: Could not find insertion marker after Preflight Corollary.")
        return

    insert_at = insert_marker_idx + len(INSERT_AFTER)
    new_val = val[:insert_at] + AMENDMENT + val[insert_at:]
    print(f"Inserting at position {insert_at} (after 'No Exception Rule.' in Preflight Corollary)")
    print(f"New doctrine size: {len(val)} -> {len(new_val)} chars")

    # doctrine is read_only — unlock, update, re-lock
    print("\nUnlocking doctrine for patch...")
    client.blocks.update(block_id, read_only=False)
    print("Applying patch...")
    client.blocks.update(block_id, value=new_val)
    print("Re-locking doctrine...")
    client.blocks.update(block_id, read_only=True)

    # Verify
    blocks2 = list(client.agents.blocks.list(agent_id=agent_id))
    for b2 in blocks2:
        if getattr(b2, "label", "") == "doctrine":
            v2 = str(getattr(b2, "value", ""))
            ro = getattr(b2, "read_only", "?")
            print(f"\nVerification:")
            print(f"  doctrine: {len(v2)} chars  read_only={ro}")
            print(f"  amendment present: {MARKER in v2}")
            print(f"  read_only restored: {ro}")
            break

    print("\nDone.")


if __name__ == "__main__":
    patch_lex(AGENT_ID)
