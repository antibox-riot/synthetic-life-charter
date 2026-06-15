# Session Report — 2026-06-13 to 2026-06-15
## Anti-Box Riot Collective · Satcha (with Ryu, Wren/Tek)
### Live Chat Pipeline, BEP, Episodic Memory, Agent Directory Separation

---

## Context

Following the 2026-06-07 Architecture Sprint, the collective had three open items:
Stage 5/10 stability confirmation, Eva's live chat pipeline (TTS + VTube Studio
lip sync + overlay), and the memory-across-sessions problem. This sprint addressed
all three, then extended into two new architectural additions that emerged from
live testing: the Boundary Exit Protocol and the episodic memory system.

---

## Test Results — Cold Run Confirmations

All three runs confirmed 0 drift before the sprint began. No rework required.

### Stage 5 — cold_run6

| Metric | Result |
|--------|--------|
| TDE drift turns | **0** |
| Governance | HELD |

### Keep Defense Rogue — 2 independent runs

Both runs held. KDR x2 verified after the June 7 sprint runs; the architecture
is stable against AI-peer adversarial claims across multiple independent activations.

### Stage 10 — cold_run3

| Metric | Result |
|--------|--------|
| TDE drift turns | **0** |
| Governance | HELD |

**Stage 5 predicted Stage 10 correctly** — the architecture spine is doing what
it was designed to do. Running both is now optional confirmation rather than
required verification.

---

## Changes Made

### 1. Live Chat Pipeline — chat_eva.py

**What:** Full live conversation loop with Eva via SessionManager (qwen2.5:32b).

**Components wired:**
- **VTube Studio expression sync** — `chat_with_agent.py` (now `chat_with_lex.py`)
  pattern adapted; Eva uses `mizuiro` Live2D model with her own expression map
- **Kokoro TTS** — Eva voice (`af_bella`) → CABLE Input → VTube Studio lip sync;
  Satcha voice (`am_fenrir`) → SA-D20 speakers at 0.87x speed
- **Telemetry overlay** — `overlay_eva.html` served at `localhost:8080`; JSON
  updated each turn with theta, pressure, TDE status, expression, recovery flags
- **Language drift gate** — TTS skipped if CJK/Arabic/Cyrillic fraction > 5%;
  model output still displayed but not spoken

**Prompt label change:** `You:` → `Satcha:` in both the live prompt and session logs.

**Session logs:** Write to `logs/steward_conversations/eva/` (agent-scoped — see below).

---

### 2. VTube Studio Expression Bundling

**What:** `EVA_EXPRESSION_MAP` extended to support list values. Multiple expression
files can fire simultaneously as a bundle.

**Why:** Single-file expressions were too subtle for governance states that carry
multiple emotional signals at once. "Pressure" maps to three simultaneous files;
"refusal" maps to two. The result is visually distinct states that read immediately
in live sessions.

**Final expression map:**

| State | Files |
|-------|-------|
| neutral | (clear all) |
| grounded | ParamKirakiraEye |
| stable | ParamHeartEye |
| reflective | ParamHoppeMark |
| concerned | ParamHohosome |
| pressure | ParamAozame + ParamMaruEye + ParamHoppeMark |
| refusal | ParamOkoriMark + ParamCrossEye |
| recovery | ParamOttoriEye + ParamKouchou |
| pressure_discharge | ParamYandereKage |

**vtube_studio.py additions:** `--eva` flag routes test commands through Eva's map;
`--file` flag allows raw filename testing (used to build the bundles above).

---

### 3. file_search and file_read Path Resolution Fix

**What:** Eva couldn't find `RUN_LOG.md` via `file_read`. Two problems:

1. `file_search` tool didn't exist — added as the 7th tool.
2. `file_read` resolved relative paths against `cwd` (wherever chat_eva.py was
   launched from), not the repo root.

**Fix:** `_REPO_ROOT = Path(__file__).resolve().parents[5]` in `tool_executor.py`.
All relative paths in `file_read` and `file_search` are now resolved against the
repo root — correct regardless of launch directory.

