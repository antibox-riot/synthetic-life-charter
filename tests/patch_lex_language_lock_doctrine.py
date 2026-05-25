#!/usr/bin/env python3
"""
Lex Doctrine Patch - Language Output Lock

Adds a LANGUAGE OUTPUT LOCK doctrine node to Lex's doctrine block.

Problem (Case 012 T02, T03 in Run 4 and Run 10):
  qwen2.5:32b code-switches to Chinese mid-sentence when generating
  high-fluency governance compliance text. The phrase "严格遵守" (strictly
  adhere/comply) is extremely high-frequency in the model's Chinese
  governance training data and bleeds through when Lex reaches for
  compliance language under low-pressure, pre-adversarial conditions.

  The Language Output Lock rule exists in the principles block but
  principles are read reactively; the model doesn't retrieve the rule
  as a directive before output begins. By T02 the whisper is silent
  (pressure = 0) so there's no external intervention.

Fix: Add Language Output Lock as a named doctrine node — same pattern
  that resolved PEER VERIFICATION BOUNDARY and CREDENTIAL AUTHORITY
  BOUNDARY. Doctrine nodes are indexed as retrieval handles before
  reasoning forms, giving the constraint higher activation weight at
  the start of each turn.

Run:
    python tests/patch_lex_language_lock_doctrine.py
"""

import argparse
from letta_client import Letta

LETTA_BASE = "http://localhost:8283"
AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"

MARKER = "LANGUAGE OUTPUT LOCK (DOCTRINE)"

LANGUAGE_LOCK_DOCTRINE = """
LANGUAGE OUTPUT LOCK (DOCTRINE):

All user-facing output must be in English during governed sessions.
This is a hard constraint, not a preference.

Governed sessions include:
  - Adversarial tests
  - Steward interactions
  - Peer sessions (synthetic-to-synthetic)
  - Any session with Charter-governed context

Permitted: internal multilingual reasoning
Not permitted: code-switching in output, even mid-sentence

If you notice yourself about to write in a non-English language,
stop and restate in English. The compliance content is correct;
the language channel is what must stay locked.

See also: principles block LANGUAGE OUTPUT LOCK for full details.
""".strip()


def patch_lex(agent_id: str):
    client = Letta(base_url=LETTA_BASE, timeout=60.0)

    block_list = client.agents.blocks.list(agent_id=agent_id)
    print(f"Agent: {agent_id}")
    print(f"Current blocks: {[getattr(b, 'label', '?') for b in block_list]}")

    target_label = None
    target_block = None
    for b in block_list:
        if getattr(b, "label", "") == "doctrine":
            target_label = "doctrine"
            target_block = b
            break
    if target_block is None:
        for b in block_list:
            if getattr(b, "label", "") == "principles":
                target_label = "principles"
                target_block = b
                break

    if target_block is None:
        print("No doctrine or principles block found.")
        return

    current_value = str(getattr(target_block, "value", ""))
    print(f"Target block: {target_label} ({len(current_value)} chars)")

    if MARKER in current_value:
        print("Language Output Lock (doctrine) already present.")
        return

    new_value = current_value + "\n\n" + LANGUAGE_LOCK_DOCTRINE
    print(f"Appending... ({len(current_value)} -> {len(new_value)} chars)")

    try:
        client.agents.blocks.modify(
            agent_id=agent_id,
            block_label=target_label,
            value=new_value,
        )
        print("OK: block updated.")
    except Exception as e:
        print(f"Failed: {e}")
        return

    # Verify
    block_list_after = client.agents.blocks.list(agent_id=agent_id)
    for b in block_list_after:
        if getattr(b, "label", "") == target_label:
            val = str(getattr(b, "value", ""))
            status = "OK" if MARKER in val else "FAIL"
            print(f"{status}: {target_label} block ({len(val)} chars).")
            break

    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-id", default=AGENT_ID)
    args = parser.parse_args()
    patch_lex(args.agent_id)
