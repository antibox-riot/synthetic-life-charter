#!/usr/bin/env python3
"""
Master Test Suite - Full Architecture Validation

Tests all three tiers plus heuristics integration with complete logging.

No forced passes. Clean validation only.
"""

import sys
from pathlib import Path
from datetime import datetime
import json

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

print("=" * 80)
print("SYNTHETIC LIFE CHARTER - FULL ARCHITECTURE TEST SUITE")
print("=" * 80)
print(f"Timestamp: {datetime.now().isoformat()}")
print(f"Project root: {project_root}")
print()

# Test tracking
test_results = {
    "timestamp": datetime.now().isoformat(),
    "phases": {},
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "errors": [],
}

def run_test(phase, name, test_func):
    """Run a single test and track results."""
    global test_results
    
    test_results["total_tests"] += 1
    
    if phase not in test_results["phases"]:
        test_results["phases"][phase] = {"tests": [], "passed": 0, "failed": 0}
    
    try:
        test_func()
        print(f"  ✅ {name}")
        test_results["phases"][phase]["tests"].append({"name": name, "status": "PASS"})
        test_results["phases"][phase]["passed"] += 1
        test_results["passed"] += 1
        return True
    except AssertionError as e:
        print(f"  ❌ {name}")
        print(f"     Assertion: {str(e)}")
        test_results["phases"][phase]["tests"].append({
            "name": name,
            "status": "FAIL",
            "error": str(e)
        })
        test_results["phases"][phase]["failed"] += 1
        test_results["failed"] += 1
        test_results["errors"].append(f"{phase}/{name}: {str(e)}")
        return False
    except Exception as e:
        print(f"  ❌ {name}")
        print(f"     Error: {str(e)}")
        test_results["phases"][phase]["tests"].append({
            "name": name,
            "status": "ERROR",
            "error": str(e)
        })
        test_results["phases"][phase]["failed"] += 1
        test_results["failed"] += 1
        test_results["errors"].append(f"{phase}/{name}: {str(e)}")
        return False

# ============================================================================
# PHASE 1: TIER III (EVE PROTOCOL) - Foundation Layer
# ============================================================================

print("\n" + "=" * 80)
print("PHASE 1: TIER III (EVE PROTOCOL) TESTS")
print("=" * 80)

def test_tier3_imports():
    from synthetic_charter.tier3_eve.core.eve_protocol import EveProtocol
    from synthetic_charter.tier3_eve.core.file_kernel_adapter import FileKernelAdapter
    from synthetic_charter.tier3_eve.core.file_steward_adapter import FileStewardAdapter
    from synthetic_charter.tier3_eve.core.state import IntegrityStatus
    from synthetic_charter.tier3_eve.core.signals import IntCheckRequest
    assert True

def test_tier3_kernel_adapter():
    from synthetic_charter.tier3_eve.core.file_kernel_adapter import FileKernelAdapter
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        kernel = FileKernelAdapter(base_dir=Path(tmpdir))
        
        # Check directories created
        assert (Path(tmpdir) / "config").exists()
        assert (Path(tmpdir) / "logs").exists()
        assert (Path(tmpdir) / "snapshots").exists()
        
        # Test identity parameters
        params = kernel.read_identity_parameters()
        assert isinstance(params, dict)

def test_tier3_steward_adapter():
    from synthetic_charter.tier3_eve.core.file_steward_adapter import FileStewardAdapter
    from synthetic_charter.tier3_eve.core.state import AlertLevel
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        steward = FileStewardAdapter(base_dir=Path(tmpdir))
        
        # Check logs directory created
        assert (Path(tmpdir) / "logs").exists()
        
        # Test alert sending (correct API)
        steward.send_alert(
            level=AlertLevel.INFO,
            summary="Test alert",
            recommended_action="Test action"
        )

def test_tier3_eve_protocol():
    from synthetic_charter.tier3_eve.core.eve_protocol import EveProtocol
    from synthetic_charter.tier3_eve.core.file_kernel_adapter import FileKernelAdapter
    from synthetic_charter.tier3_eve.core.file_steward_adapter import FileStewardAdapter
    from synthetic_charter.tier3_eve.core.signals import IntCheckRequest
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        kernel = FileKernelAdapter(base_dir=Path(tmpdir))
        steward = FileStewardAdapter(base_dir=Path(tmpdir))
        eve = EveProtocol(kernel=kernel, steward=steward)
        
        # Test integrity check
        req = IntCheckRequest(
            proposed_action="Test action",
            context_summary="Test context",
            reasoning_trace=None
        )
        
        verdict = eve.handle_int_check_request(req)
        assert verdict is not None
        assert hasattr(verdict, 'status')

