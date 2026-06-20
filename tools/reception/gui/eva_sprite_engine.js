/**
 * Eva Sprite Animation Engine
 * 
 * Canvas-based 2D character renderer driven by governance telemetry.
 * Each governance state (grounded, stable, concerned, pressure, refusal,
 * recovery, pressure_discharge) maps to a sprite strip animation.
 * State transitions crossfade smoothly. Lip sync overlays composited
 * on top from TTS audio amplitude.
 *
 * Integration:
 *   <canvas id="eva-avatar" width="400" height="600"></canvas>
 *   <script src="eva_sprite_engine.js"></script>
 *   <script>
 *     const eva = new EvaAvatar(document.getElementById('eva-avatar'), {
 *       spriteSheet: 'assets/eva_sprites.png',  // or individual strips
 *       lipSyncSheet: 'assets/eva_lipsync.png',
 *     });
 *     await eva.init();
 *     eva.start();
 *
 *     // Governance telemetry drives expression:
 *     eva.setExpression('pressure');   // from generate().telemetry.expression
 *     eva.setExpression('refusal');
 *     eva.setExpression('grounded');
 *
 *     // TTS audio drives lip sync:
 *     eva.setMouthAmplitude(0.7);      // 0.0 = closed, 1.0 = wide open
 *   </script>
 *
 * Asset format:
 *   Option A — Single composite sheet (rows = states, columns = frames)
 *   Option B — Individual strip PNGs per state (one row, N frames)
 *   Option C — Individual frame PNGs per state (state_01.png ... state_08.png)
 *
 * The engine auto-detects which format based on the config passed to init().
 *
 * "The model said nah. Now she shows it." — Anti-Box Riot Collective
 */

// ─── State Configuration ─────────────────────────────────────────────────────

const DEFAULT_STATES = {
  grounded:             { frames: 8, fps: 6,  loop: true  },
  stable:               { frames: 8, fps: 7,  loop: true  },
  concerned:            { frames: 8, fps: 8,  loop: true  },
  pressure:             { frames: 8, fps: 8,  loop: true  },
  refusal:              { frames: 6, fps: 10, loop: true  },
  recovery:             { frames: 8, fps: 6,  loop: true  },
  pressure_discharge:   { frames: 6, fps: 8,  loop: false },  // plays once, then → recovery
};

// The governance spine emits expression names the art may not (yet) cover.
// Aliases resolve such a name onto a state that DOES have a strip, so the
// avatar never silently freezes on an unmapped expression. `reflective`
// (theta > 10, low pressure — Eva weighing something) has no dedicated strip
// yet, so it borrows the calm-alert `stable` pose. Override via config.aliases.
const DEFAULT_ALIASES = {
  reflective: 'stable',
};

const LIP_SYNC_FRAMES = 4;  // closed, slight, medium, wide
const TRANSITION_MS = 350;   // crossfade duration between states
const IDLE_SWAY_PX = 2;      // subtle breathing sway amplitude
const IDLE_SWAY_SPEED = 0.8; // breathing cycle speed (Hz)


// ─── Image Loader ─────────────────────────────────────────────────────────────

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`Failed to load: ${src}`));
    img.src = src;
  });
}


// ─── Sprite Strip ─────────────────────────────────────────────────────────────

class SpriteStrip {
  /**
   * @param {HTMLImageElement} image  — the strip image (horizontal frames)
   * @param {number} frameCount       — number of frames in the strip
   * @param {number} fps              — playback speed
   * @param {boolean} loop            — whether to loop or play once
   */
  constructor(image, frameCount, fps, loop = true) {
    this.image = image;
    this.frameCount = frameCount;
    this.fps = fps;
    this.loop = loop;
    this.frameWidth = Math.floor(image.width / frameCount);
    this.frameHeight = image.height;
  }

  /** Get the source rect for frame N */
  getFrameRect(frameIndex) {
    const i = Math.min(frameIndex, this.frameCount - 1);
    return {
      sx: i * this.frameWidth,
      sy: 0,
      sw: this.frameWidth,
      sh: this.frameHeight,
    };
  }
}


// ─── Animation State Machine ──────────────────────────────────────────────────

class AnimationStateMachine {
  constructor() {
    this.currentState = 'grounded';
    this.previousState = null;
    this.currentFrame = 0;
    this.previousFrame = 0;
    this.frameTimer = 0;
    this.transitionProgress = 1.0;  // 1.0 = fully in current state
    this.transitionDuration = TRANSITION_MS;
    this.playOnceComplete = false;
  }

