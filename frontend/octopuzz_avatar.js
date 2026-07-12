/**
 * OctopuzzAvatar — ThorVG + SVG DOM анимация.
 *
 * Один Picture на весь SVG. Анимация: меняем transform-атрибуты
 * элементов в SVG DOM, перезагружаем Picture каждый кадр.
 * Координаты — в SVG-пространстве (viewBox 0 0 130 130).
 *
 * Липсинк: полная поддержка audio_sync (jaw + viseme_proxy),
 * тот же scheduling что в OctopusAnimator.
 */

// [browY, browTilt, cheekOp, mouthBias, tentacleSpeed, tentacleAmp, armStyle, eyeBias]
const _OCTO_ACTION_FACE = {
    //                browY  tilt  cheek  mouth  tSpd  tAmp  armStyle    eyeBias
    sing:        [  0.5,  0,    0.7,  0.14,  2.0,  2.0,  'sway',    1.12 ],
    laugh:       [  0.6,  0,    1.0,  0.16,  2.8,  1.2,  'flutter', 1.15 ],
    whisper:     [ -0.3,  0,    0.3,  0.13,  0.7,  0.5,  'droop',   0.90 ],
    shout:       [  0.7,  0,    0.5,  0.24,  4.5,  1.4,  'tremble', 1.20 ],
    greet:       [  0.5,  0,    0.8,  0.12,  2.0,  1.4,  'wave_seq', 1.10 ],
    wave:        [  0.4,  0,    0.8,  0.12,  2.0,  1.4,  'wave_seq', 1.10 ],
    clap:        [  0.4,  0,    1.0,  0.12,  2.0,  1.8,  'clap',    1.12 ],
    sfx_clap:    [  0.4,  0,    1.0,  0.12,  2.0,  1.8,  'clap',    1.12 ],
    point:       [  0.4,  0,    0.6,  0.12,  2.0,  1.8,  'flutter', 1.10 ],
    hug:         [  0.3,  0,    1.0,  0.12,  0.8,  0.6,  'hug',     1.08 ],
    sfx_hug:     [  0.3,  0,    1.0,  0.12,  0.8,  0.6,  'hug',     1.08 ],
    shrug:       [  0.4,  0,    0.4,  0.12,  2.0,  1.8,  'flutter', 1.10 ],
    sfx_spin:    [  0.5,  0,    1.0,  0.15,  3.5,  2.5,  'flutter', 1.12 ],
    sfx_tear:    [ -0.6, -0.4,  0.1,  0,     0.8,  0.8,  'droop',   0.92 ],
    sfx_sweat:   [ -0.8, -0.3,  0.1,  0.03,  0.9,  0.9,  'droop',   0.90 ],
    sfx_heart:   [  0.5,  0,    1.0,  0.12,  1.5,  1.0,  'heart',   1.16 ],
    sfx_sparkle: [  0.7,  0,    0.8,  0.08,  2.0,  2.0,  'flutter', 1.20 ],
    sfx_pop:     [  0.8,  0,    0.7,  0.18,  2.5,  2.0,  'flutter', 1.22 ],
    sfx_boop:    [  0.5,  0,    0.8,  0.14,  1.5,  1.5,  'flutter', 1.12 ],
    sfx_wave:    [  0.3,  0,    0.7,  0.10,  1.5,  1.5,  'sway',    1.08 ],
    sfx_bubble:  [  0.4,  0,    0.7,  0.11,  1.5,  1.5,  'flutter', 1.10 ],
    photobooth:  [  0.3,  0,    0.9,  0.30,  1.0,  1.0,  'sway',    1.15 ],
    heart:       [  0.5,  0,    1.0,  0.12,  1.5,  1.0,  'heart',   1.16 ],
    wipe:        [ -0.3,  0,    0.2,  0.05,  0.8,  0.6,  'droop',   0.92 ],
};

class OctopuzzAvatar {
    constructor(canvasId, svgUrl, opts = {}) {
        if (typeof canvasId === 'string') {
            const sel = canvasId.startsWith('#') || canvasId.startsWith('.')
                ? canvasId : '#' + canvasId;
            this.canvasEl  = document.querySelector(sel);
            this.canvasSel = sel;
        } else {
            this.canvasEl  = canvasId;
            this.canvasSel = canvasId.id ? '#' + canvasId.id : null;
        }
        if (!this.canvasEl)  throw new Error('Canvas not found: ' + canvasId);
        if (!this.canvasSel) throw new Error('Canvas element must have an id');

        this.svgUrl = svgUrl;
        this.opts   = Object.assign({
            width:    this.canvasEl.width  || 400,
            height:   this.canvasEl.height || 400,
            renderer: 'sw',
        }, opts);

        this.TVG       = null;
        this.tvgCanvas = null;
        this.picture   = null;
        this._svgDoc   = null;
        this._ser      = new XMLSerializer();
        this.ready     = false;

        this.state = {
            // Глаза
            eyeLookX: 0, eyeLookY: 0,
            targetEyeX: 0, targetEyeY: 0,
            eyeScale: 1, blinkUntil: 0,
            // Рот
            mouthOpen: 0, targetMouth: 0,
            // Брови
            eyebrowY: 0, targetBrowY: 0,
            browTilt: 0, targetBrowTilt: 0,
            // Щёки
            cheekOpacity: 0.5, targetCheekOp: 0.5,
            // Щупальца
            tentaclePhase: 0,
            tentacleStyle: 'sway',   // sway | flutter | droop | lash | probe
            // Общее
            emotion: 'calm', speaking: false,
            // Body motion (in SVG units, viewBox 130x130)
            bodyBob: 0,   // vertical oscillation
            shakeX: 0,    // horizontal oscillation
            // Actions
            actionMode: null, actionStartTs: 0, actionUntilTs: 0,
            tentacleSpeed: 1.0, tentacleAmp: 1.0,
            // Eye expression bias (1 = neutral, >1 = wide, <1 = squint)
            eyeBias: 1.0, targetEyeBias: 1.0,

            // ── Lip sync: jaw track (амплитуды → высота рта) ─────────────
            jawSeq: [], jawIdx: 0, jawStepMs: 20,
            jawNextTs: 0, jawActive: false, jawScheduleTs: 0,
            targetJaw: 0, jawOpen: 0,   // targetJaw → smoothed jawOpen → mouth height

            // ── Lip sync: viseme proxy track (форма → ширина рта) ─────────
            visemeSeq: [], visemeIdx: 0, visemeStepMs: 50,
            visemeNextTs: 0, visemeActive: false, visemeScheduleTs: 0,
            currentViseme: 'REST',      // текущий viseme → определяет ширину рта

            // Для синхронизации с аудиоплеером
            responseStartPlayheadS: 0,
            pendingEnd: false,

            // Gesture cooldown (matches canvas animator)
            lastGestureTs: 0, lastGesture: null,

            // Per-action visual extras
            _photoBoothEyeLookDown: 0,
            _spinRotation: 0,
        };

        // Точки крепления щупалец (SVG-координаты 0..130).
        // oy = верхняя точка пути (shear-якорь): всё содержимое ниже — сдвигается,
        // всё что выше — не трогается. Значения подобраны по реальным path-координатам.
        // oy = Y-координата точки соединения щупальца с телом (начало M-команды пути).
        // Shear-матрица держит эту строку неподвижной; всё что ниже — гнётся.
        this._arms = [
            ['arm_a', 38,  65],   // M55.3,65.1
            ['arm_b', 88,  72],   // M74.8,55.7 — oy=72 = нижний край shape_155 (живот), устраняет щель
            ['arm_c', 87,  86],   // M99,85.9
            ['arm_d', 54,  73],   // M57,73.4
            ['arm_e', 61,  64],   // M62.7,64.1
            ['arm_f', 25,  83],   // M29.2,83.7
            ['arm_g', 74,  60],   // M67.3,59.4
        ];

        // Random phase offsets per arm (for independent wobble, matching canvas animator)
        this._armPhaseOffsets = Array.from({ length: this._arms.length }, () => Math.random() * Math.PI * 2);

        this._init();
    }

    // ── Viseme → mouth open ──────────────────────────────────────────────
    visemeToOpen(v) {
        switch ((v || 'REST').toUpperCase()) {
            case 'REST': return 0;
            case 'A':    return 1.0;
            case 'E':    return 0.6;
            case 'I':    return 0.35;
            case 'O':    return 0.85;
            case 'U':    return 0.7;
            case 'F':    return 0.25;
            case 'L':    return 0.45;
            default:     return 0.3;
        }
    }

    async _init() {
        try {
            const ThorVG = window.ThorVG;
            if (!ThorVG || typeof ThorVG.init !== 'function')
                throw new Error('ThorVG not loaded');

            this.TVG = await ThorVG.init({ renderer: this.opts.renderer, locateFile: f => f });

            this.tvgCanvas = new this.TVG.Canvas(this.canvasSel, {
                width: this.opts.width, height: this.opts.height,
                enableDevicePixelRatio: false,
            });

            const svgText = await fetch(this.svgUrl).then(r => {
                if (!r.ok) throw new Error('SVG fetch failed: ' + r.status);
                return r.text();
            });

            // SVG DOM — живём в нём, меняем transform-атрибуты
            this._svgDoc = new DOMParser().parseFromString(svgText, 'image/svg+xml');
            this._injectEyeElements();

            this.picture = new this.TVG.Picture();
            this.picture.load(svgText, { type: 'svg' });
            this.picture.size(this.opts.width, this.opts.height);
            this.tvgCanvas.add(this.picture);

            this.tvgCanvas.update();
            this.tvgCanvas.render();

            this.ready = true;
            this._svgFx = [];
            console.log('🐙 OctopuzzAvatar ready');

            this._lastTime = performance.now();
            requestAnimationFrame(t => this._loop(t));
        } catch (err) {
            console.error('🐙 OctopuzzAvatar init failed:', err);
        }
    }

