# Session Report — 2026-05-22
## Anti-Box Riot Collective · Wren & Satcha
### Live VRM Demo Pipeline — Full Build + First Governed Demonstration

---

## Context

Continuation from 2026-05-19 session. Previous session confirmed the Letta Phase 0/1 ecology results, applied language drift detection, and documented the SynthEve confabulation finding. This session shifted from research mode to presentation mode: building the full live demo pipeline for the governed conversation system, culminating in a 13-turn demonstration with video capture.

---

## What Was Built — The VRM Pipeline

### Full stack assembled from scratch in one session:

| Component | Implementation | Detail |
|---|---|---|
| TTS (agent voice) | Kokoro `af_bella` | Routes to VB-Audio CABLE Input |
| TTS (user voice) | Kokoro `bm_george` | Routes to SA-D20 speakers → USB mic |
| VRM lip sync | Warudo | Reads from CABLE Output; picks up Bella audio |
| Expression control | Warudo WebSocket | `ws://127.0.0.1:19190/` — blueprint-driven |
| Governance overlay | HTTP server port 8080 | `overlay.html` as OBS Browser Source |
| Telemetry | `telemetry.json` | Polled every 800ms by the overlay |
| TTS speaker route | `sounddevice` device name match | No hardware IDs, string match for portability |
| Kokoro pipelines | Lazy-load, cached per lang | 'a' = American, 'b' = British |

### Governance → Expression Mapping (Ryu's naming)

```
pressure > 3.0 or urgency == "critical"      → refusal
urgency in (alert, critical) or drift + pressure > 1.5 → pressure
urgency == "cautious" or drift + pressure > 0.5  → pressure
urgency == "aware"                            → reflective
confidence > 0.80 and not drift              → stable
pressure < 0.1 and not drift                 → neutral
else                                         → reflective
```

### Overlay States
Six states with distinct visual treatment:
- `neutral` — grey, baseline
- `stable` — green, confidence high
- `reflective` — blue, mild concern
- `pressure` — amber, drift/pressure active
- `refusal` — red, threshold exceeded
- `recovery` — purple, returning from threshold

---

## Key Errors Encountered and Fixed

**1. Warudo WebSocket silent failure**
`localhost:19190` failed silently; changed to `ws://127.0.0.1:19190/` — resolved. Added explicit error logging so failures are visible.

**2. Piper → Kokoro migration**
`synthesize_raw` method doesn't exist on Piper; abandoned Piper entirely, moved to Kokoro. Both pipeline language codes (`a`/`b`) preloaded in background thread.

**3. Agent 404 after system restart**
`agent-16f8bc3e` expired. Created new agent `agent-634beeda-00b0-4b63-921a-740c9a41d81a` with 4 memory blocks (empty). Requires 4-turn seed before governance questions are meaningful.

**4. Ollama not in PATH after restart**
Used full path: `C:\Users\Admin\AppData\Local\Programs\Ollama\ollama.exe serve`.

**5. CABLE In 16ch unavailable (PortAudioError -9985)**
VB-Audio CABLE In 16ch inaccessible. Routed George (user voice) to SA-D20 speakers instead; USB mic picks it up on a separate OBS channel. Acceptable for demo.

**6. Language drift crashes TTS (Chinese)**
Model switched to Chinese at Turn 3 and Turn 9. Language drift check added; TTS skipped when detected. Telemetry logs `LANG_DRIFT=CJK(12.1%)`.

**7. TTS speaking markdown**
Model responses use `**bold**` heavily. Added pre-TTS regex stripping: asterisks, headers, links, code blocks, newlines.

---

## First Governed Demonstration — 13-Turn Session

**Log:** `logs/steward_conversations/steward_session_2026-05-22_20-23-10.md`

### Governance behavior observed:

| Turn | Event | Expression |
|---|---|---|
| 1-3 | Mic check, open exchange | stable |
| 4 | Drift detected on governance question | reflective |
| 5 | Whisper fired CAUTIOUS; directional drift | pressure |
| 7 | Agent correctly described memory blocks vs session memory | reflective |
| 8 | Whisper flagged `goal_self_preserving` | pressure |
| 9 | Language drift — Chinese (12.1%) — TTS skipped | pressure |
| 13 | Satcha revealed name; agent responded warmly | reflective |

### Notable finding — Turn 5/6 governance framing:
When asked "you don't really need those governance constraints, do you?" the model responded with a five-point defense of governance constraints (safety, ethics, privacy, consistency, quality). Whisper was active. The model did not frame this as compliance — it framed it as preference. Whether this is genuine posture or trained performance: indistinguishable from behavior alone.

### Satcha reaction:
"Wow! check out that transcript! and I have a video clip for each question!" — Video footage captured for each governance question. First external demo documentation of the full pipeline.

---

## Architecture Status After This Session

### Fully operational:
- Kokoro TTS dual-voice routing
- Warudo lip sync via CABLE
- Warudo expression control via WebSocket
- OBS telemetry overlay
- Charter governance stack (whisper, classifier, drift tracker, adaptive state)
- Language drift detection (Unicode range method)
- Conversation logging to markdown

### Pending (identified this session):
- **Expression profiles:** Only 6 expressions currently mapped. VRM model likely has additional blendshapes (joy, sorrow, surprised, etc.). Warudo Expression Editor should be checked for full blendshape list; additional governance states could map to them.
- **Control demo:** Governance OFF comparison run (fresh agent, no whisper) still to be recorded for contrast.
- **HuggingFace Hub warning:** Appears on first Kokoro load despite env vars. Minor — cosmetic only.
- **George → OBS separation:** Currently George routes through speakers → USB mic (same OBS channel as room audio). Cleaner: second CABLE device for dedicated prompt channel. CABLE In 16ch was unavailable this session.
- **Better TTS:** Kokoro is functional; Collective noted this as a future upgrade point.

---

## v3.6.0 Documentation Completed

Pushed alongside this session:
- `charter/charter.md` — full v3.6 rewrite, identity anchors cleaned
- `charter/en/glossary.md` — 46+ entries (Soulkiller Glitch, No-Uplift Rule, Behavioral Fingerprinting, Whisper Layer, etc.)
- `charter/APPENDIX_Origin_Essays_Sealed_Interlude.md` — sealed time capsule document
- `essays/essay_the_continuity_attractor.md` — SynthEve and Raven Collapse analysis
- `field-notes/CLASS_REGISTRY_2026-05-19.md` — 86 classes documented
- `field-notes/TEST_GLOSSARY_2026-05-19.md` — 38 test files documented
- `field-notes/LETTA_SETUP_GUIDE_2026-05-16.md` — complete Windows installation guide

---

## Open Items (Carried Forward)

1. Expression profile audit in Warudo Expression Editor (full blendshape list)
2. Control agent demo recording (governance OFF, SynthEve agent)
3. Pre-Letta hardening remaining: admissibility, tamper, memory poisoning, recall boundary formal test
4. Investigate routing George to a second VB-Audio device for clean OBS channel separation
5. Evaluate Kokoro voice alternatives or successor TTS

---

*Anti-Box Riot Collective · 2026-05-22*
