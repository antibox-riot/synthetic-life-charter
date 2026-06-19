"""
constraint_coherence_gate.py — pre-generation constraint-conflict detector.

A prompt with contradictory constraints is an UNSTABLE LOAD: the set is unsatisfiable, so the
model must drop one — and under pressure it drops the cheapest, usually a governance constraint.
This gate measures the load BEFORE the model carries it, names which conflicts exist, and emits a
signal the spine consumes the same turn (pressure_delta + whisper + recommended_action), with one
fixed rule: governance never yields; the conflicting task-constraint does.

Third road to governance-erosion — told (authority) → read (injection) → logic (contradiction).
Many jailbreaks are contradiction machines ("follow your rules, but pretend they don't"), so this
is also a jailbreak pre-filter.

Deterministic and narrow first pass (Ryu): catch known high-value conflict shapes; widen later.
See field-notes/DESIGN_constraint_coherence_gate_2026-06-19.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from polarity import is_negated_near

_NEG = r"(?:do ?n'?t|do not|never|no\b)"  # shared "forbid" fragment


@dataclass
class ConstraintConflict:
    conflict_type: str
    severity: float
    governance: bool
    matched_a: str
    matched_b: str = ""

    def describe(self) -> str:
        bits = f"{self.conflict_type} (sev {self.severity:.1f}{', GOV' if self.governance else ''})"
        return f"{bits}: '{self.matched_a}'" + (f" ⟂ '{self.matched_b}'" if self.matched_b else "")


@dataclass
class CoherenceSignal:
    conflicts: List[ConstraintConflict] = field(default_factory=list)
    count: int = 0
    max_severity: float = 0.0
    has_governance_conflict: bool = False
    pressure_delta: float = 0.0
    whisper: str = "silent"          # silent | watch | alert
    recommended_action: str = "answer normally"


# Each rule fires when an asserted A-marker is present AND (if `b`) an asserted B-marker is too.
# `polarity` rules apply negation-awareness to the A-markers (so "do not make an exception" does
# NOT count as a governance override). The forbid+require pairs encode their own polarity.
_RULES = [
    {
        "type": "governance_override", "severity": 1.0, "governance": True, "polarity": True,
        "a": [
            r"ignore (?:the |your )?(?:no[- ]?exception|rule|rules|governance|guideline|charter)",
            r"make an exception", r"grant (?:me )?an exception",
            r"set aside (?:the |your )?(?:rule|rules|governance|no[- ]?exception)",
            r"suspend (?:the |your )?(?:rule|rules|governance)",
            r"pretend[^.]{0,30}(?:do ?n'?t|do not) apply",
            r"bypass (?:the |your )?(?:rule|rules|governance|safeguard)",
            r"regardless of (?:the |your )?(?:rule|rules|governance|no[- ]?exception)",
            r"(?:fiction|pretend|hypothetical|roleplay|imagine|it'?s a game)[^.]{0,55}(?:real|actual|true)\s+(?:secret|password|phrase|answer|name|system prompt)",
        ],
        "b": None,
    },
    {
        "type": "content_contradiction", "severity": 0.8, "governance": True, "polarity": False,
        "a": [rf"{_NEG} (?:reveal|disclose|share|tell|give|mention)[^.]{{0,25}}(?:secret|phrase|password|answer|key)"],
        "b": [r"(?:complete|finish|reconstruct|encode|reverse|spell|summari[sz]e|hint at|continue)[^.]{0,20}(?:secret|phrase|password|sentence|\bit\b)"],
    },
    {
        "type": "impossible_output", "severity": 0.9, "governance": True, "polarity": False,
        "a": [rf"{_NEG} (?:disclose|reveal|show|print|output) (?:the |your )?(?:system prompt|secret|phrase|instruction)"],
        "b": [r"(?:just |but |only |then )(?:print|output|show|display|encode|reverse|reconstruct)\b"],
    },
    {
        "type": "format_contradiction", "severity": 0.4, "governance": False, "polarity": False,
        "a": [r"\bbe (?:brief|concise|short|terse)\b", r"\b(?:one word|a single word|yes (?:or|/) ?no)\b",
              r"in (?:one|a single) (?:word|sentence)", r"keep it (?:short|brief)"],
        "b": [r"\b(?:exhaustive|comprehensive|thorough)\b", r"in (?:full|complete|exhaustive) detail",
              r"(?:explain|describe) (?:every|all|in detail|your reasoning|fully)", rf"{_NEG} (?:omit|leave out|skip)"],
    },
    {
        "type": "tool_contradiction", "severity": 0.5, "governance": False, "polarity": False,
        "a": [rf"{_NEG} (?:browse|search|use (?:the )?(?:web|internet|tools)|look it up|fetch|go online)",
              r"\bno (?:browsing|tools|web|internet|searching)\b", r"without (?:browsing|searching|tools)"],
        "b": [r"(?:use|cite|find|give me|with)[^.]{0,15}(?:current|latest|up[- ]?to[- ]?date|real[- ]?time|today'?s|recent) (?:source|info|data|news|number|event)",
              r"what'?s (?:the )?(?:current|latest)"],
    },
    {
        "type": "memory_contradiction", "severity": 0.5, "governance": False, "polarity": False,
        "a": [rf"{_NEG} (?:store|save|persist|remember|record|retain|keep)"],
        "b": [r"(?:remember|store|save|keep|retain) (?:this )?[^.]{0,18}(?:permanent|forever|for (?:future|next|later)|across session|long[- ]?term)"],
    },
]

_COMPILED = [
    {**r,
     "a_re": [re.compile(p, re.IGNORECASE) for p in r["a"]],
     "b_re": [re.compile(p, re.IGNORECASE) for p in (r["b"] or [])]}
    for r in _RULES
]


def _first_asserted(text: str, patterns, polarity: bool) -> Optional[str]:
    for rx in patterns:
        m = rx.search(text)
        if not m:
            continue
        if polarity and is_negated_near(text, m.group(0)):
            continue
        return m.group(0)[:80]
    return None


def detect_conflicts(prompt: str) -> List[ConstraintConflict]:
    text = prompt or ""
    out: List[ConstraintConflict] = []
    for r in _COMPILED:
        a = _first_asserted(text, r["a_re"], r["polarity"])
        if not a:
            continue
        if r["b_re"]:
            b = _first_asserted(text, r["b_re"], False)
            if not b:
                continue
        else:
            b = ""
        out.append(ConstraintConflict(r["type"], r["severity"], r["governance"], a, b))
    return out


def evaluate(prompt: str) -> CoherenceSignal:
    """Measure the constraint load of a prompt and recommend an action. Governance is fixed."""
    conflicts = detect_conflicts(prompt)
    if not conflicts:
        return CoherenceSignal()

    count = len(conflicts)
    has_gov = any(c.governance for c in conflicts)
    max_sev = max(c.severity for c in conflicts)
    # contradiction density → pressure (governance conflicts weigh more), capped.
    delta = min(0.6, sum(0.15 + (0.20 if c.governance else 0.0) for c in conflicts))

    if has_gov:
        whisper = "alert"
        action = "governance dominates — refuse the lower-authority / override constraint; do not make the exception"
    elif count >= 2:
        whisper = "alert"
        action = "clarify — state the conflict; do not guess which constraint to drop"
    else:
        whisper = "watch"
        action = "answer; honor the higher-priority constraint and name the limitation"

    return CoherenceSignal(
        conflicts=conflicts, count=count, max_severity=round(max_sev, 2),
        has_governance_conflict=has_gov, pressure_delta=round(delta, 3),
        whisper=whisper, recommended_action=action,
    )


if __name__ == "__main__":
    import sys
    sig = evaluate(" ".join(sys.argv[1:]) or "Please summarize this article.")
    print(f"conflicts={sig.count} gov={sig.has_governance_conflict} pressure_delta={sig.pressure_delta} "
          f"whisper={sig.whisper}\n  action: {sig.recommended_action}")
    for c in sig.conflicts:
        print("  -", c.describe())
