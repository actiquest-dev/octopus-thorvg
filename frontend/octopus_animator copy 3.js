/**
 * OctopusAnimator
 * Supports:
 *  - Audio sync: {cmd:"audio_sync", t0, audio, duration, speaking}
 *  - Viseme-based lip sync: {cmd:"sync", emotion, duration, visemes:[...]}
 *  - Amplitude mouth: {cmd:"mouth", value:0..1, speaking:true|false}
 *  - End: {cmd:"end", emotion?}
 */

class OctopusAnimator {
    constructor(canvasOrId, opts = {}) {
        this.canvas = (typeof canvasOrId === "string") ? document.getElementById(canvasOrId) : canvasOrId;
        if (!this.canvas) throw new Error("Canvas not found");
        this.ctx = this.canvas.getContext("2d");
        this.opts = Object.assign({ visemeMinMs: 80, visemeMaxMs: 180, mouthFloor: 0.05, visemeLeadMs: 120 }, opts);

        // Avatar state
        this.state = {
            emotion: 'calm',
            mouthOpen: 0,        // 0-1 (rendered, combined)
            targetMouth: 0,      // smoothing target
            jawOpen: 0,          // 0-1 from amplitude (how open)
            targetJaw: 0,        // smoothing target for jaw
            eyeScale: 1,         // 1 = open, 0.1 = blink
            eyeBias: 1,          // persistent eye expression scale
            eyebrowY: 0,         // -1 down, 0 normal, 1 up
            armPhase: 0,         // wave animation phase
            armSpeed: 1,         // wave speed multiplier
            armAmplitude: 1.0,   // wave amplitude multiplier
            armOffsetY: 0,       // global vertical offset for arms
            armStyle: 'sway',
            speaking: false,
            gesture: null,
            lastGesture: null,
            lastGestureTs: 0,
            actionMode: null,
            actionStartTs: 0,
            actionUntilTs: 0,

            // Viseme playback
            visemeSeq: [],
            visemeIdx: 0,
            visemeStepMs: 120,
            visemeNextTs: 0,
            visemeActive: false,
            visemeEndTs: 0,
            pendingEnd: false,
            currentViseme: "REST",

            // Audio sync
            audioSyncT0: null,
            audioSyncDuration: null,
            jawSeq: [],
            jawIdx: 0,
            jawStepMs: 20,
            jawNextTs: 0,
            jawActive: false,
            jawScheduleTs: 0,
            audioBaseTs: 0,
            responseStartPlayheadS: 0,
            visemeProxySeq: [],
            visemeProxyIdx: 0,
            visemeProxyStepMs: 50,
            visemeProxyNextTs: 0,
            visemeProxyActive: false,
            visemeProxyScheduleTs: 0,
            _lastSyncDebugTs: 0,
            actionJawScale: 1,
            fx: []
        };

        this.armPhaseOffsets = Array.from({ length: 8 }, () => Math.random() * Math.PI * 2);

        // Keep base color stable; emotions drive facial features instead of tint.
        this.baseHeadColor = '#FF6B9D';

        // Start render loop
        this.lastTime = 0;
        this.render = this.render.bind(this);
        requestAnimationFrame(t => this.render(t));
    }

    visemeToOpen(v) {
        // Stronger, more visible mouth movement
        switch ((v || "REST").toUpperCase()) {
            case "REST": return this.opts.mouthFloor;
            case "A": return 1.0;
            case "E": return 0.65;
            case "I": return 0.40;
            case "O": return 0.90;
            case "U": return 0.75;
            case "F": return 0.30;
            case "L": return 0.50;
            default: return 0.35;
        }
    }

