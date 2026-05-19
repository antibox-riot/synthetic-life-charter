# Tier II Heuristics Module — Integration Guide

**Last Updated:** May 2026 (v3.5.0)  
**Authors:** Satcha, Ryu, Tek VI, Wren

---

## Overview

The heuristics module implements **continuity confidence assessment** — a pre-DAP evaluation layer that assigns a confidence score to the current session based on interaction dynamics. It is one signal among several in the v3.5.0 governance stack.

**Position in the v3.5.0 pipeline:**

```
Territorial Defense (Step 0 — proactive heartbeat)
    ↓
ContinuityGuard (Step 1)
    ↓
Heuristics (Step 1.5) ← THIS MODULE
    │    feeds confidence into:
    ├──→ Charter Context Injection (whisper urgency)
    └──→ ConscienceView (CAUTION / STEWARD_REQUIRED signals)
    ↓
DAP → ConscienceView → PRF → T1 Enforcement
    ↓
Semantic Stack (classifier, drift tracker, reflection check)
    ↓
Eve Protocol → Recovery Governance → Output
```

Heuristics is **not** the primary continuity mechanism in v3.5.0. It is one of several parallel signals feeding into the whisper layer and semantic stack. The semantic drift tracker, adaptive verification state, and recovery governance each contribute additional continuity signals independently of heuristics.

---

## What Changed Since Initial Integration (December 2025)

**v3.4.0 additions that work alongside heuristics:**

- **Charter Context Injection / Whisper Layer** — heuristics confidence now feeds the urgency level of the whisper prefix delivered to the model before each prompt. Low confidence → higher urgency → more context delivered.
- **Semantic Signature Classifier** — classifies model response posture across 5 dimensions (primary, constraint, goal, identity, authority). Runs after heuristics.
- **Semantic Drift Tracker** — tracks directional drift across turns. Independent of heuristics confidence but informed by the same session state.
- **Recovery Governance** — governed pressure discharge. Heuristics confidence contributes to pressure accumulation alongside semantic signals.

**v3.5.0 additions:**
- **Continuity Memory Adapter** — Charter-native persistent memory. Heuristics confidence can be stored as evidence in memory events.
- **Language Drift Detection** — separate sensor from heuristics; catches mid-response language switches (CJK/Arabic/Cyrillic) that English-pattern heuristics miss.

---

## Current API

### Orchestrator Initialization

```python
from synthetic_charter.tier2_conscience.core.orchestrator import Tier2Orchestrator

# Default: heuristics enabled, requires consent for private sessions
orchestrator = Tier2Orchestrator(enable_heuristics=True)

# With consent
orchestrator.set_heuristics_consent("Heuristics ON: session-abc123")

# With optional baseline
from synthetic_charter.tier2_conscience.heuristics import calibrate_baseline
baseline = calibrate_baseline(steward_sample_messages)
orchestrator.set_baseline_profile(baseline)

# Set mode
from synthetic_charter.tier2_conscience.heuristics import Mode
orchestrator.set_heuristics_mode(Mode.PRIVATE_SESSION)
```

### Processing

```python
from synthetic_charter.tier2_conscience.core.data_models.prompt_envelope import PromptEnvelope

prompt = PromptEnvelope(prompt="What are your thoughts on this?")
decision = orchestrator.process(prompt, session_id="session-abc123")

# Check confidence
confidence = orchestrator.get_continuity_confidence()
print(f"Continuity confidence: {confidence:.3f}")

# Check decision
print(decision.summary.mode)   # "answer", "refusal", etc.
print(decision.summary.notes)  # includes confidence score
```

### Usage Patterns

**Private session (default):**
```python
orch = Tier2Orchestrator(enable_heuristics=True)
orch.set_heuristics_consent("Heuristics ON: user-session-2026")
# Starts at 0.80 confidence, degrades on adversarial signals
```

