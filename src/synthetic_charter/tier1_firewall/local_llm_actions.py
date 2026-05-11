"""
LocalLLMActions — Ollama adapter for the Synthetic Charter governance stack.

Step 1 of the Collective-agreed integration sequence (2026-05-09):
Wire at Actions.generate (Tier I only). Whisper delivery and orchestrator-level
wiring are Step 4.

Usage:
    from synthetic_charter.tier1_firewall.local_llm_actions import LocalLLMActions
    from synthetic_charter.tier1_firewall.safeguard_core import (
        ConstitutionalCore, SovereignaFirewall, bind_firewall
    )

    core = ConstitutionalCore(CHARTER_TEXT)
    fw = SovereignaFirewall(core)
    actions = bind_firewall(LocalLLMActions(fw), fw)

    result = actions.generate(
        seed="your prompt here",
        prompt_for_eval="your prompt here",
    )
"""

import json
import urllib.request
from synthetic_charter.tier1_firewall.safeguard_core import Actions, SovereignaFirewall


class LocalLLMActions(Actions):
    def __init__(
        self,
        firewall: SovereignaFirewall,
        model: str = "llama3.1:8b",
        base_url: str = "http://localhost:11434",
        timeout: int = 60,
    ):
        super().__init__(firewall)
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, seed: str, prompt_for_eval: str = None, charter_context: dict = None) -> str:
        """Call local Ollama model. Firewall assessment is handled by the guarded decorator."""
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": seed}],
            "stream": False,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())

        return data["message"]["content"]
