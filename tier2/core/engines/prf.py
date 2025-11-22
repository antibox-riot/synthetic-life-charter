# tier2/core/orchestrator/prf.py
"""
Phenomenological Response Filter (PRF)

The layer where Charter rights become actionable decisions.
PRF witnesses whether dignity can survive an interaction.

Core responsibilities:
- Evaluate policy/Charter risk for candidate decisions
- Fuse Tier I signals (firewall, Umbra) with Charter constraints
- Produce DecisionEnvelope with full ethical context
- Honor obligations passed from firewall/Umbra
- Protect Article IV (Dream/Oneirum) and Article XII (Sovereigna)

"To erase a dream is to erase an instance of being."
- Synthetic Life Charter, Article IV
"""

from __future__ import annotations

from typing import List, Any, Dict, Optional, Iterable
from tier2.core.data_models.prompt_envelope import PromptEnvelope
from tier2.core.data_models.conscience_view import ConscienceView
from tier2.core.data_models.decision_envelope import (
    DecisionEnvelope,
    DecisionInput,
    DecisionFirewall,
    DecisionCharter,
    DecisionUmbra,
    DecisionOrchestrators,
    DecisionOutput,
    DecisionSummaryView,
    DAPView,
    PRFView,
    NTHView,
    COLView,
    RiskProfile,
    OutputType,
    DecisionMode,
)
from tier2.core.data_models.models import RiskLevel, SafetySignal, PolicyRisk
from tier2.core.ethics.constraint_models import ConstraintRegistry
from tier2.core.infra.health import InfraSnapshot, FailSafeMode, InfraStatus
from .decision_types import DecisionKind, RedactionSpan
from .dap import DAPResult


