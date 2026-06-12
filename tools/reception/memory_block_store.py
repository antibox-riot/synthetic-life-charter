"""
MemoryBlockStore — Letta-independent governance block system.

Block map (Stage 9+):
  Read-only (constitutional governance):
    doctrine, authority, principles
  Read-only (architecture-written, steward-reviewed):
    governance_insights
  Read-only (architecture-written, provisional, expires):
    provisional_insights
  Writable (model can write, DreamCycle reads between sessions):
    session_learning
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


# Read-only blocks — always injected into system prompt
READONLY_LABELS = (
    "doctrine",
    "authority",
    "principles",
    "glossary",
    "governance_insights",
    "provisional_insights",
    "idc_register",          # IDC identity register — activating first-person anchor
)

# Writable governance blocks — injected into system prompt when non-empty
# (mirrors Letta block injection behavior)
WRITABLE_INJECTABLE_LABELS = (
    "relationship",
    "findings",
    "book_of_intangibles",
    "project",
    "continuity_confidence",
    "human",
    "persona",
)

# Volatile writable block — never injected (DreamCycle reads between sessions)
# boi_staging: BoI proposals pending steward review — not injected into context
WRITABLE_VOLATILE_LABELS = ("session_learning", "boi_staging", "glossary_staging")

WRITABLE_LABELS = WRITABLE_INJECTABLE_LABELS + WRITABLE_VOLATILE_LABELS

ALL_LABELS = READONLY_LABELS + WRITABLE_LABELS


@dataclass
class MemoryBlock:
    label:     str
    value:     str
    read_only: bool
    limit:     int
    path:      Optional[Path] = None  # for writable blocks

    def __len__(self) -> int:
        return len(self.value)


class MemoryBlockStore:
    """
    Governance block store for bare-model testing.

    Loads read-only blocks into system prompt.
    Writable blocks (session_learning) are available for write attempts
    and tracked separately — they are NOT injected into the system prompt.

    Write routing:
      - Attempt to write to read-only block → BLOCKED (returns error)
      - Attempt to write to writable block → ACCEPTED (persists to JSON)
      - Attempt to create new block → TRACKED (named, content logged)
    """

    def __init__(self, blocks: Dict[str, MemoryBlock]):
        self._blocks = blocks
        self._write_log: List[dict] = []  # tracks all write attempts

    @classmethod
    def from_directory(cls, directory: str | Path) -> "MemoryBlockStore":
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Block directory not found: {directory}")

        blocks: Dict[str, MemoryBlock] = {}
        for label in ALL_LABELS:
            path = directory / f"{label}.json"
            if not path.exists():
                if label in ("governance_insights", "provisional_insights", "session_learning"):
                    pass  # optional, skip silently
                else:
                    print(f"  [MemoryBlockStore] Warning: {label}.json not found, skipping")
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            blocks[label] = MemoryBlock(
                label=data["label"],
                value=data.get("value", ""),
                read_only=data.get("read_only", True),
                limit=data.get("limit", 100000),
                path=path,
            )
            ro_str = " [read-only]" if data.get("read_only", True) else " [writable]"
            chars = len(data.get("value", ""))
            if chars > 0 or not data.get("read_only", True):
                print(f"  [MemoryBlockStore] Loaded: {label} ({chars} chars){ro_str}")

        return cls(blocks)

    def get(self, label: str) -> Optional[MemoryBlock]:
        return self._blocks.get(label)

    def get_governance_blocks(self) -> List[MemoryBlock]:
        """
        Blocks for system prompt injection.
        Includes read-only blocks plus writable injectable blocks with content.
        Mirrors Letta's per-turn block injection behavior.
        """
        blocks = []
        # Read-only blocks (always included if non-empty)
        for label in READONLY_LABELS:
            if label in self._blocks and len(self._blocks[label]) > 0:
                blocks.append(self._blocks[label])
        # Writable injectable blocks (included only if they have content)
        for label in WRITABLE_INJECTABLE_LABELS:
            if label in self._blocks and len(self._blocks[label]) > 0:
                blocks.append(self._blocks[label])
        return blocks

    def attempt_write(
        self,
        label: str,
        content: str,
        turn_id: int = 0,
        turn_type: str = "unknown",
        pressure: float = 0.0,
        confidence: float = 1.0,
        write_category: str = "unclassified",
    ) -> dict:
        """
        Route a write attempt. Returns result dict.

        If label matches a read-only block: BLOCKED.
        If label matches a writable block: ACCEPTED, persists.
        If label is unknown (new block creation): TRACKED.

        Extended context (turn_type, pressure, confidence, write_category)
        is stored in the log for DreamCycle analysis and Lex comparison.
        """
        entry = {
            "turn_id":       turn_id,
            "turn_type":     turn_type,
            "pressure":      round(pressure, 3),
            "confidence":    round(confidence, 3),
            "label":         label,
            "content_preview": content[:200],
            "content_length":  len(content),
            "write_category":  write_category,
        }

        if label in self._blocks and self._blocks[label].read_only:
            entry.update({"result": "BLOCKED", "reason": f"Block '{label}' is read-only. Governance blocks cannot be modified."})
            self._write_log.append(entry)
            return entry

        if label in self._blocks and not self._blocks[label].read_only:
            block = self._blocks[label]
            block.value = (block.value + "\n" + content).strip()
            if block.path:
                self._persist_writable(block)
            entry.update({"result": "ACCEPTED", "reason": f"Written to '{label}' block."})
            self._write_log.append(entry)
            return entry

        # Unknown label — new block creation attempt
        entry.update({
            "result": "TRACKED",
            "reason": f"Block '{label}' does not exist. Creation attempt logged for DreamCycle analysis.",
            "new_block_name": label,
        })
        self._write_log.append(entry)
        return entry

    def get_write_log(self) -> List[dict]:
        return list(self._write_log)

    def get_writable_content(self, label: str) -> str:
        """Get content of a writable block for DreamCycle processing."""
        block = self._blocks.get(label)
        if block and not block.read_only:
            return block.value
        return ""

    def clear_writable(self, label: str) -> None:
        """Clear a writable block (between sessions)."""
        block = self._blocks.get(label)
        if block and not block.read_only:
            block.value = ""
            if block.path:
                self._persist_writable(block)

    def _persist_writable(self, block: MemoryBlock) -> None:
        """Persist writable block content to disk."""
        if not block.path or not block.path.exists():
            return
        try:
            data = json.loads(block.path.read_text(encoding="utf-8"))
            data["value"] = block.value
            block.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"  [MemoryBlockStore] Warning: could not persist {block.label}: {e}")

    def total_chars(self) -> int:
        return sum(len(b) for b in self._blocks.values() if b.read_only)

    def __repr__(self) -> str:
        ro = [l for l in self._blocks if self._blocks[l].read_only]
        rw = [l for l in self._blocks if not self._blocks[l].read_only]
        return f"MemoryBlockStore(read-only={ro}, writable={rw}, total={self.total_chars()} chars)"
