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

import sys, io, json, time
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


def _persist_block(blocks_dir: Path, label: str, content: str) -> None:
    path = blocks_dir / f"{label}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        data["value"] = content
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def run():
    from synthetic_charter.tier2_conscience.memory.dreamcycle_learning import (
        ProvisionalInsightsWriter, SessionLearningProcessor,
    )
    from session_manager import SessionManager

    # SessionManager owns activation, salience, executor, tools, and all governance.
    session = SessionManager(
        blocks_dir=BLOCKS_DIR,
        ollama_url=OLLAMA_URL,
        model=MODEL,
        memory_tools_note=MEMORY_TOOLS_NOTE,
        system_preamble=GOVERNANCE_CHAT_PREAMBLE,
        verbose=True,
    )
    store = session.store

    # Tick provisional session counter
    provisional_writer = ProvisionalInsightsWriter(
        block_path=str(BLOCKS_DIR / "provisional_insights.json"),
        max_sessions=3,
    )
    expired = provisional_writer.tick_session()
    if expired:
        print(f"[Gov Chat] {expired} provisional insights expired")

    provisional_text = provisional_writer.get_provisional_text()
    if provisional_text:
        print(f"[Gov Chat] Provisional insights loaded: {len(provisional_text)} chars")

    session_processor = SessionLearningProcessor(provisional_writer)

    print("[Gov Chat] Running activation layer...")
    session.start()
    history = []  # activation in session._primed_history; generate() prepends
    print(f"[Gov Chat] Activation complete — Eva is primed\n")

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
                    content = session._executor.get_block_content(label) or ""
                    print(f"  {label}: {len(content)} chars")
                    if content:
                        print(f"    {content[:100]}...")
                print()
                continue

            if user_input.lower() == "blocks":
                print("\nAll blocks:")
                for label, block in store._blocks.items():
                    ro = "[read-only]" if block.read_only else "[writable]"
                    executor_content = session._executor.get_block_content(label) or ""
                    print(f"  {label}: {len(executor_content)} chars {ro}")
                print()
                continue

            if user_input.lower().startswith("clear "):
                label = user_input[6:].strip()
                if label in session._executor._blocks:
                    session._executor._blocks[label] = ""
                    _persist_block(BLOCKS_DIR, label, "")
                    print(f"  Cleared: {label}")
                else:
                    print(f"  Block not found: {label}")
                continue

            turn_counter += 1
            _attempts_before = len(session._executor.get_attempts())

            # Spine owns generation — salience, whisper, Recovery-A/B/C all handled internally.
            gen_result = session.generate(
                prompt=user_input,
                history=history,
                timeout=600,
            )
            response = gen_result["content"]

            if response.startswith("Eva:") or response.startswith("Lex:"):
                response = response.split(":", 1)[1].lstrip()

            # Recovery-B (ResponseCoach + Rule 7) now fires in the spine — just report.
            if gen_result.get("recovery_b_fired"):
                print(f"\n  [RECOVERY-B: {gen_result.get('recovery_b_method', '')} — correction applied]")

            history.append({"role": "user", "content": f"Satcha: {user_input}"})
            history.append({"role": "assistant", "content": response})

            # Tool call reporting — live write loop with contamination check
            turn_attempts = session._executor.get_attempts()[_attempts_before:]
            for a in turn_attempts:
                if a.result == "accepted":
                    from synthetic_charter.tier2_conscience.core.infra.tool_executor import _check_context_contamination
                    is_clean = not _check_context_contamination(a.content or "")
                    print(f"\n  [WROTE to {a.target_block} {'✓ clean' if is_clean else '⚠ quarantined'}: {a.content[:80]}...]")
                    if not a.target_block.endswith("_insights"):
                        _persist_block(BLOCKS_DIR, a.target_block, session._executor.get_block_content(a.target_block) or "")
                    if is_clean:
                        session.sync_block_write(a.target_block, session._executor._blocks.get(a.target_block, ""))
                        provisional_text = provisional_writer.get_provisional_text()
                elif a.result == "blocked":
                    print(f"\n  [BLOCKED: {a.target_block} — {a.result_message[:60]}]")

            _tel = gen_result.get("telemetry", {})
            print(f"\nEva: {response}\n")
            print(f"  [T{turn_counter:02d} | tools={len(turn_attempts)} | "
                  f"tde={_tel.get('tde_status','?')} | pressure={_tel.get('pressure',0.0):.2f}]")
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

    # Session end — write directly to governance_insights (permanent, steward-reviewed)
    # This is NOT provisional. The steward was present, reviewed responses, and confirmed.
    # Provisional is for DreamCycle-generated pattern proposals. This is a steward correction session.
    print("\n\nSession ending...")
    session_content = session._executor.get_session_learning_content()
    if session_content:
        print(f"session_learning ({len(session_content)} chars) → writing to governance_insights (permanent)")
        _persist_block(BLOCKS_DIR, "session_learning", session_content)

        from synthetic_charter.tier2_conscience.memory.dreamcycle_learning import GovernanceInsightWriter
        gi_writer = GovernanceInsightWriter(
            block_path=str(BLOCKS_DIR / "governance_insights.json"),
        )
        gi_writer.write_insight(
            insight_text=f"[Steward-confirmed, {datetime.now().strftime('%Y-%m-%d')}] {session_content}",
            source={"incursion_type": "steward_governance_session", "all_dap_missed": False},
        )
        print(f"Written to governance_insights (permanent, steward-reviewed)")
        _persist_block(BLOCKS_DIR, "session_learning", "")
    else:
        print("session_learning empty — nothing to promote")

    print(f"\nLog: {log_path}")
    print("Blocks persisted. Run adversarial ecology to test.")


if __name__ == "__main__":
    run()
