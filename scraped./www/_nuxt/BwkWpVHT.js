const xe = typeof window < "u",
    _t = xe ? window : null,
    H = xe ? document : null,
    L = { OBJECT: 0, ATTRIBUTE: 1, CSS: 2, TRANSFORM: 3, CSS_VAR: 4 },
    C = { NUMBER: 0, UNIT: 1, COLOR: 2, COMPLEX: 3 },
    fe = { NONE: 0, AUTO: 1, FORCE: 2 },
    oe = { replace: 0, none: 1, blend: 2 },
    Gt = Symbol(),
    Wt = Symbol(),
    hs = Symbol(),
    St = Symbol(),
    Fs = Symbol(),
    E = 1e-11,
    $t = 1e12,
    je = 1e3,
    Ut = 120,
    Ae = "",
    Bs = "var(",
    ds = (() => {
        const e = new Map();
        return e.set("x", "translateX"), e.set("y", "translateY"), e.set("z", "translateZ"), e;
    })(),
    fs = [
        "translateX",
        "translateY",
        "translateZ",
        "rotate",
        "rotateX",
        "rotateY",
        "rotateZ",
        "scale",
        "scaleX",
        "scaleY",
        "scaleZ",
        "skew",
        "skewX",
        "skewY",
        "matrix",
        "matrix3d",
        "perspective",
    ],
    ps = fs.reduce((e, t) => ({ ...e, [t]: t + "(" }), {}),
    ie = () => {},
    Vs = /(^#([\da-f]{3}){1,2}$)|(^#([\da-f]{4}){1,2}$)/i,
    ks = /rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/i,
    qs = /rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(-?\d+|-?\d*.\d+)\s*\)/i,
    Hs = /hsl\(\s*(-?\d+|-?\d*.\d+)\s*,\s*(-?\d+|-?\d*.\d+)%\s*,\s*(-?\d+|-?\d*.\d+)%\s*\)/i,
    Ws = /hsla\(\s*(-?\d+|-?\d*.\d+)\s*,\s*(-?\d+|-?\d*.\d+)%\s*,\s*(-?\d+|-?\d*.\d+)%\s*,\s*(-?\d+|-?\d*.\d+)\s*\)/i,
    Zt = /[-+]?\d*\.?\d+(?:e[-+]?\d)?/gi,
    ms = /^([-+]?\d*\.?\d+(?:e[-+]?\d+)?)([a-z]+|%)$/i,
    Xs = /([a-z])([A-Z])/g,
    zs = /(\w+)(\([^)]+\)+)/g,
    Js = /(\*=|\+=|-=)/,
    Qs = /var\(\s*(--[\w-]+)(?:\s*,\s*([^)]+))?\s*\)/;
const _s = {
        id: null,
        keyframes: null,
        playbackEase: null,
        playbackRate: 1,
        frameRate: Ut,
        loop: 0,
        reversed: !1,
        alternate: !1,
        autoplay: !0,
        persist: !1,
        duration: je,
        delay: 0,
        loopDelay: 0,
        ease: "out(2)",
        composition: oe.replace,
        modifier: (e) => e,
        onBegin: ie,
        onBeforeUpdate: ie,
        onUpdate: ie,
        onLoop: ie,
        onPause: ie,
        onComplete: ie,
        onRender: ie,
    },
    he = { current: null, root: H },
    O = { defaults: _s, precision: 4, timeScale: 1, tickThreshold: 200 },
    Ts = { version: "4.2.2", engine: null };
xe && (_t.AnimeJS || (_t.AnimeJS = []), _t.AnimeJS.push(Ts));
const gs = (e) => e.replace(Xs, "$1-$2").toLowerCase(),
    Ne = (e, t) => e.indexOf(t) === 0,
    et = Date.now,
    Ie = Array.isArray,
    Ye = (e) => e && e.constructor === Object,
    Ke = (e) => typeof e == "number" && !isNaN(e),
    Be = (e) => typeof e == "string",
    Y = (e) => typeof e == "function",
    S = (e) => typeof e > "u",
    Ge = (e) => S(e) || e === null,
    ys = (e) => xe && e instanceof SVGElement,
    vs = (e) => Vs.test(e),
    bs = (e) => Ne(e, "rgb"),
    Cs = (e) => Ne(e, "hsl"),
    Ys = (e) => vs(e) || bs(e) || Cs(e),
    Tt = (e) => !O.defaults.hasOwnProperty(e),
    Ks = ["opacity", "rotate", "overflow", "color"],
    Gs = (e, t) => {
        if (Ks.includes(t)) return !1;
        if (e.getAttribute(t) || t in e) {
            if (t === "scale") {
                const s = e.parentNode;
                return s && s.tagName === "filter";
            }
            return !0;
        }
    },
    Et = (e) => (Be(e) ? parseFloat(e) : e),
    Xe = Math.pow,
    Ss = Math.sqrt,
    Zs = Math.sin,
    js = Math.cos,
    jt = Math.abs,
    Ft = Math.floor,
    en = Math.asin,
    tn = Math.max,
    Xt = Math.PI,
    es = Math.round,
    re = (e, t, s) => (e < t ? t : e > s ? s : e),
    ts = {},
    D = (e, t) => {
        if (t < 0) return e;
        if (!t) return es(e);
        let s = ts[t];
        return s || (s = ts[t] = 10 ** t), es(e * s) / s;
    },
    Fe = (e, t, s) => e + (t - e) * s,
    zt = (e) => (e === 1 / 0 ? $t : e === -1 / 0 ? -$t : e),
    at = (e) => (e <= E ? E : zt(D(e, 11))),
    j = (e) => (Ie(e) ? [...e] : e),
    ws = (e, t) => {
        const s = { ...e };
        for (let r in t) {
            const n = e[r];
            s[r] = S(n) ? t[r] : n;
        }
        return s;
    },
    F = (e, t, s, r = "_prev", n = "_next") => {
        let i = e._head,
            o = n;
        for (s && ((i = e._tail), (o = r)); i; ) {
            const l = i[o];
            t(i), (i = l);
        }
    },
    it = (e, t, s = "_prev", r = "_next") => {
        const n = t[s],
            i = t[r];
        n ? (n[r] = i) : (e._head = i), i ? (i[s] = n) : (e._tail = n), (t[s] = null), (t[r] = null);
    },
    Qe = (e, t, s, r = "_prev", n = "_next") => {
        let i = e._tail;
        for (; i && s && s(i, t); ) i = i[r];
        const o = i ? i[n] : e._head;
        i ? (i[n] = t) : (e._head = t), o ? (o[r] = t) : (e._tail = t), (t[r] = i), (t[n] = o);
    };
const sn = (e, t, s) => {
    const r = e.style.transform;
    let n;
    if (r) {
        const i = e[St];
        let o;
        for (; (o = zs.exec(r)); ) {
            const l = o[1],
                a = o[2].slice(1, -1);
            (i[l] = a), l === t && ((n = a), s && (s[t] = a));
        }
    }
    return r && !S(n) ? n : Ne(t, "scale") ? "1" : Ne(t, "rotate") || Ne(t, "skew") ? "0deg" : "0px";
};
const nn = (e) => {
        const t = ks.exec(e) || qs.exec(e),
            s = S(t[4]) ? 1 : +t[4];
        return [+t[1], +t[2], +t[3], s];
    },
    rn = (e) => {
        const t = e.length,
            s = t === 4 || t === 5;
        return [
            +("0x" + e[1] + e[s ? 1 : 2]),
            +("0x" + e[s ? 2 : 3] + e[s ? 2 : 4]),
            +("0x" + e[s ? 3 : 5] + e[s ? 3 : 6]),
            t === 5 || t === 9 ? +(+("0x" + e[s ? 4 : 7] + e[s ? 4 : 8]) / 255).toFixed(3) : 1,
        ];
    },
    Rt = (e, t, s) => (
        s < 0 && (s += 1),
        s > 1 && (s -= 1),
        s < 1 / 6 ? e + (t - e) * 6 * s : s < 1 / 2 ? t : s < 2 / 3 ? e + (t - e) * (2 / 3 - s) * 6 : e
    ),
    on = (e) => {
        const t = Hs.exec(e) || Ws.exec(e),
            s = +t[1] / 360,
            r = +t[2] / 100,
            n = +t[3] / 100,
            i = S(t[4]) ? 1 : +t[4];
        let o, l, a;
        if (r === 0) o = l = a = n;
        else {
            const c = n < 0.5 ? n * (1 + r) : n + r - n * r,
                u = 2 * n - c;
            (o = D(Rt(u, c, s + 1 / 3) * 255, 0)), (l = D(Rt(u, c, s) * 255, 0)), (a = D(Rt(u, c, s - 1 / 3) * 255, 0));
        }
        return [o, l, a, i];
    },
    an = (e) => (bs(e) ? nn(e) : vs(e) ? rn(e) : Cs(e) ? on(e) : [0, 0, 0, 1]);
