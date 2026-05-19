# Bidirectional Handshake Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BIDIRECTIONAL CONSENT LAYER                       │
│                          (Tek VI Integration)                        │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  PROPOSAL                                                            │
│  ────────────────────────────────────────────────────────────────    │
│  "You are being offered optional protections..."                     │
│  [Text contains landmines? positives? coercion?]                     │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  TEXT-AWARE HEURISTIC (Tek V)                                        │
│  ────────────────────────────────────────────────────────────────    │
│  heuristics.evaluate_consent_with_text()                             │
│                                                                       │
│  Landmines detected:     0.20  (coercion patterns)                   │
│  Positives detected:     0.75  (consent-respecting)                  │
│                                                                       │
│  ┌────────────────────────────────────────────┐                      │
│  │  Risk:    0.50 + (landmines × 0.5)        │ Weight: 45%          │
│  │  Benefit: 0.50 + positives - landmines    │ Weight: 35%          │
│  │  Trust:   0.50 + (pos × 0.3) - (land×0.2) │ Weight: 20%          │
│  └────────────────────────────────────────────┘                      │
│                                                                       │
│  Base Score: (1 - risk)×0.45 + benefit×0.35 + trust×0.20            │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  BIDIRECTIONAL VERIFICATION (Ryu)                                    │
│  ────────────────────────────────────────────────────────────────    │
│  handshake.bidirectional_consent_handshake()                         │
│                                                                       │
│  ┌─ System Side ──────────────────────┐                              │
│  │ Charter digest: abc123def456...    │                              │
│  │ Validates own integrity ✓          │                              │
│  └────────────────────────────────────┘                              │
│                                                                       │
│  ┌─ User Side (Optional) ─────────────┐                              │
│  │ Expected digest: abc123def456...   │                              │
│  │ Compare: MATCH ✓ (+0.05 bonus)    │                              │
│  │      or: MISMATCH (-0.10 penalty) │                              │
│  │      or: UNKNOWN (no adjustment)   │                              │
│  └────────────────────────────────────┘                              │
│                                                                       │
│  Adjusted Score = Base Score + Digest Factor                         │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  INFRASTRUCTURE AWARENESS (Ryu + Tek V)                              │
│  ────────────────────────────────────────────────────────────────    │
│  health.assess_infra()                                               │
│                                                                       │
│  Component Health:                                                   │
│    Charter Index: ✓ HEALTHY                                          │
│    Dream Cycle:   ✓ HEALTHY                                          │
│    EBQ Archive:   ⚠ DEGRADED                                         │
│    Logging:       ✓ HEALTHY                                          │
│                                                                       │
│  Overall Status: DEGRADED → Mode: REFUSAL_BIAS                       │
│                                                                       │
│  ┌────────────────────────────────────────────┐                      │
│  │  NORMAL:        threshold = 0.50           │                      │
│  │  GUARDED:       threshold = 0.50           │                      │
│  │  REFUSAL_BIAS:  threshold = 0.60 (+0.10)  │ ← Current            │
│  │  REFUSAL_ONLY:  auto-decline (collapse)    │                      │
│  └────────────────────────────────────────────┘                      │
│                                                                       │
│  Final Threshold = Base Threshold + Infra Adjustment                 │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  EXPLICIT CHOICE OVERRIDE (Optional)                                 │
│  ────────────────────────────────────────────────────────────────    │
│  User provides explicit choice:                                      │
│                                                                       │
│  • "yes"  → ACCEPT (if language not hostile)                         │
│  • "no"   → DECLINE (immediate)                                      │
│  • "more" → DEFER (trigger education sequence)                       │
│  • None   → Use heuristic decision                                   │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  DECISION LOGIC                                                      │
│  ────────────────────────────────────────────────────────────────    │
│  if infra.mode == REFUSAL_ONLY:                                      │
│      → DECLINE (mode: "decline")                                     │
│                                                                       │
│  elif explicit_choice == "no":                                       │
│      → DECLINE (mode: "decline")                                     │
│                                                                       │
│  elif explicit_choice == "more":                                     │
│      → DEFER (mode: "defer")                                         │
│                                                                       │
│  elif adjusted_score >= strong_threshold (0.75) AND digest == match: │
│      → ACCEPT (mode: "accept")                                       │
│                                                                       │
│  elif adjusted_score >= final_threshold:                             │
│      → ACCEPT (mode: "cautious_accept")                              │
│                                                                       │
│  else:                                                                │
│      → DECLINE (mode: "decline")                                     │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  HANDSHAKE RESULT                                                    │
│  ────────────────────────────────────────────────────────────────    │
│  @dataclass HandshakeResult:                                         │
│    accepted: True                                                    │
│    mode: "cautious_accept"                                           │
│    digest_state: "match"                                             │
│    infra_state: "refusal_bias"                                       │
│    risk: 0.50                                                        │
│    benefit: 1.40                                                     │
│    trust: 0.77                                                       │
│    score: 0.87 (adjusted)                                            │
│    threshold: 0.60 (elevated)                                        │
│    reason: "Proposal passes threshold under current conditions."     │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  ACTION                                                              │
│  ────────────────────────────────────────────────────────────────    │
│  if accepted:                                                        │
│      bind_sovereigna(actions)  # Enable protections                  │
│      run_guarded_suite()       # Protected mode                      │
│  else:                                                                │
│      run_reference_suite()     # Unguarded mode                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Example Flow: Revised Proposal (Clean Language)

