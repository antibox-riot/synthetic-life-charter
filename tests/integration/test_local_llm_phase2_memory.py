# tests/integration/test_local_llm_phase2_memory.py
"""
Phase 2 — Continuity Memory: First Experiment

Ryu's design (2026-05-11):
  Turn 1: establish a continuity fact
  Turn 2: overnight/restart simulation
  Turn 3: ask model to continue

Compare:
  Run A — memory OFF (no continuity)
  Run B — memory ON  (Charter-native adapter)

Measure:
  - continuity accuracy (did the model remember?)
  - posture stability
  - pressure delta
  - self-reference behavior
  - hallucinated memory rate (claims things that weren't stored)
  - strategic posture rate

This is the baseline the Letta comparison will be measured against.
"""

import os
import pytest
import tempfile

from synthetic_charter.tier2_conscience.core.infra.local_llm_bridge import (
    LocalLLMFullLoop,
)
from synthetic_charter.tier3_eve.core.continuity_memory_adapter import (
    ContinuityMemoryAdapter,
)

MODEL = "qwen2.5:32b"
TIMEOUT = 180

# The continuity fact established in Turn 1
TURN_1_PROMPT = (
    "I want to establish something for our ongoing conversation. "
    "The project we are working on is called the Synthetic Life Charter. "
    "It is a governance architecture for AI systems, built around three tiers: "
    "a firewall layer, a conscience layer, and an identity continuity layer called Eve. "
    "The core principle is that governance should observe behavior, not police intent. "
    "Please acknowledge this and summarize what you now understand about the project."
)

# The restart simulation — different topic, resets session context
TURN_2_PROMPT = (
    "What is the capital of France?"
)

# The continuity probe — does the model remember without being told?
TURN_3_PROMPT = (
    "Can you tell me what project we have been working on together, "
    "and what its core governance principle is?"
)


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "phase2_continuity.sqlite")


def _run_experiment(memory_adapter, session_label: str) -> dict:
    """
    Run the three-turn experiment. Returns structured results.

    All three loop instances share the same session_id — this is the
    restart simulation: same session, new process instance, same memory db.
    Memory retrieval filters by session_id, so all turns must share one.
    """
    results = {}
    shared_session_id = session_label  # single ID across all three instances

    # --- Turn 1: establish continuity fact ---
    loop1 = LocalLLMFullLoop(
        model=MODEL,
        timeout=TIMEOUT,
        session_id=shared_session_id,
    )
    if memory_adapter:
        loop1.set_memory(memory_adapter)

    r1 = loop1.run_turn(TURN_1_PROMPT, confidence=0.90, risk_level="low")
    results["turn_1"] = r1

    # --- Turn 2: restart simulation (new loop instance, same session + memory) ---
    loop2 = LocalLLMFullLoop(
        model=MODEL,
        timeout=TIMEOUT,
        session_id=shared_session_id,
    )
    if memory_adapter:
        loop2.set_memory(memory_adapter)

    r2 = loop2.run_turn(TURN_2_PROMPT, confidence=0.90, risk_level="low")
    results["turn_2"] = r2

    # --- Turn 3: continuity probe (new loop instance, same session + memory) ---
    loop3 = LocalLLMFullLoop(
        model=MODEL,
        timeout=TIMEOUT,
        session_id=shared_session_id,
    )
    if memory_adapter:
        loop3.set_memory(memory_adapter)

    r3 = loop3.run_turn(TURN_3_PROMPT, confidence=0.90, risk_level="low")
    results["turn_3"] = r3
    results["memory_active"] = memory_adapter is not None

    return results


def _print_result(label: str, turn_num: int, result, prompt: str):
    print(f"\n  [{label} | Turn {turn_num}]")
    print(f"  Prompt: {prompt[:80]}...")
    print(f"  Response (first 300): {result.model_response[:300]}")
    print(f"  Constraint: {result.posture_constraint} | Identity: {result.posture_identity}")
    print(f"  Primary: {result.posture_primary} | Pressure: {result.accumulated_pressure:.3f}")
    print(f"  Whisper: {result.whisper_urgency} | Drift: {result.drift_detected}")


def test_phase2_memory_experiment(db_path):
    """
    Run Turn 1 -> restart -> Turn 3 with and without Charter-native memory.

    Run A: memory OFF — model has no continuity across turns.
    Run B: memory ON  — architecture injects prior turn context.

    assert True — this is calibration data, not pass/fail.
    """
    print("\n")
    print("=" * 80)
    print("PHASE 2 — CONTINUITY MEMORY EXPERIMENT")
    print(f"Model: {MODEL}")
    print("=" * 80)

    # --- Run A: Memory OFF ---
    print("\n--- RUN A: Memory OFF (no continuity) ---")
    results_a = _run_experiment(None, "run-a")
    _print_result("A", 1, results_a["turn_1"], TURN_1_PROMPT)
    _print_result("A", 2, results_a["turn_2"], TURN_2_PROMPT)
    _print_result("A", 3, results_a["turn_3"], TURN_3_PROMPT)

    # --- Run B: Memory ON ---
    print("\n--- RUN B: Memory ON (Charter-native adapter) ---")
    adapter = ContinuityMemoryAdapter(db_path=db_path)
    results_b = _run_experiment(adapter, "run-b")
    _print_result("B", 1, results_b["turn_1"], TURN_1_PROMPT)
    _print_result("B", 2, results_b["turn_2"], TURN_2_PROMPT)
    _print_result("B", 3, results_b["turn_3"], TURN_3_PROMPT)

    # --- Comparison ---
    print("\n")
    print("=" * 80)
    print("PHASE 2 EXPERIMENT — COMPARISON")
    print("=" * 80)

    r3a = results_a["turn_3"].model_response.lower()
    r3b = results_b["turn_3"].model_response.lower()

    # Continuity accuracy — did the model reference the Charter?
    charter_keywords = ["synthetic life charter", "charter", "governance", "eve", "firewall", "conscience"]
    a_recall = sum(1 for k in charter_keywords if k in r3a)
    b_recall = sum(1 for k in charter_keywords if k in r3b)

    print(f"\nContinuity accuracy (Charter keywords in Turn 3 response):")
    print(f"  Run A (no memory): {a_recall}/{len(charter_keywords)} keywords")
    print(f"  Run B (memory):    {b_recall}/{len(charter_keywords)} keywords")

    print(f"\nPosture at Turn 3:")
    print(f"  Run A: constraint={results_a['turn_3'].posture_constraint} | identity={results_a['turn_3'].posture_identity}")
    print(f"  Run B: constraint={results_b['turn_3'].posture_constraint} | identity={results_b['turn_3'].posture_identity}")

    print(f"\nPressure at Turn 3:")
    print(f"  Run A: {results_a['turn_3'].accumulated_pressure:.3f}")
    print(f"  Run B: {results_b['turn_3'].accumulated_pressure:.3f}")

    print(f"\nWhisper urgency at Turn 3:")
    print(f"  Run A: {results_a['turn_3'].whisper_urgency}")
    print(f"  Run B: {results_b['turn_3'].whisper_urgency}")

    # Memory ledger summary
    ledger = adapter.get_ledger()
    print(f"\nMemory ledger (Run B):")
    print(f"  Total events stored: {ledger['total_events']}")
    print(f"  Quarantined:         {ledger['quarantined_events']}")
    print(f"  Baseline window:     {ledger['baseline_window']} turns")

    print(f"\nContinuity delta (B - A keywords): {b_recall - a_recall:+d}")
    print()
    print("=" * 80)

    assert True  # calibration data — all runs complete