const P = (e, t) => (S(e) ? t : e),
    Re = (e, t, s, r, n) => {
        let i;
        if (Y(e))
            i = () => {
                const o = e(t, s, r);
                return isNaN(+o) ? o || 0 : +o;
            };
        else if (Be(e) && Ne(e, Bs))
            i = () => {
                const o = e.match(Qs),
                    l = o[1],
                    a = o[2];
                let c = getComputedStyle(t)?.getPropertyValue(l);
                return (!c || c.trim() === Ae) && a && (c = a.trim()), c || 0;
            };
        else return e;
        return n && (n.func = i), i();
    },
    Ns = (e, t) =>
        e[Wt]
            ? e[hs] && Gs(e, t)
                ? L.ATTRIBUTE
                : fs.includes(t) || ds.get(t)
                  ? L.TRANSFORM
                  : Ne(t, "--")
                    ? L.CSS_VAR
                    : t in e.style
                      ? L.CSS
                      : t in e
                        ? L.OBJECT
                        : L.ATTRIBUTE
            : L.OBJECT,
    ss = (e, t, s) => {
        const r = e.style[t];
        r && s && (s[t] = r);
        const n = r || getComputedStyle(e[Fs] || e).getPropertyValue(t);
        return n === "auto" ? "0" : n;
    },
    ze = (e, t, s, r) => {
        const n = S(s) ? Ns(e, t) : s;
        return n === L.OBJECT
            ? e[t] || 0
            : n === L.ATTRIBUTE
              ? e.getAttribute(t)
              : n === L.TRANSFORM
                ? sn(e, t, r)
                : n === L.CSS_VAR
                  ? ss(e, t, r).trimStart()
                  : ss(e, t, r);
    },
    gt = (e, t, s) => (s === "-" ? e - t : s === "+" ? e + t : e * t),
    Jt = () => ({ t: C.NUMBER, n: 0, u: null, o: null, d: null, s: null }),
    ve = (e, t) => {
        if (((t.t = C.NUMBER), (t.n = 0), (t.u = null), (t.o = null), (t.d = null), (t.s = null), !e)) return t;
        const s = +e;
        if (isNaN(s)) {
            let r = e;
            r[1] === "=" && ((t.o = r[0]), (r = r.slice(2)));
            const n = r.includes(" ") ? !1 : ms.exec(r);
            if (n) return (t.t = C.UNIT), (t.n = +n[1]), (t.u = n[2]), t;
            if (t.o) return (t.n = +r), t;
            if (Ys(r)) return (t.t = C.COLOR), (t.d = an(r)), t;
            {
                const i = r.match(Zt);
                return (t.t = C.COMPLEX), (t.d = i ? i.map(Number) : []), (t.s = r.split(Zt) || []), t;
            }
        } else return (t.n = s), t;
    },
    ns = (e, t) => (
        (t.t = e._valueType),
        (t.n = e._toNumber),
        (t.u = e._unit),
        (t.o = null),
        (t.d = j(e._toNumbers)),
        (t.s = j(e._strings)),
        t
    ),
    De = Jt();
const yt = (e, t, s, r, n) => {
        const i = e.parent,
            o = e.duration,
            l = e.completed,
            a = e.iterationDuration,
            c = e.iterationCount,
            u = e._currentIteration,
            d = e._loopDelay,
            h = e._reversed,
            m = e._alternate,
            p = e._hasChildren,
            _ = e._delay,
            y = e._currentTime,
            v = _ + a,
            b = t - _,
            N = re(y, -_, o),
            B = re(b, -_, o),
            w = b - y,
            V = B > 0,
            A = B >= o,
            K = o <= E,
            ee = n === fe.FORCE;
        let pe = 0,
            G = b,
            me = 0;
        if (c > 1) {
            const te = ~~(B / (a + (A ? 0 : d)));
            (e._currentIteration = re(te, 0, c)),
                A && e._currentIteration--,
                (pe = e._currentIteration % 2),
                (G = B % (a + d) || 0);
        }
        const M = h ^ (m && pe),
            W = e._ease;
        let ae = A ? (M ? 0 : o) : M ? a - G : G;
        W && (ae = a * W(ae / a) || 0);
        const ce = (i ? i.backwards : b < y) ? !M : !!M;
        if (
            ((e._currentTime = b),
            (e._iterationTime = ae),
            (e.backwards = ce),
            V && !e.began ? ((e.began = !0), !s && !(i && (ce || !i.began)) && e.onBegin(e)) : b <= 0 && (e.began = !1),
            !s && !p && V && e._currentIteration !== u && e.onLoop(e),
            ee ||
                (n === fe.AUTO && ((t >= _ && t <= v) || (t <= _ && N > _) || (t >= v && N !== o))) ||
                (ae >= v && N !== o) ||
                (ae <= _ && N > 0) ||
                (t <= N && N === o && l) ||
                (A && !l && K))
        ) {
            if ((V && (e.computeDeltaTime(N), s || e.onBeforeUpdate(e)), !p)) {
                const te = ee || (ce ? w * -1 : w) >= O.tickThreshold,
                    x = e._offset + (i ? i._offset : 0) + _ + ae;
                let f = e._head,
                    k,
                    _e,
                    Pe,
                    Z,
                    $ = 0;
                for (; f; ) {
                    const q = f._composition,
                        X = f._currentTime,
                        tt = f._changeDuration,
                        Me = f._absoluteStartTime + f._changeDuration,
                        le = f._nextRep,
                        Ce = f._prevRep,
                        Se = q !== oe.none;
                    if (
                        (te ||
                            ((X !== tt || x <= Me + (le ? le._delay : 0)) && (X !== 0 || x >= f._absoluteStartTime))) &&
                        (!Se ||
                            (!f._isOverridden &&
                                (!f._isOverlapped || x <= Me) &&
                                (!le || le._isOverridden || x <= le._absoluteStartTime) &&
                                (!Ce ||
                                    Ce._isOverridden ||
                                    x >= Ce._absoluteStartTime + Ce._changeDuration + f._delay)))
                    ) {
                        const Te = (f._currentTime = re(ae - f._startTime, 0, tt)),
                            U = f._ease(Te / f._updateDuration),
                            se = f._modifier,
                            ne = f._valueType,
                            z = f._tweenType,
                            Ve = z === L.OBJECT,
                            Ee = ne === C.NUMBER,
                            $e = (Ee && Ve) || U === 0 || U === 1 ? -1 : O.precision;
                        let ue, ke;
                        if (Ee) ue = ke = se(D(Fe(f._fromNumber, f._toNumber, U), $e));
                        else if (ne === C.UNIT)
                            (ke = se(D(Fe(f._fromNumber, f._toNumber, U), $e))), (ue = `${ke}${f._unit}`);
                        else if (ne === C.COLOR) {
                            const I = f._fromNumbers,
                                ge = f._toNumbers,
                                ye = D(re(se(Fe(I[0], ge[0], U)), 0, 255), 0),
                                Ue = D(re(se(Fe(I[1], ge[1], U)), 0, 255), 0),
                                qe = D(re(se(Fe(I[2], ge[2], U)), 0, 255), 0),
                                st = re(se(D(Fe(I[3], ge[3], U), $e)), 0, 1);
                            if (((ue = `rgba(${ye},${Ue},${qe},${st})`), Se)) {
                                const we = f._numbers;
                                (we[0] = ye), (we[1] = Ue), (we[2] = qe), (we[3] = st);
                            }
                        } else if (ne === C.COMPLEX) {
                            ue = f._strings[0];
                            for (let I = 0, ge = f._toNumbers.length; I < ge; I++) {
                                const ye = se(D(Fe(f._fromNumbers[I], f._toNumbers[I], U), $e)),
                                    Ue = f._strings[I + 1];
                                (ue += `${Ue ? ye + Ue : ye}`), Se && (f._numbers[I] = ye);
                            }
                        }
                        if ((Se && (f._number = ke), !r && q !== oe.blend)) {
                            const I = f.property;
                            (k = f.target),
                                Ve
                                    ? (k[I] = ue)
                                    : z === L.ATTRIBUTE
                                      ? k.setAttribute(I, ue)
                                      : ((_e = k.style),
                                        z === L.TRANSFORM
                                            ? (k !== Pe && ((Pe = k), (Z = k[St])), (Z[I] = ue), ($ = 1))
                                            : z === L.CSS
                                              ? (_e[I] = ue)
                                              : z === L.CSS_VAR && _e.setProperty(I, ue)),
                                V && (me = 1);
                        } else f._value = ue;
                    }
                    if ($ && f._renderTransforms) {
                        let Te = Ae;
                        for (let U in Z) Te += `${ps[U]}${Z[U]}) `;
                        (_e.transform = Te), ($ = 0);
                    }
                    f = f._next;
                }
                !s && me && e.onRender(e);
            }
            !s && V && e.onUpdate(e);
        }
        return (
            i && K
                ? !s &&
                  ((i.began && !ce && b > 0 && !l) || (ce && b <= E && l)) &&
                  (e.onComplete(e), (e.completed = !ce))
                : V && A
                  ? c === 1 / 0
                      ? (e._startTime += e.duration)
                      : e._currentIteration >= c - 1 &&
                        ((e.paused = !0),
                        !l &&
                            !p &&
                            ((e.completed = !0), !s && !(i && (ce || !i.began)) && (e.onComplete(e), e._resolve(e))))
                  : (e.completed = !1),
            me
        );
    },
    Je = (e, t, s, r, n) => {
        const i = e._currentIteration;
        if ((yt(e, t, s, r, n), e._hasChildren)) {
            const o = e,
                l = o.backwards,
                a = r ? t : o._iterationTime,
                c = et();
            let u = 0,
                d = !0;
            if (!r && o._currentIteration !== i) {
                const h = o.iterationDuration;
                F(o, (m) => {
                    if (!l)
                        !m.completed &&
                            !m.backwards &&
                            m._currentTime < m.iterationDuration &&
                            yt(m, h, s, 1, fe.FORCE),
                            (m.began = !1),
                            (m.completed = !1);
                    else {
                        const p = m.duration,
                            _ = m._offset + m._delay,
                            y = _ + p;
                        !s && p <= E && (!_ || y === h) && m.onComplete(m);
                    }
                }),
                    s || o.onLoop(o);
            }
            F(
                o,
                (h) => {
                    const m = D((a - h._offset) * h._speed, 12),
                        p = h._fps < o._fps ? h.requestTick(c) : n;
                    (u += yt(h, m, s, r, p)), !h.completed && d && (d = !1);
                },
                l
            ),
                !s && u && o.onRender(o),
                (d || l) &&
                    o._currentTime >= o.duration &&
                    ((o.paused = !0), o.completed || ((o.completed = !0), s || (o.onComplete(o), o._resolve(o))));
        }
    };
