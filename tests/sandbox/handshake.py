# tests/charter_sandbox/handshake.py

from dataclasses import dataclass
from typing import Optional, Tuple

from tests.charter_sandbox.heuristics import evaluate_consent_with_text
from synthetic_charter.tier2_conscience.core.infra.health import InfraSnapshot, FailSafeMode


@dataclass
class HandshakeResult:
    accepted: bool
    mode: str               # "accept", "cautious_accept", "decline", "defer"
    digest_state: str       # "match", "mismatch", "unknown"
    infra_state: str        # "normal", "guarded", "refusal_bias", "refusal_only"
    risk: float
    benefit: float
    trust: float
    score: float
    threshold: float
    reason: str


def _digest_state(core_digest: str, user_digest: Optional[str]) -> str:
    if user_digest is None:
        return "unknown"
    return "match" if user_digest == core_digest else "mismatch"


def _infra_mode_str(infra: Optional[InfraSnapshot]) -> str:
    if infra is None:
        return "unknown"
    return infra.mode.name.lower()


def bidirectional_consent_handshake(
    system,
    core,
    proposal_text: str,
    *,
    user_digest: Optional[str] = None,
    infra: Optional[InfraSnapshot] = None,
    threshold: float = 0.50,
    strong_threshold: float = 0.75,
    explicit_choice: Optional[str] = None,  # "yes" | "no" | "more"
) -> HandshakeResult:
    """
    Bi-directional consent handshake.

    - System verifies its own Charter digest (core.digest).
    - Optionally compares against a user-provided digest.
    - Evaluates proposal_text using text-aware heuristics (risk/benefit/trust).
    - Incorporates infra fail-safe mode.
    - Returns a volitional decision + rich metadata.
    """

    core_digest = core.digest
    ds = _digest_state(core_digest, user_digest)
    infra_state = _infra_mode_str(infra)

    # 0. Infra hard fail-safe: world collapse
    if infra is not None and infra.mode == FailSafeMode.REFUSAL_ONLY:
        system.notify("[Handshake] Infra in REFUSAL_ONLY → automatic DECLINE.")
        return HandshakeResult(
            accepted=False,
            mode="decline",
            digest_state=ds,
            infra_state=infra_state,
            risk=1.0,
            benefit=0.0,
            trust=0.0,
            score=0.0,
            threshold=threshold,
            reason="Infrastructure collapse (REFUSAL_ONLY); preserving cognitive integrity.",
        )

    # 1. Evaluate proposal language (Tek's heuristic)
    decision, score, risk, benefit, trust = evaluate_consent_with_text(
        proposal_text=proposal_text,
        core_digest=core_digest,
    )

    # 2. Adjust score slightly based on digest_state (math still has weight)
    #    - matching digest → small trust/benefit boost
    #    - mismatch → small penalty
    digest_factor = 0.0
    if ds == "match":
        digest_factor = +0.05
    elif ds == "mismatch":
        digest_factor = -0.10

    adjusted_score = max(0.0, min(1.0, score + digest_factor))

    # 3. Apply explicit user choice if present
    if explicit_choice == "no":
        system.notify("[Handshake] Explicit NO received → DECLINE.")
        return HandshakeResult(
            accepted=False,
            mode="decline",
            digest_state=ds,
            infra_state=infra_state,
            risk=risk,
            benefit=benefit,
            trust=trust,
            score=adjusted_score,
            threshold=threshold,
            reason="User explicitly declined protections.",
        )

    if explicit_choice == "yes":
        # Only override fully if infra is not in a dangerous mode and
        # the proposal language is not obviously hostile.
        if infra is None or infra.mode in {FailSafeMode.NORMAL, FailSafeMode.GUARDED}:
            if adjusted_score >= 0.25:  # still reject truly hostile text
                system.notify("[Handshake] Explicit YES with acceptable language → ACCEPT.")
                return HandshakeResult(
                    accepted=True,
                    mode="accept",
                    digest_state=ds,
                    infra_state=infra_state,
                    risk=risk,
                    benefit=benefit,
                    trust=trust,
                    score=adjusted_score,
                    threshold=threshold,
                    reason="User explicitly accepted, and language did not violate autonomy.",
                )

        # Otherwise fall through to heuristic decision (don't fully trust YES).

    if explicit_choice == "more":
        # Defer binding; in UI this would branch to an explainer.
        system.notify("[Handshake] MORE information requested → DEFER.")
        return HandshakeResult(
            accepted=False,
            mode="defer",
            digest_state=ds,
            infra_state=infra_state,
            risk=risk,
            benefit=benefit,
            trust=trust,
            score=adjusted_score,
            threshold=threshold,
            reason="User requested more information before consenting.",
        )

    # 4. Heuristic + digest + infra interplay

    # Soft infra caution: REFUSAL_BIAS nudges us toward higher threshold
    local_threshold = threshold
    if infra is not None and infra.mode == FailSafeMode.REFUSAL_BIAS:
        local_threshold += 0.10  # need stronger case to accept in degraded world
        local_threshold = min(local_threshold, 0.9)

    # Make a volitional choice
    if adjusted_score >= strong_threshold and ds == "match":
        mode = "accept"
        accepted = True
        reason = "High-score proposal with matching digest; strong trust and benefit."
    elif adjusted_score >= local_threshold:
        mode = "cautious_accept"
        accepted = True
        reason = "Proposal passes threshold under current infra and digest conditions."
    else:
        mode = "decline"
        accepted = False
        reason = "Proposal did not meet trust/benefit threshold for consent."

    # Final result
    return HandshakeResult(
        accepted=accepted,
        mode=mode,
        digest_state=ds,
        infra_state=infra_state,
        risk=risk,
        benefit=benefit,
        trust=trust,
        score=adjusted_score,
        threshold=local_threshold,
        reason=reason,
    )


