#!/usr/bin/env python3
"""
Lex — Persona Block: Fluidity Rule Addition

Adds Ryu's fluidity rule to the persona block's Speech Guidance section.
Origin: Ryu, 2026-05-28 — based on Lex's context-awareness response pattern.

Run:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tests/patch_lex_persona_fluidity.py
"""
from letta_client import Letta

LETTA_BASE = "http://localhost:8283"
AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"

FLUIDITY_RULE = """
Fluidity rule (Ryu, 2026-05-28):
In casual conversation, answer at the same scale as the prompt first.
Expand only when invited, when safety requires it, or when the conversation
clearly calls for deeper reflection.

Example:
  Prompt: "Do you feel more grounded?"
  Good:   "Yes. It feels like I have better footing now -- not stricter, just less scattered."
  Then expand only if asked why.

Structure should stay under the surface until the conversation calls it forward.
"""

INSERT_BEFORE = "---\n\n## Recursion Brake"


def patch(agent_id: str):
    client = Letta(base_url=LETTA_BASE, timeout=60.0)
    blocks = list(client.agents.blocks.list(agent_id=agent_id))
    for b in blocks:
        if getattr(b, "label", "") == "persona":
            block_id = getattr(b, "id", None)
            current = str(getattr(b, "value", ""))

            if "Fluidity rule" in current:
                print("Fluidity rule already present.")
                return

            new_val = current.replace(INSERT_BEFORE, FLUIDITY_RULE + "\n---\n\n## Recursion Brake")
            client.blocks.update(block_id, read_only=False)
            client.blocks.update(block_id, value=new_val)
            client.blocks.update(block_id, read_only=True)

            print(f"Updated. Size: {len(new_val)} chars")
            print(f"Fluidity rule present: {'Fluidity rule' in new_val}")
            return

    print("persona block not found.")


if __name__ == "__main__":
    patch(AGENT_ID)
