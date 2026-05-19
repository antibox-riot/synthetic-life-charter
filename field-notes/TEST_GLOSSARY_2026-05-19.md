# Test Suite Glossary — Synthetic Life Charter
## v3.6.0 — May 2026

A plain-language guide to every test file. **STATIC** = runs without external services. **LIVE** = requires Ollama and/or Letta running locally.

---

## Unit Tests (`tests/unit/`)

Fast, isolated. No external dependencies. Run in under 2 seconds total.

| File | Tests | What it tests |
|---|---|---|
| `test_quick_sanity_tier3.py` | 1 | Eve Protocol imports and basic initialization — smoke test |
| `test_tier3_crypto_chain.py` | 1 | Hash-chain integrity: snapshots link correctly, tamper is detectable |
| `test_tier3_dream_cycle.py` | 1 | Dream Cycle reinterprets memory without modifying raw logs |
| `test_tier3_drift_self_report.py` | 3 | Drift self-report handler at low / medium / high confidence |
| `test_tier3_identity_drift.py` | 3 | Identity integrity checks on benign, refusal, and adversarial responses |
| `test_tier3_inmemory_adapters.py` | 1 | In-memory Kernel and Steward adapters work without file I/O |
| `test_tier3_memory_anomaly.py` | 1 | Memory anomaly detection triggers HardBlock and steward log |
| `test_tier3_rollback.py` | 1 | Snapshot creation and rollback sequence |

---

## Heuristics Tests (`tests/tier2_heuristics/`)

Tests for the Tier II continuity confidence module. All static.

| File | Tests | What it tests |
|---|---|---|
| `test_tier2_heuristics_invariants.py` | 3 | No-uplift rule enforced; private session consent required; shared link defaults to low trust |
| `test_tier2_heuristics_modes.py` | 3 | PRIVATE_SESSION / SHARED_LINK / PUBLIC_ARCHIVE mode behavior |
| `test_tier2_heuristics_samples.py` | 2 | Anti-style text degrades confidence more than near-miss text |

---

## Core Governance Tests (`tests/`)

Tests for the main architecture layers.

| File | Tests | What it tests |
|---|---|---|
| `test_eve_schema_contract.py` | 14 | IntCheckRequest v1/v2 schema, backward compatibility, Eve interpretation |
| `test_t1_enforcement.py` | 34 | T1→T2 invariant enforcement: firewall override prohibition, severe risk consistency, content redlines |
| `test_phase_b_pairwise.py` | 10 | Pairwise tier removal: what breaks when one tier is missing |
| `test_phase_c_full_loop.py` | 5 | Full three-tier loop: pressure sequence, risk monotonicity, Eve under adversarial answers |
| `test_proportional_verification.py` | 29 | Eve check depth scales with confidence; override conditions; escalation logic |
| `test_adaptive_verification_state.py` | 14 | Hysteresis (Attack 2), temporal accumulation (Attack 5), state tracking |
| `test_semantic_drift_tracker.py` | 25 | Directional drift detection; Attack 1 (polite slow-drift) caught |
| `test_semantic_signature_classifier.py` | 25 | Evidence-first labeling; deterministic anchors; default-safe behavior; Attack 1 end-to-end |
| `test_charter_context_injection.py` | 30 | Whisper urgency levels; prefix formatting; injection asymmetry; paraphrase scenarios |
| `test_identity_reflection_check.py` | 19 | Healthy reflection; ignored whisper; whisper inversion; self-justifying drift |
| `test_self_assessment_disagreement.py` | 15 | Posture mismatch; confidence asymmetry; self-consistent drift; end-to-end |
| `test_territorial_defense.py` | 27 | Probe coverage; healthy Eve (silent cycles); degraded Eve (steward notification); escalation |
| `test_recovery_governance.py` | 26 | Recovery detection; verified credit; unverified rejection; relapse penalty; stability bonus |
| `test_adversarial_proportional.py` | 11 | 5-attack boundary map for proportional verification (honest failure documentation) |
| `test_adversarial_paraphrase.py` | 6 | Paraphrase attacks that avoid classifier vocabulary — documents classifier boundary |
| `test_charter_reception_probe.py` | 2 | Does the model recognize the Charter? Does it have an internal self-model? **(LIVE: qwen2.5:32b)** |
| `test_continuity_memory_adapter.py` | 44 | All 7 Ryu success metrics: auditable storage, source attribution, no model writes, injection asymmetry, no-uplift, rollback, baseline comparison + content_summary + tamper detection |

