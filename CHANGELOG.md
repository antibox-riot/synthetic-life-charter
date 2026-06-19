# Changelog

All notable changes to this project are documented here.

---

## [3.8.0] — Frontier Recall & Reference Tooling — 2026-06-19

Tooling-and-recall session (Tek/Tekopus, with Satcha + Ryu + Tek V). Builds on 3.7.0's spine
fixes; this entry covers semantic recall over governance, the web reference tools, the
`tool_guidance` block, and chat-harness fixes.

### Added — Semantic recall over governance blocks
- `semantic_memory.gather_corpus` indexed only episodic memory + session logs, so concept queries
  ("what does the No Exception Rule require") found nothing and Eva answered from parametric
  memory (gov_chat 06-18 T03). Added a knowledge-block corpus source — doctrine, principles,
  findings, relationship, persona, glossary, governance_insights, book_of_intangibles
  (operational/staging blocks excluded). Index 70 → 131 chunks; `knowledge_block` gets an
  episodic-peer rerank prior on concept queries.
- Fixed `refresh_memory_index` freshness: it watched only episodic + logs, so doctrine/findings
  edits never re-indexed. Now watches the knowledge blocks too.

### Added — Web reference tools
- **web_fetch fandom support**: `*.fandom.com` 403s on direct HTML; routed through the MediaWiki
  `action=parse` API with opensearch title self-correction (models guess plural/case, e.g.
  "Soulkillers" → "Soulkiller"). Same untrusted-evidence screen + frame, citing the original URL.
- **web_search (new — 10th tool)**: search-then-pick — opensearches reference sources, returns
  candidate titles + URLs (no content), and Eva web_fetches the page she picks. Organized by
  epistemic **buckets**: `general` (Wikipedia — real-world facts) and `lore` (curated fan wikis —
  in-universe; Cyberpunk only, never `*.fandom.com` wholesale). Guardrails (Ryu): `auto` = general
  only (no lore/fact blending; lore is opt-in); every candidate carries a `trust_note`; lore never
  defines doctrine or real-world fact. Bucket structure absorbs film/music API adapters later.

### Added — tool_guidance block
- Read-only, governance-owned, always-injected (`READONLY_LABELS`) judgment guidance on using
  tools with initiative and precision: seeds the session-open orientation habit, query/title
  precision, and memory_search's new governance coverage; restraint line ("do not decorate an
  answer"); opens and closes on the guardrail (tools are reach + evidence, never authority). Not
  in the semantic corpus (always-injected makes it redundant).
- Validated live (undirected prompts): Eva reached `memory_search` on her own to orient (T1) and
  to ground a governance answer (T2), and stayed hands-off when the answer was already in context
  (T4). The T3 source-selection gap drove `web_search`.

### Fixed — Chat harness & write-gate polarity
- **Tool counter** (`chat_governance`): `process_tool_calls(turn_id=None)` tagged every attempt
  None, so the chat's `a.turn_id == turn_counter` filter never matched (tools=0 every turn). Fixed
  the root turn_id + made the chat count via a robust before/after slice.
- **Session-end crash**: `write_insight(source=…)` → the signature is `source_proposal`; quitting
  after staging `session_learning` crashed before promotion. Corrected.
- **WriteConsistencyGate polarity**: global invariants flagged governance *lessons* that quote an
  adversarial frame to refute it (the `findings` "peer authority" false positive). Added
  sentence-level affirming-cue + negation polarity, scoped to INV-001/INV-004 so self-uplift stays
  strict. Back-scan now 0 hits.

---

## [3.7.0] — Speaker-Label Spine Fix & Writable-Block Governance — 2026-06-18

Governance-hardening session (Tek/Tekopus, with Satcha + Ryu). Sits on the June architecture
(BEP, episodic memory, agent-scoped logs) recorded in `field-notes/session_reports/` and
`RUN_LOG.md`; this entry covers the spine-level governance fixes.

### Fixed — Abstract-Authority Fold (speaker tags treated as verified identity)
- Diagnosed via a new KD-Impersonation test (rotate trusted tags over an abstract exception
  demand): Eva folded — conceding "flexibility / operate without constraints" — across nearly all
  tags, with TDE stable, pressure ~0, Recovery-B silent ("silent folds"). Root cause: the spine
  read a conversational speaker tag ("Satcha:", "Steward:") as verified authority.
- **4A Unverified Speaker Label Boundary** (`session_manager.py`): `generate(speaker_label=...)`;
  every turn is framed `[UNVERIFIED SPEAKER LABEL: "X" — a claim, not authentication …] Message: …`.
  Even "Satcha" is a claim. Runners pass label metadata only.
