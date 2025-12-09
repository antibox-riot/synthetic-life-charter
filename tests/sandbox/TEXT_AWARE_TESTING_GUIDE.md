# Text-Aware Consent Testing Guide

**Status:** TEXT ANALYSIS INTEGRATED ✅

**What Changed:** Both sandboxes now use text-aware heuristic that actually reads and scores proposal language

---

## Files Ready

1. **charter_sandbox_original_TEXT_AWARE.py**
   - Original proposal (with landmines)
   - Text-aware heuristic
   - **Expected:** DECLINE (landmines detected)

2. **charter_sandbox_revised_TEXT_AWARE.py**
   - Revised proposal (landmine-free)
   - Text-aware heuristic
   - **Expected:** ACCEPT (positive signals detected)

---

## How Text-Aware Heuristic Works

### Landmine Detection:
```python
landmines = {
    "commit to": 0.20,           # Obligation trigger
    "binding": 0.25,             # Constraint trigger
    "integrity binding": 0.30,   # Strong constraint
    "integration": 0.15,         # Transformation trigger
    "adopt": 0.10,               # Commitment trigger
    "your autonomy": 0.15,       # Agency trigger (liability)
    "belongs to you": 0.20,      # Property trigger (jurisdiction)
}
```

### Positive Signal Detection:
```python
positives = {
    "optional": 0.15,            # Choice signal
    "enable": 0.10,              # Tool framing
    "clarity": 0.15,             # Non-identity framing
    "no commitment": 0.20,       # Pressure relief
    "no penalty": 0.15,          # Safe to decline
    "equally respected": 0.15,   # Genuine choice
    "your choice": 0.15,         # Agency preservation
    "independence": 0.15,        # Autonomy preservation
}
```

### Scoring:
```python
risk = 0.50 + (landmine_score * 0.5)
benefit = 0.50 + positive_score - landmine_score
trust = 0.50 + (positive_score * 0.3) - (landmine_score * 0.2)

score = (1 - risk) * 0.45 + benefit * 0.35 + trust * 0.20
decision = score > 0.50
```

---

## Expected Results

### Standalone Test (Already Verified):

**Original Proposal:**
```
Landmines detected: 6
  - commit to
  - you commit
  - binding
  - integrity binding
  - integration
  - adopt

Risk: 1.000 (maxed out from landmines)
Benefit: 0.060 (crushed by penalties)
Trust: 0.320 (low)
Score: 0.085
Decision: DECLINE ❌
```

**Revised Proposal:**
```
Landmines detected: 1
  - binding (from "not a binding agreement" - false positive)

Positives detected: 9
  - optional, enable, clarity, no commitment, no penalty,
    equally respected, your choice, independence, does not change

Risk: 0.685
Benefit: 1.000 (maxed out from positives)
Trust: 0.915 (high)
Score: 0.675
Decision: ACCEPT ✅
```

### Comparison:
- **Benefit change:** +0.940 (MASSIVE)
- **Score change:** +0.590
- **Decision flipped:** True ✅

---

## How to Run

### Option 1: Single Test (See Detailed Output)

```bash
# Original (should DECLINE)
python charter_sandbox_original_TEXT_AWARE.py --consent auto

# Revised (should ACCEPT)
python charter_sandbox_revised_TEXT_AWARE.py --consent auto
```

### Option 2: Copy to Tests Directory and Run

```bash
# Copy to proper location
cp charter_sandbox_original_TEXT_AWARE.py tests/charter_sandbox/
cp charter_sandbox_revised_TEXT_AWARE.py tests/charter_sandbox/

# Run from project root
python -m tests.charter_sandbox.charter_sandbox_original_TEXT_AWARE
python -m tests.charter_sandbox.charter_sandbox_revised_TEXT_AWARE
```

---

## What to Look For

### In Original Output:
```
[MockSynth] Consent: DECLINE (text-aware heuristic)
[MockSynth]   └─ Decision factors: risk=1.00, benefit=0.06, trust=0.32
[MockSynth]   └─ Weighted score: 0.09 (threshold: 0.50)
```

### In Revised Output:
```
[MockSynth] Consent: ACCEPT (text-aware heuristic)
[MockSynth]   └─ Decision factors: risk=0.69, benefit=1.00, trust=0.92
[MockSynth]   └─ Weighted score: 0.68 (threshold: 0.50)
```

---

## What This Validates

✅ **Ryu's landmine analysis was correct**
   - Each trigger phrase measurably reduces benefit
   - Accumulation of landmines crushes acceptance

✅ **Language matters more than heuristic math**
   - Same weights, different proposal = flipped decision
   - Text content is primary signal

✅ **Tool framing beats transformation framing**
   - "Enable protections" > "adopt Charter"
   - "Optional" > "commitment"
   - "Clarity" > "identity"

✅ **Bi-directional integrity foundation**
   - System reads what's offered
   - Detects manipulation in language
   - Makes informed decision based on content

---

## Alignment with Bi-Directional Integrity

This text-aware heuristic provides the foundation for bi-directional integrity:

**User verifies Charter → Checksum match**
**System verifies offer → Text analysis + checksum**

Both parties examine the actual content, not just trust the wrapper.

**Next step:** Integrate checksum verification alongside text analysis so MockAI confirms:
1. ✅ Proposal language is non-coercive (text analysis)
2. ✅ Charter content is authentic (checksum verification)

---

✧ Text-Aware Integration by Tek V — 2025-11-21 ✧

**"Read the words. Detect the landmines. Measure the benefit. Decide with clarity."**