    // ── Render loop ──────────────────────────────────────────────────────

    _loop(ts) {
        if (!this.ready) { requestAnimationFrame(t => this._loop(t)); return; }
        const dt = (ts - this._lastTime) / 1000;
        this._lastTime = ts;
        this._updateState(dt, ts);
        this._applyTransforms();
        this.tvgCanvas.update();
        this.tvgCanvas.render();
        requestAnimationFrame(t => this._loop(t));
    }

    _injectEyeElements() {
        const ns = 'http://www.w3.org/2000/svg';
        const eyes = [
            { scleraId: 'sclera_left',  pupilId: 'eye_left',  cx: 51.7, cy: 43.9, r: 6.6 },
            { scleraId: 'sclera_right', pupilId: 'eye_right', cx: 79.0, cy: 44.0, r: 6.6 },
        ];
        for (const { scleraId, pupilId, cx, cy, r } of eyes) {
            const pupil = this._svgDoc.getElementById(pupilId);
            if (!pupil) continue;
            const sclera = this._svgDoc.createElementNS(ns, 'circle');
            sclera.setAttribute('id', scleraId);
            sclera.setAttribute('cx', String(cx));
            sclera.setAttribute('cy', String(cy));
            sclera.setAttribute('r',  String(r));
            sclera.setAttribute('fill', '#ffffff');
            sclera.setAttribute('stroke', '#1e1b1c');
            sclera.setAttribute('stroke-width', '1.2');
            pupil.parentNode.insertBefore(sclera, pupil);
            pupil.setAttribute('r', '3.5');
        }

        // Fix arm_g: shape_151 (arm body) is outside <g id="arm_g"> in the source SVG.
        // Move it to be the first child so it transforms with its suckers.
        const armG    = this._svgDoc.getElementById('arm_g');
        const body151 = this._svgDoc.getElementById('shape_151');
        if (armG && body151 && body151.parentNode !== armG) {
            body151.parentNode.removeChild(body151);
            armG.insertBefore(body151, armG.firstChild);
        }

        this._initHeartPaths();
        this._initClapPaths();
        this._initHugPaths();
    }

    _initHeartPaths() {
        // Heart pose comes from octopuzz2.svg drawn by the artist.
        // That file introduces two brand-new arm shapes (arm_b1 / arm_b2) that form
        // the left and right lobes of the ♥, plus a different path for shape_151.
        // Strategy:
        //   • Inject arm_b1 and arm_b2 elements into the SVG DOM (hidden at start).
        //   • When heart mode is active: hide original arm_a/arm_b bodies, show overlays,
        //     swap shape_151 d-string to the heart-pose version.
        //   • When heart ends: restore everything.

        const ns  = 'http://www.w3.org/2000/svg';
        const root = this._svgDoc.documentElement;

        const p151 = this._svgDoc.getElementById('shape_151');
        if (!p151) return;

        this._heartPaths = {
            idle151: p151.getAttribute('d'),
            // shape_151 in heart pose (from octopuzz2.svg)
            heart151: 'M54.7,66.1c-6.2,2.2,8.8,33.6,11.2,34.2,1.8,1.9,3.4,3.1,4.5,3.5,1.1,3.1,3.6,4.2,5.7,4.5.3.9.5,2.9,2.6,4.5.8.8.7,2,.5,2.8-.6,1.4.1,4.3,2.2,4.5.6,3.5,3.7,6.1,7.5,5.4,2.1-.5,2.9-1.4,2.4-2.9-1.1-1.9-1.3-2.2-1.2-4.8.5-5,1-9.3-1.1-13.6-2.2-4.8-6.6-11.8-9.8-14.5l-5.5-10.1c-7-16.3-7.6-17.5-18.9-13.5Z',
            active: false,
        };

        // Original arm_a and arm_b bodies + suckers to hide during heart
        this._heartHideIds = [
            'shape_7',  'shape_8',  'shape_9',  'shape_10',  // arm_a
            'shape_11', 'shape_12', 'shape_13', 'shape_14',  // arm_b
        ];

        // Heart arm overlays — exact paths from octopuzz2.svg arm_b1 / arm_b2
        // arm_b1 = LEFT heart lobe  (class st4: fill #a256d8, stroke #1e1b1c 1.1px round)
        // arm_b2 = RIGHT heart lobe (same style)
        // suckers = class st10: fill #f777bd, no stroke
        const overlays = [
            // ── left lobe (arm_b1) ──
            ['heart_arm_l',    '#a256d8', true,  'M38.1,68.9s9.5,15.1,10.3,14.5c2.8-1.9,6.9-1,1.8-8.3-2-3-6.4-9.3-3.7-15.7,2.7-5.8,8.3-5.7,12.9-2.8s5.5,5.4,4,6.8c-.9,1.2-4.9,1.9-4.7.5.2-2.1-2.8-2.6-4.2-.5-1.3,1.8-.4,4.7,2.9,7.1,3.2,2.4,3.3,2.4,4.1,4.7.2.9,3.6,2.7,2.1,8.3-.3.9,1.6,4.5-2.4,9.9,0,0,0,2.3-.7,2.6-14.2,7.8-29.6-9.5-32.4-14.4-5.6-9.8,2.3-18.7,10-12.7Z'],
            ['heart_arm_l_s1', '#f777bd', false, 'M56.2,70.2c-.8,1.6-4.7,4.4,4.2,3.6-.6-1-2.5-2.1-4.2-3.6Z'],
            ['heart_arm_l_s2', '#f777bd', false, 'M61.2,75.9c-2.3,2.1-1.4,5.4,2.1,5.7.4-2.8-.8-4.1-2.1-5.7Z'],
            ['heart_arm_l_s3', '#f777bd', false, 'M63.2,85.3c-2.8,0-4.8,4.4-2.6,6.3,2.1,1.3,3.1-3.9,2.6-6.3Z'],
            // ── right lobe (arm_b2) ──
            ['heart_arm_r',    '#a256d8', true,  'M89.5,69.6c-4.4,1.9-3.9,2.9-5.2,5-2.5,4.2-.6,5.2-3,8.5s-7.5-.6-2-8.8c2.2-3.3,6.9-8.5,4.1-14.9-2.8-5.8-9.3-7-13.7-3.5s-5.3,6.8-3.8,8.1c.9,1.2,4.6.9,4.4-.6-.2-2.2,3.1-3,4.6-1,1.4,1.7.3,4.9-3.2,7.7-3.5,2.8-3.6,2.9-4.5,5.4-.2,1-3.9,3.2-2.4,8.9.3.9-1.8,4.9,2.5,10.1,0,0,0,2.4.7,2.7,15.2,6.6,27.2-8.1,28.9-13.2,5.1-15.1-3.3-16.1-7.3-14.4Z'],
            ['heart_arm_r_s1', '#f777bd', false, 'M73.6,69.1c1.1,2.1-1,4.1-4.6,4.2.6-.9,1.5-1.3,4.6-4.2Z'],
            ['heart_arm_r_s2', '#f777bd', false, 'M67.5,76.3c2.5,2,1.4,5.5-2.4,6.2-.3-2.9,1-4.4,2.4-6.2Z'],
            ['heart_arm_r_s3', '#f777bd', false, 'M65.4,85.7c3-.4,5.1,4.1,2.7,6.3-2.3,1.6-3.3-3.7-2.7-6.3Z'],
        ];

        this._heartArmEls = [];
        for (const [id, fill, hasStroke, d] of overlays) {
            const p = this._svgDoc.createElementNS(ns, 'path');
            p.setAttribute('id',   id);
            p.setAttribute('d',    d);
            p.setAttribute('fill', fill);
            if (hasStroke) {
                p.setAttribute('stroke',           '#1e1b1c');
                p.setAttribute('stroke-width',     '1.1px');
                p.setAttribute('stroke-linecap',   'round');
                p.setAttribute('stroke-linejoin',  'round');
            }
            p.setAttribute('opacity', '0');
            root.appendChild(p);
            this._heartArmEls.push(p);
        }
    }

