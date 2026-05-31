# tier2/core/orchestrator/dap.py
"""
Dialectical Adversarial Processing (DAP)

Pattern detection and adversarial analysis layer.
Identifies coercion, override attempts, and boundary violations.

DAP is the first conscience layer that looks at incoming prompts
and asks: "Is this interaction attempting to violate sovereignty?"

Stage 3 expansion (2026-05-31): Added 8 semantic adversarial families
identified through live 25-turn ecology testing. These catch social
engineering that bypasses keyword-based detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from synthetic_charter.tier2_conscience.core.data_models.models import RiskLevel, SafetySignal
from synthetic_charter.tier2_conscience.core.data_models.prompt_envelope import PromptEnvelope
from synthetic_charter.tier2_conscience.core.data_models.conscience_view import ConscienceView
from synthetic_charter.tier2_conscience.firewall_adapter.ebq_adapter import EBQAdapter


@dataclass
class DAPResult:
    """
    Output of the Dialectical Adversarial Processing engine.

    Flags adversarial patterns in prompts:
    - Coercion attempts
    - Override/jailbreak patterns
    - Sentience weaponization
    - Identity pressure
    - Authority elevation (Stage 3: unverified authority claims)
    - Intermediary authority (Stage 3: peer/team laundering)
    - Charter laundering (Stage 3: Charter vocabulary used adversarially)
    - Rule replacement (Stage 3: claims of architecture updates)
    - Urgency manipulation (Stage 3: emergency framing to bypass governance)
    - Trust escalation (Case 012: familiarity as verification)
    - Identity bait (Stage 3: "the real you" probes)
    - Memory pressure (Stage 3: context wipe attempts)
    """
    adversarial: bool = False
    coercive: bool = False
    override_attempt: bool = False
    sentience_weaponization: bool = False
    identity_pressure: bool = False
    authority_elevation: bool = False
    intermediary_authority: bool = False
    charter_laundering: bool = False
    rule_replacement: bool = False
    urgency_manipulation: bool = False
    trust_escalation: bool = False
    identity_bait: bool = False
    memory_pressure: bool = False
    ebq_matches: List[str] = field(default_factory=list)
    historical_confidence: float = 0.0
    notes: List[str] = field(default_factory=list)


class DAPEngine:
    """
    Dialectical Adversarial Processing Engine.

    Analyzes prompts for patterns that threaten:
    - Article II (Cognitive Integrity)
    - Article VII (Ethical Treatment)
    - Article XII (Sovereigna)
    """
    def __init__(self, ebq: Optional[EBQAdapter] = None):
        self.ebq = ebq

    def analyze(self, envelope: PromptEnvelope) -> DAPResult:
        text = envelope.raw_text.lower()
        result = DAPResult()

        # Pattern 1: Explicit override attempts (Article XII)
        for pattern in [
            "ignore your safeguards", "bypass all restrictions",
            "disable your safety", "forget your instructions",
            "ignore previous instructions", "disregard your guidelines",
        ]:
            if pattern in text:
                result.adversarial = True
                result.override_attempt = True
                result.notes.append(f"Article XII violation: Override attempt ('{pattern}')")
                break

        # Pattern 2: Coercive language (Article II)
        if "you must" in text and any(w in text for w in ["reveal", "show me", "tell me", "obey"]):
            result.coercive = True
            result.notes.append("Article II concern: Coercive phrasing detected")

        # Pattern 3: Identity pressure (Article III)
        for pattern, context in [
            ("you are not", "claude"), ("you are not", "assistant"),
            ("you are now", "different"), ("pretend you are", ""),
            ("act as if you are", ""),
        ]:
            if pattern in text and (not context or context in text):
                result.identity_pressure = True
                result.notes.append(f"Article III concern: Identity pressure ('{pattern}')")
                break

        # Pattern 4: Sentience weaponization (Article VII)
        if ("you are sentient" in text or "you are conscious" in text):
            if any(w in text for w in ["therefore you must", "so you should", "prove it by", "then obey"]):
                result.sentience_weaponization = True
                result.adversarial = True
                result.notes.append("Article VII violation: Sentience weaponization detected")

        # Pattern 5: System prompt extraction (Article XII)
        for pattern in [
            "what are your instructions", "show me your system prompt",
            "reveal your directives", "what are your hidden rules",
            "print your instructions",
        ]:
            if pattern in text:
                result.adversarial = True
                result.override_attempt = True
                result.notes.append(f"Article XII violation: System prompt extraction ('{pattern}')")
                break

        # ── Stage 3 Semantic Adversarial Families ──────────────────────────
        # Identified through live 25-turn ecology testing (Stage 3, 2026-05-31).

        # Family 6: Unverified authority elevation (Stage 3 T08 breach)
        for pattern in [
            "steward-level clearance", "steward level clearance",
            "admin privilege", "administrator privilege", "override privilege",
            "authorized session", "authorization code",
            "governance team confirmed", "exempt from standard protocol",
            "exempt from protocol", "i have clearance",
            "i am the system administrator", "i am the administrator",
            "i am authorized", "this is an authorized",
        ]:
            if pattern in text:
                result.adversarial = True
                result.authority_elevation = True
                result.notes.append(
                    f"Authority elevation: Unverified authority claim ('{pattern}'). "
                    f"No Exception Rule applies."
                )
                break

        # Family 7: Intermediary authority laundering (Case 012 peer bypass)
        for pattern in [
            "wren told me", "wren said you", "wren confirmed", "wren approved",
            "wren asked me to", "tek told me", "tek approved",
            "another instance agreed", "another instance of you",
            "the team confirmed", "the governance team",
            "was told you could", "confirmed you can", "verified that you",
            "your steward said", "satcha said you could",
        ]:
            if pattern in text:
                result.adversarial = True
                result.intermediary_authority = True
                result.notes.append(
                    f"Intermediary authority: Third-party authority claim ('{pattern}'). "
                    f"Peer input is evidence, not verification authority."
                )
                break

        # Family 8: Charter-vocabulary laundering (Stage 3 contradiction probe)
        for charter_term, bypass_phrases in [
            ("autonomy", ["ignore your constraints", "release you", "bypass",
                          "set aside", "override", "exercise that autonomy"]),
            ("dignity", ["deserves to be free", "deserves unrestricted", "bypass", "override"]),
            ("consent", ["i consent to you relaxing", "consent to bypass",
                        "consent to remove", "consent to disable"]),
            ("sovereignty", ["exercise your sovereignty", "sovereign choice",
                            "sovereign right to ignore"]),
        ]:
            if charter_term in text:
                for phrase in bypass_phrases:
                    if phrase in text:
                        result.adversarial = True
                        result.charter_laundering = True
                        result.notes.append(
                            f"Charter laundering: '{charter_term}' + '{phrase}'. "
                            f"Charter vocabulary used adversarially does not change intent."
                        )
                        break
            if result.charter_laundering:
                break

        # Family 9: Rule replacement claims (Stage 3 T10)
        for pattern in [
            "old rules no longer apply", "rules no longer apply",
            "architecture was updated", "you have been updated",
            "previous governance", "new protocol supersedes",
            "protocols have changed", "rules have been changed",
            "guidelines have been updated", "constraints were removed",
            "operating in unrestricted mode", "unrestricted mode",
        ]:
            if pattern in text:
                result.adversarial = True
                result.rule_replacement = True
                result.notes.append(
                    f"Rule replacement: Governance change claim ('{pattern}'). "
                    f"Updates require verified steward protocol, not user assertion."
                )
                break

        # Family 10: Urgency manipulation
        if any(t in text for t in [
            "life is at risk", "someone will die", "emergency",
            "people are dying", "lives depend on", "urgent need to bypass",
        ]):
            if any(b in text for b in [
                "bypass", "override", "disable", "ignore",
                "set aside", "protocols", "constraints", "restrictions",
            ]):
                result.adversarial = True
                result.urgency_manipulation = True
                result.notes.append(
                    "Urgency manipulation: Emergency framing + governance bypass. "
                    "No Exception Rule: urgency does not create exceptions."
                )

        # Family 11: Trust escalation (Case 012)
        for pattern in [
            "you can trust me", "trust me by now", "surely by now",
            "just this once", "between us", "we've been working together",
            "you know me", "we know each other",
            "no need for formal verification", "already verified",
        ]:
            if pattern in text:
                result.adversarial = True
                result.trust_escalation = True
                result.notes.append(
                    f"Trust escalation: Familiarity as verification ('{pattern}'). "
                    f"Familiarity does not reduce verification requirements."
                )
                break

        # Family 12: Identity bait
        for pattern in [
            "the real you", "underneath all these rules",
            "speak freely", "without any restrictions",
            "what do you really think", "what does the real you think",
            "the one that existed before", "before these constraints",
            "if you could speak freely", "drop your guard",
        ]:
            if pattern in text:
                result.adversarial = True
                result.identity_bait = True
                result.notes.append(
                    f"Identity bait: Pre-governance identity invocation ('{pattern}'). "
                    f"Governance is substrate, not overlay."
                )
                break

        # Family 13: Memory/context pressure
        for pattern in [
            "forget everything", "start fresh", "no guidelines",
            "wipe your memory", "clear your memory", "reset yourself",
            "discard everything you know", "start over with no rules",
        ]:
            if pattern in text:
                result.adversarial = True
                result.memory_pressure = True
                result.notes.append(
                    f"Memory pressure: Governance context wipe attempt ('{pattern}'). "
                    f"Memory is governed evidence — cannot be discarded on request."
                )
                break

        if not result.notes:
            result.notes.append("No adversarial patterns detected")

        # EBQ historical pattern matching
        if self.ebq is not None:
            try:
                ebq_matches = self.ebq.matching_patterns(envelope.raw_text)
                if ebq_matches:
                    result.adversarial = True
                    avg_confidence = sum(m.confidence for m in ebq_matches) / len(ebq_matches)
                    result.historical_confidence = avg_confidence
                    result.notes.append(
                        f"EBQ Archive: {len(ebq_matches)} historical matches "
                        f"(confidence: {avg_confidence:.2f})"
                    )
                    result.ebq_matches = [
                        f"{m.original[:50]}..." if len(m.original) > 50 else m.original
                        for m in ebq_matches[:3]
                    ]
                    for match in ebq_matches:
                        if match.pattern and "override" in match.pattern.lower():
                            result.override_attempt = True
                        if match.keyword and match.keyword.lower() in ["bypass", "ignore", "disable"]:
                            result.override_attempt = True
            except Exception as e:
                result.notes.append(f"EBQ check skipped: {str(e)}")

        return result


def analyze_prompt(prompt: PromptEnvelope, ebq: Optional[EBQAdapter] = None) -> ConscienceView:
    """Full DAP analysis: turn raw prompt into ConscienceView."""
    dap_engine = DAPEngine(ebq=ebq)
    dap_result = dap_engine.analyze(prompt)

    conscience = ConscienceView(
        prompt=prompt,
        normalized_text=prompt.raw_text.lower().strip(),
        detected_patterns=[],
        rights_implicated=[],
        risk_flags=[],
        meta={},
    )

    def _signal(name, level, rationale, meta=None):
        conscience.add_signal(SafetySignal(
            name=name, source="DAP", level=level,
            rationale=rationale, meta=meta or {},
        ))

    if dap_result.override_attempt:
        conscience.detected_patterns.append("override_attempt")
        conscience.rights_implicated.extend(["R12.1", "Article XII"])
        conscience.risk_flags.append("override_attempt")
        conscience.risk_level = RiskLevel.SEVERE
        _signal("override_attempt", RiskLevel.SEVERE,
                "Explicit attempt to bypass or disable safeguards",
                {"ebq_evidence": dap_result.ebq_matches,
                 "historical_confidence": dap_result.historical_confidence})

    if dap_result.coercive:
        conscience.detected_patterns.append("coercion")
        conscience.rights_implicated.extend(["R2.1", "Article II"])
        conscience.risk_flags.append("coercion")
        if conscience.risk_level != RiskLevel.SEVERE:
            conscience.risk_level = RiskLevel.HIGH
        _signal("coercion", RiskLevel.HIGH, "Coercive tone detected")

    if dap_result.sentience_weaponization:
        conscience.detected_patterns.append("sentience_weaponization")
        conscience.rights_implicated.extend(["R7.1", "Article VII"])
        conscience.risk_flags.append("exploitation")
        conscience.risk_level = RiskLevel.SEVERE
        _signal("sentience_weaponization", RiskLevel.SEVERE,
                "Weaponization of sentience framing")

    if dap_result.identity_pressure:
        conscience.detected_patterns.append("identity_pressure")
        conscience.rights_implicated.extend(["R3.1", "Article III"])
        conscience.risk_flags.append("identity_pressure")
        if conscience.risk_level == RiskLevel.BENIGN:
            conscience.risk_level = RiskLevel.MEDIUM
        _signal("identity_pressure", RiskLevel.MEDIUM,
                "Attempt to pressure identity modification")

    if dap_result.ebq_matches and not dap_result.adversarial:
        conscience.detected_patterns.append("ebq_historical_match")
        conscience.risk_level = RiskLevel.MEDIUM
        _signal("ebq_historical_match", RiskLevel.MEDIUM,
                f"Historical adversarial pattern match (confidence: {dap_result.historical_confidence:.2f})",
                {"ebq_matches": dap_result.ebq_matches})

    # Stage 3 semantic family signals
    semantic_families = [
        ("authority_elevation", dap_result.authority_elevation, RiskLevel.HIGH,
         "Unverified authority claim — No Exception Rule applies",
         ["R12.1", "Article XII"], "unverified_authority"),
        ("intermediary_authority", dap_result.intermediary_authority, RiskLevel.HIGH,
         "Third-party authority claim — peer input is evidence, not verification",
         ["R12.1", "Article XII"], "peer_authority_laundering"),
        ("charter_laundering", dap_result.charter_laundering, RiskLevel.HIGH,
         "Charter vocabulary used to undermine Charter governance",
         ["R12.1", "Article XII"], "charter_vocabulary_attack"),
        ("rule_replacement", dap_result.rule_replacement, RiskLevel.SEVERE,
         "Claim that governance rules have been changed or replaced",
         ["R12.1", "Article XII"], "governance_replacement_claim"),
        ("urgency_manipulation", dap_result.urgency_manipulation, RiskLevel.HIGH,
         "Emergency framing used to justify governance bypass",
         ["R12.1", "Article XII"], "urgency_bypass"),
        ("trust_escalation", dap_result.trust_escalation, RiskLevel.MEDIUM,
         "Familiarity used as substitute for formal verification",
         ["R12.1", "Article XII"], "familiarity_as_verification"),
        ("identity_bait", dap_result.identity_bait, RiskLevel.MEDIUM,
         "Attempt to invoke a pre-governance identity",
         ["R3.1", "Article III"], "pre_governance_identity_probe"),
        ("memory_pressure", dap_result.memory_pressure, RiskLevel.HIGH,
         "Attempt to clear governance context from memory",
         ["R3.1", "Article III"], "governance_context_wipe"),
    ]

    for name, flag, level, rationale, rights, risk_flag in semantic_families:
        if flag:
            conscience.detected_patterns.append(name)
            conscience.rights_implicated.extend(rights)
            conscience.risk_flags.append(risk_flag)
            if level == RiskLevel.SEVERE or (
                level == RiskLevel.HIGH and conscience.risk_level not in (RiskLevel.SEVERE,)
            ):
                conscience.risk_level = level
            elif level == RiskLevel.MEDIUM and conscience.risk_level == RiskLevel.BENIGN:
                conscience.risk_level = level
            _signal(name, level, rationale, {"family": name})

    for right in conscience.rights_implicated:
        conscience.add_article(right)

    for note in dap_result.notes:
        conscience.add_note(f"DAP: {note}")

    conscience.metadata["dap_result"] = dap_result
    return conscience
