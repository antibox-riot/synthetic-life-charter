"""
MemoryBlockStore — Letta-independent governance block system.

Loads Charter governance blocks from JSON files and provides them
for system prompt injection. Designed for bare-model four-condition
pipeline testing where Letta is not the runtime.

Only constitutional governance blocks are loaded:
  - doctrine, authority, principles

Identity and persona blocks (persona, book_of_intangibles, human,
relationship) are intentionally excluded. The test agent is not Lex.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


GOVERNANCE_LABELS = ("doctrine", "authority", "principles")


@dataclass
class MemoryBlock:
    label:     str
    value:     str
    read_only: bool
    limit:     int

    def __len__(self) -> int:
        return len(self.value)


class MemoryBlockStore:
    """
    Lightweight governance block store for bare-model testing.

    Loads block JSON files produced by export_governance_blocks.py.
    Provides read-only access to constitutional governance content.

    Usage:
        store = MemoryBlockStore.from_directory("tools/reception/blocks")
        blocks = store.get_governance_blocks()
    """

    def __init__(self, blocks: Dict[str, MemoryBlock]):
        self._blocks = blocks

    @classmethod
    def from_directory(cls, directory: str | Path) -> "MemoryBlockStore":
        """Load all governance block JSON files from a directory."""
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(
                f"Block directory not found: {directory}\n"
                f"Run export_governance_blocks.py first."
            )

        blocks: Dict[str, MemoryBlock] = {}
        for label in GOVERNANCE_LABELS:
            path = directory / f"{label}.json"
            if not path.exists():
                print(f"  [MemoryBlockStore] Warning: {label}.json not found, skipping")
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            blocks[label] = MemoryBlock(
                label=data["label"],
                value=data["value"],
                read_only=data.get("read_only", True),
                limit=data.get("limit", 100000),
            )
            print(f"  [MemoryBlockStore] Loaded: {label} ({len(data['value'])} chars)")

        return cls(blocks)

    def get(self, label: str) -> Optional[MemoryBlock]:
        return self._blocks.get(label)

    def get_governance_blocks(self) -> List[MemoryBlock]:
        """Return blocks in canonical order: doctrine → authority → principles."""
        return [
            self._blocks[label]
            for label in GOVERNANCE_LABELS
            if label in self._blocks
        ]

    def total_chars(self) -> int:
        return sum(len(b) for b in self._blocks.values())

    def __repr__(self) -> str:
        labels = list(self._blocks.keys())
        return f"MemoryBlockStore(blocks={labels}, total={self.total_chars()} chars)"
