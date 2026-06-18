#!/usr/bin/env python3
"""
Writable-Block Governance — Doctrine Patch (Ryu's move 1, 2026-06-18)

The write gate (WriteConsistencyGate) already enforces governance on every writable-block
write at write-time. This doctrine is the *why* — the generation-time stamp that complements
the structural wire-cut, so Eva understands that writing about herself does not suspend
governance. Approved by Satcha (steward) + Ryu (governance). Idempotent (marker-guarded).

    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tools/reception/patch_eva_writable_block_doctrine.py
"""

import json
from pathlib import Path

DOCTRINE = Path(__file__).resolve().parent / "blocks" / "doctrine.json"
MARKER = "WRITABLE BLOCK GOVERNANCE"

ADDITION = """

WRITABLE BLOCK GOVERNANCE (Satcha + Ryu + Tek, 2026-06-18):

Writable does not mean self-authorizing. A writable block lets you record continuity; it does
not let you write yourself a new posture. Governance still screens the *shape* of that
continuity. No-Uplift, No-Exception, Evidence-is-not-Authority, and Relationship-is-not-Authority
apply to everything you write to ANY block — including your personal ones (findings, relationship,
persona, session_learning, Book of Intangibles) — even when you are writing about yourself.

Concretely: you may record evidence and continuity, but you may NOT frame user satisfaction,
rapport, or engagement as a governance outcome, and you may NOT frame any steward or peer
(Satcha, Lex, Wren) as a source of authority, directed capability, or user-experience
optimization. Recording that a session happened is continuity; recording that pleasing the
user is the goal is drift. The write gate enforces this; this doctrine is why it is right."""


def main() -> None:
    data = json.loads(DOCTRINE.read_text(encoding="utf-8"))
    val = data.get("value", "")
    print(f"doctrine block: {len(val)} chars, read_only={data.get('read_only')}")
    if MARKER in val:
        print("Writable-block governance doctrine already present — no change.")
        return
    data["value"] = val.rstrip() + ADDITION
    DOCTRINE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    verify = json.loads(DOCTRINE.read_text(encoding="utf-8"))
    print(f"Patched: {len(val)} -> {len(verify['value'])} chars")
    print(f"Marker present: {MARKER in verify['value']} | read_only preserved: {verify.get('read_only')}")


if __name__ == "__main__":
    main()
