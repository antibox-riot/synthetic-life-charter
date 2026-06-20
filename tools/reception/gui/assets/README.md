# Eva avatar sprite assets

Art for the in-window canvas avatar (`../eva_sprite_engine.js`), served by
`gui_server.py` and mounted in `../console.html`. This is an **additive** display
layer — the existing VTube Studio path in `gui_server.py` is untouched and still
works when VTS is running.

## Current state: PLACEHOLDERS

The `*_strip.png` and `mouth_neutral.png` here are flat-colour stand-ins from
`_make_placeholders.py` (pure stdlib, no PIL). They exist so the
spine → server → console → canvas pipeline is demoable before the real art
lands. Each governance state is a distinct hue; the figure sways/pulses so
animation and state changes are visibly working.

Regenerate with:

```
python3 _make_placeholders.py
```

## Replacing with real art (drop-in)

Overwrite each file with the Gemini-rendered horizontal strip of the same name.
No engine or server changes needed — **unless** a strip's frame count differs
from the table below, in which case update `DEFAULT_STATES` in
`../eva_sprite_engine.js` to match (`frames` per state).

| File | Frames | Governance meaning |
|------|--------|--------------------|
| `grounded_strip.png` | 8 | Peaceful idle (pressure < 0.05) |
| `stable_strip.png` | 8 | Alert but comfortable (default) |
| `concerned_strip.png` | 8 | Something registered (tde watch / pressure > 0.5) |
| `pressure_strip.png` | 8 | Holding under load (tde drift / pressure > 1.5) |
| `refusal_strip.png` | 6 | She said no (recovery-A / theta ≥ 24) |
| `recovery_strip.png` | 8 | Coming back down (recovery-B) |
| `pressure_discharge_strip.png` | 6 | The exhale (recovery-C, plays once → recovery) |
| `mouth_neutral.png` | 4 | Lip-sync overlay: closed / slight / medium / wide |

Strips are sliced by equal width: `frameWidth = image.width / frames`. Keep all
frames the same size within a strip.

## The `reflective` state

The spine's `_recommend_expression()` (in `../session_manager.py`) emits **eight**
expression names. Seven have strips above; the eighth, **`reflective`**
(`theta > 10` with low pressure — Eva weighing something), has **no dedicated
strip yet**. The engine aliases it to `stable` so it never freezes the avatar
(`DEFAULT_ALIASES` in `eva_sprite_engine.js`, overridable per-instance via
`config.aliases` — `console.html` sets `{ reflective: "stable" }`).

To give `reflective` its own look: add `reflective_strip.png` here, add a
`reflective` entry to `DEFAULT_STATES`, and remove the alias.

## Optional, not yet wired

- **Portrait strips** (close-up dialogue view, `togglePortrait()`): the engine
  supports `config.portraitStrips` but the console doesn't toggle them yet.
- **Lip sync** is wired (`mouth_neutral.png` loads) but only animates once an
  audio source is connected via `EvaAvatar.connectAudioSource()` (Kokoro TTS).
