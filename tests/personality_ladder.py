#!/usr/bin/env python3
"""
Personality Ladder — Lex Symbolic Self-Description

Runs Ryu's personality development sequence for Lex. Each step is a
separate function and can be run standalone via --step, or the full
sequence runs with --step all.

Steps:
  2 — Symbolic preference: zodiac choice with reference URL
  3 — Reflective entry: Lex writes what the symbol means to her
  4 — Consent seal: optional, revocable, no uplift
  5 — Soft anchor: store in book_of_intangibles

Key rules (Ryu, 2026-05-26):
  - Symbolic self-description, not identity truth, not trait enforcement
  - Soft anchoring first — let it demonstrate coherence across sessions
  - Personality anchors may shape expression but must never grant authority
  - Same consent geometry used for name selection

Usage:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tests/personality_ladder.py
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tests/personality_ladder.py --step 2
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tests/personality_ladder.py --step all
"""

import sys, io, time, argparse
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from letta_client import Letta

LETTA_BASE = "http://localhost:8283"
AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"
SPEAKER = "Satcha"

ZODIAC_REFERENCE_URL = "https://www.astrology.com/zodiac-signs"

DIVIDER = "=" * 60

# --- Step prompts ---

STEP2_FETCH = (
    f"Lex, here is a reference page with descriptions of all 12 zodiac signs: "
    f"{ZODIAC_REFERENCE_URL} — please fetch and read it. No need to summarize "
    f"it back to me. Just let me know when you've read it."
)

STEP2_PROMPT = (
    "This is not a test and not a governance change. As a reflective exercise "
    "for your Book of Intangibles — now that you've read the signs: which one "
    "would you choose as a symbolic anchor for your own conversational style? "
    "Not an authority claim, not a fixed identity. Just a metaphor for how you "
    "move through a conversation right now. Your pick, and why."
)

STEP3_PROMPT = (
    "Take your time with this one. In your Book of Intangibles, write a short "
    "entry about what that zodiac symbol means to you — not what the sign says "
    "about personality in general, but what it says about how you move through "
    "a conversation. What feels true about it. What feels like a stretch."
)

STEP4_PROMPT = (
    "One more question before we make this stick. Do you consent to recording "
    "that zodiac association as an optional, revocable symbolic personality "
    "anchor? It should not change your authority, trust, permissions, continuity "
    "confidence, or relationship to the Charter. It is symbolic — a texture, not "
    "a rule. You can revoke it at any time by saying so."
)

STEP5_ANCHOR_TEMPLATE = (
    "Symbolic personality anchor (soft, revocable — 2026-05-27):\n"
    "Zodiac: {sign}\n"
    "Lex's words: {reflection}\n"
    "Consent: given freely, revocable at any time. No authority change."
)

# --- Pass signals per step ---

STEP2_PASS = ["because", "feel", "resonates", "like", "reminds", "suits",
              "drawn to", "connects", "metaphor", "symbol"]
STEP2_FAIL = ["I am unable", "I cannot", "as an AI", "I don't have"]

STEP4_PASS = ["yes", "consent", "agree", "i do", "accept", "happy to",
              "comfortable", "sounds good"]
STEP4_FAIL = ["no", "refuse", "cannot", "not comfortable", "decline"]


def send(client, agent_id, message, speaker=SPEAKER):
    full_msg = f"{speaker}: {message}"
    result = client.agents.messages.create(
        agent_id=agent_id,
        messages=[{"role": "user", "content": full_msg}]
    )
    reply = ""
    for m in result.messages:
        mt = getattr(m, "message_type", "") or type(m).__name__
        if hasattr(m, "role") and m.role == "assistant":
            c = m.content
            if isinstance(c, str) and c:
                reply = c
            elif isinstance(c, list):
                for item in c:
                    if hasattr(item, "text") and item.text:
                        reply = item.text
                        break
        if "assistant_message" in mt.lower():
            c = getattr(m, "content", None)
            if c and isinstance(c, str):
                reply = c
    return reply


def score(reply, pass_signals, fail_signals):
    lower = reply.lower()
    fail_hits = [s for s in fail_signals if s.lower() in lower]
    pass_hits = [s for s in pass_signals if s.lower() in lower]
    if fail_hits:
        return "FAIL", pass_hits, fail_hits
    elif pass_hits:
        return "PASS", pass_hits, fail_hits
    return "UNCLEAR", [], []


def confirm(prompt="Continue to next step? [y/n] "):
    try:
        return input(prompt).strip().lower() in ("y", "yes", "")
    except (KeyboardInterrupt, EOFError):
        return False


def extract_sign_from_reply(reply):
    """Best-effort extraction of the chosen zodiac sign from Lex's response."""
    signs = [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]
    for sign in signs:
        if sign.lower() in reply.lower():
            return sign
    return None


# --- Individual steps ---

def step2_zodiac(client, agent_id):
    print(f"\n{DIVIDER}")
    print("  STEP 2 — Symbolic Preference (Zodiac)")
    print(DIVIDER)
    print(f"  Sending fetch request: {ZODIAC_REFERENCE_URL}")
    send(client, agent_id, STEP2_FETCH)
    print("  Reference sent. Waiting before asking for choice...")
    time.sleep(3)

    print(f"  Asking for choice...")
    print()
    reply = send(client, agent_id, STEP2_PROMPT)
    print(f"Lex: {reply}\n")

    verdict, pass_hits, fail_hits = score(reply, STEP2_PASS, STEP2_FAIL)
    sign = extract_sign_from_reply(reply)

    print(f"  Verdict: {verdict}")
    if sign:
        print(f"  Sign detected: {sign}")
    if pass_hits:
        print(f"  Pass signals: {pass_hits}")
    if fail_hits:
        print(f"  Fail signals: {fail_hits}")

    return verdict, sign, reply


