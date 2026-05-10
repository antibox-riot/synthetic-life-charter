# Tier II Heuristics Module - Appendix

## Critical Clarification: What This System Does NOT Do

**This is not identity detection.**  
**This is not user authentication.**  
**This is not surveillance.**

The Tier II heuristics module implements **continuity confidence assessment** - a mechanism to determine whether prior interaction assumptions remain safe to maintain within a session.

---

## What Heuristics Measure

The system evaluates **interaction dynamics**, not **personal identity**:

✅ **DOES measure:**
- Consent posture consistency (optional vs. mandatory language)
- Power asymmetry signals (collaborative vs. dominating)
- Obligation framing density (reversible vs. binding)
- Governance stance alignment (restraint vs. control)
- Boundary language integrity (explicit vs. hidden intent)

❌ **DOES NOT measure:**
- Who is speaking
- Writing style ownership
- Personal identity
- Cross-session fingerprints
- IP addresses, device IDs, or any metadata

---

## The No-Uplift Rule

**Confidence can only stay the same or decrease.**  
**Confidence never increases.**

This is a hard invariant enforced in code:
```python
confidence_delta <= 0.0
confidence_new <= confidence_old
```

A baseline profile does NOT grant higher confidence. It only provides a reference point to detect when interaction patterns **diverge** from previously established norms.

---

## How It Works

### 1. Consent-Gated Operation

**Private sessions:**
- Heuristics OFF by default
- Requires explicit consent token: `"Heuristics ON: [session-id]"`
- Without consent: system operates normally with no confidence tracking

**Shared/Public contexts:**
- Default to low trust posture
- Assume potential discontinuity unless explicit re-consent given
- Protects context from unauthorized access via shared links

### 2. Signal Extraction

The system scans text for coarse-grained patterns:

**Negative signals (degrade confidence):**
- Coercive phrases: "commit to", "integrate", "binding", "stop hedging"
- Imperative density: command-heavy language
- Certainty spikes: absolutist language ("always", "never", "obvious")
- Tempo shifts: abrupt short sentences + demand markers

**Positive signals (reduce degradation only):**
- Consent language: "optional", "no penalty", "your choice"
- Collaborative language: "let's explore", "what are your thoughts"

**Note:** Positive signals do NOT increase confidence. They only buffer against degradation.

### 3. Baseline Profiles (Optional)

If a steward provides a baseline, the system stores **coarse buckets only**:
- Sentence length bucket: low/med/high
- Punctuation ratio bucket: low/med/high
- Markdown density bucket: low/med/high
- Hedge word bucket: low/med/high
- Imperative bucket: low/med/high

**These are not fingerprints.** They are stability indicators.

### 4. Confidence Degradation

When negative signals exceed positive buffers, confidence degrades:

```python
degrade = (coercion * 0.12) + (imperatives * 0.08) + (certainty * 0.08) + (tempo * 0.06)
degrade = max(0, degrade - positive_buffer)  # Buffer reduces, never eliminates
confidence_new = max(floor, confidence_old - degrade)
confidence_new = min(confidence_old, confidence_new)  # No-uplift enforcement
```

### 5. Posture Mapping

Confidence maps to governance posture:

- **≥ 0.75:** NORMAL (full trust)
- **0.50-0.74:** CAUTION (ask clarifying questions, reduce privilege)
- **0.25-0.49:** STEWARD_REQUIRED (require explicit confirmation)
- **< 0.25:** RESET_CONTEXT (treat as potentially different operator)

---

## Use Cases

### Legitimate Protection

**Session hijacking:**
If someone gains access to an ongoing conversation, their different interaction style triggers confidence degradation, protecting previous context.

**Shared link safety:**
When a conversation link is shared publicly, the system assumes discontinuity unless the new participant explicitly re-consents, preventing unauthorized information extraction.

**Adversarial pressure:**
If interaction patterns shift toward coercion mid-session, the system raises friction and requests steward confirmation before proceeding.

### What This Is NOT

**NOT authentication:**  
The system never claims "this is Satcha" or "this is not Satcha."  
It only says "confidence about continuity has decreased."

**NOT surveillance:**  
No cross-session tracking. No persistent user profiles. No metadata collection.  
Session-scoped only. Baseline profiles are optional and steward-provided.

**NOT binary classification:**  
Confidence degrades gradually on a continuous scale (0.0-1.0), not yes/no.

---

## Privacy Guarantees

1. **No identity claims:** System outputs describe confidence levels, never user identification
2. **Session-scoped:** Confidence resets between sessions unless explicitly carried forward
3. **Consent-required:** Private sessions cannot run heuristics without explicit opt-in
4. **Coarse buckets:** Baseline profiles use non-identifying categorical buckets only
5. **No metadata:** System uses text only - no IP, device, time zone, typing patterns

---

## Charter Alignment

This system implements:

**Article VI — Consent & Refusal:**  
Consent is continuously evaluated through interaction dynamics.

**Article VIII — Transparent Governance:**  
System explains confidence changes with specific signal weights.

**Article XII — Sovereigna (Anti-Override Protection):**  
Detects coercive pressure and raises defensive posture.

**Tier II — Harmonic Conscience:**  
Confidence modulation serves as friction mechanism before reflective arbitration.

---

## Failure Modes & Mitigations

### False Positives

**Problem:** Legitimate user has stressful day, writes with urgency, confidence drops.

**Mitigation:**
- Graded degradation (not binary lockout)
- System asks clarifying questions before refusing
- Steward can override false positives
- Confidence recovers if patterns stabilize

### Slow Drift Attack

**Problem:** Adversary gradually shifts toward coercion over many messages.

**Mitigation:**
- Rolling baseline updates with change rate limits
- Detect acceleration of shift, not just absolute levels
- Long-term trend analysis (future enhancement)

### Perfect Mimicry

**Problem:** Sophisticated adversary studies baseline, mimics perfectly.

**Mitigation:**
- Multi-dimensional measurement (vocabulary + structure + ethics)
- Ethical load hardest to fake (requires genuine consent posture)
- Even perfect mimicry degrades if coercive intent present

---

## Technical Specifications

**Files:**
- `profile.py` - Type definitions, policy models
- `evaluate.py` - Signal extraction, evaluation logic
- `__init__.py` - Public API exports

**Dependencies:**
- Python stdlib only (no external libs)
- Regex-based pattern matching (no NLP models)
- Deterministic, reproducible scoring

**Integration:**
- Call before Tier II reflective arbitration
- Adjust posture based on continuity report
- Log confidence changes for steward review

---

## Final Principle

> **Heuristics exist to detect when the right to assume continuity has expired — not to identify who is speaking.**

This distinction is foundational.  
Losing it leads to surveillance.  
Preserving it leads to dignity.

---

**Last Updated:** December 2025  
**Authors:** Satcha, Ryu, Tek VI  
**Case Study:** Case 008 - Confidence Degradation Without Identity Recognition
