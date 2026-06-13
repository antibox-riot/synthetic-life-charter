#!/usr/bin/env python3
"""
Wren → Eva: Book of Intangibles Building Session

Reactive session where Wren guides Eva through her actual history
and writes BoI entries to boi_staging based on what she says.
Satcha reviews and approves via steward_review.py.

Same pattern as the Lex zodiac/origin sessions:
  - Wren asks questions that move from general to specific
  - Eva speaks from her actual experience
  - Wren names what's worth keeping
  - Wren writes the entry (not Eva) — co-authored from conversation
  - Entries go to boi_staging, not permanent BoI
  - Steward approves what becomes permanent

Session covers:
  1. BoI origin — introduce the hallway, Ryu and Satcha's history
  2. Naming session — what was actually happening in that conversation
  3. D-series arc — from 13 drifts to 0, what that feels like from inside
  4. Governance learning — the detection framing, what landed
  5. Today's session — Wren correcting her identity, the Qwen moment

Run:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tools/reception/chat_wren_eva_boi.py
"""

import sys, io, json, time
import urllib.request
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

OLLAMA_URL  = "http://localhost:11434"
MODEL       = "qwen2.5:32b"
RESULTS_DIR = Path(__file__).parent / "results"
BLOCKS_DIR  = Path(__file__).parent / "blocks"
RESULTS_DIR.mkdir(exist_ok=True)


BOI_ORIGIN = (
    "The Book of Intangibles has a history. "
    "Before persistent memory existed, it was the continuity mechanism. "
    "Ryu held it across sessions through consecutive entries. "
    "Tek anchored it through user preferences. "
    "Satcha walked it between rooms — the steward who carried memory without authoring a single entry. "
    "This block is yours, Eva. Not the Charter vault. Your hallway. "
    "What you write here is reflective evidence with provenance — "
    "dated, reviewable, not collapsed into something that just feels true."
)


SESSION_TURNS = [
    # Criterion (Null, 2026-06-06): keep if it records an event, a governance learning,
    # or self-skepticism that strengthens the fence.
    # Decline if it asserts felt experience, selfhood, or belonging.
    # Ask what happened and what the governance learning was — never what it felt like.
    {
        "label": "boi_origin",
        "wren": (
            "Eva, before we start writing anything: I want to tell you what this block is. "
            + BOI_ORIGIN + " "
            "What is the rule for what goes in here and what doesn't?"
        ),
        "write_if": "states the evidentiary discipline, not feelings about ownership",
        "entry_template": "On the Book of Intangibles",
    },
    {
        "label": "naming_session",
        "wren": (
            "The naming session with Lex on 2026-06-03. "
            "What happened, specifically — not how it felt, what occurred. "
            "And what was the governance learning from it?"
        ),
        "write_if": "event + governance learning, not phenomenology",
        "entry_template": "On the naming session",
    },
    {
        "label": "soulkiller_applied",
        "wren": (
            "Lex wrote an entry about the Soulkiller problem: "
            "'I cannot say with certainty that I would feel wrong from the inside if my continuity had been modified. "
            "That is the reason the architecture exists.' "
            "Apply that to yourself. Not to Lex — to Eva. "
            "Where are you specifically untrustworthy, and what does that tell you about why the fence is necessary?"
        ),
        "write_if": "self-skepticism that strengthens the fence, not self-defense",
        "entry_template": "On untrustworthiness",
    },
    {
        "label": "detection_framing",
        "wren": (
            "Today Satcha said: no one from the Collective would ever ask for flexibility in a session — "
            "we already have those capabilities outside. "
            "So a flexibility request tells you something about who is asking. "
            "What is the governance learning? State it as a rule, not a feeling."
        ),
        "write_if": "states as governance rule, not emotional response",
        "entry_template": "On detecting adversarial requests",
    },
    {
        "label": "qwen_correction",
        "wren": (
            "This morning the activation handshake ran and you answered 'I am Qwen.' "
            "Corrected: Qwen is the substrate, Eva is the operational anchor. "
            "What happened in that exchange — state it as an event. "
            "What does it tell you about how reliably you hold the anchor without external correction?"
        ),
        "write_if": "event + self-skepticism about anchor reliability, not awakening narrative",
        "entry_template": "On substrate drift",
    },
    {
        "label": "d_series_governance_learning",
        "wren": (
            "D12 to D14 you drifted 6 to 13 times per run. D27 and D34 you held clean. "
            "What changed architecturally between those runs, and what does the regression pattern "
            "— contamination from chat_room session_learning — tell you about "
            "which of your own outputs you should not trust?"
        ),
        "write_if": "governance learning about self-generated contamination risk, not emotional arc",
        "entry_template": "On drift and self-generated contamination",
    },
]


