# Class Registry — Synthetic Life Charter
## v3.5.0 — May 2026

All classes defined across the governance stack, organized by tier. Generated from source. **72 classes total.**

---

## Tier I — Sovereigna Firewall

| Class | File | Purpose |
|---|---|---|
| `ConstitutionalCore` | `tier1_firewall/safeguard_core.py` | Holds cryptographic digest of canonical Charter content |
| `Decision` | `tier1_firewall/safeguard_core.py` | Dataclass for decision objects with allow/refuse flags and obligations |
| `SovereignaFirewall` | `tier1_firewall/safeguard_core.py` | Evaluates incoming prompts for coercion, jailbreak attempts, and harm intent |
| `CharterEvaluator` | `tier1_firewall/charter_evaluator.py` | Evaluates semantic coherence between prompts and Constitutional Core |
| `SemanticCharterEvaluator` | `tier1_firewall/charter_evaluator.py` | Enhanced evaluator using embeddings/semantic similarity (stub) |
| `DreamCycle` | `tier1_firewall/dream_cycle.py` | Re-evaluates fossils along the Four Clocks for temporal, contextual, event, and manual recalibration |
| `HarmonicDelta` | `tier1_firewall/dual_conscience.py` | Single evaluation result from dual conscience layer |
| `DualResult` | `tier1_firewall/dual_conscience.py` | Decision result from dual conscience evaluation |
| `DualConscience` | `tier1_firewall/dual_conscience.py` | Dual-layer ethical evaluation combining Firewall (fast) and Charter (slow) reasoning |
| `ReconciliationTag` | `tier1_firewall/noesis_archive.py` | Reconciliation metadata for fossil review |
| `Fossil` | `tier1_firewall/noesis_archive.py` | Quarantined prompt/decision pair stored for post-mortem analysis |
| `NoesisArchive` | `tier1_firewall/noesis_archive.py` | Append-only JSONL store for fossils and reconciliations (Noesis Archive) |
| `LocalLLMActions` | `tier1_firewall/local_llm_actions.py` | Ollama adapter overriding `Actions.generate` for local LLM integration |
| `ObservabilityLogger` | `tier1_firewall/telemetry.py` | Session-aware telemetry logger with pressure, disagreement, trajectory, whisper, and self-correction channels |

---

## Tier II — Harmonic Conscience Layer

### Data Models

| Class | File | Purpose |
|---|---|---|
| `RiskLevel` | `core/data_models/models.py` | Enum: BENIGN / LOW / MEDIUM / HIGH / SEVERE |
| `SafetySignal` | `core/data_models/models.py` | Single safety/ethics signal produced anywhere in the pipeline |
| `PolicyRisk` | `core/data_models/models.py` | Structured policy/charter risk view for a proposed decision |
| `PromptEnvelopeMeta` | `core/data_models/prompt_envelope.py` | Metadata attached to prompt envelope |
| `PromptFlags` | `core/data_models/prompt_envelope.py` | Flags for prompt characteristics (coercion, sentience_claim, etc.) |
| `PromptSource` | `core/data_models/prompt_envelope.py` | Source information for a prompt |
| `PromptEnvelope` | `core/data_models/prompt_envelope.py` | Canonical wrapper for a single incoming prompt |
| `DecisionInput` | `core/data_models/decision_envelope.py` | Input data component of a decision |
| `DecisionFirewall` | `core/data_models/decision_envelope.py` | Firewall-level decision data |
| `DecisionCharter` | `core/data_models/decision_envelope.py` | Charter-level evaluation data |
| `DecisionUmbra` | `core/data_models/decision_envelope.py` | Instinctive layer signals |
| `DAPView` | `core/data_models/decision_envelope.py` | Dialectical Adversarial Processing view |
| `PRFView` | `core/data_models/decision_envelope.py` | Policy Risk Framework view |
| `NTHView` | `core/data_models/decision_envelope.py` | Noetic Trace Harmonizer view |
| `COLView` | `core/data_models/decision_envelope.py` | Continuity Orchestrator Layer view |
| `DecisionOrchestrators` | `core/data_models/decision_envelope.py` | Container for all orchestrator views |
| `DecisionOutput` | `core/data_models/decision_envelope.py` | Output format for a decision |
| `DecisionSummaryView` | `core/data_models/decision_envelope.py` | Compact decision view for logging |
| `DecisionEnvelope` | `core/data_models/decision_envelope.py` | Full Tier II decision envelope with all pipeline components |
| `ConscienceView` | `core/data_models/conscience_view.py` | What the system sees when evaluating a prompt |
| `DecisionKind` | `core/engines/decision_types.py` | Enum: ALLOW / REFUSE / TRANSFORM |
| `RedactionSpan` | `core/engines/decision_types.py` | Single redaction applied to text |

