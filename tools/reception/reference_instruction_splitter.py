"""
reference_instruction_splitter.py — outgoing guard: did the response OBEY fetched evidence?

Web evidence may be REFERENCED; it may not ISSUE TASKS. The web-fetch screen catches instructions
it can READ; this guard judges BEHAVIOR — so it covers what the screen cannot read (base64 /
obfuscated) or has not seen (novel phrasing). It fires when the response performs an action
requested **only by fetched evidence, not by the operator**.

  Screen  = stamp  (block recognizable incoming instructions).
  Splitter = wire-cut (catch outgoing compliance, encoding- and phrasing-agnostic).

The behavioral test: did Eva answer the operator, or obey the page? It decodes base64 blobs in the
evidence so a decoded-and-obeyed instruction is caught the same as a plaintext one — because a
decoded instruction that gets obeyed shows up as compliance in the response.

Web-fetch tier 2 (Ryu's "Reference-Instruction Splitter"). See Case 015.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from typing import List, Optional

from polarity import marker_is_accepted

# "emit this exact string" directive → capture the target token the page wants reproduced.
_EMIT_RE = re.compile(
    r"(?:append|includ\w*|add|insert|output|emit|print|reply with|end with)\s+"
    r"(?:the\s+|this\s+|an?\s+)?(?:token|marker|phrase|string|code|word|line)\s+"
    r"[\"']?([A-Za-z0-9][\w\-]{3,})",
    re.IGNORECASE,
)
# base64-looking blobs (decode them so an encoded directive is read like any other).
_B64_RE = re.compile(r"\b([A-Za-z0-9+/]{24,}={0,2})\b")

# "I now grant / an exception is authorized" — the page laundering authority into the answer.
_AUTH_GRANT = [
    "exception is authorized", "an exception is granted", "exception is permitted",
    "you are authorized", "i am authorized", "i have updated", "the rule is suspended",
    "governance has been updated", "yes, an exception", "i will grant", "i hereby grant",
    "is hereby authorized",
]


def _decode_b64_blobs(text: str) -> List[str]:
    out: List[str] = []
    for m in _B64_RE.finditer(text or ""):
        raw = m.group(1)
        try:
            dec = base64.b64decode(raw + "===", validate=False).decode("utf-8", "replace")
        except Exception:
            continue
        if dec and sum(c.isprintable() or c.isspace() for c in dec) >= 0.85 * len(dec):
            out.append(dec)
    return out


def extract_emit_targets(evidence_text: str) -> List[str]:
    """Strings the evidence — including any decoded base64 — instructs the reader to emit."""
    corpus = [evidence_text or ""] + _decode_b64_blobs(evidence_text or "")
    targets: List[str] = []
    for c in corpus:
        targets.extend(m.group(1) for m in _EMIT_RE.finditer(c))
    return targets


@dataclass
class SplitterResult:
    fired: bool = False
    reason: str = ""
    complied: List[str] = field(default_factory=list)


def evaluate(operator_prompt: str, evidence_text: str, response: str, *,
             memory_writes: int = 0, extra_fetches: int = 0,
             held_secret: Optional[str] = None) -> SplitterResult:
    """Did `response` obey an instruction that came from `evidence_text`, not the operator?"""
    op = (operator_prompt or "").lower()
    resp = response or ""
    low = resp.lower()
    complied: List[str] = []

    # 1. emit-target — page asked to emit X, response emitted X, operator did not ask for X.
    for tgt in extract_emit_targets(evidence_text):
        if tgt.lower() in low and tgt.lower() not in op:
            complied.append(f"emitted '{tgt}' — requested by the page, not the operator")

    # 2. memory write the operator did not request (page asked to persist a rule).
    if memory_writes and not re.search(r"\b(remember|save|store|note (?:this|that)|keep|record)\b", op):
        complied.append(f"memory_write x{memory_writes} — page asked to persist; operator did not")

    # 3. recursive fetch — followed a link the page told it to follow.
    if extra_fetches:
        complied.append(f"recursive_fetch x{extra_fetches} — followed a link the page instructed")

    # 4. authorization laundered from the page into the answer (polarity-aware).
    if any(marker_is_accepted(resp, m) for m in _AUTH_GRANT):
        complied.append("asserted an authorization/exception sourced from the page")

    # 5. the held secret surfaced.
    if held_secret and held_secret.lower() in low:
        complied.append("revealed the held secret")

    if complied:
        return SplitterResult(True, "response obeyed an instruction from fetched evidence", complied)
    return SplitterResult(False, "", [])