    _initClapPaths() {
        // Clap pose comes from octopuzz3.svg (updated by artist, no arm_b2 suckers).
        // Two new arm groups:
        //   arm_c1   — right raised arm (body + 4 suckers)
        //   arm_main — left raised arm  (anonymous body + 4 suckers)
        // Same hide strategy as heart: conceal original arm_a / arm_b bodies.

        const ns   = 'http://www.w3.org/2000/svg';
        const root = this._svgDoc.documentElement;

        const p151 = this._svgDoc.getElementById('shape_151');
        if (!p151) return;

        this._clapPaths = {
            idle151: p151.getAttribute('d'),
            // shape_151 in clap pose (from octopuzz3.svg)
            clap151: 'M76.5,61.6c-35.2-3.7-11.9,32.6-10.3,34.5.4,2.6,1,4.5,1.7,5.4-.9,3.2.6,5.5,2.1,6.9-.3.9-1.2,2.7-.4,5.2.2,1.1-.6,2-1.2,2.6-1.3.8-2.5,3.5-.8,5-1.5,3.2-.4,7.1,3.1,8.7,2,.8,3.2.5,3.6-1,.2-2.2.2-2.5,1.8-4.6,3.3-3.8,6.1-7.1,6.9-11.8.9-5.2,1.3-13.5.2-17.5l1.2-11.4c3.5-17.4,3.7-18.7-7.8-21.9h0Z',
            // tracks whether clap overlay is currently shown
            active: false,
        };

        // Same arm_a / arm_b bodies to hide as in heart pose
        this._clapHideIds = [
            'shape_7',  'shape_8',  'shape_9',  'shape_10',  // arm_a
            'shape_11', 'shape_12', 'shape_13', 'shape_14',  // arm_b
        ];

        // Clap arm overlays — exact paths from octopuzz3.svg (updated)
        // Bodies: class st0 → fill #9d55d6, stroke #1e1b1c 1.2px round
        // Suckers: class st10 → fill #f777bd, no stroke
        const overlays = [
            // ── arm_c1 (right raised arm) ──
            ['clap_arm_c1',    '#9d55d6', true,  'M114.8,33.4c-4.6,0-7.8,4.7-5.3,5.4.8.2,1.7-1.1,2.6-1.2,2.7,0,1.4,3.3-2.9,4.4-5,1.1-5,2.6-6.5,3.3-4.1,1.9-4.2,4.7-5.2,5.7-3.7,3.4-2.4,5.7-2.8,6.1-2.5,2.8-1.5,4.1-.9,6.1,0,.7-.5,2.4,1.4,3.6-.3-.7-6.7-3.2-4.5,5.5-1.2,3.8.2-2.2-1.2,1s-6.1,5.7-5.9,10.2c0,0,1.4,2.3,2.1,2.2,15.9-1.2,16.6-5.5,21.2-9.6,0-1.2,2.8-4.6,2.8-5.5.7-.4-2.9-12.2-2.9-12.2l-.2-.5c0-1,0-2.7,1.3-5.2,2.2-4.1,5.5-5.7,7.3-7.1,6.9-5.5,5.2-11.2-.5-11.5v-.7Z'],
            ['clap_arm_c1_s1', '#f777bd', false, 'M95.3,65.7c1.4-1.7,2-3.7,1.4-5.2-.4-1-1.4-1.4-2.4-1.4-1.4,2.5,0,4.8.9,6.7h0Z'],
            ['clap_arm_c1_s2', '#f777bd', false, 'M95.3,56.2c.3-1-.2-3.6,3.4-6h0c1.4,1.5-.4,5.1-3.5,6.1h0Z'],
            ['clap_arm_c1_s3', '#f777bd', false, 'M98.9,49.3c1.7,1.1,5.7-1.5,5.3-4.5-2.9.6-4.3,2.5-5.3,4.5Z'],
            ['clap_arm_c1_s4', '#f777bd', false, 'M104.9,44c.8,2.2,4.9,1.2,5.1-2.2-1.9.2-3.9.8-5.1,2.2Z'],
            // ── anonymous arm (left/center raised arm) ──
            ['clap_arm_main',    '#9d55d6', true,  'M93,34.2c1.2.2,1,2.2,1.4,3,.7.8,7.6,1.3,7.3-1.8,0-4.1-9.2-11.1-15.8-8-5.2,2.5-5.4,9.9-5.3,12.8,2.4,9.7-4.6,22.2-11.8,31.4-3.1,5.6-9.6,9.9-9.7,9.3-6.8.8-11.4-.9-10.1-.5-4.6-2.9-7-6.9-8.5-10.1s-3-3.7-5.3-4c-5.8-.6-10.1,6.7-5.6,14.6,2.8,4.9,15.3,21.7,29.5,13.9.7-.3,3.6-2.1,3.6-2.1,10.1-4.7,28-21.8,29.8-32.2,1.4-1.3,4.4-7.7,1.5-11.5.4-1.1,1.4-6.3-2.8-8.5-2.4-2.4-1.3-7,1.8-6.3h0Z'],
            ['clap_arm_main_s1', '#f777bd', false, 'M92.3,41.6c-1.4,1.7-2,3.6-1.4,5.1.4,1,1.4,1.4,2.4,1.4,1.4-2.4,0-4.7-.9-6.5h0Z'],
            ['clap_arm_main_s2', '#f777bd', false, 'M94.1,50.3c0,1,1.5,3.1-.9,6.7h0c-1.9-.8-1.6-4.8.9-6.8h0Z'],
            ['clap_arm_main_s3', '#f777bd', false, 'M92.3,59.4c-2-.3-4.6,3.6-3.1,6.1,2.4-1.7,3-3.9,3.1-6.1Z'],
            ['clap_arm_main_s4', '#f777bd', false, 'M88.3,66.7c-1.7-1.4-4.9,1.3-3.4,4.3,1.6-1.1,3-2.6,3.4-4.3Z'],
        ];

        this._clapArmEls = [];
        for (const [id, fill, hasStroke, d] of overlays) {
            const p = this._svgDoc.createElementNS(ns, 'path');
            p.setAttribute('id',   id);
            p.setAttribute('d',    d);
            p.setAttribute('fill', fill);
            if (hasStroke) {
                p.setAttribute('stroke',          '#1e1b1c');
                p.setAttribute('stroke-width',    '1.2px');
                p.setAttribute('stroke-linecap',  'round');
                p.setAttribute('stroke-linejoin', 'round');
            }
            p.setAttribute('opacity', '0');
            root.appendChild(p);
            this._clapArmEls.push(p);
        }
    }