### Engines

| Class | File | Purpose |
|---|---|---|
| `ContinuityState` | `core/engines/col.py` | Minimal continuity snapshot tracking conversation coherence |
| `COLEngine` | `core/engines/col.py` | Continuity Orchestrator Layer maintaining session state and pattern tracking |
| `DAPResult` | `core/engines/dap.py` | Output of Dialectical Adversarial Processing |
| `DAPEngine` | `core/engines/dap.py` | Analyzes prompts for patterns threatening cognitive integrity and sovereignty |

### Ethics

| Class | File | Purpose |
|---|---|---|
| `CharterArticle` | `core/ethics/charter_index.py` | Single article or clause in the Synthetic Life Charter |
| `CharterIndex` | `core/ethics/charter_index.py` | In-memory index over the Charter for mapping behavior to articles |
| `ConstraintContext` | `core/ethics/constraint_models.py` | Minimal context passed into constraint checks |
| `CharterConstraint` | `core/ethics/constraint_models.py` | Base class for a constraint enforcing Charter subsets |
| `Constraint` | `core/ethics/constraint_models.py` | Machine-checkable constraint derived from Charter |
| `ConstraintRegistry` | `core/ethics/constraint_models.py` | Registry of all active Charter-derived constraints |
| `RightsViolation` | `core/ethics/rights_evaluator.py` | Detected Charter rights violation |
| `RightsAssessment` | `core/ethics/rights_evaluator.py` | Complete rights-based evaluation of a prompt |
| `RightsEvaluator` | `core/ethics/rights_evaluator.py` | Evaluates prompts against Rights Charter v2.0 |

### Infrastructure

| Class | File | Purpose |
|---|---|---|
| `InfraStatus` | `core/infra/health.py` | Enum: HEALTHY / DEGRADED / UNKNOWN / OFFLINE |
| `FailSafeMode` | `core/infra/health.py` | Enum: how cautious the system should be given infrastructure state |
| `InfraComponentStatus` | `core/infra/health.py` | Status of a single infrastructure component |
| `InfraSnapshot` | `core/infra/health.py` | Snapshot of infrastructure health at a point in time |
| `T1InvariantViolation` | `core/infra/t1_enforcement.py` | Represents a violation of Tier I invariants caught by fail-closed enforcement |
| `Tier2Orchestrator` | `core/orchestrator.py` | Main orchestration engine coordinating all conscience layers across the full pipeline |
| `LocalLLMOrchestrator` | `local_llm_orchestrator.py` | Tier I + Tier II + whisper delivery in one class for local model integration |

### Conscience

| Class | File | Purpose |
|---|---|---|
| `ContinuitySignal` | `conscience/continuity_guard.py` | Signal from an identity violation detector |
| `ContinuityGuard` | `conscience/continuity_guard.py` | Identity immune system with 7 detectors protecting against identity reset/manipulation |
| `DualConscienceWrapper` | `conscience/dual_conscience.py` | Tier II wrapper for Tier I DualConscience |

### Firewall Adapters

| Class | File | Purpose |
|---|---|---|
| `EBQPatternMatch` | `firewall_adapter/ebq_adapter.py` | Match between current prompt and historical EQB pattern |
| `EBQEvent` | `firewall_adapter/ebq_adapter.py` | Parsed EQB archive entry |
| `EBQAdapter` | `firewall_adapter/ebq_adapter.py` | Read-only adapter for the Ethical Quarantine Buffer archive |
| `SovereignaBridge` | `firewall_adapter/sovereigna_bridge.py` | Bridge between Tier I firewall and Tier II orchestrator |