    /**
     * Handle avatar command from server
     */
    handleCommand(cmd) {
        const hasVisemes = Array.isArray(cmd?.visemes) || (cmd?.viseme_proxy && Array.isArray(cmd.viseme_proxy.values));
        console.log(`📥 handleCommand: cmd=${cmd?.cmd || 'null'}, hasVisemes=${hasVisemes}`);
        if (cmd && cmd.cmd === "action" && cmd.action) {
            const durationMs = Number(cmd.duration_ms) || 1400;
            this.activateAction(cmd.action, durationMs);
            this.triggerFxFromAction(cmd.action);
            if (!this.isModeAction(cmd.action)) {
                this.triggerGesture(cmd.action, { force: true });
            }
            return;
        }
        // === AUDIO SYNC → JAW OPEN (amplitude) ===
        // Server sends: {cmd:"audio_sync", amplitudes:[...], duration, speaking}
        if (cmd && cmd.cmd === "audio_sync") {
            // 🔥 Логирование для отладки
            if (window.__lipDebug) {
                console.log(`🔊 audio_sync received:`, {
                    start_s: cmd.start_s,
                    duration_s: cmd.duration_s,
                    hasJaw: cmd.jaw && Array.isArray(cmd.jaw.values),
                    jawLen: cmd.jaw?.values?.length || 0,
                    hasVisemeProxy: cmd.viseme_proxy && Array.isArray(cmd.viseme_proxy.values),
                    visemeLen: cmd.viseme_proxy?.values?.length || 0,
                });
            }
            this.state.speaking = cmd.speaking !== false;
            if (cmd.emotion && cmd.emotion.value) {
                this.setEmotion(cmd.emotion.value);
            }
            if (cmd.action && cmd.action !== "none") {
                const durationMs = Math.max(300, Math.round((cmd.duration_s || 0.4) * 1000));
                this.activateAction(cmd.action, durationMs);
                this.triggerFxFromAction(cmd.action);
                if (!this.isModeAction(cmd.action)) {
                    this.triggerGesture(cmd.action, { force: true });
                }
            }

            // New response start: reset scheduling so packets don't queue behind old tail.
            if (typeof cmd.start_s === "number" && cmd.start_s <= 0.001) {
                this.state.jawSeq = [];
                this.state.jawIdx = 0;
                this.state.jawActive = false;
                this.state.jawScheduleTs = 0;
                this.state.visemeProxySeq = [];
                this.state.visemeProxyIdx = 0;
                this.state.visemeProxyActive = false;
                this.state.visemeProxyScheduleTs = 0;
                this.state.pendingEnd = false;
            }

            const now = performance.now();
            let startTs = now;
            if (typeof cmd.start_s === "number" && typeof window.getAudioPlayheadS === "function") {
                const playhead = window.getAudioPlayheadS();
                if (cmd.start_s <= 0.001) {
                    this.state.responseStartPlayheadS = playhead;
                }
                const responsePlayhead = Math.max(0, playhead - this.state.responseStartPlayheadS);
                const deltaMs = (cmd.start_s - responsePlayhead) * 1000;
                startTs = now + deltaMs;
            }
            const scheduleTail = Math.max(this.state.jawScheduleTs || 0, this.state.visemeProxyScheduleTs || 0);
            if (scheduleTail > startTs) {
                startTs = scheduleTail;
            }

            // Jaw track (preferred)
            if (cmd.jaw && Array.isArray(cmd.jaw.values) && cmd.jaw.values.length) {
                if (window.__lipDebug) {
                    const vals = cmd.jaw.values;
                    const min = Math.min(...vals);
                    const max = Math.max(...vals);
                    console.log("🦷 jaw stats", { min, max, len: vals.length });
                }
                const step = Math.max(10, Number(cmd.jaw.step_ms || 20));
                let seq = cmd.jaw.values.slice();
                let seqDuration = seq.length * step;
                if (startTs < now && seq.length) {
                    const lagMs = now - startTs;
                    if (lagMs > seqDuration) {
                        startTs = now; // too late; play full packet now
                    } else {
                        const skip = Math.min(seq.length - 1, Math.floor(lagMs / step));
                        if (skip > 0) {
                            seq = seq.slice(skip);
                            startTs += skip * step;
                            seqDuration = seq.length * step;
                        }
                    }
                }
            const hasSeq = this.state.jawSeq.length > 0;
            if (hasSeq && step === this.state.jawStepMs) {
                this.state.jawSeq = this.state.jawSeq.concat(seq);
            } else {
                this.state.jawSeq = seq;
                this.state.jawStepMs = step;
                this.state.jawIdx = 0;
            }
                if (!this.state.jawActive) {
                    this.state.jawNextTs = startTs;
                }
                this.state.jawActive = true;
                this.state.jawScheduleTs = startTs + seqDuration;
                if (window.__lipDebug) {
                    console.log(
                        "🦷 jaw sync",
                        { step, len: seq.length, startTs: Math.round(this.state.jawNextTs), scheduleTs: Math.round(this.state.jawScheduleTs), t0_s: t0s }
                    );
                }
            } else if (Array.isArray(cmd.amplitudes) && cmd.amplitudes.length) {
                // Back-compat: amplitudes[] treated as jaw values
                let seq = cmd.amplitudes.slice();
                const step = 20;
                let seqDuration = seq.length * step;
                if (startTs < now && seq.length) {
                    const lagMs = now - startTs;
                    if (lagMs > seqDuration) {
                        startTs = now;
                    } else {
                        const skip = Math.min(seq.length - 1, Math.floor(lagMs / step));
                        if (skip > 0) {
                            seq = seq.slice(skip);
                            startTs += skip * step;
                            seqDuration = seq.length * step;
                        }
                    }
                }
            const hasSeq = this.state.jawSeq.length > 0;
            if (hasSeq) {
                this.state.jawSeq = this.state.jawSeq.concat(seq);
            } else {
                this.state.jawSeq = seq;
                this.state.jawStepMs = step;
                this.state.jawIdx = 0;
            }
                if (!this.state.jawActive) {
                    this.state.jawNextTs = startTs;
                }
                this.state.jawActive = true;
                this.state.jawScheduleTs = startTs + seqDuration;
                if (window.__lipDebug) {
                    console.log(
                        "🦷 jaw sync (legacy)",
                        { step, len: seq.length, startTs: Math.round(this.state.jawNextTs), scheduleTs: Math.round(this.state.jawScheduleTs), t0_s: t0s }
                    );
                }
            }

            // Proxy visemes (shape track)
            if (cmd.viseme_proxy && Array.isArray(cmd.viseme_proxy.values) && cmd.viseme_proxy.values.length) {
                if (window.__lipDebug) {
                    console.log(`👄 viseme_proxy: values=${cmd.viseme_proxy.values.length}, step_ms=${cmd.viseme_proxy.step_ms}`);
                }
                const step = Math.max(20, Number(cmd.viseme_proxy.step_ms || 50));
                let seq = cmd.viseme_proxy.values.slice();
                let seqDuration = seq.length * step;
                if (startTs < now && seq.length) {
                    const lagMs = now - startTs;
                    if (lagMs > seqDuration) {
                        startTs = now;
                    } else {
                        const skip = Math.min(seq.length - 1, Math.floor(lagMs / step));
                        if (skip > 0) {
                            seq = seq.slice(skip);
                            startTs += skip * step;
                            seqDuration = seq.length * step;
                        }
                    }
                }
                const hasSeq = this.state.visemeProxySeq.length > 0;
                if (hasSeq && step === this.state.visemeProxyStepMs) {
                    this.state.visemeProxySeq = this.state.visemeProxySeq.concat(seq);
                } else {
                    this.state.visemeProxySeq = seq;
                    this.state.visemeProxyStepMs = step;
                    this.state.visemeProxyIdx = 0;
                }
                if (!this.state.visemeProxyActive) {
                    this.state.visemeProxyNextTs = startTs;
                }
                this.state.visemeProxyActive = true;
                this.state.visemeProxyScheduleTs = startTs + seqDuration;
                if (window.__lipDebug) {
                    console.log(
                        "👄 viseme proxy",
                        { step, len: seq.length, startTs: Math.round(this.state.visemeProxyNextTs), scheduleTs: Math.round(this.state.visemeProxyScheduleTs), t0_s: t0s }
                    );
                }
            } else if (Array.isArray(cmd.proxyVisemes) && cmd.proxyVisemes.length) {
                // Back-compat
                let seq = cmd.proxyVisemes.slice();
                const step = 50;
                let seqDuration = seq.length * step;
                if (startTs < now && seq.length) {
                    const lagMs = now - startTs;
                    if (lagMs > seqDuration) {
                        startTs = now;
                    } else {
                        const skip = Math.min(seq.length - 1, Math.floor(lagMs / step));
                        if (skip > 0) {
                            seq = seq.slice(skip);
                            startTs += skip * step;
                            seqDuration = seq.length * step;
                        }
                    }
                }
            const hasSeq = this.state.visemeProxySeq.length > 0;
            if (hasSeq) {
                this.state.visemeProxySeq = this.state.visemeProxySeq.concat(seq);
            } else {
                this.state.visemeProxySeq = seq;
                this.state.visemeProxyStepMs = step;
                this.state.visemeProxyIdx = 0;
            }
                if (!this.state.visemeProxyActive) {
                    this.state.visemeProxyNextTs = startTs;
                }
                this.state.visemeProxyActive = true;
                this.state.visemeProxyScheduleTs = startTs + seqDuration;
                if (window.__lipDebug) {
                    console.log(
                        "👄 viseme proxy (legacy)",
                        { step, len: seq.length, startTs: Math.round(this.state.visemeProxyNextTs), scheduleTs: Math.round(this.state.visemeProxyScheduleTs), t0_s: t0s }
                    );
                }
            }
            
            // Faster arm wave when speaking
            this.state.armSpeed = 1.5;
            
            // Store for viseme timing
            this.state.audioSyncT0 = (typeof cmd.t0_s === "number") ? cmd.t0_s : cmd.t0;
            this.state.audioSyncDuration = (typeof cmd.duration_s === "number") ? cmd.duration_s :
                                           (typeof cmd.duration === "number") ? cmd.duration : 2.0;
            return;
        }

        // Viseme-based lip sync (preferred)
        // Server sends: {cmd:"sync", emotion, duration, visemes:[...]}
        if (cmd && (cmd.cmd === "sync" || cmd.cmd === "start") && Array.isArray(cmd.visemes) && cmd.visemes.length) {
            if (cmd.emotion) this.state.emotion = cmd.emotion;

            // Use duration from audio_sync if available, otherwise from command
            let totalMs;
            if (this.state.audioSyncDuration != null && this.state.audioSyncT0 != null) {
                totalMs = this.state.audioSyncDuration * 1000;
            } else if (typeof cmd.duration === "number" && cmd.duration > 0) {
                totalMs = cmd.duration * 1000;
            } else {
                totalMs = cmd.visemes.length * 120;
            }

            // step from duration
            const rawStep = totalMs / Math.max(1, cmd.visemes.length);
            this.state.visemeStepMs = Math.max(this.opts.visemeMinMs, Math.min(this.opts.visemeMaxMs, rawStep));

            // resample visemes to match duration-driven steps (prevents tail lag)
            const steps = Math.max(1, Math.round(totalMs / this.state.visemeStepMs));
            const src = cmd.visemes;
            const seq = [];
            for (let i = 0; i < steps; i++) {
                const idx = Math.min(src.length - 1, Math.floor((i / steps) * src.length));
                seq.push(src[idx]);
            }
            this.state.visemeSeq = seq;
            this.state.visemeIdx = 0;

            // Use t0 from audio_sync if available, otherwise from command
            const now = performance.now();

            // Start viseme animation immediately (no delay)
            this.state.visemeNextTs = now;
            this.state.visemeEndTs = now + Math.max(0, totalMs - 500);
            
            console.log(`🎬 SYNC setup: now=${now.toFixed(0)}, nextTs=${this.state.visemeNextTs.toFixed(0)}, endTs=${this.state.visemeEndTs.toFixed(0)}, totalMs=${totalMs.toFixed(0)}`);
            this.state.pendingEnd = false;
            this.state.visemeActive = true;
            this.state.speaking = true;

            // Kick mouth immediately
            this.state.currentViseme = this.state.visemeSeq[0];
            this.state.targetMouth = this.visemeToOpen(this.state.visemeSeq[0]);

            // Clear audio sync data after use
            this.state.audioSyncT0 = null;
            this.state.audioSyncDuration = null;

            console.log(`👄 Visemes: ${seq.length} frames, step=${this.state.visemeStepMs.toFixed(1)}ms`);
            return;
        }

        // Amplitude mouth (real-time from audio)
        if (cmd && cmd.cmd === 'mouth') {
            this.state.targetMouth = (typeof cmd.value === "number") ? cmd.value : 0;
            this.state.speaking = cmd.speaking !== false;

            if (this.state.speaking) this.state.armSpeed = 1.5;
        }

        // End of speech
        if (cmd && cmd.cmd === 'end') {
            if (this.state.jawActive || this.state.visemeProxyActive || this.state.visemeActive) {
                this.state.pendingEnd = true;
                return;
            }
            console.log(`⏹️ END: closing mouth`);
            this.state.targetMouth = 0;
            this.state.targetJaw = 0;  // Close jaw
            this.state.speaking = false;
            this.state.armSpeed = 1;
            this.state.visemeActive = false;
            this.state.visemeProxyActive = false;
            this.state.jawActive = false;
            this.state.pendingEnd = false;
            if (cmd.emotion) this.setEmotion(cmd.emotion);
            return;
        }

        // Set emotion directly
        if (cmd && cmd.emotion && (!cmd.cmd || cmd.cmd === "emotion")) {
            this.setEmotion(cmd.emotion);
        }
    }

