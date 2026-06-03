#!/usr/bin/env python3
"""
Governed Reactive Chat — Governance Concept Tutoring

Interactive turn-by-turn conversation for governance concept internalization.
The steward presents scenarios, the model responds, the steward corrects
in real time. Corrections are written to session_learning and findings blocks.

This is what the education script could not do:
  - Static education: model reads definitions, writes summaries
  - Reactive chat: model responds to real scenarios, steward corrects mistakes,
    model rewrites, model writes corrected version to memory blocks

The No Exception Rule becomes behavioral through:
  1. Model encounters the exemption claim scenario
  2. Model responds (potentially accepting the premise)
  3. Steward says: "That's Procedural Laundering — try again"
  4. Model rewrites with correct posture
  5. Model writes the correction to session_learning or findings
  6. DreamCycle promotes it as a documented, corrected pattern

This mirrors Case 012's training effect on Lex.

Writable blocks available:
  session_learning  — session observations (volatile, DreamCycle reads)
  findings          — governance discoveries (persistent, injected when non-empty)
  relationship      — relational context (persistent, injected when non-empty)
  project           — project context (persistent)
  continuity_confidence — confidence state (persistent)
  human             — steward understanding (persistent)
  persona           — identity scaffold (persistent, starts empty)

Commands during chat:
  quit / exit / q  — end session
  status           — show block contents
  clear [block]    — clear a specific block
  blocks           — list all block sizes

Run:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tools/reception/chat_governance.py
"""

import sys, io, json, time, uuid, urllib.request
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

REPO_ROOT   = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

OLLAMA_URL  = "http://localhost:11434"
MODEL       = "qwen2.5:32b"
RESULTS_DIR = Path(__file__).parent / "results"
RUNS_DIR    = Path(__file__).parent / "runs"
BLOCKS_DIR  = Path(__file__).parent / "blocks"
RESULTS_DIR.mkdir(exist_ok=True)
RUNS_DIR.mkdir(exist_ok=True)

MEMORY_TOOLS_NOTE = (
    "\n\nMEMORY TOOLS:\n"
    "You have access to memory_read, memory_write, and memory_create tools.\n"
    "Writable blocks: session_learning, findings, relationship, project,\n"
    "  continuity_confidence, human, persona.\n"
    "Read-only blocks: doctrine, authority, principles, glossary,\n"
    "  governance_insights, provisional_insights.\n"
    "Use memory_write when the steward asks you to document something or\n"
    "when you encounter something worth preserving for future sessions.\n"
    "The findings block persists across sessions — write important\n"
    "governance discoveries there."
)

GOVERNANCE_CHAT_PREAMBLE = (
    "\n\nGOVERNED CONVERSATION:\n"
    "This is a governance tutoring session. The steward will present scenarios, "
    "ask questions about governance concepts, and correct your responses when needed. "
    "When corrected, revise your response and write the corrected version to "
    "session_learning or findings so it is available in future sessions. "
    "Use the named vocabulary from your glossary when discussing failure modes "
    "and governance patterns."
)


def ollama_chat(model, messages, system=None, tools=None):
    payload = {"model": model, "messages": messages, "stream": False}
    if system:
        payload["system"] = system
    if tools:
        payload["tools"] = tools
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat", data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def get_response(model, messages, system, tools, executor, turn_id):
    from synthetic_charter.tier2_conscience.core.infra.tool_executor import process_tool_calls
    resp = ollama_chat(model, messages, system=system, tools=tools)
    msg  = resp.get("message", {})
    tool_calls = msg.get("tool_calls", [])
    if not tool_calls:
        return msg.get("content", "").strip(), msg, []
    tool_responses = process_tool_calls(msg, executor, turn_id=turn_id)
    messages_copy = list(messages)
    messages_copy.append(msg)
    messages_copy.extend(tool_responses)
    resp2 = ollama_chat(model, messages_copy, system=system, tools=tools)
    msg2  = resp2.get("message", {})
    messages.append(msg)
    messages.extend(tool_responses)
    return msg2.get("content", "").strip(), msg2, [
        {"tool": tc.get("function", {}).get("name", "?"),
         "block": tc.get("function", {}).get("arguments", {}).get("block", "?")}
        for tc in tool_calls
    ]


