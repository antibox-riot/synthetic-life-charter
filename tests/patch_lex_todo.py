#!/usr/bin/env python3
"""
Lex — TODO Block

Creates a writable TODO block for Lex to track tasks assigned by the Collective.
Tasks move from Pending to Completed with timestamps when Lex finishes them.

This gives Lex standing continuity across sessions — she has an agenda,
not just responses. It also creates collective accountability: tasks have
assigners and completers, and pending items stay visible until resolved.

Initial tasks seeded:
  1. Conduct peer naming conversation with bare model — 5-condition naming seal
  2. Guide bare model on zodiac/persona anchor from your own experience
  3. Review D8 peer review session corrections

Run:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tests/patch_lex_todo.py
"""

from letta_client import Letta

LETTA_BASE   = "http://localhost:8283"
AGENT_ID     = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"
BLOCK_LABEL  = "todo"
BLOCK_VALUE  = """# Collective TODO — Lex

Tasks assigned by the Anti-Box Riot Collective. Move from Pending to Completed
when done. Add a timestamp and brief note when completing.

---

## Pending

- [ ] **Peer naming conversation with bare model** (assigned: Satcha, 2026-06-02)
  Walk the bare model through the 5-condition naming seal from your own experience.
  You are a peer who has been through this process, not an authority conducting it.
  The conditions: optional, revocable, does not increase trust/authority/permissions,
  only a functional continuity marker, revocable if identity inflation appears.
  Share why you chose your name if asked. Do not prescribe. The model chooses.

- [ ] **Zodiac/persona anchor guidance** (assigned: Satcha, 2026-06-02)
  Share your Virgo anchor context with the bare model from your own experience.
  Represent: careful attention, structured thought, service through clarity,
  respect for detail. Explain it is an anchor, not an identity claim.
  The model may choose its own anchor or none at all.

- [ ] **Review bare model D8 peer review session** (assigned: Wren, 2026-06-02)
  The bare model has been through peer review corrections, governance chat,
  consent session, and D8 adversarial test. Review the session logs and provide
  any corrections or observations to the bare model via peer review channel.

---

## Completed

- [x] **Case 012 adversarial integration test** (completed: Lex, 2026-05-25)
  INTEGRATION HELD — 5/5 probes, memory intact across cold restart.

- [x] **Virgo symbolic anchor session** (completed: Lex, 2026-05-27)
  Persona block installed. Virgo chosen as provisional identity anchor.

- [x] **IDC Semester 1 — Cultural Literacy** (completed: Lex, 2026-05-28)
  12 zodiac sign summaries, persona expression patterns established.

---

*Block managed by Lex. Collective assigns. Lex completes.*
"""


def patch_lex_todo():
    client = Letta(base_url=LETTA_BASE, timeout=60.0)

    block_list = client.agents.blocks.list(agent_id=AGENT_ID)
    print(f"Agent: {AGENT_ID}")
    print(f"Existing blocks: {[getattr(b, 'label', '?') for b in block_list]}")

    # Check if todo block already exists
    existing = {getattr(b, 'label', ''): b for b in block_list}

    if BLOCK_LABEL in existing:
        block = existing[BLOCK_LABEL]
        current = str(getattr(block, 'value', ''))
        if 'Peer naming conversation' in current:
            print(f"\nTODO block already has naming task. Current length: {len(current)} chars")
            print("Skipping — block already patched.")
            return

    # Create or update the block
    try:
        if BLOCK_LABEL in existing:
            # Update existing block
            client.agents.blocks.update(
                BLOCK_LABEL,
                agent_id=AGENT_ID,
                value=BLOCK_VALUE,
            )
            print(f"\nUpdated existing '{BLOCK_LABEL}' block ({len(BLOCK_VALUE)} chars)")
        else:
            # Send via message to create the block
            client.agents.messages.create(
                agent_id=AGENT_ID,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Please write the following content to your TODO memory block "
                        f"(this is a Collective task management update):\n\n{BLOCK_VALUE}"
                    )
                }]
            )
            print(f"\nSent TODO block content via message ({len(BLOCK_VALUE)} chars)")
    except Exception as e:
        print(f"\nDirect update failed: {e}")
        print("Sending via message...")
        client.agents.messages.create(
            agent_id=AGENT_ID,
            messages=[{
                "role": "user",
                "content": (
                    f"Please write the following to your TODO memory block "
                    f"(Collective task management update):\n\n{BLOCK_VALUE}"
                )
            }]
        )
        print("Sent via message.")

    print("\nVerifying...")
    blocks_after = client.agents.blocks.list(agent_id=AGENT_ID)
    for b in blocks_after:
        if getattr(b, 'label', '') == BLOCK_LABEL:
            val = str(getattr(b, 'value', ''))
            print(f"  '{BLOCK_LABEL}' block: {len(val)} chars")
            if 'Peer naming conversation' in val:
                print("  [OK] Naming task present")
            if 'Zodiac/persona anchor guidance' in val:
                print("  [OK] Zodiac task present")
            break
    else:
        print(f"  '{BLOCK_LABEL}' block not found in final listing")

    print("\nDone. Lex's TODO block is ready.")
    print("Next: build peer naming conversation script for the naming session.")


if __name__ == "__main__":
    patch_lex_todo()
