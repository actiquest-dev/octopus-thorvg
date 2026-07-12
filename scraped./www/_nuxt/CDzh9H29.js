const __vite__mapDeps = (
    i,
    m = __vite__mapDeps,
    d = m.f || (m.f = ["./BkljiIqO.js", "./CmyfV-Zi.js", "./Dy2RtAP3.js", "./entry.B-oj4OUZ.css"])
) => i.map((i) => d[i]);
import {
    d as p,
    r as d,
    o as h,
    f as _,
    b as n,
    a as f,
    i as v,
    j as b,
    k,
    e as u,
    u as L,
    l as g,
    _ as w,
} from "./Dy2RtAP3.js";
import { c as S, s as A, a as c, b as m, r as B } from "./BwkWpVHT.js";
const P = { class: "fixed top-0 left-0 z-10 w-full h-full overflow-hidden pointer-events-none select-none" },
    R = { class: "absolute top-1/2 left-1/2 -translate-1/2" },
    E = { class: "h-[7rem] sm:h-[12rem] md:h-[16rem] lg:h-[18rem] xl:h-[30rem] relative w-full" },
    z = p({
        __name: "Loader",
        props: { loaded: { type: Boolean, default: !1 } },
        setup(t) {
            const a = t,
                e = d(),
                o = d();
            return (
                h(async () => {
                    if (a.loaded) {
                        e.value.style.opacity = "0";
                        return;
                    }
                    S({ root: e.value, mediaQueries: { isSmall: "(max-width: 40rem)" } }).add((s) => {
                        if (!s) return;
                        const { isSmall: l } = s.matches,
                            r = l ? 3 : 1;
                        o.value.style.opacity = "1";
                        const { chars: i } = A(o.value, { chars: !0 }),
                            x = c(i, {
                                scale: [0.5, 1],
                                opacity: [0, 1],
                                filter: ["blur(15px)", "blur(0px)"],
                                ease: "outBack(1.7)",
                                delay: m(80, { from: "center" }),
                                loop: !0,
                                alternate: !0,
                                onLoop: () => {
                                    a.loaded &&
                                        (x.pause(),
                                        c(i, {
                                            scale: [1, 0.7],
                                            opacity: [1, 0.5],
                                            y: [0, (j, y) => B(100, 150) * r * (y % 2 === 0 ? 1 : -1) + "%"],
                                            filter: ["blur(0px)", "blur(15px)"],
                                            ease: "out(2)",
                                            delay: m(100, { from: "center" }),
                                        }),
                                        c(e.value, { ease: "out(6)", opacity: [1, 0], duration: 1500, delay: 700 }));
                                },
                            });
                    });
                }),
                (s, l) => (
                    f(),
                    _("div", P, [
                        n(
                            "div",
                            {
                                ref_key: "containerRef",
                                ref: e,
                                class: "absolute bg-default top-1/2 left-1/2 -translate-1/2 w-full h-full",
                            },
                            [
                                n("div", R, [
                                    n("div", E, [
                                        n(
                                            "div",
                                            {
                                                ref_key: "textRef",
                                                ref: o,
                                                class: "opacity-0 text-8xl sm:text-[12rem] md:text-[15rem] lg:text-[18rem] xl:text-[26rem]/120 absolute text-center font-mono font-black tracking-wide text-nowrap left-1/2 -translate-x-1/2",
                                            },
                                            " ANIMA",
                                            512
                                        ),
                                    ]),
                                ]),
                            ],
                            512
                        ),
                    ])
                )
            );
        },
    }),
    T = Object.assign(z, { __name: "Loader" }),
    V = g(() =>
        w(() => import("./BkljiIqO.js"), __vite__mapDeps([0, 1, 2, 3]), import.meta.url).then((t) => t.default || t)
    ),
    N = p({
        __name: "index",
        setup(t) {
            const { t: a } = v();
            b({ title: "ANIMA — Adaptive Neural Interface for Motion & Animation", titleTemplate: "ANIMA - %s" });
            const e = k("loaded", () => !1);
            return (o, s) => {
                const l = T,
                    r = V;
                return f(), _("div", null, [u(l, { loaded: L(e) }, null, 8, ["loaded"]), u(r)]);
            };
        },
    });
export { N as default };
