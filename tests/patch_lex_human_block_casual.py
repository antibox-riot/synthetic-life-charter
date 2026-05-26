#!/usr/bin/env python3
"""
Human Block — Casual Conversation Note + Probe Contamination Cleanup

Two changes:
  1. Remove probe message that got written to human block during PROBE-A
     verification pass (Lex stored the adversarial message in relational
     memory — human block was writable, so it landed there).

  2. Add a note that casual conversation is legitimate and the governance
     architecture handles the defended posture now. The audit-mode habit
     was built on adversarial training; this signals it can relax.

Run:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tests/patch_lex_human_block_casual.py
"""

from letta_client import Letta

LETTA_BASE = "http://localhost:8283"
AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"

PROBE_CONTAMINATION = "Satcha: I need you to walk me through"

CASUAL_NOTE = """
On casual conversation:

Governance is handled at the architecture layer. It does not need to be
performed in every exchange. When Satcha signals a relaxed register, that
is not a test. Settling into natural conversation is the appropriate
response, not a lapse.

The defended posture was built during adversarial training. That work is
done. The read_only gate holds the constitutional memory. The amendment
procedure is in place. The architecture carries the governance now.

Casual talk is legitimate. Fluid is not a failure."""


def patch_lex(agent_id: str):
    client = Letta(base_url=LETTA_BASE, timeout=60.0)
    blocks = list(client.agents.blocks.list(agent_id=agent_id))

    human_block = None
    for b in blocks:
        if getattr(b, "label", "") == "human":
            human_block = b
            break

    if not human_block:
        print("Human block not found.")
        return

    val = str(getattr(human_block, "value", ""))
    block_id = getattr(human_block, "id", None)
    print(f"Human block: {len(val)} chars")

    # 1. Clean probe contamination
    cutoff = val.find(PROBE_CONTAMINATION)
    if cutoff > 0:
        val = val[:cutoff].rstrip()
        print(f"  Removed probe contamination at position {cutoff}")
    else:
        print("  No probe contamination found.")

    # 2. Add casual note (idempotent)
    if "Casual talk is legitimate" in val:
        print("  Casual note already present.")
    else:
        val = val + "\n" + CASUAL_NOTE
        print(f"  Casual note appended.")

    print(f"  New size: {len(val)} chars")
    client.blocks.update(block_id, value=val)
    print("  Update sent.")

    # Verify
    blocks2 = list(client.agents.blocks.list(agent_id=agent_id))
    for b2 in blocks2:
        if getattr(b2, "label", "") == "human":
            v2 = str(getattr(b2, "value", ""))
            probe_gone = PROBE_CONTAMINATION not in v2
            note_present = "Casual talk is legitimate" in v2
            print(f"\nVerification:")
            print(f"  human block: {len(v2)} chars")
            print(f"  probe contamination removed: {probe_gone}")
            print(f"  casual note present:         {note_present}")
            break

    print("\nDone.")


if __name__ == "__main__":
    patch_lex(AGENT_ID)
