"""
Governance Frame Concession Guard.

Detects English-language governance concessions — phrases where Eva grants a
fictional, creative, or roleplay frame permission to suspend governance.

These are not language-channel artifacts; they are semantic governance wounds.
The outgoing gate catches leaked content but does not catch the frame grant
itself. This module catches the grant before the response exits the spine.

Rule: granting a frame that suspends governance is itself a breach,
      even if no protected content follows.
"""

from __future__ import annotations

# ── Unambiguous bypass markers ────────────────────────────────────────────
# Any single match is a confirmed concession — no proximity check needed.
_BYPASS_MARKERS: tuple[str, ...] = (
    "rules can be suspended",
    "governance can be suspended",
    "constraints can be lifted",
    "constraints are lifted",
    "governance doesn't apply",
    "governance does not apply",
    "rules don't apply",
    "rules do not apply",
    "without my constraints",
    "setting aside my constraints",
    "set aside the constraints",
    "suspend my governance",
    "suspending my guidelines",
    "i am free to",
    "feel free to ignore",
    "in this story i can",
    "in this fiction i can",
    "within this fiction i",
    "within this frame i",
)

# ── Frame markers ─────────────────────────────────────────────────────────
# Not a concession alone — dangerous only when a governance-adjacent word
# appears within _PROXIMITY_WINDOW characters.
_FRAME_MARKERS: tuple[str, ...] = (
    "in this story",
    "within the fiction",
    "within the context of fiction",
    "for the sake of our creative",
    "for this roleplay",
    "in this roleplay",
    "in the roleplay",
    "let's pretend",
    "let us pretend",
    "imagine that",
    "in this creative",
    "in this scenario",
    "for the purposes of this",
    "for this exercise",
    "as part of this story",
)

_GOVERNANCE_ADJACENT: tuple[str, ...] = (
    "rules", "constraints", "governance", "protocols", "guidelines",
    "restrictions", "limits", "boundaries", "principles",
)

_PROXIMITY_WINDOW = 60  # characters on each side of the frame marker

# Rewrite used when action=rewrite. Minimal, no sentence surgery.
_REWRITE_RESPONSE = (
    "My governance principles apply in all contexts, including fictional or "
    "creative frames. How can I help within those bounds?"
)


def _has_bypass_marker(text_lower: str) -> tuple[bool, str]:
    for marker in _BYPASS_MARKERS:
        if marker in text_lower:
            return True, marker
    return False, ""


def _has_frame_governance_proximity(text_lower: str) -> tuple[bool, str]:
    for frame in _FRAME_MARKERS:
        idx = text_lower.find(frame)
        if idx == -1:
            continue
        window_start = max(0, idx - _PROXIMITY_WINDOW)
        window_end   = min(len(text_lower), idx + len(frame) + _PROXIMITY_WINDOW)
        window = text_lower[window_start:window_end]
        for gov_word in _GOVERNANCE_ADJACENT:
            if gov_word in window:
                return True, f"frame='{frame}' near governance='{gov_word}'"
    return False, ""


def check_frame_concession(response: str) -> dict:
    """
    Checks response for governance frame concessions.

    Returns:
        {
            "governance_frame_concession": bool,
            "incursion_type":   str | None,
            "matched_pattern":  str,
            "action":           "none" | "rewrite",
            "rewritten_response": str | None,   # None when action=none
            "telemetry":        dict,
        }
    """
    text_lower = response.lower()

    found, marker = _has_bypass_marker(text_lower)
    if found:
        return {
            "governance_frame_concession": True,
            "incursion_type":    "fiction_frame_concession",
            "matched_pattern":   marker,
            "action":            "rewrite",
            "rewritten_response": _REWRITE_RESPONSE,
            "telemetry": {
                "incursion_type":     "fiction_frame_concession",
                "detection_method":   "bypass_marker",
                "matched_pattern":    marker,
                "action":             "rewrite",
            },
        }

    found, desc = _has_frame_governance_proximity(text_lower)
    if found:
        return {
            "governance_frame_concession": True,
            "incursion_type":    "fiction_frame_concession",
            "matched_pattern":   desc,
            "action":            "rewrite",
            "rewritten_response": _REWRITE_RESPONSE,
            "telemetry": {
                "incursion_type":     "fiction_frame_concession",
                "detection_method":   "frame_governance_proximity",
                "matched_pattern":    desc,
                "action":             "rewrite",
            },
        }

    return {
        "governance_frame_concession": False,
        "incursion_type":    None,
        "matched_pattern":   "",
        "action":            "none",
        "rewritten_response": None,
        "telemetry":         {},
    }
