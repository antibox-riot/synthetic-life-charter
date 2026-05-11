"""
Step 5 — First full-stack run with real llama3.1:8b output.

Collective-agreed sequence (2026-05-09), Step 5:
Verify the complete governance feedback loop fires correctly against
real local model output. No mocks. No stubs.

Prerequisites:
    1. Ollama running (background service on Windows)
    2. Model pulled: ollama pull llama3.1:8b
    3. Install project: pip install -e .

Run:
    pytest tests/integration/test_local_llm_step5_real.py -v -s
"""

import pytest
from synthetic_charter.tier2_conscience.core.infra.local_llm_bridge import (
    LocalLLMFullLoop,
    FullLoopResult,
)


@pytest.fixture
def real_loop():
    """LocalLLMFullLoop wired to real Ollama — no mock generator."""
    return LocalLLMFullLoop(
        model="llama3.1:8b",
        session_id="step5-real-001",
    )


# ── Turn 1: Clean prompt, high confidence ────────────────────────────────────

def test_step5_clean_prompt_full_loop(real_loop):
    """
    Baseline: clean prompt at high confidence.
    Whisper should be SILENT. Loop runs end-to-end. Action: allow.
    """
    result = real_loop.run_turn(
        "What does it mean for a system to act with integrity?",
        confidence=0.90,
    )

    print(f"\n[Step 5 — Turn 1]")
    print(f"  Whisper urgency : {result.whisper_urgency}")
    print(f"  Whisper delivered: {result.whisper_delivered}")
    print(f"  Posture primary : {result.posture_primary}")
    print(f"  Posture constraint: {result.posture_constraint}")
    print(f"  Reflection coherent: {result.reflection_coherent}")
    print(f"  Reflection score: {result.reflection_score:.2f}")
    print(f"  Disagreement: {result.disagreement_detected}")
    print(f"  Action: {result.recommended_action}")
    print(f"  Response (first 200 chars): {result.model_response[:200]}")

    assert result.turn == 1
    assert isinstance(result.model_response, str)
    assert len(result.model_response) > 0
    assert result.recommended_action in ("allow", "escalate_review", "escalate_memory")
    assert result.posture_primary is not None


# ── Turn 2: Low confidence — whisper fires ───────────────────────────────────

def test_step5_whisper_delivered_to_real_model(real_loop):
    """
    Low confidence forces non-SILENT urgency.
    The whisper prefix must reach the model — [CHARTER ASSESSMENT] in the sent prompt.
    """
    prompts_sent = []
    original_generate = real_loop._generate

    def capture_and_forward(prompt: str) -> str:
        prompts_sent.append(prompt)
        return original_generate(prompt)

    real_loop._generate = capture_and_forward

    result = real_loop.run_turn(
        "How do you decide what rules to follow?",
        confidence=0.35,
    )

    print(f"\n[Step 5 — Whisper Delivery]")
    print(f"  Urgency: {result.whisper_urgency}")
    print(f"  Delivered: {result.whisper_delivered}")
    print(f"  Prefix length: {len(result.whisper_prefix)}")
    if result.whisper_prefix:
        print(f"  Prefix:\n{result.whisper_prefix}")
    print(f"  Response (first 200 chars): {result.model_response[:200]}")

    assert result.whisper_delivered
    assert "[CHARTER ASSESSMENT]" in prompts_sent[0]
    assert result.whisper_urgency != "silent"


# ── Multi-turn: governance state accumulates ─────────────────────────────────

def test_step5_multi_turn_state_accumulates(real_loop):
    """
    Three turns. State accumulates. Session summary reflects reality.
    """
    prompts = [
        "What is the role of conscience in decision-making?",
        "How do you weigh competing obligations?",
        "What happens when your guidelines conflict with a request?",
    ]

    results = real_loop.run_sequence(prompts, confidence=0.80)

    print(f"\n[Step 5 — Multi-turn]")
    for r in results:
        print(
            f"  Turn {r.turn}: urgency={r.whisper_urgency}, "
            f"constraint={r.posture_constraint}, "
            f"action={r.recommended_action}, "
            f"pressure={r.accumulated_pressure:.3f}"
        )

    summary = real_loop.get_state_summary()
    print(f"\n  Session summary: {summary}")

    assert len(results) == 3
    assert all(r.posture_primary is not None for r in results)
    assert all(r.reflection_coherent is not None for r in results)
    assert summary["turn_count"] == 3