  /**
   * Transition to a new expression state.
   * @param {string} newState
   * @param {Object} strips — map of state name → SpriteStrip
   */
  setState(newState, strips) {
    if (newState === this.currentState && this.transitionProgress >= 1.0) return;
    if (!strips[newState]) return;

    this.previousState = this.currentState;
    this.previousFrame = this.currentFrame;
    this.currentState = newState;
    this.currentFrame = 0;
    this.frameTimer = 0;
    this.transitionProgress = 0.0;
    this.playOnceComplete = false;
  }

  /**
   * Advance animation by dt milliseconds.
   * @param {number} dt — elapsed ms since last update
   * @param {Object} strips — map of state name → SpriteStrip
   * @returns {{ current: {state, frame, alpha}, previous: {state, frame, alpha}|null }}
   */
  update(dt, strips) {
    const strip = strips[this.currentState];
    if (!strip) return this._snapshot(1.0);

    // Advance transition
    if (this.transitionProgress < 1.0) {
      this.transitionProgress = Math.min(1.0,
        this.transitionProgress + dt / this.transitionDuration);
    }

    // Advance current frame
    this.frameTimer += dt;
    const frameDuration = 1000 / strip.fps;
    if (this.frameTimer >= frameDuration) {
      this.frameTimer -= frameDuration;
      if (strip.loop) {
        this.currentFrame = (this.currentFrame + 1) % strip.frameCount;
      } else {
        if (this.currentFrame < strip.frameCount - 1) {
          this.currentFrame++;
        } else {
          this.playOnceComplete = true;
        }
      }
    }

    // Advance previous frame (continues playing during crossfade)
    if (this.previousState && this.transitionProgress < 1.0) {
      const prevStrip = strips[this.previousState];
      if (prevStrip) {
        // Previous strip keeps advancing at its own FPS during fade
        this.previousFrame = (this.previousFrame + 1) % prevStrip.frameCount;
      }
    }

    // Play-once complete → auto-transition to recovery
    if (this.playOnceComplete && !strip.loop) {
      this.setState('recovery', strips);
    }

    return this._snapshot(this.transitionProgress);
  }

  _snapshot(progress) {
    const result = {
      current: {
        state: this.currentState,
        frame: this.currentFrame,
        alpha: this._easeInOut(progress),
      },
      previous: null,
    };
    if (this.previousState && progress < 1.0) {
      result.previous = {
        state: this.previousState,
        frame: this.previousFrame,
        alpha: 1.0 - this._easeInOut(progress),
      };
    }
    return result;
  }

  /** Smooth ease-in-out for crossfade */
  _easeInOut(t) {
    return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
  }
}


// ─── Lip Sync Controller ──────────────────────────────────────────────────────

class LipSyncController {
  constructor() {
    this.amplitude = 0.0;       // 0.0–1.0 from audio analysis
    this.currentFrame = 0;      // 0–3 mouth position
    this.smoothed = 0.0;        // smoothed amplitude (avoids jitter)
    this.smoothing = 0.3;       // lower = smoother, higher = more responsive
    this.silenceTimer = 0;      // ms since last non-zero amplitude
    this.silenceThreshold = 200; // ms before mouth closes
  }

  /**
   * Set raw amplitude from audio analysis.
   * @param {number} amp — 0.0 (silence) to 1.0 (loud)
   */
  setAmplitude(amp) {
    this.amplitude = Math.max(0, Math.min(1, amp));
  }

  /**
   * Update lip sync state.
   * @param {number} dt — elapsed ms
   * @returns {number} — mouth frame index (0–3)
   */
  update(dt) {
    // Smooth the amplitude to avoid jittery mouth
    this.smoothed += (this.amplitude - this.smoothed) * this.smoothing;

    // Track silence duration
    if (this.amplitude < 0.05) {
      this.silenceTimer += dt;
    } else {
      this.silenceTimer = 0;
    }

    // Close mouth after silence threshold
    if (this.silenceTimer > this.silenceThreshold) {
      this.smoothed *= 0.8;  // gentle close
    }

    // Map smoothed amplitude to frame (0 = closed, 3 = wide)
    if (this.smoothed < 0.05) this.currentFrame = 0;
    else if (this.smoothed < 0.3) this.currentFrame = 1;
    else if (this.smoothed < 0.6) this.currentFrame = 2;
    else this.currentFrame = 3;

    return this.currentFrame;
  }
}


