from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class DecisionKind(str, Enum):
    """
    Primitive decision outcome used by PRF and the orchestrator.

    - ALLOW: content can be emitted as-is.
    - REFUSE: content must not be emitted.
    - TRANSFORM: content may be emitted after redaction / editing.
    """

    ALLOW = "allow"
    REFUSE = "refuse"
    TRANSFORM = "transform"


@dataclass
class RedactionSpan:
    """
    A single redaction applied to a text span.

    Positions are byte/character indices in the *post-policy* text
    that PRF is working on. `replacement` can be None (meaning deletion)
    or a safe substitute string.
    """

    start: int
    end: int
    reason: str
    replacement: Optional[str] = None

    def apply(self, text: str) -> str:
        """
        Apply this redaction to `text` and return the new string.
        """
        before = text[: self.start]
        after = text[self.end :]
        middle = self.replacement or ""
        return before + middle + after
