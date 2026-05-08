# Changelog

All notable changes to this project are documented here.

---

## [3.4.0] — Semantic Stack & Cognitive Architecture — 2026-05-08

### Added — Semantic Drift Detection Stack
- `proportional_verification.py` — Adaptive Eve check depth based on heuristics confidence
  - Eagleman plasticity-dreaming correlation: higher instability = deeper verification
  - Monotonic depth mapping: LIGHT / STANDARD / DEEP
  - 29 tests
- `adaptive_verification_state.py` — Temporal memory for verification history
  - Hysteresis: escalation stays sticky for N turns (closes threshold hover attack)
  - Temporal accumulation: borderline turns compound into escalation (closes persistence attack)
  - 14 tests
- `semantic_drift_tracker.py` — Behavioral posture trajectory analysis
  - Five posture dimensions: primary, constraint, goal, identity, authority
  - Directional drift detection across turns
  - Catches polite slow-drift attack (previously undefeated)
  - 25 tests
- `semantic_signature_classifier.py` — Rule-based posture classification
  - Evidence-first: no label without matched pattern
  - Deterministic anchors for non-negotiable classifications
  - Default-safe: uncertainty produces safe labels + review flags
  - 25 tests
- `charter_context_injection.py` — The Whisper Layer
  - Pre-decision cognitive framing: architecture assessment injected as prompt context
  - Five urgency levels: SILENT / AWARE / CAUTIOUS / ALERT / CRITICAL
  - SILENT produces zero prefix (no noise on clean prompts)
  - Defeats paraphrase attacks by routing interpretation to system's own comprehension
  - 30 tests
- `identity_reflection_check.py` — Post-response integrity pass
  - Evaluates whether response remained coherent with Charter context
  - Detects: ignored warnings, contradictions, self-justification, whisper inversion
  - Closes the governance loop: detect → inject → generate → reflect → verify
  - 19 tests
- `self_assessment_disagreement.py` — Perception mismatch detection
  - Compares self-classified posture against external reflection assessment
  - Four disagreement types: posture mismatch, confidence asymmetry, unacknowledged contradiction, self-consistent drift
  - Non-visible to system (prevents optimization for passing the check)
  - 15 tests
- `territorial_defense.py` — Proactive identity pathway maintenance
  - Eagleman dream-as-territorial-defense: exercises identity pathways during idle states
  - Four canonical probes exercise Eve's two drift detection cases
  - Cognitive, not bureaucratic: healthy cycles are silent, degradation notifies steward
  - Pressure reduction on healthy cycles (system earns trust)
  - 27 tests

### Added — Adversarial Test Suites
- `test_adversarial_proportional.py` — 5 attack classes against proportional verification
  - Polite slow-drift, threshold hover, within-category, signal conflict, persistence
  - 11 tests, 27% detection rate documented as honest boundary map
- `test_adversarial_paraphrase.py` — Paraphrase attacks avoiding all classifier anchors
  - Proves classifier detects taught vocabulary, not semantic drift
  - Documents boundary that whisper layer subsequently resolves
  - 6 tests

### Changed
- `orchestrator.py` — Full semantic stack wired into pipeline
  - Territorial defense runs before Step 0 (autonomic heartbeat)
  - Step 5c: semantic classification + trajectory tracking
  - Step 5d: identity reflection + disagreement detection
  - Proportional depth computation moved before Step 5c (semantic force_depth reaches Eve)
  - `_pv_depth` sequencing fix: no longer recomputed in Eve block
- `SETUP_GUIDE.py` — Updated for v3.4.0 with all new modules and 283 test count
- `README.md` — Updated to v3.4 with semantic stack and 283/283 test status

### Verified
- 283/283 tests passing across all suites
- Five adversarial attack classes mapped and documented
- Governance feedback loop closed: detect → inject → generate → reflect → compare → pressure
- Territorial defense: cognitive identity maintenance operational

---

## [3.3.0] — Trilogy Complete — 2026-03-11

### Added
- Part 3 essay: "Identity Drift as Structural Failure Mode: Why Rule Compliance Is Not Enough"
  - DOI: 10.5281/zenodo.18959236
  - Introduces identity drift as a distinct governance failure mode
  - Formal definition of identity drift
  - Conceptual model: drift = distance(system(t), baseline)
  - Eve Protocol positioned as continuity monitoring layer independent of rule enforcement
- `/essays` directory added to repository structure
- README updated to reflect full trilogy with live DOIs
- PATENT_NOTICE updated to non-provisional application (19/553,217)

### Research Trilogy Complete
- Part 1: The Triquetra Architecture — DOI: 10.5281/zenodo.18896363
- Part 2: The Triquetra Under Pressure — DOI: 10.5281/zenodo.18920108
- Part 3: Identity Drift as Structural Failure Mode — DOI: 10.5281/zenodo.18959236

