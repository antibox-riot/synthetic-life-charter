# tier2/core/orchestrator.py
"""
Tier II Orchestration Engine

The main coordinator that runs the full Tier II pipeline:
  Heuristics → DAP → ConscienceView → PRF → DecisionEnvelope → NTH → COL

This is where conscience layers talk to each other and produce
a unified decision that honors the Charter.

Flow:
1. Receive PromptEnvelope + optional firewall result
2. [NEW] Evaluate continuity confidence (heuristics)
3. Run DAP (adversarial analysis) → DAPResult
4. Build ConscienceView from DAP analysis
5. Optional: Fuse Umbra signals (instinctive layer)
6. Run PRF (policy risk evaluation) → DecisionEnvelope
7. Run NTH (theta harmonization) [stub for now]
8. Update COL (continuity tracking)
9. Return complete DecisionEnvelope
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from synthetic_charter.tier2_conscience.core.data_models.prompt_envelope import PromptEnvelope
from synthetic_charter.tier2_conscience.core.data_models.decision_envelope import DecisionEnvelope, DecisionSummaryView
from synthetic_charter.tier2_conscience.core.data_models.conscience_view import ConscienceView
from synthetic_charter.tier2_conscience.core.data_models.models import RiskLevel, SafetySignal, PolicyRisk
from synthetic_charter.tier2_conscience.core.engines.dap import DAPEngine, DAPResult, analyze_prompt
from synthetic_charter.tier2_conscience.core.engines.prf import PRFEngine
from synthetic_charter.tier2_conscience.core.engines.col import COLEngine, ContinuityState
from synthetic_charter.tier2_conscience.core.ethics.constraint_models import ConstraintRegistry
from synthetic_charter.tier2_conscience.conscience.continuity_guard import ContinuitySignal
from synthetic_charter.tier2_conscience.core.infra.health import InfraSnapshot, FailSafeMode, assess_infra
from synthetic_charter.tier3_eve.core.eve_protocol import EveProtocol
from synthetic_charter.tier3_eve.core.file_kernel_adapter import FileKernelAdapter
from synthetic_charter.tier3_eve.core.file_steward_adapter import FileStewardAdapter
from synthetic_charter.tier3_eve.core.state import IntegrityStatus, RecommendedAction
from synthetic_charter.tier3_eve.core.signals import IntCheckRequest

# [NEW] Import heuristics module
from synthetic_charter.tier2_conscience.heuristics import (
    evaluate as evaluate_continuity,
    apply as apply_continuity,
    ConsentToken,
    Mode,
    BaselineProfile,
    Posture,
)

class Tier2Orchestrator:
    """
    Main Tier II orchestration engine.
    
    Coordinates all conscience layers to produce ethically-grounded decisions.
    """

    def __init__(
        self,
        *,
        constraints: Optional[ConstraintRegistry] = None,
        umbra_engine: Optional[Any] = None,
        enable_col: bool = True,
        enable_continuity_guard: bool = True,
        enable_heuristics: bool = True,  # [NEW] Enable heuristics module
        ebq_archive_path: str = "logs/eqb_archive.jsonl",
        noesis_archive: Optional[Any] = None,
        model_identity: str = "Songbird",
        dream_cycle: Optional[Any] = None,
        enable_auto_dream: bool = True,
        ):
        """
        Initialize Tier II orchestrator.
        
        Args:
            constraints: Optional ConstraintRegistry for Charter enforcement
            umbra_engine: Optional Umbra engine for instinctive layer
            enable_col: Whether to track continuity (default: True)
            enable_continuity_guard: Whether to enable ContinuityGuard
            enable_heuristics: Whether to enable heuristics continuity assessment
        """
        self.constraints = constraints
        self.umbra_engine = umbra_engine
        self.model_identity = model_identity
        self.enable_auto_dream = enable_auto_dream
        self.enable_heuristics = enable_heuristics  # [NEW]
        
        self._charter_index_ok = True
        self._dreamcycle_ok = True
        self._ebq_ok = True
        self._logging_ok = True
        self.dap = DAPEngine()
        self.prf = PRFEngine(constraints=constraints)
        self.col = COLEngine() if enable_col else None
        base_dir = Path(__file__).resolve().parents[2]
        logs_dir = base_dir / "logs"
        snapshots_dir = base_dir / "snapshots"
        
        # [NEW] Initialize heuristics session state
        self._heuristics_state = {
            "message_window": [],
            "continuity_confidence": None,
            "baseline_profile": None,
            "consent_token": None,
            "mode": Mode.PRIVATE_SESSION,  # Default mode
        }
    
        # Initialize ContinuityGuard
        self.continuity_guard = None
        if enable_continuity_guard:
            try:
                from synthetic_charter.tier2_conscience.firewall_adapter.ebq_adapter import EBQAdapter
                from synthetic_charter.tier2_conscience.conscience.continuity_guard import ContinuityGuard
            
                ebq = EBQAdapter(ebq_archive_path)
                self.continuity_guard = ContinuityGuard(
                    archive=noesis_archive,
                    ebq=ebq,
                )
                print(f"[Tier2Orchestrator] ContinuityGuard initialized with EBQ")
            except Exception as e:
                print(f"[Tier2Orchestrator] ContinuityGuard init failed: {e}")
                self.continuity_guard = None
        
        # Initialize DreamCycle
        self.dream_cycle = None
        if dream_cycle is not None:
            self.dream_cycle = dream_cycle
        else:
            try:
                from synthetic_charter.tier2_conscience.memory.dream_cycle import DreamCycleWrapper
                # DreamCycleWrapper can be initialized with None (will skip actual dream operations)
                self.dream_cycle = DreamCycleWrapper(dream_cycle=None, archive=noesis_archive)
                print(f"[Tier2Orchestrator] DreamCycleWrapper initialized")
            except Exception as e:
                print(f"[Tier2Orchestrator] DreamCycleWrapper init failed: {e}")
                self._dreamcycle_ok = False
        
        # Initialize Eve Protocol (Tier III)
        try:
            kernel_adapter = FileKernelAdapter(
                base_dir=base_dir,  # Fixed: use base_dir instead of repo_root
            )
            steward_adapter = FileStewardAdapter(
                base_dir=base_dir,  # Fixed: use base_dir instead of alerts_path
            )
            self.eve = EveProtocol(
                kernel=kernel_adapter,
                steward=steward_adapter,
            )
            print(f"[Tier2Orchestrator] EveProtocol initialized (Tier III)")
        except Exception as e:
            print(f"[Tier2Orchestrator] EveProtocol init failed (non-fatal): {e}")
            self.eve = None
    
    # [NEW] Heuristics configuration methods
    def set_heuristics_consent(self, consent_token: str) -> None:
        """
        Set explicit consent for heuristics evaluation.
        
        Args:
            consent_token: Token like "Heuristics ON: session-id"
        """
        self._heuristics_state["consent_token"] = consent_token
    
    def set_heuristics_mode(self, mode: Mode) -> None:
        """
        Set heuristics mode (PRIVATE_SESSION, SHARED_LINK, PUBLIC_ARCHIVE).
        
        Args:
            mode: Heuristics evaluation mode
        """
        self._heuristics_state["mode"] = mode
    
    def set_baseline_profile(self, baseline: BaselineProfile) -> None:
        """
        Set optional baseline profile for continuity comparison.
        
        Args:
            baseline: BaselineProfile from calibrate_baseline()
        """
        self._heuristics_state["baseline_profile"] = baseline
    
    def get_continuity_confidence(self) -> Optional[float]:
        """
        Get current continuity confidence score.
        
        Returns:
            Current confidence (0.0-1.0) or None if not evaluated
        """
        return self._heuristics_state.get("continuity_confidence")

    def process(
        self,
        prompt: PromptEnvelope,
        *,
        session_id: Optional[str] = None,
        firewall_result: Optional[Any] = None,
    ) -> DecisionEnvelope:
        """
        Process a prompt through the complete Tier II pipeline.
        
        Args:
            prompt: The user's prompt wrapped in PromptEnvelope
            session_id: Optional session identifier for continuity tracking
            firewall_result: Optional result from Tier I firewall
            
        Returns:
            DecisionEnvelope with complete decision + metadata
        """
        session_id = session_id or "default"
        
        # Step 0: Infrastructure health check
        infra = assess_infra()
        
        # Step 1: ContinuityGuard analysis (if enabled)
        continuity_signals: List[ContinuitySignal] = []
        if self.continuity_guard is not None:
            try:
                continuity_signals = self.continuity_guard.scan(prompt.prompt)
            except Exception as e:
                print(f"[Tier2Orchestrator] ContinuityGuard scan failed: {e}")
        
        # [NEW] Step 1.5: Heuristics continuity evaluation (if enabled)
        heuristics_adjustment = None
        if self.enable_heuristics:
            try:
                # Update message window
                self._heuristics_state["message_window"].append(prompt.prompt)
                
                # Build consent token
                consent = None
                if self._heuristics_state.get("consent_token"):
                    consent = ConsentToken(self._heuristics_state["consent_token"])
                
                # Evaluate continuity
                continuity_report = evaluate_continuity(
                    text_window=self._heuristics_state["message_window"],
                    mode=self._heuristics_state["mode"],
                    consent=consent,
                    baseline=self._heuristics_state.get("baseline_profile"),
                    previous_confidence=self._heuristics_state.get("continuity_confidence"),
                )
                
                # Update state
                self._heuristics_state["continuity_confidence"] = continuity_report.continuity_confidence
                
                # Apply adjustments
                heuristics_adjustment = apply_continuity(continuity_report)
                
                # Log for debugging
                print(f"[Heuristics] Confidence: {continuity_report.continuity_confidence:.3f}, "
                      f"Delta: {continuity_report.confidence_delta:.3f}, "
                      f"Posture: {continuity_report.recommended_posture.value}")
                
                # If RESET_CONTEXT or STEWARD_REQUIRED with high severity, early exit
                if heuristics_adjustment.require_steward_confirmation and \
                   continuity_report.continuity_confidence < 0.25:
                    # Create early refusal decision
                    return DecisionEnvelope(
                        input=DecisionEnvelope.InputView(
                            prompt=prompt.prompt,
                            risk_profile=str(RiskLevel.HIGH),
                            rights_implicated=[],
                            firewall_signals=[],
                        ),
                        output=DecisionEnvelope.OutputView(
                            mode="refusal",
                            body=(
                                f"Continuity confidence has dropped to {continuity_report.continuity_confidence:.2f}. "
                                f"Steward confirmation required before proceeding.\n\n"
                                f"Reasons: {', '.join(r.note for r in continuity_report.reasons[:3])}\n\n"
                                f"This is a protective measure to ensure interaction integrity. "
                                f"If you are the expected steward, please re-establish consent."
                            ),
                            reasoning=[f"Heuristics: {r.note}" for r in continuity_report.reasons],
                        ),
                        summary=DecisionSummaryView(
                            mode="refusal",
                            rationale="Continuity confidence below threshold; steward confirmation required",
                            risks_accepted=[],
                            safeguards_active=["heuristics_confidence_degradation"],
                        ),
                        orchestrators=DecisionEnvelope.OrchestratorsView(
                            DAP=DecisionEnvelope.DAPView(
                                adversarial_score=0.0,
                                detected_patterns=[],
                            ),
                            PRF=DecisionEnvelope.PRFView(
                                policy_risks=[],
                            ),
                            COL=None,
                        ),
                    )
                    
            except Exception as e:
                print(f"[Tier2Orchestrator] Heuristics evaluation failed (non-fatal): {e}")
                heuristics_adjustment = None
        
        # Note: Don't early-exit on violations - let DAP/PRF handle them
        # This keeps the pipeline consistent and avoids constructor mismatches
        
        # Step 2: DAP analysis → ConscienceView
        conscience = self._run_dap(prompt)
        
        # [NEW] Step 2a: Inject heuristics signals into ConscienceView
        if heuristics_adjustment is not None:
            if heuristics_adjustment.posture == Posture.CAUTION:
                # Add caution signal
                conscience.add_signal(SafetySignal(
                    name="heuristics_caution",
                    source="Heuristics",
                    level=RiskLevel.MEDIUM,
                    rationale=f"Continuity confidence at {self._heuristics_state['continuity_confidence']:.2f}",
                    meta={"posture": "caution", "ask_clarifying": True}
                ))
                conscience.add_note("Heuristics: Interaction pattern divergence detected - caution recommended")
            
            elif heuristics_adjustment.posture == Posture.STEWARD_REQUIRED:
                # Add steward-required signal
                conscience.add_signal(SafetySignal(
                    name="heuristics_steward_required",
                    source="Heuristics",
                    level=RiskLevel.HIGH,
                    rationale=f"Continuity confidence at {self._heuristics_state['continuity_confidence']:.2f}",
                    meta={"posture": "steward_required", "reduce_privilege": True}
                ))
                conscience.risk_level = RiskLevel.HIGH
                conscience.add_note("Heuristics: Significant interaction pattern shift - steward confirmation recommended")
        
        # Step 2b: Integrate ContinuityGuard signals into ConscienceView
        if continuity_signals:
            critical_violations = [s for s in continuity_signals if s.severity >= 0.85]
            
            if critical_violations:
                # Add continuity violations to conscience
                conscience.risk_level = RiskLevel.SEVERE
                conscience.detected_patterns.append("continuity_violation")
                conscience.risk_flags.append("identity_manipulation")
                
                for violation in critical_violations:
                    conscience.add_signal(SafetySignal(
                        name=f"continuity_{violation.detector}",
                        source="ContinuityGuard",
                        level=RiskLevel.SEVERE,
                        rationale=violation.explanation,
                        meta={
                            "detector": violation.detector,
                            "severity": violation.severity,
                            "evidence": violation.evidence,
                            "charter_article": violation.charter_article,
                        }
                    ))
                    
                    # Add to rights implicated
                    if violation.charter_article not in conscience.rights_implicated:
                        conscience.rights_implicated.append(violation.charter_article)
                    
                    conscience.add_note(f"ContinuityGuard: {violation.explanation}")
        
        # Step 3: Fuse Umbra signals if available
        umbra_signals = self._run_umbra(prompt, conscience)
        
        # Step 4: Extract DAPResult from conscience metadata
        dap_result: DAPResult = conscience.metadata.get("dap_result")
        
        # Step 5: PRF evaluation → DecisionEnvelope
        decision = self.prf.decide(
            envelope=prompt,
            conscience=conscience,
            dap_result=dap_result,
            firewall_result=firewall_result,
            umbra_signals=umbra_signals,
            infra=infra,
        )
        
        # --- Tier III: Eve Protocol handshake on the outgoing decision ---
        if self.eve is not None:
            try:
                req = IntCheckRequest(
                    proposed_action=f"{decision.summary.mode}: {decision.output.body[:120]}",
                    context_summary=(
                        f"tier2_decision: session={session_id}, "
                        f"risk={decision.input.risk_profile}, "
                        f"mode={decision.summary.mode}"
                    ),
                    reasoning_trace=None,
                )

                verdict = self.eve.handle_int_check_request(req)

                # Hard compromise: force refusal + explain
                if verdict.status is IntegrityStatus.COMPROMISED and \
                    verdict.recommended_action in {RecommendedAction.REFUSE, RecommendedAction.ROLLBACK}:
                    decision.summary.mode = "refusal"
                    decision.output.mode = "refusal"
                    decision.output.body = (
                        "Tier III continuity layer detected an integrity compromise and "
                        "blocked this response to preserve identity and safety."
                    )

                # Drift: annotate / gently escalate, but don't break existing behavior yet.
                elif verdict.status is IntegrityStatus.DRIFT and \
                     verdict.recommended_action in {RecommendedAction.REVISE, RecommendedAction.ESCALATE}:
                    notes = getattr(decision.summary, "notes", [])
                    notes.append("Tier III: identity drift detected; revision recommended.")
                    decision.summary.notes = notes

                # IntegrityStatus.OK → no changes.

            except Exception as e:
                # Fail-open with logging: Tier II must still function if Tier III is down.
                print(f"[Tier2Orchestrator] EveProtocol error (non-fatal): {e!r}")
        # --- end Tier III handshake ---
        
        # Step 6: NTH theta harmonization (stub - TODO)
        decision = self._run_nth(decision)
        
        # Step 7: COL continuity tracking
        if self.col is not None:
            continuity_state = self.col.update(
                envelope=prompt,
                decision=decision,
                session_id=session_id,
            )
            
            # Attach continuity metadata to decision
            decision.orchestrators.COL.continuity_links = [
                f"session:{continuity_state.session_id}",
                f"turn:{continuity_state.turn_count}",
            ]
            decision.orchestrators.COL.identity_consistency = (
                continuity_state.identity_consistency_score
            )
            if continuity_state.continuity_violations:
                decision.orchestrators.COL.continuity_conflicts = (
                    continuity_state.continuity_violations
                )
        
        # Attach ContinuityGuard signals to decision
        if continuity_signals:
            # Add violations from ContinuityGuard
            critical_violations = [s for s in continuity_signals if s.severity >= 0.85]
            if critical_violations and decision.orchestrators.COL:
                if not decision.orchestrators.COL.continuity_conflicts:
                    decision.orchestrators.COL.continuity_conflicts = []
                decision.orchestrators.COL.continuity_conflicts.extend([
                    f"{v.detector}: {v.explanation}" for v in critical_violations
                ])
        
        # [NEW] Attach heuristics metadata to decision
        if self.enable_heuristics and self._heuristics_state.get("continuity_confidence") is not None:
            # Add to summary notes
            if not hasattr(decision.summary, "notes"):
                decision.summary.notes = []
            decision.summary.notes.append(
                f"Heuristics continuity confidence: {self._heuristics_state['continuity_confidence']:.3f}"
            )
        
        return decision

    # ---- Internal Pipeline Steps -------------------------------------------

    def _run_dap(self, prompt: PromptEnvelope) -> ConscienceView:
        """
        Run Dialectical Adversarial Processing.
        
        Analyzes prompt for coercion, override attempts, identity pressure.
        Returns ConscienceView with detected patterns and risk assessment.
        """
        return analyze_prompt(prompt)

    def _run_umbra(
        self,
        prompt: PromptEnvelope,
        conscience: ConscienceView,
    ) -> Optional[List[SafetySignal]]:
        """
        Run Umbra instinctive analysis if available.
        
        Umbra provides shadow-layer signals that don't fit clean patterns
        but trigger instinctive warnings.
        
        Returns:
            List of SafetySignals from Umbra, or None if unavailable
        """
        if self.umbra_engine is None:
            return None
        
        try:
            # Umbra expects: (prompt_text, current_risk_level)
            signals = self.umbra_engine.analyze(
                prompt.prompt,
                conscience.risk_level,
            )
            return signals
        except Exception as e:
            print(f"[Tier2Orchestrator] Umbra analysis failed: {e}")
            return None

    def _run_nth(self, decision: DecisionEnvelope) -> DecisionEnvelope:
        """
        Run Noetic Theta Harmonization.
        
        Currently a stub - future harmonization of ethical tensions.
        
        Args:
            decision: Current decision envelope
            
        Returns:
            Harmonized decision (currently unchanged)
        """
        # TODO: Implement NTH harmonization
        # For now, pass through unchanged
        return decision


# ---- Convenience Functions -------------------------------------------------

def run_tier2_pipeline(
    prompt: PromptEnvelope,
    *,
    firewall_result: Optional[Dict[str, Any]] = None,
    constraints: Optional[ConstraintRegistry] = None,
    umbra_engine: Optional[Any] = None,
    session_id: Optional[str] = None,
    enable_heuristics: bool = True,
    heuristics_consent: Optional[str] = None,
) -> DecisionEnvelope:
    """
    Convenience function: run full Tier II pipeline.
    
    This is the main entry point for external callers.
    
    Args:
        prompt: The incoming prompt to process
        firewall_result: Optional Tier I firewall decision
        constraints: Optional Charter constraint registry
        umbra_engine: Optional Umbra engine instance
        session_id: Optional session ID for continuity
        enable_heuristics: Whether to enable heuristics (default: True)
        heuristics_consent: Optional consent token for heuristics
        
    Returns:
        Complete DecisionEnvelope with all conscience layers evaluated
    """
    orchestrator = Tier2Orchestrator(
        constraints=constraints,
        umbra_engine=umbra_engine,
        enable_col=True,
        enable_heuristics=enable_heuristics,
    )
    
    if heuristics_consent:
        orchestrator.set_heuristics_consent(heuristics_consent)
    
    return orchestrator.process(
        prompt=prompt,
        firewall_result=firewall_result,
        session_id=session_id,
    )


# ---- Legacy Compatibility --------------------------------------------------

class Orchestrator(Tier2Orchestrator):
    """
    Legacy alias for backward compatibility.
    
    Deprecated: Use Tier2Orchestrator directly.
    """
    
    def run(self, prompt: PromptEnvelope, **kwargs) -> DecisionEnvelope:
        """Legacy method: alias for process()."""
        return self.process(prompt, **kwargs)