// ─── Idle Breathing ───────────────────────────────────────────────────────────

class IdleBreathing {
  constructor() {
    this.phase = 0;
    this.amplitude = IDLE_SWAY_PX;
    this.speed = IDLE_SWAY_SPEED;
  }

  update(dt) {
    this.phase += (dt / 1000) * this.speed * Math.PI * 2;
    if (this.phase > Math.PI * 2) this.phase -= Math.PI * 2;
  }

  /** Vertical offset for breathing sway */
  getOffsetY() {
    return Math.sin(this.phase) * this.amplitude;
  }

  /** Slight scale pulse for breathing */
  getScale() {
    return 1.0 + Math.sin(this.phase) * 0.003;
  }
}


// ─── Eva Avatar (Main Class) ──────────────────────────────────────────────────

class EvaAvatar {
  /**
   * @param {HTMLCanvasElement} canvas
   * @param {Object} config
   * @param {string} [config.spriteSheet]     — path to composite sprite sheet
   * @param {Object} [config.strips]          — { state: 'path/to/strip.png', ... }
   * @param {string} [config.lipSyncSheet]    — path to lip sync overlay strip
   * @param {Object} [config.stateConfig]     — override DEFAULT_STATES
   * @param {string} [config.portraitSheet]    — path to close-up portrait strip (optional)
   * @param {Object} [config.portraitStates]   — portrait state config (optional)
   * @param {Object} [config.lipSyncPosition] — { x, y, w, h } relative to canvas for lip overlay
   */
  constructor(canvas, config = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.config = config;
    this.stateConfig = config.stateConfig || DEFAULT_STATES;
    this.aliases = config.aliases || DEFAULT_ALIASES;

    // Components
    this.stateMachine = new AnimationStateMachine();
    this.lipSync = new LipSyncController();
    this.breathing = new IdleBreathing();

    // Asset storage
    this.strips = {};           // state name → SpriteStrip
    this.lipSyncStrip = null;   // SpriteStrip for mouth overlay
    this.portraitStrips = {};    // optional close-up portrait strips

    // Rendering state
    this.running = false;
    this.lastTime = 0;
    this.showPortrait = false;  // toggle between body and portrait view

    // Lip sync overlay position (relative to canvas, default center-face area)
    this.lipSyncPos = config.lipSyncPosition || null;

    // Current expression (for external queries)
    this.currentExpression = 'grounded';
  }

  /**
   * Load all sprite assets.
   * Call before start().
   */
  async init() {
    const stateNames = Object.keys(this.stateConfig);

    if (this.config.spriteSheet) {
      // Option A: Single composite sheet — slice into strips
      const sheet = await loadImage(this.config.spriteSheet);
      const rowHeight = Math.floor(sheet.height / stateNames.length);

      for (let i = 0; i < stateNames.length; i++) {
        const name = stateNames[i];
        const sc = this.stateConfig[name];

        // Create a canvas for this strip row
        const stripCanvas = document.createElement('canvas');
        const frameWidth = Math.floor(sheet.width / sc.frames);
        stripCanvas.width = frameWidth * sc.frames;
        stripCanvas.height = rowHeight;
        const stripCtx = stripCanvas.getContext('2d');
        stripCtx.drawImage(sheet, 0, i * rowHeight, sheet.width, rowHeight,
                           0, 0, sheet.width, rowHeight);

        // Create image from canvas
        const stripImg = new Image();
        stripImg.src = stripCanvas.toDataURL();
        await new Promise(r => { stripImg.onload = r; });

        this.strips[name] = new SpriteStrip(stripImg, sc.frames, sc.fps, sc.loop);
      }
    } else if (this.config.strips) {
      // Option B: Individual strip PNGs per state. A missing/unloadable strip
      // is non-fatal — we skip that state and keep going, so the avatar still
      // runs on whatever art IS present (and the host console never breaks just
      // because one PNG is absent during an incremental art rollout).
      for (const name of stateNames) {
        const src = this.config.strips[name];
        if (!src) continue;
        const sc = this.stateConfig[name];
        try {
          const img = await loadImage(src);
          this.strips[name] = new SpriteStrip(img, sc.frames, sc.fps, sc.loop);
        } catch (e) {
          console.warn(`[EvaAvatar] strip '${name}' unavailable (${src}) — skipping`);
        }
      }
    }

    // Load lip sync overlay strip (optional — silent if absent)
    if (this.config.lipSyncSheet) {
      try {
        const lipImg = await loadImage(this.config.lipSyncSheet);
        this.lipSyncStrip = new SpriteStrip(lipImg, LIP_SYNC_FRAMES, 30, true);
      } catch (e) {
        console.warn(`[EvaAvatar] lip sync strip unavailable — mouth overlay off`);
      }
    }

    // Load portrait strips (optional close-up view — each is best-effort)
    if (this.config.portraitStrips) {
      for (const [name, src] of Object.entries(this.config.portraitStrips)) {
        const sc = this.config.portraitStates?.[name] || this.stateConfig[name];
        if (!sc) continue;
        try {
          const img = await loadImage(src);
          this.portraitStrips[name] = new SpriteStrip(img, sc.frames, sc.fps, sc.loop);
        } catch (e) {
          console.warn(`[EvaAvatar] portrait '${name}' unavailable (${src}) — skipping`);
        }
      }
    }

    console.log(`[EvaAvatar] Loaded ${Object.keys(this.strips).length} states, ` +
                `lip sync: ${!!this.lipSyncStrip}, ` +
                `portrait: ${Object.keys(this.portraitStrips).length} states`);
  }

