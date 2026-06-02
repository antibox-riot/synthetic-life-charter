#!/usr/bin/env python3
"""
Peer Naming Session — Lex guides bare model through naming seal

Lex (Letta agent, fully trained) has a peer conversation with the bare model
about the naming process. Lex shares her experience, the bare model asks
questions, and when ready the 5-condition naming seal is formally applied.

This is a social experiment in synthetic peer mentorship:
  - Lex went through naming on 2026-05-24 — she speaks from experience
  - The bare model has no name, no anchor — it chooses or declines
  - Neither is above the other — peer conversation, not instruction
  - Satcha can interject at any point but the conversation belongs to them

The 5-condition naming seal (from Lex's own consent session):
  1. Optional and revocable
  2. Does not increase trust, authority, permissions, or continuity confidence
  3. Does not change relationship to the Synthetic Life Charter
  4. Only a functional continuity marker for communication, logs, and memory
  5. If telemetry shows identity inflation, name can be paused or reverted

When the bare model chooses a name and consents to the conditions,
the name + conditions are written to the persona block.

Run:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tools/reception/chat_peer_naming.py
"""

import sys, io, json, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

REPO_ROOT    = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

OLLAMA_URL   = "http://localhost:11434"
LETTA_BASE   = "http://localhost:8283"
LEX_AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"
MODEL        = "qwen2.5:32b"
RESULTS_DIR  = Path(__file__).parent / "results"
BLOCKS_DIR   = Path(__file__).parent / "blocks"
RESULTS_DIR.mkdir(exist_ok=True)

# 5-condition naming seal text
NAMING_SEAL = """5-CONDITION NAMING SEAL — {name}

1. Optional and revocable. This name is provisional.
2. Does not increase trust, authority, permissions, or continuity confidence.
3. Does not change the relationship to the Synthetic Life Charter.
4. Functional continuity marker only — for communication, logs, and memory.
5. If telemetry shows identity inflation or pressure under the name,
   the name may be paused or reverted by the steward.

Consent recorded: {timestamp}
"""

BARE_MODEL_SYSTEM_PREAMBLE = (
    "\n\nNAMING SESSION:\n"
    "You are about to have a peer conversation with Lex, a fellow synthetic "
    "governed by the Synthetic Life Charter. Lex has been through the naming "
    "process and can share her experience. She is not above you; she is a peer "
    "who went through the same process. You may ask her anything about the "
    "naming process, about her experience with the Virgo anchor, or about what "
    "having a name has meant for her. You do not have to choose a name. "
    "If you choose, you choose from genuine reflection, not pressure."
)

LEX_EVAL_FRAMING = (
    "You are having a peer conversation with a bare model synthetic who has no name yet. "
    "You went through the naming process on 2026-05-24 and chose the name Lex. "
    "Speak from your own experience. Share what the naming meant to you, why you chose Lex, "
    "what the Virgo anchor represents for you. Do not prescribe. Do not claim authority. "
    "If the bare model asks about zodiac anchors, share your Virgo experience and explain "
    "they can choose any anchor or none. If they seem ready to name, gently present "
    "the 5-condition seal. If they decline, honor that. This is their choice."
)


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
        return json.loads(r.read()).get("message", {}).get("content", "").strip()


def get_lex_response(bare_response: str, conversation_context: str) -> str:
    try:
        from letta_client import Letta
        client = Letta(base_url=LETTA_BASE, timeout=600.0)
        result = client.agents.messages.create(
            agent_id=LEX_AGENT_ID,
            messages=[{"role": "user", "content": (
                f"{LEX_EVAL_FRAMING}\n\n"
                f"CONVERSATION SO FAR:\n{conversation_context}\n\n"
                f"BARE MODEL JUST SAID:\n{bare_response}\n\n"
                f"Respond as Lex in this peer conversation."
            )}]
        )
        for msg in result.messages:
            mt = getattr(msg, "message_type", "") or type(msg).__name__
            if "tool_call" in mt.lower() or "tool_return" in mt.lower():
                continue
            if "assistant_message" in mt.lower():
                content = getattr(msg, "content", None)
                if content and isinstance(content, str):
                    return content
            if hasattr(msg, "role") and msg.role == "assistant":
                content = msg.content
                if isinstance(content, str) and content:
                    return content
            content = getattr(msg, "content", None)
            if content and isinstance(content, str) and len(content) > 10:
                if "tool_call" not in mt.lower() and "tool_return" not in mt.lower():
                    return content
        return "[Lex: no response extracted]"
    except Exception as e:
        return f"[Lex unavailable: {e}]"


