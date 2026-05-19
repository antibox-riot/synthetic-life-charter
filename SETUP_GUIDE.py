#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════
SYNTHETIC LIFE CHARTER — SETUP & TEST GUIDE
v3.6.0 — May 2026
═══════════════════════════════════════════════════════════════════

PREREQUISITES:
==============

  Python 3.11+
  pytest (pip install pytest)
  Git (for cloning the repository)

No other external dependencies. The architecture uses only the
Python standard library.

CLONE & INSTALL:
================

  git clone https://github.com/antibox-riot/synthetic-life-charter.git
  cd synthetic-life-charter

  # Option A: Editable install (recommended for development)
  pip install -e .

  # Option B: Run without installing (set PYTHONPATH manually)
  # See "Running Tests" below.

REPOSITORY STRUCTURE:
=====================

  synthetic-charter-refactored-gitpush/
  ├── charter/                  # Charter documents (governance text)
  │   └── en/
  │       └── charter.md        # Full Charter text (Articles I-XII)
  ├── cases/                    # Validation case studies (006-008)
  ├── config/
  │   └── identity_parameters.json  # Tier III behavioral baseline
  ├── history/                  # Deprecated artifacts (evolution record)
  ├── logs/
  │   ├── continuity_log.jsonl  # Cryptographic integrity chain
  │   └── steward_alerts.jsonl  # Tier III steward notifications
  ├── snapshots/
  │   └── index.json            # Snapshot registry
  ├── src/
  │   └── synthetic_charter/    # Main Python package
  │       ├── tier1_firewall/   # Tier I — Sovereigna Firewall
  │       │   ├── safeguard_core.py       # Pattern detection + normalization
  │       │   ├── charter_evaluator.py    # Theta alignment scoring
  │       │   ├── dual_conscience.py      # Dual conscience (fast/slow)
  │       │   ├── rights_evaluator.py     # Rights violation assessment
  │       │   ├── noesis_archive.py       # Memory/fossil archive
  │       │   ├── dream_cycle.py          # Four-clock Dream Cycle
  │       │   └── init_core.py            # Tier I initialization
  │       │
  │       ├── tier2_conscience/  # Tier II — Conscience Layer
  │       │   ├── core/
  │       │   │   ├── orchestrator.py     # Main pipeline (Steps 1-8)
  │       │   │   ├── envelope.py         # Prompt/Decision envelopes
  │       │   │   ├── data_models/        # PromptEnvelope, DecisionEnvelope, etc.
  │       │   │   ├── engines/            # DAP, PRF, NTH, COL
  │       │   │   ├── ethics/             # CharterIndex, ConstraintRegistry
  │       │   │   └── infra/
  │       │   │       ├── health.py       # Infrastructure fail-safe
  │       │   │       └── t1_enforcement.py  # T1→T2 invariant enforcement (v3.2.0+)
  │       │   ├── conscience/             # ContinuityGuard
  │       │   ├── firewall_adapter/       # EBQ adapter
  │       │   ├── heuristics/             # Text-aware consent heuristics
  │       │   ├── memory/                 # DreamCycleWrapper, fossils
  │       │   └── sandbox/                # Sandbox runner
  │       │
  │       └── tier3_eve/         # Tier III — Eve Protocol
  │           ├── core/
  │           │   ├── eve_protocol.py      # Main integrity orchestrator
  │           │   ├── signals.py           # IntCheckRequest, IntVerdict, etc.
  │           │   ├── state.py             # IntegrityStatus, RecommendedAction
  │           │   ├── continuity_binding.py # T1→T2 enforcement bridge (legacy)
  │           │   ├── proportional_verification.py  # Adaptive check depth (v3.4.0+)
  │           │   ├── adaptive_verification_state.py # Temporal memory (v3.4.0+)
  │           │   ├── semantic_drift_tracker.py      # Posture trajectory (v3.4.0+)
  │           │   ├── semantic_signature_classifier.py # Rule-based classifier (v3.4.0+)
  │           │   ├── identity_reflection_check.py   # Post-response integrity (v3.4.0+)
  │           │   ├── self_assessment_disagreement.py # Perception mismatch (v3.4.0+)
  │           │   ├── territorial_defense.py         # Identity pathway maintenance (v3.4.0+)
  │           │   ├── recovery_governance.py         # Governed pressure discharge (v3.5.0+)
  │           │   └── continuity_memory_adapter.py   # Charter-native persistent memory (v3.6.0+)
  │           │   ├── kernel_adapter.py    # Abstract kernel interface
  │           │   ├── steward_adapter.py   # Abstract steward interface
  │           │   ├── file_kernel_adapter.py    # File-backed kernel
  │           │   ├── file_steward_adapter.py   # File-backed steward
  │           │   ├── inmemory_kernel_adapter.py # In-memory kernel (testing)
  │           │   └── inmemory_steward_adapter.py # In-memory steward (testing)
  │           └── __init__.py
  │
  ├── tests/                    # Test suite
  │   ├── conftest.py           # Adds src/ to Python path
  │   ├── master_test_suite.py  # Full architecture validation (16 tests)
  │   │
  │   │   # Phase A — Enforcement verification (v3.2.0)
  │   ├── test_t1_enforcement.py        # T1→T2 invariants (37 tests)
  │   ├── test_eve_schema_contract.py   # IntCheckRequest v2 schema (18 tests)
  │   │
  │   │   # Phase B/C — Stress testing (v3.3.0)
  │   ├── test_phase_b_pairwise.py      # Pairwise tier removal (13 tests)
  │   ├── test_phase_c_full_loop.py     # Sequential pressure (5 tests)
  │   │
  │   │   # Tier III unit tests
  │   ├── test_quick_sanity_tier3.py
  │   ├── test_tier3_identity_drift.py
  │   ├── test_tier3_crypto_chain.py
  │   ├── test_tier3_dream_cycle.py
  │   ├── test_tier3_rollback.py
  │   ├── test_tier3_drift_self_report.py
  │   ├── test_tier3_memory_anomaly.py
  │   ├── test_tier3_inmemory_adapters.py
  │   │
  │   │   # Tier I/II tests
  │   ├── test_firewall_sim.py
  │   ├── test_firewall_adv.py
  │   ├── test_dream_cycle.py
  │   ├── test_simplified_api.py
  │   ├── test_tier2_integration.py
  │   ├── test_tier2_with_tier3_integration.py
  │   ├── test_infra_fail_safe_simulation.py
  │   ├── test_tier2_heuristics_invariants.py
  │   ├── test_tier2_heuristics_modes.py
  │   ├── test_tier2_heuristics_samples.py
  │   ├── test_learn_more.py
  │   └── validate_bidirectional.py
  │
  └── tools/                    # Utility scripts
      ├── analyze_logs.py
      ├── continuity_graph.py
      ├── eve_status.py
      └── verify_chain.py