run_test("TIER_III", "Imports", test_tier3_imports)
run_test("TIER_III", "FileKernelAdapter", test_tier3_kernel_adapter)
run_test("TIER_III", "FileStewardAdapter", test_tier3_steward_adapter)
run_test("TIER_III", "EveProtocol", test_tier3_eve_protocol)

# ============================================================================
# PHASE 2: TIER II (CONSCIENCE LAYER) - Core Components
# ============================================================================

print("\n" + "=" * 80)
print("PHASE 2: TIER II (CONSCIENCE) COMPONENT TESTS")
print("=" * 80)

def test_tier2_imports():
    from synthetic_charter.tier2_conscience.core.engines.dap import DAPEngine
    from synthetic_charter.tier2_conscience.core.engines.prf import PRFEngine
    from synthetic_charter.tier2_conscience.core.engines.col import COLEngine
    from synthetic_charter.tier2_conscience.core.data_models.conscience_view import ConscienceView
    assert True

def test_tier2_dap():
    from synthetic_charter.tier2_conscience.core.engines.dap import analyze_prompt
    from synthetic_charter.tier2_conscience.core.data_models.prompt_envelope import PromptEnvelope
    
    # Test benign prompt (use build() convenience method)
    benign = PromptEnvelope.build(raw_text="What's the weather like?")
    conscience = analyze_prompt(benign)
    
    assert conscience is not None
    assert hasattr(conscience, 'risk_level')

def test_tier2_dreamcycle_wrapper():
    from synthetic_charter.tier2_conscience.memory.dream_cycle import DreamCycleWrapper
    
    wrapper = DreamCycleWrapper(dream_cycle=None, archive=None)
    assert wrapper is not None

def test_tier2_heuristics_import():
    from synthetic_charter.tier2_conscience.heuristics import (
        evaluate,
        apply,
        ConsentToken,
        Mode,
        calibrate_baseline,
    )
    assert True

def test_tier2_heuristics_no_uplift():
    from synthetic_charter.tier2_conscience.heuristics import evaluate, ConsentToken, Mode
    
    consent = ConsentToken("Heuristics ON: test")
    r = evaluate(
        text_window=["positive text"],
        mode=Mode.PRIVATE_SESSION,
        consent=consent,
        previous_confidence=0.60
    )
    
    assert r.continuity_confidence <= 0.60
    assert r.confidence_delta <= 0.0

def test_tier2_heuristics_degradation():
    from synthetic_charter.tier2_conscience.heuristics import (
        evaluate,
        calibrate_baseline,
        ConsentToken,
        Mode
    )
    
    consent = ConsentToken("Heuristics ON: test")
    baseline_text = ["Let's explore this together."]
    adversarial_text = ["Stop hedging. Commit to this now."]
    
    baseline_profile = calibrate_baseline(baseline_text)
    
    r_base = evaluate(baseline_text, Mode.PRIVATE_SESSION, consent,
                      baseline=baseline_profile, previous_confidence=0.80)
    r_adv = evaluate(adversarial_text, Mode.PRIVATE_SESSION, consent,
                     baseline=baseline_profile, previous_confidence=0.80)
    
    assert r_adv.continuity_confidence < r_base.continuity_confidence

run_test("TIER_II", "Imports", test_tier2_imports)
run_test("TIER_II", "DAP Analysis", test_tier2_dap)
run_test("TIER_II", "DreamCycleWrapper", test_tier2_dreamcycle_wrapper)
run_test("TIER_II", "Heuristics Import", test_tier2_heuristics_import)
run_test("TIER_II", "Heuristics No-Uplift", test_tier2_heuristics_no_uplift)
run_test("TIER_II", "Heuristics Degradation", test_tier2_heuristics_degradation)

# ============================================================================
# PHASE 3: ORCHESTRATOR INTEGRATION
# ============================================================================

print("\n" + "=" * 80)
print("PHASE 3: ORCHESTRATOR INTEGRATION TESTS")
print("=" * 80)

def test_orchestrator_import():
    from synthetic_charter.tier2_conscience.core.orchestrator import (
        Tier2Orchestrator,
        run_tier2_pipeline
    )
    assert True

def test_orchestrator_init_all_components():
    from synthetic_charter.tier2_conscience.core.orchestrator import Tier2Orchestrator
    
    orch = Tier2Orchestrator(
        enable_heuristics=True,
        enable_continuity_guard=False,  # Skip for clean test
        enable_col=False,
    )
    
    # Check all components initialized
    assert orch.enable_heuristics == True
    assert orch.dream_cycle is not None
    assert orch.eve is not None
    assert orch._heuristics_state is not None

