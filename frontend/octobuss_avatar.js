/**
 * OctobussAvatar — рантайм-риг для octobuss.rigged.svg.
 *
 * Щупальца = FK-цепочки костей по data-spine; «кожа» (контур, тень,
 * присоски, пятна, манжеты) пересобирается каждый кадр вокруг сплайна,
 * поэтому щупальца реально СГИБАЮТСЯ, а не поворачиваются целиком.
 *
 * Совместим с avatar-proxy из index.html:
 *   handleCommand(cmd)  — audio_sync / sync / mouth / action / end / emotion / gaze
 *   setEmotion(name), blink(), activateAction(name, ms),
 *   triggerGesture(name, opts), triggerFxFromAction(name)
 *
 * AI-API поз:
 *   avatar.setPose('wave_right', {durationMs: 600})
 *   avatar.setPose({tentacle_up_r: {rot: -0.6, curl: 1.2, straighten: 0.5}})
 *   avatar.setTentacle('tentacle_up_r', {curl: 2.0}, 800)
 * Параметры щупальца:
 *   rot        — поворот у корня, рад (знак: экранный CW)
 *   curl       — до-сгиб вдоль всей цепочки, ед. «естественного» завитка
 *   straighten — 0..1 разгибание (1 = прямая линия от корня)
 *   stretch    — 0.8..1.2 удлинение
 *   swingAmp/swingSpeed — циклический мах (для wave/clap)
 */
"use strict";