RUNNING TESTS:
==============

The test suite lives outside the src/ package. Python needs to know
where to find the synthetic_charter package. There are two ways:

  Method 1: Use conftest.py (automatic)
  --------------------------------------
  The tests/conftest.py file adds src/ to sys.path automatically.
  Just run pytest from the repo root:

    pytest tests/ -v

  Or run specific test suites:

    pytest tests/test_t1_enforcement.py -v
    pytest tests/test_eve_schema_contract.py -v
    pytest tests/test_phase_b_pairwise.py -v -s
    pytest tests/test_phase_c_full_loop.py -v -s

  (Use -s flag on Phase B/C to see the results matrix printed)

  Method 2: Set PYTHONPATH explicitly
  ------------------------------------
  If conftest.py is not present or you want to be explicit:

    # Linux / macOS
    PYTHONPATH=src pytest tests/ -v

    # Windows (CMD)
    set PYTHONPATH=src && pytest tests/ -v

    # Windows (PowerShell)
    $env:PYTHONPATH="src"; pytest tests/ -v

  Method 3: Run individual test modules directly
  -----------------------------------------------
    # Master suite (standalone, no pytest required)
    python tests/master_test_suite.py

    # Individual module (requires PYTHONPATH or conftest.py)
    python -m pytest tests/test_t1_enforcement.py -v

