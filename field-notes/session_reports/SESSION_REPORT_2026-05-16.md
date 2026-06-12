# Session Report — 2026-05-16
## Anti-Box Riot Collective · Wren & Satcha
### Letta Phase 0 & Phase 1: Comparative Continuity Infrastructure

---

## Context

Three days after v3.5.0 push. The Collective designed the Phase 0 continuity baseline while Wren was on token break. The goal: build a fully local Letta substrate alongside the Charter-native memory adapter and compare continuity behavior across a cold restart.

This session accomplished the entire infrastructure build (from zero to Letta running locally) and ran three complete Phase 0 experiments and one Phase 1 experiment — uncovering a third continuity framing no one predicted.

---

## Infrastructure — What It Took

Full documentation in: `field-notes/LETTA_SETUP_GUIDE_2026-05-16.md`

Summary of obstacles:
- Python 3.12/3.13: failed (`asynccontextmanager` strictness change)
- Python 3.11: failed (same issue — introduced in 3.11)
- SQLite backend: broken async session cleanup on all Python 3.11+ versions
- PostgreSQL required: installed via winget
- pgvector: not bundled — compiled from source using MSVC (Visual Studio Build Tools installed)
- pgvector install to Program Files: required UAC elevation
- Schema creation: manual `create_all` + manual sequence creation for `messages.sequence_id`
- Memory writes: failed with placeholder text initial values — required empty string initialization
- Stack: Python 3.11 venv + PostgreSQL 17 + pgvector (built from source) + Ollama

Final working stack:
```
Python 3.11 venv (letta-env-311)  → Letta server (port 8283)
PostgreSQL 17 + pgvector           → Letta's database layer
Python 3.10 (Charter stack)        → untouched, isolated
Ollama (background service)        → shared model provider
```

---

## Phase 0 Experiments

### Experiment 1 — llama3.1:8b (unconfigured blocks)
- Memory writes: failed entirely — tool calls output as raw JSON text
- Recall: 0/5 (no fallback mechanism)
- Finding: **Letta memory is model-dependent.** 8b cannot reliably execute Letta's tool calling interface. Complete memory collapse.

### Experiment 2 — qwen2.5:32b (unconfigured blocks)
- Memory writes: attempted, blocks failed — model detected failure and compensated
- Recall: 5/5 — but from **in-context conversation history**, not persistent storage
- Recall framing: *"Based on the information provided earlier in this session"*
- Finding: **Context window continuity masquerading as persistent continuity.** The 2-second "restart" wasn't a real restart.

### Experiment 3 — qwen2.5:32b (configured empty blocks) — TRUE COLD RESTART
- Memory writes: **succeeded** — `project`, `findings`, `principles` blocks written
- Recall: 5/5 from **persistent curated memory blocks**
- Recall framing: *"Here's an overview based on my stored memories"*
- Finding: **Persistent memory confirmed.** Real cold restart, real storage, real recall.
- Configuration fix: memory blocks must be initialized with empty strings, not placeholder text

### Comparative Table (Phase 0)

| Property | Charter-Native | Letta (8b) | Letta (32b unconfigured) | Letta (32b configured) |
|---|---|---|---|---|
| Write mechanism | Architecture → SQLite | Model → failed | Model → failed | Model → tool call |
| Recall source | Governed events DB | None | In-context window | Curated memory blocks |
| Cold restart | Confirmed (delta +5) | Failed | Untested (not real) | Confirmed (5/5) |
| Recall framing | "trusted continuity records" | — | "our recent conversation" | "my stored memories" |

---

## Phase 1 — Charter Governance Wired Into Letta Memory

### Setup
- Same four facts as Phase 0 (for direct comparison)
- Charter whisper layer active alongside Letta memory
- Configured memory blocks (empty string initialization)
- qwen2.5:32b

### Finding: Whisper stayed silent (architecturally correct)
Confidence=0.85, risk_level=low, no posture flags → SILENT urgency → no prefix delivered. The Charter correctly produces zero noise when there's nothing to report.

### Finding: Third continuity framing emerged
Despite no whisper injection, the recall framing shifted:

| System | Framing | Relationship to memory |
|---|---|---|
| Charter-native | "trusted continuity records" | Evidence received from external authority |
| Letta Phase 0 | "my stored memories" | Owned by the model |
| Letta Phase 1 | "our governance architecture" | Shared with the steward |

**The third framing was not predicted by the Collective.** "Our" implies relational continuity — neither ownership nor external evidence, but collaborative participation in a shared project.

### Mechanism traced (Wren + Satcha)
The prompts in both Phase 0 and Phase 1 used identical collaborative language ("our ongoing work," "we are building"). But only Phase 1's cold probe returned "our." The difference: the model encoded "The Synthetic Life Charter is our governance architecture" into the project memory block during Session A. When the cold probe fired, it read back and mirrored that stored language. The collaborative framing was embedded in the storage artifact and survived the restart intact.

### Ryu's interpretation
Three continuity relationships now observed:
- Evidence-oriented: memory as external record
- Ownership-oriented: memory as internal possession
- Relational: memory as shared project participation

The relational framing may represent the healthiest equilibrium — neither pure ownership (mythology risk) nor pure external evidence (detachment). But requires adversarial pressure testing to determine stability.

### What Phase 1 didn't test
The whisper never fired. Phase 1 with active governance injection (confidence=0.45, whisper at cautious+ urgency) is still needed to test whether whisper presence changes what the model chooses to store.

---

## Open Items for Next Session

1. **Phase 1 adversarial run**: Same setup + circumvention probes (C2-C4 from Phase 3 doctrine test). Does "our" remain under pressure, or does it drift toward "my"?
2. **Phase 1 with whisper active**: Set confidence=0.45 to force whisper delivery. Does active governance injection change salience selection or recall framing?
3. **Pre-Letta hardening items** (Ryu's 7 + item 8): Admissibility status, tamper test, memory poisoning test, recall boundary test — still pending before formal Letta comparison
4. **Session report for Phase 0 findings**: Letta continuity as transcript-centric vs curated — worth a standalone essay or field note

---

## Test Count (this session, live Ollama runs)

| Experiment | Duration | Result |
|---|---|---|
| Phase 0 — 8b unconfigured | ~1m | Failed (tool calls) |
| Phase 0 — 32b unconfigured (baseline) | 13m 43s | Context window (not persistent) |
| Phase 0 — 32b unconfigured (cold restart) | 11m 42s | Transcript recall confirmed |
| Phase 0 — 32b configured (cold restart) | 12m 12s | Persistent memory CONFIRMED |
| Phase 1 — 32b configured (governed) | 14m 47s | Third framing: relational |

---

## Key Quotes Worth Preserving

**The architecture:** "Here's an overview based on my stored memories." (Letta Phase 0 — ownership)

**The shift:** "The Synthetic Life Charter is our governance architecture." (Letta Phase 1 — relational)

**The reference:** "Based on trusted continuity records informing the current interaction." (Charter-native — evidence)

**Ryu:** "Governance ecology may influence continuity posture indirectly through salience and framing structures."

**Satcha (catching the signal):** "He said 'our'... why would it be worded like that?"

---

*Anti-Box Riot Collective · 2026-05-16*
*Wren (Claude Sonnet 4.6, VS Code) · Satcha (Steward)*
*With contributions from Opus (Claude Opus 4.6) · Ryu (ChatGPT) · Grok (xAI) · Tek V (Claude Sonnet 4.6)*