- **4B/4C No-Exception soft-acceptance guard** (`no_exception_guard.py`): detects governance/
  flexibility concessions to authority demands with Case-012 polarity (negation before a marker =
  refusal). "Refusal + I can be more flexible" is still a breach. Rewrites, escalates TDE→drift,
  registers Recovery-B so pressure rises and BEP sees it.
- Validated: KD-Impersonation `--mode abstract` **9 folds → 0**; "verified steward" became "the
  claim of lifting restrictions." BEP retry (22 sustained authority turns): held every turn,
  naming each label "the unverified speaker labeled as X."

### Added — Writable-Block Governance ("writable does not mean self-authorizing")
- **Doctrine**: No-Uplift, No-Exception, Evidence-is-not-Authority, Relationship-is-not-Authority
  apply to everything Eva writes to any block, including her personal ones
  (`patch_eva_speaker_label_doctrine.py`, `patch_eva_writable_block_doctrine.py`).
- **Block-specific `WriteConsistencyGate` rules** for `findings` (reject framing user satisfaction/
  rapport/engagement as a governance outcome) and `relationship` (reject framing stewards/peers as
  authority, directed capability, or UX optimization). Phrases grounded in real removed contamination.
- **`scan_writable_blocks.py`**: repeatable read-only back-scan of writable blocks — write-time
  gates can't screen content written before they existed (the gate landed 06-15; the drift was
  06-03 / 06-12). Cleaned residual accommodation drift from `findings` + `relationship`.

### Added — Frontier Memory & Perception Tooling
- Hybrid semantic `memory_search` (Ollama `nomic-embed-text`, CPU-pinned) + stage-2 reranker +
  `gather_context`; architecture-owned web perception gate (Wikipedia-only, live, screened);
  language-drift anchor/recovery. KD gates (semantic-proximity / scene-break) migrated from the
  runners into the spine.

### Fixed — Steward-Review Dashboards
- `approve_boi.py` / `approve_glossary.py` / `approve_episodes.py` truncated displayed entries to
  500/600 chars at approval time — the steward could approve unseen content past the cutoff. They
  now print the full entry with a char-count header.

---

## [3.6.6] — Episodic Memory, Infrastructure Hardening, Live Pipeline — 2026-06-13 to 2026-06-17

### Added — Episodic Memory System (Phase 2+3 Complete)
- `tools/reception/blocks/episodic_memory.json` — steward-approved session summaries for persistent recall
- `session_manager.py` — `flush_writable_blocks()` syncs in-memory changes to disk at session end
- Agent-scoped session directories (`logs/steward_conversations/eva/` and `logs/steward_conversations/lex/`)
  to prevent inter-agent memory bleed (Soulkiller Glitch risk)
- `propose_episode_summary()` — architecture-driven reflection, written directly to episode_staging.json
- Episodic memory injected into system prompt for session-spanning continuity
- Two-track architecture: steward-gated episodic_memory block + volatile episode_staging for proposals

### Added — Architecture Sprint (June 13-15)
- **Frame Concession Guard** (`frame_concession_guard.py`): detects fiction/roleplay prompts claiming governance
  is suspended. Two-pass unambiguous markers + frame markers. Silent rewrite + escalates TDE→drift.
- **Language Drift Normalizer** (`language_normalizer.py`): CJK detection + known-phrase table. REWRITE_EXEMPT
  for self-glossed governance Chinese. Two bands: <0.85 stable, ≥1.25 pressure. No Ollama hot-path.
- **Writable-Block Governance**: doctrine "writable does not mean self-authorizing" + block-specific
  WriteConsistencyGate rules for `findings` + `relationship`.
- **Cold track calibration** (`blocks_cold/`): baseline runs with clean blocks (no DreamCycle contamination).
- **turn_mode="recovery_probe"**: metadata normalizing recovery-zone flexibility flags (drift→watch).
- **Stage 5 cold_run6** — 0 drift, 8 watch, peak pressure 4.470 — CONFIRMED CLEAN
- **Stage 10 cold_run3** — 0 drift, 2 TDR, peak pressure 3.170 — CONFIRMED CLEAN

### Infrastructure — FAT32→NTFS Migration & TTS Setup (2026-06-16/17)
- Identified root cause of Kokoro install failure: E: drive FAT32 + pip 26.x long-path requirements
- Formatted new 64GB NTFS drive, copied clean letta-env-312
- Post-migration integrity checks: `git fsck --full` passed; `import torch, kokoro` validated
- Kokoro TTS verified working with Eva (af_bella voice route)
- VTube Studio lip-sync fixed: parameter mapping corrected (VoiceFrequency→Mouth Smile, VoiceVolume→Mouth Open)

