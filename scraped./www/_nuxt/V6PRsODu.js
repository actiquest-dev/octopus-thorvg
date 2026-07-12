import {
    G as r,
    H as c,
    I as o,
    c as l,
    a as u,
    w as p,
    m as i,
    q as f,
    u as m,
    P as x
}

from"./Dy2RtAP3.js";
const C=(s, e)=> {
    const a=s.__vccOpts||s;
    for(const[t, n]of e)a[t]=n;
    return a
}

,
_= {
    base: "w-full max-w-(--ui-container) mx-auto px-4 sm:px-6 lg:px-8"
}

,
g= {
    __name:"UContainer",
    props: {
        as: {
            type: null, required: !1
        }
        ,
        class: {
            type: null, required: !1
        }
    }
    ,
    setup(s) {
        const e=s,
        a=r(),
        t=c(()=>o( {
            extend:o(_), ...a.ui?.container|| {}
        }
        ));
        return(n, d)=>(u(), l(m(x), {
            as:s.as, class:f(t.value( {
                class: e.class
            }
            ))
        }
        , {
            default: p(()=>[i(n.$slots, "default")]), _:3
        }
        , 8, ["as", "class"]))
    }
}

;
export {
    C as _,
    g as a
}

;