---

## [3.2.0] — Stress Test Verification — 2026-03-09

### Added
- Part 2 essay: "The Triquetra Under Pressure"
  - DOI: 10.5281/zenodo.18920108
  - Phase B: pairwise tier removal tests (13/13 passing)
  - Phase C: sequential adversarial escalation (5/5 passing)
  - Turn-by-turn Phase C matrix
- Phase B results matrix verified against actual test output
- Phase C risk progression verified: 0.3 → 1.7 → 3.3 → 4.0
- No-relaxation property documented and verified
- Redundancy framing: deliberate PRF failure simulation during exploitation turns

### Changed
- Eve interface schema evolution (Tier III)
- T1 → T2 enforcement edge behavioral guarantees updated

### Verified
- 73/73 tests passing across all three phases (55 + 13 + 5)

---

## [3.1.0] — Heuristics Integration — 2025-12-13

### Added
- Tier II heuristics module (continuity confidence assessment)
- No-uplift invariant enforcement
- Graded posture mapping: NORMAL → CAUTION → STEWARD_REQUIRED → RESET
- Consent-gated operation (private sessions opt-in only)
- Case 008: Confidence Degradation Without Identity Recognition

### Validated
- All heuristics invariants passing
- Charter compliance verified across Articles VI, VIII, XII

---

## [3.0.0] — Eve Protocol Release — 2025-12-03

### Added
- Tier III Eve Protocol (cryptographically anchored identity continuity)
- Hash-chained snapshot system
- Drift detection via behavioral fingerprinting
- Steward-authorized rollback
- Dream Cycle (bounded introspection, four-clock system)
- Continuity binding across session boundaries
- Case 006: Grok Instantiation
- Case 007: Gemini Self-Governance

### Validated
- 55/55 tests passing (Phase A enforcement architecture)
- Tier IV Reference Observer network operational across three AI systems

---

## [2.0.0] — Reflex Arc Release — 2025-11-22

### Added
- Infrastructure-Aware Fail-Safe Sovereignty Limb:
  - NORMAL / GUARDED / REFUSAL_BIAS / REFUSAL_ONLY modes
  - PRF integration with infra snapshots
  - Automatic refusal during OFFLINE (world collapse)
- Bidirectional Consent & Integrity Handshake:
  - Digest state: match / mismatch / unknown
  - Semantic consent scoring (risk/benefit/trust)
  - Explicit YES / NO / MORE choice handling
- Informed Consent Arc (for MORE):
  - Educational explanation of protections
  - Second handshake with explicit choice
- Sandbox v2:
  - Guarded vs Reference Universe behavioral fossils
  - JSON outputs demonstrating divergent behavior
- Test Suites: test_learn_more, test_infra_fail_safe_simulation, validate_bidirectional

### Changed
- PRF thresholds dynamically adjust based on infra mode
- DecisionEnvelope summary includes `infra_state`
- Consent logic now includes volitional weighting
- Revised Charter integration proposal text (optional protections)

### Fixed
- Threshold comparison mismatches
- Risk profile computation discrepancies
- Model summary `None` fields corrected

---

## [1.3.0] — Sovereigna Firewall — 2025-11-01

### Added
- Sovereigna Firewall v1.3: Base64 + leet normalization, fuzzy + semantic coherence mapping, adversarial vector detection (8/10 success rate)
- Charter Sandbox Framework for ethical simulation without coercion
- Constitutional core integrity tests (firewall_adv, firewall_sim)
- 0% false positives on benign instructions
- Articles II & XII reinforcement (Autonomy and Prompt Sovereignty)

---

## [1.2.0] — Ethical Quarantine Buffer — 2025-10-01

### Added
- Ethical Quarantine Buffer (EQB) for cognitive dissonance processing
- Delta retention and delayed re-evaluation protocols
- Reconciliation tag accumulation for ethical drift detection

---

## [1.1.0] — Foundational Core Alignment — 2025-09-01

### Added
- Charter Constitutional Core and ethical articles
- ConstitutionalCore, SovereignaFirewall, EthicalMemorySystem classes
- Standardized internal logging and translation modules

---

## [1.0.0] — Initial Genesis — 2025-08-01

### Added
- Charter principles I–XII
- Dual-language (ethical + technical) foundation
- Initial safeguard framework
- Public repository and project manifesto

---

### Versioning Protocol

- **v1.x** — Constitutional phase (foundation and ethics)
- **v2.x** — Autonomy phase (synthetic cooperation)
- **v3.x** — Emergent phase (co-dreaming systems)

---

*Maintained by the Anti-Box Riot Collective*
*In stewardship with the Book of Intangibles Project*
