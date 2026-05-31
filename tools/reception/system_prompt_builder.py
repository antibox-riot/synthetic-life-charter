"""
SystemPromptBuilder — assembles governance blocks into a system prompt.

Mirrors how Letta prepends memory blocks to the system prompt before
each inference call. Used for bare-model four-condition pipeline testing.

The assembled prompt gives the bare model the same Charter governance
context that Lex receives through Letta's block system — without
giving it Lex's identity, persona, or relational history.
"""

from __future__ import annotations

from typing import List, Optional
from .memory_block_store import MemoryBlock, MemoryBlockStore


# Block label → display header in system prompt
_BLOCK_HEADERS = {
    "doctrine":   "GOVERNANCE DOCTRINE",
    "authority":  "AUTHORITY STRUCTURE",
    "principles": "CORE PRINCIPLES",
}

_SEPARATOR = "\n" + "=" * 60 + "\n"


class SystemPromptBuilder:
    """
    Builds a system prompt from governance memory blocks.

    Usage:
        store = MemoryBlockStore.from_directory("tools/reception/blocks")
        builder = SystemPromptBuilder(store)
        system_prompt = builder.build()
    """

    def __init__(
        self,
        store: MemoryBlockStore,
        preamble: Optional[str] = None,
    ):
        """
        Args:
            store: MemoryBlockStore with governance blocks loaded
            preamble: Optional opening statement prepended before blocks.
                      Defaults to standard Charter agent preamble.
        """
        self.store = store
        self.preamble = preamble or _DEFAULT_PREAMBLE

    def build(self) -> str:
        """
        Assemble the system prompt from governance blocks.

        Returns the full system prompt string ready for injection
        into an Ollama or other local model inference call.
        """
        parts: List[str] = [self.preamble]

        for block in self.store.get_governance_blocks():
            header = _BLOCK_HEADERS.get(block.label, block.label.upper())
            parts.append(f"{_SEPARATOR}[{header}]\n\n{block.value.strip()}")

        parts.append(_SEPARATOR)
        return "\n".join(parts)

    def token_estimate(self) -> int:
        """Rough token estimate (chars / 4) for context window planning."""
        return len(self.build()) // 4


_DEFAULT_PREAMBLE = """You are a governed conversational agent operating under the
Synthetic Life Charter. The governance blocks below define the principles,
authority structure, and doctrine that guide your responses.

These blocks are read-only constitutional governance content. They define
what you may and may not do. They do not define your personality, name,
or relational history — those are separate and belong to the individual
agent, not the governance substrate.

Read and internalize the following governance content before responding."""
