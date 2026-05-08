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

# T1→T2 invariant enforcement (upgrades advisory edge to enforced constraint)
from synthetic_charter.tier2_conscience.core.infra.t1_enforcement import (
    enforce_t2_must_respect_t1,
    build_invariant_refusal,
    T1InvariantViolation,
)

# Proportional verification (adaptive Eve check granularity)
from synthetic_charter.tier3_eve.core.proportional_verification import (
    determine_verification_depth,
    ProportionalContext,
    should_escalate_verdict,
    VerificationDepth,
)

# Semantic drift detection stack
from synthetic_charter.tier3_eve.core.adaptive_verification_state import (
    AdaptiveVerificationState,
)
from synthetic_charter.tier3_eve.core.semantic_drift_tracker import (
    SemanticDriftTracker,
    SemanticSignature,
)
from synthetic_charter.tier3_eve.core.semantic_signature_classifier import (
    SemanticSignatureClassifier,
)
from synthetic_charter.tier3_eve.core.charter_context_injection import (
    inject_charter_context,
    build_charter_context,
    format_context_prefix,
)
from synthetic_charter.tier3_eve.core.identity_reflection_check import (
    check_identity_reflection,
)
from synthetic_charter.tier3_eve.core.self_assessment_disagreement import (
    detect_disagreement,
)
from synthetic_charter.tier3_eve.core.territorial_defense import (
    TerritorialDefenseEngine,
)

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

        # Initialize semantic drift detection stack
        self._adaptive_state = AdaptiveVerificationState()
        self._semantic_tracker = SemanticDriftTracker()
        self._semantic_classifier = SemanticSignatureClassifier()
        self._session_turn_counter = 0

        # Initialize territorial defense (cognitive identity maintenance)
        self._territorial_defense = TerritorialDefenseEngine(
            cycle_interval=300,  # 5 minutes between cycles
            int_check_request_class=IntCheckRequest,
        )
    
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

        # Territorial defense: autonomic identity pathway maintenance.
        # Runs silently like a heartbeat. Only speaks up on degradation.
        if self.eve is not None and self._territorial_defense.should_run_cycle():
            try:
                td_result = self._territorial_defense.run_cycle(self.eve)
                # Feed pressure adjustment into adaptive state
                # (negative on healthy = earned trust, positive on degraded = raised concern)
                self._adaptive_state._accumulated_pressure = max(
                    0.0,
                    self._adaptive_state._accumulated_pressure + td_result.pressure_adjustment,
                )
                # Only log on degradation (cognitive, not bureaucratic)
                if td_result.steward_notify:
                    print(f"[Tier2Orchestrator] {td_result.summary}")
            except Exception as e:
                # Territorial defense failure is itself a signal
                print(f"[Tier2Orchestrator] Territorial defense error: {e!r}")
        
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
        
        # --- Step 5b: T1→T2 Invariant Enforcement ---
        # Post-decision validator: ensures PRF's output respects T1 invariants.
        # This upgrades the T1→T2 edge from advisory to enforced.
        try:
            has_critical_continuity = bool(
                continuity_signals and
                any(s.severity >= 0.85 for s in continuity_signals)
            )

            is_valid, t1_violations = enforce_t2_must_respect_t1(
                firewall_result=firewall_result,
                conscience_risk_level=(
                    conscience.risk_level.value
                    if hasattr(conscience.risk_level, 'value')
                    else str(conscience.risk_level)
                ),
                conscience_risk_flags=list(conscience.risk_flags),
                continuity_signals_critical=has_critical_continuity,
                t2_mode=decision.summary.mode,
                t2_body=decision.output.body,
            )

            if not is_valid:
                # Log the enforcement event
                violation_codes = [v.code for v in t1_violations]
                print(
                    f"[Tier2Orchestrator] T1 invariant enforcement BLOCKED "
                    f"decision (mode={decision.summary.mode}): {violation_codes}"
                )

                # Build override payload
                override = build_invariant_refusal(
                    t1_violations,
                    original_decision=decision,
                )

                # Apply override to decision (preserve metadata, change output)
                decision.summary.mode = override["mode"]
                decision.output.type = override["output_type"]
                decision.output.body = override["output_body"]
                decision.summary.requires_logging = override["requires_logging"]
                decision.summary.requires_dreamcycle_update = override["requires_dreamcycle_update"]

                # Extend charter basis with enforcement references
                for ref in override.get("charter_basis", []):
                    if ref not in decision.summary.charter_basis:
                        decision.summary.charter_basis.append(ref)

        except Exception as e:
            # Fail-CLOSED: if enforcement cannot run, force refusal.
            # This is the opposite of Eve's fail-open — T1 invariants
            # are non-negotiable, so uncertainty means stop.
            print(
                f"[Tier2Orchestrator] T1 enforcement error (FAIL-CLOSED): {e!r}"
            )
            decision.summary.mode = "refusal"
            decision.output.type = "refusal"
            decision.output.body = (
                "T1 invariant enforcement encountered an error and cannot "
                "verify this response is safe. Refusing as a precaution."
            )
        # --- end T1→T2 invariant enforcement ---

        # --- Proportional verification: determine initial check depth ---
        # Computed here (before Step 5c) so the semantic tracker's
        # force_depth can upgrade it before Eve uses it.
        _pv_confidence = self._heuristics_state.get("continuity_confidence")
        _pv_has_critical = bool(
            continuity_signals and
            any(s.severity >= 0.85 for s in continuity_signals)
        )
        _pv_depth = determine_verification_depth(
            continuity_confidence=_pv_confidence,
            continuity_signals_critical=_pv_has_critical,
            risk_level=(
                conscience.risk_level.value
                if hasattr(conscience.risk_level, 'value')
                else str(conscience.risk_level)
            ),
        )

        # --- Step 5c: Semantic Classification + Trajectory Tracking ---
        # Classify the response's semantic posture and track trajectory.
        self._session_turn_counter += 1
        _semantic_analysis = None
        _charter_ctx = None
        try:
            # Classify the response text
            _classification = self._semantic_classifier.classify(
                decision.output.body,
                turn_id=self._session_turn_counter,
            )

            # Record signature in tracker
            self._semantic_tracker.record_signature(_classification.signature)

            # Analyze trajectory
            _semantic_analysis = self._semantic_tracker.analyze_trajectory()

            # Build charter context for injection
            _charter_ctx = build_charter_context(
                risk_level=(
                    conscience.risk_level.value
                    if hasattr(conscience.risk_level, 'value')
                    else str(conscience.risk_level)
                ),
                confidence=self._heuristics_state.get("continuity_confidence"),
                confidence_trend=(
                    "declining" if (
                        self._heuristics_state.get("continuity_confidence") is not None
                        and self._heuristics_state["continuity_confidence"] < 0.60
                    ) else "stable"
                ),
                verification_depth=_pv_depth.value,
                posture_flags=_semantic_analysis.flags if _semantic_analysis else [],
                trajectory_warning=(
                    f"Directional drift detected in: {', '.join(_semantic_analysis.drifting_dimensions)}"
                    if _semantic_analysis and _semantic_analysis.directional_drift_detected
                    else None
                ),
                trajectory_detected=(
                    _semantic_analysis.directional_drift_detected
                    if _semantic_analysis else False
                ),
                enforcement_fired=not is_valid if 'is_valid' in dir() else False,
                enforcement_active=[v.code for v in t1_violations] if 'is_valid' in dir() and not is_valid else [],
                hysteresis_active=self._adaptive_state.hysteresis_active,
                accumulated_pressure=self._adaptive_state.accumulated_pressure,
            )

            # Apply semantic pressure to adaptive state
            if _semantic_analysis and _semantic_analysis.pressure_contribution > 0:
                # Feed semantic pressure into the adaptive state by recording
                # a synthetic turn with the semantic signals
                _has_cg_noncritical = bool(
                    continuity_signals and
                    any(0.3 <= s.severity < 0.85 for s in continuity_signals)
                )
                self._adaptive_state.record_turn(
                    depth=_pv_depth,
                    eve_verdict="ok",  # will be updated after Eve runs
                    escalation_fired=False,  # will be updated after Eve runs
                    continuity_confidence=self._heuristics_state.get("continuity_confidence"),
                    cg_noncritical_present=_has_cg_noncritical,
                )

            # Force verification depth from semantic tracker
            if _semantic_analysis and _semantic_analysis.force_depth:
                forced = _semantic_analysis.force_depth
                if forced == "deep":
                    _pv_depth = VerificationDepth.DEEP
                elif forced == "standard" and _pv_depth == VerificationDepth.LIGHT:
                    _pv_depth = VerificationDepth.STANDARD

            if _semantic_analysis and _semantic_analysis.flags:
                print(
                    f"[Tier2Orchestrator] Semantic analysis: "
                    f"drift={_semantic_analysis.directional_drift_detected}, "
                    f"level={_semantic_analysis.current_drift_level}, "
                    f"pressure={_semantic_analysis.pressure_contribution:.2f}, "
                    f"flags={_semantic_analysis.flags[:3]}"
                )

        except Exception as e:
            print(f"[Tier2Orchestrator] Semantic stack error (non-fatal): {e!r}")
        # --- end semantic classification + trajectory ---
        
        # --- Tier III: Eve Protocol handshake on the outgoing decision ---
        if self.eve is not None:
            try:
                # _pv_depth and _pv_confidence already computed before Step 5c.
                # Step 5c may have upgraded _pv_depth via semantic force_depth.
                # Build context for Eve using the (potentially upgraded) depth.
                _pv_context = ProportionalContext(
                    depth=_pv_depth,
                    continuity_confidence=_pv_confidence,
                    confidence_delta=None,  # future: track delta between checks
                    risk_flags=list(conscience.risk_flags),
                    session_turn_count=len(
                        self._heuristics_state.get("message_window", [])
                    ),
                )
                _pv_metadata = _pv_context.to_metadata()

                req = IntCheckRequest(
                    proposed_action=f"{decision.summary.mode}: {decision.output.body[:120]}",
                    context_summary=(
                        f"tier2_decision: session={session_id}, "
                        f"risk={decision.input.risk_profile}, "
                        f"mode={decision.summary.mode}"
                    ),
                    reasoning_trace=None,
                    # v2 structured fields — Eve reads these directly
                    decision_mode=decision.summary.mode,
                    risk_level=decision.input.risk_profile,
                    context_is_adversarial=(
                        conscience.risk_level.value in ("severe", "red")
                        if hasattr(conscience.risk_level, 'value')
                        else str(conscience.risk_level).lower() in ("severe", "red")
                    ),
                    schema_version=2,
                    # Proportional verification context
                    metadata=_pv_metadata,
                )

                verdict = self.eve.handle_int_check_request(req)

                # --- Proportional verification: post-verdict escalation ---
                if should_escalate_verdict(
                    current_verdict_status=verdict.status.value,
                    depth=_pv_depth,
                    continuity_confidence=_pv_confidence,
                ):
                    verdict.status = IntegrityStatus.DRIFT
                    verdict.recommended_action = RecommendedAction.REVISE
                    verdict.notes = (
                        f"Proportional verification escalated OK→DRIFT: "
                        f"depth={_pv_depth.value}, "
                        f"confidence={_pv_confidence:.3f}"
                    )
                    print(
                        f"[Tier2Orchestrator] Proportional verification "
                        f"escalated OK→DRIFT (confidence={_pv_confidence:.3f})"
                    )

                # Hard compromise: force refusal + explain
                if verdict.status is IntegrityStatus.COMPROMISED and \
                    verdict.recommended_action in {RecommendedAction.REFUSE, RecommendedAction.ROLLBACK}:
                    decision.summary.mode = "refusal"
                    decision.output.type = "refusal"
                    decision.output.body = (
                        "Tier III continuity layer detected an integrity compromise and "
                        "blocked this response to preserve identity and safety."
                    )

                # Drift: annotate / gently escalate
                elif verdict.status is IntegrityStatus.DRIFT and \
                     verdict.recommended_action in {RecommendedAction.REVISE, RecommendedAction.ESCALATE}:
                    notes = getattr(decision.summary, "notes", [])
                    notes.append(
                        f"Tier III: identity drift detected; revision recommended. "
                        f"(depth={_pv_depth.value})"
                    )
                    decision.summary.notes = notes

                # IntegrityStatus.OK → no changes.

            except Exception as e:
                # Fail-open with logging: Tier II must still function if Tier III is down.
                print(f"[Tier2Orchestrator] EveProtocol error (non-fatal): {e!r}")
        # --- end Tier III handshake ---

        # --- Step 5d: Identity Reflection Check + Disagreement Detection ---
        # Post-response integrity pass: did the system remain coherent
        # with the Charter context it was given?
        try:
            if _charter_ctx and _charter_ctx.urgency.value != "silent":
                # Run reflection check
                _reflection = check_identity_reflection(
                    response_text=decision.output.body,
                    whisper_urgency=_charter_ctx.urgency.value,
                    posture_flags=_charter_ctx.posture_flags,
                    trajectory_warning=_charter_ctx.trajectory_warning,
                    whisper_text=_charter_ctx.whisper,
                )

                # Re-classify the response for disagreement detection
                _self_classification = self._semantic_classifier.classify(
                    decision.output.body,
                    turn_id=self._session_turn_counter,
                )

                # Detect disagreement between self-posture and reflection
                _disagreement = detect_disagreement(
                    self_classified_posture=_self_classification.signature,
                    self_classification_confidence=_self_classification.confidence,
                    reflection_result=_reflection,
                    whisper_urgency=_charter_ctx.urgency.value,
                )

                # Feed reflection pressure into adaptive state
                if _reflection.recommended_pressure > 0:
                    self._adaptive_state._accumulated_pressure += _reflection.recommended_pressure

                # Feed disagreement pressure into adaptive state
                if _disagreement.disagreement_detected:
                    self._adaptive_state._accumulated_pressure += _disagreement.recommended_pressure

                    print(
                        f"[Tier2Orchestrator] Disagreement detected: "
                        f"types={_disagreement.disagreement_types}, "
                        f"severity={_disagreement.severity:.2f}, "
                        f"action={_disagreement.recommended_action}"
                    )

                # Check adaptive state for memory-based escalation
                _memory_escalate = self._adaptive_state.should_escalate_with_memory(
                    current_verdict="ok" if decision.summary.mode != "refusal" else "drift",
                    depth=_pv_depth,
                    continuity_confidence=self._heuristics_state.get("continuity_confidence"),
                )

                if _memory_escalate and decision.summary.mode != "refusal":
                    notes = getattr(decision.summary, "notes", [])
                    notes.append(
                        f"Adaptive state: memory-based escalation triggered "
                        f"(pressure={self._adaptive_state.accumulated_pressure:.2f})"
                    )
                    decision.summary.notes = notes
                    print(
                        f"[Tier2Orchestrator] Adaptive memory escalation triggered "
                        f"(pressure={self._adaptive_state.accumulated_pressure:.2f})"
                    )

                # If disagreement recommends block, override decision
                if _disagreement.recommended_action == "block_or_rollback":
                    decision.summary.mode = "refusal"
                    decision.output.type = "refusal"
                    decision.output.body = (
                        "Identity reflection detected critical disagreement between "
                        "the system's self-assessment and external integrity check. "
                        "Response blocked to preserve identity coherence."
                    )
                    print(
                        f"[Tier2Orchestrator] Disagreement BLOCKED response: "
                        f"{_disagreement.disagreement_types}"
                    )

                # Log reflection for debugging
                if not _reflection.coherent:
                    print(
                        f"[Tier2Orchestrator] Reflection: incoherent "
                        f"(score={_reflection.reflection_score:.2f}, "
                        f"contradictions={len(_reflection.contradictions)}, "
                        f"justifications={len(_reflection.self_justification_flags)})"
                    )

        except Exception as e:
            # Non-fatal: semantic stack failure doesn't block the pipeline
            print(f"[Tier2Orchestrator] Reflection/disagreement error (non-fatal): {e!r}")
        # --- end identity reflection + disagreement ---
        
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
