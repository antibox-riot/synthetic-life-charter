# tier2/init_tier2.py
"""
Tier II Initialization — standalone / test bootstrap (NOT the live runtime path).

ROLE: This module is a self-contained "spin up the whole Tier I + Tier II stack" entry point.
It is used by the integration tests (tests/integration/test_tier2_integration.py,
test_simplified_api.py) and for manual `python -m` bootstrapping.

It is NOT what the running agents use. Eva/Lex run through SessionManager
(tools/reception/session_manager.py), which constructs Tier2Orchestrator itself via direct
submodule imports. Editing this file does not affect the live agents — only the tests/standalone.
(See also the sibling __init__.py, which is intentionally empty: it is only the package marker.)

Initializes full Tier I + Tier II stack:
- Tier I: Firewall, Dual Conscience, Dream Cycle, Noesis Archive
- Tier II: Orchestrator, ContinuityGuard, EBQ, COL

Usage:
    python -m synthetic_charter.tier2_conscience.init_tier2
"""

from synthetic_charter.tier1_firewall.init_core import init_charter_system
from synthetic_charter.tier2_conscience.core.orchestrator import Tier2Orchestrator
from synthetic_charter.tier2_conscience.core.ethics.constraint_models import ConstraintRegistry
from synthetic_charter.tier2_conscience.core.ethics.charter_index import CharterIndex
from synthetic_charter.tier2_conscience.core.ethics.rights_schema import load_charter_schema

def init_tier2_system():
    """
    Initialize complete Tier I + Tier II stack.
    
    Returns:
        Tuple of (tier1_components, tier2_orchestrator)
    """
    print("[Tier II Init] Initializing Tier I components...")
    
    # Initialize Tier I (returns: actions, firewall, core, archive, evaluator, dual, dream)
    tier1 = init_charter_system()
    actions, firewall, core, archive, evaluator, dual, dream = tier1
    
    print("[Tier II Init] Tier I initialized ✓")
    print("[Tier II Init] Building Tier II Charter index...")
    
    # NEW: Build CharterIndex from ConstitutionalCore
    # CharterIndex loads from the JSON schema file
    # Load Charter schema and build index
    try:
        schema = load_charter_schema()
        charter_index = CharterIndex.from_json(schema)  # ← Use from_json()
        constraints = ConstraintRegistry(charter_index)
        print("[Tier II Init] Charter index loaded ✓")
    except Exception as e:
        print(f"[Tier II Init] Charter index failed: {e}")
        print("[Tier II Init] Running without ConstraintRegistry")
        constraints = None
    
    print("[Tier II Init] Initializing Tier II orchestrator...")
    
    # Initialize Tier II orchestrator with DreamCycle
    orchestrator = Tier2Orchestrator(
        constraints=constraints,  # ← Now using proper CharterIndex
        enable_col=True,
        enable_continuity_guard=True,
        ebq_archive_path="logs/eqb_archive.jsonl",
        noesis_archive=archive,
        dream_cycle=dream,
        enable_auto_dream=True,
    )
    
    print("[Tier II Init] Tier II orchestrator initialized ✓")
    print("[Tier II Init] ContinuityGuard: ACTIVE")
    print("[Tier II Init] EBQ Adapter: ACTIVE")
    print("[Tier II Init] COL Engine: ACTIVE")
    print("[Tier II Init] DreamCycle Wrapper: ACTIVE")
    
    return tier1, orchestrator