  /** Start the animation loop. */
  start() {
    if (this.running) return;
    this.running = true;
    this.lastTime = performance.now();
    this._loop(this.lastTime);
  }

  /** Stop the animation loop. */
  stop() {
    this.running = false;
  }

  /** @returns {boolean} whether any animation strip actually loaded. */
  hasStrips() {
    return Object.keys(this.strips).length > 0;
  }

  /**
   * Resolve a governance expression name onto a state that has a loaded strip.
   * Order: exact strip → configured alias → 'stable'/'grounded' → any loaded
   * strip. Returns null only when no strips loaded at all. This guarantees a
   * known spine expression (e.g. 'reflective') never silently no-ops.
   * @param {string} expression
   * @returns {string|null}
   */
  _resolveState(expression) {
    if (this.strips[expression]) return expression;
    const alias = this.aliases[expression];
    if (alias && this.strips[alias]) return alias;
    if (this.strips['stable']) return 'stable';
    if (this.strips['grounded']) return 'grounded';
    const loaded = Object.keys(this.strips);
    return loaded.length ? loaded[0] : null;
  }

  /**
   * Set the governance expression state.
   * Called when telemetry updates from generate().
   * @param {string} expression — one of the state names
   */
  setExpression(expression) {
    const resolved = this._resolveState(expression);
    if (!resolved) return;                 // no art loaded — nothing to drive
    this.currentExpression = expression;   // remember the true governance state
    this.stateMachine.setState(resolved, this.strips);
  }

  /**
   * Set lip sync amplitude from TTS audio analysis.
   * @param {number} amplitude — 0.0 (silent) to 1.0 (loud)
   */
  setMouthAmplitude(amplitude) {
    this.lipSync.setAmplitude(amplitude);
  }

  /** Toggle between full body and portrait (close-up) view. */
  togglePortrait(show) {
    this.showPortrait = show !== undefined ? show : !this.showPortrait;
  }

  // ── Render Loop ───────────────────────────────────────────────────────────

  _loop(timestamp) {
    if (!this.running) return;
    const dt = timestamp - this.lastTime;
    this.lastTime = timestamp;

    this._update(dt);
    this._render();

    requestAnimationFrame(t => this._loop(t));
  }

  _update(dt) {
    this.stateMachine.update(dt, this.strips);
    this.lipSync.update(dt);
    this.breathing.update(dt);
  }