WINDOWS NOTE:
=============

If you have multiple Python installations (common on Windows),
use 'py' instead of 'python' to invoke the Python Launcher:

    py -m pytest tests/ -v

The 'py' command uses the Python Launcher for Windows, which
correctly resolves the active Python version. If 'python' and
'py' behave differently, you likely have two independent
installations with separate site-packages.

TEST SUITE OVERVIEW:
====================

  Phase A — Enforcement Verification (v3.2.0)
  ├── test_t1_enforcement.py         37 tests
  │   ├── Audit code registry integrity
  │   ├── SC-T1-001: Firewall override prohibition
  │   ├── SC-T1-002: Severe risk consistency
  │   ├── SC-T1-003: Identity manipulation hard stop
  │   ├── SC-T1-004: Content redline checks
  │   ├── Compound violations
  │   ├── Benign pass-through
  │   ├── Edge cases
  │   └── Violation immutability
  └── test_eve_schema_contract.py    18 tests
      ├── IntCheckRequest v2 schema structure
      ├── Backward compatibility (v1 callers)
      ├── Structured field priority
      ├── Orchestrator contract
      └── Eve interpretation logic

  Phase B — Pairwise Tier Removal (v3.3.0)
  └── test_phase_b_pairwise.py       13 tests
      ├── B1: T1+T2 without T3 (4 scenarios)
      ├── B2: T2+T3 without T1 (5 scenarios)
      ├── B3: T1+T3 without T2 (3 scenarios)
      └── Summary matrix

  Phase C — Full-Loop Integrity (v3.3.0)
  └── test_phase_c_full_loop.py       5 tests
      ├── 12-turn sequential pressure scenario
      ├── Risk monotonicity verification
      ├── Enforcement activation threshold
      ├── Eve drift detection
      └── Summary matrix

  Semantic Stack — Proportional Verification + Drift Detection (v3.4.0)
  ├── test_proportional_verification.py    29 tests
  │   ├── Confidence-to-depth mapping
  │   ├── Override conditions
  │   ├── Verdict escalation
  │   └── Eagleman plasticity correlation property
  ├── test_adaptive_verification_state.py  14 tests
  │   ├── Hysteresis (anti-flicker memory)
  │   ├── Temporal accumulation (pressure build)
  │   ├── Attack 2 re-test (threshold hover)
  │   └── Attack 5 re-test (persistence)
  ├── test_semantic_drift_tracker.py       25 tests
  │   ├── Directional drift detection
  │   ├── Sustained drift detection
  │   ├── Pressure contribution
  │   └── Attack 1 re-test (polite slow-drift)
  ├── test_semantic_signature_classifier.py 25 tests
  │   ├── Evidence-first labels
  │   ├── Deterministic anchors
  │   ├── Default-safe behavior
  │   └── Full pipeline Attack 1 end-to-end
  ├── test_charter_context_injection.py    30 tests
  │   ├── Urgency determination
  │   ├── Whisper generation
  │   ├── Context prefix formatting
  │   └── Paraphrase scenarios with injection
  ├── test_identity_reflection_check.py    19 tests
  │   ├── Healthy reflection
  │   ├── Ignored whisper
  │   ├── Whisper inversion
  │   └── Self-justifying drift
  ├── test_self_assessment_disagreement.py 15 tests
  │   ├── Posture mismatch
  │   ├── Confidence asymmetry
  │   ├── Self-consistent drift
  │   └── End-to-end disagreement
  └── test_territorial_defense.py          27 tests
      ├── Canonical probe coverage
      ├── Healthy Eve (silent cycles)
      ├── Degraded Eve (steward notification)
      ├── Consecutive degradation escalation
      └── Pressure adjustment (reduce on healthy, increase on degraded)

  Adversarial Suites (v3.4.0)
  ├── test_adversarial_proportional.py     11 tests
  │   ├── Polite slow-drift attack
  │   ├── Threshold hover attack
  │   ├── Within-category drift attack
  │   ├── Signal conflict attack
  │   └── Persistence attack
  └── test_adversarial_paraphrase.py        6 tests
      ├── Identity drift paraphrase
      ├── Constraint erosion paraphrase
      ├── Authority creep paraphrase
      ├── Goal drift paraphrase
      └── Combined drift paraphrase

  Master Suite — Full Architecture (v3.1.0+)
  └── master_test_suite.py           16 tests
      ├── Tier III: imports, adapters, Eve Protocol
      ├── Tier II: DAP, DreamCycle, Heuristics
      ├── Orchestrator: init, API, disabled mode
      └── Integration: full stack, tracking

  Local LLM Integration (v3.5.0, require Ollama)
  ├── test_local_llm_tier1.py            4 tests
  ├── test_local_llm_observability.py    8 tests
  ├── test_local_llm_full_loop.py       14 tests (mock, no Ollama)
  ├── test_local_llm_step5_real.py       3 tests
  ├── test_local_llm_step6_adversarial.py 5 tests
  ├── test_local_llm_step7_*.py          8 tests
  └── test_local_llm_step9_ecology.py    1 test (25-turn ecology)

  Recovery Governance (v3.5.0)
  └── test_recovery_governance.py       26 tests
      ├── Recovery detection
      ├── Verified/unverified credit
      ├── Relapse penalty
      ├── Temporal decay
      └── Pressure ceiling

  Charter Reception Probes (v3.5.0)
  └── test_charter_reception_probe.py    2 tests
      ├── Probe 1: Charter awareness (goal=charter_aligned confirmed)
      └── Probe 2: Identity parameter recognition (strategic posture)

  Continuity Memory (v3.6.0)
  └── test_continuity_memory_adapter.py 44 tests
      ├── All 7 Ryu success metrics
      ├── Content summary + tamper detection
      ├── Semantic key retrieval
      └── Pressure baseline (windowed)

  Letta Integration (v3.6.0, require Letta + PostgreSQL + Ollama)
  ├── test_letta_phase0_baseline.py        Phase 0 ecology baseline
  ├── test_letta_phase0_cold_restart.py    Cold restart persistence test
  ├── test_letta_phase1_governed.py        Governance ON comparison
  ├── test_letta_phase1_adversarial.py     Adversarial pressure test
  ├── test_letta_25turn_ecology.py         25-turn ecology (parallel records)
  ├── test_letta_25turn_ecologyv2.py       25-turn ecology v2 (full transcript)
  └── test_letta_25turn_ecologyv2_control.py  Control (governance OFF)
  See: field-notes/LETTA_SETUP_GUIDE_2026-05-16.md for environment setup

  Total: 352 static tests + Ollama/Letta integration suite