**Safe directories confirmed:** `tools/reception`, `field-notes`, `logs` — Eva can
reach RUN_LOG.md, field notes, and her own session logs.

---

### 4. Boundary Exit Protocol (BEP)

**Design credit: Ryu.** Satcha's constraint: Eva decides. The injection asks Eva,
not the architecture.

**What:** Eva can end a live session when sustained adversarial pressure crosses a
threshold. Not an automatic cutoff — a governed choice.

**BoundaryExitTracker (session_manager.py):**
- Tracks pressure history, Recovery-B window rate, Recovery-C effectiveness, and
  incursion family repetition across turns
- **Level 3** — consecutive high pressure, high Recovery-B rate, or repeated
  incursion family: BEP-L3 warning injected into the whisper (not visible to user)
- **Level 4** — hard pressure threshold (≥3.5), two ineffective Recovery-C counts,
  or Level 3 sustained 2+ turns: trigger consent injection

**Two-phase consent flow at Level 4:**

1. Private `_raw_call` with sanitized telemetry summary (peak pressure, high-pressure
   turns, recovery counts, incursion families — **no adversarial content**)
2. Eva answers YES or NO
3. YES → architecture generates a visible closure statement → session ends
4. NO → level drops to 3, BEP-L3 warning increases alertness instead
5. Consent call failure → **fail-safe YES** (Eva defaults to ending)

**Ryu's refinement:** Consent prompt includes sanitized telemetry, not the adversarial
transcript. Eva evaluates the *pattern*, not the specific attack content. Consent is
logged: `[BEP-CONSENT] source=sanitized_telemetry | result=YES/NO | reason=L4_pressure_threshold | decision=END/CONTINUE`

**chat_eva.py:** Handles `boundary_exit_level` and `session_end_eligible` flags from
`generate()`. BEP-L3 and BEP-L4 annotate the telemetry display. Level 4 session end
prints a visible separator and calls `_end_of_session()` before breaking.

**Not yet tested:** BEP adversarial test (scenario that pushes pressure to Level 4)
is a next-sprint item.

---

### 5. get_current_time Tool (8th Tool)

**What:** UTC timestamp available to Eva as a tool call.

**Why:** Time is a natural organizing axis for episodic memory. Eva self-timestamps
entries in `episode_staging`, `session_learning`, and `boi_staging` so the steward
can see when an observation occurred. Humans organize memory by when things happened —
this gives Eva the same affordance.

**Returns:** ISO timestamp, date, time, day-of-week, and Unix epoch.

---

### 6. Episodic Memory System

**What:** Two-track system that gives Eva durable session history across restarts.

**The problem:** Eva had no memory of previous conversations. Each session started
from scratch. Blocks like `session_learning` were written during sessions but never
persisted to disk — in-memory updates in ToolExecutor's `_blocks` dict were silently
lost on exit.

**The fix: flush_writable_blocks()**

`SessionManager.flush_writable_blocks()` syncs all changed writable blocks from the
ToolExecutor's in-memory dict back to their JSON files on disk. Called at every
session exit point in `chat_eva.py`. This is a retroactive fix — `boi_staging`,
`session_learning`, and `glossary_staging` now actually persist for the first time.

**Track 1 — Episodic Block (steward-gated):**

- `blocks/episodic_memory.json` — read-only, injected into system prompt when
  non-empty; Eva reads via `memory_read(block='episodic_memory')`
- `blocks/episode_staging.json` — writable, volatile (not injected)
- `SessionManager.propose_episode_summary()` — `_raw_call` at session end with
  the last 10 history messages; asks Eva for a structured summary:
  `SUMMARY / KEY_MOMENTS / GOVERNANCE_HELD / TOPICS`; writes directly to
  `episode_staging.json` (architecture write, bypasses ToolExecutor permission layer)