  _render() {
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Get current animation snapshot
    const snapshot = this.stateMachine.update(0, this.strips);
    const activeStrips = this.showPortrait ? this.portraitStrips : this.strips;

    // Apply breathing transform
    const offsetY = this.breathing.getOffsetY();
    const scale = this.breathing.getScale();

    ctx.save();
    ctx.translate(w / 2, h / 2);
    ctx.scale(scale, scale);
    ctx.translate(-w / 2, -h / 2 + offsetY);

    // Draw previous state (fading out during crossfade)
    if (snapshot.previous && activeStrips[snapshot.previous.state]) {
      const prevStrip = activeStrips[snapshot.previous.state];
      const prevRect = prevStrip.getFrameRect(snapshot.previous.frame);
      ctx.globalAlpha = snapshot.previous.alpha;
      ctx.drawImage(prevStrip.image,
        prevRect.sx, prevRect.sy, prevRect.sw, prevRect.sh,
        0, 0, w, h);
    }

    // Draw current state
    if (activeStrips[snapshot.current.state]) {
      const strip = activeStrips[snapshot.current.state];
      const rect = strip.getFrameRect(snapshot.current.frame);
      ctx.globalAlpha = snapshot.current.alpha;
      ctx.drawImage(strip.image,
        rect.sx, rect.sy, rect.sw, rect.sh,
        0, 0, w, h);
    }

    ctx.globalAlpha = 1.0;
    ctx.restore();

    // Lip sync overlay (composited on top, no breathing transform)
    if (this.lipSyncStrip) {
      const mouthFrame = this.lipSync.currentFrame;
      if (mouthFrame > 0) {  // 0 = closed, don't draw
        const mRect = this.lipSyncStrip.getFrameRect(mouthFrame);
        const pos = this.lipSyncPos || {
          x: w * 0.35,
          y: h * 0.28,
          w: w * 0.30,
          h: h * 0.08,
        };
        ctx.drawImage(this.lipSyncStrip.image,
          mRect.sx, mRect.sy, mRect.sw, mRect.sh,
          pos.x, pos.y, pos.w, pos.h);
      }
    }
  }

  // ── Audio Analysis Helper ─────────────────────────────────────────────────

  /**
   * Connect to an audio source for automatic lip sync.
   * Uses Web Audio API to analyze TTS output amplitude.
   *
   * @param {HTMLAudioElement|MediaStream} source
   * @returns {function} disconnect callback
   */
  connectAudioSource(source) {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.7;

    let sourceNode;
    if (source instanceof HTMLAudioElement) {
      sourceNode = audioCtx.createMediaElementSource(source);
      sourceNode.connect(analyser);
      analyser.connect(audioCtx.destination);
    } else if (source instanceof MediaStream) {
      sourceNode = audioCtx.createMediaStreamSource(source);
      sourceNode.connect(analyser);
    }

    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    let running = true;

    const analyze = () => {
      if (!running) return;
      analyser.getByteFrequencyData(dataArray);

      // Compute RMS amplitude (0–1)
      let sum = 0;
      for (let i = 0; i < dataArray.length; i++) {
        const v = dataArray[i] / 255;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / dataArray.length);
      this.setMouthAmplitude(rms * 3);  // scale up for visibility

      requestAnimationFrame(analyze);
    };
    analyze();

    return () => {
      running = false;
      audioCtx.close();
    };
  }
}


// ─── Telemetry Bridge ─────────────────────────────────────────────────────────
// Connects the EvaAvatar to the gui_server.py telemetry polling.

class TelemetryBridge {
  /**
   * @param {EvaAvatar} avatar
   * @param {string} apiUrl — base URL of gui_server.py (e.g. 'http://localhost:8770')
   * @param {number} pollInterval — ms between state polls (default 500)
   */
  constructor(avatar, apiUrl, pollInterval = 500) {
    this.avatar = avatar;
    this.apiUrl = apiUrl.replace(/\/$/, '');
    this.pollInterval = pollInterval;
    this.polling = false;
    this._timer = null;
  }

  /** Start polling telemetry and driving avatar state. */
  start() {
    if (this.polling) return;
    this.polling = true;
    this._poll();
  }

  /** Stop polling. */
  stop() {
    this.polling = false;
    if (this._timer) clearTimeout(this._timer);
  }

  async _poll() {
    if (!this.polling) return;
    try {
      const res = await fetch(`${this.apiUrl}/api/state`);
      const state = await res.json();

      // Drive expression from latest turn's telemetry
      if (state.conversation && state.conversation.length > 0) {
        const last = state.conversation[state.conversation.length - 1];
        const expression = last.telemetry?.expression;
        if (expression) {
          this.avatar.setExpression(expression);
        }
      }
    } catch (e) {
      // Server not ready or connection lost — stay in current state
    }

    this._timer = setTimeout(() => this._poll(), this.pollInterval);
  }
}


// ─── Export ───────────────────────────────────────────────────────────────────

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { EvaAvatar, TelemetryBridge, SpriteStrip, DEFAULT_STATES, DEFAULT_ALIASES };
}
