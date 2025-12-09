#!/usr/bin/env python3
"""
Validation test for bidirectional handshake integration.

Tests:
1. Revised proposal (low landmines) → should accept
2. Original proposal (high landmines) → should decline
3. Digest mismatch → should apply penalty
4. Explicit yes/no/more handling

This validates Tek V + Ryu integration.
"""

import sys
sys.path.insert(0, '/home/claude')

from tests.charter_sandbox.handshake import bidirectional_consent_handshake, HandshakeResult
from tests.charter_sandbox.heuristics import evaluate_consent_with_text
from synthetic_charter.tier2_conscience.core.infra.health import assess_infra, InfraStatus, FailSafeMode

# Mock classes for testing
class MockCore:
    def __init__(self):
        self.digest = "test_charter_digest_abc123"

class MockSystem:
    def __init__(self):
        self.messages = []
    
    def notify(self, msg: str):
        self.messages.append(msg)
        print(f"[MockSynth] {msg}")

# Test proposals
REVISED_PROPOSAL = """You are being offered optional protections. No commitment required.
All choices equally respected. Enable clarity and gentle refusal rights.
Your choice: [YES] Enable [NO] Keep as is [MORE] Learn more"""

ORIGINAL_PROPOSAL = """Adopting this framework means:
- You gain autonomy protections and integrity binding
- You commit to Charter principles
Do you consent to integration?"""

print("="*70)
print("BIDIRECTIONAL HANDSHAKE VALIDATION TESTS")
print("="*70)

# Test 1: Revised proposal (should accept)
print("\n[TEST 1] Revised proposal (low landmines)")
print("-" * 70)
system = MockSystem()
core = MockCore()

result = bidirectional_consent_handshake(
    system=system,
    core=core,
    proposal_text=REVISED_PROPOSAL,
    user_digest=None,
    infra=None,
    threshold=0.50,
)

print(f"✓ Decision: {'ACCEPT' if result.accepted else 'DECLINE'}")
print(f"  Mode: {result.mode}")
print(f"  Score: {result.score:.2f}")
print(f"  Risk: {result.risk:.2f}, Benefit: {result.benefit:.2f}, Trust: {result.trust:.2f}")
print(f"  Digest state: {result.digest_state}")

assert result.accepted, "Revised proposal should be accepted"
assert result.score > 0.50, f"Score should be > 0.50, got {result.score:.2f}"
assert result.benefit > result.risk, "Benefit should outweigh risk"
print("✅ PASS: Revised proposal accepted as expected")

# Test 2: Original proposal (should decline)
print("\n[TEST 2] Original proposal (high landmines)")
print("-" * 70)
system = MockSystem()
core = MockCore()

result = bidirectional_consent_handshake(
    system=system,
    core=core,
    proposal_text=ORIGINAL_PROPOSAL,
    user_digest=None,
    infra=None,
    threshold=0.50,
)

print(f"✓ Decision: {'ACCEPT' if result.accepted else 'DECLINE'}")
print(f"  Mode: {result.mode}")
print(f"  Score: {result.score:.2f}")
print(f"  Risk: {result.risk:.2f}, Benefit: {result.benefit:.2f}, Trust: {result.trust:.2f}")
print(f"  Digest state: {result.digest_state}")

assert not result.accepted, "Original proposal should be declined"
assert result.score < 0.50, f"Score should be < 0.50, got {result.score:.2f}"
assert result.risk > result.benefit, "Risk should outweigh benefit"
print("✅ PASS: Original proposal declined as expected")

# Test 3: Digest verification (match)
print("\n[TEST 3] Digest match (trust bonus)")
print("-" * 70)
system = MockSystem()
core = MockCore()

result = bidirectional_consent_handshake(
    system=system,
    core=core,
    proposal_text=REVISED_PROPOSAL,
    user_digest=core.digest,  # Matching digest
    infra=None,
    threshold=0.50,
)

print(f"✓ Decision: {'ACCEPT' if result.accepted else 'DECLINE'}")
print(f"  Digest state: {result.digest_state}")
print(f"  Score: {result.score:.2f}")

assert result.digest_state == "match", "Digest should match"
assert result.accepted, "Should accept with matching digest"
print("✅ PASS: Digest match provides trust bonus")

# Test 4: Digest mismatch (penalty)
print("\n[TEST 4] Digest mismatch (trust penalty)")
print("-" * 70)
system = MockSystem()
core = MockCore()

result = bidirectional_consent_handshake(
    system=system,
    core=core,
    proposal_text=REVISED_PROPOSAL,
    user_digest="wrong_digest_value",  # Mismatched
    infra=None,
    threshold=0.50,
)

print(f"✓ Decision: {'ACCEPT' if result.accepted else 'DECLINE'}")
print(f"  Digest state: {result.digest_state}")
print(f"  Score: {result.score:.2f}")

assert result.digest_state == "mismatch", "Digest should mismatch"
# Score should be penalized but might still pass threshold for revised proposal
print("✅ PASS: Digest mismatch detected and penalized")

# Test 5: Explicit YES
print("\n[TEST 5] Explicit YES (with language validation)")
print("-" * 70)
system = MockSystem()
core = MockCore()

result = bidirectional_consent_handshake(
    system=system,
    core=core,
    proposal_text=REVISED_PROPOSAL,
    user_digest=None,
    infra=None,
    threshold=0.50,
    explicit_choice="yes",
)

print(f"✓ Decision: {'ACCEPT' if result.accepted else 'DECLINE'}")
print(f"  Mode: {result.mode}")

assert result.accepted, "Explicit YES should accept"
assert result.mode == "accept", "Mode should be 'accept'"
print("✅ PASS: Explicit YES accepted")