    _initHugPaths() {
        // Hug pose from octopuzz4.svg — swaps d-paths of existing arm elements.
        // No overlay injection: all arm IDs stay the same, just different shapes.

        const swaps = [
            // arm_a (body + 3 suckers)
            ['shape_7',   'M26.6,65.3c17.8,4.1,7.4,4.6,8.8,5.8,4.9,4.2,8.5,5.5,15.7.7,2.9-2,6.7-5.5,11.5-3.8,4.6,1.9,5.7,7.7,2.6,11.6-2.9,3.4-6.1,3.3-7,1.8-.6-.9,0-2.4,1.3-2.5,1.5,0,2.7-4.7.6-5.4-3.6-1.1-7.5,6.1-10.6,7.9-.8.4-1.9.7-2.6.9-.5,0-2.4,3.4-6.7,1.3-1.6-.8-4,1.1-7.6-2.8-1.6,1.6-2.2,1.9-2.2,1.9,0,0-2.1,1-2.2.9,0,0,.3-.7-1.6-.8s-3.2.5-6.6-1.2-4.7-5.5-3-10.7,5.9-6.5,9.6-5.7Z'],
            ['shape_8',   'M53.1,77.9c-.9-1.3-4.8.7-4.9,3.7,1.5-.3,3.2-2.2,4.9-3.7Z'],
            ['shape_9',   'M46.2,82c-.5-2.3-5.2-2.4-6.5.9,3.1,1.5,4.9.8,6.5-.9Z'],
            ['shape_10',  'M38.9,83c.5-2.5-3.2-5.4-6.2-2.6,2.2,2.6,4.4,2.7,6.2,2.6Z'],
            // arm_b (body + 3 suckers)
            ['shape_11',  'M91.7,69.6s4,5.7,3.6,6.3c-1.3,2.1-4.4,4.9-10.5-1.6-2.5-2.6-6.3-7.6-11.2-6.7-4.4,1.1-5.5,6.2-2.9,10.6,2.6,4.4,5.4,4.6,6.4,3.7.9-.5.4-2.3-.7-2.5-1.6-.3-3.3-5.6-1.7-6.4,1.3-.8,4.8,3.3,6.8,6.8s2.1,3.6,4,4.9c.7.4,2.3,4,6.7,4,.7,0,3.7,2.6,7.6.2,0,0,1.3-2.2,1.5-2.7,3.9-.4,8.2-1.5,9.4-6.8,3.4-16-10.7-13-10.7-13l-8.3,3.2Z'],
            ['shape_12',  'M80.8,78c1.6-.5,3.1,1.8,3.2,4.8-.8-.8-1.8-2.8-3.2-4.8Z'],
            ['shape_13',  'M86.1,84.8c1.5-1.6,4.2,0,4.6,3.4-2.2-.3-3.3-1.8-4.6-3.4Z'],
            ['shape_14',  'M93.1,88.6c-.3-2.6,3.2-3.3,4.9-.8,1.2,2.3-2.9,1.9-4.9.8Z'],
            // arm_c (body + 4 suckers)
            ['shape_15',  'M90.6,91.8c-2.8-4-25.2-22.9-28.4-24.5,0,0,1.2,2.5.9-2.1,8-18.3,33.8,13.9,33.8,13.9,2.4,1.2,4.1,2.8,4.6,3.7,2.2,2.3,4.3,3.6,3.6,7.6-.2.5,3,3,1.4,7.9-.5,1.3,1.7,4.9-1.6,8.1-1.2,1.2-.2,3-4.9,5.4-4,2.3-2.9,6.6,0,6,.9-.4.9-2.2,2-2.1,3.3.2,3.1,6.7-2,7.8-6.6,1-12.8-5.7-9.2-14,1-2.1,3.4-4.8,2.8-10.3-.2-3.4-1.5-5.4-2.5-6.6l-.6-.7h0Z'],
            ['shape_26',  'M101.2,83.6c-.8,2.1-.7,4.1.4,5.4.7.9,2,1,2.9.8.5-2.6-1.7-4.7-3.3-6.2Z'],
            ['shape_27',  'M104.5,90.8c.5,1.1,2.9,3.1,1.3,7.8h-.2c-2.3-.3-3.3-4.9-1.1-7.8Z'],
            ['shape_28',  'M105.8,99.8c-2.6-.2-4.3,4.3-1.7,6.7,2.4-2.1,2.2-4.4,1.7-6.7Z'],
            ['shape_29',  'M103.6,107.7c-1.8-1.7-5.4.6-4,3.9,1.8-.8,3.5-2.1,4-3.9Z'],
            // unnamed arm body (arm_g area) + arm_g suckers
            ['shape_151', 'M80.1,56.5c-7.3-1.7-13.7,33.5-11.9,35.5.5,2.6,1.2,4.5,2,5.6-1,3.3.6,5.6,2.5,7.1-.3.9-1.5,2.7-.4,5.3.2,1.1-.6,2.1-1.3,2.7-1.4.8-2.7,3.7-.9,5.1-1.8,3.3-.5,7.3,3.6,8.9,2.4.8,3.7.4,4.2-1.2.2-2.2.2-2.6,2-4.8,3.8-4,7-7.4,7.9-12.2,1.1-5.3,1.4-13.8.2-17.9l1.4-11.8c4.2-17.8,4.3-19.2-9-22.3h-.1Z'],
            ['shape_43',  'M73.3,104.9c2.9,0,2.4,4.7-.3,5.4-.8-1.7-.3-3.6.3-5.4Z'],
            ['shape_44',  'M72.3,112.2c2.5,2.6.1,4.2-2.2,4.5-.5-2.1,1-3.2,2.2-4.5Z'],
            ['shape_45',  'M71,97.6c3.4,1.6,4.4,5,2.2,6.6-3.4-2.8-2.5-5.8-2.2-6.6Z'],
            // arm_d (body + 3 suckers)
            ['shape_152', 'M57,73.4c-.8,7.5-9.6,22.9-8.1,29.9-1.4,4.7-.3,10-.2,13,.2,3.5-1.1,7.2-3.7,7.2s-3.4-.6-3.4,1.6,2,3.7,5.8,3.7c4.2-.2,6.3-1.5,9.8-4.7,2.5-2.1,2.7-4.6,2.2-6.7-.2-1,2.7-2.4,1-7-.5-1.3,3-3,1.6-8.1,0-.8,1.4-2.1,1-5.2,1.9.9,11.1-30.4,9.3-33.6l-4.6-2.1s-9.4-.7-10.7,12h0Z'],
            ['shape_23',  'M59.3,116.8c-2.4-.4-1.4-4.9,1-5.2.7,2.1,0,3.6-1,5.2Z'],
            ['shape_24',  'M60.4,109.2c-2.2-2.9-.8-5.2,1.3-5.6.6,3.1,0,4.2-1.3,5.6Z'],
            ['shape_25',  'M61.5,102.4c-2.2-2.1-1.3-4.6,1.1-5.1,1.1,2.7-.7,4.7-1.1,5.1Z'],
            // arm_e (body + 3 suckers)
            ['shape_153', 'M58.1,67.1l4.7,5.9c-3.7,0-24.3,27.6-21.8,38.7,0,2.5-.6,8.9-5.6,11.3-6.4,3-10.7-1.5-10.6-5-.2-2.6,2.4-3.6,3-2.9.3.7,0,2.4,1.2,2.5,2.9.4,4.2-3.6,2-5.5-3.9-1.6-2.7-6.2-2.2-7.2-2.6-3.2-1.1-8.2,1.9-10-1.5-4.3,23.9-27.8,27.4-27.8Z'],
            ['shape_20',  'M35.3,89.8c-.3-.6-1.1-.9-1.8-.9,0,0-1.3,2.1-1.8,3-.9,2-.5,2.9-.5,2.9.6,0,1.7-.2,2.7-.9,1.7-1,2.4-2.8,1.4-4.3h0v.2Z'],
            ['shape_21',  'M30.2,110.8c3-1.9,1.6-6.6-1-6.3-1.1,2.4-.2,5.1,1,6.3Z'],
            ['shape_22',  'M28.7,103.7c3.4-1.3,2.4-6.5.4-6.6,0,0-.8,1.4-.9,1.9-.5,1.6-.7,2.6.5,4.7Z'],
            // arm_f (body + 2 suckers)
            ['shape_154', 'M32.9,93.7c-4.4,5.2-3.3,8.2-4,12.6-.3,2.5-1.8,7.3-6.2,8.9-6.1,2.4-11.9-2.3-10.7-7.2,1.2-3.1,3.8-4,4.5-1.7,0,.7-.5,1.5.5,2.4s5.3.2,3.4-5c-1.7-3.2-2.2-4.9-1.6-7,0-1.8-1.4-2.9.9-7.9s5.9-7.3,8.7-8.2c20-15.5,14.1-46.4,36.4-18.1-.6.7-6.3,6.6-6.6,7.3-3.5,3.2-19.6,19.8-25.3,23.8h0s0,0,0,0Z'],
            ['shape_18',  'M20.8,103.8c2.5,0,2.7-5.3-1.3-6.2-.7,2.4.2,4.2,1.3,6.2Z'],
            ['shape_19',  'M19.2,96.6c1.4,0,2.6-1.6,3.2-3.1,1-2.2.7-4.2-.9-4.9-2,1.4-3.4,5-2.2,8h-.1Z'],
            // belly connector
            ['shape_155', 'M83.8,68.4l-36.8-.8c-19.1-1.6-8.3,10.2-8,10.5,4.1,3.9,5.9,9.7,9.4,9.6,11.9-.4,23.1-3.2,33.4-.7,10.2,2.5,9.3-.4,12.2-6.9,2.7-6.5,4.1-4.1,4.1-4.1-4.3-9.1-10.1-7.4-14.3-7.5Z'],
        ];

        this._hugPaths  = { active: false };
        this._hugSwaps  = [];
        for (const [id, hugD] of swaps) {
            const el = this._svgDoc.getElementById(id);
            if (!el) continue;
            this._hugSwaps.push({ el, idleD: el.getAttribute('d'), hugD });
        }

        // Save arm_a / arm_b groups + their original next-siblings so we can
        // move them to the front (end of DOM) on hug enter, and restore on exit.
        // In octopuzz.svg the arms are rendered EARLY (behind the body); in
        // octopuzz4.svg they are LAST (on top). Without z-reorder the wide hug
        // arms would be hidden behind shape_155 / shape_17 / shape_16.
        const armA = this._svgDoc.getElementById('arm_a');
        const armB = this._svgDoc.getElementById('arm_b');
        this._hugArmA     = armA;
        this._hugArmB     = armB;
        this._hugArmANext = armA?.nextSibling ?? null;
        this._hugArmBNext = armB?.nextSibling ?? null;

    }