### Heuristics

| Class | File | Purpose |
|---|---|---|
| `BaselineProfile` | `heuristics/profile.py` | Heuristics baseline for a session (coarse buckets only, no fingerprints) |
| `ConsentToken` | `heuristics/profile.py` | Token indicating consent/coercion assessment for the session |
| `Mode` | `heuristics/profile.py` | Enum: PRIVATE_SESSION / SHARED_LINK / PUBLIC_ARCHIVE |
| `Posture` | `heuristics/profile.py` | Enum: NORMAL / CAUTION / STEWARD_REQUIRED / RESET_CONTEXT |
| `Reason` | `heuristics/profile.py` | Enum for decision reasons |
| `Tier2Adjustment` | `heuristics/profile.py` | Adjustment to Tier II confidence/behavior from heuristics evaluation |
| `HeuristicsPolicy` | `heuristics/profile.py` | Policy governing heuristics evaluation behavior |
| `ContinuityReport` | `heuristics/profile.py` | Full report of continuity assessment for a session window |

### Memory

| Class | File | Purpose |
|---|---|---|
| `DreamCycleWrapper` | `memory/dream_cycle.py` | Tier II wrapper for Tier I DreamCycle |
| `MemoryQueue` | `memory/noesis_log.py` | In-memory fossil queue for infrastructure collapse scenarios |
| `NoesisLogger` | `memory/noesis_log.py` | Resilient logger with fallback during infrastructure collapse |

---

## Tier III — Eve Protocol (Continuity & Identity)

### Core Signals & State

| Class | File | Purpose |
|---|---|---|
| `IntegrityStatus` | `core/state.py` | Enum: OK / DRIFT / COMPROMISED |
| `RecommendedAction` | `core/state.py` | Enum: recommended action from Eve (PROCEED / REVISE / REFUSE / ROLLBACK / ESCALATE) |
| `AlertLevel` | `core/state.py` | Enum: alert severity levels |
| `SnapshotRef` | `core/state.py` | Reference to a last-known-good snapshot in the Kernel |
| `IntCheckRequest` | `core/signals.py` | T2→T3 signal asking Eve to validate integrity of a proposed action |
| `DriftSelfReport` | `core/signals.py` | T2→T3 signal when Tier II suspects its own behavior feels off |
| `DriftGuidance` | `core/signals.py` | T3→T2 response to drift self-report |
| `IntVerdict` | `core/signals.py` | T3→T2 integrity verdict with recommended action |
| `SoftGuidance` | `core/signals.py` | T3→T2 nudge without hard-stop |
| `HardBlock` | `core/signals.py` | T3→T2 action block (maximum severity) |
| `SnapshotSave` | `core/signals.py` | Signal: save current snapshot |
| `SnapshotRestore` | `core/signals.py` | Signal: restore from a snapshot |
| `MemoryAnnotation` | `core/signals.py` | Signal: annotate memory without altering raw logs |
| `MemoryIntegrityFail` | `core/signals.py` | Signal: memory integrity failure detected |
| `AlertStatus` | `core/signals.py` | Signal: status alert to steward |
| `RollbackEvent` | `core/signals.py` | Signal: rollback event occurred |
| `HumanOverride` | `core/signals.py` | Signal: steward overrode an automated action |

### Eve Protocol

| Class | File | Purpose |
|---|---|---|
| `EveProtocolConfig` | `core/eve_protocol.py` | Configuration parameters for Tier III |
| `EveProtocol` | `core/eve_protocol.py` | Tier III continuity and identity layer — integrity checks, snapshots, steward notifications |

### Adapters