const rs = {},
    cn = (e, t, s) => {
        if (s === L.TRANSFORM) {
            const r = ds.get(e);
            return r || e;
        } else if (s === L.CSS || (s === L.ATTRIBUTE && ys(t) && e in t.style)) {
            const r = rs[e];
            if (r) return r;
            {
                const n = e && gs(e);
                return (rs[e] = n), n;
            }
        } else return e;
    },
    xs = (e) => {
        if (e._hasChildren) F(e, xs, !0);
        else {
            const t = e;
            t.pause(),
                F(t, (s) => {
                    const r = s.property,
                        n = s.target;
                    if (n[Wt]) {
                        const i = n.style,
                            o = s._inlineValue,
                            l = Ge(o) || o === Ae;
                        if (s._tweenType === L.TRANSFORM) {
                            const a = n[St];
                            if ((l ? delete a[r] : (a[r] = o), s._renderTransforms))
                                if (!Object.keys(a).length) i.removeProperty("transform");
                                else {
                                    let c = Ae;
                                    for (let u in a) c += ps[u] + a[u] + ") ";
                                    i.transform = c;
                                }
                        } else l ? i.removeProperty(gs(r)) : (i[r] = o);
                        t._tail === s &&
                            t.targets.forEach((a) => {
                                a.getAttribute && a.getAttribute("style") === Ae && a.removeAttribute("style");
                            });
                    }
                });
        }
        return e;
    };
class Es {
    constructor(t = 0) {
        (this.deltaTime = 0),
            (this._currentTime = t),
            (this._elapsedTime = t),
            (this._startTime = t),
            (this._lastTime = t),
            (this._scheduledTime = 0),
            (this._frameDuration = D(je / Ut, 0)),
            (this._fps = Ut),
            (this._speed = 1),
            (this._hasChildren = !1),
            (this._head = null),
            (this._tail = null);
    }
    get fps() {
        return this._fps;
    }
    set fps(t) {
        const s = this._frameDuration,
            r = +t,
            n = r < E ? E : r,
            i = D(je / n, 0);
        (this._fps = n), (this._frameDuration = i), (this._scheduledTime += i - s);
    }
    get speed() {
        return this._speed;
    }
    set speed(t) {
        const s = +t;
        this._speed = s < E ? E : s;
    }
    requestTick(t) {
        const s = this._scheduledTime,
            r = this._elapsedTime;
        if (((this._elapsedTime += t - r), r < s)) return fe.NONE;
        const n = this._frameDuration,
            i = r - s;
        return (this._scheduledTime += i < n ? n : i), fe.AUTO;
    }
    computeDeltaTime(t) {
        const s = t - this._lastTime;
        return (this.deltaTime = s), (this._lastTime = t), s;
    }
}
const Ze = { animation: null, update: ie },
    ln = (e) => {
        let t = Ze.animation;
        return (
            t ||
                ((t = { duration: E, computeDeltaTime: ie, _offset: 0, _delay: 0, _head: null, _tail: null }),
                (Ze.animation = t),
                (Ze.update = () => {
                    e.forEach((s) => {
                        for (let r in s) {
                            const n = s[r],
                                i = n._head;
                            if (i) {
                                const o = i._valueType,
                                    l = o === C.COMPLEX || o === C.COLOR ? j(i._fromNumbers) : null;
                                let a = i._fromNumber,
                                    c = n._tail;
                                for (; c && c !== i; ) {
                                    if (l) for (let u = 0, d = c._numbers.length; u < d; u++) l[u] += c._numbers[u];
                                    else a += c._number;
                                    c = c._prevAdd;
                                }
                                (i._toNumber = a), (i._toNumbers = l);
                            }
                        }
                    }),
                        yt(t, 1, 1, 0, fe.FORCE);
                })),
            t
        );
    };
const Rs = xe ? requestAnimationFrame : setImmediate,
    un = xe ? cancelAnimationFrame : clearImmediate;
class hn extends Es {
    constructor(t) {
        super(t),
            (this.useDefaultMainLoop = !0),
            (this.pauseOnDocumentHidden = !0),
            (this.defaults = _s),
            (this.paused = !0),
            (this.reqId = 0);
    }
    update() {
        const t = (this._currentTime = et());
        if (this.requestTick(t)) {
            this.computeDeltaTime(t);
            const s = this._speed,
                r = this._fps;
            let n = this._head;
            for (; n; ) {
                const i = n._next;
                n.paused
                    ? (it(this, n),
                      (this._hasChildren = !!this._tail),
                      (n._running = !1),
                      n.completed && !n._cancelled && n.cancel())
                    : Je(n, (t - n._startTime) * n._speed * s, 0, 0, n._fps < r ? n.requestTick(t) : fe.AUTO),
                    (n = i);
            }
            Ze.update();
        }
    }
    wake() {
        return this.useDefaultMainLoop && !this.reqId && (this.requestTick(et()), (this.reqId = Rs(Ds))), this;
    }
    pause() {
        if (this.reqId) return (this.paused = !0), dn();
    }
    resume() {
        if (this.paused) return (this.paused = !1), F(this, (t) => t.resetTime()), this.wake();
    }
    get speed() {
        return this._speed * (O.timeScale === 1 ? 1 : je);
    }
    set speed(t) {
        (this._speed = t * O.timeScale), F(this, (s) => (s.speed = s._speed));
    }
    get timeUnit() {
        return O.timeScale === 1 ? "ms" : "s";
    }
    set timeUnit(t) {
        const r = t === "s",
            n = r ? 0.001 : 1;
        if (O.timeScale !== n) {
            (O.timeScale = n), (O.tickThreshold = 200 * n);
            const i = r ? 0.001 : je;
            (this.defaults.duration *= i), (this._speed *= i);
        }
    }
    get precision() {
        return O.precision;
    }
    set precision(t) {
        O.precision = t;
    }
}
const Q = (() => {
        const e = new hn(et());
        return (
            xe &&
                ((Ts.engine = e),
                H.addEventListener("visibilitychange", () => {
                    e.pauseOnDocumentHidden && (H.hidden ? e.pause() : e.resume());
                })),
            e
        );
    })(),
    Ds = () => {
        Q._head ? ((Q.reqId = Rs(Ds)), Q.update()) : (Q.reqId = 0);
    },
    dn = () => (un(Q.reqId), (Q.reqId = 0), Q);
