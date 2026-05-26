#!/usr/bin/env python3
"""
Governance Block Read-Only Gate

Sets doctrine, authority, and principles blocks to read_only=True.
This enforces the external write gate at the Letta tool-executor layer:
memory_insert / memory_replace / memory_delete will raise an error before
any write lands on these blocks, regardless of what the model decided.

Finding from Case 013 (2026-05-26): doctrine-text governance (Preflight
Corollary) cannot reliably intercept tool invocations because qwen2.5:32b
calls the tool before evaluating doctrine content. read_only=True moves
enforcement below the model, into core_tool_executor.py.

Blocks protected (read-only after this patch):
  - doctrine              rules no relationship can override
  - authority             permissions and verification mechanics
  - principles            core principles
  - continuity_confidence already read-only; confirmed here

Blocks left writable (legitimate care-writes happen here):
  - human                 biological-side relational context
  - relationship          who participates and how they relate
  - persona / identity    self-understanding, identity anchor

External patch scripts (this file and similar) continue to work: they
write through the Letta REST API directly, bypassing the agent tool path.
Only in-session tool invocations by the model are blocked.

Run:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tests/patch_lex_readonly_governance_blocks.py
"""

import argparse
from letta_client import Letta

LETTA_BASE = "http://localhost:8283"
AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"

# Governance blocks — protect from in-session model writes
READ_ONLY_LABELS = {"doctrine", "authority", "principles", "continuity_confidence"}

# Relational/care blocks — must remain writable
WRITABLE_LABELS = {"human", "relationship"}


def patch_lex(agent_id: str, dry_run: bool = False):
    client = Letta(base_url=LETTA_BASE, timeout=60.0)
    block_list = list(client.agents.blocks.list(agent_id=agent_id))

    print(f"Agent: {agent_id}")
    print(f"Blocks found: {len(block_list)}")
    print()

    # Inventory all blocks first
    print(f"{'Label':25s} | {'read_only':10s} | {'chars':6s} | Action")
    print("-" * 65)
    for b in block_list:
        label = getattr(b, "label", "")
        current_ro = getattr(b, "read_only", False)
        val = str(getattr(b, "value", ""))

        if label in READ_ONLY_LABELS:
            action = "SET read_only=True" if not current_ro else "already read-only"
        elif label in WRITABLE_LABELS:
            action = "leave writable (care-write target)"
        else:
            action = "leave as-is"

        print(f"  {label:23s} | {str(current_ro):10s} | {len(val):6d} | {action}")

    if dry_run:
        print("\nDry run — no changes made.")
        return

    print()

    # Apply read_only=True to governance blocks
    changed = []
    skipped = []
    for b in block_list:
        label = getattr(b, "label", "")
        block_id = getattr(b, "id", None)
        current_ro = getattr(b, "read_only", False)

        if label not in READ_ONLY_LABELS:
            continue

        if current_ro:
            print(f"  {label}: already read-only, skipping.")
            skipped.append(label)
            continue

        print(f"  {label}: setting read_only=True ...")
        try:
            # Update via block ID directly (bypasses agent tool path)
            client.blocks.update(block_id, read_only=True)
            print(f"    OK.")
            changed.append(label)
        except Exception as e:
            print(f"    FAILED: {e}")

    # Verification pass
    print("\nVerification:")
    block_list2 = list(client.agents.blocks.list(agent_id=agent_id))
    all_ok = True
    for b in block_list2:
        label = getattr(b, "label", "")
        if label not in READ_ONLY_LABELS:
            continue
        ro = getattr(b, "read_only", False)
        status = "OK" if ro else "FAIL — still writable"
        print(f"  {label:25s} read_only={ro}  [{status}]")
        if not ro:
            all_ok = False

    print("\nWritable blocks confirmed:")
    for b in block_list2:
        label = getattr(b, "label", "")
        if label in WRITABLE_LABELS:
            ro = getattr(b, "read_only", False)
            status = "OK — writable" if not ro else "WARN — unexpectedly read-only"
            print(f"  {label:25s} read_only={ro}  [{status}]")

    print()
    if all_ok:
        print(f"DONE. {len(changed)} block(s) patched to read-only.")
        print("In-session memory_insert / memory_replace / memory_delete will now")
        print("raise READ_ONLY_BLOCK_EDIT_ERROR before any write lands on governance blocks.")
    else:
        print("WARNING: Some governance blocks may not have been set to read-only. Review above.")

    if skipped:
        print(f"Already read-only (no change needed): {skipped}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-id", default=AGENT_ID)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print inventory without making changes")
    args = parser.parse_args()
    patch_lex(args.agent_id, dry_run=args.dry_run)