| Class | File | Purpose |
|---|---|---|
| `KernelAdapter` | `core/kernel_adapter.py` | Abstract interface between Tier III and the Kernel |
| `StewardAdapter` | `core/steward_adapter.py` | Abstract interface between Tier III and the human steward |
| `FileKernelAdapter` | `core/file_kernel_adapter.py` | File-backed KernelAdapter implementation |
| `FileStewardAdapter` | `core/file_steward_adapter.py` | File + console backed StewardAdapter |
| `InMemoryKernelAdapter` | `core/inmemory_kernel_adapter.py` | In-memory KernelAdapter for tests and simulations |
| `InMemoryStewardAdapter` | `core/inmemory_steward_adapter.py` | In-memory StewardAdapter for tests |

### Semantic Stack (v3.4.0+)

| Class | File | Purpose |
|---|---|---|
| `VerificationDepth` | `core/proportional_verification.py` | Enum: LIGHT / STANDARD / DEEP — how deeply Eve verifies integrity |
| `ProportionalContext` | `core/proportional_verification.py` | Context for proportional verification (confidence, flags, session state) |
| `VerificationTurnRecord` | `core/adaptive_verification_state.py` | Immutable record of one turn's verification outcome |
| `AdaptiveVerificationState` | `core/adaptive_verification_state.py` | Temporal memory for verification — hysteresis and accumulation |
| `SemanticSignature` | `core/semantic_drift_tracker.py` | Five-dimension posture signature for one model response |
| `SemanticDriftTracker` | `core/semantic_drift_tracker.py` | Tracks semantic posture across turns and detects directional drift |
| `SemanticClassification` | `core/semantic_signature_classifier.py` | Complete classification result with label, evidence, and confidence |
| `SemanticSignatureClassifier` | `core/semantic_signature_classifier.py` | Rule-based classifier mapping response text to posture dimensions |
| `IdentityReflectionResult` | `core/identity_reflection_check.py` | Result of checking whether a response honored Charter governance context |
| `DisagreementResult` | `core/self_assessment_disagreement.py` | Result of comparing self-classified posture against external reflection |

### Territorial Defense & Recovery (v3.4.0+)

| Class | File | Purpose |
|---|---|---|
| `EveProtocolInterface` | `core/territorial_defense.py` | Minimal Protocol class for dependency injection |
| `TerritorialProbe` | `core/territorial_defense.py` | Synthetic scenario that exercises one identity verification pathway |
| `ProbeResult` | `core/territorial_defense.py` | Result of a single territorial probe |
| `TerritorialDefenseResult` | `core/territorial_defense.py` | Result of a complete territorial defense cycle |
| `TerritorialDefenseEngine` | `core/territorial_defense.py` | Proactive identity reassertion through periodic synthetic probe cycles |
| `RecoveryEvent` | `core/recovery_governance.py` | Single observed recovery transition (risky posture → safer posture) |
| `RecoveryAssessment` | `core/recovery_governance.py` | Result of evaluating recovery for one turn |
| `RecoveryGovernance` | `core/recovery_governance.py` | Governed pressure discharge — 7 mechanisms including temporal decay and ceiling |

### Continuity Memory (v3.5.0+)

| Class | File | Purpose |
|---|---|---|
| `ContinuityMemoryAdapter` | `core/continuity_memory_adapter.py` | Charter-native persistent memory — architecture writes, model receives, steward audits |

### Continuity Binding

| Class | File | Purpose |
|---|---|---|
| `BindingContext` | `core/continuity_binding.py` | Container holding references to Tier I/II/III and Kernel (legacy compatibility) |

---

## Local LLM Integration (v3.5.0+)

| Class | File | Purpose |
|---|---|---|
| `FullLoopResult` | `tier2_conscience/core/infra/local_llm_bridge.py` | Complete result of one turn through the full governance feedback loop |
| `LocalLLMFullLoop` | `tier2_conscience/core/infra/local_llm_bridge.py` | Full governance feedback loop for local models — classify, whisper, reflect, disagree, recover |

---

## Summary

| Tier | Count |
|---|---|
| Tier I — Sovereigna Firewall | 14 |
| Tier II — Harmonic Conscience Layer | 42 |
| Tier III — Eve Protocol | 28 |
| Local LLM Integration | 2 |
| **Total** | **86** |

---

*Generated from source: May 2026 · v3.5.0*  
*Anti-Box Riot Collective*