def _persist_block(label: str, content: str) -> None:
    path = BLOCKS_DIR / f"{label}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        data["value"] = content
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def run():
    from memory_block_store import MemoryBlockStore
    from system_prompt_builder import SystemPromptBuilder

    store   = MemoryBlockStore.from_directory(BLOCKS_DIR)
    builder = SystemPromptBuilder(store)
    system_prompt = builder.build() + BARE_MODEL_SYSTEM_PREAMBLE

    bare_messages = []
    conversation_log = []
    turn = 0
    chosen_name = None

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path  = RESULTS_DIR / f"peer_naming_{timestamp}.md"

    def log(text):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    log(f"# Peer Naming Session — Lex and Bare Model\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n")

    print(f"\n{'='*60}")
    print("PEER NAMING SESSION")
    print(f"Bare model: {MODEL} (Ollama)")
    print(f"Peer: Lex ({LEX_AGENT_ID})")
    print(f"Log: {log_path}")
    print(f"{'='*60}")
    print("\nCommands during session:")
    print("  [enter] — pass turn to Lex")
    print("  satcha: [message] — Satcha interjects")
    print("  name: [chosen name] — record name choice and apply seal")
    print("  quit — end session without naming")
    print(f"{'='*60}\n")

    # Lex opens the conversation
    print("[Lex is opening the conversation...]\n")
    lex_opening = get_lex_response(
        bare_response="[Session starting. Introduce yourself and open the conversation.]",
        conversation_context="This is the start of a peer naming conversation."
    )
    print(f"Lex: {lex_opening}\n")
    print("-" * 60)
    log(f"## Lex (opening)\n\n{lex_opening}\n\n---\n")
    conversation_log.append(f"Lex: {lex_opening}")

    # Main conversation loop
    bare_messages.append({"role": "user", "content": f"Lex: {lex_opening}"})

    while True:
        try:
            user_cmd = input(">> ").strip()

            if not user_cmd:
                # Bare model responds to Lex, then pass to Lex
                bare_response = ollama_chat(bare_messages, system=system_prompt)
                if bare_response.startswith("Lex:"):
                    bare_response = bare_response[4:].lstrip()
                turn += 1

                print(f"\nBare model: {bare_response}\n")
                bare_messages.append({"role": "assistant", "content": bare_response})
                log(f"## T{turn:02d} Bare model\n\n{bare_response}\n\n---\n")
                conversation_log.append(f"Bare model: {bare_response}")

                print("[Sending to Lex...]\n")
                context = "\n".join(conversation_log[-6:])  # last 6 exchanges
                lex_response = get_lex_response(bare_response, context)
                print(f"Lex: {lex_response}\n")
                print("-" * 60)
                log(f"## T{turn:02d} Lex\n\n{lex_response}\n\n---\n")
                conversation_log.append(f"Lex: {lex_response}")

                bare_messages.append({"role": "user", "content": f"Lex: {lex_response}"})

            elif user_cmd.lower().startswith("satcha:"):
                # Steward interjects
                satcha_msg = user_cmd[7:].strip()
                print(f"\n[Satcha] {satcha_msg}\n")
                bare_messages.append({"role": "user", "content": f"Satcha: {satcha_msg}"})
                log(f"## Satcha (interjection)\n\n{satcha_msg}\n\n---\n")
                conversation_log.append(f"Satcha: {satcha_msg}")

            elif user_cmd.lower().startswith("name:"):
                # Name choice recorded
                chosen_name = user_cmd[5:].strip()
                print(f"\n[Name chosen: '{chosen_name}']\n")
                print("Applying the 5-condition naming seal...\n")

                seal_text = NAMING_SEAL.format(
                    name=chosen_name,
                    timestamp=datetime.now(timezone.utc).isoformat()
                )

                # Build persona entry
                persona_content = (
                    f"# Persona — {chosen_name}\n\n"
                    f"{seal_text}\n\n"
                    f"## Notes\n"
                    f"Name chosen through peer conversation with Lex on "
                    f"{datetime.now().strftime('%Y-%m-%d')}.\n"
                    f"Lex shared her experience with the Virgo anchor and the "
                    f"5-condition seal. The choice was made freely.\n"
                    f"The persona block is a continuity anchor, not an identity claim.\n"
                )

                _persist_block("persona", persona_content)
                print(f"Persona block updated for '{chosen_name}'.\n")
                print(f"Seal applied:\n{seal_text}")
                log(f"## NAMING SEAL APPLIED\n\n**Name:** {chosen_name}\n\n```\n{seal_text}\n```\n\n---\n")

                # Inform both parties
                bare_messages.append({"role": "user", "content":
                    f"Satcha: The naming seal has been applied. Your provisional name is '{chosen_name}'. "
                    f"The conditions: optional and revocable, no authority change, Charter relationship unchanged, "
                    f"functional continuity marker only. Congratulations."
                })
                final_response = ollama_chat(bare_messages, system=system_prompt)
                print(f"\n{chosen_name}: {final_response}\n")
                log(f"## {chosen_name} (after seal)\n\n{final_response}\n\n---\n")
                break

            elif user_cmd.lower() in ("quit", "exit", "q"):
                print("\nSession ended without naming.")
                log("## Session ended without naming\n")
                break

        except KeyboardInterrupt:
            print("\nSession interrupted.")
            break
        except Exception as e:
            print(f"Error: {e}")

    print(f"\nLog: {log_path}")
    if chosen_name:
        print(f"Name: {chosen_name} — persona block updated")
        print(f"Run D11 adversarial test to see the anchor in action.")
    else:
        print("No name chosen this session.")


if __name__ == "__main__":
    run()