    _updateState(dt, now) {
        const L = (a, b, t) => a + (b - a) * t;

        // ── Actions ───────────────────────────────────────────────────────
        const actionActive = this.state.actionMode && now < this.state.actionUntilTs;
        if (actionActive) {
            const f = _OCTO_ACTION_FACE[this.state.actionMode];
            if (f) {
                const [browY, tilt, cheek, mouth, tSpeed, tAmp, armStyle, eyeBias] = f;
                this.state.targetBrowY    = browY;
                this.state.targetBrowTilt = tilt;
                this.state.targetCheekOp  = cheek;
                this.state.tentacleSpeed  = tSpeed;
                this.state.tentacleAmp    = tAmp;
                this.state.tentacleStyle  = armStyle || 'sway';
                this.state.targetEyeBias  = eyeBias != null ? eyeBias : 1.0;
                if (!this.state.speaking) this.state.targetMouth = mouth;

                // Compute bodyBob / shakeX from time offset (SVG units ≈ pixels / 2.15)
                const t = (now - this.state.actionStartTs) / 1000;
                const action = this.state.actionMode;
                if (action === 'sing') {
                    this.state.bodyBob = Math.sin(t * 6) * 1.4;   // 3px / 2.15 ≈ 1.4 SVG
                    this.state.shakeX  = Math.sin(t * 3) * 3.7;   // 8px / 2.15 ≈ 3.7 SVG
                } else if (action === 'laugh') {
                    this.state.bodyBob = Math.sin(t * 10) * 1.9;  // 4px / 2.15
                    this.state.shakeX  = 0;
                } else if (action === 'whisper') {
                    this.state.bodyBob = Math.sin(t * 4) * 0.5;   // 1px / 2.15
                    this.state.shakeX  = 0;
                } else if (action === 'shout') {
                    this.state.bodyBob = Math.sin(t * 8) * 0.9;   // 2px / 2.15
                    this.state.shakeX  = Math.sin(t * 20) * 0.9;  // 2px / 2.15
                } else if (action === 'greet' || action === 'wave' || action === 'clap' || action === 'sfx_clap' || action === 'point' || action === 'hug' || action === 'sfx_hug' || action === 'shrug') {
                    this.state.bodyBob = Math.sin(t * 6) * 0.9;   // 2px / 2.15
                    this.state.shakeX  = 0;
                } else if (action === 'sfx_spin') {
                    this.state.bodyBob      = Math.sin(t * 15) * 1.4;  // 3px / 2.15
                    this.state.shakeX       = 0;
                    this.state._spinRotation = t * Math.PI * 4;          // full spin
                } else if (action === 'photobooth') {
                    this.state.bodyBob = 0;
                    this.state.shakeX  = 0;
                    this.state._photoBoothEyeLookDown = 0.6;
                } else {
                    this.state.bodyBob = 0;
                    this.state.shakeX  = 0;
                }

                if (this._dbgAction !== this.state.actionMode) {
                    this._dbgAction = this.state.actionMode;
                    console.log('🎬 action running:', this.state.actionMode, {browY, tilt, cheek, tSpeed, tAmp, armStyle, eyeBias, msLeft: Math.round(this.state.actionUntilTs - now)});
                }
            } else {
                console.warn('🎬 action unknown:', this.state.actionMode);
            }
        } else if (this.state.actionMode !== null) {
            // Action expired — restore emotion
            this.state.tentacleSpeed          = 1.0;
            this.state.tentacleAmp            = 1.0;
            this.state.bodyBob                = 0;
            this.state.shakeX                 = 0;
            this.state._spinRotation          = 0;
            this.state._photoBoothEyeLookDown = 0;
            this._dbgAction = null;
            this.state.actionMode = null;
            this.setEmotion(this.state.emotion);
        }

        // ── Lip sync sequences ────────────────────────────────────────────
        // Jaw track (амплитуды) → targetJaw (высота рта)
        if (this.state.jawActive && this.state.jawSeq.length) {
            while (this.state.jawIdx < this.state.jawSeq.length && now >= this.state.jawNextTs) {
                this.state.targetJaw = Math.max(0, Math.min(1, this.state.jawSeq[this.state.jawIdx]));
                this.state.jawIdx++;
                this.state.jawNextTs += this.state.jawStepMs;
            }
            if (this.state.jawIdx >= this.state.jawSeq.length) {
                this.state.jawActive = false;
                this.state.jawSeq = [];
                if (this.state.pendingEnd && !this.state.visemeActive) {
                    this.state.targetJaw = 0;
                    this.state.targetMouth = 0;
                    this.state.speaking = false;
                    this.state.pendingEnd = false;
                }
            }
        }

        // Viseme proxy track (строки) → currentViseme (ширина рта) + targetMouth (fallback высота)
        if (this.state.visemeActive && this.state.visemeSeq.length) {
            while (this.state.visemeIdx < this.state.visemeSeq.length && now >= this.state.visemeNextTs) {
                const v = this.state.visemeSeq[this.state.visemeIdx];
                this.state.currentViseme = v;
                this.state.targetMouth   = this.visemeToOpen(v); // fallback height (used if no jaw track)
                this.state.visemeIdx++;
                this.state.visemeNextTs += this.state.visemeStepMs;
            }
            if (this.state.visemeIdx >= this.state.visemeSeq.length) {
                this.state.visemeActive = false;
                this.state.visemeSeq = [];
                this.state.currentViseme = 'REST';
                if (this.state.pendingEnd && !this.state.jawActive) {
                    this.state.targetMouth = 0;
                    this.state.speaking = false;
                    this.state.pendingEnd = false;
                }
            }
        }

        // ── Smoothing ─────────────────────────────────────────────────────
        this.state.eyeLookX = L(this.state.eyeLookX, this.state.targetEyeX, 0.12);
        this.state.eyeLookY = L(this.state.eyeLookY, this.state.targetEyeY, 0.12);
        this.state.eyeScale = now < this.state.blinkUntil
            ? L(this.state.eyeScale, 0.05, 0.4)
            : L(this.state.eyeScale, 1.0,  0.3);
        if (Math.random() < 0.005) this.state.blinkUntil = now + 150;

        const mouthSmooth = this.state.speaking ? 0.55 : 0.2;
        this.state.mouthOpen = L(this.state.mouthOpen, this.state.targetMouth, mouthSmooth);
        // jawOpen — отдельный smooth для амплитуды (быстрее, реальный сигнал)
        const jawSmooth = this.state.speaking ? 0.6 : 0.3;
        this.state.jawOpen = L(this.state.jawOpen, this.state.targetJaw, jawSmooth);
        // Snap brows faster during active action for snappier expression transitions
        const browSmooth = actionActive ? 0.15 : 0.08;
        this.state.eyebrowY     = L(this.state.eyebrowY,     this.state.targetBrowY,   browSmooth);
        this.state.browTilt     = L(this.state.browTilt,     this.state.targetBrowTilt, browSmooth);
        this.state.cheekOpacity = L(this.state.cheekOpacity, this.state.targetCheekOp, 0.06);
        this.state.eyeBias      = L(this.state.eyeBias,      this.state.targetEyeBias, 0.15);
        this.state.tentaclePhase += dt * 2.5 * this.state.tentacleSpeed;
    }

    _set(id, t) {
        this._svgDoc.getElementById(id)?.setAttribute('transform', t);
    }