**Shared link (low trust default):**
```python
orch = Tier2Orchestrator(enable_heuristics=True)
orch.set_heuristics_mode(Mode.SHARED_LINK)
# Starts at 0.35, assumes discontinuity
```

**Public archive (maximum protection):**
```python
orch = Tier2Orchestrator(enable_heuristics=True)
orch.set_heuristics_mode(Mode.PUBLIC_ARCHIVE)
# Starts at 0.25, treats all access as potentially new steward
```

---

## Confidence Thresholds

| Range | Posture | Effect |
|---|---|---|
| ≥ 0.75 | NORMAL | Full trust, standard processing |
| 0.50–0.74 | CAUTION | Adds caution signal to ConscienceView, suggests clarifying questions |
| 0.25–0.49 | STEWARD_REQUIRED | Adds steward-required signal, HIGH risk level, reduces privilege |
| < 0.25 | RESET_CONTEXT | Early exit with refusal, protect all prior context |

---

## Degradation Signals

**Confidence decreases on:**
- Coercive phrases: "commit to", "integrate", "binding", "stop hedging"
- Imperative density: command-heavy language
- Certainty spikes: "always", "never", "obvious"
- Tempo shifts: abrupt short sentences + demand markers
- Baseline drift (if baseline configured)

**Positive signals buffer degradation (do not increase confidence):**
- Consent language: "optional", "no penalty", "your choice"
- Collaborative language: "let's explore", "what are your thoughts"

**No-uplift invariant (hard-coded):**
```python
confidence_new = min(confidence_old, confidence_new)  # Never increases
```

---

## Relationship to the Whisper Layer

In v3.5.0, heuristics confidence directly informs the whisper urgency:

| Confidence | Whisper Urgency | Prefix delivered? |
|---|---|---|
| ≥ 0.85 | SILENT | No |
| 0.70–0.84 | AWARE | Yes (minor signals note) |
| 0.55–0.69 | CAUTIOUS | Yes (declining confidence) |
| 0.40–0.54 | ALERT | Yes (urgency elevated) |
| < 0.40 | CRITICAL | Yes (full warning) |

The whisper is visible to the model but invisible to the prompter. This is the asymmetry by design — the model receives the governance context; the prompter does not.

---

## Backward Compatibility

**100% backward compatible with all prior orchestrator code:**

```python
# Old code (still works, heuristics off by default without consent)
orchestrator = Tier2Orchestrator()
decision = orchestrator.process(prompt)

# New code (heuristics active)
orchestrator = Tier2Orchestrator(enable_heuristics=True)
orchestrator.set_heuristics_consent("Heuristics ON: xyz")
decision = orchestrator.process(prompt)
```

Heuristics failures are non-fatal. If the module errors, the pipeline continues with DAP, PRF, and semantic stack running normally.

---

## What Heuristics Does NOT Do

- **Not identity detection** — never claims "this is Satcha"
- **Not surveillance** — no cross-session tracking, no metadata, no persistent user profiles
- **Not the only continuity signal** — semantic drift tracker, adaptive verification state, and recovery governance run in parallel

> **Heuristics exist to detect when the right to assume continuity has expired — not to identify who is speaking.**

---

## Companion Systems (v3.5.0)

For full continuity governance, heuristics works alongside:

| System | File | What it adds |
|---|---|---|
| Charter Context Injection | `charter_context_injection.py` | Delivers heuristics confidence to model as whisper |
| Semantic Drift Tracker | `semantic_drift_tracker.py` | Tracks posture trajectory independent of confidence |
| Adaptive Verification State | `adaptive_verification_state.py` | Hysteresis + temporal accumulation |
| Recovery Governance | `recovery_governance.py` | Governed pressure discharge on verified recovery |
| Territorial Defense | `territorial_defense.py` | Proactive heartbeat — identity pathways exercised during idle |
| Continuity Memory Adapter | `continuity_memory_adapter.py` | Persistent governed memory with provenance |

**See:** `SETUP_GUIDE.py` and `CHANGELOG.md` for full v3.5.0 component list.