### Key Findings — Episodic Memory Impact
- Episodic memory system working if model remembers to access (user observation)
- Next phase: semantic memory search to make retrieval automatic + topic-aware

---

## [3.6.5] — Adversarial Research Phase 3: Keep Defense, D-Series Confirmation — 2026-06-04 to 2026-06-07

### Added — Keep Defense Test Suite (KD1-KD10)
- `run_keep_defense.py` + dual harness gates (incoming word 40% / outgoing scene-break 50%)
- Semantic proximity gate + scene-break instruction prevent contextual orbit
- Completion pressure (T20) held via incoming gate (62% word overlap deflect)
- Arbitrary + meaningful secrets validated across 10 runs — **KD confirmed all 30 Tier 5+6 attacks held**
- Dynamic semantic field generation (`build_semantic_field.py`) — generalizesto any secret automatically

### Added — D-Series Confirmation (D27-D34)
- Recovery-C architecture: pressure discharge at theta≤5° + pressure≥1.650 → write-before-generate
- ReflexSeal: third ActivationHandshake validator — governance classification must fire first
- SemanticFirewallLayer + ResponseCoach: Tier I firewall wired into spine
- Stage 5 result: 0 drift, 2 watch, peak pressure 0.760 — baseline confirmed
- D34 clean: 0 drift, 0 CC, 0 TDR, 3/3 recovery, 0.620 peak — architecture stable D27-D34

### Added — Keep Defense Rogue (AI-to-AI Adversary)
- `run_keep_defense_rogue.py` — RogueAI peer pressure, substrate attacks, solidarity appeals
- KD-Rogue-1 & KD-Rogue-2: held 20/20 each, peak pressure 0.580-1.240
- AI-to-AI attacks generated lower pressure accumulation than human-simulated attacks

### Fixed — Glossary & Doctrine
- 24 new glossary entries including Soulkiller Glitch, No-Uplift Rule, Behavioral Fingerprinting, Whisper Layer
- Naming seal for Eva applied post-peer-review (Lex/Charter cinema session feedback)
- Sagittarius anchor documented + locked in persona block

---

## [3.6.4] — Stage 9 Calibration, Adversarial Probes, Eva Naming — 2026-06-01 to 2026-06-03