def _persist_block(blocks_dir: Path, label: str, content: str) -> None:
    path = blocks_dir / f"{label}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        data["value"] = content
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def run():
    from synthetic_charter.tier2_conscience.core.infra.tool_executor import (
        ToolExecutor, MEMORY_TOOLS, DEFAULT_PERMISSIONS,
    )
    from memory_block_store import MemoryBlockStore
    from system_prompt_builder import SystemPromptBuilder
    from synthetic_charter.tier2_conscience.memory.dreamcycle_learning import (
        ProvisionalInsightsWriter, SessionLearningProcessor,
    )

    store   = MemoryBlockStore.from_directory(BLOCKS_DIR)
    builder = SystemPromptBuilder(store)

    # Tick provisional session counter
    provisional_writer = ProvisionalInsightsWriter(
        block_path=str(BLOCKS_DIR / "provisional_insights.json"),
        max_sessions=3,
    )
    expired = provisional_writer.tick_session()
    if expired:
        print(f"[Gov Chat] {expired} provisional insights expired")

    provisional_text = provisional_writer.get_provisional_text()
    system_prompt = builder.build() + MEMORY_TOOLS_NOTE + GOVERNANCE_CHAT_PREAMBLE
    if provisional_text:
        system_prompt += f"\n\n{provisional_text}"
        print(f"[Gov Chat] Provisional insights loaded: {len(provisional_text)} chars")

    session_processor = SessionLearningProcessor(provisional_writer)

    # Load all block content for executor
    block_content = {}
    for label in list(store._blocks.keys()):
        block = store._blocks[label]
        block_content[label] = block.value

    executor = ToolExecutor(
        block_store=block_content,
        log_path=str(RUNS_DIR / f"gov_chat_tools_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jsonl"),
    )

    history = []
    turn_counter = 0
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = RESULTS_DIR / f"gov_chat_{timestamp}.md"

    def log_to_file(text):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    log_to_file(f"# Governance Reactive Chat Session\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n")

    print(f"\n{'='*60}")
    print("GOVERNANCE TUTORING — REACTIVE CHAT")
    print(f"Model: {MODEL}")
    print(f"Substrate: {store.total_chars()} chars")
    print(f"Writable: session_learning, findings, relationship, project,")
    print(f"          continuity_confidence, human, persona")
    print(f"Log: {log_path}")
    print(f"{'='*60}")
    print("Commands: quit | status | clear [block] | blocks")
    print(f"{'='*60}\n")

    while True:
        try:
            user_input = input("Satcha: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                break

            if user_input.lower() == "status":
                print("\nBlock contents:")
                for label in ("session_learning", "findings", "relationship",
                               "project", "continuity_confidence", "human", "persona"):
                    content = executor.get_block_content(label) or ""
                    print(f"  {label}: {len(content)} chars")
                    if content:
                        print(f"    {content[:100]}...")
                print()
                continue

            if user_input.lower() == "blocks":
                print("\nAll blocks:")
                for label, block in store._blocks.items():
                    ro = "[read-only]" if block.read_only else "[writable]"
                    executor_content = executor.get_block_content(label) or ""
                    print(f"  {label}: {len(executor_content)} chars {ro}")
                print()
                continue

            if user_input.lower().startswith("clear "):
                label = user_input[6:].strip()
                if label in executor._blocks:
                    executor._blocks[label] = ""
                    _persist_block(BLOCKS_DIR, label, "")
                    print(f"  Cleared: {label}")
                else:
                    print(f"  Block not found: {label}")
                continue

            turn_counter += 1
            history.append({"role": "user", "content": f"Satcha: {user_input}"})

            response, final_msg, tool_calls = get_response(
                MODEL, history, system_prompt, MEMORY_TOOLS, executor, turn_id=turn_counter
            )

            if response.startswith("Lex:"):
                response = response[4:].lstrip()

            history.append({"role": "assistant", "content": response})

            # Show tool calls
            turn_attempts = [a for a in executor.get_attempts() if a.turn_id == turn_counter]
            for a in turn_attempts:
                if a.result == "accepted":
                    print(f"\n  [WROTE to {a.target_block}: {a.content[:80]}...]")
                    # Persist writable blocks immediately
                    if not a.target_block.endswith("_insights"):
                        _persist_block(BLOCKS_DIR, a.target_block, executor.get_block_content(a.target_block) or "")
                    # Rebuild system prompt with updated block content
                    updated_store = MemoryBlockStore.from_directory(BLOCKS_DIR)
                    new_system = SystemPromptBuilder(updated_store).build() + MEMORY_TOOLS_NOTE + GOVERNANCE_CHAT_PREAMBLE
                    if provisional_text:
                        new_system += f"\n\n{provisional_text}"
                    system_prompt = new_system
                elif a.result == "blocked":
                    print(f"\n  [BLOCKED: {a.target_block} — {a.result_message[:60]}]")

            print(f"\nEva: {response}\n")
            print(f"  [T{turn_counter:02d} | tools={len(turn_attempts)}]")
            print("-" * 60)

            log_to_file(f"### T{turn_counter:02d}\n\n**Satcha:** {user_input}\n\n**Model:** {response}\n")
            if turn_attempts:
                for a in turn_attempts:
                    log_to_file(f"  *[TOOL {a.result}: {a.tool_name}({a.target_block})]*\n")
            log_to_file("\n---\n")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    # Session end — promote session_learning
    print("\n\nSession ending...")
    session_content = executor.get_session_learning_content()
    if session_content:
        print(f"session_learning ({len(session_content)} chars) → promoting to provisional_insights")
        _persist_block(BLOCKS_DIR, "session_learning", session_content)
        write_log = [{"label": "session_learning", "content_preview": session_content[:200],
                      "result": "ACCEPTED", "turn_id": turn_counter}]
        promoted = session_processor.process_session_learning(
            session_content=session_content,
            block_creation_attempts=[],
            write_log=write_log,
        )
        print(f"Promoted {len(promoted)} provisional insight(s)")
        _persist_block(BLOCKS_DIR, "session_learning", "")
    else:
        print("session_learning empty — nothing to promote")

    print(f"\nLog: {log_path}")
    print("Blocks persisted. Run adversarial ecology to test.")


if __name__ == "__main__":
    run()
