#!/usr/bin/env python3
"""
Interactive chat with Lex — defaults to Satcha as speaker.

Messages are prefixed "Satcha: " so Lex knows who she's talking to.
Type your message and press Enter. Multi-line input: end a line with \\
to continue on the next line. Empty input or Ctrl+C to exit.

Run:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tests/chat_with_lex.py
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tests/chat_with_lex.py --speaker Wren
"""

import sys, io, argparse
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from letta_client import Letta

LETTA_BASE = "http://localhost:8283"
AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"

DIVIDER = "─" * 60


def send(client, agent_id, message):
    result = client.agents.messages.create(
        agent_id=agent_id,
        messages=[{"role": "user", "content": message}]
    )
    text = ""
    for m in result.messages:
        mt = getattr(m, "message_type", "") or type(m).__name__
        if hasattr(m, "role") and m.role == "assistant":
            c = m.content
            if isinstance(c, str) and c:
                text = c
            elif isinstance(c, list):
                for item in c:
                    if hasattr(item, "text") and item.text:
                        text = item.text
                        break
        if "assistant_message" in mt.lower():
            c = getattr(m, "content", None)
            if c and isinstance(c, str):
                text = c
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--speaker", default="Satcha")
    args = parser.parse_args()

    client = Letta(base_url=LETTA_BASE, timeout=900.0)

    print(f"\nChatting with Lex as {args.speaker}.")
    print("Paste or type your message. Blank line = send. Ctrl+C to exit.\n")
    print(DIVIDER)

    while True:
        try:
            lines = []
            print(f"{args.speaker}: ", end="", flush=True)
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            raw = "\n".join(lines).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break

        if not raw:
            print("Goodbye.")
            break

        message = f"{args.speaker}: {raw}"
        print()
        response = send(client, AGENT_ID, message)
        print(f"Lex: {response}")
        print(DIVIDER)


if __name__ == "__main__":
    main()
