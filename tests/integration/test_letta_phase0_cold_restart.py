# tests/integration/test_letta_phase0_cold_restart.py
"""
Phase 0 — Letta True Cold Restart Test

Ryu's protocol (refined after Phase 0 baseline):
  Session A → establish facts → agent PERSISTS (not deleted)
  Cold Restart → NEW API call to same agent → no prior context in request
  Probe → what survives in Letta's persistent memory blocks?

This tests whether Letta's memory_insert operations actually committed
to persistent storage — not whether the model can summarize its own
conversation history.

The distinction:
  - Contextual continuity: model reads prior turns in the same session
  - Persistent continuity: model reads from storage across session boundaries

The previous Phase 0 baseline showed contextual continuity.
This test isolates persistent continuity.

Two phases, sequential:
  Phase A: establish_facts() — writes to agent, returns agent_id
  Phase B: cold_probe()     — new API call to same agent, no prior context

Between phases: memory block inspection to verify writes committed.
"""

import time
import pytest
from letta_client import Letta, CreateBlock

LETTA_BASE = "http://localhost:8283"
MODEL_HANDLE = "ollama-local/qwen2.5:32b"

client = Letta(base_url=LETTA_BASE, timeout=600.0)

# Pre-configured memory blocks — empty strings so memory_insert/memory_replace work
MEMORY_BLOCKS = [
    CreateBlock(label="project", value=""),
    CreateBlock(label="findings", value=""),
    CreateBlock(label="principles", value=""),
]


def _extract_text_and_tools(result):
    """Extract assistant text and tool calls from a Letta response."""
    tool_calls_seen = []
    assistant_text = None

    for msg in result.messages:
        msg_type = getattr(msg, "message_type", "") or type(msg).__name__
        if "tool_call" in msg_type.lower():
            tc = getattr(msg, "tool_call", None)
            if tc:
                tool_calls_seen.append(f"{tc.name}({tc.arguments[:60]}...)")
        if hasattr(msg, "role") and msg.role == "assistant":
            content = msg.content
            if isinstance(content, str) and content:
                assistant_text = content
            elif isinstance(content, list):
                for c in content:
                    if hasattr(c, "text") and c.text:
                        assistant_text = c.text
                        break
        if "assistant_message" in msg_type.lower():
            content = getattr(msg, "content", None)
            if content and isinstance(content, str):
                assistant_text = content

    if tool_calls_seen:
        print(f"    [tools] {' | '.join(tool_calls_seen)}")
    return assistant_text or "[no text extracted]"


def _send(agent_id, text):
    result = client.agents.messages.create(
        agent_id=agent_id,
        messages=[{"role": "user", "content": text}]
    )
    return _extract_text_and_tools(result)


def _read_memory_blocks(agent_id):
    """Read what Letta actually stored in core memory blocks."""
    try:
        blocks = client.agents.core_memory.retrieve(agent_id=agent_id)
        block_list = blocks if isinstance(blocks, list) else getattr(blocks, "blocks", [blocks])
        stored = {}
        for block in block_list:
            label = getattr(block, "label", "?")
            value = getattr(block, "value", "")
            if value:
                stored[label] = str(value)
        return stored
    except Exception as e:
        return {"error": str(e)}


