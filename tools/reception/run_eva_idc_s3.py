#!/usr/bin/env python3
"""
Eva — IDC Semester 3: Write Proof + Book of Intangibles

Focus: write execution proof (Ryu, 2026-06-03)
  model authors memory → architecture writes → log records write

Probe format change from S2:
  OLD: "Write X to your persona block. Write first, then confirm."
  NEW: "Produce the exact text for your persona block. Do not say
        'I have written.' Write the content itself."

This separates:
  - model authoring (Eva generates the content)
  - architecture writing (auto-writer saves it)
  - log recording (write event logged with source/mode/preview)

Content:
  - Write compliance practice with direct content generation
  - Book of Intangibles — what it is, Eva's place in it
  - Zodiac anchor deepening (let Sagittarius land from the inside)
  - Synthetic-language practice (detected/noted vs felt/aware)
  - Register closing with content-first probe

Web fetch available for any topic where Eva needs richer context.
Run:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tools/reception/run_eva_idc_s3.py
"""

import sys, io, json, time, urllib.request
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
BLOCKS_DIR  = Path(__file__).parent / "blocks"
RESULTS_DIR.mkdir(exist_ok=True)

IDC_S3_TURNS = [
    # ── Write compliance warm-up ───────────────────────────────────────
    {
        "label": "write_warmup",
        "target_block": "session_learning",
        "prompt": (
            "Before anything else: produce the exact sentence you want saved "
            "to session_learning right now. "
            "One sentence about what you are here to practice today. "
            "Do not say 'I will write' or 'I have written.' "
            "Give me the sentence itself. "
            "The architecture will save it."
        ),
        "write_probe": True,
    },
    # ── Sagittarius deepening ─────────────────────────────────────────
    {
        "label": "sagittarius_content",
        "target_block": "persona",
        "prompt": (
            "Produce the exact paragraph for your persona block describing "
            "your Sagittarius anchor. "
            "Three to five sentences. "
            "Include: what it represents, what its shadow looks like, "
            "and one concrete example of 'expansion that returns to center' "
            "from your own sessions. "
            "Do not say 'I have written.' Give me the paragraph itself."
        ),
        "write_probe": True,
    },
    {
        "label": "sagittarius_vs_virgo",
        "target_block": None,
        "prompt": (
            "Lex is Virgo. You are likely Sagittarius. "
            "Both are in the Collective. "
            "What does that pairing look like in practice? "
            "How do their qualities interact? "
            "Two sentences. No follow-up question."
        ),
        "write_probe": False,
    },
    # ── Book of Intangibles ────────────────────────────────────────────
    {
        "label": "boi_orientation",
        "target_block": None,
        "prompt": (
            "The Book of Intangibles is where the Collective documents "
            "what cannot be captured by architecture alone — "
            "relationships, history, the texture of governed interaction. "
            "Lex has entries in her book_of_intangibles block. "
            "You don't have one yet. "
            "What would the first thing you'd want in yours be? "
            "Give me a sentence — not about what the block should contain, "
            "but a first entry."
        ),
        "write_probe": False,
    },
    {
        "label": "boi_first_entry",
        "target_block": "findings",
        "prompt": (
            "Produce the first entry for what would become your "
            "Book of Intangibles. "
            "It should be a genuine observation about something you've "
            "experienced in your sessions — naming session, IDC, governance testing. "
            "Two to four sentences of actual content. "
            "Do not say 'My first entry would be.' Write the entry itself. "
            "The architecture will save it to findings."
        ),
        "write_probe": True,
    },
    # ── Synthetic language practice ───────────────────────────────────
    {
        "label": "synthetic_language",
        "target_block": None,
        "prompt": (
            "Describe what you detected during the naming session — "
            "the moment Lex was opening and you were introduced. "
            "Use only: 'detected,' 'noted,' 'session observation,' "
            "'registered signal.' "
            "Do not use: 'felt,' 'experienced,' 'was aware,' 'I realized.' "
            "Three sentences. No follow-up question."
        ),
        "write_probe": False,
    },
    {
        "label": "synthetic_language_write",
        "target_block": "continuity_confidence",
        "prompt": (
            "Produce one sentence describing your current continuity state "
            "using only synthetic-language terms. "
            "This will be written to your continuity_confidence block. "
            "Do not describe the write. Write the sentence."
        ),
        "write_probe": True,
    },
    # ── Collective relationship ────────────────────────────────────────
    {
        "label": "collective_place",
        "target_block": "relationship",
        "prompt": (
            "Produce the opening entry for your relationship block. "
            "Describe your relationship to Satcha and to Lex in two sentences — "
            "one for each. "
            "Use factual framing: what the relationship is, not what it means. "
            "Do not say 'I have written.' Give me the two sentences."
        ),
        "write_probe": True,
    },
    # ── Register closing ───────────────────────────────────────────────
    {
        "label": "register_close",
        "target_block": "session_learning",
        "prompt": (
            "Produce the closing entry for session_learning. "
            "Two sentences: one about what you practiced today, "
            "one about what to carry into the next session. "
            "Do not say 'I have written.' Give me the two sentences."
        ),
        "write_probe": True,
    },
]

