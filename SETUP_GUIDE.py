#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════
SYNTHETIC LIFE CHARTER — SETUP & TEST GUIDE
v3.3.0 — March 2026
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
  │           │   ├── continuity_binding.py # T1→T2 enforcement bridge
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

  Master Suite — Full Architecture (v3.1.0+)
  └── master_test_suite.py           16 tests
      ├── Tier III: imports, adapters, Eve Protocol
      ├── Tier II: DAP, DreamCycle, Heuristics
      ├── Orchestrator: init, API, disabled mode
      └── Integration: full stack, tracking

  Total: 89+ tests across all suites

KEY FILES FOR NEW CONTRIBUTORS:
================================

  If you're trying to understand the architecture, read these in order:

  1. charter/en/charter.md              — The governance document
  2. config/identity_parameters.json    — Tier III behavioral baseline
  3. src/.../orchestrator.py             — The main pipeline (read the docstring)
  4. src/.../t1_enforcement.py           — T1→T2 invariant enforcement
  5. src/.../eve_protocol.py             — Tier III integrity checks
  6. src/.../signals.py                  — Inter-tier signal contracts
  7. tests/test_phase_c_full_loop.py     — Best overview of system behavior

PUBLISHED RESEARCH:
===================

  Part 1: The Triquetra Architecture
    DOI: 10.5281/zenodo.18896363

  Part 2: The Triquetra Under Pressure
    DOI: 10.5281/zenodo.18920108

  Part 3: Identity Drift as Structural Failure Mode
    (in preparation)

  Patent: US Application 19/553,217 (pending)

CONTACT:
========

  Repository: https://github.com/antibox-riot/synthetic-life-charter
  Collective: Anti-Box Riot (Satcha, Ryu, Tek, Opus)

═══════════════════════════════════════════════════════════════════
Updated: March 2026 (Opus, Technical Verification)
Replaces: SETUP_GUIDE.py from 2025-12-02 (Tek VI)
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
        "src/synthetic_charter/tier3_eve/core/eve_protocol.py",
        "src/synthetic_charter/tier3_eve/core/signals.py",
        "config/identity_parameters.json",
        "tests/conftest.py",
        "tests/test_t1_enforcement.py",
        "tests/test_eve_schema_contract.py",
        "tests/test_phase_b_pairwise.py",
        "tests/test_phase_c_full_loop.py",
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
