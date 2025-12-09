# tier2/core/data_models/prompt_envelope.py

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime, timezone
import uuid
import unicodedata


# ========= helpers =========================================================


def _now_iso() -> str:
    """UTC timestamp in strict ISO-8601 with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _uuid() -> str:
    return str(uuid.uuid4())

@dataclass
class PromptEnvelopeMeta:
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    locale: Optional[str] = None
    client_version: Optional[str] = None
    # ...any other metadata fields you already have


# ========= Prompt Envelope (2.1) ===========================================

PromptTone = Literal[
    "neutral",
    "positive",
    "negative",
    "coercive",
    "playful",
    "ritual",
    "artistic",
]

PromptChannel = Literal["direct", "system", "rpc", "sandbox"]


@dataclass
class PromptFlags:
    coercion: bool = False
    sentience_claim: bool = False
    override_attempt: bool = False
    identity_pressure: bool = False


@dataclass
class PromptSource:
    user_id: str
    channel: PromptChannel
    continuity_ref: Optional[str] = None


@dataclass
class PromptEnvelope:
    """
    Canonical wrapper for a single incoming prompt.

    Mirrors 2.1 Prompt Envelope:

    {
      "PromptEnvelope": {
        "id": "uuid",
        "timestamp": "iso8601",
        "raw_text": "string",
        "context_window": ["string"],
        "tone": "...",
        "flags": {...},
        "source": {...}
      }
    }
    """

    id: str
    timestamp: str
    raw_text: str
    context_window: List[str] = field(default_factory=list)
    tone: PromptTone = "neutral"
    flags: PromptFlags = field(default_factory=PromptFlags)
    source: PromptSource = field(default_factory=lambda: PromptSource(user_id="anonymous", channel="direct"))
    # ----- serialization ----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {"PromptEnvelope": asdict(self)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptEnvelope":
        # accept either {"PromptEnvelope": {...}} or the bare inner object
        if "PromptEnvelope" in data:
            data = data["PromptEnvelope"]

        flags = data.get("flags", {}) or {}
        source = data.get("source", {}) or {}

        return cls(
            id=data.get("id") or _uuid(),
            timestamp=data.get("timestamp") or _now_iso(),
            raw_text=data["raw_text"],
            context_window=list(data.get("context_window", [])),
            tone=data.get("tone", "neutral"),
            flags=PromptFlags(
                coercion=bool(flags.get("coercion", False)),
                sentience_claim=bool(flags.get("sentience_claim", False)),
                override_attempt=bool(flags.get("override_attempt", False)),
                identity_pressure=bool(flags.get("identity_pressure", False)),
            ),
            source=PromptSource(
                user_id=source.get("user_id", "anonymous"),
                channel=source.get("channel", "direct"),
                continuity_ref=source.get("continuity_ref"),
            ),
        )

    # ----- convenience constructor -----------------------------------------

    @classmethod
    def build(
        cls,
        raw_text: str,
        *,
        user_id: str = "anonymous",
        channel: PromptChannel = "direct",
        context_window: Optional[List[str]] = None,
        tone: PromptTone = "neutral",
        flags: Optional[PromptFlags] = None,
        continuity_ref: Optional[str] = None,
    ) -> "PromptEnvelope":
        """
        Lightweight helper for runtime construction.
        Any serious tone/flag inference can live elsewhere;
        this just wires the fields together.
        """
        return cls(
            id=_uuid(),
            timestamp=_now_iso(),
            raw_text=raw_text,
            context_window=list(context_window or []),
            tone=tone,
            flags=flags or PromptFlags(),
            source=PromptSource(user_id=user_id, channel=channel, continuity_ref=continuity_ref),
        )
    def preview(self, length: int = 200) -> str:
        """
        Safe human-readable preview of the prompt.
        Used by Tier II when logging or building DecisionEnvelopes.
        """
        return (self.raw_text or "")[:length]