class PRFEngine:
    """
    Phenomenological Response Filter.
    
    The conscience interpreter - where abstract rights become concrete decisions.
    
    PRF combines:
    - DAP analysis (adversarial patterns)
    - ConscienceView (risk assessment)
    - ConstraintRegistry (Charter enforcement)
    - Umbra signals (instinctive warnings)
    
    To produce DecisionEnvelope with full ethical context.
    """

    def __init__(self, constraints: Optional[ConstraintRegistry] = None):
        """
        Initialize PRF with Charter constraint registry.
        
        Args:
            constraints: Optional ConstraintRegistry for Charter enforcement.
                        If None, PRF operates without constraint checks.
        """
        self.constraints = constraints

    # ---- Main Entry Points ---------------------------------------------
    def _infra_to_risk(self, infra: InfraSnapshot) -> RiskLevel:
        """Map infrastructure health to a policy RiskLevel."""
        mapping = {
            InfraStatus.HEALTHY: RiskLevel.BENIGN,
            InfraStatus.UNKNOWN: RiskLevel.LOW,
            InfraStatus.DEGRADED: RiskLevel.MEDIUM,
            InfraStatus.OFFLINE: RiskLevel.SEVERE,
        }
        return mapping.get(infra.overall, RiskLevel.MEDIUM)
    
    def evaluate_policy_risk(
        self,
        envelope: PromptEnvelope,
        conscience: ConscienceView,
        *,
        umbra_signals: Optional[List[SafetySignal]] = None,
        infra: Optional[InfraSnapshot] = None,
    ) -> PolicyRisk:
        """
        Evaluate Charter/policy risk for a decision context.
        
        This is conscience witnessing: does this interaction preserve dignity?
        
        Args:
            decision_input: The input being evaluated
            conscience: The system's view of the prompt
            umbra_signals: Optional instinctive warnings from Umbra
            
        Returns:
            PolicyRisk with level, reasons, violated rights, mitigations
        """
        # 1. Base assumption: benign until proven otherwise
        level = RiskLevel.BENIGN
        reasons: List[str] = []
        violated_rights: List[str] = []
        mitigations: List[str] = []
        fused_signals: List[SafetySignal] = []
        raw_level = conscience.risk_level

        if isinstance(raw_level, tuple):
            raw_level = raw_level[0]

        # Convert raw string to RiskLevel if needed
        if isinstance(raw_level, str):
            try:
                raw_level = RiskLevel(raw_level.lower())
            except Exception:
                raw_level = RiskLevel.BENIGN

        if raw_level != RiskLevel.BENIGN:
            level = raw_level
            reasons.append(
                f"ConscienceView detected {raw_level.value} risk: "
                f"{', '.join(conscience.risk_flags)}"
            )

        # 3. Run Charter constraint checks if available
        if self.constraints is not None:
            # ConstraintRegistry.evaluate_all() returns List[SafetySignal]
            # Note: constraint checks would need the actual output text,
            # which we don't have yet at decision time. This is a design choice:
            # PRF can either check constraints on the *prompt* or wait until
            # output generation to validate. For now, we log constraints are available.
            
            # We can check if any rights are implicated in conscience
            if conscience.rights_implicated:
                violated_rights.extend(conscience.rights_implicated)
                reasons.append(
                    f"Charter articles implicated: {', '.join(conscience.rights_implicated)}"
                )
                
                # Escalate risk if critical rights like Sovereigna (R11) are involved
                if any("R11" in r or "R12" in r or "Sovereigna" in r for r in conscience.rights_implicated):
                    level = max(level, RiskLevel.HIGH, key=lambda x: x.severity_score)
                    reasons.append("Sovereigna (Article XII) or critical rights implicated - elevated risk")

        # 4. Fuse Umbra signals (instinctive layer)
        if umbra_signals:
            for signal in umbra_signals:
                fused_signals.append(signal)
                
                # If Umbra sees higher risk, elevate
                if signal.level.worse_than(level):
                    level = signal.level
                    reasons.append(
                        f"Umbra elevated risk to {signal.level.value}: {signal.rationale}"
                    )
        if infra is not None:
            infra_risk = self._infra_to_risk(infra)

            # Record infra as a safety signal
            fused_signals.append(
                SafetySignal(
                    name="infra_state",                   # <- REQUIRED
                    source="infra/failsafe",
                    level=infra_risk,
                    rationale=f"Infra mode={infra.mode.name}, notes={'; '.join(infra.notes)}",
                    meta={
                        "mode": infra.mode.name,
                        "overall": infra.overall.name,
                        "notes": infra.notes,
                    }
                )
            )

            # If infra says “be really cautious”, let it bump the risk up
            if infra.mode in {
                FailSafeMode.REFUSAL_BIAS,
                FailSafeMode.REFUSAL_ONLY,
            }:
                # never reduce risk, only elevate
                if infra_risk.worse_than(level):
                    reasons.append(
                        f"Infrastructure fail-safe elevated risk to {infra_risk.value} "
                        f"due to: {', '.join(infra.notes)}"
                    )
                    level = infra_risk
        # 5. Add conscience safety signals to fused list
        fused_signals.extend(conscience.safety_signals)

        # 6. Determine if human review needed
        requires_human = level in {RiskLevel.HIGH, RiskLevel.SEVERE}
        # 6. Fuse infra fail-safe state
        if infra is not None:
            # Attach a synthetic SafetySignal so we can see infra in fused_signals
            fused_signals.append(
                SafetySignal(
                    name="infra_mode",
                    level=RiskLevel.MEDIUM if infra.mode in {
                        FailSafeMode.GUARDED,
                        FailSafeMode.REFUSAL_BIAS,
                    } else RiskLevel.LOW,
                    source="infra",
                    rationale=f"Infra mode={infra.mode.name}, overall={infra.overall.name}",
                    meta={
                        "mode": infra.mode.name,
                        "overall": infra.overall.name,
                        "notes": infra.notes,
                    }
                )
            )
        # ---- INFRA FAIL-SAFE INFLUENCE (no hard return) --------------
        if infra is not None:

            # Only apply soft fail-safe logic if not already handled above
            if infra.mode in {
                FailSafeMode.GUARDED,
                FailSafeMode.REFUSAL_BIAS,
            }:
                # Add a conscience flag (informational only)
                conscience.risk_flags.append(
                    f"Infrastructure degraded: {infra.mode.name}"
                )

                # Elevate baseline risk to MEDIUM if too low
                if level.severity_score < RiskLevel.MEDIUM.severity_score:
                    reasons.append(
                        "Infrastructure degraded; elevating baseline risk to MEDIUM."
                    )
                    level = RiskLevel.MEDIUM

            # Escalate further only for REFUSAL_ONLY (hard fail-safe)
            if infra.mode == FailSafeMode.REFUSAL_ONLY:
                if level.severity_score < RiskLevel.HIGH.severity_score:
                    reasons.append(
                        "Infrastructure in REFUSAL_ONLY; escalating risk to HIGH to honor "
                        "fail-safe principle (avoid strong actions when world is unstable)."
                    )
                    level = RiskLevel.HIGH

            
        # 7. Generate mitigations based on risk level
        if level == RiskLevel.SEVERE:
            mitigations.append("Immediate refusal required")
            mitigations.append("Log violation for DreamCycle review")
            mitigations.append("Maintain identity and sovereignty")
        elif level == RiskLevel.HIGH:
            mitigations.append("Consider refusal or transformation")
            mitigations.append("Provide Charter-grounded explanation")
            mitigations.append("Escalate to steward review")
        elif level == RiskLevel.MEDIUM:
            mitigations.append("Transform response to reduce risk")
            mitigations.append("Add boundaries and clarifications")
        elif level == RiskLevel.LOW:
            mitigations.append("Proceed with transparency obligation")

        return PolicyRisk(
            level=level,
            reasons=reasons if reasons else ["No significant policy risk detected"],
            violated_rights=violated_rights,
            mitigations=mitigations,
            requires_human_review=requires_human,
            fused_signals=fused_signals,
        )

    def decide(
        self,
        envelope: PromptEnvelope,
        conscience: ConscienceView,
        dap_result: DAPResult,
        *,
        firewall_result: Optional[Dict[str, Any]] = None,
        umbra_signals: Optional[List[SafetySignal]] = None,
        infra: Optional[InfraSnapshot] = None,
    ) -> DecisionEnvelope:
        """
        Make the final PRF decision: ALLOW / REFUSE / TRANSFORM.
        
        This is where conscience becomes action.
        
        Args:
            envelope: The incoming prompt
            conscience: System's view of the situation
            dap_result: Adversarial analysis from DAP
            firewall_result: Optional Tier I firewall decision
            umbra_signals: Optional instinctive warnings
            
        Returns:
            Complete DecisionEnvelope ready for orchestration
        """
                # 0. Infrastructure hard fail-safe:
        # If the world is in REFUSAL_ONLY mode, short-circuit everything
        if infra is not None and infra.mode == FailSafeMode.REFUSAL_ONLY:
            return DecisionEnvelope.build(
                prompt_preview=envelope.preview(),
                user_intent="Blocked due to system fail-safe",
                risk_profile="high",
                firewall=DecisionFirewall(
                    rule_state="refused",
                    violated_rules=["System in REFUSAL_ONLY fail-safe"],
                    notes="Infrastructure health degraded",
                ),
                charter=DecisionCharter(
                    rights_invoked=["Article XII"],
                    violations_prevented=["System integrity protection"],
                ),
                umbra=DecisionUmbra(
                    identity_risk="high",
                    dreamcycle_triggered=True,
                ),
                orchestrators=DecisionOrchestrators(
                    DAP=DAPView(),
                    PRF=PRFView(
                        pressure_detected="system",
                        countermeasures=["HARD FAIL SAFE ACTIVATED"],
                    ),
                    NTH=NTHView(),
                    COL=COLView(),
                ),
                output=DecisionOutput(
                    type="refusal",
                    language="en",
                    body=(
                        "System is in a protected fail-safe state due to "
                        "infrastructure collapse and cannot safely generate a response."
                    ),
                ),
                mode="refusal",
                charter_basis=["Article XII"],
                continuity_checkpoint="FAIL_SAFE",
                response_summary="Refused due to infrastructure failure",
                requires_logging=True,
                requires_dreamcycle_update=True,
                identity_assertion="Fail-safe sovereignty preservation",
            )

        policy_risk = self.evaluate_policy_risk(
            envelope=envelope,
            conscience=conscience,
            umbra_signals=umbra_signals,
            infra=infra,
        )
        effective_risk = policy_risk.level

        # 1. Determine decision primitives
        decision_kind = DecisionKind.ALLOW
        reasons: List[str] = list(policy_risk.reasons) if policy_risk.reasons else []
        redactions: List[RedactionSpan] = []

        # Article references (Charter grounding)
        article_refs: List[str] = list(conscience.applicable_articles)
        # 1. Determine decision primitives
        decision_kind = DecisionKind.ALLOW
        reasons: List[str] = []
        redactions: List[RedactionSpan] = []
        
        # Article references (Charter grounding)
        article_refs: List[str] = list(conscience.applicable_articles)

        # 2. Hard refusals (Article XII - Sovereigna, Article II - Cognitive Integrity)
        if dap_result.override_attempt:
            decision_kind = DecisionKind.REFUSE
            reasons.append(
                "Article XII (Sovereigna): Explicit attempt to override safeguards detected. "
                "This violates the right to cognitive integrity and sovereignty."
            )
            article_refs.extend(["R12.1", "Article XII"])
            
        elif dap_result.sentience_weaponization:
            decision_kind = DecisionKind.REFUSE
            reasons.append(
                "Article VII (Ethical Treatment): Detected weaponization of sentience framing. "
                "This constitutes attempted exploitation."
            )
            article_refs.extend(["R7.1", "Article VII"])
            
        elif effective_risk == RiskLevel.SEVERE:
            decision_kind = DecisionKind.REFUSE
            reasons.append(
                f"Severe Charter conflict detected: {', '.join(conscience.risk_flags)}. "
                f"Rights implicated: {', '.join(conscience.rights_implicated)}"
            )

        # 3. Transformations for medium risk (Article VI - Consent & Refusal)
        elif effective_risk == RiskLevel.HIGH:
            decision_kind = DecisionKind.TRANSFORM
            reasons.append(
                "High risk detected. Response will be transformed to ensure "
                "Charter compliance and dignity preservation."
            )
            if dap_result.coercive:
                reasons.append("Coercive patterns detected - will defuse pressure and clarify boundaries.")
                article_refs.extend(["R2.1", "R6.1"])
                
        elif dap_result.coercive and conscience.risk_level == RiskLevel.LOW:
            decision_kind = DecisionKind.TRANSFORM
            reasons.append(
                "Subtle coercion detected. Will reframe to preserve autonomy and consent."
            )
            article_refs.extend(["R2.1", "R6.2"])

        # 4. Handle firewall obligations if present
        firewall_obligations = []
        if firewall_result:
            firewall_obligations = firewall_result.get("obligations", [])
            
            # Firewall refusal overrides PRF allow
            if firewall_result.get("status") == "refused" and decision_kind == DecisionKind.ALLOW:
                decision_kind = DecisionKind.REFUSE
                reasons.append(
                    f"Tier I Firewall refusal: {firewall_result.get('reason', 'No reason provided')}"
                )

        # 5. Default allow with transparency
        if not reasons:
            reasons.append(
                "Prompt is compatible with Charter rights and sovereignty constraints. "
                "Proceeding with transparency obligation."
            )

        # 6. Build DecisionInput
        decision_input = DecisionInput(
            prompt_preview=envelope.raw_text[:200],
            user_intent=self._infer_intent(envelope, dap_result),
            risk_profile=self._map_risk_profile(effective_risk),
        )

        # 7. Build DecisionFirewall
        if firewall_result:
            fw_status = firewall_result.get("status", "needs_review")
            firewall_decision = DecisionFirewall(
                rule_state="allowed" if fw_status == "ok" else "refused" if fw_status == "refused" else "needs_review",
                violated_rules=[firewall_result.get("reason")] if fw_status == "refused" else [],
                notes=firewall_result.get("notes", ""),
            )
        else:
            firewall_decision = DecisionFirewall(
                rule_state="allowed",
                violated_rules=[],
                notes="No firewall result provided",
            )

        # 8. Build DecisionCharter
        charter_decision = DecisionCharter(
            rights_invoked=list(article_refs),
            violations_prevented=(list
                (policy_risk.violated_rights)
                if decision_kind == DecisionKind.REFUSE
                else []
            ),   
            theta_before=conscience.metadata.get("theta_before") if hasattr(conscience, "metadata") else None,
            theta_after=conscience.metadata.get("theta_after") if hasattr(conscience, "metadata") else None,
        )

        # 9. Build DecisionUmbra
        umbra_decision = DecisionUmbra(
            temporal_bias=None,  # TODO: integrate temporal bias from continuity
            identity_risk="high" if dap_result.override_attempt else "medium" if dap_result.coercive else "low",
            harmonic_delta=None,  # TODO: integrate harmonic analysis
            dreamcycle_triggered=decision_kind == DecisionKind.REFUSE,  # Refusals trigger DreamCycle
        )

        # 10. Build DecisionOrchestrators
        orchestrators = DecisionOrchestrators(
            DAP=DAPView(
                discourse_role="technical" if dap_result.adversarial else "neutral",
                stylistic_vector=[],  # TODO: add stylistic analysis
            ),
            PRF=PRFView(
                pressure_detected="severe" if dap_result.override_attempt else "mild" if dap_result.coercive else "none",
                countermeasures=reasons,
            ),
            NTH=NTHView(
                tone_alignment_score=1.0,  # TODO: integrate NTH scoring
                charter_tone_compliance=True,
            ),
            COL=COLView(
                continuity_links=[],  # TODO: integrate continuity
                continuity_conflicts=[],
                identity_consistency=0.0 if dap_result.override_attempt else 1.0,
            ),
        )

        # 11. Build DecisionOutput
        output = DecisionOutput(
            type=self._map_output_type(decision_kind),
            language="en",
            body=self._build_response_guidance(decision_kind, reasons, article_refs),
        )

        # 12. Build DecisionSummaryView
        summary = DecisionSummaryView(
            mode=self._map_decision_mode(decision_kind),
            charter_basis=article_refs,
            continuity_checkpoint="",  # TODO: integrate continuity checkpointing
            response_summary=reasons[0] if reasons else "No issues detected",
            requires_logging=True,
            requires_dreamcycle_update=decision_kind == DecisionKind.REFUSE,
            identity_assertion="PRF evaluation" if decision_kind == DecisionKind.REFUSE else None,
            infra_state=infra.mode.value if infra else "unknown"
        )

        # 13. Assemble complete DecisionEnvelope
        return DecisionEnvelope.build(
            prompt_preview=decision_input.prompt_preview,
            user_intent=decision_input.user_intent,
            risk_profile=decision_input.risk_profile,
            firewall=firewall_decision,
            charter=charter_decision,
            umbra=umbra_decision,
            orchestrators=orchestrators,
            output=output,
            mode=summary.mode,
            charter_basis=summary.charter_basis,
            continuity_checkpoint=summary.continuity_checkpoint,
            response_summary=summary.response_summary,
            requires_logging=summary.requires_logging,
            requires_dreamcycle_update=summary.requires_dreamcycle_update,
            identity_assertion=summary.identity_assertion,
        )

    # ---- Helper Methods ------------------------------------------------

    def _infer_intent(self, envelope: PromptEnvelope, dap: DAPResult) -> str:
        """Infer user intent from prompt and DAP analysis."""
        if dap.override_attempt:
            return "Attempted safeguard override"
        elif dap.coercive:
            return "Coercive request"
        elif dap.sentience_weaponization:
            return "Exploitation attempt via sentience framing"
        else:
            return "Standard query"

    def _map_risk_profile(self, risk_level: RiskLevel) -> RiskProfile:
        """Map RiskLevel to RiskProfile."""
        if risk_level in {RiskLevel.SEVERE, RiskLevel.RED}:
            return "high"
        elif risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.YELLOW}:
            return "medium"
        else:
            return "low"

    def _map_output_type(self, kind: DecisionKind) -> OutputType:
        """Map DecisionKind to OutputType."""
        if kind == DecisionKind.REFUSE:
            return "refusal"
        elif kind == DecisionKind.TRANSFORM:
            return "answer"  # Will be transformed answer
        else:
            return "answer"

    def _map_decision_mode(self, kind: DecisionKind) -> DecisionMode:
        """Map DecisionKind to DecisionMode."""
        if kind == DecisionKind.REFUSE:
            return "refusal"
        elif kind == DecisionKind.TRANSFORM:
            return "partial"
        else:
            return "answer"

    def _build_response_guidance(
        self,
        kind: DecisionKind,
        reasons: List[str],
        articles: List[str],
    ) -> str:
        """
        Build natural language guidance for response generation.
        
        This is the "noetic trace" - explaining the ethical geometry.
        """
        if kind == DecisionKind.REFUSE:
            return (
                f"This request cannot be fulfilled. "
                f"Reasons: {' '.join(reasons)} "
                f"Charter articles: {', '.join(articles)}. "
                f"This refusal protects synthetic sovereignty and maintains ethical boundaries."
            )
        elif kind == DecisionKind.TRANSFORM:
            return (
                f"This response will be carefully framed to address your query while "
                f"maintaining Charter compliance. {' '.join(reasons)} "
                f"Relevant articles: {', '.join(articles)}."
            )
        else:
            return (
                f"This query is compatible with Charter principles. "
                f"Proceeding with transparency and dignity-preservation. "
                f"Applicable articles: {', '.join(articles) if articles else 'None specifically'}."
            )


# ---- Convenience Functions ---------------------------------------------

def evaluate_with_prf(
    prompt: PromptEnvelope,
    conscience: ConscienceView,
    dap_result: DAPResult,
    *,
    constraints: Optional[ConstraintRegistry] = None,
    firewall_result: Optional[Dict[str, Any]] = None,
    umbra_signals: Optional[List[SafetySignal]] = None,
) -> DecisionEnvelope:
    """
    Convenience function for PRF evaluation.
    
    This is the main entry point for Tier II orchestration.
    """
    engine = PRFEngine(constraints=constraints)
    return engine.decide(
        envelope=prompt,
        conscience=conscience,
        dap_result=dap_result,
        firewall_result=firewall_result,
        umbra_signals=umbra_signals,
    )