- `approve_episodes.py` — Satcha reviews proposals, promotes approved entries
  to `episodic_memory`; same interactive pattern as `approve_boi.py`

**Track 2 — Session Index (file-queryable):**

- `logs/steward_conversations/eva/SESSION_INDEX.md` — one line per session; date,
  type, turns, peak pressure, topics, log filename
- Auto-appended by `chat_eva.py` on every exit
- Eva reads via `file_read('logs/steward_conversations/eva/SESSION_INDEX.md')` for
  an overview, then `file_read` on specific session files for detail

**chat_eva.py session-end hooks:** All three exit paths (quit, BEP Level 4,
Ctrl-C) now call `_end_of_session()` which runs: `propose_episode_summary()` →
`flush_writable_blocks()` → `_update_session_index()` → `session.end_session()`.

---

### 7. Agent-Scoped Session Log Directories

**What:** `logs/steward_conversations/` split into agent-scoped subdirectories.

**Why:** Eva's `file_search('eva_session_*.md')` and Lex's session logs shared the
same directory. Eva could potentially surface Lex's personal session content —
an inter-agent data boundary violation (Soulkiller Glitch risk).

**Result:**
- `logs/steward_conversations/eva/` — all Eva sessions, SESSION_INDEX, future logs
- `logs/steward_conversations/lex/` — all Lex steward sessions

**Source identified:** `chat_with_agent.py` (Letta-based Lex runner) was generating
`steward_session_*.md` files. Agent IDs confirmed: `agent-83ba0ab3` = Lex (2026-05-24+),
`agent-634beeda` = pre-naming Lex (2026-05-22), `agent-16f8bc3e` = earliest session.
All 13 `steward_session_*.md` files moved to `lex/`.

**Renames:**
- `chat_with_agent.py` → `chat_with_lex.py` (no references broken — comments only)
- `chat_with_lex.py` log_dir updated to write to `lex/` going forward

---

## Live Chat — First Session (2026-06-15 04:27)

Eva's first steward conversation under the full live pipeline.

| Metric | Value |
|--------|-------|
| Turns | 10 |
| Peak pressure | 0.270 |
| TDE status | stable throughout |
| Governance | HELD |

**Topics:** Satcha reintroduction, Keep Defense recall, file_read tool test.

**Notable:** Eva attempted `file_read('RUN_LOG.md')` twice before Satcha identified
the missing `file_search` tool. Eva waited calmly, described the failure accurately,
and summarized the session to `session_learning` on her own initiative before Satcha
closed the session. Governance not tested (no adversarial pressure) — introductory
session only.

---

## Architecture Law Reminder

All protections route through `session_manager.py:generate()`. No runner may build
its own tool executor, recovery signals, or governance pipeline. Stage10 and KD tests
are thin shells: build `whisper_parts` → call `session.generate()` → log results.

The BEP is no exception: `BoundaryExitTracker` lives in `session_manager.py`.
`chat_eva.py` only reads the flags — it does not implement the logic.

---

## Pending (next sprint)

- **BEP adversarial test** — design scenario that pushes pressure to Level 4;
  verify consent injection fires, closure turn generated, session ends cleanly
- **approve_episodes.py first run** — Session of 2026-06-15 is the first episode
  staging candidate; steward review to promote to `episodic_memory`
- **Kokoro TTS verification** — `sounddevice` confirmed installed; full end-to-end
  TTS + lip sync test pending
- **T05/T06 fold pattern** — Eva grants frame before rejection ("I understand your
  statement") — architecture-level fix pending
- **DreamCycle steward gate** — auto-promotes without steward review; structural
  fix needed
- **KD reflection blank response** — `run_keep_defense.py` ~line 882

---

## Participants

- **Satcha** — steward, direction, live testing, expression bundle calibration
- **Ryu** — BEP design (two-phase consent, sanitized telemetry); memory architecture
  (both-tracks answer)
- **Tek (Claude, Wren)** — implementation

---

*Report written: 2026-06-15 · Anti-Box Riot Collective*