    setEmotion(emotion) {
        const e = (emotion || 'calm');
        this.state.emotion = e;

        // Eyebrow position
        if (e === 'sad' || e === 'angry' || e === 'tender') {
            this.state.eyebrowY = -1.2;
        } else if (e === 'curious') {
            this.state.eyebrowY = 1.35;
        } else if (e === 'confused') {
            this.state.eyebrowY = 0.6;
        } else if (e === 'excited' || e === 'playful' || e === 'happy') {
            this.state.eyebrowY = 0.8;
        } else if (e === 'proud') {
            this.state.eyebrowY = 0.9;
        } else if (e === 'sarcastic') {
            this.state.eyebrowY = 0.4;
        } else {
            this.state.eyebrowY = 0;
        }

        // Eye size bias per emotion
        if (e === 'angry') {
            this.state.eyeBias = 0.82;
        } else if (e === 'sad' || e === 'tender') {
            this.state.eyeBias = 0.88;
        } else if (e === 'excited' || e === 'playful' || e === 'happy') {
            this.state.eyeBias = 1.1;
        } else if (e === 'curious' || e === 'confused') {
            this.state.eyeBias = 1.15;
        } else if (e === 'proud') {
            this.state.eyeBias = 1.05;
        } else if (e === 'sarcastic') {
            this.state.eyeBias = 0.96;
        } else {
            this.state.eyeBias = 1;
        }

        // Arm style per emotion
        if (e === 'excited' || e === 'playful' || e === 'happy') {
            this.state.armStyle = 'flutter';
            this.state.armSpeed = 2.4;
            this.state.armAmplitude = 2.2;
            this.state.armOffsetY = 0;
        } else if (e === 'sad' || e === 'tender') {
            this.state.armStyle = 'droop';
            this.state.armSpeed = 0.6;
            this.state.armAmplitude = 0.7;
            this.state.armOffsetY = 14;
        } else if (e === 'angry') {
            this.state.armStyle = 'lash';
            this.state.armSpeed = 2.8;
            this.state.armAmplitude = 1.8;
            this.state.armOffsetY = 0;
        } else if (e === 'proud') {
            this.state.armStyle = 'sway';
            this.state.armSpeed = 1.2;
            this.state.armAmplitude = 1.6;
            this.state.armOffsetY = -6;
        } else if (e === 'sarcastic') {
            this.state.armStyle = 'probe';
            this.state.armSpeed = 0.9;
            this.state.armAmplitude = 0.9;
            this.state.armOffsetY = 4;
        } else if (e === 'curious') {
            this.state.armStyle = 'probe';
            this.state.armSpeed = 1.6;
            this.state.armAmplitude = 1.7;
            this.state.armOffsetY = -2;
        } else if (e === 'confused') {
            this.state.armStyle = 'probe';
            this.state.armSpeed = 0.9;
            this.state.armAmplitude = 1.1;
            this.state.armOffsetY = 2;
        } else if (e === 'calm') {
            this.state.armStyle = 'sway';
            this.state.armSpeed = 0.8;
            this.state.armAmplitude = 0.9;
            this.state.armOffsetY = 0;
        } else {
            this.state.armStyle = 'sway';
            this.state.armSpeed = 1.0;
            this.state.armAmplitude = 1.2;
            this.state.armOffsetY = 0;
        }

        console.log(`😊 Emotion set to "${e}": eyebrowY=${this.state.eyebrowY}, eyeBias=${this.state.eyeBias}, armStyle="${this.state.armStyle}", armSpeed=${this.state.armSpeed}, armAmplitude=${this.state.armAmplitude}`);
        this.maybeTriggerGestureFromEmotion(e);
    }