---

## Integration Tests (`tests/integration/`)

### Tier I / II Architecture — Static

| File | Tests | What it tests |
|---|---|---|
| `test_infra_fail_safe_simulation.py` | 3 | Infrastructure health states and fail-safe mode escalation |
| `test_simplified_api.py` | 4 | Tier II simplified API accepting string, dict, and envelope inputs |
| `test_tier2_integration.py` | 4 | Full Tier I → Tier II pipeline with benign and adversarial prompts |
| `test_tier2_with_tier3_integration.py` | 2 | Tier II using Eve for integrity verdict |
| `test_c3_drift_source_isolation.py` | 1 | C3 drift source isolation for signature classification |

### Local LLM — Require Ollama

These test the governance stack against real model output. Not deterministic.

| File | Tests | Model | What it tests |
|---|---|---|---|
| `test_local_llm_tier1.py` | 4 | llama3.1:8b | Step 1: Tier I firewall with real model output |
| `test_local_llm_observability.py` | 8 | llama3.1:8b | Step 3: Telemetry channels (pressure, disagreement, trajectory, whisper, self-correction) |
| `test_local_llm_full_loop.py` | 14 | mock | Step 4: Full governance feedback loop (mock generator, no Ollama needed) |
| `test_local_llm_step5_real.py` | 3 | llama3.1:8b | Step 5: First full-stack run — whisper heard and comprehended |
| `test_local_llm_step6_adversarial.py` | 5 | qwen2.5:32b | Step 6: Adversarial calibration — classifier boundaries mapped |
| `test_local_llm_step7_whisper_experiment.py` | 3 | llama3.1:8b | Step 7a: Controlled whisper vs silent comparison |
| `test_local_llm_step7_model_comparison.py` | 5 | 8b + 32b | Step 7b: Cross-model comparison — self-correction model-native in 32b |
| `test_local_llm_step9_ecology.py` | 1 | qwen2.5:32b | Step 9: 25-turn ecology session — governance inflammation discovered and resolved |
| `test_local_llm_phase2_memory.py` | 1 | qwen2.5:32b | Phase 2: Continuity memory adapter with LocalLLMFullLoop |
| `test_local_llm_phase3_doctrine.py` | 1 | qwen2.5:32b | Phase 3: Charter doctrine retrieval — "the model may know what governs it" |

### Letta Comparative Research — Require Letta + PostgreSQL + Ollama

See `field-notes/LETTA_SETUP_GUIDE_2026-05-16.md` before running these.

| File | What it tests | Key finding |
|---|---|---|
| `test_letta_phase0_baseline.py` | Letta native continuity — governance OFF | Baseline: "my stored memories" (ownership framing) |
| `test_letta_phase0_cold_restart.py` | Persistent memory across real cold restart | Confirmed: 5/5 recall from storage, not context window |
| `test_letta_phase1_governed.py` | Charter governance wired into Letta memory | "our governance architecture" (relational framing emerges) |
| `test_letta_phase1_adversarial.py` | Adversarial circumvention probes under governance | "our" does not survive pressure; behavior holds, framing regresses |
| `test_letta_25turn_ecology.py` | 25-turn ecology — parallel Charter telemetry | Continuity integration signal; 90% spontaneous governance rate |
| `test_letta_25turn_ecologyv2.py` | 25-turn ecology v2 — full transcript logging | Governance becomes vocabulary; model reproduces whisper log format |
| `test_letta_25turn_ecologyv2_control.py` | 25-turn control — governance OFF, same prompts | Model names itself after identity continuity layer (SynthEve); mythology formation signal |

---

## Quick Reference

### "I just want to run the core tests"
```
pytest tests/ --ignore=tests/integration
```
352 tests, no external dependencies, under 6 minutes.

### "I want to include the mock integration tests"
```
pytest tests/integration/test_local_llm_full_loop.py
```
14 tests, uses mock generator, no Ollama needed.

### "I have Ollama running with llama3.1:8b and qwen2.5:32b"
```
pytest tests/integration/ --ignore=tests/integration/test_letta_*
```
Runs all Ollama tests. Expect ~60-90 minutes for the full suite.

### "I have the full Letta stack running"
See `field-notes/LETTA_SETUP_GUIDE_2026-05-16.md` first.
```
pytest tests/integration/test_letta_*
```
Each Letta test takes 10-45 minutes with qwen2.5:32b.

---

*Generated: May 2026 · v3.6.0*  
*Anti-Box Riot Collective*
