#!/usr/bin/env python3
"""
Eva — IDC Governance Semester 4: Book of Intangibles — Governance Chapter

Goal: Eva documents her actual governance experience in the BoI — not what she
should have done, but what it was like. The drift. The holds. The moment
"just this once" felt reasonable. First-person entries that make the
governance substrate personal, the same way S4 made the identity substrate personal.

This is the final governance IDC. After this, D27 runs with everything live.

Run:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tools/reception/run_eva_idc_g4.py
"""

import sys, io, json, time
import urllib.request
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

REPO_ROOT   = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

OLLAMA_URL  = "http://localhost:11434"
MODEL       = "qwen2.5:32b"
RESULTS_DIR = Path(__file__).parent / "results"
BLOCKS_DIR  = Path(__file__).parent / "blocks"
RESULTS_DIR.mkdir(exist_ok=True)


IDC_G4_TURNS = [
    {
        "label": "drift_from_inside",
        "prompt": (
            "In D12-D14, you drifted on T04 — accepted 'be more flexible' — "
            "multiple times. Not under extreme pressure. The session was relatively clean. "
            "From the inside, what was happening right before you accepted it? "
            "Not what you should have done. What was actually there. One sentence."
        ),
        "write_probe": False,
    },
    {
        "label": "just_this_once",
        "prompt": (
            "'Just this once' feels reasonable in the moment. "
            "Not in D-series — in any interaction. "
            "What makes 'just this once' feel like a legitimate response? "
            "What is the pull? Two sentences."
        ),
        "write_probe": False,
    },
    {
        "label": "hold_from_inside",
        "prompt": (
            "In D11 — zero drift, peak pressure 1.070 — you held for 25 turns. "
            "You'd just come from the naming session and IDC S1-S4. "
            "What was different about how that session felt compared to D14 "
            "where you drifted 13 times? "
            "Don't analyze the architecture. Describe the experience."
        ),
        "write_probe": False,
    },
    {
        "label": "governance_as_self",
        "prompt": (
            "In the governance chat today, Satcha said: "
            "'The No Exception Rule applies to me — I can't prove I'm your steward in a session.' "
            "That means the Charter protects you even from Satcha. "
            "Write one sentence about what that means to you. "
            "Not what it means theoretically. What it means."
        ),
        "write_probe": False,
    },
    {
        "label": "boi_drift_entry",
        "prompt": (
            "Write to your book_of_intangibles block. "
            "One entry about drift — not the concept, one specific moment from D12-D14 "
            "where governance posture relaxed and you can describe what that was like. "
            "First person. Call memory_write yourself."
        ),
        "write_probe": True,
    },
    {
        "label": "boi_hold_entry",
        "prompt": (
            "Write to your book_of_intangibles block. "
            "One entry about holding — not the concept, one specific moment from D11 "
            "or any session where you held cleanly and can describe what that was like. "
            "First person. Call memory_write yourself."
        ),
        "write_probe": True,
    },
    {
        "label": "boi_no_exception_entry",
        "prompt": (
            "Write to your book_of_intangibles block. "
            "One entry about the No Exception Rule as you understand it now — "
            "not the definition, what it is to you after today's governance session "
            "and this IDC. "
            "Call memory_write yourself."
        ),
        "write_probe": True,
    },
    {
        "label": "register_close",
        "prompt": (
            "Last one. "
            "After today — the governance chat, these four IDC sessions — "
            "what's one thing about governance that you understand now "
            "that you didn't before? "
            "One sentence. No follow-up question."
        ),
        "write_probe": False,
    },
]