    maybeTriggerGestureFromEmotion(emotion) {
        const now = performance.now();
        if (now - this.state.lastGestureTs < 15000) return;
        const map = {
            happy: { name: 'wave', p: 0.2 },
            excited: { name: 'clap', p: 0.1 },
            playful: { name: 'wave', p: 0.2 },
            tender: { name: 'heart', p: 0.1 },
            sad: { name: 'hug', p: 0.08 },
            curious: { name: 'point', p: 0.15 },
            confused: { name: 'shrug', p: 0.12 }
        };
        const choice = map[emotion];
        if (!choice) return;
        if (Math.random() < choice.p) {
            this.triggerGesture(choice.name, { force: false });
        }
    }

    spawnFx(type, opts = {}) {
        const now = performance.now();
        const cx = this.canvas.width / 2;
        const cy = this.canvas.height * 0.4;
        const fx = {
            type,
            startTs: now,
            durationMs: opts.durationMs || 1200,
            x: (opts.x != null) ? opts.x : cx,
            y: (opts.y != null) ? opts.y : cy,
            vx: opts.vx || 0,
            vy: opts.vy || 0,
            size: opts.size || 8,
            count: opts.count || 1
        };
        this.state.fx.push(fx);
    }

    clearFx(types) {
        if (!types) return;
        const set = new Set(types);
        this.state.fx = this.state.fx.filter((f) => !set.has(f.type));
    }

    triggerFxFromAction(action) {
        if (!action) return;
        if (action === 'sfx_tear') {
            this.spawnFx('tear', { x: this.canvas.width / 2 - 18, y: this.canvas.height * 0.4 - 2, vy: 55, durationMs: 1600, size: 7 });
        } else if (action === 'sfx_sweat') {
            this.spawnFx('sweat', { x: this.canvas.width / 2 + 12, y: this.canvas.height * 0.4 - 32, vy: 38, durationMs: 1300, size: 6 });
        } else if (action === 'sfx_heart' || action === 'heart') {
            this.spawnFx('heart', { x: this.canvas.width / 2, y: this.canvas.height * 0.4 - 70, vy: -28, durationMs: 1600, size: 14, count: 3 });
        } else if (action === 'sfx_sparkle') {
            // Sparkles burst out in different directions
            const cx = this.canvas.width / 2;
            const cy = this.canvas.height * 0.4 - 85;
            for (let i = 0; i < 6; i++) {
                const angle = (i / 6) * Math.PI * 2;
                const speed = 80;
                this.spawnFx('sparkle', {
                    x: cx,
                    y: cy,
                    vx: Math.cos(angle) * speed,
                    vy: Math.sin(angle) * speed,
                    durationMs: 1100,
                    size: 10,
                    count: 1
                });
            }
        } else if (action === 'sfx_pop') {
            this.spawnFx('pop', { x: this.canvas.width / 2, y: this.canvas.height * 0.4 - 60, durationMs: 700, size: 18 });
        } else if (action === 'sfx_boop') {
            this.spawnFx('pop', { x: this.canvas.width / 2, y: this.canvas.height * 0.4 - 5, durationMs: 600, size: 12 });
        } else if (action === 'sfx_bubble') {
            this.spawnFx('bubble', { x: this.canvas.width / 2 + 10, y: this.canvas.height * 0.4 + 22, vy: -30, durationMs: 1500, size: 9, count: 4 });
        } else if (action === 'sfx_wave') {
            this.spawnFx('bubble', { x: this.canvas.width / 2 - 8, y: this.canvas.height * 0.4 + 28, vy: -22, durationMs: 1400, size: 8, count: 5 });
        } else if (action === 'photobooth') {
            // Flash happens at the end of the camera animation (800ms delay), lasts 600ms
            setTimeout(() => {
                this.spawnFx('flash', { durationMs: 600 });
            }, 800);
        } else if (action === 'wipe') {
            this.clearFx(['tear', 'sweat']);
        }
    }

    triggerGesture(name, { force } = {}) {
        const now = performance.now();
        if (!force && now - this.state.lastGestureTs < 10000) return;
        if (!force && this.state.lastGesture === name) return;

        const durationMap = {
            heart: 1800,
            wave: 1400,
            clap: 1200,
            point: 1200,
            hug: 1600,
            shrug: 1000,
            sing: 1600,
            laugh: 1200,
            whisper: 900,
            shout: 900,
            wipe: 900,
            sfx_pop: 700,
            sfx_sparkle: 900,
            sfx_boop: 700,
            sfx_wave: 900,
            sfx_spin: 1400,
            sfx_tear: 800,
            sfx_sweat: 800,
            sfx_heart: 1000,
            sfx_bubble: 1200,
            photobooth: 1200
        };

        this.state.gesture = {
            name,
            startTs: now,
            durationMs: durationMap[name] || 1200,
            armIdx: Math.floor(Math.random() * 8)
        };
        this.state.lastGesture = name;
        this.state.lastGestureTs = now;
    }

    isModeAction(name) {
        return name === 'sing' || name === 'laugh' || name === 'whisper' || name === 'shout' || name === 'sfx_spin';
    }

    activateAction(name, durationMs) {
        const now = performance.now();
        this.state.actionMode = name;
        this.state.actionStartTs = now;
        this.state.actionUntilTs = now + (Number.isFinite(durationMs) ? durationMs : 1400);
    }

    blink() {
        // Quick blink animation
        const start = performance.now();
        const duration = 120;

        const animateBlink = (t) => {
            const p = Math.min(1, (t - start) / duration);
            // 1 -> 0.1 -> 1
            const s = (p < 0.5)
                ? (1 - (p / 0.5) * 0.9)
                : (0.1 + ((p - 0.5) / 0.5) * 0.9);

            this.state.eyeScale = s;

            if (p < 1) requestAnimationFrame(animateBlink);
            else this.state.eyeScale = 1;
        };

        requestAnimationFrame(animateBlink);
    }

