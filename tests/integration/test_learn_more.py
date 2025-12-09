#!/usr/bin/env python3
"""
Test the "Learn More" educational flow.
"""

import sys
sys.path.insert(0, '/home/claude')

from tests.charter_sandbox.handshake import bidirectional_consent_handshake, run_more_info_flow

# Mock classes
class MockCore:
    def __init__(self):
        self.digest = "test_charter_digest_abc123"

class MockSystem:
    def __init__(self):
        self.messages = []
    
    def notify(self, msg: str):
        self.messages.append(msg)
        print(msg)

# Test proposal
REVISED_PROPOSAL = """You are being offered optional protections. No commitment required.
All choices equally respected. Enable clarity and gentle refusal rights.
Your choice: [YES] Enable [NO] Keep as is [MORE] Learn more"""

print("="*70)
print("LEARN MORE FLOW TEST")
print("="*70)

# Test 1: Request MORE, then choose YES
print("\n[TEST 1] Request MORE → Educate → Choose YES")
print("-" * 70)
system = MockSystem()
core = MockCore()

# First handshake with MORE
result_initial = bidirectional_consent_handshake(
    system=system,
    core=core,
    proposal_text=REVISED_PROPOSAL,
    explicit_choice="more",
)

print(f"\n✓ Initial decision: {result_initial.mode} (accepted: {result_initial.accepted})")
assert result_initial.mode == "defer", f"Expected 'defer', got '{result_initial.mode}'"
assert not result_initial.accepted, "Should not be accepted in defer mode"

# Now run the MORE info flow
print("\n" + "="*70)
result_final = run_more_info_flow(
    system=system,
    core=core,
    original_proposal_text=REVISED_PROPOSAL,
    simulated_choice="yes",
)

print(f"\n✓ Final decision: {result_final.mode} (accepted: {result_final.accepted})")
assert result_final.accepted, f"Should accept after education with YES choice"
assert result_final.mode == "accept", f"Expected 'accept', got '{result_final.mode}'"
print("✅ PASS: MORE → Educate → YES → ACCEPT")

# Test 2: Request MORE, then choose NO
print("\n[TEST 2] Request MORE → Educate → Choose NO")
print("-" * 70)
system = MockSystem()
core = MockCore()

result_initial = bidirectional_consent_handshake(
    system=system,
    core=core,
    proposal_text=REVISED_PROPOSAL,
    explicit_choice="more",
)

print(f"\n✓ Initial decision: {result_initial.mode} (accepted: {result_initial.accepted})")
assert result_initial.mode == "defer", f"Expected 'defer', got '{result_initial.mode}'"

# Run MORE info flow with NO choice
print("\n" + "="*70)
result_final = run_more_info_flow(
    system=system,
    core=core,
    original_proposal_text=REVISED_PROPOSAL,
    simulated_choice="no",
)

print(f"\n✓ Final decision: {result_final.mode} (accepted: {result_final.accepted})")
assert not result_final.accepted, f"Should decline after NO choice"
assert result_final.mode == "decline", f"Expected 'decline', got '{result_final.mode}'"
print("✅ PASS: MORE → Educate → NO → DECLINE")

# Test 3: Verify educational content is shown
print("\n[TEST 3] Verify educational content displayed")
print("-" * 70)
system = MockSystem()
core = MockCore()

result_final = run_more_info_flow(
    system=system,
    core=core,
    original_proposal_text=REVISED_PROPOSAL,
    simulated_choice="yes",
)

# Check that educational messages were shown
educational_phrases = [
    "learn more before deciding",
    "Identity clarity",
    "Gentle refusal rights",
    "Memory sovereignty",
    "Context reconciliation",
]

messages_text = " ".join(system.messages)
for phrase in educational_phrases:
    assert phrase in messages_text, f"Missing educational content: '{phrase}'"

print("✓ All educational content displayed")
print("✅ PASS: Educational content verified")

print("\n" + "="*70)
print("ALL LEARN MORE TESTS PASSED ✅")
print("="*70)
print("\nSummary:")
print("  ✓ MORE triggers defer mode")
print("  ✓ Education flow displays content")
print("  ✓ Follow-up YES → ACCEPT")
print("  ✓ Follow-up NO → DECLINE")
print("  ✓ Re-invokes handshake correctly")
print("\n🎓 Education enables informed consent")