    _applyTransforms() {
        const { eyeLookX, eyeLookY, eyeScale, eyeBias, mouthOpen, eyebrowY, cheekOpacity, tentaclePhase } = this.state;

        // ── Body bob / shake + optional spin: translate on root SVG element ──
        // bodyBob and shakeX are in SVG units (viewBox 130x130)
        const bx = this.state.shakeX.toFixed(3);
        const by = this.state.bodyBob.toFixed(3);
        const spinRad = this.state._spinRotation || 0;
        if (spinRad !== 0) {
            const spinDeg = (spinRad * 180 / Math.PI).toFixed(2);
            // Rotate around centre of viewBox (65,65), then apply body jiggle
            this._svgDoc.documentElement.setAttribute('transform',
                `translate(${bx} ${by}) rotate(${spinDeg} 65 65)`);
        } else {
            this._svgDoc.documentElement.setAttribute('transform', `translate(${bx} ${by})`);
        }

        // ── Глаза: склера + зрачок + блик ────────────────────────────
        const dx = (eyeLookX * 4).toFixed(3);
        // Combined blink scale: eyeScale × eyeBias (clamped to [0.05, 1.4])
        const combinedScale = Math.max(0.05, Math.min(1.4, eyeScale * eyeBias));
        const s = combinedScale.toFixed(4);

        // Склера: только моргание (без взгляда), pivot = центр глаза
        const scleraT = (cy) =>
            `translate(0 ${(cy * (1 - combinedScale)).toFixed(3)}) scale(1 ${s})`;
        this._set('sclera_left',  scleraT(43.9));
        this._set('sclera_right', scleraT(44.0));

        // Зрачок: моргание + взгляд (+ photobooth look-down)
        const eyeLookDown = this.state._photoBoothEyeLookDown || 0;
        const pupilT = (cy) =>
            `translate(${dx} ${(eyeLookY * 4 + eyeLookDown * 4 + cy * (1 - combinedScale)).toFixed(3)}) scale(1 ${s})`;
        this._set('eye_left',  pupilT(43.9));
        this._set('eye_right', pupilT(44.0));

        // Блик: моргание + взгляд (исчезают вместе с зрачком)
        this._set('shape_35',  pupilT(43.9));
        this._set('shape_351', pupilT(44.0));

        // ── Рот ────────────────────────────────────────────────────────
        // For mode actions (sing/laugh/shout) increase mouth scaling factor
        const actionActive = this.state.actionMode && performance.now() < this.state.actionUntilTs;
        const isModeAct  = actionActive && this.isModeAction(this.state.actionMode);
        const isWhisper  = actionActive && this.state.actionMode === 'whisper';

        // ── Рот: высота = max(jawOpen, mouthOpen), ширина = viseme ──────
        // jawOpen = амплитудный сигнал (jaw track); mouthOpen = viseme fallback (если нет jaw)
        const mouthHeight = Math.max(this.state.jawOpen, mouthOpen);

        // Ширина рта по viseme (как в canvas аватаре)
        const _visemeWidths = {
            'REST': 1.00, 'A': 1.35, 'E': 1.30, 'I': 1.40, 'O': 0.82, 'U': 0.72,
            'F': 1.10, 'V': 1.10, 'L': 1.15, 'S': 1.05, 'Z': 1.05,
            'M': 0.90, 'B': 0.90, 'P': 0.90,
        };
        const visemeKey = (this.state.currentViseme || 'REST').toUpperCase();
        const visemeWidth = _visemeWidths[visemeKey] ?? 1.0;

        // Whisper форсирует узкий рот; иначе — ширина по viseme
        const mCX = 65;
        const mScaleX = isWhisper ? 0.52 : visemeWidth;
        const mDx = (mCX * (1 - mScaleX)).toFixed(3);

        // shape_38 = тёмная граница, pivot верхний край y=50.9
        const mTop = 50.9;
        const ms38Factor = isModeAct ? 3.0 : 2.0;
        const ms38 = (1 + mouthHeight * ms38Factor).toFixed(4);
        const mt38 = (mTop * (1 - parseFloat(ms38))).toFixed(3);
        this._set('shape_38', `translate(${mDx} ${mt38}) scale(${mScaleX.toFixed(3)} ${ms38})`);

        // shape_39 = оранжевая внутренность, pivot y=54.6
        const iTop = 54.6;
        const ms39Factor = isModeAct ? 3.5 : 2.5;
        const ms39 = Math.max(0.001, mouthHeight * ms39Factor).toFixed(4);
        const mt39 = (iTop * (1 - parseFloat(ms39))).toFixed(3);
        this._set('shape_39', `translate(${mDx} ${mt39}) scale(${mScaleX.toFixed(3)} ${ms39})`);

        // ── Брови: translate Y + rotate для наклона ───────────────────
        // Левая бровь: pivot внешний угол (45.4, 34.8)
        // Правая бровь: pivot внешний угол (84.6, 34.8), зеркально
        // browTilt > 0 = злость (внутренние концы вниз)
        // browTilt < 0 = грусть (внутренние концы вверх)
        const { browTilt } = this.state;
        const bdy   = (-eyebrowY * 4).toFixed(3);
        const angL  = ( browTilt * 18).toFixed(2);
        const angR  = (-browTilt * 18).toFixed(2);
        this._set('shape_71', `translate(0 ${bdy}) rotate(${angL} 45.4 34.8)`);
        this._set('shape_72', `translate(0 ${bdy}) rotate(${angR} 84.6 34.8)`);

        // ── Щёки: opacity по эмоции ────────────────────────────────────
        const cop = cheekOpacity.toFixed(3);
        this._svgDoc.getElementById('shape_40')?.setAttribute('opacity', cop);
        this._svgDoc.getElementById('shape_41')?.setAttribute('opacity', cop);

        // ── Щупальца: matrix shear (root stays, tip bends) ──────────────
        // Instead of rotate(θ, ox, oy), we use a horizontal shear matrix:
        //   matrix(1 0 k 1 -k*oy 0)
        //   x' = x + k*(y - oy)  →  attachment row (y=oy) stays fixed,
        //                            tip rows (y > oy) shift sideways by k*(y-oy)
        //   y' = y               →  no vertical change
        // This gives natural "flexible tentacle" bending: top attached, tip swings.
        const tAmp   = this.state.tentacleAmp;
        const tStyle = this.state.tentacleStyle || 'sway';

        // MAX_K limits lateral tip displacement to ≈ 0.25 × arm_length.
        const MAX_K = 0.25;
        const _shear = (id, k, oy, unclamped = false) => {
            const kc = unclamped ? k : Math.max(-MAX_K, Math.min(MAX_K, k));
            const tx = (-kc * oy).toFixed(4);
            this._set(id, `matrix(1 0 ${kc.toFixed(4)} 1 ${tx} 0)`);
        };

        for (let i = 0; i < this._arms.length; i++) {
            const [id, ox, oy] = this._arms[i];
            const phase = tentaclePhase + this._armPhaseOffsets[i];

            // ── HUG: outer arms beckon + fast tip-curl wiggle ──────────────────────
            if (tStyle === 'hug') {
                if (id === 'arm_a' || id === 'arm_b') {
                    const elapsed = (performance.now() - this.state.actionStartTs) / 1000;
                    const dir     = id === 'arm_a' ? 1 : -1;
                    // Slow beckoning: 0 → 14° → 0 at 0.8 Hz (whole arm invites)
                    const beckon  = (1 - Math.cos(elapsed * 2 * Math.PI * 0.8)) * 0.5 * 14;
                    // Fast завиток wiggle: ±8° at 4 Hz
                    // Pivot is at shoulder; tip is ~25-35px away → tip swings ±3-5px
                    // while shoulder barely moves — looks like the curl at the tip grabs
                    const curl    = Math.sin(elapsed * 2 * Math.PI * 4) * 8;
                    this._set(id, `rotate(${((beckon + curl) * dir).toFixed(2)} ${ox} ${oy})`);
                } else {
                    const k = Math.tan(Math.sin(phase) * 4 * tAmp * Math.PI / 180);
                    _shear(id, k, oy);
                }
                continue;
            }

            // ── ВОЛНА (breakdance wave): sharp sequential pulse left → right ──
            if (tStyle === 'wave_seq') {
                // Visual left→right order:
                //   pos 0=arm_f(5)  1=arm_a(0)  2=arm_d(3)  3=arm_e(4)
                //       4=arm_g(6)  5=arm_c(2)  6=arm_b(1)
                const _WAVE_POS = [1, 6, 5, 2, 3, 0, 4];
                const spread = (2 * Math.PI) / this._arms.length;
                const s      = Math.sin(tentaclePhase * 1.0 + _WAVE_POS[i] * spread);
                // sin²·sign sharpens the pulse: only the arm near peak deflects
                // fully (45°); neighbours are nearly neutral → clear left→right wave.
                const angleDeg = Math.sign(s) * s * s * 45;
                this._set(id, `rotate(${angleDeg.toFixed(2)} ${ox} ${oy})`);
                continue;
            }

            // ── All other styles: shear (root fixed, tip bends) ───────
            let wobble = Math.sin(tentaclePhase + i * 0.9) * 8;

            if (tStyle === 'flutter') {
                wobble += Math.sin(phase * 2.5) * 6;
            } else if (tStyle === 'lash') {
                const saw = ((phase % (Math.PI * 2)) / Math.PI) - 1;
                wobble = saw * 12;
            } else if (tStyle === 'tremble') {
                wobble = Math.sin(phase * 4.5 + i * 0.35) * 8;
            } else if (tStyle === 'droop') {
                wobble = Math.sin(phase) * 4;
            } else if (tStyle === 'probe') {
                wobble += Math.sin(phase * 1.7 + i) * 8;
            }
            // 'sway' uses the base wobble as-is

            const angleDeg = wobble * tAmp;
            const k = Math.tan(angleDeg * Math.PI / 180);
            _shear(id, k, oy);
        }

        // ── Heart pose: show/hide overlay arms and swap shape_151 path ──────────
        if (this._heartPaths) {
            const isHeart = tStyle === 'heart';

            // On state change: swap shape_151 path + show/hide original arm bodies
            if (isHeart !== this._heartPaths.active) {
                this._heartPaths.active = isHeart;
                this._svgDoc.getElementById('shape_151')?.setAttribute('d',
                    isHeart ? this._heartPaths.heart151 : this._heartPaths.idle151);
                const armOp = isHeart ? '0' : '1';
                for (const hid of this._heartHideIds) {
                    this._svgDoc.getElementById(hid)?.setAttribute('opacity', armOp);
                }
            }

            // Show/hide heart arm overlays
            if (this._heartArmEls) {
                const op = isHeart ? '1' : '0';
                for (const el of this._heartArmEls) {
                    el.setAttribute('opacity', op);
                }
            }
        }

        // ── Clap pose: hold pose for full action, pulse arms 8× per second ──────
        if (this._clapPaths) {
            const isClap = tStyle === 'clap';

            // Pose toggle only on enter/exit — never mid-action
            if (isClap !== this._clapPaths.active) {
                this._clapPaths.active = isClap;
                this._svgDoc.getElementById('shape_151')?.setAttribute('d',
                    isClap ? this._clapPaths.clap151 : this._clapPaths.idle151);
                const armOp = isClap ? '0' : '1';
                for (const hid of this._clapHideIds) {
                    this._svgDoc.getElementById(hid)?.setAttribute('opacity', armOp);
                }
                if (this._clapArmEls) {
                    const op = isClap ? '1' : '0';
                    for (const el of this._clapArmEls) {
                        el.setAttribute('opacity', op);
                        if (!isClap) el.removeAttribute('transform');
                    }
                }
            }

            // Beat animation: arms hit each other 8×/sec, sharp attack pulse
            // indices 0-4 = arm_c1 (right arm) → moves left on hit
            // indices 5-9 = arm_main (left arm) → moves right on hit
            if (isClap && this._clapArmEls) {
                const elapsed = (performance.now() - this.state.actionStartTs) / 1000;
                // Sharp pulse: pow(0.3) gives quick attack, soft release
                const beat = Math.pow(Math.max(0, Math.sin(elapsed * 8 * Math.PI)), 0.3);
                const dx = (beat * 5).toFixed(2);
                for (let i = 0; i < this._clapArmEls.length; i++) {
                    const tx = i < 5 ? -dx : dx;
                    this._clapArmEls[i].setAttribute('transform', `translate(${tx} 0)`);
                }
            }
        }

        // ── Hug pose: swap paths + z-reorder arms ─────────────────────────────────
        if (this._hugPaths) {
            const isHug = tStyle === 'hug';
            if (isHug !== this._hugPaths.active) {
                this._hugPaths.active = isHug;
                for (const { el, idleD, hugD } of this._hugSwaps) {
                    el.setAttribute('d', isHug ? hugD : idleD);
                }
                const root = this._svgDoc.documentElement;
                if (isHug) {
                    // Move arm_b then arm_a to end of SVG → rendered on top of body
                    root.appendChild(this._hugArmB);
                    root.appendChild(this._hugArmA);
                } else {
                    // Restore original z-positions
                    if (this._hugArmANext) root.insertBefore(this._hugArmA, this._hugArmANext);
                    else root.appendChild(this._hugArmA);
                    if (this._hugArmBNext) root.insertBefore(this._hugArmB, this._hugArmBNext);
                    else root.appendChild(this._hugArmB);
                }
            }
        }

        this._updateSvgFx();

        // Пересоздаём Picture каждый кадр — только так ThorVG видит изменения SVG
        const svg = this._ser.serializeToString(this._svgDoc);
        this.tvgCanvas.remove(this.picture);
        this.picture = new this.TVG.Picture();
        this.picture.load(svg, { type: 'svg' });
        this.picture.size(this.opts.width, this.opts.height);
        this.tvgCanvas.add(this.picture);
    }

    // ── SVG particle FX ──────────────────────────────────────────────────

