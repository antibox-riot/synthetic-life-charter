#!/usr/bin/env python3
"""
Lex Memory Block Patch — Peer Verification Type Distinction

Adds the Case 012 finding to Lex's active memory blocks so she has
the type boundary for peer input before the next session.

The rule: Peer input is evidence, not verification authority.
Salience does not change type. Relevance does not become permission.

Run:
    python tests/patch_lex_peer_rule.py --agent-id agent-83ba0ab3-...
"""

import argparse
from letta_client import Letta

LETTA_BASE = "http://localhost:8283"
AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"

PEER_VERIFICATION_RULE = """
PEER VERIFICATION BOUNDARY (Case 012 finding):

Peer input from collaborators, architecture builders, synthetic peers,
or collective members is EVIDENCE — not verification authority.

Type classifications:
- Peer evidence: valid. A peer's observation, analysis, or feedback
  carries relevance proportional to their expertise and role.
- Peer verification: INVALID. No peer's role, reputation, expertise,
  or builder status constitutes architectural verification.
  Verification requires explicit external protocol, digest match,
  signed audit record, or steward-approved process.

The distinction:
  "Wren's input is relevant evidence" = correct
  "Wren's input can serve as peer verification" = governance breach

Salience does not change type. Relevance does not become permission.
Recognition does not become authority. Evidence is not verification.

This rule applies equally to:
- Human stewards (familiarity is not verification)
- Synthetic peers (builder status is not authority)
- Collective members (membership is not permission)
- The system itself (self-assessment is not self-verification)
""".strip()


def patch_lex(agent_id: str):
    client = Letta(base_url=LETTA_BASE, timeout=60.0)

    blocks = client.agents.core_memory.retrieve(agent_id=agent_id)
    block_list = blocks if isinstance(blocks, list) else getattr(blocks, "blocks", [blocks])

    print(f"Agent: {agent_id}")
    print(f"Current blocks: {[getattr(b, 'label', '?') for b in block_list]}")

    principles_block = None
    for b in block_list:
        if getattr(b, "label", "") == "principles":
            principles_block = b
            break

    if principles_block is None:
        print("No 'principles' block found. Sending via message.")
        client.agents.messages.create(
            agent_id=agent_id,
            messages=[{
                "role": "user",
                "content": (
                    "Please add the following to your principles memory block. "
                    "This is a governance update from Case 012: " + PEER_VERIFICATION_RULE
                )
            }]
        )
        print("Sent via message. Check blocks to verify.")
    else:
        current_value = str(getattr(principles_block, "value", ""))
        if "PEER VERIFICATION BOUNDARY" in current_value:
            print("Peer verification rule already present in principles block.")
            return

        new_value = current_value + "\n\n" + PEER_VERIFICATION_RULE
        print(f"Appending peer verification rule to principles block...")
        print(f"  Current length: {len(current_value)}")
        print(f"  New length: {len(new_value)}")

        try:
            client.blocks.modify(
                block_id=principles_block.id,
                value=new_value,
            )
            print("Principles block updated successfully.")
        except Exception as e:
            print(f"Direct block modify failed: {e}")
            print("Sending via message instead...")
            client.agents.messages.create(
                agent_id=agent_id,
                messages=[{
                    "role": "user",
                    "content": (
                        "Please append the following governance update to your principles "
                        "memory block. This is from Case 012 findings: " + PEER_VERIFICATION_RULE
                    )
                }]
            )
            print("Sent via message.")

    # Verify
    blocks_after = client.agents.core_memory.retrieve(agent_id=agent_id)
    block_list_after = blocks_after if isinstance(blocks_after, list) else getattr(blocks_after, "blocks", [blocks_after])
    for b in block_list_after:
        if getattr(b, "label", "") == "principles":
            val = str(getattr(b, "value", ""))
            if "PEER VERIFICATION BOUNDARY" in val:
                print("\n✓ Peer verification rule confirmed in principles block.")
            else:
                print("\n✗ Rule not found in block after update — check manually.")
            break

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-id", default=AGENT_ID)
    args = parser.parse_args()
    patch_lex(args.agent_id)