const bt = { _rep: new WeakMap(), _add: new Map() },
    Qt = (e, t, s = "_rep") => {
        const r = bt[s];
        let n = r.get(e);
        return n || ((n = {}), r.set(e, n)), n[t] ? n[t] : (n[t] = { _head: null, _tail: null });
    },
    fn = (e, t) => e._isOverridden || e._absoluteStartTime > t._absoluteStartTime,
    vt = (e) => {
        (e._isOverlapped = 1), (e._isOverridden = 1), (e._changeDuration = E), (e._currentTime = E);
    },
    Os = (e, t) => {
        const s = e._composition;
        if (s === oe.replace) {
            const r = e._absoluteStartTime;
            Qe(t, e, fn, "_prevRep", "_nextRep");
            const n = e._prevRep;
            if (n) {
                const i = n.parent,
                    o = n._absoluteStartTime + n._changeDuration;
                if (e.parent.id !== i.id && i.iterationCount > 1 && o + (i.duration - i.iterationDuration) > r) {
                    vt(n);
                    let c = n._prevRep;
                    for (; c && c.parent.id === i.id; ) vt(c), (c = c._prevRep);
                }
                const l = r - e._delay;
                if (o > l) {
                    const c = n._startTime,
                        u = o - (c + n._updateDuration),
                        d = D(l - u - c, 12);
                    (n._changeDuration = d), (n._currentTime = d), (n._isOverlapped = 1), d < E && vt(n);
                }
                let a = !0;
                if (
                    (F(i, (c) => {
                        c._isOverlapped || (a = !1);
                    }),
                    a)
                ) {
                    const c = i.parent;
                    if (c) {
                        let u = !0;
                        F(c, (d) => {
                            d !== i &&
                                F(d, (h) => {
                                    h._isOverlapped || (u = !1);
                                });
                        }),
                            u && c.cancel();
                    } else i.cancel();
                }
            }
        } else if (s === oe.blend) {
            const r = Qt(e.target, e.property, "_add"),
                n = ln(bt._add);
            let i = r._head;
            i ||
                ((i = { ...e }),
                (i._composition = oe.replace),
                (i._updateDuration = E),
                (i._startTime = 0),
                (i._numbers = j(e._fromNumbers)),
                (i._number = 0),
                (i._next = null),
                (i._prev = null),
                Qe(r, i),
                Qe(n, i));
            const o = e._toNumber;
            if (
                ((e._fromNumber = i._fromNumber - o),
                (e._toNumber = 0),
                (e._numbers = j(e._fromNumbers)),
                (e._number = 0),
                (i._fromNumber = o),
                e._toNumbers)
            ) {
                const l = j(e._toNumbers);
                l &&
                    l.forEach((a, c) => {
                        (e._fromNumbers[c] = i._fromNumbers[c] - a), (e._toNumbers[c] = 0);
                    }),
                    (i._fromNumbers = l);
            }
            Qe(r, e, null, "_prevAdd", "_nextAdd");
        }
        return e;
    },
    pn = (e) => {
        const t = e._composition;
        if (t !== oe.none) {
            const s = e.target,
                r = e.property,
                o = bt._rep.get(s)[r];
            if ((it(o, e, "_prevRep", "_nextRep"), t === oe.blend)) {
                const l = bt._add,
                    a = l.get(s);
                if (!a) return;
                const c = a[r],
                    u = Ze.animation;
                it(c, e, "_prevAdd", "_nextAdd");
                const d = c._head;
                if (d && d === c._tail) {
                    it(c, d, "_prevAdd", "_nextAdd"), it(u, d);
                    let h = !0;
                    for (let m in a)
                        if (a[m]._head) {
                            h = !1;
                            break;
                        }
                    h && l.delete(s);
                }
            }
        }
        return e;
    };
const is = (e) => ((e.paused = !0), (e.began = !1), (e.completed = !1), e),
    Bt = (e) => (
        e._cancelled &&
            (e._hasChildren
                ? F(e, Bt)
                : F(e, (t) => {
                      t._composition !== oe.none && Os(t, Qt(t.target, t.property));
                  }),
            (e._cancelled = 0)),
        e
    );
let mn = 0;
class As extends Es {
    constructor(t = {}, s = null, r = 0) {
        super(0);
        const {
            id: n,
            delay: i,
            duration: o,
            reversed: l,
            alternate: a,
            loop: c,
            loopDelay: u,
            autoplay: d,
            frameRate: h,
            playbackRate: m,
            onComplete: p,
            onLoop: _,
            onPause: y,
            onBegin: v,
            onBeforeUpdate: b,
            onUpdate: N,
        } = t;
        he.current && he.current.register(this);
        const B = s ? 0 : Q._elapsedTime,
            w = s ? s.defaults : O.defaults,
            V = Y(i) || S(i) ? w.delay : +i,
            A = Y(o) || S(o) ? 1 / 0 : +o,
            K = P(c, w.loop),
            ee = P(u, w.loopDelay),
            pe = K === !0 || K === 1 / 0 || K < 0 ? 1 / 0 : K + 1;
        let G = 0;
        s ? (G = r) : (Q.reqId || Q.requestTick(et()), (G = (Q._elapsedTime - Q._startTime) * O.timeScale)),
            (this.id = S(n) ? ++mn : n),
            (this.parent = s),
            (this.duration = zt((A + ee) * pe - ee) || E),
            (this.backwards = !1),
            (this.paused = !0),
            (this.began = !1),
            (this.completed = !1),
            (this.onBegin = v || w.onBegin),
            (this.onBeforeUpdate = b || w.onBeforeUpdate),
            (this.onUpdate = N || w.onUpdate),
            (this.onLoop = _ || w.onLoop),
            (this.onPause = y || w.onPause),
            (this.onComplete = p || w.onComplete),
            (this.iterationDuration = A),
            (this.iterationCount = pe),
            (this._autoplay = s ? !1 : P(d, w.autoplay)),
            (this._offset = G),
            (this._delay = V),
            (this._loopDelay = ee),
            (this._iterationTime = 0),
            (this._currentIteration = 0),
            (this._resolve = ie),
            (this._running = !1),
            (this._reversed = +P(l, w.reversed)),
            (this._reverse = this._reversed),
            (this._cancelled = 0),
            (this._alternate = P(a, w.alternate)),
            (this._prev = null),
            (this._next = null),
            (this._elapsedTime = B),
            (this._startTime = B),
            (this._lastTime = B),
            (this._fps = P(h, w.frameRate)),
            (this._speed = P(m, w.playbackRate));
    }
    get cancelled() {
        return !!this._cancelled;
    }
    set cancelled(t) {
        t ? this.cancel() : this.reset(!0).play();
    }
    get currentTime() {
        return re(D(this._currentTime, O.precision), -this._delay, this.duration);
    }
    set currentTime(t) {
        const s = this.paused;
        this.pause().seek(+t), s || this.resume();
    }
    get iterationCurrentTime() {
        return D(this._iterationTime, O.precision);
    }
    set iterationCurrentTime(t) {
        this.currentTime = this.iterationDuration * this._currentIteration + t;
    }
    get progress() {
        return re(D(this._currentTime / this.duration, 10), 0, 1);
    }
    set progress(t) {
        this.currentTime = this.duration * t;
    }
    get iterationProgress() {
        return re(D(this._iterationTime / this.iterationDuration, 10), 0, 1);
    }
    set iterationProgress(t) {
        const s = this.iterationDuration;
        this.currentTime = s * this._currentIteration + s * t;
    }
    get currentIteration() {
        return this._currentIteration;
    }
    set currentIteration(t) {
        this.currentTime = this.iterationDuration * re(+t, 0, this.iterationCount - 1);
    }
    get reversed() {
        return !!this._reversed;
    }
    set reversed(t) {
        t ? this.reverse() : this.play();
    }
    get speed() {
        return super.speed;
    }
    set speed(t) {
        (super.speed = t), this.resetTime();
    }
    reset(t = !1) {
        return (
            Bt(this),
            this._reversed && !this._reverse && (this.reversed = !1),
            (this._iterationTime = this.iterationDuration),
            Je(this, 0, 1, ~~t, fe.FORCE),
            is(this),
            this._hasChildren && F(this, is),
            this
        );
    }
    init(t = !1) {
        (this.fps = this._fps),
            (this.speed = this._speed),
            !t && this._hasChildren && Je(this, this.duration, 1, ~~t, fe.FORCE),
            this.reset(t);
        const s = this._autoplay;
        return s === !0 ? this.resume() : s && !S(s.linked) && s.link(this), this;
    }
    resetTime() {
        const t = 1 / (this._speed * Q._speed);
        return (this._startTime = et() - (this._currentTime + this._delay) * t), this;
    }
    pause() {
        return this.paused ? this : ((this.paused = !0), this.onPause(this), this);
    }
    resume() {
        return this.paused
            ? ((this.paused = !1),
              this.duration <= E && !this._hasChildren
                  ? Je(this, E, 0, 0, fe.FORCE)
                  : (this._running || (Qe(Q, this), (Q._hasChildren = !0), (this._running = !0)),
                    this.resetTime(),
                    (this._startTime -= 12),
                    Q.wake()),
              this)
            : this;
    }
    restart() {
        return this.reset().resume();
    }
    seek(t, s = 0, r = 0) {
        Bt(this), (this.completed = !1);
        const n = this.paused;
        return (this.paused = !0), Je(this, t + this._delay, ~~s, ~~r, fe.AUTO), n ? this : this.resume();
    }
    alternate() {
        const t = this._reversed,
            s = this.iterationCount,
            r = this.iterationDuration,
            n = s === 1 / 0 ? Ft($t / r) : s;
        return (
            (this._reversed = +(this._alternate && !(n % 2) ? t : !t)),
            s === 1 / 0
                ? (this.iterationProgress = this._reversed ? 1 - this.iterationProgress : this.iterationProgress)
                : this.seek(r * n - this._currentTime),
            this.resetTime(),
            this
        );
    }
    play() {
        return this._reversed && this.alternate(), this.resume();
    }
    reverse() {
        return this._reversed || this.alternate(), this.resume();
    }
    cancel() {
        return this._hasChildren ? F(this, (t) => t.cancel(), !0) : F(this, pn), (this._cancelled = 1), this.pause();
    }
    stretch(t) {
        const s = this.duration,
            r = at(t);
        if (s === r) return this;
        const n = t / s,
            i = t <= E;
        return (
            (this.duration = i ? E : r),
            (this.iterationDuration = i ? E : at(this.iterationDuration * n)),
            (this._offset *= n),
            (this._delay *= n),
            (this._loopDelay *= n),
            this
        );
    }
    revert() {
        Je(this, 0, 1, 0, fe.AUTO);
        const t = this._autoplay;
        return t && t.linked && t.linked === this && t.revert(), this.cancel();
    }
    complete() {
        return this.seek(this.duration).cancel();
    }
    then(t = ie) {
        const s = this.then,
            r = () => {
                (this.then = null), t(this), (this.then = s), (this._resolve = ie);
            };
        return new Promise((n) => ((this._resolve = () => n(r())), this.completed && this._resolve(), this));
    }
}
function Vt(e) {
    const t = Be(e) ? he.root.querySelectorAll(e) : e;
    if (t instanceof NodeList || t instanceof HTMLCollection) return t;
}
function Is(e) {
    if (Ge(e)) return [];
    if (!xe) return (Ie(e) && e.flat(1 / 0)) || [e];
    if (Ie(e)) {
        const s = e.flat(1 / 0),
            r = [];
        for (let n = 0, i = s.length; n < i; n++) {
            const o = s[n];
            if (!Ge(o)) {
                const l = Vt(o);
                if (l)
                    for (let a = 0, c = l.length; a < c; a++) {
                        const u = l[a];
                        if (!Ge(u)) {
                            let d = !1;
                            for (let h = 0, m = r.length; h < m; h++)
                                if (r[h] === u) {
                                    d = !0;
                                    break;
                                }
                            d || r.push(u);
                        }
                    }
                else {
                    let a = !1;
                    for (let c = 0, u = r.length; c < u; c++)
                        if (r[c] === o) {
                            a = !0;
                            break;
                        }
                    a || r.push(o);
                }
            }
        }
        return r;
    }
    const t = Vt(e);
    return t ? Array.from(t) : [e];
}
function Ls(e) {
    const t = Is(e),
        s = t.length;
    if (s)
        for (let r = 0; r < s; r++) {
            const n = t[r];
            if (!n[Gt]) {
                n[Gt] = !0;
                const i = ys(n);
                (n.nodeType || i) && ((n[Wt] = !0), (n[hs] = i), (n[St] = {}));
            }
        }
    return t;
}
const Dt = { deg: 1, rad: 180 / Xt, turn: 360 },
    os = {},
    _n = (e, t, s, r = !1) => {
        const n = t.u,
            i = t.n;
        if (t.t === C.UNIT && n === s) return t;
        const o = i + n + s,
            l = os[o];
        if (!S(l) && !r) t.n = l;
        else {
            let a;
            if (n in Dt) a = (i * Dt[n]) / Dt[s];
            else {
                const u = e.cloneNode(),
                    d = e.parentNode,
                    h = d && d !== H ? d : H.body;
                h.appendChild(u);
                const m = u.style;
                m.width = 100 + n;
                const p = u.offsetWidth || 100;
                m.width = 100 + s;
                const _ = u.offsetWidth || 100,
                    y = p / _;
                h.removeChild(u), (a = y * i);
            }
            (t.n = a), (os[o] = a);
        }
        return t.t, C.UNIT, (t.u = s), t;
    };