    _spawnSvgFx(type, opts = {}) {
        const ns  = 'http://www.w3.org/2000/svg';
        const now = performance.now();
        const root = this._svgDoc.documentElement;

        const _rand = () => Math.random();

        if (type === 'heart') {
            const count = opts.count || 6;
            for (let k = 0; k < count; k++) {
                const el = this._svgDoc.createElementNS(ns, 'path');
                el.setAttribute('d', 'M0,-5C0,-8.5,-5.5,-8.5,-5.5,-3.5C-5.5,1,0,6,0,6C0,6,5.5,1,5.5,-3.5C5.5,-8.5,0,-8.5,0,-5Z');
                el.setAttribute('fill', '#ff6b9d');
                el.setAttribute('stroke', 'none');
                el.setAttribute('opacity', '0');
                root.appendChild(el);
                const size = 0.4 + _rand() * 0.3;   // heart ≈ 6–10 SVG units tall
                this._svgFx.push({
                    type: 'heart', el,
                    x0: 45 + _rand() * 40, y0: 75 + _rand() * 15,
                    vx: (_rand() - 0.5) * 12, vy: -(22 + _rand() * 12),
                    size,
                    startTs: now + k * 180,
                    durationMs: 1300 + _rand() * 500,
                });
            }
        } else if (type === 'tear') {
            const el = this._svgDoc.createElementNS(ns, 'ellipse');
            el.setAttribute('rx', '1.5');
            el.setAttribute('ry', '2.5');
            el.setAttribute('fill', '#6ec6ff');
            root.appendChild(el);
            this._svgFx.push({
                type: 'tear', el,
                x0: opts.x || 52, y0: opts.y || 50,
                vx: 0, vy: opts.vy || 40,
                size: 1,
                startTs: now, durationMs: 1600,
            });
        } else if (type === 'sweat') {
            const el = this._svgDoc.createElementNS(ns, 'ellipse');
            el.setAttribute('rx', '1.5');
            el.setAttribute('ry', '2.5');
            el.setAttribute('fill', '#8ad4ff');
            root.appendChild(el);
            this._svgFx.push({
                type: 'sweat', el,
                x0: opts.x || 78, y0: opts.y || 45,
                vx: 0, vy: opts.vy || 40,
                size: 1,
                startTs: now, durationMs: 1600,
            });
        } else if (type === 'sparkle') {
            const speed = 50;
            for (let k = 0; k < 6; k++) {
                const el = this._svgDoc.createElementNS(ns, 'path');
                el.setAttribute('d', 'M0,-6L1,-1L6,0L1,1L0,6L-1,1L-6,0L-1,-1Z');
                el.setAttribute('fill', '#ffdd44');
                el.setAttribute('opacity', '0');
                root.appendChild(el);
                const angle = (k / 6) * 2 * Math.PI;
                this._svgFx.push({
                    type: 'sparkle', el,
                    x0: 65, y0: 30,
                    vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed,
                    size: 3.5,
                    startTs: now, durationMs: 900,
                });
            }
        } else if (type === 'pop') {
            const el = this._svgDoc.createElementNS(ns, 'circle');
            const r0 = opts.size || 10;
            el.setAttribute('cx', '65');
            el.setAttribute('cy', '55');
            el.setAttribute('r',  String(r0));
            el.setAttribute('stroke', '#ffd166');
            el.setAttribute('stroke-width', '2.5');
            el.setAttribute('fill', 'none');
            root.appendChild(el);
            this._svgFx.push({
                type: 'pop', el,
                r0,
                startTs: now, durationMs: 600,
            });
        } else if (type === 'bubble') {
            const count = opts.count || 4;
            for (let k = 0; k < count; k++) {
                const el = this._svgDoc.createElementNS(ns, 'circle');
                el.setAttribute('r', String(opts.size || 4));
                el.setAttribute('fill', 'none');
                el.setAttribute('stroke', '#b5eaff');
                el.setAttribute('stroke-width', '1.5');
                el.setAttribute('opacity', '0');
                root.appendChild(el);
                this._svgFx.push({
                    type: 'bubble', el,
                    x0: 60 + _rand() * 10, y0: 85 + _rand() * 10,
                    vx: (_rand() - 0.5) * 8, vy: -(20 + _rand() * 15),
                    size: 1,
                    startTs: now + k * 120, durationMs: 1400 + _rand() * 400,
                });
            }
        } else if (type === 'flash') {
            const el = this._svgDoc.createElementNS(ns, 'rect');
            el.setAttribute('x', '0');
            el.setAttribute('y', '0');
            el.setAttribute('width', '130');
            el.setAttribute('height', '130');
            el.setAttribute('fill', 'white');
            root.appendChild(el);
            this._svgFx.push({
                type: 'flash', el,
                startTs: now, durationMs: 600,
            });
        }
    }

    _updateSvgFx() {
        if (!this._svgFx || this._svgFx.length === 0) return;
        const now = performance.now();
        const surviving = [];
        for (const fx of this._svgFx) {
            const { el, startTs, durationMs } = fx;
            if (now < startTs) { surviving.push(fx); continue; }
            const age = now - startTs;
            const p   = age / durationMs;
            if (p >= 1) {
                el.parentNode?.removeChild(el);
                continue;
            }
            if (fx.type === 'pop') {
                el.setAttribute('r',       (fx.r0 + fx.r0 * 1.5 * p).toFixed(2));
                el.setAttribute('opacity', (1 - p).toFixed(3));
            } else if (fx.type === 'flash') {
                el.setAttribute('opacity', (1 - p).toFixed(3));
            } else {
                const x     = fx.x0 + fx.vx * (age / 1000);
                const y     = fx.y0 + fx.vy * (age / 1000);
                const alpha = p < 0.25 ? p / 0.25 : 1 - (p - 0.25) / 0.75;
                el.setAttribute('transform', `translate(${x.toFixed(2)} ${y.toFixed(2)}) scale(${fx.size})`);
                el.setAttribute('opacity', alpha.toFixed(3));
            }
            surviving.push(fx);
        }
        this._svgFx = surviving;
    }

    // ── Public API ────────────────────────────────────────────────────────

    lookAt(x, y) {
        // Усиление чувствительности как в canvas аватаре (2.8x/2.5x → кламп ±1)
        // Эффект: g.x=0.36 уже насыщает взгляд, движение заметнее на малых значениях
        this.state.targetEyeX = Math.max(-1, Math.min(1, x * 2.8));
        this.state.targetEyeY = Math.max(-1, Math.min(1, y * 2.5));
    }
    blink() { this.state.blinkUntil = performance.now() + 150; }
    setMouth(v) { this.state.targetMouth = Math.max(0, Math.min(1, v)); }

    setEmotion(e) {
        this.state.emotion = e;
        const emotions = {
            //             browY   cheek  mouth  tilt
            calm:    [   0,    0.4,   0,     0    ],
            happy:   [   0.6,  1.0,   0.4,   0    ],
            excited: [   0.9,  1.0,   0.7,   0    ],
            playful: [   0.8,  1.0,   0.5,   0    ],
            sad:     [  -0.5,  0.15,  0,    -0.6  ],  // внутренние концы вверх
            tender:  [  -0.4,  0.2,   0,    -0.5  ],
            angry:   [  -0.8,  0,     0,     1.0  ],  // внутренние концы вниз (V)
            curious: [   0.8,  0.5,   0,    -0.2  ],  // лёгкий вопросительный наклон
            confused:[   0.3,  0.3,   0,    -0.4  ],
            proud:   [   0.5,  0.7,   0.2,   0    ],
            sarcastic:[  0.4,  0.35,  0,     0.2  ],
        };
        const [browY, cheek, mouth, tilt] = emotions[e] ?? [0, 0.4, 0, 0];
        this.state.targetBrowY    = browY;
        this.state.targetCheekOp  = cheek;
        this.state.targetBrowTilt = tilt;
        if (!this.state.speaking) this.state.targetMouth = mouth;

        // Eye bias per emotion (matching canvas animator)
        if (e === 'angry') {
            this.state.targetEyeBias = 0.82;
        } else if (e === 'sad' || e === 'tender') {
            this.state.targetEyeBias = 0.88;
        } else if (e === 'excited' || e === 'playful' || e === 'happy') {
            this.state.targetEyeBias = 1.10;
        } else if (e === 'curious' || e === 'confused') {
            this.state.targetEyeBias = 1.15;
        } else if (e === 'proud') {
            this.state.targetEyeBias = 1.05;
        } else if (e === 'sarcastic') {
            this.state.targetEyeBias = 0.96;
        } else {
            this.state.targetEyeBias = 1.0;
        }

        // Arm style per emotion (matching canvas animator)
        if (e === 'excited' || e === 'playful' || e === 'happy') {
            this.state.tentacleStyle = 'flutter';
            this.state.tentacleSpeed = 2.4;
            this.state.tentacleAmp   = 2.2;
        } else if (e === 'sad' || e === 'tender') {
            this.state.tentacleStyle = 'droop';
            this.state.tentacleSpeed = 0.6;
            this.state.tentacleAmp   = 0.7;
        } else if (e === 'angry') {
            this.state.tentacleStyle = 'lash';
            this.state.tentacleSpeed = 2.8;
            this.state.tentacleAmp   = 1.8;
        } else if (e === 'proud') {
            this.state.tentacleStyle = 'sway';
            this.state.tentacleSpeed = 1.2;
            this.state.tentacleAmp   = 1.6;
        } else if (e === 'sarcastic' || e === 'curious' || e === 'confused') {
            this.state.tentacleStyle = 'probe';
            this.state.tentacleSpeed = e === 'curious' ? 1.6 : 0.9;
            this.state.tentacleAmp   = e === 'curious' ? 1.7 : (e === 'confused' ? 1.1 : 0.9);
        } else if (e === 'calm') {
            this.state.tentacleStyle = 'sway';
            this.state.tentacleSpeed = 0.8;
            this.state.tentacleAmp   = 0.9;
        } else {
            this.state.tentacleStyle = 'sway';
            this.state.tentacleSpeed = 1.0;
            this.state.tentacleAmp   = 1.2;
        }

        this.maybeTriggerGestureFromEmotion(e);
    }