(function () {

// ---------------------------------------------------------------- геометрия
function crPoint(p0, p1, p2, p3, t) {
    const t2 = t * t, t3 = t2 * t;
    return [
        0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
        0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3),
    ];
}

function sampleSpine(pts, perSeg) {
    const ext = [pts[0], ...pts, pts[pts.length - 1]];
    const out = [];
    for (let i = 0; i < pts.length - 1; i++) {
        for (let j = 0; j < perSeg; j++) {
            out.push(crPoint(ext[i], ext[i + 1], ext[i + 2], ext[i + 3], j / perSeg));
        }
    }
    out.push(pts[pts.length - 1]);
    return out;
}

function tangentsOf(P) {
    const T = [];
    for (let i = 0; i < P.length; i++) {
        const a = P[Math.max(0, i - 1)], b = P[Math.min(P.length - 1, i + 1)];
        const dx = b[0] - a[0], dy = b[1] - a[1];
        const l = Math.hypot(dx, dy) || 1;
        T.push([dx / l, dy / l]);
    }
    return T;
}

const widthAt = (t, w0, w1, taper) => w0 + (w1 - w0) * Math.pow(t, taper);
function normAng(a) {
    while (a <= -Math.PI) a += 2 * Math.PI;
    while (a > Math.PI) a -= 2 * Math.PI;
    return a;
}

function capPoints(c, r, aFrom, aMid, aTo, steps) {
    const pts = [];
    for (let k = 1; k <= steps; k++) {
        const a = aFrom + normAng(aMid - aFrom) * k / steps;
        pts.push([c[0] + r * Math.cos(a), c[1] + r * Math.sin(a)]);
    }
    for (let k = 1; k <= steps; k++) {
        const a = aMid + normAng(aTo - aMid) * k / steps;
        pts.push([c[0] + r * Math.cos(a), c[1] + r * Math.sin(a)]);
    }
    return pts;
}

function polyPath(pts) {
    let d = `M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
    for (let i = 1; i < pts.length; i++) d += `L${pts[i][0].toFixed(1)} ${pts[i][1].toFixed(1)}`;
    return d + "Z";
}

// ---------------------------------------------------------------- щупальце
const PER_SEG = 12;
const PARAM_KEYS = ["rot", "curl", "straighten", "stretch", "swingAmp", "swingSpeed", "swingPhase", "waveMul"];
const PARAM_DEFAULTS = { rot: 0, curl: 0, straighten: 0, stretch: 1, swingAmp: 0, swingSpeed: 5, swingPhase: 0, waveMul: 1 };

// направление «естественного» завитка кончика (см. генератор)
const CURL_DIR = {
    tentacle_up_l: -1, tentacle_up_r: 1, tentacle_band_l: 1, tentacle_far_r: 1,
    tentacle_front_l: -1, tentacle_front_c: -1, tentacle_front_r: -1,
};

class Tentacle {
    constructor(g) {
        this.g = g;
        this.id = g.id;
        this.basePts = g.dataset.spine.trim().split(/\s+/).map(s => s.split(",").map(Number));
        this.w0 = Number(g.dataset.w0);
        this.w1 = Number(g.dataset.w1);
        this.taper = Number(g.dataset.taper || 1.2);
        this.side = Number(g.dataset.side || 1);
        this.curlDir = CURL_DIR[this.id] || 1;
        this.behindBody = !!g.closest('#tentacles_back');

        // FK-декомпозиция: длины и относительные углы сегментов
        const m = this.basePts.length;
        this.segLen = []; this.segRel = [];
        let prevAbs = 0;
        for (let i = 0; i < m - 1; i++) {
            const dx = this.basePts[i + 1][0] - this.basePts[i][0];
            const dy = this.basePts[i + 1][1] - this.basePts[i][1];
            const abs = Math.atan2(dy, dx);
            this.segLen.push(Math.hypot(dx, dy));
            this.segRel.push(i === 0 ? abs : normAng(abs - prevAbs));
            prevAbs = abs;
        }
        // веса распределения curl по суставам (сильнее к кончику)
        const n = this.segLen.length;
        let wsum = 0;
        this.curlW = [];
        for (let i = 1; i < n; i++) { const w = Math.pow(i / (n - 1), 1.2); this.curlW.push(w); wsum += w; }
        this.curlW = this.curlW.map(w => w / wsum);

        // элементы кожи
        this.elMain = g.querySelector(".t-main");
        this.elShade = g.querySelector(".t-shade");
        this.spots = [...g.querySelectorAll(".t-spot")].map(el => ({ el, t: +el.dataset.t, scale: +el.dataset.scale }));
        this.suckers = [...g.querySelectorAll(".t-sucker")].map(el => ({ el, t: +el.dataset.t, scale: +el.dataset.scale, kind: el.dataset.kind }));
        this.bands = [...g.querySelectorAll(".t-band")].map(el => ({ el, t: +el.dataset.t, part: el.dataset.part }));

        this.cur = { ...PARAM_DEFAULTS };
        this.tgt = { ...PARAM_DEFAULTS };
        this.tau = 0.25; // сек, скорость перехода
        this._dirty = true;
    }

    setTarget(params, durationMs) {
        for (const k of PARAM_KEYS) {
            if (params[k] !== undefined) this.tgt[k] = params[k];
        }
        // сброс не указанных к дефолту, если params.__absolute
        if (params.__absolute) {
            for (const k of PARAM_KEYS) this.tgt[k] = (params[k] !== undefined) ? params[k] : PARAM_DEFAULTS[k];
        }
        if (durationMs) this.tau = Math.max(0.05, durationMs / 4000);
        this._clampVisibility();
    }

    /** хребет для заданных параметров (без идл-волны; для проверки позы) */
    spineFor(p) {
        const ROT_W = [0, 0.45, 0.35, 0.20];
        const n = this.segLen.length;
        const pts = [this.basePts[0].slice()];
        let acc = this.segRel[0];
        let x = pts[0][0], y = pts[0][1];
        for (let i = 0; i < n; i++) {
            if (i > 0) {
                acc += this.segRel[i] * (1 - p.straighten)
                     + p.rot * (ROT_W[i] || 0)
                     + p.curl * this.curlDir * this.curlW[i - 1];
            }
            x += this.segLen[i] * p.stretch * Math.cos(acc);
            y += this.segLen[i] * p.stretch * Math.sin(acc);
            pts.push([x, y]);
        }
        return pts;
    }

    tipVisible(pts) {
        const [tx, ty] = pts[pts.length - 1];
        const M = 30;
        if (tx < M || tx > 2048 - M || ty < M || ty > 2048 - M) return false;
        // кончик за стеклом шлема не виден
        const gx = (tx - 1041) / 525, gy = (ty - 722) / 487;
        if (gx * gx + gy * gy < 1) return false;
        // щупальца заднего слоя прячутся за телом-перепонкой
        if (this.behindBody) {
            const wx = (tx - 1024) / 400, wy = (ty - 1330) / 245;
            if (wx * wx + wy * wy < 1) return false;
        }
        return true;
    }

    /** если целевая поза уводит кончик за шлем или за край холста —
     *  пропорционально уменьшаем отклонение от rest до видимой зоны */
    _clampVisibility() {
        const mix = (s) => {
            const p = {};
            for (const k of PARAM_KEYS) p[k] = PARAM_DEFAULTS[k] + (this.tgt[k] - PARAM_DEFAULTS[k]) * s;
            return p;
        };
        const ok = (s) => {
            const p = mix(s);
            for (const off of (p.swingAmp ? [p.swingAmp, -p.swingAmp] : [0])) {
                if (!this.tipVisible(this.spineFor({ ...p, rot: p.rot + off }))) return false;
            }
            return true;
        };
        if (ok(1)) return;
        let lo = 0, hi = 1;
        for (let i = 0; i < 7; i++) { const mid = (lo + hi) / 2; ok(mid) ? lo = mid : hi = mid; }
        const p = mix(lo);
        for (const k of PARAM_KEYS) this.tgt[k] = p[k];
    }

    /** пересборка точек хребта из костей.
     *  Корневой сегмент неподвижен (основание приросло к телу):
     *  rot распределяется по суставам 1..3, поэтому щель у корня не открывается. */
    buildSpine(clock) {
        const p = this.cur;
        const rot = p.rot + (p.swingAmp ? p.swingAmp * Math.sin(clock * p.swingSpeed + p.swingPhase) : 0);
        const ROT_W = [0, 0.45, 0.35, 0.20]; // веса поворота по суставам
        const n = this.segLen.length;
        const pts = [this.basePts[0].slice()];
        let acc = this.segRel[0];
        let x = pts[0][0], y = pts[0][1];
        for (let i = 0; i < n; i++) {
            if (i > 0) {
                let d = this.segRel[i] * (1 - p.straighten);
                d += rot * (ROT_W[i] || 0);
                d += p.curl * this.curlDir * this.curlW[i - 1];
                // бегущая волна (идл), сильнее к кончику
                const damp = Math.pow(i / (n - 1), 1.4);
                d += 0.10 * p.waveMul * damp * Math.sin(clock * 2.2 - i * 0.85);
                acc += d;
            }
            x += this.segLen[i] * p.stretch * Math.cos(acc);
            y += this.segLen[i] * p.stretch * Math.sin(acc);
            pts.push([x, y]);
        }
        return pts;
    }

    update(dt, clock) {
        // сглаживание параметров
        const k = 1 - Math.exp(-dt / this.tau);
        let moving = false;
        for (const key of PARAM_KEYS) {
            const d = this.tgt[key] - this.cur[key];
            if (Math.abs(d) > 1e-4) { this.cur[key] = this.cur[key] + d * k; moving = true; }
        }
        // волна/мах активны всегда при waveMul>0
        const animated = moving || this.cur.waveMul > 0.01 || Math.abs(this.cur.swingAmp) > 0.01;
        if (!animated && !this._dirty) return;
        this._dirty = false;

        const spine = this.buildSpine(clock);
        const P = sampleSpine(spine, PER_SEG);
        const T = tangentsOf(P);
        const N = P.length;
        const { w0, w1, taper, side } = this;

        // контур
        const L = [], R = [];
        for (let i = 0; i < N; i++) {
            const t = i / (N - 1);
            const w = widthAt(t, w0, w1, taper) / 2;
            const nx = -T[i][1], ny = T[i][0];
            L.push([P[i][0] + nx * w, P[i][1] + ny * w]);
            R.push([P[i][0] - nx * w, P[i][1] - ny * w]);
        }
        const tipC = P[N - 1], wt = widthAt(1, w0, w1, taper) / 2;
        const tip = capPoints(tipC, wt,
            Math.atan2(L[N - 1][1] - tipC[1], L[N - 1][0] - tipC[0]),
            Math.atan2(T[N - 1][1], T[N - 1][0]),
            Math.atan2(R[N - 1][1] - tipC[1], R[N - 1][0] - tipC[0]), 6);
        const rootC = P[0], wr = widthAt(0, w0, w1, taper) / 2;
        const root = capPoints(rootC, wr,
            Math.atan2(R[0][1] - rootC[1], R[0][0] - rootC[0]),
            Math.atan2(-T[0][1], -T[0][0]),
            Math.atan2(L[0][1] - rootC[1], L[0][0] - rootC[0]), 6);
        this.elMain.setAttribute("d", polyPath([...root, ...L, ...tip, ...R.reverse()]));
        R.reverse(); // вернуть порядок для дальнейших расчётов

        // тень по нижней кромке
        if (this.elShade) {
            const i0 = Math.floor(0.02 * (N - 1)), i1 = Math.floor(0.98 * (N - 1));
            const span = Math.max(1, i1 - i0);
            const outer = [], inner = [];
            for (let i = i0; i <= i1; i++) {
                const t = i / (N - 1);
                const w = widthAt(t, w0, w1, taper);
                const nx = -T[i][1] * side, ny = T[i][0] * side;
                const f = Math.min(1, (i - i0) / (span * 0.14), (i1 - i) / (span * 0.14));
                const wi = w * 0.5 - (w * 0.5 - w * 0.06) * f;
                outer.push([P[i][0] + nx * w * 0.5, P[i][1] + ny * w * 0.5]);
                inner.push([P[i][0] + nx * wi, P[i][1] + ny * wi]);
            }
            this.elShade.setAttribute("d", polyPath([...outer, ...inner.reverse()]));
        }

        // присоски / пятна
        const place = (t) => {
            const i = Math.min(N - 1, Math.max(0, Math.round(t * (N - 1))));
            return { p: P[i], tg: T[i], w: widthAt(i / (N - 1), w0, w1, taper) };
        };
        for (const s of this.suckers) {
            const { p, tg, w } = place(s.t);
            const nx = -tg[1] * side, ny = tg[0] * side;
            const ry = w * 0.19 * s.scale;
            let cx = p[0] + nx * (w / 2 - ry * 0.15), cy = p[1] + ny * (w / 2 - ry * 0.15);
            if (s.kind === "hi") { cx -= nx * ry * 0.4; cy -= ny * ry * 0.4; }
            const ang = Math.atan2(tg[1], tg[0]) * 180 / Math.PI;
            s.el.setAttribute("cx", cx.toFixed(1));
            s.el.setAttribute("cy", cy.toFixed(1));
            s.el.setAttribute("transform", `rotate(${ang.toFixed(1)} ${cx.toFixed(1)} ${cy.toFixed(1)})`);
        }
        for (const s of this.spots) {
            const { p, tg, w } = place(s.t);
            const nx = tg[1] * side, ny = -tg[0] * side;
            const cx = p[0] + nx * w * 0.18, cy = p[1] + ny * w * 0.18;
            const ang = Math.atan2(tg[1], tg[0]) * 180 / Math.PI;
            s.el.setAttribute("cx", cx.toFixed(1));
            s.el.setAttribute("cy", cy.toFixed(1));
            s.el.setAttribute("transform", `rotate(${ang.toFixed(1)} ${cx.toFixed(1)} ${cy.toFixed(1)})`);
        }
        // манжеты
        if (this.bands.length) {
            const t = this.bands[0].t;
            const i = Math.round(t * (N - 1));
            const di = Math.max(4, Math.floor(N * 0.045));
            const strip = (j0, j1) => {
                const Lp = [], Rp = [];
                for (let k2 = Math.max(0, j0); k2 <= Math.min(N - 1, j1); k2++) {
                    const tt = k2 / (N - 1);
                    const w = widthAt(tt, w0, w1, taper) * 1.30 / 2;
                    const nx = -T[k2][1], ny = T[k2][0];
                    Lp.push([P[k2][0] + nx * w, P[k2][1] + ny * w]);
                    Rp.push([P[k2][0] - nx * w, P[k2][1] - ny * w]);
                }
                return polyPath([...Lp, ...Rp.reverse()]);
            };
            const third = Math.max(2, Math.floor(di / 3));
            for (const b of this.bands) {
                if (b.part === "base") b.el.setAttribute("d", strip(i - di, i + di));
                else if (b.part === "lite") b.el.setAttribute("d", strip(i - di, i - di + third));
                else b.el.setAttribute("d", strip(i + di - third, i + di));
            }
        }
    }
}

// ---------------------------------------------------------------- позы
// curl в единицах «естественного завитка» (умножается на curlDir щупальца)
const POSES = {
    rest: {},
    wave_right: {
        __brows: [{ op: 1, rot: -4, dy: -12 }, { op: 1, rot: 4, dy: -12 }],
        tentacle_up_r: { rot: -0.32, straighten: 0.7, curl: -0.4, swingAmp: 0.26, swingSpeed: 5.5 },
        tentacle_up_l: { rot: 0.18 },
        tentacle_front_c: { waveMul: 1.3 },
    },
    wave_left: {
        __brows: [{ op: 1, rot: -4, dy: -12 }, { op: 1, rot: 4, dy: -12 }],
        tentacle_up_l: { rot: 0.32, straighten: 0.7, curl: -0.4, swingAmp: 0.26, swingSpeed: 5.5 },
        tentacle_up_r: { rot: -0.18 },
    },
    point_right: {
        __brows: [{ op: 1, rot: 10, dy: 4 }, { op: 1, rot: -10, dy: 4 }],
        tentacle_up_r: { rot: -0.15, straighten: 0.9, curl: -0.9 },
        tentacle_up_l: { rot: -0.15, curl: 0.4 },
        tentacle_band_l: { curl: 0.4 },
        tentacle_front_l: { curl: 0.25 }, tentacle_front_c: { curl: 0.2 }, tentacle_front_r: { curl: 0.25 },
    },
    reach_up: {
        __brows: [{ op: 1, rot: 0, dy: -22 }, { op: 1, rot: 0, dy: -22 }],
        tentacle_up_l: { rot: 0.45, straighten: 0.65, curl: -0.35 },
        tentacle_up_r: { rot: -0.45, straighten: 0.65, curl: -0.35 },
        tentacle_band_l: { rot: 0.5, straighten: 0.3, curl: 0.3 },
        tentacle_far_r: { rot: -0.35, straighten: 0.25, curl: 0.3 },
        tentacle_front_l: { rot: 0.15, straighten: 0.35, curl: -0.3 },
        tentacle_front_c: { straighten: 0.3, curl: -0.2 },
        tentacle_front_r: { rot: -0.15, straighten: 0.35, curl: -0.3 },
    },
    sing: {
        __brows: [{ op: 1, rot: -6, dy: -14 }, { op: 1, rot: 6, dy: -14 }],
        tentacle_up_l:   { rot: 0.3, straighten: 0.5, curl: -0.3, swingAmp: 0.12, swingSpeed: 2.6, swingPhase: 0, waveMul: 1.4 },
        tentacle_up_r:   { rot: -0.3, straighten: 0.5, curl: -0.3, swingAmp: 0.12, swingSpeed: 2.6, swingPhase: Math.PI, waveMul: 1.4 },
        tentacle_band_l: { swingAmp: 0.10, swingSpeed: 2.6, swingPhase: 0.8, waveMul: 1.5 },
        tentacle_far_r:  { swingAmp: 0.10, swingSpeed: 2.6, swingPhase: 2.4, waveMul: 1.5 },
        tentacle_front_l:{ swingAmp: 0.16, swingSpeed: 2.6, swingPhase: 0, waveMul: 1.5 },
        tentacle_front_c:{ swingAmp: 0.13, swingSpeed: 2.6, swingPhase: 1.0, waveMul: 1.4 },
        tentacle_front_r:{ swingAmp: 0.16, swingSpeed: 2.6, swingPhase: 2.0, waveMul: 1.5 },
    },
    curl_shy: {
        __brows: [{ op: 1, rot: -10, dy: -6 }, { op: 1, rot: 10, dy: -6 }],
        tentacle_up_l: { curl: 2.0, rot: -0.4, waveMul: 0.3 },
        tentacle_up_r: { curl: 2.0, rot: 0.4, waveMul: 0.3 },
        tentacle_band_l: { curl: 1.8, rot: -0.5, waveMul: 0.3 },
        tentacle_far_r: { curl: 1.8, rot: 0.5, waveMul: 0.3 },
        tentacle_front_l: { curl: 1.4, waveMul: 0.3 },
        tentacle_front_c: { curl: 1.2, waveMul: 0.3 },
        tentacle_front_r: { curl: 1.4, waveMul: 0.3 },
    },
    droop_sad: {
        __brows: [{ op: 1, rot: -14, dy: -4 }, { op: 1, rot: 14, dy: -4 }],
        tentacle_up_l: { rot: -2.0, straighten: 0.45, curl: 0.5, waveMul: 0.4 },
        tentacle_up_r: { rot: 2.0, straighten: 0.45, curl: 0.5, waveMul: 0.4 },
        tentacle_band_l: { rot: 0.4, curl: 0.4, straighten: 0.2, waveMul: 0.4 },
        tentacle_far_r: { rot: 0.35, curl: 0.4, straighten: 0.2, waveMul: 0.4 },
        tentacle_front_l: { straighten: 0.3, curl: 0.3, waveMul: 0.4 },
        tentacle_front_c: { straighten: 0.2, waveMul: 0.4 },
        tentacle_front_r: { straighten: 0.3, curl: 0.3, waveMul: 0.4 },
    },
    excited: {
        __brows: [{ op: 1, rot: 0, dy: -26 }, { op: 1, rot: 0, dy: -26 }],
        tentacle_up_l: { rot: 0.5, straighten: 0.4, waveMul: 2.6 },
        tentacle_up_r: { rot: -0.5, straighten: 0.4, waveMul: 2.6 },
        tentacle_band_l: { straighten: 0.25, waveMul: 2.4 },
        tentacle_far_r: { straighten: 0.25, waveMul: 2.4 },
        tentacle_front_l: { waveMul: 2.2 }, tentacle_front_c: { waveMul: 2.0 }, tentacle_front_r: { waveMul: 2.2 },
    },
    // объятия: передние щупальца скрещиваются на животе, тело сжимается,
    // глаза прищуриваются — тёплое «обнимаю себя»
    hug_front: {
        __brows: [{ op: 1, rot: -5, dy: -8 }, { op: 1, rot: 5, dy: -8 }],
        __fx: { squash: 1, squint: 0.4 },
        tentacle_up_l: { rot: 1.2, straighten: 0.35, curl: 1.0 },
        tentacle_up_r: { rot: -1.2, straighten: 0.35, curl: 1.0 },
        tentacle_band_l: { rot: -1.15, straighten: 0.6, curl: 1.1, stretch: 1.05 },
        tentacle_far_r: { rot: 0.95, straighten: 0.35, curl: 0.9 },
        tentacle_front_l: { rot: -0.55, straighten: 0.45, curl: 1.35, stretch: 1.06 },
        tentacle_front_r: { rot: 0.6, straighten: 0.45, curl: 1.3, stretch: 1.06 },
        tentacle_front_c: { curl: 0.8, stretch: 0.9 },
    },
    // shout: руки «рупором» к бокам шлема (ограничитель прижмёт кончики к стеклу),
    // остальные щупальца расставлены и напряжены
    shout: {
        __brows: [{ op: 1, rot: 14, dy: 8 }, { op: 1, rot: -14, dy: 8 }],
        tentacle_up_l: { rot: 0.5, straighten: 0.4, curl: 1.2 },
        tentacle_up_r: { rot: -0.5, straighten: 0.4, curl: 1.2 },
        tentacle_band_l: { rot: 0.3, straighten: 0.4 },
        tentacle_far_r: { rot: -0.3, straighten: 0.4 },
        tentacle_front_l: { rot: 0.25, straighten: 0.4 },
        tentacle_front_c: { straighten: 0.35 },
        tentacle_front_r: { rot: -0.25, straighten: 0.4 },
    },
    dance: {
        __brows: [{ op: 1, rot: -6, dy: -20 }, { op: 1, rot: 6, dy: -20 }],
        tentacle_up_l:   { rot: 0.4, straighten: 0.6, curl: -0.4, swingAmp: 0.3, swingSpeed: 4.2, swingPhase: 0, waveMul: 2 },
        tentacle_up_r:   { rot: -0.4, straighten: 0.6, curl: -0.4, swingAmp: 0.3, swingSpeed: 4.2, swingPhase: Math.PI, waveMul: 2 },
        tentacle_band_l: { swingAmp: 0.16, swingSpeed: 4.2, swingPhase: 1.0, waveMul: 2 },
        tentacle_far_r:  { swingAmp: 0.16, swingSpeed: 4.2, swingPhase: 4.1, waveMul: 2 },
        tentacle_front_l:{ swingAmp: 0.22, swingSpeed: 4.2, swingPhase: 0.5, waveMul: 2 },
        tentacle_front_c:{ swingAmp: 0.18, swingSpeed: 4.2, swingPhase: 1.5, waveMul: 1.8 },
        tentacle_front_r:{ swingAmp: 0.22, swingSpeed: 4.2, swingPhase: 2.5, waveMul: 2 },
    },
    think: {
        __brows: [{ op: 1, rot: -8, dy: -22 }, { op: 1, rot: 4, dy: 2 }],
        tentacle_up_r: { rot: -0.3, straighten: 0.55, curl: 2.0, waveMul: 0.4 },
        tentacle_up_l: { rot: -0.2, curl: 0.3 },
        tentacle_front_c: { waveMul: 0.4 },
    },
    shrug: {
        __brows: [{ op: 1, rot: -6, dy: -18 }, { op: 1, rot: 6, dy: -18 }],
        tentacle_up_l: { rot: 0.4, straighten: 0.65, curl: -0.35 },
        tentacle_up_r: { rot: -0.4, straighten: 0.65, curl: -0.35 },
        tentacle_front_l: { curl: 0.3 }, tentacle_front_r: { curl: 0.3 },
    },
    clap: {
        __brows: [{ op: 1, rot: 0, dy: -14 }, { op: 1, rot: 0, dy: -14 }],
        tentacle_up_l: { rot: 0.35, straighten: 0.75, swingAmp: 0.24, swingSpeed: 7.5, swingPhase: 0 },
        tentacle_up_r: { rot: -0.35, straighten: 0.75, swingAmp: 0.24, swingSpeed: 7.5, swingPhase: Math.PI },
    },
};

// ---------------------------------------------------------------- эмоции
const EMOTIONS = {
    calm:       { },
    neutral:    { },
    happy:      { curve: 1.15, waveMul: 1.3 },
    excited:    { pose: "excited", pupil: 1.12, curve: 1.2,
                  brows: [{ op: 1, rot: -6, dy: -22 }, { op: 1, rot: 6, dy: -22 }] },
    sad:        { pose: "droop_sad", lid: 0.42, curve: 0.35, pupil: 0.95,
                  brows: [{ op: 1, rot: -14, dy: -4 }, { op: 1, rot: 14, dy: -4 }] },
    angry:      { lid: 0.5, curve: 0.4, pose: "point_right",
                  brows: [{ op: 1, rot: 16, dy: 10 }, { op: 1, rot: -16, dy: 10 }] },
    confused:   { lid: 0.18, pupil: 1.05, curve: 0.7,
                  brows: [{ op: 1, rot: -12, dy: -24 }, { op: 1, rot: 6, dy: 2 }] },
    curious:    { pupil: 1.18, curve: 1.0, waveMul: 1.3,
                  brows: [{ op: 1, rot: -8, dy: -18 }, { op: 1, rot: 8, dy: -18 }] },
    sarcastic:  { lid: 0.35, curve: 0.9,
                  brows: [{ op: 1, rot: -10, dy: -20 }, { op: 1, rot: 4, dy: 4 }] },
    proud:      { lid: 0.25, curve: 1.1 },
    tender:     { lid: 0.3, cheek: 1.15, curve: 1.05 },
    playful:    { pose: "wave_right", pupil: 1.1, curve: 1.2 },
    empathetic: { lid: 0.22, cheek: 1.1, curve: 1.0,
                  brows: [{ op: 1, rot: -8, dy: -8 }, { op: 1, rot: 8, dy: -8 }] },
    surprised:  { pupil: 0.8, openBias: 0.35, curve: 0.6,
                  brows: [{ op: 1, rot: 0, dy: -34 }, { op: 1, rot: 0, dy: -34 }] },
    nervous:    { pose: "curl_shy", pupil: 0.88, waveMul: 1.6, curve: 0.5,
                  brows: [{ op: 1, rot: -8, dy: -12 }, { op: 1, rot: 8, dy: -12 }] },
};

// ---------------------------------------------------------------- виземы
const VISEMES = {
    REST: { o: 0.05, w: 190, r: 0.25, c: 1.0 },
    A:    { o: 1.00, w: 196, r: 0.50, c: 0.9 },
    E:    { o: 0.52, w: 215, r: 0.20, c: 1.0 },
    I:    { o: 0.32, w: 168, r: 0.15, c: 1.1 },
    O:    { o: 0.80, w: 122, r: 1.00, c: 0.3 },
    U:    { o: 0.45, w:  96, r: 1.00, c: 0.2 },
};
const VISEME_BY_LEVEL = ["REST", "U", "I", "E", "A"]; // числовой proxy → буква

// ---------------------------------------------------------------- рот
class MouthRig {
    constructor(svg) {
        this.elMouth = svg.getElementById("mouth_open");
        this.elTongue = svg.getElementById("tongue");
        this.elTongueHi = svg.getElementById("tongue_hi");
        this.cx = 986; this.topY = 862;
        this.cur = { o: 0.5, w: 190, r: 0.35, c: 1 };
        this.tgt = { o: 0.05, w: 190, r: 0.25, c: 1 };
    }
    setViseme(v, jaw) {
        const s = VISEMES[v] || VISEMES.REST;
        const jawK = (jaw === undefined || jaw === null) ? 1 : (0.25 + 0.95 * jaw);
        this.tgt = { o: Math.min(1, s.o * jawK), w: s.w, r: s.r, c: s.c };
    }
    setOpen(o, curve) {
        this.tgt = { o: Math.max(0, Math.min(1, o)), w: 190 - 40 * o * 0.3, r: 0.3 + 0.3 * o, c: curve !== undefined ? curve : 1 };
    }
    update(dt, curveBias, openBias) {
        const k = 1 - Math.exp(-dt / 0.06);
        for (const key of ["o", "w", "r", "c"]) this.cur[key] += (this.tgt[key] - this.cur[key]) * k;
        const { cx, topY } = this;
        const o = Math.max(0, Math.min(1, this.cur.o + (openBias || 0)));
        const half = (this.cur.w / 2) * (1 - 0.22 * this.cur.r);
        const cl = 14 * this.cur.c * (curveBias === undefined ? 1 : curveBias);
        const cornerY = topY - cl + 8;
        const topCtrlY = cornerY + 30 + 8 * o;
        const bottomY = cornerY + 16 + o * 105 * (0.6 + 0.4 * this.cur.r);
        const midY = cornerY + (bottomY - cornerY) * 0.66;
        const d = `M${(cx - half).toFixed(1)} ${cornerY.toFixed(1)}` +
            `Q${cx} ${topCtrlY.toFixed(1)} ${(cx + half).toFixed(1)} ${cornerY.toFixed(1)}` +
            `C${(cx + half * 0.98).toFixed(1)} ${midY.toFixed(1)} ${(cx + half * 0.55).toFixed(1)} ${bottomY.toFixed(1)} ${cx} ${bottomY.toFixed(1)}` +
            `C${(cx - half * 0.55).toFixed(1)} ${bottomY.toFixed(1)} ${(cx - half * 0.98).toFixed(1)} ${midY.toFixed(1)} ${(cx - half).toFixed(1)} ${cornerY.toFixed(1)}Z`;
        this.elMouth.setAttribute("d", d);
        // язык
        const tOp = Math.max(0, Math.min(1, (o - 0.16) / 0.25));
        if (this.elTongue) {
            const hw = half * 0.6;
            const y0 = cornerY + (bottomY - cornerY) * 0.55;
            const yb = bottomY - 4;
            this.elTongue.setAttribute("opacity", tOp.toFixed(2));
            this.elTongue.setAttribute("d",
                `M${(cx - hw).toFixed(1)} ${y0.toFixed(1)}` +
                `Q${cx} ${(y0 - 10).toFixed(1)} ${(cx + hw).toFixed(1)} ${y0.toFixed(1)}` +
                `C${(cx + hw * 0.7).toFixed(1)} ${yb.toFixed(1)} ${(cx - hw * 0.7).toFixed(1)} ${yb.toFixed(1)} ${(cx - hw).toFixed(1)} ${y0.toFixed(1)}Z`);
            // блик едет вместе с языком
            if (this.elTongueHi) {
                const hy = y0 + (yb - y0) * 0.35;
                this.elTongueHi.setAttribute("cx", (cx - hw * 0.35).toFixed(1));
                this.elTongueHi.setAttribute("cy", hy.toFixed(1));
                this.elTongueHi.setAttribute("rx", (hw * 0.38).toFixed(1));
                this.elTongueHi.setAttribute("ry", Math.max(3, (yb - y0) * 0.16).toFixed(1));
                this.elTongueHi.setAttribute("opacity", (tOp * 0.8).toFixed(2));
            }
        }
    }
}

// ---------------------------------------------------------------- спецэффекты
const SVG_NS = "http://www.w3.org/2000/svg";

class FxSystem {
    constructor(svg) {
        this.layer = document.createElementNS(SVG_NS, "g");
        this.layer.setAttribute("id", "fx_layer");
        svg.appendChild(this.layer);
        this.parts = [];
    }
    _el(tag, attrs) {
        const e = document.createElementNS(SVG_NS, tag);
        for (const k in attrs) e.setAttribute(k, attrs[k]);
        return e;
    }
    _make(kind, o) {
        switch (kind) {
            case "heart": return this._el("path", { d: "M0 10 C0 -6 22 -6 22 10 C22 24 0 38 0 38 C0 38 -22 24 -22 10 C-22 -6 0 -6 0 10 Z", fill: "#F888A8" });
            case "sparkle": return this._el("path", { d: "M0 -16 L4 -4 L16 0 L4 4 L0 16 L-4 4 L-16 0 L-4 -4 Z", fill: "#FFE066" });
            case "drop": return this._el("path", { d: "M0 -14 C10 2 12 10 8 18 C4 25 -4 25 -8 18 C-12 10 -10 2 0 -14 Z", fill: o.color || "#8AD4FF" });
            case "bubble": return this._el("circle", { r: "14", fill: "#C8E8F8", "fill-opacity": "0.2", stroke: "#C8E8F8", "stroke-width": "4" });
            case "ring": return this._el("circle", { r: "10", fill: "none", stroke: "#FFD166", "stroke-width": "9" });
            case "confetti": return this._el("rect", { x: "-7", y: "-4", width: "14", height: "8", fill: o.color || "#FFD166" });
            case "note": {
                const g = this._el("g", {});
                g.appendChild(this._el("ellipse", { cx: "-4", cy: "16", rx: "11", ry: "8", fill: "#F2FCFD", transform: "rotate(-20 -4 16)" }));
                g.appendChild(this._el("path", { d: "M6 14 L6 -16 L24 -21 L24 -10 L10 -6", fill: "none", stroke: "#F2FCFD", "stroke-width": "6", "stroke-linejoin": "round" }));
                return g;
            }
            case "flash": return this._el("rect", { x: "0", y: "0", width: "2048", height: "2048", fill: "#FFFFFF", opacity: "0" });
        }
        return null;
    }
    spawn(kind, o = {}) {
        const el = this._make(kind, o);
        if (!el) return;
        this.layer.appendChild(el);
        this.parts.push({
            el, kind, age: 0, life: o.life || 1.4,
            x: o.x || 1024, y: o.y || 600, vx: o.vx || 0, vy: o.vy || 0,
            spin: o.spin || 0, scale: o.scale || 1, wobble: Math.random() * Math.PI * 2,
        });
    }
    update(dt) {
        let alive = false;
        for (const p of this.parts) {
            p.age += dt;
            const t = p.age / p.life;
            if (t >= 1) { p.el.remove(); p.dead = true; continue; }
            alive = true;
            if (p.kind === "flash") {
                const a = t < 0.25 ? t / 0.25 : 1 - (t - 0.25) / 0.75;
                p.el.setAttribute("opacity", (a * 0.85).toFixed(2));
                continue;
            }
            p.x += p.vx * dt; p.y += p.vy * dt;
            let s = p.scale;
            if (p.kind === "ring") p.el.setAttribute("r", String(10 + t * 150 * p.scale));
            if (p.kind === "heart" || p.kind === "note") p.x += Math.sin(p.age * 5 + p.wobble) * 34 * dt;
            if (p.kind === "bubble") p.x += Math.sin(p.age * 4 + p.wobble) * 26 * dt;
            if (p.kind === "sparkle") s = p.scale * (0.7 + 0.3 * Math.sin(p.age * 12 + p.wobble));
            if (p.kind === "confetti") p.vy += 700 * dt;
            p.el.setAttribute("transform",
                `translate(${p.x.toFixed(1)} ${p.y.toFixed(1)}) scale(${s.toFixed(2)}) rotate(${(p.spin * p.age * 180).toFixed(1)})`);
            p.el.setAttribute("opacity", (1 - t).toFixed(2));
        }
        if (this.parts.length) this.parts = this.parts.filter(p => !p.dead);
        return alive;
    }
}

// ---------------------------------------------------------------- аватар
class OctobussAvatar {
    constructor(containerOrId, svgUrl = "octobuss.rigged.svg", opts = {}) {
        this.container = (typeof containerOrId === "string") ? document.getElementById(containerOrId) : containerOrId;
        this.opts = Object.assign({ mouthFloor: 0.05 }, opts);
        this.ready = false;
        this.state = {
            emotion: "calm",
            speaking: false,
            pendingEnd: false,
            actionUntil: 0,
            jaw: 0, targetJaw: 0,
            viseme: "REST",
            // планировщики (совместимы с timeline-sync)
            jawSeq: [], jawIdx: 0, jawStep: 20, jawNext: 0, jawActive: false, jawSched: 0,
            visSeq: [], visIdx: 0, visStep: 50, visNext: 0, visActive: false, visSched: 0,
            respStartPlayhead: null,
            blinkT: -1,
            gaze: null,
        };
        this._init(svgUrl);
    }

    async _init(svgUrl) {
        const res = await fetch(svgUrl);
        const text = await res.text();
        this.container.innerHTML = text;
        const svg = this.container.querySelector("svg");
        svg.removeAttribute("width");
        svg.removeAttribute("height");
        svg.style.width = "100%";
        svg.style.height = "100%";
        this.svg = svg;

        this.tentacles = {};
        for (const g of svg.querySelectorAll("g.tentacle")) this.tentacles[g.id] = new Tentacle(g);
        this.mouth = new MouthRig(svg);
        this.headGroup = svg.getElementById("head_group");
        this.pupils = [
            { el: svg.getElementById("pupil_l"), cx: 821, cy: 749 },
            { el: svg.getElementById("pupil_r"), cx: 1179, cy: 767 },
        ];
        this.lids = [svg.getElementById("lid_l"), svg.getElementById("lid_r")];
        this.cheeks = [svg.getElementById("cheek_l"), svg.getElementById("cheek_r")];
        this.brows = [svg.getElementById("brow_l"), svg.getElementById("brow_r")];
        for (const b of this.brows) {
            if (b) b.style.transition = "transform 0.25s ease, opacity 0.25s ease";
        }
        this.root = svg.getElementById("octobuss");
        this.bodyEl = svg.getElementById("body");
        this.fx = new FxSystem(svg);
        this._poseFxTgt = { squash: 0, squint: 0 };
        this._poseFxCur = { squash: 0, squint: 0 };
        this.motion = { spinStart: -1, spinDur: 1400, bounceUntil: 0, bounceAmp: 0,
                        bounceFreq: 5, swayUntil: 0, swayAmp: 0, boopT: -1 };

        this._last = performance.now();
        this._clock = 0;
        const loop = (ts) => { this._tick(ts); requestAnimationFrame(loop); };
        requestAnimationFrame(loop);
        this.ready = true;
        console.log("🐙 OctobussAvatar ready:", Object.keys(this.tentacles));
    }

    // ---------------- AI pose API ----------------
    /** setPose('wave_right', {durationMs}) или setPose({tentacle_up_r:{...}}) */
    setPose(pose, opts = {}) {
        const ms = opts.durationMs || 600;
        let map;
        if (typeof pose === "string") {
            map = POSES[pose];
            if (!map) { console.warn("🐙 unknown pose:", pose); return false; }
        } else {
            map = pose;
        }
        for (const [id, t] of Object.entries(this.tentacles)) {
            const params = map[id] ? { ...map[id], __absolute: true } : { __absolute: true };
            t.setTarget(params, ms);
        }
        this._poseFxTgt = map.__fx || { squash: 0, squint: 0 };
        if (map.__brows) this._setBrows(map.__brows);
        if (opts.holdMs) this.state.actionUntil = performance.now() + opts.holdMs;
        return true;
    }

    setTentacle(id, params, durationMs = 600) {
        const t = this.tentacles[id] || this.tentacles["tentacle_" + id];
        if (!t) { console.warn("🐙 unknown tentacle:", id); return false; }
        t.setTarget(params, durationMs);
        return true;
    }

    listPoses() { return Object.keys(POSES); }

    // ---------------- proxy-совместимый интерфейс ----------------
    setEmotion(emotion) {
        if (!EMOTIONS[emotion]) emotion = "calm";
        this.state.emotion = emotion;
        const e = EMOTIONS[emotion];
        // поза-осанка от эмоции (если нет активного действия)
        if (performance.now() > this.state.actionUntil) {
            this.setPose(e.pose || "rest", { durationMs: 900 });
        }
        // брови эмоции (если нет активного действия со своими бровями)
        if (performance.now() > this.state.actionUntil) this._setBrows(e.brows);
        console.log(`🐙 emotion: ${emotion}`);
    }

    /** брови видимы всегда; state = [{op,rot,dy}, {op,rot,dy}] или undefined (нейтральные) */
    _setBrows(state) {
        const def = [{ op: 0.9, rot: 0, dy: 0 }, { op: 0.9, rot: 0, dy: 0 }];
        const br = state || def;
        if (!this.brows) return;
        this.brows.forEach((el, i) => {
            if (!el) return;
            const b = br[i] || br[0];
            el.style.opacity = String(b.op !== undefined ? b.op : 0.9);
            el.style.transform = `translateY(${b.dy || 0}px) rotate(${b.rot || 0}deg)`;
        });
    }

    blink() { this.state.blinkT = 0; }

    activateAction(name, durationMs = 1400) {
        const map = {
            wave: "wave_right", point: "point_right", hug: "hug_front",
            shrug: "shrug", clap: "clap", heart: "excited",
            sing: "sing", dance: "dance", laugh: "excited", shout: "shout",
            whisper: "curl_shy", photobooth: "rest",
            sfx_wave: "wave_right", sfx_spin: "excited", sfx_heart: "excited",
        };
        const pose = map[name] || (POSES[name] ? name : null);
        if (pose) {
            this.setPose(pose, { durationMs: 450 });
            this.state.actionUntil = performance.now() + durationMs;
        }
        // моушены всего персонажа (портированы из legacy-аниматора)
        const now = performance.now();
        if (name === "sfx_spin") {
            this.motion.spinStart = now;
            this.motion.spinDur = Math.max(900, durationMs);
        } else if (name === "laugh") {
            this.motion.bounceUntil = now + durationMs;
            this.motion.bounceAmp = 26; this.motion.bounceFreq = 5.5;
        } else if (name === "dance") {
            this.motion.bounceUntil = now + durationMs;
            this.motion.bounceAmp = 30; this.motion.bounceFreq = 2.2;
            this.motion.swayUntil = now + durationMs;
            this.motion.swayAmp = 3.5;
        } else if (name === "sing") {
            this.motion.swayUntil = now + durationMs;
            this.motion.swayAmp = 2.0;
        }
        this.triggerFxFromAction(name);
        // брови для эффектов без позы
        const fxBrows = {
            sfx_tear:  [{ op: 1, rot: -14, dy: -4 }, { op: 1, rot: 14, dy: -4 }],
            sfx_sweat: [{ op: 1, rot: -10, dy: -8 }, { op: 1, rot: 10, dy: -8 }],
            sfx_pop:   [{ op: 1, rot: 0, dy: -28 }, { op: 1, rot: 0, dy: -28 }],
            sfx_boop:  [{ op: 1, rot: 0, dy: -28 }, { op: 1, rot: 0, dy: -28 }],
            sfx_heart: [{ op: 1, rot: -6, dy: -14 }, { op: 1, rot: 6, dy: -14 }],
            heart:     [{ op: 1, rot: -6, dy: -14 }, { op: 1, rot: 6, dy: -14 }],
            laugh:     [{ op: 1, rot: 0, dy: -20 }, { op: 1, rot: 0, dy: -20 }],
            whisper:   [{ op: 1, rot: -8, dy: -6 }, { op: 1, rot: 8, dy: -6 }],
            photobooth:[{ op: 1, rot: 0, dy: -18 }, { op: 1, rot: 0, dy: -18 }],
        };
        if (fxBrows[name]) this._setBrows(fxBrows[name]);
        this._actionMouth = { sing: 0.18, laugh: 0.22, shout: 0.3, whisper: -0.04 }[name] || 0;
        setTimeout(() => {
            if (performance.now() >= this.state.actionUntil - 20) {
                this._actionMouth = 0;
                this.state.actionUntil = 0;
                this.setEmotion(this.state.emotion); // осанка + брови эмоции
            }
        }, durationMs + 30);
    }

    triggerGesture(name, _opts) { this.activateAction(name, 1400); }

    /** частицы (порт FX из octopus_animator.js в SVG) */
    triggerFxFromAction(action) {
        if (!this.fx || !action) return;
        const F = this.fx;
        switch (action) {
            case "sfx_tear":
                F.spawn("drop", { x: 758, y: 860, vy: 280, color: "#6EC6FF", life: 1.6, scale: 1.2 });
                break;
            case "sfx_sweat":
                F.spawn("drop", { x: 1335, y: 555, vx: 45, vy: 210, color: "#8AD4FF", life: 1.3 });
                break;
            case "heart":
            case "sfx_heart":
                for (let i = 0; i < 6; i++) {
                    F.spawn("heart", { x: 800 + i * 90, y: 430 - (i % 2) * 80,
                        vy: -150 - Math.random() * 70, life: 1.5 + Math.random() * 0.6,
                        scale: 0.8 + Math.random() * 0.8, spin: (Math.random() - 0.5) * 1.5 });
                }
                break;
            case "sfx_sparkle":
            case "photobooth_burst":
                for (let i = 0; i < 8; i++) {
                    const a = i / 8 * Math.PI * 2;
                    F.spawn("sparkle", { x: 1033, y: 500, vx: Math.cos(a) * 340, vy: Math.sin(a) * 340,
                        life: 1.1, scale: 0.9 + Math.random() * 0.8 });
                }
                break;
            case "sfx_pop":
                F.spawn("ring", { x: 1033, y: 520, life: 0.7, scale: 1.6 });
                for (let i = 0; i < 12; i++) {
                    const a = Math.random() * Math.PI * 2, v = 220 + Math.random() * 280;
                    F.spawn("confetti", { x: 1033, y: 520, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 150,
                        life: 1.1, spin: (Math.random() - 0.5) * 8,
                        color: ["#FFD166", "#F888A8", "#8AD4FF", "#D8B8F8"][i % 4] });
                }
                break;
            case "sfx_boop":
                F.spawn("ring", { x: 1033, y: 250, life: 0.6 });
                this.motion.boopT = 0;
                break;
            case "sfx_bubble":
            case "sfx_wave":
                for (let i = 0; i < 6; i++) {
                    F.spawn("bubble", { x: 680 + Math.random() * 700, y: 1180,
                        vy: -190 - Math.random() * 130, life: 1.5 + Math.random() * 0.6,
                        scale: 0.5 + Math.random() });
                }
                break;
            case "sing":
            case "dance":
                for (let i = 0; i < 5; i++) {
                    F.spawn("note", { x: (i % 2 ? 380 : 1560) + Math.random() * 140,
                        y: 600 + Math.random() * 260, vy: -120 - Math.random() * 70,
                        life: 1.9, scale: 0.9 + Math.random() * 0.5, spin: (Math.random() - 0.5) * 0.8 });
                }
                break;
            case "photobooth":
                setTimeout(() => {
                    if (!this.fx) return;
                    this.fx.spawn("flash", { life: 0.6 });
                    this.triggerFxFromAction("photobooth_burst");
                }, 800);
                break;
        }
    }

    setGaze(x, y) { this.state.gaze = { x, y }; } // нормализованные -1..1

    // ---------------- протокол команд ----------------
    handleCommand(cmd) {
        if (!cmd || !this.ready) return;
        const st = this.state;
        const now = performance.now();

        if (cmd.cmd === "action" && cmd.action) {
            this.activateAction(cmd.action, Number(cmd.duration_ms) || 1400);
            return;
        }
        if (cmd.cmd === "pose" && cmd.pose) { // прямая AI-команда позы
            this.setPose(cmd.pose, { durationMs: cmd.duration_ms || 600, holdMs: cmd.hold_ms });
            return;
        }
        if (cmd.cmd === "gaze") { this.setGaze(cmd.x, cmd.y); return; }

        if (cmd.cmd === "audio_sync") {
            st.speaking = cmd.speaking !== false;
            if (cmd.emotion && cmd.emotion.value) this.setEmotion(cmd.emotion.value);
            if (cmd.action && cmd.action !== "none") {
                this.activateAction(cmd.action, Math.max(300, Math.round((cmd.duration_s || 0.4) * 1000)));
            }
            if (typeof cmd.start_s === "number" && cmd.start_s <= 0.001) {
                st.jawSeq = []; st.jawIdx = 0; st.jawActive = false; st.jawSched = 0;
                st.visSeq = []; st.visIdx = 0; st.visActive = false; st.visSched = 0;
                st.respStartPlayhead = null;
            }
            let startTs = now;
            if (typeof cmd.start_s === "number" && typeof window.getAudioPlayheadS === "function") {
                const playhead = window.getAudioPlayheadS();
                if (cmd.start_s <= 0.001 || st.respStartPlayhead === null) st.respStartPlayhead = playhead;
                const rel = Math.max(0, playhead - st.respStartPlayhead);
                startTs = now + (cmd.start_s - rel) * 1000;
            }
            startTs = Math.max(startTs, Math.max(st.jawSched || 0, st.visSched || 0));

            const schedule = (track, seqKey, stepKey, idxKey, nextKey, activeKey, schedKey, defStep, minStep) => {
                if (!track || !Array.isArray(track.values) || !track.values.length) return;
                const step = Math.max(minStep, Number(track.step_ms || defStep));
                let seq = track.values.slice();
                let dur = seq.length * step;
                let ts = startTs;
                if (ts < now && seq.length) {
                    const lag = now - ts;
                    if (lag > dur) ts = now;
                    else {
                        const skip = Math.min(seq.length - 1, Math.floor(lag / step));
                        seq = seq.slice(skip); ts += skip * step; dur = seq.length * step;
                    }
                }
                if (st[seqKey].length && step === st[stepKey]) st[seqKey] = st[seqKey].concat(seq);
                else { st[seqKey] = seq; st[stepKey] = step; st[idxKey] = 0; }
                if (!st[activeKey]) st[nextKey] = ts;
                st[activeKey] = true;
                st[schedKey] = ts + dur;
            };
            schedule(cmd.jaw || (Array.isArray(cmd.amplitudes) ? { values: cmd.amplitudes, step_ms: 20 } : null),
                "jawSeq", "jawStep", "jawIdx", "jawNext", "jawActive", "jawSched", 20, 10);
            schedule(cmd.viseme_proxy,
                "visSeq", "visStep", "visIdx", "visNext", "visActive", "visSched", 50, 20);
            return;
        }

        if (cmd.cmd === "sync" && Array.isArray(cmd.visemes)) {
            const durMs = (cmd.duration || 1) * 1000;
            const step = Math.max(80, Math.min(180, durMs / cmd.visemes.length));
            st.visSeq = cmd.visemes.slice(); st.visIdx = 0; st.visStep = step;
            st.visNext = now; st.visActive = true; st.visSched = now + step * cmd.visemes.length;
            st.speaking = true;
            if (cmd.emotion) this.setEmotion(cmd.emotion);
            return;
        }

        if (cmd.cmd === "mouth") {
            st.targetJaw = Math.max(0, Math.min(1, Number(cmd.value) || 0));
            st.speaking = cmd.speaking !== false;
            if (st.speaking) this.mouth.setViseme(st.targetJaw > 0.6 ? "A" : st.targetJaw > 0.25 ? "E" : "I", st.targetJaw);
            else this.mouth.setViseme("REST");
            return;
        }

        if (cmd.cmd === "end") {
            st.pendingEnd = true;
            if (cmd.emotion) this.setEmotion(cmd.emotion);
            return;
        }

        if (cmd.cmd === "emotion" && cmd.value) { this.setEmotion(cmd.value); return; }
        if (cmd.emotion && typeof cmd.emotion === "string") this.setEmotion(cmd.emotion);
    }

    // ---------------- главный цикл ----------------
    _tick(ts) {
        const dt = Math.min(0.1, (ts - this._last) / 1000);
        this._last = ts;
        this._clock += dt;
        const st = this.state;

        // --- продвижение jaw-трека
        if (st.jawActive && st.jawSeq.length) {
            while (ts >= st.jawNext && st.jawIdx < st.jawSeq.length) {
                st.targetJaw = Number(st.jawSeq[st.jawIdx]) || 0;
                st.jawIdx++; st.jawNext += st.jawStep;
            }
            if (st.jawIdx >= st.jawSeq.length) { st.jawActive = false; st.jawSeq = []; }
        }
        // --- продвижение visеme-трека
        if (st.visActive && st.visSeq.length) {
            while (ts >= st.visNext && st.visIdx < st.visSeq.length) {
                let v = st.visSeq[st.visIdx];
                if (typeof v === "number") v = VISEME_BY_LEVEL[Math.max(0, Math.min(4, Math.round(v * 4)))];
                st.viseme = v;
                st.visIdx++; st.visNext += st.visStep;
            }
            if (st.visIdx >= st.visSeq.length) { st.visActive = false; st.visSeq = []; }
        }
        if (st.pendingEnd && !st.jawActive && !st.visActive) {
            st.pendingEnd = false; st.speaking = false;
            st.targetJaw = 0; st.viseme = "REST";
        }

        // --- рот
        st.jaw += (st.targetJaw - st.jaw) * (1 - Math.exp(-dt / 0.045));
        const emo = EMOTIONS[st.emotion] || {};
        if (st.speaking && (st.jawActive || st.visActive || st.jaw > 0.02)) {
            this.mouth.setViseme(st.viseme, st.jawActive || st.jaw > 0.02 ? st.jaw : undefined);
        } else if (!st.speaking) {
            this.mouth.setViseme("REST");
        }
        this.mouth.update(dt, emo.curve, (emo.openBias || 0) + (this._actionMouth || 0));

        // --- щупальца
        for (const t of Object.values(this.tentacles)) t.update(dt, this._clock);

        // --- частицы
        if (this.fx) this.fx.update(dt);

        // --- сжатие тела / прищур позы (объятия и т.п.)
        const kFx = 1 - Math.exp(-dt / 0.18);
        this._poseFxCur.squash += (this._poseFxTgt.squash - this._poseFxCur.squash) * kFx;
        this._poseFxCur.squint += (this._poseFxTgt.squint - this._poseFxCur.squint) * kFx;
        if (this.bodyEl) {
            const s = this._poseFxCur.squash;
            this.bodyEl.style.transformOrigin = "1005px 1320px";
            this.bodyEl.style.transform = s > 0.01
                ? `scale(${(1 + 0.045 * s).toFixed(3)}, ${(1 - 0.05 * s).toFixed(3)})` : "";
        }

        // --- моушены всего персонажа: спин, баунс, покачивание
        if (this.root) {
            let rootT = "";
            if (this.motion.spinStart >= 0) {
                const t = (ts - this.motion.spinStart) / this.motion.spinDur;
                if (t >= 1) this.motion.spinStart = -1;
                else {
                    const e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
                    rootT += `rotate(${(e * 360).toFixed(1)}deg) `;
                }
            }
            let by = 0, brot = 0;
            if (ts < this.motion.bounceUntil) {
                by = -Math.abs(Math.sin(this._clock * Math.PI * this.motion.bounceFreq)) * this.motion.bounceAmp;
            }
            if (ts < this.motion.swayUntil) {
                brot = Math.sin(this._clock * Math.PI * this.motion.bounceFreq * 0.5) * this.motion.swayAmp;
            }
            if (by || brot) rootT += `translateY(${by.toFixed(1)}px) rotate(${brot.toFixed(2)}deg)`;
            this.root.style.transformOrigin = "1024px 1200px";
            this.root.style.transform = rootT;
        }

        // --- голова: дыхание/кивок (чуть живее при речи) + буп-сквош
        if (this.headGroup) {
            const bob = Math.sin(this._clock * 1.4) * (st.speaking ? 9 : 6);
            const tilt = Math.sin(this._clock * 0.9) * (st.speaking ? 1.0 : 0.6);
            let squash = 1;
            if (this.motion.boopT >= 0) {
                this.motion.boopT += dt;
                const p = this.motion.boopT / 0.35;
                if (p >= 1) this.motion.boopT = -1;
                else squash = 1 - 0.09 * Math.sin(p * Math.PI);
            }
            this.headGroup.style.transform =
                `translateY(${bob.toFixed(1)}px) rotate(${tilt.toFixed(2)}deg) scale(1, ${squash.toFixed(3)})`;
        }

        // --- глаза: моргание + веки эмоции
        let lidCover = Math.max(emo.lid || 0, this._poseFxCur.squint);
        if (st.blinkT >= 0) {
            st.blinkT += dt;
            const ph = st.blinkT / 0.16;
            if (ph >= 1) st.blinkT = -1;
            else lidCover = Math.max(lidCover, ph < 0.5 ? ph * 2 : (1 - ph) * 2);
        } else if (Math.random() < dt / 4.2) {
            st.blinkT = 0; // случайное моргание ~раз в 4 сек
        }
        for (const lid of this.lids) {
            if (!lid) continue;
            const ry = Number(lid.getAttribute("ry"));
            lid.setAttribute("opacity", lidCover > 0.03 ? "1" : "0");
            lid.style.transform = `translateY(${(-(1 - lidCover) * 2 * ry).toFixed(1)}px)`;
        }
        // --- зрачки: взгляд
        const pupilScale = emo.pupil || 1;
        for (const p of this.pupils) {
            if (!p.el) continue;
            let dx = 0, dy = 0;
            if (st.gaze) { dx = st.gaze.x * 30; dy = st.gaze.y * 24; }
            p.el.style.transform = `translate(${dx.toFixed(1)}px, ${dy.toFixed(1)}px) scale(${pupilScale})`;
            p.el.style.transformOrigin = `${p.cx}px ${p.cy}px`;
        }
        // --- щёки
        const cheekOp = emo.cheek !== undefined ? Math.min(1, emo.cheek) : 1;
        for (const c of this.cheeks) if (c) c.setAttribute("opacity", cheekOp.toFixed(2));
    }
}

window.OctobussAvatar = OctobussAvatar;
window.OCTOBUSS_POSES = Object.keys(POSES);

})();