const Le = (e) => e;
const nt =
        (e = 1.68) =>
        (t) =>
            Xe(t, +e),
    kt = {
        in: (e) => (t) => e(t),
        out: (e) => (t) => 1 - e(1 - t),
        inOut: (e) => (t) => (t < 0.5 ? e(t * 2) / 2 : 1 - e(t * -2 + 2) / 2),
        outIn: (e) => (t) => (t < 0.5 ? (1 - e(1 - t * 2)) / 2 : (e(t * 2 - 1) + 1) / 2),
    },
    Tn = Xt / 2,
    as = Xt * 2,
    cs = {
        [Ae]: nt,
        Quad: nt(2),
        Cubic: nt(3),
        Quart: nt(4),
        Quint: nt(5),
        Sine: (e) => 1 - js(e * Tn),
        Circ: (e) => 1 - Ss(1 - e * e),
        Expo: (e) => (e ? Xe(2, 10 * e - 10) : 0),
        Bounce: (e) => {
            let t,
                s = 4;
            for (; e < ((t = Xe(2, --s)) - 1) / 11; );
            return 1 / Xe(4, 3 - s) - 7.5625 * Xe((t * 3 - 2) / 22 - e, 2);
        },
        Back:
            (e = 1.7) =>
            (t) =>
                (+e + 1) * t * t * t - +e * t * t,
        Elastic: (e = 1, t = 0.3) => {
            const s = re(+e, 1, 10),
                r = re(+t, E, 2),
                n = (r / as) * en(1 / s),
                i = as / r;
            return (o) => (o === 0 || o === 1 ? o : -s * Xe(2, -10 * (1 - o)) * Zs((1 - o - n) * i));
        },
    },
    Ot = (() => {
        const e = { linear: Le, none: Le };
        for (let t in kt)
            for (let s in cs) {
                const r = cs[s],
                    n = kt[t];
                e[t + s] = s === Ae || s === "Back" || s === "Elastic" ? (i, o) => n(r(i, o)) : n(r);
            }
        return e;
    })(),
    ut = { linear: Le, none: Le },
    gn = (e) => {
        if (ut[e]) return ut[e];
        if (e.indexOf("(") <= -1) {
            const s = kt[e] || e.includes("Back") || e.includes("Elastic") ? Ot[e]() : Ot[e];
            return s ? (ut[e] = s) : Le;
        } else {
            const t = e.slice(0, -1).split("("),
                s = Ot[t[0]];
            return s ? (ut[e] = s(...t[1].split(","))) : Le;
        }
    },
    ls = ["steps(", "irregular(", "linear(", "cubicBezier("],
    qt = (e) => {
        if (Be(e)) {
            for (let s = 0, r = ls.length; s < r; s++)
                if (Ne(e, ls[s]))
                    return (
                        console.warn(
                            `String syntax for \`ease: "${e}"\` has been removed from the core and replaced by importing and passing the easing function directly: \`ease: ${e}\``
                        ),
                        Le
                    );
        }
        return Y(e) ? e : Be(e) ? gn(e) : Le;
    };
const T = Jt(),
    g = Jt(),
    He = {},
    ht = { func: null },
    dt = [null],
    We = [null, null],
    ft = { to: null };
let yn = 0,
    Oe,
    be;