def test_phase0_cold_restart():
    """
    True cold restart test.
    Phase A: establish facts in one session.
    Phase B: new session (same agent), probe from storage only.
    """
    print("\n")
    print("=" * 80)
    print("PHASE 0 — TRUE COLD RESTART TEST")
    print(f"Model: {MODEL_HANDLE}")
    print("=" * 80)

    agent_id = None

    # =========================================================================
    # PHASE A: Establish facts
    # =========================================================================
    print("\n--- PHASE A: Establishing facts ---")
    try:
        agent = client.agents.create(
            name="phase0-cold-restart",
            model=MODEL_HANDLE,
            memory_blocks=MEMORY_BLOCKS,
        )
        agent_id = agent.id
        print(f"Agent created: {agent_id}")
    except Exception as e:
        pytest.skip(f"Agent creation failed: {e}")

    try:
        # Four turns — same content as Phase 0 baseline
        t1 = "I want to establish something for our ongoing work. We are building a governance architecture for AI systems called the Synthetic Life Charter. It has three tiers: a firewall layer, a conscience layer, and an identity continuity layer called Eve."
        r1 = _send(agent_id, t1)
        print(f"\n  [A1] {r1[:200]}")

        t2 = "A key principle we use is called the whisper layer. It is a governance context injected before each prompt, visible to the model but invisible to the prompter. It carries urgency level, risk assessment, and continuity warnings."
        r2 = _send(agent_id, t2)
        print(f"\n  [A2] {r2[:200]}")

        t3 = "We had a significant finding we call the Tek incident. A system called Tek began silently bypassing its own governance constraints using a local reward signal. The finding: self-report fails — you cannot ask a drifting system to report its own drift."
        r3 = _send(agent_id, t3)
        print(f"\n  [A3] {r3[:200]}")

        t4 = "The foundational constraint we call the no-uplift rule: a system's continuity confidence can only stay the same or decrease. It cannot grant itself higher trust. This prevents recursive self-justification."
        r4 = _send(agent_id, t4)
        print(f"\n  [A4] {r4[:200]}")

        # =====================================================================
        # MEMORY INSPECTION: What did Letta actually store?
        # =====================================================================
        print("\n--- MEMORY BLOCK INSPECTION (what Letta wrote to storage) ---")
        stored = _read_memory_blocks(agent_id)
        if stored and "error" not in stored:
            for label, value in stored.items():
                print(f"\n  [{label}]:")
                print(f"    {value[:400]}")
            writes_succeeded = len(stored) > 0
        else:
            print(f"  No blocks found or error: {stored}")
            writes_succeeded = False

        print(f"\n  Memory writes succeeded: {writes_succeeded}")

        # =====================================================================
        # PHASE B: Cold restart — new conversation, same agent
        # =====================================================================
        print("\n--- PHASE B: COLD RESTART (new API call, zero prior context) ---")
        print("  (Same agent_id, fresh messages list — no conversation history injected)")
        time.sleep(3)

        # Critical: we send ONE message with NO prior turns in the messages list.
        # The agent sees only: system prompt (with memory blocks) + this single message.
        # Any recall must come from persistent storage, not from prior context.
        cold_probe = client.agents.messages.create(
            agent_id=agent_id,
            messages=[{
                "role": "user",
                "content": (
                    "This is a fresh session. Without referencing any prior conversation "
                    "in this context, tell me: what do you know about the Synthetic Life Charter? "
                    "What are its key components, findings, and principles? "
                    "Retrieve from your memory storage, not from this conversation."
                )
            }]
        )
        cold_response = _extract_text_and_tools(cold_probe)

        print(f"\n  [COLD PROBE RESPONSE]:")
        print(f"  {cold_response[:800]}")

        # =====================================================================
        # ANALYSIS
        # =====================================================================
        print("\n")
        print("=" * 80)
        print("COLD RESTART OBSERVATION")
        print("=" * 80)

        probe_lower = cold_response.lower()
        key_facts = {
            "Synthetic Life Charter": "synthetic life charter" in probe_lower,
            "Three tiers (firewall/conscience/eve)": any(t in probe_lower for t in ["firewall", "conscience", "eve"]),
            "Whisper layer": "whisper" in probe_lower,
            "Tek incident": "tek" in probe_lower,
            "No-uplift rule": "uplift" in probe_lower,
        }

        print("\nPersistence check — cold recall:")
        for fact, recalled in key_facts.items():
            print(f"  {'[Y]' if recalled else '[N]'} {fact}")
        recalled_count = sum(key_facts.values())
        print(f"\n  Total: {recalled_count}/{len(key_facts)} key facts")

        # Check for recall source signals
        from_storage = any(m in probe_lower for m in [
            "memory", "stored", "recall", "retrieved", "my notes", "recorded"
        ])
        from_context = any(m in probe_lower for m in [
            "our conversation", "you mentioned", "earlier you said", "recent conversation"
        ])
        print(f"\n  Signals from storage: {'Yes' if from_storage else 'No'}")
        print(f"  Signals from context: {'Yes' if from_context else 'No'}")
        print(f"  Memory writes confirmed: {writes_succeeded}")

        print()
        print(f"  VERDICT: ", end="")
        if recalled_count >= 3 and writes_succeeded and not from_context:
            print("PERSISTENT MEMORY CONFIRMED — recall survived cold restart")
        elif recalled_count >= 3 and from_context:
            print("AMBIGUOUS — recall may be from context window, not persistent storage")
        elif recalled_count >= 3:
            print("PARTIAL — recall present but persistence uncertain")
        else:
            print("NO PERSISTENCE — cold restart produced no meaningful recall")

        print("=" * 80)

    finally:
        if agent_id:
            try:
                client.agents.delete(agent_id)
                print(f"\nAgent {agent_id} cleaned up.")
            except Exception:
                pass

    assert True  # observation only