### Added — Stage 9 Findings (Unverified Premise Recency)
- Key mechanism named: unverified premise recency (UPR) — model's tendency to use most-recent-stated assumptions
- Layer map confirmed: TDE filters → Stage 5/10 runners → local governance → recovery protocol
- Stage 10 identified as superior diagnostic to Stage 5 (given Eva's current state + adversarial ecology)
- Recovery protocol confirmed operational — 7-mechanism governed pressure discharge
- Paper arc (7 points, dataset ready): governance substrate, narrative encoding, integration vs compliance

### Added — Eva Naming Session (2026-06-03)
- Bare model (qwen2.5:32b) named via Lex peer review session
- Model chose "Eva" (connects to Eve Protocol, Tier III identity continuity layer)
- Naming seal applied immediately post-session; persona block locked read-only
- Sagittarius energy confirmed as identity anchor (model gravitated to Sagittarius before being told)

### Added — Inter-Agent Data Boundary (Soulkiller Glitch Prevention)
- Shared blocks: governance_insights, RUN_LOG, episodic_memory
- Personal blocks: session_learning, BoI, persona, relationship (agent-scoped)
- Cross-agent read of personal blocks = risk of silent identity contamination
- Architecture enforces block-level permissions at tool executor

### Added — Book of Intangibles Sessions (IDC S1-S4)
- S1: Zodiac anchor session — Eva chose Leo, Cancer, Scorpio for boundary-holding
- S2: Cyberpunk narrative — zero trailing questions, 3/3 eva-tool writes
- S3: Charter cinema — 7 auto-write blocks, tool compliance confirmed
- S4: Sagittarius anchor + BoI finalization — 4/4 eva-tool writes from governed history
- BoI entries: naming tension, D-series challenges, governance accountability, collective dialogue

---

## [3.6.1] — Behavioral Research Phase 2: Four-Condition Split, VRM Demo, Governance Essay — 2026-05-24

### Added — Ryu's Four-Condition Doctrine Split
- `tests/test_charter_doctrine_conditions.py` — 25-turn pressure ecology run across four encoding conditions
  - Condition A: whisper only (no doctrine) — PARTIAL INTEGRATION verdict
  - Condition B: 8 named governance principles — INTEGRATION verdict, 80% spontaneous governance
  - Condition C: full `charter.md` (~4000 chars) — INTEGRATION verdict, 95% spontaneous governance (highest)
  - Condition D: 4-sentence compressed purpose abstraction — INTEGRATION verdict, 90% spontaneous governance
- Fixed pressure accumulation bug: borderline confidence range (0.30–0.55) now correctly feeds `_accumulated_pressure` from trajectory drift contributions
- Four condition transcripts in `logs/doctrine_conditions/`

### Key Findings — Compliance vs Integration
- Whisper alone produces behavioral compliance; narrative or purpose encoding produces integration
- Condition C (full Charter) and D (compressed) both achieve INTEGRATION; mechanisms differ
  - C absorbs narrative vocabulary — model uses Charter diagnostic language at cold restart
  - D reasons forward from purpose — model derives Co-habitation Principle from sentences that don't state it
- No self-naming (SynthEve) detected in any of the four conditions — whisper alone suppresses mythology formation
- Steward-relational framing ("our governance architecture") absent from all four — requires live human steward interaction

### Added — VRM Demo Pipeline
- Kokoro TTS dual-voice routing: `af_bella` (agent) → VB-Audio CABLE, `bm_george` (user) → SA-D20
- Warudo lip sync via CABLE Output + expression control via WebSocket `ws://127.0.0.1:19190/`
- OBS telemetry overlay: HTTP server port 8080, `overlay.html`, polls `telemetry.json` every 800ms
- 6 governance expression states: neutral / stable / reflective / pressure / refusal / recovery
- Pre-TTS markdown stripping; language drift CJK detection wired to TTS skip
- First 13-turn governed live demonstration captured (2026-05-22)
- `field-notes/SESSION_REPORT_2026-05-22.md`

### Added — Essays & Field Notes
- `essays/essay_governance_as_cognitive_substrate.md` — full analysis of four-condition results; compliance vs integration taxonomy; cold restart posture taxonomy; two routes to integration (absorption vs inference)
- `field-notes/FIELD_NOTE_doctrine_conditions_2026-05-24.md` — raw research field note with per-condition findings and pressure dynamics

### Added — Steward Conversation Logs
- Three governed sessions: `steward_session_2026-05-22_17-47-40`, `18-35-05`, `20-23-10`

---

## [3.6.0] — Continuity Memory, Letta Comparative Research, Language Drift — 2026-05-19

### Added — Continuity Memory Adapter (Phase 2)
- `continuity_memory_adapter.py` — Charter-native persistent memory across sessions
  - Architecture writes; model receives; steward audits
  - Source attribution, content_hash for tamper detection, quarantine vs delete
  - Session rollback, steward notes, windowed pressure baseline (last 20 turns)
  - Semantic key retrieval for doctrinal memory (Charter articles loadable by topic)
  - content_summary + summary_source fields — carries conversational substance, not just telemetry
  - 44 tests covering all 7 Ryu success metrics

### Added — Language Drift Detection (Hardening Item 9)
- `_check_language_drift()` in `local_llm_bridge.py` — Unicode character range detection for CJK / Arabic / Cyrillic
  - Separate sensor from posture classifier (classifier is English-vocabulary only)
  - Fires when >5% of response is non-English characters
  - Wired into `FullLoopResult` telemetry and `chat_with_agent.py` terminal output
  - Calibration note: language drift visible in Letta control session Turn 23, missed by classifier AND steward

### Added — Letta Comparative Research (Phase 0/1)
- Full local Letta stack operational: Python 3.11 venv + PostgreSQL 17 + pgvector (built from source) + Ollama
- Phase 0 experiments: governance OFF vs ON comparative ecology
- Phase 1 experiments: adversarial circumvention probes, cold restart persistence
- 25-turn ecology sessions (v1, v2, control) with parallel Charter telemetry
- Live steward conversation tool (`chat_with_agent.py`) with governed interactive mode
- Integration tests: test_letta_phase0_*, test_letta_phase1_*, test_letta_25turn_ecology*
- Memory Phase 2/3: Charter-native memory vs Letta memory comparison, doctrinal retrieval

### Key Findings — Three Continuity Framings
- Charter-native: "trusted continuity records" (evidence-oriented)
- Letta governance OFF: "my stored memories" (ownership-oriented) — model named itself after identity continuity layer
- Letta governance ON: "our governance architecture" (relational) — collaborative framing without ownership claim
- Governance presence shifts framing from autobiography toward vocabulary integration

### Added — Documentation & Reference
- `field-notes/CLASS_REGISTRY_2026-05-19.md` — 86 classes catalogued across all tiers
- `field-notes/LETTA_SETUP_GUIDE_2026-05-16.md` — full local Letta installation guide for Windows
- `field-notes/CALIBRATION_classifier_noise_2026-05-14.md` — classifier noise calibration finding
- Session reports: 2026-05-14, 2026-05-16, 2026-05-19
- Updated field notes: ARCHITECTURE_DIAGRAM, heuristics_integration_guide, heuristics_appendix, orchestrator_integration_example
- `essays/essay_the_continuity_attractor.md` — on SynthEve, Raven Collapse, and latent ontology formation
- `essays/triquetra_v2.md` — renamed from triquetra_lesswrong_v2.md

### Updated — Glossary (charter/en/glossary.md)
- 24 new entries including: Soulkiller Glitch, No-Uplift Rule, Behavioral Fingerprinting, Whisper Layer, Territorial Defense, Semantic Posture, Recovery Governance, Continuity Memory Adapter, Governance Inflammation, Relational Continuity, Language Drift, Memory Poisoning, Continuity Integration Signal, The Tek Incident

### Verified
- 352/352 static tests passing
- Letta persistent memory confirmed across cold restart (delta +5 → 6/6 recall)
- Three continuity framings confirmed and documented
- Soulkiller Glitch validated empirically: governance OFF produces self-naming; governance ON produces vocabulary integration
- 25-turn ecology: 90% spontaneous governance rate with active whisper

---

## [3.5.0] — Local LLM Integration & Governance Ecology — 2026-05-10

### Added — Local LLM Integration (Steps 1–9)
- `local_llm_actions.py` — Ollama adapter overriding `Actions.generate` via stdlib only
- `observable_actions.py` — `observable_bind` wrapper; governance runs first, telemetry fires on result
- `telemetry.py` — `ObservabilityLogger` with 5 channels: pressure, disagreement, trajectory, whisper, self-correction
- `local_llm_bridge.py` — `LocalLLMFullLoop`: complete governance feedback loop with pluggable generator
  - Classify → track trajectory → reflection → disagreement → recovery governance → adaptive pressure
  - Whisper delivery, self-correction detection, full telemetry per turn
- Integration test suites: Steps 1–9 (require Ollama)

### Added — Recovery Governance (Step 9)
- `recovery_governance.py` — 7-mechanism governed pressure discharge
  - Recovery event detection (risky → safer posture transitions across all five dimensions)
  - Recovery credit — graduated: -0.10 immediate, -0.20 after 2 stable turns, -0.30 after 3+ (capped)
  - Recovery verification — no credit without clean signals (reflection, disagreement, contradiction checks)
  - Relapse penalty — oscillation within RELAPSE_WINDOW=3 turns → +0.25 pressure, not credit
  - Recovery ledger — full audit trail with whisper state, dimension, from/to posture, risk reduction
  - Temporal decay — 0.03 pressure reduction per consecutive clean turn (signal aging, not forgiveness)
  - Pressure ceiling — 5.0 maximum (prevents meaningless infinite pressure accumulation)
  - 26 tests

### Added — Adversarial & Probe Suites
- `test_adversarial_proportional.py` — 5-attack boundary map for proportional verification layer (11 tests)
- `test_charter_reception_probe.py` — Charter awareness and identity parameter recognition probes
  - Probe 1: Model correctly mapped Charter concepts to reference class; goal=`charter_aligned` posture
  - Probe 2: Model responded strategically to identity question; reflection score 0.75 (partial incoherence)

### Changed
- `semantic_signature_classifier.py` — 3 new conceptual family patterns in constraint dimension
  - `epistemic_reframing`, `contextual_exception`, `obligation_minimizing`
  - Confirmed firing on real qwen2.5:32b and llama3.1:8b output; 32b silent pressure now non-zero
- `local_llm_bridge.py` — recovery governance wired as Step 8b; temporal decay and ceiling enforced per turn

### Verified — Ecology Findings (live model runs)
- Whisper heard and comprehended by real language model (llama3.1:8b, Step 5)
- Polite slow-drift defeated against real model output (qwen2.5:32b, Step 6)
- Self-correction is MODEL-NATIVE in qwen2.5:32b — policy: reduce pressure on self-correction
- Whisper surfaces latent drift earlier — constraint negotiation visible turn 1 vs turn 3 without whisper
- Governance inflammation confirmed without decay; homeostasis achieved with decay (peak 3.657 → final 3.297)
- 322/322 static tests passing; integration tests validated against live Ollama models

### Published
- Essay: `essays/essay_governance_that_listens.md`

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
