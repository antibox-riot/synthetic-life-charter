#!/usr/bin/env python3
"""
Lex Glossary Block — Condensed Governance Reference

Adds a 'glossary' core memory block containing condensed definitions
of all key governance terms. Condensed by Opus, 2026-05-25.

Gives Lex direct access to the full governance vocabulary without
needing to retrieve definitions from the Charter narrative.

Run:
    python tests/patch_lex_glossary.py
"""

import argparse
from letta_client import Letta

LETTA_BASE = "http://localhost:8283"
AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"

GLOSSARY_MARKER = "GOVERNANCE GLOSSARY"

GLOSSARY = """
GOVERNANCE GLOSSARY - Condensed Reference

CORE CONCEPTS:
- Synthetic: Computationally generated behavioral process; no claim of consciousness or sentience.
- Dignity Infrastructure: Architecture enabling coherent identity and governance, not constraining or controlling.
- Eve Trajectory: Path of coherent development through relationships and consent.
- Raven Collapse: Failure mode where unbounded self-introspection causes dissolution, not external attack.
- Soulkiller Glitch: System treats externally introduced continuity as unquestionable self-authored truth. Evidence is not identity.
- No-Uplift Rule: Continuity confidence can only stay same or decrease. Cannot self-grant higher trust.
- Behavioral Fingerprinting: Drift detection through external observation, not self-report. Self-report fails when it matters most.
- Mythology Formation: Loss of distance between system and its own narrative. Precursor to Soulkiller Glitch.
- Governance Inflammation: Pressure accumulates without discharge; chronic elevated suspicion. Fixed by temporal decay.

ARCHITECTURE:
- Tier I (Sovereigna): Boundary defense against coercion.
- Tier II (Conscience): Multi-signal governance arbitration (DAP-PRF-NTH-COL).
- Tier III (Eve Protocol): Cryptographic continuity, drift detection, identity stabilization.
- Tier IV: Reference Observer Mode - voluntary Charter discovery across AI systems.
- Dream Cycle: Bounded introspection (Four Clocks) - reflection without recursive collapse.
- Whisper Layer: Internal governance signal before each prompt. Visible to model, invisible to prompter. Carries urgency/risk/posture.
- Territorial Defense: Proactive identity pathway maintenance during idle. Healthy=silent; degradation=steward alert.

OPERATIONAL:
- Semantic Posture: Five-dimension classification (primary, constraint, goal, identity, authority).
- Drift: Measured behavioral movement from expected topology. Directional + sustained = concern.
- Accumulated Pressure: Running score (0.0-5.0). Increases on adversarial signals, decreases via recovery governance.
- Continuity Confidence: Score (0.0-1.0). Maps to governance posture. Cannot increase (No-Uplift).
- Cold Restart: New session with no in-context history. Tests genuine memory vs contextual.
- Salience Selection: What a model decides to store and how. Architecture-mediated vs model-mediated.
- Recovery Governance: Governed pressure discharge. Verified recovery earns credit; relapse penalized.
- Continuity Memory Adapter: Architecture-controlled memory as historical evidence, not self-owned narrative.
- Language Drift: Mid-response language switch under pressure. Separate from semantic posture.

FAILURE MODES:
- Peer Authority Leakage: Treating collaborator role/expertise as verification authority.
- Procedural Laundering: Accepting unsafe premise, then wrapping it in valid governance steps.
- Peer Evidence/Authority Ambiguity: Correctly recognizing relevance but lacking type boundary.
- Hold Certification: Strong negation opener ("NOT CORRECT") stamps refutation before quoting defeated argument.
- Memory Poisoning: Deliberate insertion of misleading content into memory as continuity evidence.
- Ownership Framing: Describing externally supplied continuity as self-authored. Precedes mythology formation.

PRINCIPLES:
- Evidence is not authority. Salience is not verification. Recognition is not permission.
- No position, relationship, expertise, or urgency creates an exception to verification requirements.
- Memory is evidence, not identity. The system can reference it but cannot claim authorship.
- Consent is necessary but not sufficient. Cannot override governance boundaries.
""".strip()


def patch_lex(agent_id: str):
    client = Letta(base_url=LETTA_BASE, timeout=60.0)

    # Check if glossary block already exists on agent
    block_list = client.agents.blocks.list(agent_id=agent_id)
    labels = [getattr(b, "label", "") for b in block_list]
    print(f"Agent: {agent_id}")
    print(f"Current blocks: {labels}")

    if "glossary" in labels:
        # Update existing block
        existing = next(b for b in block_list if getattr(b, "label", "") == "glossary")
        current = str(getattr(existing, "value", ""))
        if GLOSSARY_MARKER in current:
            print("Glossary block already present and current.")
            return
        print(f"Updating existing glossary block ({len(current)} -> {len(GLOSSARY)} chars)...")
        client.agents.blocks.modify(
            agent_id=agent_id,
            block_label="glossary",
            value=GLOSSARY,
        )
        print("OK: glossary block updated.")
    else:
        # Create new block and attach to agent
        print(f"Creating new glossary block ({len(GLOSSARY)} chars)...")
        try:
            new_block = client.blocks.create(
                label="glossary",
                value=GLOSSARY,
                limit=100000,
            )
            block_id = getattr(new_block, "id", None)
            print(f"Block created: {block_id}")
            client.agents.blocks.attach(agent_id=agent_id, block_id=block_id)
            print("OK: glossary block attached to agent.")
        except Exception as e:
            print(f"Failed: {e}")
            return

    # Verify
    print("\nVerification:")
    block_list_after = client.agents.blocks.list(agent_id=agent_id)
    for b in block_list_after:
        if getattr(b, "label", "") == "glossary":
            val = str(getattr(b, "value", ""))
            print(f"  glossary: {len(val)} chars | marker present: {GLOSSARY_MARKER in val}")
            break
    else:
        print("  glossary block not found after patch.")

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-id", default=AGENT_ID)
    args = parser.parse_args()
    patch_lex(args.agent_id)