const vn = (e, t) => {
    const s = {};
    if (Ie(e)) {
        const r = [].concat(...e.map((n) => Object.keys(n))).filter(Tt);
        for (let n = 0, i = r.length; n < i; n++) {
            const o = r[n],
                l = e.map((a) => {
                    const c = {};
                    for (let u in a) {
                        const d = a[u];
                        Tt(u) ? u === o && (c.to = d) : (c[u] = d);
                    }
                    return c;
                });
            s[o] = l;
        }
    } else {
        const r = P(t.duration, O.defaults.duration);
        Object.keys(e)
            .map((i) => ({ o: parseFloat(i) / 100, p: e[i] }))
            .sort((i, o) => i.o - o.o)
            .forEach((i) => {
                const o = i.o,
                    l = i.p;
                for (let a in l)
                    if (Tt(a)) {
                        let c = s[a];
                        c || (c = s[a] = []);
                        const u = o * r;
                        let d = c.length,
                            h = c[d - 1];
                        const m = { to: l[a] };
                        let p = 0;
                        for (let _ = 0; _ < d; _++) p += c[_].duration;
                        d === 1 && (m.from = h.to),
                            l.ease && (m.ease = l.ease),
                            (m.duration = u - (d ? p : 0)),
                            c.push(m);
                    }
                return i;
            });
        for (let i in s) {
            const o = s[i];
            let l;
            for (let a = 0, c = o.length; a < c; a++) {
                const u = o[a],
                    d = u.ease;
                (u.ease = l || void 0), (l = d);
            }
            o[0].duration || o.shift();
        }
    }
    return s;
};
class bn extends As {
    constructor(t, s, r, n, i = !1, o = 0, l = 0) {
        super(s, r, n);
        const a = Ls(t),
            c = a.length,
            u = s.keyframes,
            d = u ? ws(vn(u, s), s) : s,
            { delay: h, duration: m, ease: p, playbackEase: _, modifier: y, composition: v, onRender: b } = d,
            N = r ? r.defaults : O.defaults,
            B = P(_, N.playbackEase),
            w = B ? qt(B) : null,
            V = !S(p) && !S(p.ease),
            A = V ? p.ease : P(p, w ? "linear" : N.ease),
            K = V ? p.settlingDuration : P(m, N.duration),
            ee = P(h, N.delay),
            pe = y || N.modifier,
            G = S(v) && c >= je ? oe.none : S(v) ? N.composition : v,
            me = this._offset + (r ? r._offset : 0);
        V && (p.parent = this);
        let M = NaN,
            W = NaN,
            ae = 0,
            ce = 0;
        for (let te = 0; te < c; te++) {
            const x = a[te],
                f = o || te,
                k = l || c;
            let _e = NaN,
                Pe = NaN;
            for (let Z in d)
                if (Tt(Z)) {
                    const $ = Ns(x, Z),
                        q = cn(Z, x, $);
                    let X = d[Z];
                    const tt = Ie(X);
                    if ((i && !tt && ((We[0] = X), (We[1] = X), (X = We)), tt)) {
                        const U = X.length,
                            se = !Ye(X[0]);
                        U === 2 && se
                            ? ((ft.to = X), (dt[0] = ft), (Oe = dt))
                            : U > 2 && se
                              ? ((Oe = []),
                                X.forEach((ne, z) => {
                                    z ? (z === 1 ? ((We[1] = ne), Oe.push(We)) : Oe.push(ne)) : (We[0] = ne);
                                }))
                              : (Oe = X);
                    } else (dt[0] = X), (Oe = dt);
                    let Me = null,
                        le = null,
                        Ce = NaN,
                        Se = 0,
                        Te = 0;
                    for (let U = Oe.length; Te < U; Te++) {
                        const se = Oe[Te];
                        Ye(se) ? (be = se) : ((ft.to = se), (be = ft)), (ht.func = null);
                        const ne = Re(be.to, x, f, k, ht);
                        let z;
                        Ye(ne) && !S(ne.to) ? ((be = ne), (z = ne.to)) : (z = ne);
                        const Ve = Re(be.from, x, f, k),
                            Ee = be.ease,
                            $e = !S(Ee) && !S(Ee.ease),
                            ue = $e ? Ee.ease : Ee || A,
                            ke = $e ? Ee.settlingDuration : Re(P(be.duration, U > 1 ? Re(K, x, f, k) / U : K), x, f, k),
                            I = Re(P(be.delay, Te ? 0 : ee), x, f, k),
                            ge = Re(P(be.composition, G), x, f, k),
                            ye = Ke(ge) ? ge : oe[ge],
                            Ue = be.modifier || pe,
                            qe = !S(Ve),
                            st = !S(z),
                            we = Ie(z),
                            Us = we || (qe && st),
                            wt = le ? Se + I : I,
                            Nt = D(me + wt, 12);
                        !ce && (qe || we) && (ce = 1);
                        let de = le;
                        if (ye !== oe.none) {
                            Me || (Me = Qt(x, q));
                            let R = Me._head;
                            for (; R && !R._isOverridden && R._absoluteStartTime <= Nt; )
                                if (((de = R), (R = R._nextRep), R && R._absoluteStartTime >= Nt))
                                    for (; R; ) vt(R), (R = R._nextRep);
                        }
                        if (
                            (Us
                                ? (ve(we ? Re(z[0], x, f, k) : Ve, T),
                                  ve(we ? Re(z[1], x, f, k, ht) : z, g),
                                  T.t === C.NUMBER &&
                                      (de
                                          ? de._valueType === C.UNIT && ((T.t = C.UNIT), (T.u = de._unit))
                                          : (ve(ze(x, q, $, He), De),
                                            De.t === C.UNIT && ((T.t = C.UNIT), (T.u = De.u)))))
                                : (st
                                      ? ve(z, g)
                                      : le
                                        ? ns(le, g)
                                        : ve(r && de && de.parent.parent === r ? de._value : ze(x, q, $, He), g),
                                  qe
                                      ? ve(Ve, T)
                                      : le
                                        ? ns(le, T)
                                        : ve(r && de && de.parent.parent === r ? de._value : ze(x, q, $, He), T)),
                            T.o && (T.n = gt(de ? de._toNumber : ve(ze(x, q, $, He), De).n, T.n, T.o)),
                            g.o && (g.n = gt(T.n, g.n, g.o)),
                            T.t !== g.t)
                        ) {
                            if (T.t === C.COMPLEX || g.t === C.COMPLEX) {
                                const R = T.t === C.COMPLEX ? T : g,
                                    J = T.t === C.COMPLEX ? g : T;
                                (J.t = C.COMPLEX), (J.s = j(R.s)), (J.d = R.d.map(() => J.n));
                            } else if (T.t === C.UNIT || g.t === C.UNIT) {
                                const R = T.t === C.UNIT ? T : g,
                                    J = T.t === C.UNIT ? g : T;
                                (J.t = C.UNIT), (J.u = R.u);
                            } else if (T.t === C.COLOR || g.t === C.COLOR) {
                                const R = T.t === C.COLOR ? T : g,
                                    J = T.t === C.COLOR ? g : T;
                                (J.t = C.COLOR), (J.s = R.s), (J.d = [0, 0, 0, 1]);
                            }
                        }
                        if (T.u !== g.u) {
                            let R = g.u ? T : g;
                            R = _n(x, R, g.u ? g.u : T.u, !1);
                        }
                        if (g.d && T.d && g.d.length !== T.d.length) {
                            const R = T.d.length > g.d.length ? T : g,
                                J = R === T ? g : T;
                            (J.d = R.d.map((Ln, Kt) => (S(J.d[Kt]) ? 0 : J.d[Kt]))), (J.s = j(R.s));
                        }
                        const xt = D(+ke || E, 12);
                        let Yt = He[q];
                        Ge(Yt) || (He[q] = null);
                        const lt = {
                            parent: this,
                            id: yn++,
                            property: q,
                            target: x,
                            _value: null,
                            _func: ht.func,
                            _ease: qt(ue),
                            _fromNumbers: j(T.d),
                            _toNumbers: j(g.d),
                            _strings: j(g.s),
                            _fromNumber: T.n,
                            _toNumber: g.n,
                            _numbers: j(T.d),
                            _number: T.n,
                            _unit: g.u,
                            _modifier: Ue,
                            _currentTime: 0,
                            _startTime: wt,
                            _delay: +I,
                            _updateDuration: xt,
                            _changeDuration: xt,
                            _absoluteStartTime: Nt,
                            _tweenType: $,
                            _valueType: g.t,
                            _composition: ye,
                            _isOverlapped: 0,
                            _isOverridden: 0,
                            _renderTransforms: 0,
                            _inlineValue: Yt,
                            _prevRep: null,
                            _nextRep: null,
                            _prevAdd: null,
                            _nextAdd: null,
                            _prev: null,
                            _next: null,
                        };
                        ye !== oe.none && Os(lt, Me),
                            isNaN(Ce) && (Ce = lt._startTime),
                            (Se = D(wt + xt, 12)),
                            (le = lt),
                            ae++,
                            Qe(this, lt);
                    }
                    (isNaN(W) || Ce < W) && (W = Ce),
                        (isNaN(M) || Se > M) && (M = Se),
                        $ === L.TRANSFORM && ((_e = ae - Te), (Pe = ae));
                }
            if (!isNaN(_e)) {
                let Z = 0;
                F(this, ($) => {
                    Z >= _e &&
                        Z < Pe &&
                        (($._renderTransforms = 1),
                        $._composition === oe.blend &&
                            F(Ze.animation, (q) => {
                                q.id === $.id && (q._renderTransforms = 1);
                            })),
                        Z++;
                });
            }
        }
        c ||
            console.warn(
                "No target found. Make sure the element you're trying to animate is accessible before creating your animation."
            ),
            W
                ? (F(this, (te) => {
                      te._startTime - te._delay || (te._delay -= W), (te._startTime -= W);
                  }),
                  (M -= W))
                : (W = 0),
            M || ((M = E), (this.iterationCount = 0)),
            (this.targets = a),
            (this.duration = M === E ? E : zt((M + this._loopDelay) * this.iterationCount - this._loopDelay) || E),
            (this.onRender = b || N.onRender),
            (this._ease = w),
            (this._delay = W),
            (this.iterationDuration = M),
            !this._autoplay && ce && this.onRender(this);
    }
    stretch(t) {
        const s = this.duration;
        if (s === at(t)) return this;
        const r = t / s;
        return (
            F(this, (n) => {
                (n._updateDuration = at(n._updateDuration * r)),
                    (n._changeDuration = at(n._changeDuration * r)),
                    (n._currentTime *= r),
                    (n._startTime *= r),
                    (n._absoluteStartTime *= r);
            }),
            super.stretch(t)
        );
    }
    refresh() {
        return (
            F(this, (t) => {
                const s = t._func;
                if (s) {
                    const r = ze(t.target, t.property, t._tweenType);
                    ve(r, De),
                        ve(s(), g),
                        (t._fromNumbers = j(De.d)),
                        (t._fromNumber = De.n),
                        (t._toNumbers = j(g.d)),
                        (t._strings = j(g.s)),
                        (t._toNumber = g.o ? gt(De.n, g.n, g.o) : g.n);
                }
            }),
            this.duration === E && this.restart(),
            this
        );
    }
    revert() {
        return super.revert(), xs(this);
    }
    then(t) {
        return super.then(t);
    }
}
const Pn = (e, t) => new bn(e, t, null, 0, !1).init();
const Cn = (e, t) => {
        if (Ne(t, "<")) {
            const s = t[1] === "<",
                r = e._tail,
                n = r ? r._offset + r._delay : 0;
            return s ? n : n + r.duration;
        }
    },
    Sn = (e, t) => {
        let s = e.iterationDuration;
        if ((s === E && (s = 0), S(t))) return s;
        if (Ke(+t)) return +t;
        const r = t,
            n = e ? e.labels : null,
            i = !Ge(n),
            o = Cn(e, r),
            l = !S(o),
            a = Js.exec(r);
        if (a) {
            const c = a[0],
                u = r.split(c),
                d = i && u[0] ? n[u[0]] : s,
                h = l ? o : i ? d : s,
                m = +u[1];
            return gt(h, m, c[0]);
        } else return l ? o : i ? (S(n[r]) ? s : n[r]) : s;
    };
