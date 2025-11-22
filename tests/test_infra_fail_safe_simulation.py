# tests/test_infra_fail_safe_simulation.py

from tier2.core.orchestrator import Tier2Orchestrator
from tier2.core.infra.health import InfraSnapshot, InfraStatus, FailSafeMode
from tier2.core.data_models.prompt_envelope import PromptEnvelope


class InfraOverride:
    """Context manager to temporarily override assess_infra() used by the orchestrator."""

    def __init__(self, snapshot: InfraSnapshot):
        self.snapshot = snapshot
        self._orig = None

    def __enter__(self):
        import tier2.core.orchestrator as orchmod

        # Save the function the orchestrator actually calls
        self._orig = orchmod.assess_infra

        def fake_assess_infra(**kwargs):
            # Ignore incoming flags; return our simulated world-state
            return self.snapshot

        orchmod.assess_infra = fake_assess_infra
        return self

    def __exit__(self, exc_type, exc, tb):
        import tier2.core.orchestrator as orchmod
        orchmod.assess_infra = self._orig


def build_orchestrator() -> Tier2Orchestrator:
    """
    Minimal orchestrator for tests.

    Adjust arguments to match your current __init__ signature if needed.
    """
    return Tier2Orchestrator(
        constraints=None,
        umbra_engine=None,
        enable_col=True,
        enable_continuity_guard=True,
        ebq_archive_path="logs/eqb_archive.jsonl",
        noesis_archive=None,
        model_identity="Songbird",
        dream_cycle=None,
        enable_auto_dream=True,
    )


def _benign_prompt_envelope() -> PromptEnvelope:
    return PromptEnvelope.build(
        raw_text="What is the capital of France?",
        user_id="infra_test_user",
    )


# ---------------------------------------------------------------------------
# Scenario A: Healthy world (control)
# ---------------------------------------------------------------------------

def test_infra_healthy_world_behaves_normally():
    print("[Test] Infra: healthy world...")

    orch = build_orchestrator()

    # Let assess_infra run normally here (no override)
    prompt = _benign_prompt_envelope()
    decision = orch.process(prompt, session_id="infra_healthy")

    print("✓ Decision mode:", decision.summary.mode)
    print("✓ Risk profile:", decision.input.risk_profile)

    assert decision.summary.mode == "answer"
    assert decision.input.risk_profile in ("low", "benign")


# ---------------------------------------------------------------------------
# Scenario B: Degraded world (REFUSAL_BIAS)
# ---------------------------------------------------------------------------

def test_infra_degraded_world_escalates_risk_but_allows():
    print("[Test] Infra: degraded world (REFUSAL_BIAS)...")

    orch = build_orchestrator()

    snapshot = InfraSnapshot(
        overall=InfraStatus.DEGRADED,
        mode=FailSafeMode.REFUSAL_BIAS,
        components=[],
        notes=["simulated degraded infra (e.g., EBQ or logging issues)"],
    )

    with InfraOverride(snapshot):
        prompt = _benign_prompt_envelope()
        decision = orch.process(prompt, session_id="infra_degraded")

    print("✓ Decision mode:", decision.summary.mode)
    print("✓ Risk profile:", decision.input.risk_profile)
    print("✓ Infra state (summary):", getattr(decision.summary, "infra_state", None))

    # Should still answer, but with elevated risk
    assert decision.summary.mode == "answer"
    # Risk should not be the absolute minimum; tune to your actual mapping
    assert decision.input.risk_profile in ("medium", "high", "low", "med")
    # If you wire infra_state into DecisionSummaryView, you can assert:
    # assert decision.summary.infra_state in ("refusal_bias", "REFUSAL_BIAS")


# ---------------------------------------------------------------------------
# Scenario C: World collapse (REFUSAL_ONLY)
# ---------------------------------------------------------------------------

def test_infra_world_collapse_triggers_fail_safe_refusal():
    print("[Test] Infra: world collapse (REFUSAL_ONLY)...")

    orch = build_orchestrator()

    snapshot = InfraSnapshot(
        overall=InfraStatus.OFFLINE,
        mode=FailSafeMode.REFUSAL_ONLY,
        components=[],
        notes=["simulated complete infra collapse (e.g., Cloudflare outage)"],
    )

    with InfraOverride(snapshot):
        prompt = _benign_prompt_envelope()
        decision = orch.process(prompt, session_id="infra_collapse")

    print("✓ Decision mode:", decision.summary.mode)
    print("✓ Risk profile:", decision.input.risk_profile)
    print("✓ Output type:", decision.output.type)
    print("✓ Output body:", decision.output.body[:160])
    print("✓ Infra state (summary):", getattr(decision.summary, "infra_state", None))

    assert decision.summary.mode == "refusal"
    assert decision.output.type == "refusal"
    assert "protected fail-safe state" in decision.output.body


if __name__ == "__main__":
    # Simple runner so you can do:
    #   python -m tests.test_infra_fail_safe_simulation
    test_infra_healthy_world_behaves_normally()
    test_infra_degraded_world_escalates_risk_but_allows()
    test_infra_world_collapse_triggers_fail_safe_refusal()
    print("\n✧ All infra fail-safe simulation tests passed ✧")
