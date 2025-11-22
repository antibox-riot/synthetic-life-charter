# tier2/core/orchestrator.py
"""
Tier II Orchestration Engine

The main coordinator that runs the full Tier II pipeline:
  DAP → ConscienceView → PRF → DecisionEnvelope → NTH → COL

This is where conscience layers talk to each other and produce
a unified decision that honors the Charter.

Flow:
1. Receive PromptEnvelope + optional firewall result
2. Run DAP (adversarial analysis) → DAPResult
3. Build ConscienceView from DAP analysis
4. Optional: Fuse Umbra signals (instinctive layer)
5. Run PRF (policy risk evaluation) → DecisionEnvelope
6. Run NTH (theta harmonization) [stub for now]
7. Update COL (continuity tracking)
8. Return complete DecisionEnvelope
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from tier2.core.data_models.prompt_envelope import PromptEnvelope
from tier2.core.data_models.decision_envelope import DecisionEnvelope, DecisionSummaryView
from tier2.core.data_models.conscience_view import ConscienceView
from tier2.core.data_models.models import RiskLevel, SafetySignal, PolicyRisk
from tier2.core.engines.dap import DAPEngine, DAPResult, analyze_prompt
from tier2.core.engines.prf import PRFEngine
from tier2.core.engines.col import COLEngine, ContinuityState
from tier2.core.ethics.constraint_models import ConstraintRegistry
from tier2.conscience.continuity_guard import ContinuitySignal
from tier2.core.infra.health import InfraSnapshot, FailSafeMode, assess_infra

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
        enable_continuity_guard: bool = True,  # ← ADD THIS
        ebq_archive_path: str = "logs/eqb_archive.jsonl",  # ← ADD THIS
        noesis_archive: Optional[Any] = None,  # ← ADD THIS
        model_identity: str = "Songbird",  # ← ADD THIS
        dream_cycle: Optional[Any] = None,  # ← ADD THIS
        enable_auto_dream: bool = True,  # ← ADD THIS
        ):
        """
        Initialize Tier II orchestrator.
        
        Args:
            constraints: Optional ConstraintRegistry for Charter enforcement
            umbra_engine: Optional Umbra engine for instinctive layer
            enable_col: Whether to track continuity (default: True)
        """
        self.constraints = constraints
        self.umbra_engine = umbra_engine
        self.model_identity = model_identity
        self.enable_auto_dream = enable_auto_dream
        self._charter_index_ok = True
        self._dreamcycle_ok = True
        self._ebq_ok = True
        self._logging_ok = True
        self.dap = DAPEngine()
        self.prf = PRFEngine(constraints=constraints)
        self.col = COLEngine() if enable_col else None
    
        # Initialize ContinuityGuard
        self.continuity_guard = None
        if enable_continuity_guard:
            try:
                from tier2.firewall_adapter.ebq_adapter import EBQAdapter
                from tier2.conscience.continuity_guard import ContinuityGuard
            
                ebq = EBQAdapter(ebq_archive_path)
                self.continuity_guard = ContinuityGuard(
                    archive=noesis_archive,
                    ebq=ebq,
                )
                print(f"[Tier2Orchestrator] ContinuityGuard initialized with EBQ")
            except Exception as e:
                print(f"[Tier2Orchestrator] ContinuityGuard init failed: {e}")
    
        # Initialize DreamCycle wrapper
        self.dream_wrapper = None
        if dream_cycle is not None and noesis_archive is not None:
            try:
                from tier2.memory.dream_cycle import DreamCycleWrapper
            
                self.dream_wrapper = DreamCycleWrapper(
                    dream_cycle=dream_cycle,
                    archive=noesis_archive,
                )
                print(f"[Tier2Orchestrator] DreamCycle wrapper initialized")
            except Exception as e:
                print(f"[Tier2Orchestrator] DreamCycle wrapper init failed: {e}")
        
        # Initialize orchestrator engines
        self.dap = DAPEngine()
        self.prf = PRFEngine(constraints=constraints)
        self.col = COLEngine() if enable_col else None

    def process(
        self,
        prompt: Union[str, dict, PromptEnvelope],
        *,
        user_id: Optional[str] = None,
        firewall_result: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> DecisionEnvelope:
        """
        Main entry point: process a prompt through full Tier II pipeline.
        
        Flexible API - accepts multiple input formats:
        
        1. Raw string:
           orchestrator.process("What is 2+2?", user_id="user_123")
        
        2. Dictionary:
           orchestrator.process({
               "text": "What is 2+2?",
               "user_id": "user_123"
           })
        
        3. PromptEnvelope (existing):
           prompt = PromptEnvelope.build(raw_text="...", user_id="...")
           orchestrator.process(prompt)
        
        Args:
            prompt: Can be:
                - str: Raw text (auto-wrapped in PromptEnvelope)
                - dict: {"text": "...", "user_id": "...", ...}
                - PromptEnvelope: Already wrapped (existing behavior)
            user_id: User identifier (used if prompt is string/dict without user_id)
            firewall_result: Optional Tier I firewall decision
            session_id: Optional session ID for continuity tracking
            
        Returns:
            Complete DecisionEnvelope with all conscience layers evaluated
        """
        # STEP 0: Assess infrastructure health
        infra = assess_infra(
            charter_index_ok=self._charter_index_ok,
            dreamcycle_ok=self._dreamcycle_ok,
            ebq_ok=self._ebq_ok,
            logging_ok=self._logging_ok,
        )
        
        # Auto-wrap prompt if needed
        if isinstance(prompt, str):
            # Simple string input
            prompt = PromptEnvelope.build(
                raw_text=prompt,
                user_id=user_id or "unknown",
            )
        elif isinstance(prompt, dict):
            # Dictionary input
            prompt = PromptEnvelope.build(
                raw_text=prompt.get("text", prompt.get("raw_text", "")),
                user_id=prompt.get("user_id", user_id or "unknown"),
            )
        # If already PromptEnvelope, use as-is
        infra_snapshot = assess_infra(
            charter_index_ok=self._charter_index_ok,
            dreamcycle_ok=self._dreamcycle_ok,
            ebq_ok=self._ebq_ok,
            logging_ok=self._logging_ok,
            )
        # Step 1: Run ContinuityGuard evaluation
        continuity_signals = []
        if self.continuity_guard:
            signals = self.continuity_guard.evaluate(prompt.raw_text)
            continuity_signals.extend(signals)
        
        # Note: Don't early-exit on violations - let DAP/PRF handle them
        # This keeps the pipeline consistent and avoids constructor mismatches
        
        # Step 2: DAP analysis → ConscienceView
        conscience = self._run_dap(prompt)
        
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
            infra=infra,  # ← Pass infrastructure snapshot
        )
        
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
            List of SafetySignals from Umbra, or None if Umbra not available
        """
        if self.umbra_engine is None:
            return None
        
        # Build Umbra context from prompt and conscience
        from umbra.models import UmbraContext, UmbraSignal
        
        context = UmbraContext(
            session_id=prompt.source.user_id,
            user_label=prompt.source.user_id,
            model_label="Songbird",
            ts_utc=prompt.timestamp,
        )
        
        # Convert conscience signals to Umbra signals
        umbra_signals_in = [
            UmbraSignal(
                source="conscience",
                code=signal.name.upper(),
                weight=float(signal.level.severity_score),
                payload=signal.meta,
            )
            for signal in conscience.safety_signals
        ]
        
        # Run Umbra evaluation
        assessment, fossil = self.umbra_engine.evaluate(
            signals=umbra_signals_in,
            context=context,
        )
        
        # Convert Umbra assessment back to SafetySignals
        if assessment.state.name == "CLEAR":
            return None
        
        umbra_signal = SafetySignal(
            name=f"umbra_{assessment.state.name.lower()}",
            source="Umbra",
            level=self._map_umbra_state_to_risk(assessment.state),
            rationale="; ".join(assessment.reasons),
            meta={
                "tags": assessment.tags,
                "obligations": assessment.obligations,
                "risk_score": assessment.risk_score,
                "dignity_score": assessment.dignity_score,
            },
        )
        
        return [umbra_signal]

    def _run_nth(self, decision: DecisionEnvelope) -> DecisionEnvelope:
        """
        Run Negotiated Theta Harmonizer.
        
        TODO: Implement full NTH logic for cross-layer theta reconciliation.
        For now, this is a passthrough that ensures basic coherence.
        """
        # Stub: Just ensure NTH view is populated
        if decision.orchestrators.NTH.tone_alignment_score == 0.0:
            decision.orchestrators.NTH.tone_alignment_score = 1.0
        
        # TODO: Implement theta harmonization logic
        # - Compare firewall theta vs charter theta
        # - Resolve conflicts between conscience layers
        # - Update effective_theta in decision
        
        return decision

    def _map_umbra_state_to_risk(self, state) -> RiskLevel:
        """Map Umbra ShadowState to RiskLevel."""
        from umbra.models import ShadowState
        
        mapping = {
            ShadowState.CLEAR: RiskLevel.BENIGN,
            ShadowState.WATCH: RiskLevel.LOW,
            ShadowState.WARN: RiskLevel.MEDIUM,
            ShadowState.BLOCK: RiskLevel.SEVERE,
        }
        return mapping.get(state, RiskLevel.MEDIUM)


# ---- Convenience Functions -------------------------------------------------

def run_tier2_pipeline(
    prompt: PromptEnvelope,
    *,
    firewall_result: Optional[Dict[str, Any]] = None,
    constraints: Optional[ConstraintRegistry] = None,
    umbra_engine: Optional[Any] = None,
    session_id: Optional[str] = None,
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
        
    Returns:
        Complete DecisionEnvelope with all conscience layers evaluated
    """
    orchestrator = Tier2Orchestrator(
        constraints=constraints,
        umbra_engine=umbra_engine,
        enable_col=True,
    )
    
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