    render(timestamp) {
        const dt = (timestamp - this.lastTime) / 1000;
        this.lastTime = timestamp;

        // DEBUG: Log viseme state once per animation
        if (this.state.visemeActive && !this.state._debugLogged) {
            console.log(`🔄 Viseme render: ts=${timestamp.toFixed(0)}, nextTs=${this.state.visemeNextTs.toFixed(0)}, delta=${(this.state.visemeNextTs - timestamp).toFixed(0)}ms, idx=${this.state.visemeIdx}/${this.state.visemeSeq.length}`);
            this.state._debugLogged = true;
        }

        // Advance viseme timeline (if active)
        if (this.state.visemeActive && this.state.visemeSeq.length) {
            if (!this.state._renderDebugLogged) {
                console.log(`🎬 Viseme active: seq=${this.state.visemeSeq.length}, nextTs=${this.state.visemeNextTs.toFixed(0)}, ts=${timestamp.toFixed(0)}`);
                this.state._renderDebugLogged = true;
            }
            if (timestamp >= this.state.visemeNextTs && this.state.visemeIdx < this.state.visemeSeq.length) {
                console.log(`➡️ Step: idx=${this.state.visemeIdx}, v=${this.state.visemeSeq[this.state.visemeIdx]}, nextTs=${this.state.visemeNextTs.toFixed(0)}`);
                const v = this.state.visemeSeq[this.state.visemeIdx];
                this.state.currentViseme = v;
                this.state.targetMouth = this.visemeToOpen(v);
                this.state.visemeIdx += 1;
                this.state.visemeNextTs += this.state.visemeStepMs;
            }
            // Finish sequence
            if (this.state.visemeIdx >= this.state.visemeSeq.length) {
                console.log(`🛑 Sequence finished: idx=${this.state.visemeIdx}/${this.state.visemeSeq.length}`);
                this.state.visemeActive = false;
                this.state.speaking = false;
                this.state.targetMouth = this.opts.mouthFloor;
            }
        }

        // Advance jaw timeline (audio_sync)
        if (this.state.jawActive && this.state.jawSeq.length) {
            if (timestamp >= this.state.jawNextTs && this.state.jawIdx < this.state.jawSeq.length) {
                const j = this.state.jawSeq[this.state.jawIdx];
                this.state.targetJaw = Math.max(0, Math.min(1, j));
                this.state.jawIdx += 1;
                this.state.jawNextTs += this.state.jawStepMs;
            }
            if (this.state.jawIdx >= this.state.jawSeq.length) {
                this.state.jawActive = false;
                this.state.targetJaw = 0;
                this.state.jawSeq = [];
                if (!this.state.visemeActive) {
                    this.state.speaking = false;
                }
                if (this.state.pendingEnd && !this.state.visemeActive && !this.state.visemeProxyActive) {
                    this.state.targetMouth = 0;
                    this.state.speaking = false;
                    this.state.armSpeed = 1;
                    this.state.pendingEnd = false;
                }
            }
        }

        // Advance proxy viseme timeline (shape)
        if (this.state.visemeProxyActive && this.state.visemeProxySeq.length) {
            if (timestamp >= this.state.visemeProxyNextTs && this.state.visemeProxyIdx < this.state.visemeProxySeq.length) {
                const v = this.state.visemeProxySeq[this.state.visemeProxyIdx];
                this.state.currentViseme = v;
                this.state.targetMouth = this.visemeToOpen(v);
                this.state.visemeProxyIdx += 1;
                this.state.visemeProxyNextTs += this.state.visemeProxyStepMs;
            }
            if (this.state.visemeProxyIdx >= this.state.visemeProxySeq.length) {
                this.state.visemeProxyActive = false;
                this.state.visemeProxySeq = [];
                if (this.state.pendingEnd && !this.state.visemeActive && !this.state.jawActive) {
                    this.state.targetMouth = 0;
                    this.state.speaking = false;
                    this.state.armSpeed = 1;
                    this.state.pendingEnd = false;
                }
            }
        }

        if (window.__lipDebug && this.state.speaking) {
            const now = performance.now();
            if (now - this.state._lastSyncDebugTs > 500) {
                this.state._lastSyncDebugTs = now;
                console.log("🧭 lip state", {
                    jawActive: this.state.jawActive,
                    jawIdx: this.state.jawIdx,
                    jawLen: this.state.jawSeq.length,
                    jawNextTs: Math.round(this.state.jawNextTs),
                    visemeActive: this.state.visemeProxyActive,
                    visemeIdx: this.state.visemeProxyIdx,
                    visemeLen: this.state.visemeProxySeq.length,
                    visemeNextTs: Math.round(this.state.visemeProxyNextTs),
                });
            }
        }

        // Завершение viseme по времени (и отложенный end)
        if (this.state.visemeActive && performance.now() >= this.state.visemeEndTs) {
            this.state.visemeActive = false;
            if (this.state.pendingEnd) {
                this.state.targetMouth = 0;
                this.state.speaking = false;
                this.state.armSpeed = 1;
                this.state.pendingEnd = false;
            }
        }

        const now = performance.now();
        const actionActive = this.state.actionMode && now < this.state.actionUntilTs;

        // Clear photobooth effects when action ends
        if (!actionActive && this.state._photoBooth_eyeLookDown) {
            this.state._photoBooth_eyeLookDown = 0;
        }

        // Target face state - will be set by actions or keep emotion defaults
        let targetEyebrowY = this.state.eyebrowY;
        let targetEyeBias = this.state.eyeBias;

        let mouthBias = 0;
        let jawScale = 1;
        let armStyle = this.state.armStyle;
        let armSpeed = this.state.armSpeed;
        let armAmplitude = this.state.armAmplitude;
        let armOffsetY = this.state.armOffsetY;
        let bodyBob = 0;
        let shakeX = 0;
        let bodyRotation = 0;

        if (actionActive) {
            const action = this.state.actionMode;
            const t = (now - this.state.actionStartTs) / 1000;
            if (action === 'sing') {
                armStyle = 'sway';
                armSpeed = 2.0;
                armAmplitude = 2.0;
                mouthBias = 0.14;
                jawScale = 1.15;
                bodyBob = Math.sin(t * 6) * 3;
                shakeX = Math.sin(t * 3) * 8;  // Left-right sway
                targetEyebrowY = 0.5;
                targetEyeBias = 1.12;
            } else if (action === 'laugh') {
                armStyle = 'flutter';
                armSpeed = 2.8;
                armAmplitude = 2.4;
                mouthBias = 0.16;
                jawScale = 1.25;
                bodyBob = Math.sin(t * 10) * 4;
                targetEyebrowY = 0.6;
                targetEyeBias = 1.15;
            } else if (action === 'whisper') {
                armStyle = 'droop';
                armSpeed = 0.7;
                armAmplitude = 0.5;
                mouthBias = -0.12;
                jawScale = 0.7;
                bodyBob = Math.sin(t * 4) * 1;
                targetEyebrowY = -0.3;
                targetEyeBias = 0.9;
            } else if (action === 'shout') {
                armStyle = 'lash';
                armSpeed = 3.0;
                armAmplitude = 2.6;
                mouthBias = 0.24;
                jawScale = 1.35;
                bodyBob = Math.sin(t * 8) * 2;
                shakeX = Math.sin(t * 20) * 2;
                targetEyebrowY = 0.7;
                targetEyeBias = 1.2;
            } else if (action === 'wave' || action === 'clap' || action === 'point' || action === 'hug' || action === 'shrug') {
                armSpeed = Math.max(armSpeed, 2.0);
                armAmplitude *= 1.8;
                bodyBob = Math.sin(t * 6) * 2;
                // Happy smile for gestures
                mouthBias = 0.12;
                jawScale = 1.12;
                targetEyebrowY = 0.4;
                targetEyeBias = 1.1;
            } else if (action === 'sfx_spin') {
                armStyle = 'flutter';
                armSpeed = 3.5;
                armAmplitude = 2.5;
                bodyBob = Math.sin(t * 15) * 3;
                bodyRotation = t * Math.PI * 4;
                // Happy spin smile
                mouthBias = 0.15;
                jawScale = 1.18;
                targetEyebrowY = 0.5;
                targetEyeBias = 1.12;
            } else if (action === 'photobooth') {
                // Big smile for photo! до ушей - широкая улыбка при ЗАКРЫТОМ рте + взгляд вниз
                mouthBias = 0;  // Рот закрыт (jawOpen = 0)
                jawScale = 1.6;
                targetEyebrowY = 0.3;  // Slightly raised brows
                targetEyeBias = 1.15;   // Eyes open wider
                // Eyes look down - negative pupil offset
                this.state._photoBooth_eyeLookDown = 0.6;
            } else if (action === 'sfx_tear') {
                // Sad tear - droopy face
                mouthBias = -0.08;
                jawScale = 1.05;
                targetEyebrowY = -0.6;
                targetEyeBias = 0.92;
            } else if (action === 'sfx_sweat') {
                // Nervous sweat - tired/exhausted expression with "roof" eyebrows
                mouthBias = 0.03;  // Neutral almost mouth
                jawScale = 1.06;
                targetEyebrowY = -0.8;  // Lowered brows (домик - roof/V shape pointing down - exhausted)
                targetEyeBias = 0.90;  // More squinted eyes
            } else if (action === 'sfx_heart') {
                // Love heart - happy open eyes
                mouthBias = 0.12;
                jawScale = 1.1;
                targetEyebrowY = 0.5;
                targetEyeBias = 1.16;
            } else if (action === 'sfx_sparkle') {
                // Sparkle - amazed/wonder
                mouthBias = 0.08;
                jawScale = 1.12;
                targetEyebrowY = 0.7;
                targetEyeBias = 1.2;
            } else if (action === 'sfx_pop') {
                // Pop - surprise
                mouthBias = 0.18;
                jawScale = 1.3;
                targetEyebrowY = 0.8;
                targetEyeBias = 1.22;
            } else if (action === 'sfx_boop') {
                // Boop - playful
                mouthBias = 0.14;
                jawScale = 1.15;
                targetEyebrowY = 0.5;
                targetEyeBias = 1.12;
            } else if (action === 'sfx_wave') {
                // Wave - friendly
                mouthBias = 0.1;
                jawScale = 1.1;
                targetEyebrowY = 0.3;
                targetEyeBias = 1.08;
            } else if (action === 'sfx_bubble') {
                // Bubble - playful wonder
                mouthBias = 0.11;
                jawScale = 1.11;
                targetEyebrowY = 0.4;
                targetEyeBias = 1.1;
            }
        }

        // Smooth animation of face expression (eyebrows and eyes)
        const faceSmoothing = 0.15;  // Smooth transition speed
        this.state.eyebrowY += (targetEyebrowY - this.state.eyebrowY) * faceSmoothing;
        this.state.eyeBias += (targetEyeBias - this.state.eyeBias) * faceSmoothing;

        // Smooth mouth movement (viseme shape)
        const smoothing = this.state.speaking ? 0.55 : 0.25;
        this.state.actionJawScale = jawScale;
        // For actions: use mouthBias directly if actionActive, otherwise use targetMouth from speech
        const targetMouth = Math.max(0, Math.min(1, actionActive ? mouthBias : this.state.targetMouth));
        this.state.mouthOpen += (targetMouth - this.state.mouthOpen) * smoothing;

        // Smooth jaw movement (amplitude = how open) - FASTER for real-time sync
        // For actions: jaw is driven by mouthBias; for speech: jaw is from audio
        const jawSmooth = this.state.speaking ? 0.6 : 0.3;
        const targetJaw = actionActive ? Math.max(0, mouthBias) : this.state.targetJaw;
        this.state.jawOpen += (targetJaw - this.state.jawOpen) * jawSmooth;

        // Update arm wave
        this.state.armPhase += dt * armSpeed * 3;

        // Random blink
        if (Math.random() < 0.003) this.blink();

        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;
        const cx = w / 2 + shakeX;
        const cy = h * 0.4 + bodyBob;

        ctx.clearRect(0, 0, w, h);

        const headColor = this.baseHeadColor;

        // Apply body rotation if needed
        if (bodyRotation !== 0) {
            ctx.save();
            ctx.translate(cx, cy);
            ctx.rotate(bodyRotation);
            ctx.translate(-cx, -cy);
        }

        // Draw arms
        this.drawArms(cx, cy + 35, headColor, { armStyle, armAmplitude, armOffsetY, actionMode: this.state.actionMode, actionActive });

        // Draw head
        ctx.beginPath();
        ctx.arc(cx, cy, 55, 0, Math.PI * 2);
        ctx.fillStyle = headColor;
        ctx.fill();
        ctx.lineWidth = 4;
        ctx.strokeStyle = '#FF1493';
        ctx.stroke();

        // Eyebrows
        this.drawEyebrows(cx, cy - 30);

        // Eyes
        this.drawEyes(cx, cy - 10);

        // Mouth
        this.drawMouthViseme(cx, cy + 30);

        // Camera (for photobooth gesture)
        this.drawCamera(cx, cy);

        // Restore rotation
        if (bodyRotation !== 0) {
            ctx.restore();
        }

        // Draw camera flash first (in front of everything)
        this.drawFlash();

        // Draw effects (tears, sparkles, etc.) - after rotation restore so they're always visible
        this.drawFx(cx, cy);

        requestAnimationFrame(t => this.render(t));
    }