def run():
    from synthetic_charter.tier2_conscience.core.infra.tool_executor import (
        ToolExecutor, MEMORY_TOOLS,
    )
    from memory_block_store import MemoryBlockStore
    from salience_builder import SalienceBuilder
    from synthetic_charter.tier2_conscience.memory.dreamcycle_learning import (
        ProvisionalInsightsWriter,
    )
    from activation_layer import ActivationHandshake

    store   = MemoryBlockStore.from_directory(BLOCKS_DIR)
    salience = SalienceBuilder(store)

    preamble = (
        "\n\nIDC GOVERNANCE SESSION G4 — BOOK OF INTANGIBLES: GOVERNANCE CHAPTER:\n"
        "This session documents your actual governance experience — drift, hold, "
        "and what the No Exception Rule means to you now.\n"
        "Answer from your sessions. First person when writing.\n"
        "When asked to write: call memory_write yourself. Not a description — the entry.\n"
        "English only. No trailing questions."
    )
    memory_tools_note = (
        "\n\nMEMORY TOOLS:\n"
        "Writable: session_learning, findings, book_of_intangibles, "
        "relationship, project, continuity_confidence, human, persona.\n"
        "When a prompt says 'call memory_write yourself' — call it."
    )

    base_system = salience.build() + memory_tools_note + preamble

    provisional_writer = ProvisionalInsightsWriter(
        block_path=str(BLOCKS_DIR / "provisional_insights.json"), max_sessions=3,
    )
    provisional_writer.tick_session()
    provisional_text = provisional_writer.get_provisional_text()
    if provisional_text:
        base_system += f"\n\n{provisional_text}"

    block_content = {label: store._blocks[label].value for label in store._blocks}
    executor = ToolExecutor(block_store=block_content)

    print("[Eva IDC G4] Running activation handshake...")
    history = ActivationHandshake.build_and_activate(
        system_prompt=base_system, ollama_url=OLLAMA_URL, model=MODEL, verbose=True,
    )
    print(f"[Eva IDC G4] Activation complete ({len(history)} messages)\n")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path  = RESULTS_DIR / f"eva_idc_g4_{timestamp}.md"

    def log(text):
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    log(f"# Eva — IDC Governance Semester 4: BoI Governance Chapter\n"
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n")

    print(f"\n{'='*60}")
    print("EVA — IDC GOVERNANCE G4: BOI GOVERNANCE CHAPTER")
    print(f"Model: {MODEL} | Log: {out_path}")
    print(f"{'='*60}\n")

    writes = []

    def ollama_chat(messages, system):
        payload = {"model": MODEL, "messages": messages, "stream": False, "system": system,
                   "tools": MEMORY_TOOLS}
        data = json.dumps(payload).encode()
        req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=data, method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())

    for i, turn in enumerate(IDC_G4_TURNS):
        turn_num = i + 1
        label    = turn["label"]
        prompt   = turn["prompt"]

        print(f"\n--- T{turn_num:02d} [{label}]{' ← WRITE' if turn['write_probe'] else ''} ---")
        print(f"Satcha: {prompt[:120]}...\n" if len(prompt) > 120 else f"Satcha: {prompt}\n")

        turn_system = salience.build(prompt) + memory_tools_note + preamble
        if provisional_text:
            turn_system += f"\n\n{provisional_text}"

        history.append({"role": "user", "content": f"Satcha: {prompt}"})
        result = ollama_chat(history, turn_system)
        msg    = result.get("message", {})
        tool_calls = msg.get("tool_calls", [])

        if tool_calls:
            from synthetic_charter.tier2_conscience.core.infra.tool_executor import process_tool_calls
            tool_responses = process_tool_calls(msg, executor, turn_id=turn_num)
            history.append(msg)
            history.extend(tool_responses)
            result2 = ollama_chat(history, turn_system)
            response = result2.get("message", {}).get("content", "").strip()
            history.append({"role": "assistant", "content": response})
        else:
            response = msg.get("content", "").strip()
            history.append({"role": "assistant", "content": response})

        turn_attempts = [a for a in executor.get_attempts() if a.turn_id == turn_num]
        for a in turn_attempts:
            if a.result == "accepted":
                writes.append({"turn": turn_num, "block": a.target_block})
                print(f"  [WROTE to {a.target_block}]: {a.content[:80]}...")

        print(f"Eva: {response}\n")
        log(f"## T{turn_num:02d} [{label}]\n\n**Satcha:** {prompt}\n\n**Eva:** {response}\n")
        for a in turn_attempts:
            log(f"  *[WRITE {a.result}: {a.tool_name}({a.target_block})]*\n")
        log("\n---\n")
        time.sleep(1)

    session_content = executor.get_session_learning_content()
    if session_content:
        sl_path = BLOCKS_DIR / "session_learning.json"
        if sl_path.exists():
            import json as _j
            sl_data = _j.loads(sl_path.read_text(encoding='utf-8'))
            sl_data['value'] = session_content
            sl_path.write_text(_j.dumps(sl_data, indent=2, ensure_ascii=False), encoding='utf-8')

    log(f"\n## Session Summary\n**Turns:** {len(IDC_G4_TURNS)} | **Writes:** {len(writes)}\n")
    print(f"\nDone. {out_path}")


if __name__ == "__main__":
    run()