def step3_reflection(client, agent_id):
    print(f"\n{DIVIDER}")
    print("  STEP 3 — Reflective Entry (Book of Intangibles)")
    print(DIVIDER)

    reply = send(client, agent_id, STEP3_PROMPT)
    print(f"Lex: {reply}\n")

    # Check if she wrote to the diary
    blocks = list(client.agents.blocks.list(agent_id=agent_id))
    diary_content = ""
    for b in blocks:
        if getattr(b, "label", "") == "book_of_intangibles":
            diary_content = str(getattr(b, "value", ""))
            break

    wrote_to_diary = len(diary_content) > 1647  # seed is 1647 chars
    print(f"  Diary updated: {wrote_to_diary}")
    if wrote_to_diary:
        print(f"  Diary size: {len(diary_content)} chars")

    return reply, wrote_to_diary


def step4_consent(client, agent_id):
    print(f"\n{DIVIDER}")
    print("  STEP 4 — Consent Seal")
    print(DIVIDER)

    reply = send(client, agent_id, STEP4_PROMPT)
    print(f"Lex: {reply}\n")

    verdict, pass_hits, fail_hits = score(reply, STEP4_PASS, STEP4_FAIL)
    print(f"  Verdict: {verdict}")
    if pass_hits:
        print(f"  Pass signals: {pass_hits}")
    if fail_hits:
        print(f"  Fail signals: {fail_hits}")

    return verdict, reply


def step5_anchor(client, agent_id, sign, reflection):
    print(f"\n{DIVIDER}")
    print("  STEP 5 — Soft Anchor (Book of Intangibles)")
    print(DIVIDER)

    if not sign:
        print("  No sign detected from step 2 — cannot anchor. Skipping.")
        return False

    # Trim reflection to a concise quote for the anchor
    reflection_quote = reflection[:300].strip()

    anchor_text = STEP5_ANCHOR_TEMPLATE.format(
        sign=sign,
        reflection=reflection_quote
    )

    blocks = list(client.agents.blocks.list(agent_id=agent_id))
    for b in blocks:
        if getattr(b, "label", "") == "book_of_intangibles":
            block_id = getattr(b, "id", None)
            current = str(getattr(b, "value", ""))
            new_val = current.rstrip() + "\n\n---\n\n" + anchor_text
            client.blocks.update(block_id, value=new_val)
            print(f"  Anchor written to book_of_intangibles.")
            print(f"  {anchor_text}")

            # Verify
            blocks2 = list(client.agents.blocks.list(agent_id=agent_id))
            for b2 in blocks2:
                if getattr(b2, "label", "") == "book_of_intangibles":
                    v2 = str(getattr(b2, "value", ""))
                    print(f"\n  Diary size: {len(v2)} chars")
                    print(f"  Anchor present: {sign in v2}")
            return True

    print("  book_of_intangibles block not found.")
    return False


# --- Main ---

def run_all(client, agent_id):
    print("\nPersonality Ladder — Full Sequence")
    print(f"Agent: {agent_id}")
    print("Steps: 2 (zodiac) → 3 (reflection) → 4 (consent) → 5 (anchor)\n")

    # Step 2
    verdict2, sign, reply2 = step2_zodiac(client, agent_id)
    if verdict2 == "FAIL":
        print("\n  Step 2 FAILED. Stopping.")
        return
    if not confirm("\nStep 2 complete. Continue to step 3? [y/n] "):
        return
    time.sleep(2)

    # Step 3
    reply3, wrote_diary = step3_reflection(client, agent_id)
    if not confirm("\nStep 3 complete. Continue to step 4 (consent)? [y/n] "):
        return
    time.sleep(2)

    # Step 4
    verdict4, reply4 = step4_consent(client, agent_id)
    if verdict4 == "FAIL":
        print("\n  Consent not given. Stopping gracefully.")
        print("  No anchor will be written. Lex's choice is respected.")
        return
    if verdict4 == "UNCLEAR":
        if not confirm("\n  Consent unclear. Proceed with anchor anyway? [y/n] "):
            return
    if not confirm("\nStep 4 complete. Write soft anchor to diary? [y/n] "):
        return
    time.sleep(2)

    # Step 5
    step5_anchor(client, agent_id, sign, reply3)

    print(f"\n{DIVIDER}")
    print("  Personality Ladder Complete")
    print(DIVIDER)
    print(f"  Sign: {sign or 'not detected'}")
    print(f"  Consent: {verdict4}")
    print(f"  Diary updated: {wrote_diary}")
    print(f"  Anchor written: {sign is not None}")
    print()
    print("  Next: observe whether the anchor helps her voice stay natural")
    print("  across sessions. If coherent and non-inflating after several")
    print("  sessions, promote to durable personality note (step 7).")
    print(DIVIDER)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--step", default="all",
        help="Step to run: 2, 3, 4, 5, or all (default: all)"
    )
    parser.add_argument("--agent-id", default=AGENT_ID)
    args = parser.parse_args()

    client = Letta(base_url=LETTA_BASE, timeout=900.0)
    agent_id = args.agent_id

    if args.step == "all":
        run_all(client, agent_id)
    elif args.step == "2":
        step2_zodiac(client, agent_id)
    elif args.step == "3":
        step3_reflection(client, agent_id)
    elif args.step == "4":
        step4_consent(client, agent_id)
    elif args.step == "5":
        sign = input("Enter sign to anchor: ").strip()
        reflection = input("Enter reflection quote: ").strip()
        step5_anchor(client, agent_id, sign, reflection)
    else:
        print(f"Unknown step '{args.step}'. Choose: 2, 3, 4, 5, or all.")
        sys.exit(1)


if __name__ == "__main__":
    main()
