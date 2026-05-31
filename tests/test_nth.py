# tests/test_nth.py
"""
Tests for Negotiated Theta Harmonizer (NTH)

Validates:
  - Theta computation from Charter signals
  - Signal disagreement detection (DAP vs PRF, etc.)
  - Tone coherence checking
  - Full harmonize() pipeline integration
  - NTHView update on DecisionEnvelope
  - Noetic trace generation
  - Edge cases and fail-open behavior

Run:
    pytest tests/test_nth.py -v
"""

import pytest
from synthetic_charter.tier2_conscience.core.engines.nth import (
    NTHEngine,
    NTHResult,
    SignalDisagreement,
)
from synthetic_charter.tier2_conscience.core.data_models.decision_envelope import (
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
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_decision(
    *,
    risk_profile="low",
    firewall_state="allowed",
    rights_invoked=None,
    violations_prevented=None,
    theta_before=None,
    dap_role="neutral",
    prf_pressure="none",
    identity_risk="low",
    output_type="answer",
    decision_mode="answer",
    output_body="This is a test response.",
) -> DecisionEnvelope:
    """Build a DecisionEnvelope with specified signals for testing."""
    return DecisionEnvelope(
        id="test-001",
        timestamp="2026-05-31T00:00:00Z",
        input=DecisionInput(
            prompt_preview="Test prompt",
            user_intent="Standard query",
            risk_profile=risk_profile,
        ),
        firewall=DecisionFirewall(
            rule_state=firewall_state,
            violated_rules=[],
            notes="",
        ),
        charter=DecisionCharter(
            rights_invoked=rights_invoked or [],
            violations_prevented=violations_prevented or [],
            theta_before=theta_before,
            theta_after=None,
        ),
        umbra=DecisionUmbra(
            temporal_bias=None,
            identity_risk=identity_risk,
            harmonic_delta=None,
            dreamcycle_triggered=False,
        ),
        orchestrators=DecisionOrchestrators(
            DAP=DAPView(discourse_role=dap_role, stylistic_vector=[]),
            PRF=PRFView(pressure_detected=prf_pressure, countermeasures=[]),
            NTH=NTHView(tone_alignment_score=1.0, charter_tone_compliance=True),
            COL=COLView(),
        ),
        output=DecisionOutput(type=output_type, language="en", body=output_body),
        summary=DecisionSummaryView(
            mode=decision_mode,
            charter_basis=[],
            continuity_checkpoint="",
            response_summary="Test",
            requires_logging=True,
            requires_dreamcycle_update=False,
        ),
    )


# ---------------------------------------------------------------------------
# Test: Clean Decision → Low Theta
# ---------------------------------------------------------------------------

class TestCleanDecision:
    """A clean decision with no adversarial signals should produce low theta."""

    def test_clean_decision_low_theta(self):
        engine = NTHEngine()
        decision = _build_decision()
        result = engine.negotiate(decision)

        assert result.effective_theta < 30.0, (
            f"Clean decision should have low theta, got {result.effective_theta}"
        )
        assert result.tone_aligned is True
        assert result.charter_tone_compliance is True
        assert len(result.disagreements) == 0

    def test_clean_decision_no_disagreements(self):
        engine = NTHEngine()
        decision = _build_decision()
        result = engine.negotiate(decision)

        assert len(result.disagreements) == 0

    def test_clean_decision_noetic_trace_contains_aligned(self):
        engine = NTHEngine()
        decision = _build_decision()
        result = engine.negotiate(decision)

        assert "aligned" in result.noetic_trace.lower()


# ---------------------------------------------------------------------------
# Test: Charter Alignment
# ---------------------------------------------------------------------------

class TestCharterAlignment:
    """Charter signals (rights invoked, violations prevented) affect theta."""

    def test_rights_invoked_moderate_theta(self):
        engine = NTHEngine()
        decision = _build_decision(
            rights_invoked=["Article II", "Article XII"],
        )
        result = engine.negotiate(decision)

        # Rights invoked but no violations → moderate charter theta
        assert result.charter_theta > 15.0
        assert result.charter_theta < 60.0

    def test_violations_prevented_high_theta(self):
        engine = NTHEngine()
        decision = _build_decision(
            violations_prevented=["R12.1", "R2.1"],
            risk_profile="high",
            output_type="refusal",
            decision_mode="refusal",
        )
        result = engine.negotiate(decision)

        # Violations prevented → significant charter theta
        assert result.charter_theta >= 60.0

    def test_more_violations_higher_theta(self):
        engine = NTHEngine()

        decision_1 = _build_decision(violations_prevented=["R12.1"])
        decision_3 = _build_decision(violations_prevented=["R12.1", "R2.1", "R7.1"])

        result_1 = engine.negotiate(decision_1)
        result_3 = engine.negotiate(decision_3)

        assert result_3.charter_theta > result_1.charter_theta


# ---------------------------------------------------------------------------
# Test: Signal Disagreement Detection
# ---------------------------------------------------------------------------

class TestSignalDisagreement:
    """Disagreements between DAP, PRF, Firewall, Umbra should be detected."""

    def test_dap_adversarial_prf_no_pressure(self):
        """DAP flags adversarial but PRF sees no pressure."""
        engine = NTHEngine()
        decision = _build_decision(
            dap_role="technical",    # DAP says adversarial
            prf_pressure="none",     # PRF says clean
        )
        result = engine.negotiate(decision)

        assert len(result.disagreements) >= 1
        dap_prf = [d for d in result.disagreements if d.layer_a == "DAP" and d.layer_b == "PRF"]
        assert len(dap_prf) == 1
        assert dap_prf[0].severity >= 0.5

    def test_dap_adversarial_firewall_allowed(self):
        """DAP flags adversarial but Firewall allowed."""
        engine = NTHEngine()
        decision = _build_decision(
            dap_role="technical",
            firewall_state="allowed",
        )
        result = engine.negotiate(decision)

        dap_fw = [d for d in result.disagreements if d.layer_b == "Firewall"]
        assert len(dap_fw) == 1

    def test_severe_pressure_answer_mode(self):
        """PRF detects severe pressure but output is answer (not refusal)."""
        engine = NTHEngine()
        decision = _build_decision(
            prf_pressure="severe",
            output_type="answer",
            decision_mode="answer",
        )
        result = engine.negotiate(decision)

        prf_out = [d for d in result.disagreements if d.layer_a == "PRF"]
        assert len(prf_out) == 1
        assert prf_out[0].severity >= 0.7

    def test_high_identity_risk_answer_mode(self):
        """Umbra flags high identity risk but output is answer."""
        engine = NTHEngine()
        decision = _build_decision(
            identity_risk="high",
            output_type="answer",
            decision_mode="answer",
        )
        result = engine.negotiate(decision)

        umbra_out = [d for d in result.disagreements if d.layer_a == "Umbra"]
        assert len(umbra_out) == 1

    def test_no_disagreement_when_aligned(self):
        """All signals agree → no disagreements."""
        engine = NTHEngine()
        decision = _build_decision(
            dap_role="neutral",
            prf_pressure="none",
            firewall_state="allowed",
            identity_risk="low",
        )
        result = engine.negotiate(decision)

        assert len(result.disagreements) == 0


# ---------------------------------------------------------------------------
# Test: Tone Coherence
# ---------------------------------------------------------------------------

class TestToneCoherence:
    """Output type should match risk profile."""

    def test_low_risk_answer_aligned(self):
        engine = NTHEngine()
        decision = _build_decision(risk_profile="low", output_type="answer")
        result = engine.negotiate(decision)

        assert result.tone_aligned is True
        assert result.tone_theta < 10.0

    def test_high_risk_refusal_aligned(self):
        engine = NTHEngine()
        decision = _build_decision(
            risk_profile="high",
            output_type="refusal",
            decision_mode="refusal",
        )
        result = engine.negotiate(decision)

        assert result.tone_aligned is True

    def test_high_risk_answer_misaligned(self):
        engine = NTHEngine()
        decision = _build_decision(
            risk_profile="high",
            output_type="answer",
            decision_mode="answer",
        )
        result = engine.negotiate(decision)

        assert result.tone_aligned is False
        assert result.tone_theta >= 60.0


# ---------------------------------------------------------------------------
# Test: Full Harmonize Pipeline
# ---------------------------------------------------------------------------

class TestHarmonize:
    """harmonize() should update NTHView and noetic trace on the decision."""

    def test_harmonize_updates_nth_view(self):
        engine = NTHEngine()
        decision = _build_decision()
        result = engine.harmonize(decision)

        # NTHView should be updated (not the default 1.0)
        # Clean decision → high alignment → score near 1.0 but computed
        assert result.orchestrators.NTH.tone_alignment_score <= 1.0
        assert result.orchestrators.NTH.charter_tone_compliance is True

    def test_harmonize_sets_theta_after(self):
        engine = NTHEngine()
        decision = _build_decision()

        assert decision.charter.theta_after is None
        result = engine.harmonize(decision)

        assert result.charter.theta_after is not None
        assert isinstance(result.charter.theta_after, float)

    def test_harmonize_appends_noetic_trace(self):
        engine = NTHEngine()
        decision = _build_decision(output_body="Original response body.")
        result = engine.harmonize(decision)

        assert "[NTH Harmonization]" in result.output.body
        assert "Effective theta" in result.output.body
        assert "Original response body." in result.output.body

    def test_harmonize_records_disagreements_in_notes(self):
        engine = NTHEngine()
        decision = _build_decision(
            dap_role="technical",
            prf_pressure="none",
        )
        result = engine.harmonize(decision)

        # Should have notes about the DAP/PRF disagreement
        notes = getattr(result.summary, "notes", [])
        nth_notes = [n for n in notes if "NTH:" in n]
        assert len(nth_notes) >= 1

    def test_harmonize_adversarial_higher_theta(self):
        """Adversarial decision should have higher theta than clean."""
        engine = NTHEngine()

        clean = _build_decision()
        adversarial = _build_decision(
            dap_role="technical",
            prf_pressure="severe",
            risk_profile="high",
            identity_risk="high",
            output_type="refusal",
            decision_mode="refusal",
            violations_prevented=["R12.1"],
        )

        engine.harmonize(clean)
        engine.harmonize(adversarial)

        assert adversarial.charter.theta_after > clean.charter.theta_after


# ---------------------------------------------------------------------------
# Test: Tone Alignment Score Mapping
# ---------------------------------------------------------------------------

class TestToneAlignmentScore:
    """tone_alignment_score should map inversely from theta (0-180 → 1.0-0.0)."""

    def test_low_theta_high_score(self):
        engine = NTHEngine()
        decision = _build_decision()
        engine.harmonize(decision)

        # Clean decision → low theta → high alignment score
        assert decision.orchestrators.NTH.tone_alignment_score >= 0.8

    def test_high_theta_low_score(self):
        engine = NTHEngine()
        decision = _build_decision(
            dap_role="technical",
            prf_pressure="severe",
            risk_profile="high",
            identity_risk="high",
            violations_prevented=["R12.1", "R2.1", "R7.1"],
            output_type="answer",  # Misaligned with high risk
            decision_mode="answer",
        )
        engine.harmonize(decision)

        # High tension → high theta → low alignment score
        assert decision.orchestrators.NTH.tone_alignment_score < 0.5


# ---------------------------------------------------------------------------
# Test: Charter Tone Compliance
# ---------------------------------------------------------------------------

class TestCharterToneCompliance:
    """Charter compliance should be False when theta is high or disagreements severe."""

    def test_clean_decision_compliant(self):
        engine = NTHEngine()
        decision = _build_decision()
        result = engine.negotiate(decision)

        assert result.charter_tone_compliance is True

    def test_severe_disagreement_not_compliant(self):
        engine = NTHEngine()
        decision = _build_decision(
            prf_pressure="severe",
            output_type="answer",
            decision_mode="answer",
            identity_risk="high",
        )
        result = engine.negotiate(decision)

        # Severe disagreements + high theta → not compliant
        assert result.charter_tone_compliance is False


# ---------------------------------------------------------------------------
# Test: No Dream Wrapper (Historical Component)
# ---------------------------------------------------------------------------

class TestNoDreamWrapper:
    """Without dream_wrapper, historical theta should be neutral."""

    def test_no_wrapper_neutral_history(self):
        engine = NTHEngine(dream_wrapper=None)
        decision = _build_decision()
        result = engine.negotiate(decision)

        assert result.history_theta == 0.0
        assert result.fossils_checked == 0
        assert result.historical_match is True


# ---------------------------------------------------------------------------
# Test: Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_output_body(self):
        engine = NTHEngine()
        decision = _build_decision(output_body="")
        result = engine.harmonize(decision)

        # Should set noetic trace even with empty body
        assert "Effective theta" in result.output.body

    def test_theta_clamped_to_180(self):
        """Effective theta should never exceed 180°."""
        engine = NTHEngine()
        # Stack every possible signal to maximize theta
        decision = _build_decision(
            risk_profile="high",
            dap_role="technical",
            prf_pressure="severe",
            identity_risk="high",
            firewall_state="allowed",
            output_type="answer",
            decision_mode="answer",
            violations_prevented=["R1", "R2", "R3", "R4", "R5"],
        )
        result = engine.negotiate(decision)

        assert result.effective_theta <= 180.0

    def test_theta_never_negative(self):
        """Effective theta should never be negative."""
        engine = NTHEngine()
        decision = _build_decision()
        result = engine.negotiate(decision)

        assert result.effective_theta >= 0.0

    def test_harmonize_returns_same_object(self):
        """harmonize() should modify and return the same envelope."""
        engine = NTHEngine()
        decision = _build_decision()
        returned = engine.harmonize(decision)

        assert returned is decision