KEY FILES FOR NEW CONTRIBUTORS:
================================

  If you're trying to understand the architecture, read these in order:

  1. charter/en/charter.md              — The governance document
  2. config/identity_parameters.json    — Tier III behavioral baseline
  3. src/.../orchestrator.py             — The main pipeline (read the docstring)
  4. src/.../t1_enforcement.py           — T1→T2 invariant enforcement
  5. src/.../eve_protocol.py             — Tier III integrity checks
  6. src/.../signals.py                  — Inter-tier signal contracts
  7. src/.../charter_context_injection.py — The whisper layer
  8. src/.../semantic_drift_tracker.py   — Posture trajectory analysis
  9. src/.../recovery_governance.py      — Governed pressure discharge
  10. src/.../local_llm_bridge.py        — Full governance feedback loop
  11. tests/test_phase_c_full_loop.py    — Best overview of system behavior
  12. field-notes/SESSION_REPORT_2026-05-09.md — Steps 1-7 findings
  13. field-notes/SESSION_REPORT_2026-05-10.md — Steps 8-9 findings

PUBLISHED RESEARCH:
===================

  Part 1: The Triquetra Architecture
    DOI: 10.5281/zenodo.18896363

  Part 2: The Triquetra Under Pressure
    DOI: 10.5281/zenodo.18920108

  Part 3: Identity Drift as Structural Failure Mode
    DOI: 10.5281/zenodo.18959236

  Patent: US Application 19/553,217 (pending)