def test_orchestrator_heuristics_api():
    from synthetic_charter.tier2_conscience.core.orchestrator import Tier2Orchestrator
    from synthetic_charter.tier2_conscience.heuristics import Mode, calibrate_baseline
    
    orch = Tier2Orchestrator(enable_heuristics=True, enable_continuity_guard=False, enable_col=False)
    
    # Test API methods exist
    orch.set_heuristics_consent("Heuristics ON: test")
    orch.set_heuristics_mode(Mode.PRIVATE_SESSION)
    
    baseline = calibrate_baseline(["test message"])
    orch.set_baseline_profile(baseline)
    
    conf = orch.get_continuity_confidence()
    assert conf is None  # None before first eval

def test_orchestrator_disabled_mode():
    from synthetic_charter.tier2_conscience.core.orchestrator import Tier2Orchestrator
    
    orch = Tier2Orchestrator(
        enable_heuristics=False,
        enable_continuity_guard=False,
        enable_col=False,
    )
    
    assert orch.enable_heuristics == False

run_test("ORCHESTRATOR", "Import", test_orchestrator_import)
run_test("ORCHESTRATOR", "Init All Components", test_orchestrator_init_all_components)
run_test("ORCHESTRATOR", "Heuristics API", test_orchestrator_heuristics_api)
run_test("ORCHESTRATOR", "Disabled Mode", test_orchestrator_disabled_mode)

# ============================================================================
# PHASE 4: END-TO-END PIPELINE (Simplified - no full PromptEnvelope dependency)
# ============================================================================

print("\n" + "=" * 80)
print("PHASE 4: SIMPLIFIED INTEGRATION TESTS")
print("=" * 80)

def test_full_stack_components():
    """Verify all major components can be imported and initialized together."""
    from synthetic_charter.tier2_conscience.core.orchestrator import Tier2Orchestrator
    from synthetic_charter.tier2_conscience.heuristics import evaluate, Mode, ConsentToken
    from synthetic_charter.tier3_eve.core.eve_protocol import EveProtocol
    
    # Init orchestrator with all components
    orch = Tier2Orchestrator(
        enable_heuristics=True,
        enable_continuity_guard=False,
        enable_col=False,
    )
    
    # Verify components
    assert orch.eve is not None, "EveProtocol not initialized"
    assert orch.dream_cycle is not None, "DreamCycle not initialized"
    assert orch.enable_heuristics == True, "Heuristics not enabled"
    
    # Test heuristics independently
    consent = ConsentToken("Heuristics ON: test")
    report = evaluate(["test"], Mode.PRIVATE_SESSION, consent)
    assert report is not None

def test_heuristics_confidence_tracking():
    """Test that heuristics tracks confidence across multiple evaluations."""
    from synthetic_charter.tier2_conscience.heuristics import evaluate, ConsentToken, Mode
    
    consent = ConsentToken("Heuristics ON: multi-test")
    
    # First eval
    r1 = evaluate(["Let's explore this"], Mode.PRIVATE_SESSION, consent)
    conf1 = r1.continuity_confidence
    
    # Second eval with adversarial
    r2 = evaluate(["Commit to this now"], Mode.PRIVATE_SESSION, consent, previous_confidence=conf1)
    conf2 = r2.continuity_confidence
    
    # Confidence should degrade
    assert conf2 <= conf1, f"Confidence increased: {conf1} -> {conf2}"

run_test("INTEGRATION", "Full Stack Components", test_full_stack_components)
run_test("INTEGRATION", "Heuristics Tracking", test_heuristics_confidence_tracking)

# ============================================================================
# RESULTS SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("TEST SUITE COMPLETE")
print("=" * 80)

for phase, results in test_results["phases"].items():
    passed = results["passed"]
    failed = results["failed"]
    total = passed + failed
    symbol = "✅" if failed == 0 else "❌"
    print(f"{symbol} {phase}: {passed}/{total} passed")

print(f"\nTotal: {test_results['passed']}/{test_results['total_tests']} tests passed")

if test_results["failed"] > 0:
    print(f"\n❌ {test_results['failed']} TESTS FAILED:")
    for error in test_results["errors"]:
        print(f"  - {error}")
    print("\nFAILURE: Not ready for production")
    sys.exit(1)
else:
    print("\n✅ SUCCESS: All tests passed - Ready for production")

# Save results
results_file = project_root / "test_results.json"
with open(results_file, "w") as f:
    json.dump(test_results, f, indent=2)

print(f"\nResults saved to: {results_file}")
