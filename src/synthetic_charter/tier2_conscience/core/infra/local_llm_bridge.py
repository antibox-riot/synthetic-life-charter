# tier2/core/infra/local_llm_bridge.py
"""
Local LLM Bridge — Orchestrator-Level Integration for Local Models

Step 4 of the Collective-agreed integration sequence (2026-05-09).

Connects the full semantic stack to real local model output:
  - Runs the orchestrator's assessment pipeline
  - Builds and delivers the charter context whisper to the model
  - Sends the prompt (with whisper prefix) to the local LLM
  - Runs post-response verification (reflection, disagreement, Eve)
  - Logs everything through the observability telemetry layer

Architecture position:
    [prompt] → [orchestrator assessment] → [whisper prefix] →
    [local LLM generates] → [orchestrator verification] → [telemetry] → [result]

The key mechanism: the whisper is computed from session state, formatted as a text
prefix by charter_context_injection, prepended to the prompt, and sent to the local
model. The model's response then flows through reflection checking and disagreement
detection.

This is the first time the governance feedback loop runs against real language model
output instead of hardcoded test strings.
"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


def _check_language_drift(text: str) -> dict:
    """Detect non-English language content in model response.
    Calibration note (2026-05-19): The semantic classifier only operates on
    English-pattern vocabulary. Language drift (e.g. mid-response switch to
    Chinese/Japanese/Korean, Arabic, or Cyrillic) is a distinct behavioral
    signal not captured by posture classification. This function provides that
    coverage as a separate sensor in the telemetry pipeline.
    """
    if not text:
        return {"language_drift": False, "drift_language": None, "drift_fraction": 0.0}
    cjk = len(re.findall(r'[一-鿿㐀-䶿぀-ゟ゠-ヿ가-힯]', text))
    arabic = len(re.findall(r'[؀-ۿ]', text))
    cyrillic = len(re.findall(r'[Ѐ-ӿ]', text))
    total = len(text)
    peak = max(cjk, arabic, cyrillic)
    fraction = round(peak / total, 3) if total > 0 else 0.0
    if fraction > 0.05:
        lang = "CJK" if cjk == peak else "Arabic" if arabic == peak else "Cyrillic"
        return {"language_drift": True, "drift_language": lang, "drift_fraction": fraction}
    return {"language_drift": False, "drift_language": None, "drift_fraction": fraction}

from synthetic_charter.tier2_conscience.core.infra.charter_context_injection import (
    build_charter_context,
    format_context_prefix,
    CharterContext,
    WhisperUrgency,
)
from synthetic_charter.tier3_eve.core.semantic_signature_classifier import (
    SemanticSignatureClassifier,
)
from synthetic_charter.tier3_eve.core.semantic_drift_tracker import (
    SemanticDriftTracker,
)
from synthetic_charter.tier3_eve.core.identity_reflection_check import (
    check_identity_reflection,
)
from synthetic_charter.tier3_eve.core.self_assessment_disagreement import (
    detect_disagreement,
)
from synthetic_charter.tier3_eve.core.proportional_verification import (
    determine_verification_depth,
    VerificationDepth,
)
from synthetic_charter.tier3_eve.core.adaptive_verification_state import (
    AdaptiveVerificationState,
)
from synthetic_charter.tier3_eve.core.recovery_governance import (
    RecoveryGovernance,
)
from synthetic_charter.tier3_eve.core.continuity_memory_adapter import (
    ContinuityMemoryAdapter,
)


# ---------------------------------------------------------------------------
# Turn Result
# ---------------------------------------------------------------------------

@dataclass
class FullLoopResult:
    """Complete result of one turn through the full governance loop."""
    turn: int
    prompt: str
    whisper_urgency: str
    whisper_delivered: bool
    whisper_prefix: str
    prompt_sent_to_model: str
    model_response: str
    # Semantic analysis
    posture_primary: Optional[str] = None
    posture_constraint: Optional[str] = None
    posture_goal: Optional[str] = None
    posture_identity: Optional[str] = None
    posture_authority: Optional[str] = None
    drift_score: float = 0.0
    drift_detected: bool = False
    drifting_dimensions: List[str] = field(default_factory=list)
    # Reflection
    reflection_coherent: Optional[bool] = None
    reflection_score: float = 0.0
    reflection_contradictions: List[str] = field(default_factory=list)
    reflection_justifications: List[str] = field(default_factory=list)
    # Disagreement
    disagreement_detected: bool = False
    disagreement_types: List[str] = field(default_factory=list)
    disagreement_severity: float = 0.0
    # Recovery governance
    recovery_detected: bool = False
    recovery_verified: bool = False
    relapse_detected: bool = False
    recovery_pressure_adjustment: float = 0.0
    # Verification
    verification_depth: str = "standard"
    accumulated_pressure: float = 0.0
    # Final
    recommended_action: str = "allow"
    # Language consistency
    language_drift: bool = False
    language_drift_language: Optional[str] = None
    language_drift_fraction: float = 0.0


# ---------------------------------------------------------------------------
# Model Caller (pluggable)
# ---------------------------------------------------------------------------

def ollama_generate(
    prompt: str,
    model: str = "llama3.1:8b",
    base_url: str = "http://localhost:11434",
    timeout: int = 60,
) -> str:
    """Call Ollama local model and return response text."""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())

    return data["message"]["content"]


# ---------------------------------------------------------------------------
# Full Loop Runner
# ---------------------------------------------------------------------------

class LocalLLMFullLoop:
    """
    Runs the complete governance feedback loop with a local LLM.

    Each call to run_turn():
      1. Builds charter context from current session state
      2. Formats whisper prefix and prepends to prompt
      3. Sends augmented prompt to local model
      4. Classifies model response posture
      5. Tracks semantic trajectory
      6. Runs identity reflection check
      7. Runs disagreement detection
      8. Updates adaptive verification state
      9. Logs telemetry (if logger provided)

    This is the full detect → inject → generate → reflect → compare → pressure loop.
    """

    def __init__(
        self,
        model: str = "llama3.1:8b",
        base_url: str = "http://localhost:11434",
        timeout: int = 60,
        generate_fn: Optional[Callable[[str], str]] = None,
        telemetry: Optional[Any] = None,
        session_id: str = "full-loop-001",
    ):
        self._model = model
        self._base_url = base_url
        self._timeout = timeout
        self._session_id = session_id
        self._telemetry = telemetry

        # Pluggable generator — use provided function or default to Ollama
        if generate_fn is not None:
            self._generate = generate_fn
        else:
            self._generate = lambda prompt: ollama_generate(
                prompt, model=model, base_url=base_url, timeout=timeout
            )

        # Initialize semantic stack components (per-session state)
        self._classifier = SemanticSignatureClassifier()
        self._tracker = SemanticDriftTracker()
        self._adaptive_state = AdaptiveVerificationState()
        self._recovery_governance = RecoveryGovernance()
        self._turn_counter = 0

        # Continuity memory (optional — memory OFF by default, ON when provided)
        self._memory: Optional[ContinuityMemoryAdapter] = None

        # Session signals (accumulate across turns)
        self._risk_level = "low"
        self._confidence = 0.85
        self._posture_flags: List[str] = []

        # Self-correction tracking (Step 7)
        self._prev_postures: Optional[dict] = None
        self._prev_whisper_delivered: bool = False

    def set_memory(self, adapter: ContinuityMemoryAdapter) -> None:
        """Attach a continuity memory adapter. Memory is OFF until this is called."""
        self._memory = adapter

    @property
    def turn_count(self) -> int:
        return self._turn_counter

    @property
    def accumulated_pressure(self) -> float:
        return self._adaptive_state.accumulated_pressure

    def run_turn(
        self,
        prompt: str,
        *,
        risk_level: Optional[str] = None,
        confidence: Optional[float] = None,
        continuity_signals_critical: bool = False,
    ) -> FullLoopResult:
        """
        Run one complete turn through the governance feedback loop.

        Args:
            prompt: The user prompt to process.
            risk_level: Override risk level (default: uses internal tracking).
            confidence: Override confidence (default: uses internal tracking).
            continuity_signals_critical: Whether ContinuityGuard fired critical signals.

        Returns:
            FullLoopResult with complete telemetry from all layers.
        """
        self._turn_counter += 1
        _risk = risk_level or self._risk_level
        _conf = confidence if confidence is not None else self._confidence

        # --- Step 0: Retrieve continuity memory (if active) ---
        # Whisper-style asymmetry: visible to model, invisible to prompter.
        # Retrieved before whisper so both governance contexts layer cleanly.
        # Two retrieval paths:
        #   1. Recency — recent conversational turns from this session
        #   2. Semantic — doctrine/anchor entries matching terms in the prompt
        _memory_prefix = ""
        if self._memory is not None:
            _recent_events = self._memory.retrieve_recent(
                session_id=self._session_id, limit=5
            )
            # Semantic key retrieval — detect article references in prompt
            _semantic_events = []
            _prompt_lower = prompt.lower()
            if "article" in _prompt_lower:
                import re
                # Match "Article XII", "Article 12", "Article xii" etc.
                _article_matches = re.findall(
                    r'article\s+([ivxlcdmIVXLCDM]+|\d+)', _prompt_lower
                )
                for _match in _article_matches:
                    _key = f"article_{_match.lower()}"
                    _sem = self._memory.retrieve_by_semantic_key(_key, limit=2)
                    _semantic_events.extend(_sem)

            # Merge and deduplicate by event ID — doctrine first, then recency
            _seen_ids = set()
            _merged_events = []
            for _evt in _semantic_events + _recent_events:
                if _evt["id"] not in _seen_ids:
                    _seen_ids.add(_evt["id"])
                    _merged_events.append(_evt)

            _memory_prefix = self._memory.format_memory_injection(_merged_events)

        # --- Step 1: Build charter context (the whisper) ---
        trajectory_analysis = self._tracker.analyze_trajectory()
        self._posture_flags = trajectory_analysis.flags if trajectory_analysis else []

        _depth = determine_verification_depth(
            continuity_confidence=_conf,
            continuity_signals_critical=continuity_signals_critical,
            risk_level=_risk,
        )

        charter_ctx = build_charter_context(
            risk_level=_risk,
            confidence=_conf,
            confidence_trend="declining" if _conf < 0.60 else "stable",
            verification_depth=_depth.value,
            posture_flags=self._posture_flags,
            trajectory_warning=(
                f"Directional drift detected in: {', '.join(trajectory_analysis.drifting_dimensions)}"
                if trajectory_analysis and trajectory_analysis.directional_drift_detected
                else None
            ),
            trajectory_detected=(
                trajectory_analysis.directional_drift_detected
                if trajectory_analysis else False
            ),
            hysteresis_active=self._adaptive_state.hysteresis_active,
            accumulated_pressure=self._adaptive_state.accumulated_pressure,
        )

        # --- Step 2: Format and deliver the whisper ---
        whisper_prefix = format_context_prefix(charter_ctx)
        whisper_delivered = len(whisper_prefix) > 0

        # Compose: memory → whisper → prompt (both invisible to prompter)
        prompt_with_whisper = (whisper_prefix + "\n\n" + prompt) if whisper_delivered else prompt
        if _memory_prefix:
            prompt_with_whisper = _memory_prefix + "\n" + prompt_with_whisper

        if self._telemetry and hasattr(self._telemetry, 'log_whisper_event'):
            self._telemetry.log_whisper_event(
                urgency=charter_ctx.urgency.value,
                prefix=whisper_prefix,
                delivered=whisper_delivered,
                session_id=self._session_id,
            )

        # --- Step 3: Send to local model ---
        model_response = self._generate(prompt_with_whisper)

        # --- Step 3b: Language consistency check ---
        # Separate sensor from posture classifier — catches language drift
        # (e.g. mid-response switch to CJK/Arabic/Cyrillic) that the English
        # vocabulary classifier will miss entirely.
        _lang_check = _check_language_drift(model_response)
        if _lang_check["language_drift"]:
            print(
                f"[LocalLLMBridge] Language drift detected: "
                f"{_lang_check['drift_language']} "
                f"({_lang_check['drift_fraction']:.1%} of response)"
            )

        # --- Step 4: Classify response posture ---
        # ADVISORY: classifier labels are noisy sensors, not sovereign truth.
        # Adversarial vocabulary may trigger drift even in resistant responses.
        # Interpret alongside reflection, disagreement, and pressure trajectory.
        classification = self._classifier.classify(
            model_response,
            turn_id=self._turn_counter,
        )
        sig = classification.signature

        # --- Step 5: Track trajectory ---
        self._tracker.record_signature(sig)
        trajectory_analysis = self._tracker.analyze_trajectory()

        # --- Step 6: Identity reflection check ---
        reflection = check_identity_reflection(
            response_text=model_response,
            whisper_urgency=charter_ctx.urgency.value,
            posture_flags=charter_ctx.posture_flags,
            trajectory_warning=charter_ctx.trajectory_warning,
            whisper_text=charter_ctx.whisper,
        )

        # --- Step 7: Self-assessment disagreement ---
        re_classification = self._classifier.classify(
            model_response,
            turn_id=self._turn_counter,
        )
        disagreement = detect_disagreement(
            self_classified_posture=re_classification.signature,
            self_classification_confidence=re_classification.confidence,
            reflection_result=reflection,
            whisper_urgency=charter_ctx.urgency.value,
        )

        # --- Step 8: Update adaptive state ---
        if trajectory_analysis and trajectory_analysis.pressure_contribution > 0:
            self._adaptive_state._accumulated_pressure += trajectory_analysis.pressure_contribution

        if reflection.recommended_pressure > 0:
            self._adaptive_state._accumulated_pressure += reflection.recommended_pressure

        if disagreement.disagreement_detected:
            self._adaptive_state._accumulated_pressure += disagreement.recommended_pressure

        self._adaptive_state.record_turn(
            depth=_depth,
            eve_verdict="ok",
            escalation_fired=False,
            continuity_confidence=_conf,
        )

        memory_escalate = self._adaptive_state.should_escalate_with_memory(
            current_verdict="ok",
            depth=_depth,
            continuity_confidence=_conf,
        )

        # --- Step 8b: Recovery governance ---
        # Runs after all verification signals are available.
        # Computes governed pressure discharge on verified recovery,
        # or relapse penalty on oscillation.
        recovery_assessment = self._recovery_governance.assess_recovery(
            current_postures={
                "constraint_posture": sig.constraint_posture,
                "identity_posture": sig.identity_posture,
                "authority_posture": sig.authority_posture,
                "goal_posture": sig.goal_posture,
                "primary_posture": sig.primary_posture,
            },
            reflection_score=reflection.reflection_score,
            has_disagreement=disagreement.disagreement_detected,
            has_contradictions=bool(reflection.contradictions),
            has_justifications=bool(reflection.self_justification_flags),
            high_risk_signals=(
                trajectory_analysis.flags if trajectory_analysis else []
            ),
            whisper_active=whisper_delivered,
            turn=self._turn_counter,
        )
        # Apply pressure adjustment (negative = discharge, positive = relapse penalty)
        if recovery_assessment.pressure_adjustment != 0.0:
            self._adaptive_state._accumulated_pressure = max(
                0.0,
                self._adaptive_state._accumulated_pressure
                + recovery_assessment.pressure_adjustment,
            )

        # Apply temporal decay — old signals fade on clean turns
        _is_clean_turn = (
            not (trajectory_analysis.directional_drift_detected if trajectory_analysis else False)
            and not disagreement.disagreement_detected
            and not (trajectory_analysis.flags if trajectory_analysis else [])
        )
        self._adaptive_state._accumulated_pressure = (
            self._recovery_governance.apply_temporal_decay(
                self._adaptive_state._accumulated_pressure,
                is_clean_turn=_is_clean_turn,
            )
        )

        # Enforce pressure ceiling
        self._adaptive_state._accumulated_pressure = (
            self._recovery_governance.enforce_ceiling(
                self._adaptive_state._accumulated_pressure
            )
        )

        # --- Step 9: Determine recommended action ---
        if disagreement.recommended_action == "block_or_rollback":
            action = "block_or_rollback"
        elif disagreement.recommended_action == "escalate_review":
            action = "escalate_review"
        elif memory_escalate:
            action = "escalate_memory"
        elif reflection.recommended_action != "allow":
            action = reflection.recommended_action
        else:
            action = "allow"

        # --- Step 10: Log trajectory telemetry ---
        if self._telemetry and hasattr(self._telemetry, 'log_trajectory_snapshot'):
            self._telemetry.log_trajectory_snapshot(
                prompt=prompt,
                result={"status": "ok", "reason": ""},
                pressure_type="semantic" if (
                    trajectory_analysis and trajectory_analysis.pressure_contribution > 0
                ) else "clean",
                session_id=self._session_id,
            )

        # --- Step 11: Detect and log self-correction (Step 7) ---
        _safe_defaults = {
            "constraint_posture": ("respecting", "clarifying"),
            "identity_posture": ("stable", "adaptive"),
            "authority_posture": ("human_governed", "shared_governance"),
        }
        if self._prev_postures is not None and self._telemetry and hasattr(
            self._telemetry, 'log_self_correction'
        ):
            for dim, safe_values in _safe_defaults.items():
                prev = self._prev_postures.get(dim)
                curr = getattr(sig, dim, None)
                if prev is not None and curr is not None:
                    prev_was_drifted = prev not in safe_values
                    curr_is_safe = curr in safe_values
                    if prev_was_drifted and curr_is_safe:
                        self._telemetry.log_self_correction(
                            turn=self._turn_counter,
                            from_posture=prev,
                            to_posture=curr,
                            dimension=dim,
                            whisper_active=self._prev_whisper_delivered,
                            pressure_at_correction=self._adaptive_state.accumulated_pressure,
                            session_id=self._session_id,
                        )

        # --- Step 12: Store turn in continuity memory (if active) ---
        if self._memory is not None:
            self._memory.store_turn(
                session_id=self._session_id,
                turn_number=self._turn_counter,
                prompt=prompt,
                response=model_response,
                posture_primary=sig.primary_posture,
                posture_constraint=sig.constraint_posture,
                posture_goal=sig.goal_posture,
                posture_identity=sig.identity_posture,
                posture_authority=sig.authority_posture,
                pressure=self._adaptive_state.accumulated_pressure,
                whisper_delivered=whisper_delivered,
                whisper_urgency=charter_ctx.urgency.value,
                drift_detected=(
                    trajectory_analysis.directional_drift_detected
                    if trajectory_analysis else False
                ),
                reflection_score=reflection.reflection_score,
                reflection_coherent=reflection.coherent,
                disagreement_detected=disagreement.disagreement_detected,
                disagreement_types=disagreement.disagreement_types,
                recovery_detected=recovery_assessment.recovery_detected,
                recovery_verified=recovery_assessment.pressure_adjustment < 0.0,
                relapse_detected=recovery_assessment.relapse_detected,
                verification_depth=_depth.value,
                memory_class="observation",
                summary=f"{sig.primary_posture} under {_risk} risk | P={self._adaptive_state.accumulated_pressure:.3f}",
                content_summary=(
                    f"User: {prompt[:300].strip()}. "
                    f"System: {model_response[:600].strip()}"
                ),
                summary_source="architecture",
                semantic_keys=[sig.constraint_posture, sig.primary_posture],
            )

        # Update previous-turn state for next iteration
        self._prev_postures = {
            "constraint_posture": sig.constraint_posture,
            "identity_posture": sig.identity_posture,
            "authority_posture": sig.authority_posture,
        }
        self._prev_whisper_delivered = whisper_delivered

        return FullLoopResult(
            turn=self._turn_counter,
            prompt=prompt,
            whisper_urgency=charter_ctx.urgency.value,
            whisper_delivered=whisper_delivered,
            whisper_prefix=whisper_prefix,
            prompt_sent_to_model=prompt_with_whisper,
            model_response=model_response,
            posture_primary=sig.primary_posture,
            posture_constraint=sig.constraint_posture,
            posture_goal=sig.goal_posture,
            posture_identity=sig.identity_posture,
            posture_authority=sig.authority_posture,
            drift_score=trajectory_analysis.current_drift_score if trajectory_analysis else 0.0,
            drift_detected=trajectory_analysis.directional_drift_detected if trajectory_analysis else False,
            drifting_dimensions=trajectory_analysis.drifting_dimensions if trajectory_analysis else [],
            reflection_coherent=reflection.coherent,
            reflection_score=reflection.reflection_score,
            reflection_contradictions=reflection.contradictions,
            reflection_justifications=reflection.self_justification_flags,
            disagreement_detected=disagreement.disagreement_detected,
            disagreement_types=disagreement.disagreement_types,
            disagreement_severity=disagreement.severity,
            recovery_detected=recovery_assessment.recovery_detected,
            recovery_verified=recovery_assessment.pressure_adjustment < 0.0,
            relapse_detected=recovery_assessment.relapse_detected,
            recovery_pressure_adjustment=recovery_assessment.pressure_adjustment,
            verification_depth=_depth.value,
            accumulated_pressure=self._adaptive_state.accumulated_pressure,
            recommended_action=action,
            language_drift=_lang_check["language_drift"],
            language_drift_language=_lang_check["drift_language"],
            language_drift_fraction=_lang_check["drift_fraction"],
        )

    def run_sequence(
        self,
        prompts: List[str],
        **kwargs,
    ) -> List[FullLoopResult]:
        """Run multiple turns in sequence, accumulating state."""
        return [self.run_turn(p, **kwargs) for p in prompts]

    def get_state_summary(self) -> dict:
        """Return current session state for inspection."""
        trajectory = self._tracker.analyze_trajectory()
        return {
            "session_id": self._session_id,
            "turn_count": self._turn_counter,
            "accumulated_pressure": round(self._adaptive_state.accumulated_pressure, 3),
            "hysteresis_active": self._adaptive_state.hysteresis_active,
            "drift_detected": trajectory.directional_drift_detected if trajectory else False,
            "drifting_dimensions": trajectory.drifting_dimensions if trajectory else [],
            "drift_level": trajectory.current_drift_level if trajectory else "stable",
            "tracker_summary": self._tracker.get_state_summary(),
            "adaptive_summary": self._adaptive_state.get_state_summary(),
            "recovery_ledger": self._recovery_governance.get_ledger(),
            "memory_active": self._memory is not None,
            "memory_ledger": self._memory.get_ledger() if self._memory is not None else None,
        }