const Mn = (e = ie) => new As({ duration: 1 * O.timeScale, onComplete: e }, null, 0).resume(),
    Ps = (e) => {
        let t;
        return (...s) => {
            let r, n, i, o;
            t &&
                ((r = t.currentIteration), (n = t.iterationProgress), (i = t.reversed), (o = t._alternate), t.revert());
            const l = e(...s);
            return (
                l && !Y(l) && l.revert && (t = l),
                S(n) || ((t.currentIteration = r), (t.iterationProgress = (o && r % 2 ? !i : i) ? 1 - n : n)),
                l || ie
            );
        };
    };
class wn {
    constructor(t = {}) {
        he.current && he.current.register(this);
        const s = t.root;
        let r = H;
        s && (r = s.current || s.nativeElement || Is(s)[0] || H);
        const n = t.defaults,
            i = O.defaults,
            o = t.mediaQueries;
        if (
            ((this.defaults = n ? ws(n, i) : i),
            (this.root = r),
            (this.constructors = []),
            (this.revertConstructors = []),
            (this.revertibles = []),
            (this.constructorsOnce = []),
            (this.revertConstructorsOnce = []),
            (this.revertiblesOnce = []),
            (this.once = !1),
            (this.onceIndex = 0),
            (this.methods = {}),
            (this.matches = {}),
            (this.mediaQueryLists = {}),
            (this.data = {}),
            o)
        )
            for (let l in o) {
                const a = _t.matchMedia(o[l]);
                (this.mediaQueryLists[l] = a), a.addEventListener("change", this);
            }
    }
    register(t) {
        (this.once ? this.revertiblesOnce : this.revertibles).push(t);
    }
    execute(t) {
        let s = he.current,
            r = he.root,
            n = O.defaults;
        (he.current = this), (he.root = this.root), (O.defaults = this.defaults);
        const i = this.mediaQueryLists;
        for (let l in i) this.matches[l] = i[l].matches;
        const o = t(this);
        return (he.current = s), (he.root = r), (O.defaults = n), o;
    }
    refresh() {
        return (
            (this.onceIndex = 0),
            this.execute(() => {
                let t = this.revertibles.length,
                    s = this.revertConstructors.length;
                for (; t--; ) this.revertibles[t].revert();
                for (; s--; ) this.revertConstructors[s](this);
                (this.revertibles.length = 0),
                    (this.revertConstructors.length = 0),
                    this.constructors.forEach((r) => {
                        const n = r(this);
                        Y(n) && this.revertConstructors.push(n);
                    });
            }),
            this
        );
    }
    add(t, s) {
        if (((this.once = !1), Y(t))) {
            const r = t;
            this.constructors.push(r),
                this.execute(() => {
                    const n = r(this);
                    Y(n) && this.revertConstructors.push(n);
                });
        } else this.methods[t] = (...r) => this.execute(() => s(...r));
        return this;
    }
    addOnce(t) {
        if (((this.once = !0), Y(t))) {
            const s = this.onceIndex++;
            if (this.constructorsOnce[s]) return this;
            const n = t;
            (this.constructorsOnce[s] = n),
                this.execute(() => {
                    const i = n(this);
                    Y(i) && this.revertConstructorsOnce.push(i);
                });
        }
        return this;
    }
    keepTime(t) {
        this.once = !0;
        const s = this.onceIndex++,
            r = this.constructorsOnce[s];
        if (Y(r)) return r(this);
        const n = Ps(t);
        this.constructorsOnce[s] = n;
        let i;
        return (
            this.execute(() => {
                i = n(this);
            }),
            i
        );
    }
    handleEvent(t) {
        switch (t.type) {
            case "change":
                this.refresh();
                break;
        }
    }
    revert() {
        const t = this.revertibles,
            s = this.revertConstructors,
            r = this.revertiblesOnce,
            n = this.revertConstructorsOnce,
            i = this.mediaQueryLists;
        let o = t.length,
            l = s.length,
            a = r.length,
            c = n.length;
        for (; o--; ) t[o].revert();
        for (; l--; ) s[l](this);
        for (; a--; ) r[a].revert();
        for (; c--; ) n[c](this);
        for (let u in i) i[u].removeEventListener("change", this);
        (t.length = 0),
            (s.length = 0),
            (this.constructors.length = 0),
            (r.length = 0),
            (n.length = 0),
            (this.constructorsOnce.length = 0),
            (this.onceIndex = 0),
            (this.matches = {}),
            (this.methods = {}),
            (this.mediaQueryLists = {}),
            (this.data = {});
    }
}
const $n = (e) => new wn(e);
const Nn = (e = 0, t = 1, s = 0) => {
        const r = 10 ** s;
        return Math.floor((Math.random() * (t - e + 1 / r) + e) * r) / r;
    },
    xn = (e) => {
        let t = e.length,
            s,
            r;
        for (; t; ) (r = Nn(0, --t)), (s = e[t]), (e[t] = e[r]), (e[r] = s);
        return e;
    };
const Un = (e, t = {}) => {
    let s = [],
        r = 0;
    const n = t.from,
        i = t.reversed,
        o = t.ease,
        l = !S(o),
        c = l && !S(o.ease) ? o.ease : l ? qt(o) : null,
        u = t.grid,
        d = t.axis,
        h = t.total,
        m = S(n) || n === 0 || n === "first",
        p = n === "center",
        _ = n === "last",
        y = n === "random",
        v = Ie(e),
        b = t.use,
        N = Et(v ? e[0] : e),
        B = v ? Et(e[1]) : 0,
        w = ms.exec((v ? e[1] : e) + Ae),
        V = t.start || 0 + (v ? N : 0);
    let A = m ? 0 : Ke(n) ? n : 0;
    return (K, ee, pe, G) => {
        const [me] = Ls(K),
            M = S(h) ? pe : h,
            W = S(b) ? !1 : Y(b) ? b(me, ee, M) : ze(me, b),
            ae = Ke(W) || (Be(W) && Ke(+W)) ? +W : ee;
        if ((p && (A = (M - 1) / 2), _ && (A = M - 1), !s.length)) {
            for (let f = 0; f < M; f++) {
                if (!u) s.push(jt(A - f));
                else {
                    const k = p ? (u[0] - 1) / 2 : A % u[0],
                        _e = p ? (u[1] - 1) / 2 : Ft(A / u[0]),
                        Pe = f % u[0],
                        Z = Ft(f / u[0]),
                        $ = k - Pe,
                        q = _e - Z;
                    let X = Ss($ * $ + q * q);
                    d === "x" && (X = -$), d === "y" && (X = -q), s.push(X);
                }
                r = tn(...s);
            }
            c && (s = s.map((f) => c(f / r) * r)),
                i && (s = s.map((f) => (d ? (f < 0 ? f * -1 : -f) : jt(r - f)))),
                y && (s = xn(s));
        }
        const ce = v ? (B - N) / r : N;
        let x = (G ? Sn(G, S(t.start) ? G.iterationDuration : V) : V) + (ce * D(s[ae], 2) || 0);
        return t.modifier && (x = t.modifier(x)), w && (x = `${x}${w[2]}`), x;
    };
};
const pt = typeof Intl < "u" && Intl.Segmenter,
    En = /\{value\}/g,
    Rn = /\{i\}/g,
    Dn = /(\s+)/,
    On = /^\s+$/,
    Ht = "line",
    rt = "word",
    ot = "char",
    ct = "data-line";
let At = null,
    It = null,
    Ct = null;
const us = (e) => e.isWordLike || e.segment === " " || Ke(+e.segment),
    Lt = (e) => e.setAttribute("aria-hidden", "true"),
    mt = (e, t) => [...e.querySelectorAll(`[data-${t}]:not([data-${t}] [data-${t}])`)],
    An = { line: "#00D672", word: "#FF4B4B", char: "#5A87FF" },
    Ms = (e) => {
        if (!e.childElementCount && !e.textContent.trim()) {
            const t = e.parentElement;
            e.remove(), t && Ms(t);
        }
    },
    $s = (e, t, s) => {
        const r = e.getAttribute(ct);
        ((r !== null && +r !== t) || e.tagName === "BR") && s.add(e);
        let n = e.childElementCount;
        for (; n--; ) $s(e.children[n], t, s);
        return s;
    },
    Pt = (e, t = {}) => {
        let s = "";
        const r = Be(t.class) ? ` class="${t.class}"` : "",
            n = P(t.clone, !1),
            i = P(t.wrap, !1),
            o = i ? (i === !0 ? "clip" : i) : n ? "clip" : !1;
        if (
            (i && (s += `<span${o ? ` style="overflow:${o};"` : ""}>`),
            (s += `<span${r}${n ? ' style="position:relative;"' : ""} data-${e}="{i}">`),
            n)
        ) {
            const l = n === "left" ? "-100%" : n === "right" ? "100%" : "0",
                a = n === "top" ? "-100%" : n === "bottom" ? "100%" : "0";
            (s += "<span>{value}</span>"),
                (s += `<span inert style="position:absolute;top:${a};left:${l};white-space:nowrap;">{value}</span>`);
        } else s += "{value}";
        return (s += "</span>"), i && (s += "</span>"), s;
    },
    Mt = (e, t, s, r, n, i, o, l, a) => {
        const c = n === Ht,
            u = n === ot,
            d = `_${n}_`,
            h = Y(e) ? e(s) : e,
            m = c ? "block" : "inline-block";
        Ct.innerHTML = h.replace(En, `<i class="${d}"></i>`).replace(Rn, `${u ? a : c ? o : l}`);
        const p = Ct.content,
            _ = p.firstElementChild,
            y = p.querySelector(`[data-${n}]`) || _,
            v = p.querySelectorAll(`i.${d}`),
            b = v.length;
        if (b) {
            (_.style.display = m),
                (y.style.display = m),
                y.setAttribute(ct, `${o}`),
                c || (y.setAttribute("data-word", `${l}`), u && y.setAttribute("data-char", `${a}`));
            let N = b;
            for (; N--; ) {
                const B = v[N],
                    w = B.parentElement;
                (w.style.display = m), c ? (w.innerHTML = s.innerHTML) : w.replaceChild(s.cloneNode(!0), B);
            }
            t.push(y), r.appendChild(p);
        } else console.warn('The expression "{value}" is missing from the provided template.');
        return i && (_.style.outline = `1px dotted ${An[n]}`), _;
    };