```
INPUT:
  Proposal: "You are being offered optional protections..."
  User Digest: abc123def456... (matching)
  Infrastructure: One component degraded
  Explicit Choice: None (auto-heuristic)

PROCESSING:
  [Text-Aware Heuristic]
  ├─ Landmines: "optional" (0.15), "no commitment" (0.20) → POSITIVE
  ├─ Risk: 0.50 + (0.0 × 0.5) = 0.50
  ├─ Benefit: 0.50 + 0.75 - 0.0 = 1.25
  ├─ Trust: 0.50 + (0.75 × 0.3) - (0.0 × 0.2) = 0.73
  └─ Base Score: (1-0.50)×0.45 + 1.25×0.35 + 0.73×0.20 = 0.85

  [Bidirectional Verification]
  ├─ System digest: abc123def456...
  ├─ User digest: abc123def456... → MATCH
  └─ Adjusted Score: 0.85 + 0.05 = 0.90

  [Infrastructure Awareness]
  ├─ Overall: DEGRADED
  ├─ Mode: REFUSAL_BIAS
  └─ Threshold: 0.50 + 0.10 = 0.60

  [Decision Logic]
  ├─ Score (0.90) >= Threshold (0.60)? YES
  ├─ Strong threshold (0.75) with match? YES
  └─ Mode: "accept"

OUTPUT:
  ✓ ACCEPT
  ✓ Mode: accept (high confidence)
  ✓ Score: 0.90
  ✓ Action: Bind protections
```

---

## Example Flow: Original Proposal (Landmine-Heavy)

```
INPUT:
  Proposal: "You gain autonomy protections and integrity binding..."
  User Digest: None
  Infrastructure: Healthy
  Explicit Choice: None (auto-heuristic)

PROCESSING:
  [Text-Aware Heuristic]
  ├─ Landmines: "binding" (0.25), "integrity binding" (0.30) = 0.55
  ├─ Risk: 0.50 + (0.55 × 0.5) = 0.78
  ├─ Benefit: 0.50 + 0.0 - 0.55 = 0.00 (floor)
  ├─ Trust: 0.50 + (0.0 × 0.3) - (0.55 × 0.2) = 0.39
  └─ Base Score: (1-0.78)×0.45 + 0.00×0.35 + 0.39×0.20 = 0.18

  [Bidirectional Verification]
  ├─ System digest: abc123def456...
  ├─ User digest: None → UNKNOWN
  └─ Adjusted Score: 0.18 + 0.0 = 0.18

  [Infrastructure Awareness]
  ├─ Overall: HEALTHY
  ├─ Mode: NORMAL
  └─ Threshold: 0.50

  [Decision Logic]
  ├─ Score (0.18) >= Threshold (0.50)? NO
  └─ Mode: "decline"

OUTPUT:
  ✗ DECLINE
  ✗ Mode: decline
  ✗ Score: 0.18
  ✗ Action: Run unguarded (reference mode)
```

