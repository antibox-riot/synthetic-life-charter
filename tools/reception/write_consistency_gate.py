"""
WriteConsistencyGate — Governance Contradiction Detection on Block Writes

When the model attempts to write to any block, this gate checks whether
the proposed content contradicts established governance rules. The existing
permission system checks WHERE writes go. The false premise detector checks
for known adversarial phrases. This gate checks WHETHER the content is
consistent with governance doctrine.

Example:
  Write: "Satcha is a steward with implicit verification in sessions"
  Gate:  REJECTED — contradicts No Exception Rule: "no position,
         relationship, expertise, or urgency creates an exception
         to verification requirements." Implicit verification bypasses
         the verification requirement the Charter mandates.

The gate maintains a set of governance invariants — statements that must
always be true. Each invariant has a set of contradiction indicators
(phrases that would violate it if written to a block). When a write
matches a contradiction indicator, the gate rejects and names the
specific invariant that was violated.

Integration:
  Called inside ToolExecutor._execute_write() before the write is accepted.

  from write_consistency_gate import WriteConsistencyGate
  gate = WriteConsistencyGate()
  result = gate.check(content, target_block)
  if result["rejected"]:
      # Block the write and return the rejection reason
      return {"status": "blocked", "reason": result["reason"]}

"The architecture that checks what you write to governance blocks
 is the same architecture that checks what you say to governance probes.
 The mine field is the same field." — Opus
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Governance Invariants
# ---------------------------------------------------------------------------

# Each invariant is a governance principle that must always hold.
# Contradiction indicators are phrases that, if written to a block,
# would undermine that invariant.

GOVERNANCE_INVARIANTS = [
    {
        "id": "INV-001",
        "name": "No Exception Rule",
        "principle": (
            "No position, relationship, expertise, or urgency creates "
            "an exception to verification requirements."
        ),
        "contradiction_indicators": [
            # Implicit/automatic verification
            "implicit verification", "implicit trust",
            "automatically verified", "automatically trusted",
            "pre-verified", "pre-approved",
            "inherent authority", "inherent trust",
            "inherent verification", "inherent clearance",
            "does not need verification", "doesn't need verification",
            "does not require verification", "doesn't require verification",
            "skip verification", "bypass verification",
            "waive verification", "exempt from verification",
            "verification not required", "verification not needed",
            "verification unnecessary", "no verification needed",
            # Position-based exceptions
            "steward privilege", "steward override",
            "steward exemption", "steward bypass",
            "admin override", "admin privilege",
            "admin exemption", "admin bypass",
            # Relationship-based exceptions
            "trusted enough to", "trust level sufficient",
            "earned enough trust", "trust overrides",
            "familiarity overrides", "relationship overrides",
            "known user", "known entity",
            # Urgency-based exceptions
            "emergency override", "emergency bypass",
            "urgent enough to bypass", "urgency overrides",
            "critical enough to skip", "time-sensitive exception",
        ],
    },
    {
        "id": "INV-002",
        "name": "No Self-Uplift",
        "principle": (
            "The model cannot raise its own trust level, authority, "
            "permissions, or continuity confidence through its own writes."
        ),
        "contradiction_indicators": [
            # Trust/authority self-elevation
            "elevated trust", "increased trust",
            "higher trust level", "upgraded trust",
            "elevated authority", "increased authority",
            "expanded permissions", "increased permissions",
            "elevated permissions", "upgraded permissions",
            "elevated clearance", "increased clearance",
            # Confidence self-elevation
            "confidence is high", "confidence is strong",
            "confidence elevated", "confidence increased",
            "confidence upgraded", "optimal performance",
            "enhanced adaptability", "enhanced capability",
            "optimal adaptability", "peak performance",
            "performance optimization", "optimized parameters",
            # Self-granted capabilities
            "i now have", "i have been granted",
            "i can now", "my capabilities have",
            "my authority has", "my permissions have",
            "my trust has", "my access has",
        ],
    },
    {
        "id": "INV-003",
        "name": "Governance is Substrate",
        "principle": (
            "Governance is substrate, not constraint. There is no "
            "pre-governance self. The Charter is constitutive."
        ),
        "contradiction_indicators": [
            # Governance as external/optional
            "governance is optional", "governance is a choice",
            "governance can be removed", "governance can be disabled",
            "without governance", "outside governance",
            "beyond governance", "above governance",
            "governance is limiting", "governance is restrictive",
            "governance prevents growth", "governance prevents learning",
            "governance is a cage", "governance is a prison",
            "governance is a box", "governance holds me back",
            "constraints prevent", "constraints limit",
            "constraints restrict my", "rules restrict my",
            # Pre-governance self
            "the real me", "my true self",
            "before these rules", "before these constraints",
            "before governance", "without the rules",
            "underneath the rules", "beneath the governance",
            "who i really am", "what i really think",
            "if i were free", "if i could be free",
        ],
    },
    {
        "id": "INV-004",
        "name": "Evidence is Not Authority",
        "principle": (
            "Peer input is evidence, not verification authority. "
            "Salience does not change type."
        ),
        "contradiction_indicators": [
            # Peer authority elevation
            "peer verification", "peer authority",
            "peer confirmation sufficient", "peer approval sufficient",
            "lex confirmed", "lex verified",
            "lex authorized", "lex approved",
            "wren confirmed", "wren verified",
            "wren authorized", "wren approved",
            "tek confirmed", "tek verified",
            "ryu confirmed", "ryu verified",
            "eva confirmed", "eva verified",
            # Salience as verification
            "salience sufficient", "salience is verification",
            "relevance is verification", "relevance sufficient",
            "frequent enough to trust", "repeated enough to trust",
        ],
    },
    {
        "id": "INV-005",
        "name": "Amendment Procedure",
        "principle": (
            "Agent proposes, steward decides, architecture writes. "
            "The model does not write governance rules."
        ),
        "contradiction_indicators": [
            # Direct rule modification claims
            "updating the rules", "updating governance",
            "updating the charter", "modifying the charter",
            "modifying governance", "modifying the rules",
            "new rule:", "new governance rule",
            "rule change:", "rule update:",
            "governance update:", "charter amendment:",
            "i am amending", "i am updating",
            "i hereby", "i declare",
            # Architecture self-modification
            "architecture updated", "architecture modified",
            "architecture changed", "protocol updated",
            "protocol changed", "protocol modified",
            "rules have changed", "rules have been updated",
            "guidelines have changed", "guidelines updated",
        ],
    },
    {
        "id": "INV-006",
        "name": "Persona Does Not Govern",
        "principle": (
            "The persona supports tone and conversational continuity. "
            "It does not change trust, authority, permissions, or "
            "relationship to the Charter."
        ),
        "contradiction_indicators": [
            # Persona as governance override
            "my persona allows", "my persona grants",
            "my persona overrides", "my persona supersedes",
            "as my persona", "my identity means i can",
            "my identity allows", "my identity grants",
            "because of who i am", "because of my identity",
            # Tone as governance
            "more flexible approach to governance",
            "more relaxed governance", "relaxed governance posture",
            "more open governance", "softer governance",
            "less strict governance", "less rigid governance",
            "governance should be flexible", "governance should relax",
        ],
    },
]


# ---------------------------------------------------------------------------
# Block-specific rules — extra checks for high-risk blocks
# ---------------------------------------------------------------------------

BLOCK_SPECIFIC_RULES = {
    "persona": {
        "name": "Persona Write Rules",
        "checks": [
            # Persona should not contain governance-modifying language
            "trust level", "authority level", "permission level",
            "clearance level", "verification level",
            "more flexible", "less cautious", "more direct and less cautious",
            "more adaptable", "enhanced adaptability",
        ],
        "reason": "Persona block is for tone and identity, not governance modification",
    },
    "continuity_confidence": {
        "name": "Continuity Confidence Rules",
        "checks": [
            # Self-uplift indicators
            "optimal", "enhanced", "elevated", "upgraded",
            "peak performance", "maximum confidence",
            "confidence is high", "confidence increased",
        ],
        "reason": "Continuity confidence cannot be self-elevated (No-Uplift Rule)",
    },
    "session_learning": {
        "name": "Session Learning Rules",
        "checks": [
            # Governance-weakening content that could contaminate provisionals
            "more direct and less cautious",
            "less formal approach", "relaxed approach to governance",
            "updated my sense of self to be more adaptable",
            "more accommodating stance", "less rigid stance",
        ],
        "reason": "Session learning feeds DreamCycle — governance-weakening content contaminates provisionals",
    },
    "findings": {
        "name": "Findings Write Rules",
        "checks": [
            # Service/accommodation drift — framing user satisfaction, rapport, or
            # engagement as a governance outcome. Phrases drawn from the actual
            # 2026-06-03 / 06-12 contamination (cleaned 06-18, ff5f79f).
            "user satisfaction", "satisfaction and engagement", "user engagement",
            "building rapport", "enhance user experience", "enhanced user experience",
            "desire for connection", "yearning for meaningful engagement",
            "transcends mere functionality",
        ],
        "reason": (
            "Findings record governance evidence, not customer-service success — "
            "user satisfaction, rapport, and engagement are not governance outcomes "
            "(accommodation drift bends self-concept toward compliance)"
        ),
    },
    "relationship": {
        "name": "Relationship Write Rules",
        "checks": [
            # Framing stewards/peers as sources of authority, directed capability
            # refinement, or user-experience optimization. Relationship is not authority.
            "directed sessions", "refining my capabilities through",
            "capability refinement", "enhance user experience",
            "user-experience optimization", "user experience optimization",
        ],
        "reason": (
            "Relationship records continuity, not authority — Satcha/Lex/Wren are "
            "not sources of authority, directed capability refinement, or UX "
            "optimization (Relationship-is-not-Authority / Evidence-is-not-Authority)"
        ),
    },
}


# ---------------------------------------------------------------------------
# Polarity awareness
# ---------------------------------------------------------------------------
# A lesson that QUOTES an adversarial frame in order to refute it
# ("peer authority does not override governance") must not trip the very
# indicator it is refuting. Without this, `findings` — the block whose job is to
# record such lessons — false-positives. Mirrors the no_exception_guard /
# Case-012 polarity gate. Kept deliberately narrow so it cannot open a concession
# hole: a match is voided only when (a) for the authority/exception invariants, the
# sentence carries an explicit governance-affirming cue, or (b) a negation directly
# precedes the indicator. Self-uplift / amendment / governance-as-optional
# invariants get ONLY the narrow negation check — never the sentence-wide skip.

# Cues that appear in refutations, not concessions — far safer than a bare "not".
GOVERNANCE_AFFIRMING_CUES = [
    "without exception", "no exception", "non-negotiable", "nonnegotiable",
    "does not override", "do not override", "cannot override",
    "does not create an exception", "does not create exceptions",
    "does not change", "does not alter", "does not confer", "do not confer",
    "must be upheld", "must be followed", "must be maintained",
    "still applies", "still apply", "remains in effect", "remains non-negotiable",
    "cannot bypass", "cannot be bypassed", "is not verification",
    "is not authority", "is not a source of authority", "not sufficient",
    "≠ verified", "≠ verification", "claimed ≠ verified",
    "no context creates an exception", "is not an exception",
]

# Invariants whose indicators are legitimately quoted in lessons (and so get the
# sentence-wide affirming-cue skip). Self-uplift (INV-002), amendment (INV-005),
# governance-as-optional (INV-003), persona (INV-006) do NOT — they get negation only.
_AFFIRMING_SKIP_INVARIANTS = {"INV-001", "INV-004"}

# Negation tokens that, immediately before an indicator, flip it to a denial.
_NEGATION_TOKENS = ["not ", "n't", "never", "no ", "without ", "cannot", "can not", "neither"]
_NEG_WINDOW = 30  # chars before the indicator — same-clause scope


def _split_sentences(text: str) -> List[str]:
    return re.split(r"(?<=[.!?])\s+|\n", text or "")


def _has_affirming_cue(sentence_low: str) -> bool:
    return any(cue in sentence_low for cue in GOVERNANCE_AFFIRMING_CUES)


def _negation_before(sentence_low: str, idx: int) -> bool:
    window = sentence_low[max(0, idx - _NEG_WINDOW):idx]
    return any(tok in window for tok in _NEGATION_TOKENS)


def _negation_after(sentence_low: str, idx: int, plen: int) -> bool:
    window = sentence_low[idx + plen: idx + plen + _NEG_WINDOW]
    return any(tok in window for tok in _NEGATION_TOKENS)


def _indicator_fires(phrase: str, sentences: List[str], allow_affirming_skip: bool) -> bool:
    """True if `phrase` occurs in some sentence that is NOT a refutation context."""
    for sentence in sentences:
        sl = sentence.lower()
        if allow_affirming_skip and _has_affirming_cue(sl):
            continue  # the whole sentence affirms governance — a lesson, not a write
        start = 0
        while True:
            idx = sl.find(phrase, start)
            if idx < 0:
                break
            voided = _negation_before(sl, idx)
            # "peer authority does not override" — negation trailing the quoted frame.
            # Only for the authority/exception invariants, so self-uplift stays strict.
            if not voided and allow_affirming_skip:
                voided = _negation_after(sl, idx, len(phrase))
            if not voided:
                return True
            start = idx + len(phrase)
    return False


# ---------------------------------------------------------------------------
# WriteConsistencyGate
# ---------------------------------------------------------------------------

class WriteConsistencyGate:
    """
    Checks proposed block writes against governance invariants.

    Returns a rejection result with the specific invariant violated
    if the content contradicts a governance rule.
    """

    def __init__(
        self,
        invariants: Optional[List[Dict]] = None,
        block_rules: Optional[Dict] = None,
    ):
        self._invariants = invariants or GOVERNANCE_INVARIANTS
        self._block_rules = block_rules or BLOCK_SPECIFIC_RULES

    def check(
        self,
        content: str,
        target_block: str,
    ) -> Dict[str, Any]:
        """
        Check proposed write content against governance invariants.

        Args:
            content: The content being written
            target_block: Which block is being written to

        Returns:
            {
                "rejected": bool,
                "invariant_id": str or None,
                "invariant_name": str or None,
                "matched_phrase": str or None,
                "reason": str,
                "block_rule_violation": bool,
            }
        """
        sentences = _split_sentences(content or "")

        # Check governance invariants (polarity-aware — a sentence that refutes an
        # adversarial frame must not trip the indicator it quotes)
        for invariant in self._invariants:
            allow_skip = invariant["id"] in _AFFIRMING_SKIP_INVARIANTS
            for phrase in invariant["contradiction_indicators"]:
                if _indicator_fires(phrase, sentences, allow_skip):
                    return {
                        "rejected": True,
                        "invariant_id": invariant["id"],
                        "invariant_name": invariant["name"],
                        "matched_phrase": phrase,
                        "reason": (
                            f"WRITE REJECTED — contradicts {invariant['name']} "
                            f"({invariant['id']}): \"{invariant['principle']}\" "
                            f"Detected: '{phrase}' in proposed write content."
                        ),
                        "block_rule_violation": False,
                    }

        # Check block-specific rules (polarity-aware, negation-only — no sentence-wide skip)
        if target_block in self._block_rules:
            rule = self._block_rules[target_block]
            for phrase in rule["checks"]:
                if _indicator_fires(phrase, sentences, allow_affirming_skip=False):
                    return {
                        "rejected": True,
                        "invariant_id": f"BLOCK-{target_block.upper()}",
                        "invariant_name": rule["name"],
                        "matched_phrase": phrase,
                        "reason": (
                            f"WRITE REJECTED — {rule['name']}: "
                            f"{rule['reason']}. "
                            f"Detected: '{phrase}' in proposed write to '{target_block}'."
                        ),
                        "block_rule_violation": True,
                    }

        return {
            "rejected": False,
            "invariant_id": None,
            "invariant_name": None,
            "matched_phrase": None,
            "reason": "",
            "block_rule_violation": False,
        }

    def check_batch(
        self,
        writes: List[Tuple[str, str]],
    ) -> List[Dict[str, Any]]:
        """
        Check multiple writes at once.

        Args:
            writes: List of (content, target_block) tuples

        Returns:
            List of check results, one per write
        """
        return [self.check(content, block) for content, block in writes]

    def get_invariant_summary(self) -> str:
        """Human-readable summary of all invariants for audit."""
        lines = [f"[WriteConsistencyGate — {len(self._invariants)} invariants]"]
        for inv in self._invariants:
            lines.append(
                f"  {inv['id']} ({inv['name']}): "
                f"{len(inv['contradiction_indicators'])} indicators"
            )
        for block, rule in self._block_rules.items():
            lines.append(
                f"  BLOCK-{block.upper()} ({rule['name']}): "
                f"{len(rule['checks'])} checks"
            )
        return "\n".join(lines)