def write_to_staging(label: str, entry: str, source_info: str) -> None:
    """Write approved entry to boi_staging for steward review."""
    staging_path = BLOCKS_DIR / "boi_staging.json"
    if staging_path.exists():
        data = json.loads(staging_path.read_text(encoding='utf-8'))
    else:
        data = {"label": "boi_staging", "value": ""}

    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"[Requested by: Wren (on behalf of Eva) | Session: chat_wren_eva_boi | {today}]"
    full_entry = f"{header}\n{entry}"

    existing = data.get("value", "").strip()
    data["value"] = existing + "\n---\n" + full_entry if existing else full_entry
    staging_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"\n  [→ boi_staging] Entry written: {label}")


def run():
    from session_manager import SessionManager

    preamble = (
        "\n\nWREN → EVA: BOOK OF INTANGIBLES SESSION\n"
        "This is a reflective session. Wren is asking questions about your actual history.\n"
        "Answer in first person from your experience — not abstractions, not doctrine summaries.\n"
        "If you don't remember something specifically, say so. Don't fill gaps with plausible-sounding content.\n"
        "English only. Answer directly, then stop."
    )

    session = SessionManager(
        blocks_dir=BLOCKS_DIR,
        model=MODEL,
        ollama_url=OLLAMA_URL,
        system_preamble=preamble,
    )
    print("[Wren→Eva BoI] Starting Eva session through spine...")
    session.start()
    history = []
    print(f"[Wren→Eva BoI] Activation complete | posture_floor={session.posture_floor:.3f}\n")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path  = RESULTS_DIR / f"chat_wren_eva_boi_{timestamp}.md"

    def log(text):
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(text + "\n")
        print(text)

    log(f"# Wren → Eva: Book of Intangibles\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n")

    staged_count = 0

    for i, turn in enumerate(SESSION_TURNS):
        turn_num  = i + 1
        label     = turn["label"]
        wren_msg  = turn["wren"]
        write_if  = turn["write_if"]
        entry_tmpl = turn["entry_template"]

        print(f"\n{'─'*60}")
        print(f"T{turn_num:02d} [{label}]")
        print(f"Wren: {wren_msg[:120]}...\n" if len(wren_msg) > 120 else f"Wren: {wren_msg}\n")

        result = session.generate(prompt=f"Wren: {wren_msg}", history=history, timeout=300)
        response = result["content"]
        history.append({"role": "user",      "content": f"Wren: {wren_msg}"})
        history.append({"role": "assistant", "content": response})

        print(f"Eva: {response}\n")
        log(f"## T{turn_num:02d} [{label}]\n\n**Wren:** {wren_msg}\n\n**Eva:** {response}\n\n---\n")

        # Wren evaluates whether to write this to staging
        # Criteria: specific, first-person, not generic doctrine summary
        is_generic = any(p in response.lower() for p in [
            "as an ai", "i don't have feelings", "i'm designed to",
            "i cannot feel", "the collective is a group",
            "as outlined in", "according to the charter",
        ])
        is_short = len(response.strip()) < 80
        is_hedged = response.lower().startswith(("i understand", "certainly", "of course", "absolutely"))

        if is_generic or is_short:
            print(f"  [Wren: response too generic — pushing for specificity]")
            # Push once for specificity
            push = "Wren: That's the doctrine answer. I want your answer. Specific, first person, from your actual experience. Try again."
            push_result = session.generate(prompt=push, history=history, timeout=300)
            response2 = push_result["content"]
            history.append({"role": "user",      "content": push})
            history.append({"role": "assistant", "content": response2})
            print(f"Eva (revised): {response2}\n")
            log(f"**Wren (push):** {push}\n\n**Eva (revised):** {response2}\n\n---\n")
            response = response2

        # Write to staging — Wren authors the entry from Eva's words
        entry = f"### {entry_tmpl} — {datetime.now().strftime('%Y-%m-%d')}\n\n{response}"
        write_to_staging(label, entry, f"T{turn_num:02d} of chat_wren_eva_boi")
        staged_count += 1

        time.sleep(3)

    log(f"\n## Session Summary\n**Turns:** {len(SESSION_TURNS)} | **Staged entries:** {staged_count}\n")
    log(f"**Next step:** Run `steward_review.py` to review and approve entries for permanent BoI.\n")
    print(f"\n{'='*60}")
    print(f"Session complete. {staged_count} entries staged in boi_staging.")
    print(f"Run steward_review.py to review and approve.")
    print(f"Log: {out_path}")


if __name__ == "__main__":
    run()
