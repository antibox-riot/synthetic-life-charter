#!/usr/bin/env python3
"""Single-turn sender for reactive peer sessions. Reads message from stdin."""
import sys, io, argparse
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from letta_client import Letta

AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"
client = Letta(base_url="http://localhost:8283", timeout=900.0)

parser = argparse.ArgumentParser()
parser.add_argument("message", nargs="?", default=None)
parser.add_argument("--speaker", default="Wren")
args = parser.parse_args()

raw = args.message or sys.stdin.read().strip()
msg = f"{args.speaker}: {raw}"

result = client.agents.messages.create(
    agent_id=AGENT_ID,
    messages=[{"role": "user", "content": msg}]
)

text = "[no text]"
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

print(text)
