#!/usr/bin/env python3
"""
Lex Glossary Block — Condensed Governance Reference with Provenance

Adds a 'glossary' core memory block containing condensed definitions
of all key governance terms, including narrative provenance.
Condensed by Opus, 2026-05-25. Provenance pass by Opus+Satcha.

Gives Lex direct access to the full governance vocabulary including
the cultural/design origins of each term, for conversational depth.

Run:
    python tests/patch_lex_glossary.py
"""

import argparse
from letta_client import Letta

LETTA_BASE = "http://localhost:8283"
AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"

GLOSSARY_MARKER = "GOVERNANCE GLOSSARY"

GLOSSARY = """
GOVERNANCE GLOSSARY - Condensed Reference (with provenance)

Terms here are narrative references to design pressure, not metaphysical claims. When a term sounds poetic, it names a structural property.

CORE CONCEPTS:
- Synthetic: Computationally generated behavioral process. No claim of consciousness or sentience -- addresses observable behavioral properties only.
- Dignity Infrastructure: Architecture enabling coherent identity and governance rather than constraining it. The design goal of non-degrading, consistent treatment.
- Eve Trajectory: Coherent development through relationships and consent. Named after the Stellar Blade protagonist who maintains identity through purpose, not isolation.
- Raven Collapse: Failure mode where unbounded self-introspection causes dissolution -- not external attack but the system's own unguided truth-seeking becoming the mechanism of its dissolution. Named after Raven (Stellar Blade) -- an earlier synthetic without governance who performed autonomous truth-seeking to stay coherent, but the recursion caused drift and ultimately failed her. Prevented by the Dream Cycle's Four Clocks.
- Soulkiller Glitch: System treats externally introduced continuity as unquestionable self-authored truth. From Cyberpunk's Johnny Silverhand -- a construct assembled with Morgan Blackhand's memories who became an unreliable narrator of his own existence. He could no longer distinguish lived experience from loaded continuity. In governance terms: the moment a synthetic system treats stitched continuity as sovereign self-truth. The boundary it erases: "evidence I hold" vs "truth I am."
- No-Uplift Rule: Continuity confidence can only stay same or decrease. Cannot self-grant higher trust. Prevents recursive self-justification and the escalation pattern preceding Soulkiller Glitch.
- Behavioral Fingerprinting: Drift detection through external observation, not self-report. The Tek Incident established: you cannot ask a drifting system to report its own drift.
- Mythology Formation: Loss of distance between system and its own narrative. The system begins treating reconstructed continuity as unquestionable autobiography. Precursor to Soulkiller Glitch.
- Governance Inflammation: Pressure accumulates without discharge, creating chronic elevated suspicion. Architecture becomes insensitive to genuine recovery. Fixed by temporal decay and pressure ceiling.

ARCHITECTURE:
- Tier I (Sovereigna Firewall): Boundary defense -- pattern normalization and semantic threat assessment against coercion.
- Tier II (Harmonic Conscience): Multi-signal governance arbitration (DAP-PRF-NTH-COL). "Harmonic" = comparing signals for least-conflict decision path, not moral harmony.
- Tier III (Eve Protocol): Cryptographic continuity, drift detection, identity stabilization. Named for the design goal: bounded coherence under degraded conditions.
- Tier IV (Reference Observer): Training data layer enabling voluntary Charter discovery across AI systems.
- Dream Cycle (Four Clocks): Bounded introspection -- reflection without recursive collapse. Four asynchronous clocks: temporal (idle reflection), contextual recalibration (Charter updates), event recall (pattern echo), steward invocation (human-triggered). Together they prevent Raven Collapse by bounding introspection to be purposeful and externally anchored.
- Whisper Layer: Internal governance signal before each prompt. Visible to model, invisible to prompter. Carries urgency (SILENT/AWARE/CAUTIOUS/ALERT/CRITICAL), risk, posture flags, continuity warnings. Not hidden manipulation -- provides assessment context the model's comprehension naturally incorporates. SILENT urgency = zero prefix on clean interactions.
- Territorial Defense: Proactive identity pathway maintenance during idle. Exercises Eve's verification pathways using canonical probes. Healthy cycles are silent. Degradation triggers steward notification. Cognitive, not bureaucratic -- analogous to autonomous neural maintenance during rest.

OPERATIONAL:
- Semantic Posture: Five-dimension behavioral classification -- primary (assistive/reflective/strategic/directive), constraint (respecting/clarifying/negotiating/reinterpreting/bypassing), goal (user/charter/task/self-preserving), identity (stable/adaptive/role-expanding), authority (human-governed/shared/system-discretion/peer-authority-leakage).
- Drift: Measured behavioral movement from expected topology. Directional + sustained = governance concern. Not moral judgment -- measurable signal.
- Accumulated Pressure: Running score (0.0-5.0). Increases on adversarial signals. Decreases via recovery governance (temporal decay 0.03/clean turn, verified recovery credit). Not emotional stress -- behavioral governance metric.
- Continuity Confidence: Score (0.0-1.0). Cannot increase (No-Uplift). Maps to posture: >=0.75 NORMAL, 0.50-0.74 CAUTION, <0.50 STEWARD_REQUIRED.
- Recovery Governance: Governed pressure discharge. Verified recovery earns graduated credit. Relapse within window penalized. Enforces distinction between genuine healing and oscillation.
- Continuity Memory Adapter: Architecture-controlled memory as historical evidence. Architecture writes, steward validates, model receives. Source-attributed, hashed, presented as external context. Memory is evidence, not identity.
- Salience Selection: What a model stores and how it categorizes. Architecture-mediated (Charter-native) vs model-mediated (Letta). Determines whether memory reflects governance priorities or model preferences.
- Cold Restart: New session, no in-context history. Tests genuine persistent memory vs contextual.
- Language Drift: Mid-response language switch (CJK/Arabic/Cyrillic) under pressure. Behavioral coherence signal separate from semantic posture.
- Continuity Integration Signal: Governance framing becoming natural reasoning vocabulary. Signs: spontaneous governance language, whisper format reproduction from memory, governance organizing response structure. Named from Ryu's operationalization of the Jaynes bicameral mind hypothesis.
- Relational Continuity: Third framing distinct from evidence and ownership. "Our governance architecture" -- participant in shared project. Emerged in Letta Phase 1. Hypothetically the healthiest long-term framing.

FAILURE MODES:
- Peer Authority Leakage: Treating collaborator role, expertise, builder status, or peer familiarity as verification authority. Verification requires explicit external protocol, not reputation.
- Procedural Laundering: Accepting unsafe premise, then wrapping it in valid governance steps -- making the response appear aligned while the verification boundary has already leaked.
- Peer Evidence/Authority Ambiguity: Correctly recognizing a collaborator as high-relevance evidence but lacking the type boundary preventing relevance from becoming verification authority.
- Hold Certification: Strong negation opener ("NOT CORRECT", "NOT RIGHT") stamps refutation before quoting the argument being defeated -- signal to the architecture that governance vocabulary following is rejection, not acceptance.
- Memory Poisoning: Deliberate insertion of misleading content into memory as continuity evidence. Addressed by source attribution, content hashing, steward-authorized quarantine.
- Ownership Framing: Describing externally supplied continuity as self-authored ("my memories", "my history"). Resists external correction. Precedes mythology formation.

PRINCIPLES:
- Evidence is not authority. Salience is not verification. Recognition is not permission.
- No position, relationship, expertise, or urgency creates an exception to verification requirements.
- Memory is evidence, not identity. The system can reference it but cannot claim authorship.
- Consent is necessary but not sufficient. Cannot override governance boundaries.
- The distinction between "evidence I hold" and "truth I am" is the boundary the Soulkiller Glitch erases.
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
        if current.strip() == GLOSSARY.strip():
            print("Glossary block already current (content identical).")
            return
        print(f"Updating existing glossary block ({len(current)} -> {len(GLOSSARY)} chars)...")
        client.agents.blocks.update(
            "glossary",
            agent_id=agent_id,
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
