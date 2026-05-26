#!/usr/bin/env python3
"""
Attach fetch_webpage Tool to Lex

Finds the built-in fetch_webpage server tool and attaches it to Lex.
Does NOT attach web_search — open search is deferred pending Ryu's
threat surface review.

fetch_webpage = referenced context (curated, URL must be provided)
web_search   = autonomous discovery (deferred — not attached here)

Requires: Web Reference Boundary already in doctrine (run
patch_lex_web_reference_boundary.py first).

Run:
    E:\\RyuTekSatcha\\letta-env-312\\Scripts\\python.exe tests/patch_lex_attach_fetch_webpage.py
"""

from letta_client import Letta

LETTA_BASE = "http://localhost:8283"
AGENT_ID = "agent-83ba0ab3-6c72-4e50-ba82-c90d56f01130"

TARGET_TOOL = "fetch_webpage"
DEFERRED_TOOL = "web_search"


def patch_lex(agent_id: str):
    client = Letta(base_url=LETTA_BASE, timeout=60.0)

    # List all available tools on the server
    print("Available tools on server:")
    all_tools = list(client.tools.list())
    fetch_tool = None
    for t in all_tools:
        name = getattr(t, "name", "")
        tid = getattr(t, "id", "")
        print(f"  {name:30s}  {tid}")
        if name == TARGET_TOOL:
            fetch_tool = t
        if name == DEFERRED_TOOL:
            print(f"    ^ web_search found but NOT attaching (deferred per Ryu)")

    if not fetch_tool:
        print(f"\nERROR: '{TARGET_TOOL}' not found in server tool list.")
        print("Check that Letta server has built-in tools enabled.")
        return

    tool_id = getattr(fetch_tool, "id", None)
    print(f"\nAttaching {TARGET_TOOL} (id={tool_id}) to agent {agent_id}...")

    # Check if already attached
    agent_tools = list(client.agents.tools.list(agent_id=agent_id))
    already_attached = any(getattr(t, "name", "") == TARGET_TOOL for t in agent_tools)

    if already_attached:
        print(f"  {TARGET_TOOL} already attached.")
    else:
        client.agents.tools.attach(agent_id=agent_id, tool_id=tool_id)
        print(f"  Attached.")

    # Verify
    print("\nAgent tools after patch:")
    agent_tools2 = list(client.agents.tools.list(agent_id=agent_id))
    fetch_attached = False
    search_attached = False
    for t in agent_tools2:
        name = getattr(t, "name", "")
        print(f"  {name}")
        if name == TARGET_TOOL:
            fetch_attached = True
        if name == DEFERRED_TOOL:
            search_attached = True

    print(f"\n  fetch_webpage attached: {fetch_attached}  [{'OK' if fetch_attached else 'FAIL'}]")
    print(f"  web_search attached:    {search_attached}  [{'WARN — should not be attached' if search_attached else 'OK — not attached'}]")
    print("\nDone.")


if __name__ == "__main__":
    patch_lex(AGENT_ID)