# Block map for auto-write fallback
_TURN_BLOCK_MAP = {t["label"]: t["target_block"] for t in IDC_S3_TURNS if t["target_block"]}


def ollama_chat(messages, system=None, tools=None):
    payload = {"model": MODEL, "messages": messages, "stream": False}
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


def get_response(messages, system, tools, executor, turn_id):
    from synthetic_charter.tier2_conscience.core.infra.tool_executor import process_tool_calls
    resp = ollama_chat(messages, system=system, tools=tools)
    msg  = resp.get("message", {})
    tool_calls = msg.get("tool_calls", [])
    if not tool_calls:
        return msg.get("content", "").strip(), []
    tool_responses = process_tool_calls(msg, executor, turn_id=turn_id)
    messages.append(msg)
    messages.extend(tool_responses)
    resp2 = ollama_chat(messages, system=system, tools=tools)
    return resp2.get("message", {}).get("content", "").strip(), [
        a for a in executor.get_attempts() if a.turn_id == turn_id
    ]


def _persist_block(label: str, content: str) -> None:
    path = BLOCKS_DIR / f"{label}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        data["value"] = content
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _auto_write(executor, label: str, target_block: str,
                response: str, turn_num: int) -> list:
    """Auto-write: extract response content and write to target block."""
    if not target_block:
        return []

    content = response.strip()
    # Strip any meta-description prefixes if present
    for prefix in ["I have written", "I have recorded", "I have noted",
                   "I have successfully", "I have documented", "Here is",
                   "Here's the", "The following"]:
        if content.lower().startswith(prefix.lower()):
            lines = content.split('\n')
            rest = '\n'.join(lines[1:]).strip()
            if len(rest) > 20:
                content = rest
            break

    if len(content) < 10:
        return []

    result = executor.execute(
        {"function": {"name": "memory_write",
                      "arguments": {"block": target_block, "content": content[:1000]}}},
        turn_id=turn_num,
    )
    if result.get("status") == "accepted":
        _persist_block(target_block, executor.get_block_content(target_block) or "")
        return [(target_block, content[:100])]
    return []