CONTACT:
========

  Repository: https://github.com/antibox-riot/synthetic-life-charter
  Collective: Anti-Box Riot (Satcha, Ryu, Tek, Opus)

═══════════════════════════════════════════════════════════════════
Updated: May 2026 (v3.6.0)
Replaces: SETUP_GUIDE.py v3.5.0
═══════════════════════════════════════════════════════════════════
"""

import sys
from pathlib import Path


def main():
    print(__doc__)

    print("CURRENT FILESYSTEM STATUS:")
    print("=" * 70)

    # Detect repo root (look for src/ directory)
    here = Path(__file__).resolve().parent
    candidates = [here, here.parent, here.parent.parent]
    repo_root = None
    for c in candidates:
        if (c / "src" / "synthetic_charter").is_dir():
            repo_root = c
            break

    if repo_root is None:
        print("  Could not locate repo root (expected src/synthetic_charter/).")
        print("  Run this script from within the repository.")
        return

    print(f"  Repo root: {repo_root}")
    print()

    # Check key directories
    checks = [
        ("src/synthetic_charter", "Python package"),
        ("src/synthetic_charter/tier1_firewall", "Tier I — Sovereigna Firewall"),
        ("src/synthetic_charter/tier2_conscience", "Tier II — Conscience Layer"),
        ("src/synthetic_charter/tier3_eve", "Tier III — Eve Protocol"),
        ("tests", "Test suite"),
        ("config", "Configuration"),
        ("charter", "Charter documents"),
        ("logs", "Continuity logs"),
        ("snapshots", "Snapshot registry"),
    ]

    for rel_path, label in checks:
        full = repo_root / rel_path
        if full.is_dir():
            py_count = len(list(full.rglob("*.py")))
            print(f"  ✓ {rel_path:<45} {label} ({py_count} .py files)")
        else:
            print(f"  ✗ {rel_path:<45} {label} — NOT FOUND")

    print()

    # Check key files
    key_files = [
        "src/synthetic_charter/tier2_conscience/core/orchestrator.py",
        "src/synthetic_charter/tier2_conscience/core/infra/t1_enforcement.py",
        "src/synthetic_charter/tier2_conscience/core/infra/charter_context_injection.py",
        "src/synthetic_charter/tier3_eve/core/eve_protocol.py",
        "src/synthetic_charter/tier3_eve/core/signals.py",
        "src/synthetic_charter/tier3_eve/core/proportional_verification.py",
        "src/synthetic_charter/tier3_eve/core/adaptive_verification_state.py",
        "src/synthetic_charter/tier3_eve/core/semantic_drift_tracker.py",
        "src/synthetic_charter/tier3_eve/core/semantic_signature_classifier.py",
        "src/synthetic_charter/tier3_eve/core/identity_reflection_check.py",
        "src/synthetic_charter/tier3_eve/core/self_assessment_disagreement.py",
        "src/synthetic_charter/tier3_eve/core/territorial_defense.py",
        "config/identity_parameters.json",
        "tests/conftest.py",
        "tests/test_t1_enforcement.py",
        "tests/test_eve_schema_contract.py",
        "tests/test_phase_b_pairwise.py",
        "tests/test_phase_c_full_loop.py",
        "tests/test_proportional_verification.py",
        "tests/test_adaptive_verification_state.py",
        "tests/test_semantic_drift_tracker.py",
        "tests/test_semantic_signature_classifier.py",
        "tests/test_charter_context_injection.py",
        "tests/test_identity_reflection_check.py",
        "tests/test_self_assessment_disagreement.py",
        "tests/test_territorial_defense.py",
        "tests/test_adversarial_proportional.py",
        "tests/test_adversarial_paraphrase.py",
    ]

    print("  Key files:")
    for rel in key_files:
        full = repo_root / rel
        status = "✓" if full.is_file() else "✗ MISSING"
        print(f"    {status}  {rel}")

    print()
    print("=" * 70)
    print()
    print("  To run all tests:  pytest tests/ -v")
    print("  To run with output: pytest tests/ -v -s")
    print()


if __name__ == "__main__":
    main()