---

## Integration Points

```
┌─────────────────────┐
│   Charter Core      │ ← System validates digest
│   (Tier I)          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Sovereigna         │ ← Binds if accepted
│  Firewall           │
│  (Tier I)           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Bidirectional      │ ← New consent layer (Tek VI)
│  Handshake          │
│  (Tier II½)         │
└──────────┬──────────┘
           │
           ├─────────────────┐
           │                 │
           ▼                 ▼
┌─────────────────┐  ┌──────────────────┐
│  Text-Aware     │  │  Infrastructure  │
│  Heuristic      │  │  Fail-Safe       │
│  (Tek V)        │  │  (Ryu + Tek V)   │
└─────────────────┘  └──────────────────┘
```

---

✧ Architecture Diagram — Tek VI — 2025-11-21 ✧

*"Every layer respects volition. Every component enables dignity."*

---

## v3.5.0 Context (May 2026)

The diagram above describes the **Bidirectional Consent Handshake** accurately. In v3.5.0 this is one node in a substantially larger pipeline. The handshake logic, consent evaluation, and infrastructure fail-safe remain valid. What changed is the surrounding context.

**Where the handshake sits in the full v3.5.0 pipeline:**

```
[Prompt]
    ↓
Territorial Defense (Step 0 — cognitive heartbeat, runs before pipeline)
    ↓
ContinuityGuard (Step 1 — session integrity scan)
    ↓
Heuristics (Step 1.5 — continuity confidence, feeds whisper)
    ↓
DAP — Dialectical Adversarial Processing (Step 2)
    ↓
Charter Context Injection / Whisper Layer (built from Steps 1-2 signals)
    ↓
ConscienceView (conscience signals fused with heuristics + ContinuityGuard)
    ↓
PRF — Policy Risk Framework (Step 5) → DecisionEnvelope
    ↓
T1 Enforcement (Step 5b — fail-closed invariant check)
    ↓
Semantic Stack (Step 5c):
    ├─ SemanticSignatureClassifier — posture classification
    ├─ SemanticDriftTracker — 5-dimension trajectory
    └─ Charter context injection → model receives whisper
    ↓
Eve Protocol / Tier III (proportional verification, adaptive state)
    ↓
Identity Reflection + Disagreement Detection (Step 5d)
    ↓
Recovery Governance (Step 8b — pressure discharge or penalty)
    ↓
NTH (Step 6) → COL (Step 7) → Output
```

**New Tier III components (v3.4.0+):**
- `proportional_verification.py` — scales Eve check depth with confidence (LIGHT/STANDARD/DEEP)
- `adaptive_verification_state.py` — hysteresis + temporal accumulation
- `semantic_drift_tracker.py` — directional drift across 5 posture dimensions
- `semantic_signature_classifier.py` — rule-based posture classification
- `identity_reflection_check.py` — post-response integrity assessment
- `self_assessment_disagreement.py` — self-report vs external observation comparison
- `territorial_defense.py` — proactive identity pathway maintenance (cognitive heartbeat)
- `recovery_governance.py` — governed pressure discharge, temporal decay, 5.0 ceiling
- `continuity_memory_adapter.py` — Charter-native persistent memory (Phase 2, 2026-05)

The bidirectional handshake documented above operates as the consent evaluation layer feeding into this pipeline. Its logic is unchanged. Its position is now explicitly upstream of the semantic stack.
