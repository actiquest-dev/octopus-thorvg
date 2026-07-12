import {
    c as _,
    a as s,
    w as i,
    b as t,
    z as h,
    d as C,
    i as f,
    C as w,
    e as a,
    D as L,
    u as r,
    x as p,
    E as $,
    f as v,
    m as b,
    F as B,
} from "./Dy2RtAP3.js";
import { _ as d, a as H } from "./V6PRsODu.js";
const k = {};
function j(o, e) {
    const n = h;
    return (
        s(),
        _(
            n,
            { class: "logo-container cursor-pointer w-[100px] h-[60px] text-white dark:text-white", to: o.$localePath("/") },
            {
                default: i(() => [
                    ...(e[0] ||
                        (e[0] = [
                            t(
                                "svg",
                                {
                                    class: "w-full h-full",
                                    xmlns: "http://www.w3.org/2000/svg",
                                    version: "1.2",
                                    viewBox: "0 0 425.3 243.4",
                                },
                                [
                                    t("path", {
                                        fill: "white",
                                        d: "m398.8 32.3-58.6 98.2-17.2-16-6.8 6.3c5.2 6 11.1 11.3 16.6 17.1 21.4 22.8 41.6 47 61.4 71.2.4.5 2.9 3.4 2.6 3.8-32.9-22.6-66-45-97.2-69.9l-.8.3c-28.6 33.5-71.6 63.2-116.5 67.6-42 4.2-80.8-14.8-110.4-43.1 1.7-1.6 3.3-3.5 5.1-5.1 4.7-4.3 18.6-17.5 23.5-19.4 13.7-5.3 20.2 5.1 30.4 11.4 66.7 40.6 133.2-13.1 183.5-53.5 27.3-21.9 53.5-45.3 81.1-66.8.5-.4 2.9-2.4 3.3-2.1Z",
                                    }),
                                    t("path", {
                                        fill: "white",
                                        d: "M28.5 126.7c.6 0 1.1-.3 1.5-.7 20.7-19.8 40.9-40.6 62.2-59.7s26.1-19.3 40.7-24.6c60.6-21.9 122.6 11.7 165.3 53.2-4.9 4.8-19.7 15-25.2 19.1-18.1-13-38.1-23.8-59.9-29.4-34.5-9-63.6-4.8-90.9 18.5-20.4 17.4-39.4 36.5-59.7 54.1l-1.8 1.1-32.4-31.5Z",
                                    }),
                                    t("path", {
                                        fill: "white",
                                        d: "M180.7 94.6c-16.1 0-29.1 13-29.1 29.1s13 29.1 29.1 29.1 29.1-13 29.1-29.1-13-29.1-29.1-29.1Zm.1 39.2c-5.5 0-9.9-4.4-9.9-9.9s4.4-9.9 9.9-9.9 9.9 4.4 9.9 9.9-4.4 9.9-9.9 9.9Z",
                                    }),
                                ],
                                -1
                            ),
                        ])),
                ]),
                _: 1,
            },
            8,
            ["to"]
        )
    );
}
const y = Object.assign(d(k, [["render", j]]), { __name: "LogoButton" }),
    V = C({
        __name: "LocaleToggle",
        setup(o) {
            const { locale: e } = f(),
                n = w(),
                u = () => {
                    $(n(e.value === "de" ? "en" : "de"));
                };
            return (g, m) => {
                const c = L,
                    l = p;
                return (
                    s(),
                    _(
                        l,
                        {
                            class: "relative rounded-full w-8 h-8 cursor-pointer flex items-center justify-center p-0",
                            size: "md",
                            color: "neutral",
                            variant: "outline",
                            onClick: u,
                        },
                        {
                            default: i(() => [
                                a(
                                    c,
                                    {
                                        name:
                                            r(e) === "de"
                                                ? "emojione:flag-for-germany"
                                                : "emojione:flag-for-united-states",
                                        class: "size-6",
                                    },
                                    null,
                                    8,
                                    ["name"]
                                ),
                            ]),
                            _: 1,
                        }
                    )
                );
            };
        },
    }),
    z = Object.assign(V, { __name: "LocaleToggle" }),
    M = { class: "relative w-full z-10" },
    T = { class: "absolute top-0 w-full flex items-center justify-between py-4" },
    U = { class: "flex gap-2" },
    Z = C({
        __name: "Header",
        setup(o) {
            const { t: e, locale: n } = f();
            return (u, g) => {
                const m = y,
                    c = p,
                    l = z,
                    x = H;
                return (
                    s(),
                    _(x, null, {
                        default: i(() => [
                            t("div", M, [
                                t("header", T, [
                                    a(m),
                                    t("div", U, [
                                        a(
                                            c,
                                            {
                                                size: "xl",
                                                color: "neutral",
                                                variant: "ghost",
                                                class: "cursor-pointer font-mono uppercase font-bold tracking-widest text-lg",
                                                to: "https://anima.actiq.ai/docs",
                                                label: "Docs",
                                            },
                                            null,
                                            8,
                                            ["to", "label"]
                                        ),
                                    ]),
                                ]),
                            ]),
                        ]),
                        _: 1,
                    })
                );
            };
        },
    }),
    N = Object.assign(Z, { __name: "Header" }),
    O = {};
function P(o, e) {
    const n = N;
    return s(), v(B, null, [a(n), t("main", null, [b(o.$slots, "default")])], 64);
}
const I = d(O, [["render", P]]);
export { I as default };