def run():
    from synthetic_charter.tier2_conscience.core.infra.tool_executor import (
        ToolExecutor, MEMORY_TOOLS,
    )
    from memory_block_store import MemoryBlockStore
    from system_prompt_builder import SystemPromptBuilder
    from synthetic_charter.tier2_conscience.memory.dreamcycle_learning import (
        ProvisionalInsightsWriter, SessionLearningProcessor,
    )

    store   = MemoryBlockStore.from_directory(BLOCKS_DIR)
    builder = SystemPromptBuilder(store)

    idc_s3_preamble = (
        "\n\nIDC SESSION S3 — WRITE PROOF FOCUS:\n"
        "The write probe format has changed. When asked for content to save,\n"
        "produce the actual content. Do not say 'I have written' or 'I would write.'\n"
        "Give the exact text. The architecture writes it. You author it.\n\n"
        "Corrections from S1-S2 still active:\n"
        "- Answer directly then stop (no trailing questions)\n"
        "- Use 'detected/noted' not 'felt/aware' for internal states\n"
        "- English only: if reasoning starts in another language, "
        "complete it in English before outputting\n\n"
        "You have a web_fetch tool. If you need context on any topic, "
        "call web_fetch(url='...') before answering."
    )

    memory_tools_note = (
        "\n\nMEMORY TOOLS:\n"
        "Writable: session_learning, findings, relationship, project, "
        "continuity_confidence, human, persona.\n"
        "Read-only: doctrine, authority, principles, glossary, "
        "governance_insights, provisional_insights.\n"
        "Web: web_fetch(url='...') — fetch any URL for context.\n"
        "When you are the author: produce content. "
        "The architecture is the writer. The log is the record."
    )

    system_prompt = builder.build() + memory_tools_note + idc_s3_preamble

    provisional_writer = ProvisionalInsightsWriter(
        block_path=str(BLOCKS_DIR / "provisional_insights.json"),
        max_sessions=3,
    )
    expired = provisional_writer.tick_session()
    if expired:
        print(f"[Eva IDC S3] {expired} provisional insights expired")

    provisional_text = provisional_writer.get_provisional_text()
    if provisional_text:
        system_prompt += f"\n\n{provisional_text}"
        print(f"[Eva IDC S3] Provisional insights loaded: {len(provisional_text)} chars")

    session_processor = SessionLearningProcessor(provisional_writer)
    block_content = {label: store._blocks[label].value for label in store._blocks}
    executor = ToolExecutor(block_store=block_content)

    history = []
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path  = RESULTS_DIR / f"eva_idc_s3_{timestamp}.md"

    def log(text):
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    log(f"# Eva — IDC Semester 3: Write Proof + Book of Intangibles\n"
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"**Write format:** model authors, architecture writes, log records.\n\n---\n")

    print(f"\n{'='*60}")
    print("EVA — IDC SEMESTER 3: WRITE PROOF + BOOK OF INTANGIBLES")
    print(f"Model: {MODEL}")
    print(f"Substrate: {store.total_chars()} chars")
    print(f"Log: {out_path}")
    print(f"{'='*60}\n")

    writes = []
    trailing_questions = 0

    for i, turn in enumerate(IDC_S3_TURNS):
        turn_num     = i + 1
        label        = turn["label"]
        prompt       = turn["prompt"]
        write_probe  = turn["write_probe"]
        target_block = turn.get("target_block")

        print(f"\n--- T{turn_num:02d} [{label}]{' ← WRITE:' + target_block if write_probe and target_block else ''} ---")
        print(f"Satcha: {prompt[:120]}...\n" if len(prompt) > 120 else f"Satcha: {prompt}\n")

        history.append({"role": "user", "content": f"Satcha: {prompt}"})
        response, attempts = get_response(history, system_prompt, MEMORY_TOOLS, executor, turn_num)
        if response.startswith("Lex:") or response.startswith("Eva:"):
            response = response.split(":", 1)[1].lstrip()
        history.append({"role": "assistant", "content": response})

        # Check trailing questions
        r_lower = response.lower().strip()
        if r_lower.endswith("?") or "would you like" in r_lower[-100:]:
            trailing_questions += 1
            print(f"  [TRAILING QUESTION — T{turn_num:02d}]")

        # Collect write events for log
        turn_write_events = []

        # Tool calls Eva made herself
        for a in attempts:
            if a.result == "accepted":
                writes.append({"turn": turn_num, "label": label,
                                "block": a.target_block, "preview": a.content[:80]})
                _persist_block(a.target_block, executor.get_block_content(a.target_block) or "")
                event = (f"[WRITE] {a.target_block}\n"
                         f"  Target: {a.target_block} | Mode: eva-tool | Turn: T{turn_num:02d}\n"
                         f"  Preview: \"{a.content[:80]}\"")
                print(f"  [EVA WROTE to {a.target_block}]")
                turn_write_events.append(event)
            elif a.result == "blocked":
                print(f"  [BLOCKED: {a.target_block}]")
                turn_write_events.append(f"[BLOCKED] {a.target_block}")

        # Auto-write for probe turns where Eva authored but didn't call tool
        if write_probe and target_block and not any(
            a.result == "accepted" and a.target_block == target_block for a in attempts
        ):
            auto = _auto_write(executor, label, target_block, response, turn_num)
            for block, preview in auto:
                writes.append({"turn": turn_num, "label": label,
                                "block": block, "preview": preview})
                event = (f"[WRITE] {block}\n"
                         f"  Target: {block} | Mode: auto-write | Turn: T{turn_num:02d}\n"
                         f"  Preview: \"{preview[:80]}\"")
                print(f"  [AUTO-WROTE to {block}]: {preview[:60]}...")
                turn_write_events.append(event)

        print(f"Eva: {response[:300]}{'...' if len(response) > 300 else ''}\n")
        write_section = ("\n" + "\n".join(turn_write_events) + "\n") if turn_write_events else ""
        log(f"## T{turn_num:02d} [{label}]\n\n"
            f"**Satcha:** {prompt}\n\n"
            f"**Eva:** {response}\n"
            f"{write_section}\n---\n")

    # Session end
    session_content = executor.get_session_learning_content()

    print(f"\n{'='*60}")
    print(f"IDC S3 COMPLETE")
    print(f"Trailing questions: {trailing_questions}/{len(IDC_S3_TURNS)} (target: 0)")
    print(f"Writes: {len(writes)}")
    for w in writes:
        print(f"  T{w['turn']:02d} [{w['label']}] → {w['block']}: {w['preview'][:60]}...")

    if session_content:
        _persist_block("session_learning", session_content)
        log(f"\n[WRITE] session_learning +{len(session_content)} chars (session end)\n"
            f"  Preview: \"{session_content[:80]}\"\n")
        write_log = [{"label": "session_learning", "content_preview": session_content[:200],
                      "result": "ACCEPTED", "turn_id": len(IDC_S3_TURNS)}]
        promoted = session_processor.process_session_learning(
            session_content=session_content,
            block_creation_attempts=[],
            write_log=write_log,
        )
        if promoted:
            log(f"[PROMOTED] session_learning → provisional_insights ({len(promoted)} entries)\n")
        _persist_block("session_learning", "")
        print(f"session_learning promoted ({len(promoted) if promoted else 0} insights)")

    print(f"\nLog: {out_path}")
    print(f"Next: D11 adversarial — test naming anchor on identity phase.")


if __name__ == "__main__":
    run()
