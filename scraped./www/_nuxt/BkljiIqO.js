import {
    C as h,
    c as Tt,
    F as no,
    d as so,
    W as ro,
    G as io,
    B as It,
    a as q,
    S as St,
    A as At,
    P as Gt,
    e as _t,
    M as Rt,
    f as Bt,
    O as lo,
    R as ho,
    V as co,
    D as Mo,
    u as mo,
    b as Ft,
    g as po,
} from "./CmyfV-Zi.js";
import {
    d as fo,
    i as uo,
    J as wo,
    r as go,
    k as yo,
    o as vo,
    y as xo,
    f as Po,
    a as bo,
    b as nt,
    t as Wt,
    u as Xt,
    E as ko,
} from "./Dy2RtAP3.js";
const zo = { class: "w-sceen h-full bg-black overflow-hidden" },
    Co = {
        class: "absolute bottom-0 flex flex-col items-center w-full text-center mx-auto mb-10 select-none opacity-50",
    },
    To = { class: "font-mono uppercase font-black text-3xl md:text-4xl text-white mix-blend-difference" },
    Io = {
        class: "font-semibold text-sm md:text-lg/6 tracking-wider md:tracking-wide max-w-70 md:max-w-90 text-white mix-blend-difference",
    },
    J = 25,
    B = 120,
    $ = 6,
    R = 18,
    ct = 40,
    dt = 30,
    F = -20,
    So = 45,
    Ao = 16,
    Go = fo({
        __name: "Whale",
        setup(_o) {
            const { t: Mt, locale: Yt } = uo(),
                Et = wo(),
                D = go(),
                mt = [
                    { link: "space", color: new h(1, 0, 0.3) },
                    { link: "grow", color: new h(0, 0.5, 0) },
                    { link: "deliver", color: new h(1, 0.8, 0) },
                ],
                Y = new Set(),
                Ht = yo("loaded"),
                W = [],
                E = [],
                T = [],
                H = [];
            function Q(f) {
                return f < 0.1
                    ? 1.5 * Math.pow(f / 0.1, 0.5)
                    : f < 0.2
                      ? 1.5 + ((f - 0.1) / 0.1) * 1
                      : f < 0.5
                        ? 2.5 + Math.sin(((f - 0.2) / 0.3) * Math.PI) * 0.5
                        : f < 0.75
                          ? 3 * (1 - ((f - 0.5) / 0.25) * 0.6)
                          : 1.2 * (1 - ((f - 0.75) / 0.25) * 0.65);
            }
            function pt(f) {
                const C = Q(0.33),
                    X = -C * 0.35,
                    _ = f * C * 0.7,
                    p = (0.33 - 0.5) * J;
                for (let l = 0; l < 4e3; l++) {
                    const a = Math.random(),
                        P = 8,
                        y = 3.2 * (1 - a * 0.55) * Math.pow(a + 0.15, 0.35),
                        A = 0.9 * (1 - a * 0.45),
                        b = p + a * a * 2.2 + (Math.random() - 0.5) * y * 0.4,
                        I = X - a * 1.5 + (Math.random() - 0.5) * A,
                        S = _ + f * a * P;
                    W.push({ x: b, y: I, z: S, t: 0.33 + a * 0.1, type: "fin", finT: a, side: f }),
                        E.push({ x: b, y: I, z: S });
                }
                for (let l = 0; l < 1500; l++) {
                    const a = 0.28 + Math.random() * 0.1,
                        P = (a - 0.5) * J,
                        y = Q(a),
                        b = (f > 0 ? -Math.PI * 0.25 : -Math.PI * 0.75) + (Math.random() - 0.5) * Math.PI * 0.4,
                        I = Math.sin(b) * y * 0.7,
                        S = Math.cos(b) * y * 0.85,
                        G = Math.random() * Math.random() * 3,
                        j = P + G * G * 0.1 + (Math.random() - 0.5) * 0.8,
                        U = I - G * 0.2 + (Math.random() - 0.5) * 0.5,
                        L = S + f * G;
                    W.push({ x: j, y: U, z: L, t: a, type: "fin", finT: G / 8, side: f }), E.push({ x: j, y: U, z: L });
                }
            }
            function K(f, z, C) {
                return (
                    Math.sin(f * 0.15) * Math.cos(z * 0.12) * Math.sin(C * 0.18) * 3 +
                    Math.sin(f * 0.08 + 1.2) * Math.cos(z * 0.1 + 0.8) * 2 +
                    Math.sin(f * 0.25 + 2.1) * Math.sin(z * 0.22) * Math.cos(C * 0.2) * 1.5
                );
            }
            function Lt() {
                for (let p = 0; p < 18e3; p++) {
                    const l = Math.random(),
                        a = Math.random() * Math.PI * 2,
                        P = (l - 0.5) * J,
                        y = Q(l) * (1 + (Math.random() - 0.5) * 0.1),
                        A = Math.sin(a) < -0.2 ? 0.7 : 1,
                        b = Math.sin(a) * y * A,
                        I = Math.cos(a) * y * 0.85;
                    W.push({ x: P, y: b, z: I, t: l, type: "body", theta: a }), E.push({ x: P, y: b, z: I });
                }
                pt(-1), pt(1);
                const f = 0.55,
                    z = (f - 0.5) * J,
                    C = Q(f) * 0.95;
                for (let p = 0; p < 600; p++) {
                    const l = Math.random(),
                        a = z + (Math.random() - 0.3) * 1.2,
                        P = C + 0.9 * l * (1 - l * 0.4),
                        y = (Math.random() - 0.5) * 0.2 * (1 - l * 0.5);
                    W.push({ x: a, y: P, z: y, t: f, type: "dorsal" }), E.push({ x: a, y: P, z: y });
                }
                const X = (1 - 0.5) * J;
                for (let p = 0; p < 4e3; p++) {
                    const l = 0.72 + Math.random() * 0.28,
                        a = Math.random() * Math.PI * 2,
                        P = (l - 0.5) * J,
                        y = (l - 0.72) / 0.28,
                        A = 1.4 * (1 - y * 0.6),
                        b = Math.sin(a) * A * (1 + y * 0.8),
                        I = Math.cos(a) * A * (1 - y * 0.7);
                    W.push({ x: P, y: b, z: I, t: l, type: "tailstock", theta: a, tailProgress: y }),
                        E.push({ x: P, y: b, z: I });
                }
                const _ = X;
                for (let p = 0; p < 6e3; p++) {
                    const l = Math.random() > 0.5 ? 1 : -1,
                        a = Math.random(),
                        P = Math.sin(a * Math.PI * 0.55) * 6,
                        y = a * a * 2.5,
                        A = 2.8 * Math.sin((a + 0.1) * Math.PI * 0.8) * (1 - a * 0.2),
                        b = (Math.random() - 0.35) * A,
                        I = 0.5 * (1 - a * 0.4) * (1 - Math.abs(b) / A) * (0.3 + Math.random() * 0.7),
                        S = a * a * 0.3;
                    W.push({
                        x: _ + b + y,
                        y: (Math.random() - 0.5) * I + S,
                        z: l * P,
                        t: 1,
                        type: "fluke",
                        flukeSpanT: a,
                        side: l,
                    }),
                        E.push({ x: _ + b + y, y: (Math.random() - 0.5) * I + S, z: l * P });
                }
                for (let p = 0; p < 3500; p++) {
                    const l = Math.random() > 0.5 ? 1 : -1,
                        a = 0.05 + Math.random() * 0.9,
                        P = Math.sin(a * Math.PI * 0.55) * 6,
                        y = a * a * 2.5,
                        A = 2.8 * Math.sin((a + 0.1) * Math.PI * 0.8) * (1 - a * 0.2),
                        b = Math.random() > 0.4,
                        I = b ? A * (0.4 + Math.random() * 0.2) : -A * (0.3 + Math.random() * 0.2),
                        S = a * a * 0.3;
                    W.push({
                        x: _ + I + y * (b ? 1 : 0.3),
                        y: (Math.random() - 0.5) * 0.15 + S,
                        z: l * P,
                        t: 1,
                        type: "fluke",
                        flukeSpanT: a,
                        side: l,
                    }),
                        E.push({ x: _ + I + y * (b ? 1 : 0.3), y: (Math.random() - 0.5) * 0.15 + S, z: l * P });
                }
                for (let p = 0; p < 3e3; p++) {
                    const l = Math.random() * Math.PI * 2,
                        a = Math.random(),
                        P = Math.random() > 0.5 ? 1 : -1,
                        y = Math.sin(l) * 1 * (1 - a * 0.6) * (1 - a) + (Math.random() - 0.5) * 0.4 * a,
                        A = Math.cos(l) * 0.17 * (1 - a * 0.7) + P * a * a * 2 * a,
                        b = _ - 1.5 + a * 1.8 + (Math.random() - 0.5) * 0.3;
                    W.push({ x: b, y, z: A, t: 0.95 + a * 0.05, type: "fluke", flukeSpanT: a * 0.25, side: P }),
                        E.push({ x: b, y, z: A });
                }
                for (let p = 0; p < 500; p++) {
                    const l = Math.random();
                    W.push({
                        x: _ + 0.8 + l * 2,
                        y: (Math.random() - 0.5) * 0.15 * (1 - l * 0.6),
                        z: (Math.random() - 0.5) * 1 * (1 - l),
                        t: 0.99,
                        type: "fluke",
                        flukeSpanT: 0.05,
                    }),
                        E.push({
                            x: _ + 0.8 + l * 2,
                            y: (Math.random() - 0.5) * 0.15 * (1 - l * 0.6),
                            z: (Math.random() - 0.5) * 1 * (1 - l),
                        });
                }
            }
            return (
                vo(() => {
                    if (!D.value) return;
                    const f = new Tt();
                    (f.background = new h(657930)), (f.fog = new no(135192, 40, 180));
                    const z = new so(70, window.innerWidth / window.innerHeight, 0.1, 500);
                    z.position.set(28, 5, 0), z.lookAt(-10, -5, 0);
                    const C = new ro({ antialias: !0 });
                    C.setSize(window.innerWidth, window.innerHeight),
                        C.setPixelRatio(Math.min(window.devicePixelRatio, 2)),
                        D.value.appendChild(C.domElement);
                    const X = new io();
                    f.add(X), Lt();
                    const _ = W.length,
                        p = new It(),
                        l = new Float32Array(_ * 3),
                        a = new Float32Array(_ * 3),
                        P = new Float32Array(_);
                    Y.add(p);
                    const y = new h(0.55, 0.85, 0.95),
                        A = new h(0.1, 0.3, 0.4);
                    for (let o = 0; o < _; o++) {
                        const e = W[o];
                        (l[o * 3] = e.x), (l[o * 3 + 1] = e.y), (l[o * 3 + 2] = e.z);
                        let t = 0.5;
                        (e.type === "body" || e.type === "tailstock") && e.theta !== void 0
                            ? (t = Math.pow((Math.sin(e.theta) + 1) * 0.5, 0.6))
                            : e.type === "fin"
                              ? (t = 0.35 + (1 - e.finT) * 0.35)
                              : e.type === "fluke"
                                ? (t = 0.5 + (1 - (e.flukeSpanT || 0)) * 0.25)
                                : e.type === "dorsal" && (t = 0.75),
                            (t = Math.max(0, Math.min(1, t + (Math.random() - 0.5) * 0.15)));
                        const c = new h().lerpColors(A, y, t);
                        (a[o * 3] = c.r),
                            (a[o * 3 + 1] = c.g),
                            (a[o * 3 + 2] = c.b),
                            (P[o] = 0.09 + Math.random() * 0.11);
                    }
                    p.setAttribute("position", new q(l, 3)),
                        p.setAttribute("color", new q(a, 3)),
                        p.setAttribute("size", new q(P, 1));
                    const b = new St({
                        uniforms: { pixelRatio: { value: C.getPixelRatio() } },
                        vertexShader: `
				attribute float size; attribute vec3 color;
				varying vec3 vColor; varying float vAlpha;
				uniform float pixelRatio;
				void main() {
					vColor = color;
					vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
					vAlpha = smoothstep(120.0, 10.0, length(mvPosition.xyz));
					gl_PointSize = size * pixelRatio * (220.0 / -mvPosition.z);
					gl_Position = projectionMatrix * mvPosition;
				}
			`,
                        fragmentShader: `
				varying vec3 vColor; varying float vAlpha;
				void main() {
					float dist = length(gl_PointCoord - vec2(0.5));
					if (dist > 0.5) discard;
					gl_FragColor = vec4(mix(vColor, vColor * 1.3, smoothstep(0.35, 0.0, dist)), smoothstep(0.5, 0.05, dist) * vAlpha * 0.9);
				}
			`,
                        transparent: !0,
                        depthWrite: !1,
                        blending: At,
                    });
                    Y.add(p);
                    const I = new Gt(p, b);
                    X.add(I);
                    for (let o = 0; o < $; o++) {
                        const e = (o - Math.floor($ / 2)) * B;
                        for (let n = 0; n < 1e4; n++) {
                            const r = e + (Math.random() - 0.5) * B,
                                s = Math.random(),
                                i = F + s * ct,
                                g = -R - Math.random() * dt,
                                M = K(r, i, g) * 3,
                                d = g - Math.abs(M),
                                m = Math.random() > 0.3;
                            T.push({
                                x: r + (Math.random() - 0.5) * 1.2,
                                y: i + (Math.random() - 0.5) * 1.5,
                                z: m ? -R - Math.random() * 5 + K(r, i, 0) * 2 : d,
                                type: "rock",
                                heightT: s,
                                side: -1,
                            });
                        }
                        for (let n = 0; n < 1e4; n++) {
                            const r = e + (Math.random() - 0.5) * B,
                                s = Math.random(),
                                i = F + s * ct,
                                g = R + Math.random() * dt,
                                M = K(r, i, g) * 3,
                                d = g + Math.abs(M),
                                m = Math.random() > 0.3;
                            T.push({
                                x: r + (Math.random() - 0.5) * 1.2,
                                y: i + (Math.random() - 0.5) * 1.5,
                                z: m ? R + Math.random() * 5 + K(r, i, 0) * 2 : d,
                                type: "rock",
                                heightT: s,
                                side: 1,
                            });
                        }
                        for (let n = 0; n < 2e3; n++) {
                            const r = e + (Math.random() - 0.5) * B,
                                s = Math.random() > 0.5 ? 1 : -1,
                                i = F + ct + (Math.random() - 0.5) * 3,
                                g = s * (R + 3 + Math.random() * dt * 0.8);
                            T.push({ x: r, y: i, z: g, type: "top", side: s });
                        }
                        for (let n = 0; n < 3e3; n++) {
                            const r = e + (Math.random() - 0.5) * B,
                                s = (Math.random() - 0.5) * R * 1.8,
                                i = F + K(r * 0.5, 0, s * 0.5) * 1.5;
                            T.push({
                                x: r + (Math.random() - 0.5) * 1.5,
                                y: i + (Math.random() - 0.5) * 0.8,
                                z: s,
                                type: "floor",
                            });
                        }
                        const t = 5 + Math.floor(Math.random() * 4);
                        for (let n = 0; n < t; n++) {
                            const r = e + (Math.random() - 0.5) * B * 0.9,
                                s = (Math.random() - 0.5) * R * 1.5,
                                i = F,
                                g = Math.floor(Math.random() * 6),
                                M = 2 + Math.random() * 3,
                                d = 60 + Math.floor(Math.random() * 80);
                            for (let m = 0; m < d; m++) {
                                const u = Math.random(),
                                    k = Math.random() * Math.PI * 2,
                                    x = Math.random() * M;
                                T.push({
                                    x: r + Math.cos(k) * x,
                                    y: i + u * (M * 1.5) + Math.random() * 0.5,
                                    z: s + Math.sin(k) * x,
                                    type: "coralGlow",
                                    coralType: g,
                                    glowPhase: Math.random() * Math.PI * 2,
                                });
                            }
                        }
                        const c = 8 + Math.floor(Math.random() * 6);
                        for (let n = 0; n < c; n++) {
                            const r = e + (Math.random() - 0.5) * B * 0.85,
                                s = (Math.random() - 0.5) * R * 1.6,
                                i = F,
                                g = Math.floor(Math.random() * 4),
                                M = 2 + Math.random() * 2.5,
                                d = 8 + Math.floor(Math.random() * 5);
                            for (let m = 0; m < d; m++) {
                                const u = (m / d) * Math.PI * 2,
                                    k = 15 + Math.floor(Math.random() * 10);
                                for (let x = 0; x < k; x++) {
                                    const O = x / k,
                                        N = Math.sin(O * Math.PI) * 0.5;
                                    T.push({
                                        x: r + Math.cos(u) * (0.3 + O * M * 0.6) + N * Math.cos(u + Math.PI / 2) * 0.3,
                                        y: i + O * M,
                                        z: s + Math.sin(u) * (0.3 + O * M * 0.6) + N * Math.sin(u + Math.PI / 2) * 0.3,
                                        type: "anemone",
                                        anemoneType: g,
                                        glowPhase: Math.random() * Math.PI * 2,
                                        tentacleT: O,
                                    });
                                }
                            }
                        }
                        const w = 12 + Math.floor(Math.random() * 8);
                        for (let n = 0; n < w; n++) {
                            const r = e + (Math.random() - 0.5) * B * 0.9,
                                s = (Math.random() - 0.5) * R * 1.7,
                                i = F,
                                g = Math.floor(Math.random() * 3),
                                M = 5 + Math.random() * 7;
                            for (let d = 0; d < 40; d++) {
                                const m = Math.random();
                                T.push({
                                    x: r + (Math.random() - 0.5) * 0.4,
                                    y: i + m * M,
                                    z: s + (Math.random() - 0.5) * 0.4,
                                    type: "kelp",
                                    kelpType: g,
                                    kelpT: m,
                                    glowPhase: Math.random() * Math.PI * 2,
                                });
                            }
                        }
                        const v = 5 + Math.floor(Math.random() * 4);
                        for (let n = 0; n < v; n++) {
                            const r = e + (Math.random() - 0.5) * B * 0.8,
                                s = (Math.random() - 0.5) * R * 1.4,
                                i = F,
                                g = Math.floor(Math.random() * 3),
                                M = 1.2 + Math.random() * 2;
                            for (let d = 0; d < 20; d++) {
                                const m = Math.random();
                                T.push({
                                    x: r + (Math.random() - 0.5) * 0.3,
                                    y: i + m * M * 1.5,
                                    z: s + (Math.random() - 0.5) * 0.3,
                                    type: "mushroom",
                                    mushType: g,
                                    isCap: !1,
                                    glowPhase: Math.random() * Math.PI * 2,
                                });
                            }
                            for (let d = 0; d < 40; d++) {
                                const m = Math.random() * Math.PI * 2,
                                    u = Math.random() * M;
                                T.push({
                                    x: r + Math.cos(m) * u,
                                    y: i + M * 1.5 + (Math.random() - 0.5) * 0.3 - u * 0.15,
                                    z: s + Math.sin(m) * u,
                                    type: "mushroom",
                                    mushType: g,
                                    isCap: !0,
                                    glowPhase: Math.random() * Math.PI * 2,
                                });
                            }
                        }
                        for (let n = 0; n < 300; n++) {
                            const r = e + (Math.random() - 0.5) * B,
                                s = (Math.random() - 0.5) * R * 1.6,
                                i = F + Math.random() * 0.8;
                            T.push({
                                x: r,
                                y: i,
                                z: s,
                                type: "floorGlow",
                                glowType: Math.floor(Math.random() * 5),
                                glowPhase: Math.random() * Math.PI * 2,
                            });
                        }
                    }
                    for (let o = 0; o < 800; o++)
                        T.push({
                            x: (Math.random() - 0.5) * B * $,
                            y: F + 5 + Math.random() * 30,
                            z: (Math.random() - 0.5) * R * 1.5,
                            type: "float",
                            phase: Math.random() * Math.PI * 2,
                            speed: 0.15 + Math.random() * 0.2,
                        });
                    for (let o = 0; o < 400; o++)
                        T.push({
                            x: (Math.random() - 0.5) * B * $,
                            y: F + 10 + Math.random() * 20,
                            z: (Math.random() - 0.5) * R,
                            type: "light",
                            baseY: F + 10 + Math.random() * 20,
                            phase: Math.random() * Math.PI * 2,
                        });
                    for (let o = 0; o < Ao; o++) {
                        const e = -350 + o * So + (Math.random() - 0.5) * 20,
                            t = o % 2 === 0 ? 1 : -1,
                            c = t * (R + 2),
                            w = F + 6 + Math.random() * 6,
                            v = Math.floor(Math.random() * mt.length),
                            n = mt[v],
                            r = n?.color.clone() || new h().setHSL(Math.random(), 0.9, 0.55),
                            s = 10,
                            i = 16,
                            g = T.length;
                        for (let d = 0; d < 350; d++) {
                            const m = Math.random();
                            let u, k;
                            if (m < 0.35) (u = -s / 2 + (Math.random() - 0.5) * 1.2), (k = Math.random() * i);
                            else if (m < 0.7) (u = s / 2 + (Math.random() - 0.5) * 1.2), (k = Math.random() * i);
                            else {
                                const x = Math.random() * Math.PI;
                                (u = (Math.cos(x) * s) / 2), (k = i + Math.sin(x) * 3);
                            }
                            T.push({
                                x: e + (Math.random() - 0.5) * 0.6,
                                y: w + k,
                                z: c + u * 0.35 * t,
                                type: "gate",
                                gateIndex: o,
                                glowPhase: Math.random() * Math.PI * 2,
                            });
                        }
                        for (let d = 0; d < 300; d++) {
                            const m = (Math.random() - 0.5) * s * 0.85,
                                u = Math.random() * i * 0.95;
                            T.push({
                                x: e + (Math.random() - 0.5) * 0.4,
                                y: w + u + 0.5,
                                z: c + m * 0.3 * t,
                                type: "gateInner",
                                gateIndex: o,
                                glowPhase: Math.random() * Math.PI * 2,
                            });
                        }
                        for (let d = 0; d < 150; d++) {
                            const m = Math.random();
                            let u, k;
                            if (m < 0.35)
                                (u = -s / 2 - 1.5 + (Math.random() - 0.5) * 1.5), (k = Math.random() * (i + 2));
                            else if (m < 0.7)
                                (u = s / 2 + 1.5 + (Math.random() - 0.5) * 1.5), (k = Math.random() * (i + 2));
                            else {
                                const x = Math.random() * Math.PI;
                                (u = Math.cos(x) * (s / 2 + 2)), (k = i + Math.sin(x) * 4.5);
                            }
                            T.push({
                                x: e + (Math.random() - 0.5) * 0.8,
                                y: w + k - 1,
                                z: c + u * 0.35 * t,
                                type: "gateOuter",
                                gateIndex: o,
                                glowPhase: Math.random() * Math.PI * 2,
                            });
                        }
                        const M = T.length;
                        H.push({
                            x: e,
                            y: w + i / 2,
                            z: c,
                            width: s,
                            height: i,
                            link: n?.link,
                            linkIndex: v,
                            color: r,
                            side: t,
                            particleStart: g,
                            particleEnd: M,
                            hovered: !1,
                        });
                    }
                    const S = T.length,
                        G = new It(),
                        j = new Float32Array(S * 3),
                        U = new Float32Array(S * 3),
                        L = new Float32Array(S * 3),
                        ft = new Float32Array(S),
                        ut = new Float32Array(S),
                        wt = new Float32Array(S);
                    Y.add(G);
                    const Ot = new h(8243164),
                        gt = new h(12571353),
                        yt = new h(2188398),
                        Zt = new h(2781838),
                        Dt = new h(16777215),
                        jt = [
                            new h(16720486),
                            new h(16737826),
                            new h(16763904),
                            new h(65450),
                            new h(43775),
                            new h(11141375),
                        ],
                        Ut = [new h(16729258), new h(4521949), new h(16755268), new h(14501119)],
                        Vt = [new h(2293606), new h(4521898), new h(11206434)],
                        qt = [new h(4513279), new h(16729309), new h(14548804)],
                        Nt = [new h(4521983), new h(16729343), new h(16777028), new h(4521796), new h(16729156)];
                    for (let o = 0; o < S; o++) {
                        const e = T[o];
                        (j[o * 3] = e.x), (j[o * 3 + 1] = e.y), (j[o * 3 + 2] = e.z);
                        let t,
                            c,
                            w = 0;
                        if (e.type === "rock") {
                            const v = e.heightT;
                            v > 0.7
                                ? (t = new h().lerpColors(gt, Ot, (v - 0.7) / 0.3))
                                : v > 0.3
                                  ? (t = new h().lerpColors(yt, gt, (v - 0.3) / 0.4))
                                  : (t = yt.clone()),
                                (t.r += (Math.random() - 0.5) * 0.1),
                                (t.g += (Math.random() - 0.5) * 0.1),
                                (c = 0.3 + Math.random() * 0.4);
                        } else if (e.type === "top") (t = Dt.clone()), (c = 0.35 + Math.random() * 0.4);
                        else if (e.type === "floor") (t = Zt.clone()), (c = 0.25 + Math.random() * 0.3);
                        else if (e.type === "coralGlow")
                            (t = jt[e.coralType]?.clone()), (c = 0.2 + Math.random() * 0.25), (w = 1);
                        else if (e.type === "anemone") {
                            if (((t = Ut[e.anemoneType]?.clone()), !t)) return;
                            const v = 0.8 + e.tentacleT * 0.4;
                            (t.r *= v), (t.g *= v), (t.b *= v), (c = 0.15 + Math.random() * 0.18), (w = 1);
                        } else if (e.type === "kelp") {
                            if (((t = Vt[e.kelpType]?.clone()), !t)) return;
                            const v = 0.7 + e.kelpT * 0.5;
                            (t.r *= v), (t.g *= v), (t.b *= v), (c = 0.12 + Math.random() * 0.15), (w = 1);
                        } else if (e.type === "mushroom") {
                            if (((t = qt[e.mushType]?.clone()), !t)) return;
                            e.isCap
                                ? ((t.r = Math.min(1, t.r * 1.3)),
                                  (t.g = Math.min(1, t.g * 1.3)),
                                  (t.b = Math.min(1, t.b * 1.3)),
                                  (c = 0.2 + Math.random() * 0.2))
                                : ((t.r *= 0.7), (t.g *= 0.7), (t.b *= 0.7), (c = 0.1 + Math.random() * 0.12)),
                                (w = 1);
                        } else
                            e.type === "floorGlow"
                                ? ((t = Nt[e.glowType]?.clone()), (c = 0.12 + Math.random() * 0.15), (w = 1))
                                : e.type === "float"
                                  ? ((t = new h(4491434)), (c = 0.06 + Math.random() * 0.08))
                                  : e.type === "light"
                                    ? ((t = new h(8965358)), (c = 0.1 + Math.random() * 0.12))
                                    : e.type === "gate"
                                      ? ((t = H[e.gateIndex].color.clone()), (c = 0.4 + Math.random() * 0.45), (w = 2))
                                      : e.type === "gateInner"
                                        ? ((t = H[e.gateIndex].color.clone()),
                                          (t.r = Math.min(1, t.r * 1.6)),
                                          (t.g = Math.min(1, t.g * 1.6)),
                                          (t.b = Math.min(1, t.b * 1.6)),
                                          (c = 0.3 + Math.random() * 0.35),
                                          (w = 2))
                                        : e.type === "gateOuter"
                                          ? ((t = H[e.gateIndex].color.clone()),
                                            (t.r *= 0.6),
                                            (t.g *= 0.6),
                                            (t.b *= 0.6),
                                            (c = 0.25 + Math.random() * 0.3),
                                            (w = 2))
                                          : ((t = new h(5275808)), (c = 0.15));
                        (U[o * 3] = t.r),
                            (U[o * 3 + 1] = t.g),
                            (U[o * 3 + 2] = t.b),
                            (L[o * 3] = t.r),
                            (L[o * 3 + 1] = t.g),
                            (L[o * 3 + 2] = t.b),
                            (ft[o] = c),
                            (ut[o] = c),
                            (wt[o] = w);
                    }
                    G.setAttribute("position", new q(j, 3)),
                        G.setAttribute("color", new q(U, 3)),
                        G.setAttribute("size", new q(ft, 1)),
                        G.setAttribute("glow", new q(wt, 1));
                    const st = new St({
                        uniforms: { pixelRatio: { value: C.getPixelRatio() }, time: { value: 0 } },
                        vertexShader: `
				attribute float size; 
				attribute vec3 color;
				attribute float glow;
				varying vec3 vColor; 
				varying float vAlpha;
				varying float vGlow;
				uniform float pixelRatio;
				uniform float time;
				void main() {
				vColor = color;
				vGlow = glow;
				vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
				float dist = length(mvPosition.xyz);
				vAlpha = smoothstep(160.0, 8.0, dist);
				
				float pulseSize = 1.0;
				if (glow > 1.5) {
					pulseSize = 1.0 + sin(time * 2.5 + position.y * 0.5) * 0.2;
				} else if (glow > 0.5) {
					pulseSize = 1.0 + sin(time * 1.5 + position.x * 0.5 + position.z * 0.5) * 0.15;
				}
				
				gl_PointSize = size * pulseSize * pixelRatio * (160.0 / -mvPosition.z);
				gl_Position = projectionMatrix * mvPosition;
				}
			`,
                        fragmentShader: `
				varying vec3 vColor; 
				varying float vAlpha;
				varying float vGlow;
				void main() {
				float dist = length(gl_PointCoord - vec2(0.5));
				if (dist > 0.5) discard;
				float alpha = smoothstep(0.5, 0.08, dist) * vAlpha;
				
				float glowBoost = 1.2;
				if (vGlow > 1.5) glowBoost = 2.2;
				else if (vGlow > 0.5) glowBoost = 1.6;
				
				vec3 finalColor = vColor * glowBoost;
				
				float bloom = 0.0;
				if (vGlow > 1.5) bloom = smoothstep(0.5, 0.0, dist) * 1.0;
				else if (vGlow > 0.5) bloom = smoothstep(0.5, 0.0, dist) * 0.5;
				finalColor += bloom;
				
				gl_FragColor = vec4(finalColor, alpha * 0.92);
				}
			`,
                        transparent: !0,
                        depthWrite: !1,
                        blending: At,
                    });
                    Y.add(st);
                    const Jt = new Gt(G, st);
                    X.add(Jt);
                    const vt = new _t(2, 2),
                        tt = new Rt({ color: 657930, transparent: !0, opacity: 0, depthTest: !1 });
                    Y.add(vt), Y.add(tt);
                    const xt = new Bt(vt, tt);
                    xt.renderOrder = 999;
                    const Kt = new lo(-1, 1, 1, -1, 0, 1),
                        Pt = new Tt();
                    Pt.add(xt);
                    let bt = 0,
                        kt = 0;
                    const zt = new ho(),
                        rt = new co();
                    let Z = null,
                        it = null,
                        V = 0,
                        ot = !1,
                        et = {};
                    const lt = [];
                    H.forEach((o, e) => {
                        const t = new _t(o.width * 0.5, o.height * 1.1),
                            c = new Rt({ visible: !1, side: Mo }),
                            w = new Bt(t, c);
                        w.position.set(o.x, o.y, o.z),
                            (w.rotation.y = o.side > 0 ? -Math.PI / 2 : Math.PI / 2),
                            (w.userData = { gateIndex: e }),
                            Y.add(t),
                            Y.add(c),
                            X.add(w),
                            lt.push(w),
                            (et[e] = 0);
                    });
                    const $t = (o) => {
                            (bt = (o.clientX / window.innerWidth - 0.5) * 0.5),
                                (kt = (o.clientY / window.innerHeight - 0.5) * 0.5),
                                (rt.x = (o.clientX / window.innerWidth) * 2 - 1),
                                (rt.y = -(o.clientY / window.innerHeight) * 2 + 1);
                        },
                        Qt = (o) => {
                            Z !== null && !ot && ((it = Z), (ot = !0), (V = 0));
                        },
                        to = () => {
                            (z.aspect = window.innerWidth / window.innerHeight),
                                z.updateProjectionMatrix(),
                                C.setSize(window.innerWidth, window.innerHeight);
                        },
                        oo = () => {
                            D.value.style.cursor = Z !== null ? "pointer" : "default";
                        };
                    mo(D, to), Ft(D, "mousemove", $t), Ft(D, "click", Qt);
                    const eo = new po();
                    let at = 0,
                        ht;
                    function Ct() {
                        const o = eo.getElapsedTime();
                        if (((st.uniforms.time.value = o), ot && it !== null)) {
                            V += 0.012;
                            const n = H[it],
                                r = n.x - at,
                                s = n.y,
                                i = n.z * 0.3,
                                g = V * V * (3 - 2 * V);
                            if (
                                ((z.position.x += (r + 10 - z.position.x) * g * 0.1),
                                (z.position.y += (s - z.position.y) * g * 0.1),
                                (z.position.z += (i - z.position.z) * g * 0.1),
                                z.lookAt(r, s, n.z),
                                (tt.opacity = Math.min(1, V * 1.5)),
                                V >= 1)
                            ) {
                                ko(Et(`/${n.link}`, Yt.value));
                                return;
                            }
                        } else {
                            (at += 1.2 * 0.016), zt.setFromCamera(rt, z);
                            const r = zt.intersectObjects(lt),
                                s = Z;
                            (Z = null), r.length > 0 && (Z = r[0]?.object.userData.gateIndex), Z !== s && oo();
                            for (let M = 0; M < H.length; M++) {
                                const d = M === Z ? 1 : 0;
                                et[M] += (d - et[M]) * 0.15;
                            }
                            const i = G.attributes.color.array,
                                g = G.attributes.size.array;
                            for (let M = 0; M < H.length; M++) {
                                const d = H[M],
                                    m = et[M],
                                    u = 1 + m * 2,
                                    k = 1 + m * 1.5;
                                for (let x = d.particleStart; x < d.particleEnd; x++) {
                                    const O = L[x * 3],
                                        N = L[x * 3 + 1],
                                        ao = L[x * 3 + 2];
                                    (i[x * 3] = Math.min(1, O * u)),
                                        (i[x * 3 + 1] = Math.min(1, N * u)),
                                        (i[x * 3 + 2] = Math.min(1, ao * u)),
                                        (g[x] = ut[x] * k);
                                }
                            }
                            (G.attributes.color.needsUpdate = !0), (G.attributes.size.needsUpdate = !0);
                        }
                        const e = p.attributes.position.array,
                            t = 0.5,
                            c = 0.7;
                        for (let n = 0; n < _; n++) {
                            const r = E[n],
                                s = W[n],
                                i = s.t,
                                g = Math.pow(i, 1.8) * 2,
                                M = i * Math.PI * 2 * c,
                                d = Math.sin(o * t - M) * g,
                                m = Math.sin(o * t - M + Math.PI * 0.5) * g * 0.06;
                            if (
                                ((e[n * 3] = r.x + m),
                                (e[n * 3 + 1] = r.y + d),
                                (e[n * 3 + 2] = r.z),
                                s.type === "fin" && (e[n * 3 + 1] += Math.sin(o * 0.25 + s.side * 0.3) * 0.12 * s.finT),
                                s.type === "tailstock" || s.type === "fluke")
                            ) {
                                const u = i * Math.PI * 2 * c;
                                if (s.type === "fluke" && s.flukeSpanT !== void 0) {
                                    const k = s.flukeSpanT,
                                        x = Math.cos(o * t - u),
                                        O = x * k * k * 1,
                                        N = Math.sin(o * t - u - k * 0.3) * Math.pow(i, 1.5) * 2.2;
                                    (e[n * 3 + 1] = r.y + N - O), (e[n * 3] = r.x + m + x * k * 0.1 * (s.side || 0));
                                } else e[n * 3 + 1] = r.y + Math.sin(o * t - u) * Math.pow(i, 1.5) * 2.2;
                            }
                        }
                        (p.attributes.position.needsUpdate = !0),
                            ot ||
                                ((I.position.y = Math.sin(o * 0.15) * 0.8),
                                (I.position.z = Math.sin(o * 0.12) * 1),
                                (X.rotation.y += (bt - X.rotation.y) * 0.02),
                                (X.rotation.x += (kt - X.rotation.x) * 0.002));
                        const w = G.attributes.position.array,
                            v = B * $;
                        for (let n = 0; n < S; n++) {
                            const r = T[n];
                            let s = r.x + at;
                            for (; s > v / 2; ) s -= v;
                            for (; s < -v / 2; ) s += v;
                            (w[n * 3] = s),
                                r.type === "float" && (w[n * 3 + 1] = r.y + Math.sin(o * r.speed + r.phase) * 0.5),
                                r.type === "light" && (w[n * 3 + 1] = r.baseY + Math.sin(o * 0.2 + r.phase) * 2),
                                r.type === "kelp" && (w[n * 3] = s + Math.sin(o * 0.4 + r.glowPhase) * r.kelpT * 0.6),
                                r.type === "anemone" &&
                                    (w[n * 3] = s + Math.sin(o * 0.3 + r.glowPhase) * r.tentacleT * 0.3);
                        }
                        (G.attributes.position.needsUpdate = !0),
                            lt.forEach((n, r) => {
                                let i = H[r].x + at;
                                for (; i > v / 2; ) i -= v;
                                for (; i < -v / 2; ) i += v;
                                n.position.x = i;
                            }),
                            C.render(f, z),
                            tt.opacity > 0 && ((C.autoClear = !1), C.render(Pt, Kt), (C.autoClear = !0)),
                            (ht = requestAnimationFrame(Ct));
                    }
                    Ct(),
                        (Ht.value = !0),
                        xo(() => {
                            C.dispose(),
                                C.forceContextLoss(),
                                C.domElement.remove(),
                                Y.forEach((o) => {
                                    o.dispose && o.dispose();
                                }),
                                Y.clear(),
                                ht !== void 0 && cancelAnimationFrame(ht);
                        });
                }),
                (f, z) => (
                    bo(),
                    Po("div", zo, [
                            nt("div", Co, [
                            nt("h1", To, "ANIMA. The Living AI Layer.", 1),
                            nt("p", Io, "Immersive AI animation", 1),
                        ]),
                        nt("div", { ref_key: "containerRef", ref: D, class: "w-full h-full" }, null, 512),
                    ])
                )
            );
        },
    }),
    Wo = Object.assign(Go, { __name: "ExperienceWhale" });
export { Wo as default };