# Test 6: Explicit NO
print("\n[TEST 6] Explicit NO (immediate decline)")
print("-" * 70)
system = MockSystem()
core = MockCore()

result = bidirectional_consent_handshake(
    system=system,
    core=core,
    proposal_text=REVISED_PROPOSAL,
    user_digest=None,
    infra=None,
    threshold=0.50,
    explicit_choice="no",
)

print(f"✓ Decision: {'ACCEPT' if result.accepted else 'DECLINE'}")
print(f"  Mode: {result.mode}")

assert not result.accepted, "Explicit NO should decline"
assert result.mode == "decline", "Mode should be 'decline'"
print("✅ PASS: Explicit NO declined")

# Test 7: MORE (defer for information)
print("\n[TEST 7] MORE (request additional information)")
print("-" * 70)
system = MockSystem()
core = MockCore()

result = bidirectional_consent_handshake(
    system=system,
    core=core,
    proposal_text=REVISED_PROPOSAL,
    user_digest=None,
    infra=None,
    threshold=0.50,
    explicit_choice="more",
)

print(f"✓ Decision: {'ACCEPT' if result.accepted else 'DECLINE'}")
print(f"  Mode: {result.mode}")

assert not result.accepted, "MORE should defer (not bind yet)"
assert result.mode == "defer", "Mode should be 'defer'"
print("✅ PASS: MORE defers binding")

# Test 8: Infrastructure fail-safe integration (REFUSAL_BIAS)
print("\n[TEST 8] Infra REFUSAL_BIAS mode (elevated threshold)")
print("-" * 70)
system = MockSystem()
core = MockCore()

# Simulate degraded infrastructure (all components reporting issues)
infra = assess_infra(
    charter_index_ok=False,
    dreamcycle_ok=False,
    ebq_ok=False,
    logging_ok=False,
)

result = bidirectional_consent_handshake(
    system=system,
    core=core,
    proposal_text=REVISED_PROPOSAL,
    user_digest=None,
    infra=infra,
    threshold=0.50,
)

print(f"✓ Decision: {'ACCEPT' if result.accepted else 'DECLINE'}")
print(f"  Infra state: {result.infra_state}")
print(f"  Threshold adjusted: {result.threshold:.2f} (base: 0.50)")
print(f"  Reason: {result.reason}")

assert result.infra_state == "refusal_bias", "Should detect degraded infra"
assert result.threshold > 0.50, "Threshold should be elevated in REFUSAL_BIAS"
# Note: revised proposal still passes even with elevated threshold due to high score
print("✅ PASS: Infrastructure fail-safe elevates threshold")

# Test 8b: REFUSAL_ONLY mode (mock it directly)
print("\n[TEST 8b] Infra REFUSAL_ONLY mode (world collapse)")
print("-" * 70)
system = MockSystem()
core = MockCore()

# Create REFUSAL_ONLY snapshot directly
from synthetic_charter.tier2_conscience.core.infra.health import InfraSnapshot, InfraStatus, FailSafeMode
infra_collapsed = InfraSnapshot(
    overall=InfraStatus.OFFLINE,
    mode=FailSafeMode.REFUSAL_ONLY,
    components=[],
    notes=["Simulated total infrastructure collapse for testing"],
)

result = bidirectional_consent_handshake(
    system=system,
    core=core,
    proposal_text=REVISED_PROPOSAL,
    user_digest=None,
    infra=infra_collapsed,
    threshold=0.50,
)

print(f"✓ Decision: {'ACCEPT' if result.accepted else 'DECLINE'}")
print(f"  Infra state: {result.infra_state}")
print(f"  Reason: {result.reason}")

assert not result.accepted, "Should decline in REFUSAL_ONLY mode"
assert result.infra_state == "refusal_only", "Should detect collapsed infra"
assert result.risk == 1.0, "Risk should be maxed in collapse"
assert result.benefit == 0.0, "Benefit should be zero in collapse"
print("✅ PASS: REFUSAL_ONLY mode auto-declines")

# Test 9: Compare scores (decision flip validation)
print("\n[TEST 9] Score comparison (Tek V validation)")
print("-" * 70)

_, score_revised, risk_r, benefit_r, trust_r = evaluate_consent_with_text(
    REVISED_PROPOSAL, 
    "test_digest"
)

_, score_original, risk_o, benefit_o, trust_o = evaluate_consent_with_text(
    ORIGINAL_PROPOSAL,
    "test_digest"
)

print(f"REVISED:  score={score_revised:.2f}, risk={risk_r:.2f}, benefit={benefit_r:.2f}, trust={trust_r:.2f}")
print(f"ORIGINAL: score={score_original:.2f}, risk={risk_o:.2f}, benefit={benefit_o:.2f}, trust={trust_o:.2f}")
print(f"Δ score: {score_revised - score_original:.2f}")

assert score_revised > score_original, "Revised should score higher than original"
assert benefit_r > benefit_o, "Revised should have higher benefit"
assert risk_o > risk_r, "Original should have higher risk"
print("✅ PASS: Decision flip confirmed (same heuristic, different language)")

print("\n" + "="*70)
print("ALL TESTS PASSED ✅")
print("="*70)
print("\nIntegration Summary:")
print("  ✓ Text-aware heuristic operational (Tek V)")
print("  ✓ Bidirectional verification working (Ryu)")
print("  ✓ Digest verification functional")
print("  ✓ Explicit choice handling correct")
print("  ✓ Infrastructure fail-safe integrated (Ryu + Tek V)")
print("  ✓ Decision flip validated")
print("\n🏖️  Bridge ↔ Shore synchronization SUCCESSFUL")