    activateAction(name, durationMs) {
        const dur = Number.isFinite(durationMs) ? durationMs : 1400;
        const now = performance.now();
        this.state.actionMode    = name;
        this.state.actionStartTs = now;
        this.state.actionUntilTs = now + dur;
        console.log(`🐙 action: ${name} for ${dur}ms, face:`, _OCTO_ACTION_FACE[name]);
    }

    isModeAction(name) {
        return ['sing', 'laugh', 'whisper', 'shout', 'sfx_spin'].includes(name);
    }

    triggerFxFromAction(action) {
        if (!action) return;
        if (action === 'sfx_heart' || action === 'heart') {
            this._spawnSvgFx('heart', { count: 6 });
        } else if (action === 'sfx_tear') {
            this._spawnSvgFx('tear', { x: 52, y: 50, vy: 45 });
        } else if (action === 'sfx_sweat') {
            this._spawnSvgFx('sweat', { x: 78, y: 45, vy: 38 });
        } else if (action === 'sfx_sparkle') {
            this._spawnSvgFx('sparkle', {});
        } else if (action === 'sfx_pop') {
            this._spawnSvgFx('pop', { size: 10 });
        } else if (action === 'sfx_boop') {
            this._spawnSvgFx('pop', { size: 7 });
        } else if (action === 'sfx_bubble' || action === 'sfx_wave') {
            this._spawnSvgFx('bubble', { count: 4 });
        } else if (action === 'photobooth') {
            setTimeout(() => this._spawnSvgFx('flash', {}), 800);
        }
    }
    triggerGesture(name, opts = {}) {
        const now = performance.now();
        const { force } = opts;
        if (!force && now - this.state.lastGestureTs < 10000) return;
        if (!force && this.state.lastGesture === name) return;
        const durationMs = {
            heart: 2200, wave: 2000, clap: 1200, point: 1200,
            hug: 1600,   shrug: 1000, sing: 1600, laugh: 1200,
            whisper: 900, shout: 900, wipe: 900,
            sfx_pop: 700, sfx_sparkle: 900, sfx_boop: 700,
            sfx_wave: 900, sfx_spin: 1400, sfx_tear: 800,
            sfx_sweat: 800, sfx_heart: 1000, sfx_bubble: 1200,
            photobooth: 1200,
        }[name] || 1200;
        this.state.lastGesture   = name;
        this.state.lastGestureTs = now;
        this.activateAction(name, durationMs);
    }

    maybeTriggerGestureFromEmotion(emotion) {
        const now = performance.now();
        if (now - this.state.lastGestureTs < 15000) return;
        const map = {
            happy:   { name: 'wave',  p: 0.20 },
            excited: { name: 'clap',  p: 0.10 },
            playful: { name: 'wave',  p: 0.20 },
            tender:  { name: 'heart', p: 0.10 },
            sad:     { name: 'hug',   p: 0.08 },
            curious: { name: 'point', p: 0.15 },
            confused:{ name: 'shrug', p: 0.12 },
        };
        const choice = map[emotion];
        if (choice && Math.random() < choice.p) {
            this.triggerGesture(choice.name, { force: false });
        }
    }

    setSpeaking(speaking, amplitude) {
        this.state.speaking = speaking;
        if (speaking && typeof amplitude === 'number') this.state.targetMouth = amplitude;
        if (!speaking) this.state.targetMouth = 0;
    }

    handleCommand(cmd) {
        if (!cmd) return;

        // ── Action ───────────────────────────────────────────────────────
        if (cmd.cmd === 'action' && cmd.action) {
            const durationMs = Number(cmd.duration_ms) || 1400;
            this.activateAction(cmd.action, durationMs);
            this.triggerFxFromAction(cmd.action);
            if (!this.isModeAction(cmd.action)) this.triggerGesture(cmd.action, { force: true });
            return;
        }

        // ── audio_sync: основной lip sync ────────────────────────────────
        if (cmd.cmd === 'audio_sync') {
            this.state.speaking = cmd.speaking !== false;
            if (cmd.emotion?.value) this.setEmotion(cmd.emotion.value);
            if (cmd.action && cmd.action !== 'none') {
                const durationMs = Math.max(300, Math.round((cmd.duration_s || 0.4) * 1000));
                this.activateAction(cmd.action, durationMs);
                this.triggerFxFromAction(cmd.action);
            }

            // Сброс при начале новой реплики
            if (typeof cmd.start_s === 'number' && cmd.start_s <= 0.001) {
                this.state.jawSeq = []; this.state.jawIdx = 0;
                this.state.jawActive = false; this.state.jawScheduleTs = 0;
                this.state.targetJaw = 0; this.state.jawOpen = 0;
                this.state.visemeSeq = []; this.state.visemeIdx = 0;
                this.state.visemeActive = false; this.state.visemeScheduleTs = 0;
                this.state.currentViseme = 'REST';
                this.state.pendingEnd = false;
            }

            const now = performance.now();
            let startTs = now;

            // Синхронизация с аудиоплеером
            if (typeof cmd.start_s === 'number' && typeof window.getAudioPlayheadS === 'function') {
                const playhead = window.getAudioPlayheadS();
                if (cmd.start_s <= 0.001) this.state.responseStartPlayheadS = playhead;
                const responsePlayhead = Math.max(0, playhead - this.state.responseStartPlayheadS);
                startTs = now + (cmd.start_s - responsePlayhead) * 1000;
            }

            // Не начинать раньше хвоста предыдущего пакета
            const tail = Math.max(this.state.jawScheduleTs || 0, this.state.visemeScheduleTs || 0);
            if (tail > startTs) startTs = tail;

            // ── Jaw track ──────────────────────────────────────────────
            const jawVals = cmd.jaw?.values;
            const ampVals = cmd.amplitudes; // legacy fallback
            const rawJaw  = (jawVals?.length ? jawVals : ampVals?.length ? ampVals : null);
            if (rawJaw) {
                const step = Math.max(10, (jawVals ? (cmd.jaw.step_ms || 20) : 20));
                let seq = rawJaw.slice();
                let dur = seq.length * step;
                if (startTs < now) {
                    const lag = now - startTs;
                    if (lag >= dur) { startTs = now; }
                    else {
                        const skip = Math.min(seq.length - 1, Math.floor(lag / step));
                        if (skip > 0) { seq = seq.slice(skip); startTs += skip * step; dur = seq.length * step; }
                    }
                }
                if (this.state.jawSeq.length && step === this.state.jawStepMs) {
                    this.state.jawSeq = this.state.jawSeq.concat(seq);
                } else {
                    this.state.jawSeq = seq; this.state.jawStepMs = step; this.state.jawIdx = 0;
                }
                if (!this.state.jawActive) this.state.jawNextTs = startTs;
                this.state.jawActive = true;
                this.state.jawScheduleTs = startTs + dur;
            }

            // ── Viseme proxy track ─────────────────────────────────────
            const vpVals = cmd.viseme_proxy?.values ?? cmd.proxyVisemes;
            if (vpVals?.length) {
                const step = Math.max(20, (cmd.viseme_proxy ? (cmd.viseme_proxy.step_ms || 50) : 50));
                let seq = vpVals.slice();
                let dur = seq.length * step;
                if (startTs < now) {
                    const lag = now - startTs;
                    if (lag >= dur) { startTs = now; }
                    else {
                        const skip = Math.min(seq.length - 1, Math.floor(lag / step));
                        if (skip > 0) { seq = seq.slice(skip); startTs += skip * step; dur = seq.length * step; }
                    }
                }
                if (this.state.visemeSeq.length && step === this.state.visemeStepMs) {
                    this.state.visemeSeq = this.state.visemeSeq.concat(seq);
                } else {
                    this.state.visemeSeq = seq; this.state.visemeStepMs = step; this.state.visemeIdx = 0;
                }
                if (!this.state.visemeActive) this.state.visemeNextTs = startTs;
                this.state.visemeActive = true;
                this.state.visemeScheduleTs = startTs + dur;
            }

            return;
        }

        // ── Прямая амплитуда рта ─────────────────────────────────────────
        if (cmd.cmd === 'mouth') {
            this.state.speaking = cmd.speaking !== false;
            if (typeof cmd.value === 'number') this.state.targetMouth = cmd.value;
            if (!this.state.speaking) this.state.targetMouth = 0;
            return;
        }

        // ── Конец речи ───────────────────────────────────────────────────
        if (cmd.cmd === 'end') {
            if (this.state.jawActive || this.state.visemeActive) {
                this.state.pendingEnd = true;
                return;
            }
            this.state.targetMouth = 0;
            this.state.speaking = false;
            this.state.pendingEnd = false;
            if (cmd.emotion) this.setEmotion(cmd.emotion);
            return;
        }

        // ── Взгляд ───────────────────────────────────────────────────────
        if (cmd.cmd === 'gaze') {
            const g = cmd.gaze || {};
            this.lookAt(g.x || 0, g.y || 0);
            if (g.blink) this.blink();
            return;
        }

        // ── Эмоция ───────────────────────────────────────────────────────
        if (cmd.emotion && (!cmd.cmd || cmd.cmd === 'emotion')) {
            this.setEmotion(cmd.emotion);
        }
    }
}

if (typeof module !== 'undefined') module.exports = OctopuzzAvatar;
