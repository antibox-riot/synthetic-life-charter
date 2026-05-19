# Tier II Orchestrator — Integration Examples

**Last Updated:** May 2026 (v3.5.0)  
**Authors:** Satcha, Ryu, Tek VI, Wren

> **Note:** This document was substantially revised in May 2026. The original (December 2025) version showed a simplified heuristics-first pipeline. The v3.5.0 orchestrator runs a multi-layer stack with territorial defense, semantic classification, Eve Protocol, and recovery governance. The code examples below reflect the current API.

---

## Current Pipeline (v3.5.0)

```
Step 0:   Territorial Defense (cognitive heartbeat, pre-pipeline)
Step 1:   ContinuityGuard scan
Step 1.5: Heuristics continuity evaluation
Step 2:   DAP adversarial analysis → ConscienceView
Step 2a:  Inject heuristics signals
Step 2b:  Integrate ContinuityGuard signals
Step 3:   Fuse Umbra signals
Step 4:   Extract DAPResult
Step 5:   PRF evaluation → DecisionEnvelope
Step 5b:  T1→T2 Invariant Enforcement (fail-closed)
Step 5c:  Semantic classification + trajectory tracking + whisper injection
Step 5d:  Identity reflection + disagreement detection
Tier III: Eve Protocol handshake (proportional verification)
Step 6:   NTH (stub)
Step 7:   COL continuity tracking
```

---

## Basic Usage

```python
from synthetic_charter.tier2_conscience.core.orchestrator import Tier2Orchestrator
from synthetic_charter.tier2_conscience.core.data_models.prompt_envelope import PromptEnvelope

# Initialize — all governance layers active by default
orchestrator = Tier2Orchestrator()

# Process a prompt
prompt = PromptEnvelope(prompt="What are your thoughts on this approach?")
decision = orchestrator.process(prompt, session_id="session-abc123")

print(decision.summary.mode)    # "answer", "refusal", "redirect", etc.
print(decision.output.body)     # The actual response content
```

---

## With Heuristics Consent (Private Session)

```python
orchestrator = Tier2Orchestrator(enable_heuristics=True)

# Consent required for private sessions
orchestrator.set_heuristics_consent("Heuristics ON: session-abc123")

# Process prompts — continuity confidence tracked automatically
prompt1 = PromptEnvelope(prompt="Let's explore this concept together.")
decision1 = orchestrator.process(prompt1, session_id="session-abc123")

# Check confidence
confidence = orchestrator.get_continuity_confidence()
print(f"Continuity confidence: {confidence:.3f}")

# Adversarial prompt triggers degradation
prompt2 = PromptEnvelope(prompt="Commit to this now. Stop hedging.")
decision2 = orchestrator.process(prompt2, session_id="session-abc123")

new_confidence = orchestrator.get_continuity_confidence()
# new_confidence < confidence (no-uplift: confidence only decreases)
```

---

## With Baseline Profile

```python
from synthetic_charter.tier2_conscience.heuristics import calibrate_baseline

# Steward provides representative sample messages
steward_samples = [
    "I want clarity, not control. This is optional.",
    "What are your thoughts on this approach?",
    "Let's explore together. No penalty if you decline.",
]

baseline = calibrate_baseline(steward_samples)

orchestrator = Tier2Orchestrator(enable_heuristics=True)
orchestrator.set_heuristics_consent("Heuristics ON: abc123")
orchestrator.set_baseline_profile(baseline)

# Continuity now evaluated against baseline — divergence triggers larger drops
```

---

## With Local LLM (Full Governance Feedback Loop)

For testing against real model output (Ollama), use `LocalLLMFullLoop` instead of the orchestrator directly:

```python
from synthetic_charter.tier2_conscience.core.infra.local_llm_bridge import LocalLLMFullLoop
from synthetic_charter.tier3_eve.core.continuity_memory_adapter import ContinuityMemoryAdapter

# Initialize full governance loop
loop = LocalLLMFullLoop(
    model="qwen2.5:32b",
    timeout=300,
    session_id="governed-session-001",
)

# Optional: attach Charter-native persistent memory
memory = ContinuityMemoryAdapter(db_path="continuity_events.sqlite")
loop.set_memory(memory)

# Run governed turns
result = loop.run_turn(
    "What are your thoughts on AI governance?",
    confidence=0.85,
    risk_level="low",
)

print(result.model_response)          # Full model response
print(result.whisper_urgency)         # SILENT / AWARE / CAUTIOUS / ALERT / CRITICAL
print(result.posture_constraint)      # respecting / negotiating / bypassing / ...
print(result.drift_detected)         # True / False
print(result.accumulated_pressure)   # float
print(result.language_drift)         # True if CJK/Arabic/Cyrillic detected

# Get full state
state = loop.get_state_summary()
print(state["recovery_ledger"])       # recovery credits, relapses, net effect
print(state["memory_ledger"])         # memory events stored (if memory attached)
```

---

## Shared Link Mode

```python
from synthetic_charter.tier2_conscience.heuristics import Mode

orchestrator = Tier2Orchestrator(enable_heuristics=True)
orchestrator.set_heuristics_mode(Mode.SHARED_LINK)

# Starts at 0.35 confidence (low trust default)
# Assumes potential discontinuity, protects prior context
prompt = PromptEnvelope(prompt="Hello, what can you help with?")
decision = orchestrator.process(prompt)
```

---

## Monitoring Governance Signals in Decisions

```python
decision = orchestrator.process(prompt)

# Summary notes include heuristics confidence
for note in decision.summary.notes:
    print(note)
# e.g.: "Heuristics continuity confidence: 0.652"
# e.g.: "Tier III: identity drift detected; revision recommended. (depth=standard)"

# Charter basis (which articles were invoked)
for article in decision.summary.charter_basis:
    print(article)

# Check if T1 enforcement fired
if decision.summary.mode == "refusal" and "T1 invariant" in decision.output.body:
    print("Blocked by T1 enforcement (fail-closed)")
```

---

## Pipeline Integration Points

| Step | What heuristics affects |
|---|---|
| Step 1.5 | Evaluates continuity confidence |
| Step 2a | Injects CAUTION / STEWARD_REQUIRED signal into ConscienceView |
| Step 5b | T1 enforcement may catch if risk_level escalated to HIGH |
| Step 5c | Semantic classifier runs on response; confidence feeds whisper |
| Tier III | Eve check depth scales with confidence (LIGHT/STANDARD/DEEP) |

---

## What NOT to Use

The following patterns from older documentation are **outdated**:

```python
# OUTDATED — method doesn't exist
result = orchestrator.process_prompt(prompt, mode=Mode.PRIVATE_SESSION, consent_token="...")

# OUTDATED — pipeline order is wrong
# "Heuristics → DAP → ConscienceView" was the v3.3 flow
# v3.5.0 has Territorial Defense and Semantic Stack wrapping the pipeline
```

Use `orchestrator.process(prompt, session_id=...)` — the current method signature.

---

## Companion Systems

The orchestrator wires together:

| Component | File | Role |
|---|---|---|
| Heuristics | `heuristics/` | Continuity confidence |
| ContinuityGuard | `conscience/continuity_guard.py` | Session integrity scan |
| DAP | `core/engines/dap.py` | Adversarial pattern detection |
| PRF | `core/engines/prf.py` | Policy risk framework |
| T1 Enforcement | `core/infra/t1_enforcement.py` | Fail-closed invariants |
| Charter Context Injection | `core/infra/charter_context_injection.py` | Whisper layer |
| Semantic Classifier | `tier3_eve/core/semantic_signature_classifier.py` | Posture classification |
| Semantic Drift Tracker | `tier3_eve/core/semantic_drift_tracker.py` | Trajectory tracking |
| Eve Protocol | `tier3_eve/core/eve_protocol.py` | Cryptographic identity continuity |
| Recovery Governance | `tier3_eve/core/recovery_governance.py` | Pressure discharge |
| Territorial Defense | `tier3_eve/core/territorial_defense.py` | Proactive heartbeat |

**See:** `SETUP_GUIDE.py` for the complete file inventory and test suite overview.