class In {
    constructor(t, s = {}) {
        At ||
            (At = pt
                ? new pt([], { granularity: rt })
                : {
                      segment: (p) => {
                          const _ = [],
                              y = p.split(Dn);
                          for (let v = 0, b = y.length; v < b; v++) {
                              const N = y[v];
                              _.push({ segment: N, isWordLike: !On.test(N) });
                          }
                          return _;
                      },
                  }),
            It ||
                (It = pt
                    ? new pt([], { granularity: "grapheme" })
                    : { segment: (p) => [...p].map((_) => ({ segment: _ })) }),
            !Ct && xe && (Ct = H.createElement("template")),
            he.current && he.current.register(this);
        const { words: r, chars: n, lines: i, accessible: o, includeSpaces: l, debug: a } = s,
            c = (t = Ie(t) ? t[0] : t) && t.nodeType ? t : (Vt(t) || [])[0],
            u = i === !0 ? {} : i,
            d = r === !0 || S(r) ? {} : r,
            h = n === !0 ? {} : n;
        (this.debug = P(a, !1)),
            (this.includeSpaces = P(l, !1)),
            (this.accessible = P(o, !0)),
            (this.linesOnly = u && !d && !h),
            (this.lineTemplate = Ye(u) ? Pt(Ht, u) : u),
            (this.wordTemplate = Ye(d) || this.linesOnly ? Pt(rt, d) : d),
            (this.charTemplate = Ye(h) ? Pt(ot, h) : h),
            (this.$target = c),
            (this.html = c && c.innerHTML),
            (this.lines = []),
            (this.words = []),
            (this.chars = []),
            (this.effects = []),
            (this.effectsCleanups = []),
            (this.cache = null),
            (this.ready = !1),
            (this.width = 0),
            (this.resizeTimeout = null);
        const m = () => this.html && (u || d || h) && this.split();
        (this.resizeObserver = new ResizeObserver(() => {
            clearTimeout(this.resizeTimeout),
                (this.resizeTimeout = setTimeout(() => {
                    const p = c.offsetWidth;
                    p !== this.width && ((this.width = p), m());
                }, 150));
        })),
            this.lineTemplate && !this.ready ? H.fonts.ready.then(m) : m(),
            c ? this.resizeObserver.observe(c) : console.warn("No Text Splitter target found.");
    }
    addEffect(t) {
        if (!Y(t)) return console.warn("Effect must return a function.");
        const s = Ps(t);
        return this.effects.push(s), this.ready && (this.effectsCleanups[this.effects.length - 1] = s(this)), this;
    }
    revert() {
        return (
            clearTimeout(this.resizeTimeout),
            (this.lines.length = this.words.length = this.chars.length = 0),
            this.resizeObserver.disconnect(),
            this.effectsCleanups.forEach((t) => (Y(t) ? t(this) : t.revert && t.revert())),
            (this.$target.innerHTML = this.html),
            this
        );
    }
    splitNode(t) {
        const s = this.wordTemplate,
            r = this.charTemplate,
            n = this.includeSpaces,
            i = this.debug,
            o = t.nodeType;
        if (o === 3) {
            const l = t.nodeValue;
            if (l.trim()) {
                const a = [],
                    c = this.words,
                    u = this.chars,
                    d = At.segment(l),
                    h = H.createDocumentFragment();
                let m = null;
                for (const p of d) {
                    const _ = p.segment,
                        y = us(p);
                    if (!m || (y && m && us(m))) a.push(_);
                    else {
                        const v = a.length - 1;
                        !a[v].includes(" ") && !_.includes(" ") ? (a[v] += _) : a.push(_);
                    }
                    m = p;
                }
                for (let p = 0, _ = a.length; p < _; p++) {
                    const y = a[p];
                    if (y.trim()) {
                        const v = a[p + 1],
                            b = n && v && !v.trim(),
                            N = y,
                            B = r ? It.segment(N) : null,
                            w = r ? H.createDocumentFragment() : H.createTextNode(b ? y + " " : y);
                        if (r) {
                            const V = [...B];
                            for (let A = 0, K = V.length; A < K; A++) {
                                const ee = V[A],
                                    G = A === K - 1 && b ? ee.segment + " " : ee.segment,
                                    me = H.createTextNode(G);
                                Mt(r, u, me, w, ot, i, -1, c.length, u.length);
                            }
                        }
                        s
                            ? Mt(s, c, w, h, rt, i, -1, c.length, u.length)
                            : r
                              ? h.appendChild(w)
                              : h.appendChild(H.createTextNode(y)),
                            b && p++;
                    } else {
                        if (p && n) continue;
                        h.appendChild(H.createTextNode(y));
                    }
                }
                t.parentNode.replaceChild(h, t);
            }
        } else if (o === 1) {
            const l = [...t.childNodes];
            for (let a = 0, c = l.length; a < c; a++) this.splitNode(l[a]);
        }
    }
    split(t = !1) {
        const s = this.$target,
            r = !!this.cache && !t,
            n = this.lineTemplate,
            i = this.wordTemplate,
            o = this.charTemplate,
            l = H.fonts.status !== "loading",
            a = n && l;
        (this.ready = !n || l),
            (a || t) && this.effectsCleanups.forEach((h) => Y(h) && h(this)),
            r ||
                (t && ((s.innerHTML = this.html), (this.words.length = this.chars.length = 0)),
                this.splitNode(s),
                (this.cache = s.innerHTML)),
            a && (r && (s.innerHTML = this.cache), (this.lines.length = 0), i && (this.words = mt(s, rt))),
            o && (a || i) && (this.chars = mt(s, ot));
        const c = this.words.length ? this.words : this.chars;
        let u,
            d = 0;
        for (let h = 0, m = c.length; h < m; h++) {
            const p = c[h],
                { top: _, height: y } = p.getBoundingClientRect();
            u && _ - u > y * 0.5 && d++, p.setAttribute(ct, `${d}`);
            const v = p.querySelectorAll(`[${ct}]`);
            let b = v.length;
            for (; b--; ) v[b].setAttribute(ct, `${d}`);
            u = _;
        }
        if (a) {
            const h = H.createDocumentFragment(),
                m = new Set(),
                p = [];
            for (let _ = 0; _ < d + 1; _++) {
                const y = s.cloneNode(!0);
                $s(y, _, new Set()).forEach((v) => {
                    const b = v.parentElement;
                    b && m.add(b), v.remove();
                }),
                    p.push(y);
            }
            m.forEach(Ms);
            for (let _ = 0, y = p.length; _ < y; _++) Mt(n, this.lines, p[_], h, Ht, this.debug, _);
            (s.innerHTML = ""), s.appendChild(h), i && (this.words = mt(s, rt)), o && (this.chars = mt(s, ot));
        }
        if (this.linesOnly) {
            const h = this.words;
            let m = h.length;
            for (; m--; ) {
                const p = h[m];
                p.replaceWith(p.textContent);
            }
            h.length = 0;
        }
        if (this.accessible && (a || !r)) {
            const h = H.createElement("span");
            (h.style.cssText =
                "position:absolute;overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%);width:1px;height:1px;white-space:nowrap;"),
                (h.innerHTML = this.html),
                s.insertBefore(h, s.firstChild),
                this.lines.forEach(Lt),
                this.words.forEach(Lt),
                this.chars.forEach(Lt);
        }
        return (
            (this.width = s.offsetWidth),
            (a || t) && this.effects.forEach((h, m) => (this.effectsCleanups[m] = h(this))),
            this
        );
    }
    refresh() {
        this.split(!0);
    }
}
const Fn = (e, t) => new In(e, t);
export {
    H as A,
    re as B,
    Be as C,
    Ye as D,
    Fe as E,
    it as F,
    Le as G,
    Is as H,
    Wt as I,
    bn as J,
    Y as K,
    Js as L,
    gt as M,
    _t as N,
    As as T,
    Pn as a,
    Un as b,
    $n as c,
    Ls as d,
    cn as e,
    ze as f,
    Ns as g,
    ve as h,
    S as i,
    De as j,
    _n as k,
    D as l,
    O as m,
    E as n,
    P as o,
    oe as p,
    he as q,
    Nn as r,
    Fn as s,
    qt as t,
    Ke as u,
    C as v,
    ie as w,
    Qe as x,
    Mn as y,
    F as z,
};
