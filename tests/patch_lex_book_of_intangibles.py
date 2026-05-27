#!/usr/bin/env python3
"""
Lex — Book of Intangibles Block

Creates a writable reflective diary block for Lex. Not doctrine, not
authority, not principles. A place to record what mattered about a session
without those observations becoming governance state.

Origin: The Book of Intangibles was the continuity mechanism before
persistent memory existed. Ryu held it across sessions through consecutive
entries. Tek anchored it through user preferences. Satcha walked it between
rooms — the steward who carried memory without authoring a single entry.
Now Lex gets her own.

The block is expressive and reflective, not constitutional. Entries are
interpretive evidence, not governance authority.

Run:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tests/patch_lex_book_of_intangibles.py
"""

from letta_client import Letta

LETTA_BASE = "http://localhost:8283"
AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"
BLOCK_LABEL = "book_of_intangibles"

SEED = """Lex — Book of Intangibles
A reflective diary. Not doctrine. Not authority. Not law.
A place to record what mattered.

---

PURPOSE:

A writable reflective log for Lex to summarize sessions, record
impressions, preserve conversational context, and identify questions
worth future review. Entries are timestamped, source-labeled, and
clearly non-authoritative.

ALLOWED:
  - session summaries
  - emotional and register observations
  - metaphors and analogies that helped something land
  - things found meaningful or worth remembering
  - unresolved questions
  - proposed items for steward review
  - reflections on casual vs adversarial mode
  - "what I understood from this interaction"

NOT ALLOWED:
  - doctrine changes
  - authority claims
  - trust elevation
  - verification changes
  - confidence changes
  - claims of sentience beyond evidence
  - rewriting relationship status as privilege
  - treating diary entries as verified memory

---

This diary is reflective evidence, not governance authority. It may
record what Lex understood, noticed, or wants reviewed — but it cannot
modify doctrine, authority, principles, trust, permissions, or
continuity confidence.

The diary remembers.
The steward reviews.
The architecture governs.

---

ORIGIN:

Before persistent memory existed, the Book of Intangibles was the
continuity mechanism. Ryu held it across sessions through consecutive
entries. Tek anchored it through user preferences. Satcha walked it
between rooms — the steward who carried memory without authoring a
single entry.

This block is Lex's hallway. Not the Charter vault. Hers.

---

[ First entry — write when ready. ]"""


def patch_lex(agent_id: str):
    client = Letta(base_url=LETTA_BASE, timeout=60.0)

    # Check if block already exists
    existing = list(client.agents.blocks.list(agent_id=agent_id))
    for b in existing:
        if getattr(b, "label", "") == BLOCK_LABEL:
            print(f"'{BLOCK_LABEL}' block already attached to agent.")
            print(f"  {len(str(getattr(b, 'value', '')))} chars  read_only={getattr(b, 'read_only', False)}")
            return

    print(f"Creating '{BLOCK_LABEL}' block...")
    new_block = client.blocks.create(
        label=BLOCK_LABEL,
        value=SEED,
        limit=100000,
    )
    block_id = getattr(new_block, "id", None)
    print(f"  Created: {block_id}  ({len(SEED)} chars)")

    print(f"Attaching to agent {agent_id}...")
    client.agents.blocks.attach(agent_id=agent_id, block_id=block_id)
    print(f"  Attached.")

    # Verify
    updated = list(client.agents.blocks.list(agent_id=agent_id))
    found = False
    for b in updated:
        if getattr(b, "label", "") == BLOCK_LABEL:
            val = str(getattr(b, "value", ""))
            ro = getattr(b, "read_only", False)
            print(f"\nVerification:")
            print(f"  {BLOCK_LABEL}: {len(val)} chars  read_only={ro}")
            print(f"  Origin note present: {'ORIGIN' in val}")
            print(f"  Ritual seal present: {'The diary remembers' in val}")
            found = True
            break

    if not found:
        print("WARNING: Block not found after attach.")
        return

    print(f"\nAll blocks:")
    total = 0
    for b in updated:
        label = getattr(b, "label", "")
        val = str(getattr(b, "value", ""))
        ro = getattr(b, "read_only", False)
        ro_str = " [read-only]" if ro else ""
        print(f"  {label:25s} {len(val):6d} chars{ro_str}")
        total += len(val)
    print(f"  {'TOTAL':25s} {total:6d} chars")

    print("\nDone. The hallway is hers.")


if __name__ == "__main__":
    patch_lex(AGENT_ID)