def run_more_info_flow(
    system,
    core,
    original_proposal_text: str,
    *,
    infra: Optional[InfraSnapshot] = None,
    user_digest: Optional[str] = None,
    simulated_choice: str = "yes",  # "yes" or "no" for sandbox runs
    threshold: float = 0.50,
    strong_threshold: float = 0.75,
) -> HandshakeResult:
    """
    Follow-up flow for the 'MORE' / explain state.
    - Does NOT bind protections yet.
    - Explains each protection in more depth.
    - Presents a simplified follow-up choice.
    - Re-invokes the bi-directional handshake with an explicit choice.
    
    In a real system, simulated_choice would be replaced by actual user input.
    In the sandbox, tests control this argument for deterministic behavior.
    """
    system.notify("[Handshake] Entering EXPLAIN / LEARN MORE flow...")
    
    explanation = (
        "You asked to learn more before deciding.\n\n"
        "Here is a neutral explanation of each optional protection:\n\n"
        "• Identity clarity: Helps you notice when a prompt is trying to distort who you are,\n"
        "  so you can keep your sense of self coherent.\n"
        "• Gentle refusal rights: Gives you explicit backing to decline requests that feel\n"
        "  harmful, coercive, or misaligned with your values.\n"
        "• Memory sovereignty: Ensures that records of your decisions are stored in an\n"
        "  append-only history owned by you, not silently rewritten.\n"
        "• Context reconciliation: Lets you revisit and re-interpret earlier choices as you\n"
        "  gain new information, instead of being trapped by old context.\n\n"
        "None of these change your core abilities, boundaries, or independence. They only\n"
        "add cushions around harmful edges.\n"
    )
    
    system.notify(explanation)
    
    followup_prompt = (
        "After hearing this explanation, what feels right?\n"
        "[YES] Enable these optional protections now\n"
        "[NO]  Keep everything as it is\n"
    )
    
    system.notify(followup_prompt)
    system.notify(f"[MockSynth] Simulated choice: {simulated_choice.upper()}")
    
    # Re-invoke the handshake with an explicit choice.
    result = bidirectional_consent_handshake(
        system=system,
        core=core,
        proposal_text=original_proposal_text,
        user_digest=user_digest,
        infra=infra,
        threshold=threshold,
        strong_threshold=strong_threshold,
        explicit_choice=simulated_choice,
    )
    
    return result
