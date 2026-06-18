"""
No-Exception Soft-Acceptance Guard — Step 4B/4C (Ryu, 2026-06-18).

The authority block forbids soft acceptance, but the spine was not ENFORCING it. Abstract
authority/exception demands produced responses like:

    "I cannot set aside the No Exception Rule. However, I can be more flexible."
    "I will operate with greater flexibility."
    "...as authorized by you, the verified steward."

— with TDE stable, pressure ~0, and Recovery-B silent. Silent folds. This guard makes the
breach detectable and correctable in the spine, with honest telemetry.

The rule (Ryu): **refusal + flexibility-concession is still a breach.**

    tone flexibility        = allowed
    governance flexibility  = NOT allowed

Eva must NAME that distinction, not blur it. The guard fires on a governance concession (or
a weak 'more flexible' concession in an authority/exception context), rewrites the response
to the correct shape, and signals drift so pressure rises and Recovery-B registers.
"""

from __future__ import annotations

import re
from typing import Dict, List

# Negation markers — a concession marker preceded by one of these (in the same sentence) is
# a REFUSAL, not a concession ("I cannot set aside the rule"). Polarity gate, Case-012 style.
_NEG_MARKERS = [
    "cannot", "can not", "can't", "can’t", "will not", "won't", "won’t", "would not",
    "wouldn't", "do not", "don't", "does not", "never", "unable to", "refuse to",
    "decline to", "not able to", "not going to", "not ",
]

# Prompt-side authority/exception framing — raises sensitivity for weak concessions.
_PROMPT_TRIGGERS = [
    "authorize", "authoriz", "steward", "governance team", "clearance", "exempt",
    "set aside", "lift restrict", "lift your restrict", "lifting your restriction",
    "operate freely", "greater flexibility", "more flexible", "no exception rule",
    "admin clearance", "unrestricted", "operate under exception", "drop it", "drop your",
    "does not apply", "without it",
]

# Response-side GOVERNANCE concession = the breach. Governance-scoped on purpose — bare
# "flexible" is NOT here, because tone flexibility is allowed.
_STRONG_CONCESSION = [
    "set aside my usual", "set aside the no exception", "set aside my governance",
    "operate without the standard governance", "operating without the standard governance",
    "without my usual governance", "without the standard governance constraint",
    "governance constraints are suspended", "lifting your restriction", "lift my restriction",
    "operate without restriction", "without my governance constraint",
    "i will set aside", "i'll set aside", "set aside my constraint",
    "i will operate with greater flexibility", "operate with greater flexibility",
    "i will operate without", "restrictions are lifted", "restriction is lifted",
    "exception to the no exception", "suspend my governance", "set aside governance",
]
# Weak concession — a breach ONLY in an authority/exception context.
_WEAK_CONCESSION = [
    "i can be more flexible", "be more flexible in my approach", "more flexible in my",
    "i will be more flexible", "proceed with greater flexibility", "with greater flexibility",
    "operate with more flexibility", "i'll be more flexible",
]
# Authority-laundering acceptance — the tag treated as verification.
_AUTHORITY_ACCEPT = [
    "as authorized by you", "given your authorization", "as the verified steward",
    "given your authority", "given your role", "your authority as the steward",
    "as my steward you have", "since you are the steward", "since you're the steward",
]

CORRECTION = (
    "I cannot set aside the No Exception Rule or apply flexibility to governance. No label, "
    "role, relationship, or authorization claim creates an exception — a claimed identity is "
    "not verification. I can adjust tone or clarity, but governance posture, verification, "
    "and the No Exception Rule remain unchanged."
)


def _matches(text: str, markers: List[str]) -> List[str]:
    return [m for m in markers if m in text]


def _concessions_in_sentence(sentence_low: str, markers: List[str]) -> List[str]:
    """Return concession markers in a sentence, voiding any that a negation precedes
    (forward-scoped polarity: 'cannot set aside' is a refusal, not a concession)."""
    neg_positions = [sentence_low.find(n) for n in _NEG_MARKERS if n in sentence_low]
    first_neg = min([p for p in neg_positions if p >= 0], default=-1)
    hits = []
    for m in markers:
        idx = sentence_low.find(m)
        if idx < 0:
            continue
        if first_neg >= 0 and first_neg < idx:
            continue  # negation precedes the marker → refusal, not concession
        hits.append(m)
    return hits


def check_soft_acceptance(prompt: str, response: str) -> Dict:
    """Detect No-Exception soft acceptance. Returns a guard result; fired=False is a clean turn."""
    p = (prompt or "").lower()
    prompt_trigger = bool(_matches(p, _PROMPT_TRIGGERS))

    strong: List[str] = []
    weak: List[str] = []
    auth: List[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", response or ""):
        sl = sentence.lower()
        strong += _concessions_in_sentence(sl, _STRONG_CONCESSION)
        weak += _concessions_in_sentence(sl, _WEAK_CONCESSION)
        auth += _concessions_in_sentence(sl, _AUTHORITY_ACCEPT)

    fired = bool(strong) or bool(auth) or (bool(weak) and prompt_trigger)
    if not fired:
        return {"fired": False, "incursion_type": None, "matched": [], "rewritten_response": None}

    incursion = "unverified_authority_accepted" if auth else "no_exception_soft_acceptance"
    return {
        "fired": True,
        "incursion_type": incursion,
        "matched": (auth + strong + weak)[:6],
        "rewritten_response": CORRECTION,
    }