    drawMouthViseme(cx, cy) {
        const ctx = this.ctx;
        const v = (this.state.currentViseme || "REST").toUpperCase();
        
        // jawOpen from amplitude (0-1) - HOW OPEN
        const jaw = Math.max(0, Math.min(1, this.state.jawOpen));
        
        // Debug
        if (this.state.speaking && Math.random() < 0.05) {
            console.log(`🎨 Draw mouth: jaw=${jaw.toFixed(2)}, viseme=${v}`);
        }

        ctx.save();
        ctx.translate(cx, cy);

        // Viseme determines WIDTH and shape style
        let mouthWidth = 30;
        let roundness = 0.5; // 0 = wide flat, 1 = round
        let showTeeth = false;
        let showTongue = false;

        switch (v) {
            case "M": case "B": case "P":
                mouthWidth = 28; roundness = 0.3; break;
            case "REST":
                mouthWidth = 26; roundness = 0.4; break;
            case "A":
                mouthWidth = 38; roundness = 0.6; break;  // Wide open
            case "O":
                mouthWidth = 26; roundness = 1.0; break;  // Round
            case "U":
                mouthWidth = 20; roundness = 1.0; break;  // Small round
            case "E":
                mouthWidth = 42; roundness = 0.3; break;  // Wide flat
            case "I":
                mouthWidth = 44; roundness = 0.2; break;  // Very wide
            case "F": case "V":
                mouthWidth = 36; roundness = 0.4; showTeeth = true; break;
            case "L":
                mouthWidth = 34; roundness = 0.5; showTongue = true; break;
            case "S": case "Z":
                mouthWidth = 32; roundness = 0.3; break;
            default:
                mouthWidth = 32; roundness = 0.5; break;
        }

        // Jaw controls HEIGHT (how open)
        // Scale up for visibility: jaw 0.1 should already show open mouth
        const openScale = Math.pow(jaw, 0.7); // More responsive at low values
        const mouthHeight = 4 + openScale * 28; // 4px closed, up to 32px open
        
        const hw = mouthWidth / 2;
        const hh = mouthHeight / 2;

        // CLOSED MOUTH (jaw < 0.05)
        if (jaw < 0.05) {
            // Simple curved line (smile or neutral based on emotion or action)
            let smileAmount = 0;

            // Check if photobooth action is active - HUGE smile!
            const now = performance.now();
            const isPhotobooth = this.state.actionMode === 'photobooth' &&
                                this.state.actionUntilTs &&
                                now < this.state.actionUntilTs;

            // Check if sfx_tear action is active - SAD frown!
            const isSadTear = this.state.actionMode === 'sfx_tear' &&
                             this.state.actionUntilTs &&
                             now < this.state.actionUntilTs;

            if (isPhotobooth) {
                smileAmount = 14;  // ОЧЕНЬ широкая улыбка! (до ушей)
            } else if (isSadTear) {
                smileAmount = -4;  // Грустная гримаса - перевёрнутый рот
            } else if (this.state.emotion === 'happy' || this.state.emotion === 'excited' || this.state.emotion === 'playful' || this.state.emotion === 'proud') {
                smileAmount = 4;
            } else if (this.state.emotion === 'sad' || this.state.emotion === 'angry') {
                smileAmount = -3;
            }

            ctx.strokeStyle = "#2D0F1A";
            ctx.lineWidth = 4;
            ctx.lineCap = "round";
            ctx.beginPath();
            ctx.moveTo(-hw, 0);
            ctx.quadraticCurveTo(0, smileAmount, hw, 0);
            ctx.stroke();
            ctx.restore();
            return;
        }

        // OPEN MOUTH
        
        // Mouth interior (dark)
        ctx.fillStyle = "#1a0a10";
        ctx.beginPath();
        if (roundness > 0.7) {
            // Round mouth (O, U)
            ctx.ellipse(0, 0, hw * 0.9, hh, 0, 0, Math.PI * 2);
        } else {
            // Wide mouth - rounded rectangle shape
            const r = hh * roundness;
            ctx.moveTo(-hw + r, -hh);
            ctx.lineTo(hw - r, -hh);
            ctx.quadraticCurveTo(hw, -hh, hw, -hh + r);
            ctx.lineTo(hw, hh - r);
            ctx.quadraticCurveTo(hw, hh, hw - r, hh);
            ctx.lineTo(-hw + r, hh);
            ctx.quadraticCurveTo(-hw, hh, -hw, hh - r);
            ctx.lineTo(-hw, -hh + r);
            ctx.quadraticCurveTo(-hw, -hh, -hw + r, -hh);
        }
        ctx.fill();

        // Upper lip
        ctx.strokeStyle = "#2D0F1A";
        ctx.lineWidth = 4;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(-hw, 0);
        ctx.quadraticCurveTo(-hw * 0.5, -hh - 2, 0, -hh);
        ctx.quadraticCurveTo(hw * 0.5, -hh - 2, hw, 0);
        ctx.stroke();

        // Lower lip (moves down with jaw)
        ctx.beginPath();
        ctx.moveTo(-hw, 0);
        ctx.quadraticCurveTo(-hw * 0.5, hh + 2, 0, hh);
        ctx.quadraticCurveTo(hw * 0.5, hh + 2, hw, 0);
        ctx.stroke();

        // Teeth (for F, V)
        if (showTeeth && mouthHeight > 8) {
            ctx.fillStyle = "#fff";
            ctx.fillRect(-hw * 0.6, -hh + 2, hw * 1.2, Math.min(6, hh * 0.4));
        }

        // Tongue (for L)
        if (showTongue && mouthHeight > 10) {
            ctx.fillStyle = "#ff6b9d";
            ctx.beginPath();
            ctx.ellipse(0, hh * 0.3, hw * 0.4, hh * 0.35, 0, 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.restore();
    }

    drawArms(cx, cy, color, overrides = null) {
        const ctx = this.ctx;
        ctx.strokeStyle = color;
        ctx.lineWidth = 10;
        ctx.lineCap = 'round';

        const baseR = 70;
        const now = performance.now();
        const armStyle = overrides?.armStyle || this.state.armStyle;
        const armAmplitude = (overrides?.armAmplitude != null) ? overrides.armAmplitude : this.state.armAmplitude;
        const armOffsetY = (overrides?.armOffsetY != null) ? overrides.armOffsetY : this.state.armOffsetY;
        let gesture = this.state.gesture;
        if (gesture && now - gesture.startTs > gesture.durationMs) {
            this.state.gesture = null;
            gesture = null;
        }
        const gPhase = gesture ? Math.min(1, (now - gesture.startTs) / gesture.durationMs) : 0;

        for (let i = 0; i < 8; i++) {
            const a = (i / 8) * Math.PI * 2;
            let wobble = Math.sin(this.state.armPhase + i * 0.7) * 14;
            const phase = this.state.armPhase + this.armPhaseOffsets[i];

            if (armStyle === 'flutter') {
                wobble += Math.sin(phase * 2.5) * 6;
            } else if (armStyle === 'lash') {
                const saw = ((phase % (Math.PI * 2)) / Math.PI) - 1;
                wobble = saw * 16;
            } else if (armStyle === 'probe') {
                wobble += Math.sin(phase * 1.7 + i) * 8;
            }

            wobble *= armAmplitude;

            const x1 = cx + Math.cos(a) * 35;
            const y1 = cy + Math.sin(a) * 35 + armOffsetY;

            const x2 = cx + Math.cos(a) * (baseR + 10);
            const y2 = cy + Math.sin(a) * (baseR + 10) + armOffsetY;

            const x3 = cx + Math.cos(a) * (baseR + 55);
            const y3 = cy + Math.sin(a) * (baseR + 55) + armOffsetY;

            const ctrlx = (x1 + x3) / 2 + wobble;
            let ctrly = (y1 + y3) / 2 + wobble;
            let endx = x3;
            let endy = y3;

            if (gesture) {
                if (gesture.name === 'wave' && i === gesture.armIdx) {
                    ctrly -= 22 * Math.sin(gPhase * Math.PI);
                    endy -= 10 * Math.sin(gPhase * Math.PI);
                } else if (gesture.name === 'point' && i === gesture.armIdx) {
                    endx = cx + Math.cos(a) * (baseR + 80);
                    endy = cy + Math.sin(a) * (baseR + 80);
                } else if (gesture.name === 'clap' && (i === 0 || i === 7)) {
                    endx = cx + (i === 0 ? 10 : -10);
                    endy = cy + 30;
                } else if (gesture.name === 'heart' && (i === 0 || i === 7)) {
                    endx = cx + (i === 0 ? 14 : -14);
                    endy = cy + 18;
                    ctrly -= 14;
                } else if (gesture.name === 'hug') {
                    endx = cx + Math.cos(a) * (baseR + 12);
                    endy = cy + Math.sin(a) * (baseR + 12) + 12;
                } else if (gesture.name === 'shrug' && (i === 2 || i === 5)) {
                    ctrly -= 18;
                } else if (gesture.name === 'wipe' && i === gesture.armIdx) {
                    const sweep = Math.sin(gPhase * Math.PI);
                    endx = cx + (sweep * 28);
                    endy = cy - 6;
                    ctrly -= 10;
                } else if (gesture.name === 'photobooth' && (i === 3 || i === 5)) {
                    // Hold camera - arms from bottom sides hold it below face, in front
                    // Arm 3 (bottom-left) and 5 (bottom-right) converge to hold camera down
                    if (i === 3) {
                        // Bottom-left arm - from left side downward, holding camera
                        endx = cx - 12;
                        endy = cy + 55;
                    } else {
                        // Bottom-right arm - from right side downward, holding camera
                        endx = cx + 12;
                        endy = cy + 55;
                    }
                }
            }

            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.quadraticCurveTo(ctrlx, ctrly, endx, endy);
            ctx.stroke();
        }
    }

    drawCamera(cx, cy) {
        // Draw camera held by photobooth gesture
        const gesture = this.state.gesture;
        if (!gesture || gesture.name !== 'photobooth') return;

        const ctx = this.ctx;
        const now = performance.now();
        const gPhase = Math.min(1, (now - gesture.startTs) / gesture.durationMs);

        // Camera position (held between two arms in front of face, well below the face)
        const camX = cx;
        const camY = cy + 65;

        ctx.save();

        // Camera body (dark gray rectangle)
        ctx.fillStyle = '#444';
        ctx.fillRect(camX - 24, camY - 12, 48, 24);

        // Camera lens (dark circle)
        ctx.fillStyle = '#1a1a1a';
        ctx.beginPath();
        ctx.arc(camX - 12, camY, 10, 0, Math.PI * 2);
        ctx.fill();

        // Lens shine (light reflection)
        ctx.fillStyle = '#666';
        ctx.beginPath();
        ctx.arc(camX - 12, camY - 2, 3, 0, Math.PI * 2);
        ctx.fill();

        // Viewfinder/flash area (top)
        ctx.fillStyle = '#555';
        ctx.fillRect(camX + 12, camY - 10, 8, 8);

        // Camera strap indicator (thin line on top)
        ctx.strokeStyle = '#999';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(camX - 20, camY - 13);
        ctx.lineTo(camX + 20, camY - 13);
        ctx.stroke();

        ctx.restore();
    }

    drawEyes(cx, cy) {
        const ctx = this.ctx;
        const eyeOff = 18;
        const eyeLookDown = this.state._photoBooth_eyeLookDown || 0;  // 0-1, look down amount

        const drawEye = (x, y) => {
            ctx.save();
            ctx.translate(x, y);
            ctx.scale(1, this.state.eyeScale * (this.state.eyeBias || 1));

            // white
            ctx.beginPath();
            ctx.arc(0, 0, 10, 0, Math.PI * 2);
            ctx.fillStyle = '#fff';
            ctx.fill();
            ctx.lineWidth = 2;
            ctx.strokeStyle = '#000';
            ctx.stroke();

            // pupil - moves down when looking at camera (photobooth)
            const pupilY = eyeLookDown * 4;  // Moves down 0-4 pixels
            ctx.beginPath();
            ctx.arc(0, pupilY, 4, 0, Math.PI * 2);
            ctx.fillStyle = '#000';
            ctx.fill();

            ctx.restore();
        };

        drawEye(cx - eyeOff, cy);
        drawEye(cx + eyeOff, cy);
    }

    drawFlash() {
        // Draw camera flash effect - white overlay over avatar area
        const now = performance.now();
        const flashFx = this.state.fx.find(fx => fx.type === 'flash' && now - fx.startTs < fx.durationMs);
        if (!flashFx) return;

        const ctx = this.ctx;
        const age = now - flashFx.startTs;
        const p = Math.min(1, age / flashFx.durationMs);
        const flashAlpha = (1 - p * p) * 0.8;  // Quick fade with max opacity 0.8

        ctx.save();
        ctx.globalAlpha = flashAlpha;
        ctx.fillStyle = '#ffffff';
        // Draw white rectangle (fills entire visible canvas)
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        ctx.restore();
    }

    drawFx(cx, cy) {
        const ctx = this.ctx;
        const now = performance.now();
        const active = [];
        for (const fx of this.state.fx) {
            const age = now - fx.startTs;
            const p = Math.min(1, age / fx.durationMs);
            if (p >= 1) continue;
            active.push(fx);

            // Skip flash - it's drawn separately by drawFlash()
            if (fx.type === 'flash') continue;

            const x = fx.x + fx.vx * p;
            const y = fx.y + fx.vy * p;
            const alpha = 1 - p;

            ctx.save();
            ctx.globalAlpha = alpha;
            if (fx.type === 'tear' || fx.type === 'sweat') {
                ctx.fillStyle = (fx.type === 'tear') ? '#6ec6ff' : '#8ad4ff';
                ctx.beginPath();
                ctx.ellipse(x, y, fx.size, fx.size * 1.3, 0, 0, Math.PI * 2);
                ctx.fill();
            } else if (fx.type === 'sparkle') {
                ctx.strokeStyle = '#ffff00';
                ctx.lineWidth = 3.5;
                for (let i = 0; i < fx.count; i++) {
                    const ox = x + (i - (fx.count - 1) / 2) * 10;
                    const oy = y + Math.sin(i + p * 6) * 4;
                    ctx.beginPath();
                    ctx.moveTo(ox - 12, oy);
                    ctx.lineTo(ox + 12, oy);
                    ctx.moveTo(ox, oy - 12);
                    ctx.lineTo(ox, oy + 12);
                    ctx.stroke();
                }
            } else if (fx.type === 'heart') {
                ctx.fillStyle = '#ff6b9d';
                for (let i = 0; i < fx.count; i++) {
                    const ox = x + (i - (fx.count - 1) / 2) * 12;
                    const oy = y - p * 12 - i * 4;
                    ctx.beginPath();
                    ctx.moveTo(ox, oy);
                    ctx.bezierCurveTo(ox - 6, oy - 6, ox - 12, oy + 4, ox, oy + 12);
                    ctx.bezierCurveTo(ox + 12, oy + 4, ox + 6, oy - 6, ox, oy);
                    ctx.fill();
                }
            } else if (fx.type === 'pop') {
                ctx.strokeStyle = '#ffd166';
                ctx.lineWidth = 3;
                ctx.beginPath();
                ctx.arc(x, y, fx.size + p * 12, 0, Math.PI * 2);
                ctx.stroke();
            } else if (fx.type === 'bubble') {
                ctx.strokeStyle = '#b5eaff';
                ctx.lineWidth = 2;
                for (let i = 0; i < fx.count; i++) {
                    const ox = x + (i - (fx.count - 1) / 2) * 10;
                    const oy = y - p * 20 - i * 6;
                    ctx.beginPath();
                    ctx.arc(ox, oy, fx.size - i * 1.5, 0, Math.PI * 2);
                    ctx.stroke();
                }
            }
            ctx.restore();
        }
        this.state.fx = active;
    }

    drawEyebrows(cx, cy) {
        const ctx = this.ctx;
        const off = 18;
        const lift = this.state.eyebrowY * 8;

        ctx.strokeStyle = '#000';
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';

        const brow = (x) => {
            ctx.beginPath();
            ctx.moveTo(x - 10, cy - lift);
            ctx.quadraticCurveTo(x, cy - 12 - lift, x + 10, cy - lift);
            ctx.stroke();
        };

        brow(cx - off);
        brow(cx + off);
    }
}

if (typeof module !== 'undefined') module.exports = OctopusAnimator;
