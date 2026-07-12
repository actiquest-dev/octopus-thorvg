#!/usr/bin/env python3
"""
Генерирует octobuss.rigged.svg — перерисованный осьминог-космонавт,
геометрия снята попиксельно с octobuss.source.png (цветовая сегментация).

Стиль оригинала: БЕЗ контуров, плоская заливка + тёмная двухтоновая
тень по нижней стороне каждой формы, лавандовые блики-пятна сверху.

Структура: 7 щупалец (каждое — группа с pivot и data-spine), торс-заглушка,
голова+лицо (зрачки/веки/рот/щёки отдельно), шлем, воротник.

Запуск: python3 generate_octobuss_rig.py
→ octobuss.rigged.svg + octobuss.rigged.preview.html
"""

import math

# ------------------------------------------------ палитра (снята с оригинала)
MAIN   = "#B678E4"   # основной фиолетовый
SHADE  = "#8848B8"   # тень (низ форм)
DARK   = "#683888"   # тёмные борозды между формами
HI     = "#D8B8F8"   # светлые пятна-блики
SUCK   = "#F888A8"   # присоски и щёки
SUCK_H = "#F8B8D8"   # блик присоски
SUCK_D = "#A84868"   # ободок присоски
GRAY   = "#585858"   # воротник / манжеты
GRAY_H = "#8A8290"
GRAY_D = "#383838"
SCLERA = "#F2FCFD"
GLASS  = "#C8E8F8"
GLASS_S= "#78A8B8"
MOUTH  = "#682838"
TONGUE = "#E86888"

# ------------------------------------------------ сплайн и контур

def cr_point(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    x = 0.5 * ((2*p1[0]) + (-p0[0]+p2[0])*t + (2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2 + (-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3)
    y = 0.5 * ((2*p1[1]) + (-p0[1]+p2[1])*t + (2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2 + (-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3)
    return (x, y)

def sample_spine(points, per_seg=18):
    ext = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(len(points) - 1):
        for j in range(per_seg):
            out.append(cr_point(ext[i], ext[i+1], ext[i+2], ext[i+3], j / per_seg))
    out.append(points[-1])
    return out

def tangents(P):
    T = []
    n = len(P)
    for i in range(n):
        a = P[max(0, i-1)]
        b = P[min(n-1, i+1)]
        dx, dy = b[0]-a[0], b[1]-a[1]
        l = math.hypot(dx, dy) or 1.0
        T.append((dx/l, dy/l))
    return T

def width_at(t, w0, w1, taper=1.2):
    return w0 + (w1 - w0) * (t ** taper)

def fmt(v):
    return f"{v:.1f}".rstrip('0').rstrip('.')

def poly_path(pts, close=True):
    d = f"M{fmt(pts[0][0])} {fmt(pts[0][1])}"
    for x, y in pts[1:]:
        d += f"L{fmt(x)} {fmt(y)}"
    if close:
        d += "Z"
    return d

def norm_ang(a):
    while a <= -math.pi: a += 2*math.pi
    while a > math.pi: a -= 2*math.pi
    return a

def cap_points(center, r, a_from, a_mid, a_to, steps=7):
    cx, cy = center
    pts = []
    for k in range(1, steps + 1):
        a = a_from + norm_ang(a_mid - a_from) * k / steps
        pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
    for k in range(1, steps + 1):
        a = a_mid + norm_ang(a_to - a_mid) * k / steps
        pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
    return pts

def tentacle_outline(spine, w0, w1, taper=1.2):
    """Контур: скруглённый корень + левая кромка + скруглённый кончик + правая."""
    P = sample_spine(spine)
    T = tangents(P)
    n = len(P)
    L, R = [], []
    for i, (x, y) in enumerate(P):
        t = i / (n - 1)
        w = width_at(t, w0, w1, taper) / 2
        tx, ty = T[i]
        nx, ny = -ty, tx
        L.append((x + nx*w, y + ny*w))
        R.append((x - nx*w, y - ny*w))
    # кончик
    cx, cy = P[-1]
    wt = width_at(1.0, w0, w1, taper) / 2
    a0 = math.atan2(L[-1][1]-cy, L[-1][0]-cx)
    a1 = math.atan2(R[-1][1]-cy, R[-1][0]-cx)
    amid = math.atan2(T[-1][1], T[-1][0])
    tip = cap_points(P[-1], wt, a0, amid, a1)
    # корень
    rx, ry = P[0]
    wr = width_at(0.0, w0, w1, taper) / 2
    b0 = math.atan2(R[0][1]-ry, R[0][0]-rx)
    b1 = math.atan2(L[0][1]-ry, L[0][0]-rx)
    bmid = math.atan2(-T[0][1], -T[0][0])
    root = cap_points(P[0], wr, b0, bmid, b1)
    return root + L + tip + R[::-1], P, T

def point_at(P, T, t, w0, w1, taper=1.2):
    i = min(len(P) - 1, max(0, int(round(t * (len(P) - 1)))))
    w = width_at(i / (len(P) - 1), w0, w1, taper)
    return P[i], T[i], w

# ------------------------------------------------ элементы щупальца

def el_shade(P, T, w0, w1, side, taper=1.2, t0=0.02, t1=0.98, attrs=""):
    """Тёмная тень вдоль нижней (side) кромки — двухтоновый стиль оригинала."""
    n = len(P)
    i0, i1 = int(t0*(n-1)), int(t1*(n-1))
    span = max(1, i1 - i0)
    outer, inner = [], []
    for k in range(i0, i1+1):
        t = k/(n-1)
        w = width_at(t, w0, w1, taper)
        tx, ty = T[k]
        nx, ny = -ty*side, tx*side
        x, y = P[k]
        f = min(1.0, (k-i0)/(span*0.14+1e-9), (i1-k)/(span*0.14+1e-9))
        wi = w*0.5 - (w*0.5 - w*0.06) * f   # схождение к кромке на концах
        outer.append((x + nx*w*0.5, y + ny*w*0.5))
        inner.append((x + nx*wi, y + ny*wi))
    return f'<path class="t-shade" {attrs}d="{poly_path(outer + inner[::-1])}" fill="{SHADE}" opacity="0.85"/>'

def el_sucker(P, T, t, w0, w1, side, scale=1.0, taper=1.2):
    (x, y), (tx, ty), w = point_at(P, T, t, w0, w1, taper)
    nx, ny = -ty * side, tx * side
    rx, ry = w * 0.29 * scale, w * 0.19 * scale
    cx, cy = x + nx * (w/2 - ry*0.15), y + ny * (w/2 - ry*0.15)
    ang = math.degrees(math.atan2(ty, tx))
    meta = f'data-t="{t}" data-scale="{scale:.3f}"'
    return (
        f'<ellipse class="t-sucker" data-kind="base" {meta} cx="{fmt(cx)}" cy="{fmt(cy)}" rx="{fmt(rx)}" ry="{fmt(ry)}" '
        f'fill="{SUCK}" stroke="{SUCK_D}" stroke-width="4" transform="rotate({fmt(ang)} {fmt(cx)} {fmt(cy)})"/>'
        f'<ellipse class="t-sucker" data-kind="hi" {meta} cx="{fmt(cx - nx*ry*0.4)}" cy="{fmt(cy - ny*ry*0.4)}" rx="{fmt(rx*0.6)}" ry="{fmt(ry*0.45)}" '
        f'fill="{SUCK_H}" transform="rotate({fmt(ang)} {fmt(cx - nx*ry*0.4)} {fmt(cy - ny*ry*0.4)})"/>'
    )

def el_spot(P, T, t, w0, w1, side, scale=1.0, taper=1.2):
    (x, y), (tx, ty), w = point_at(P, T, t, w0, w1, taper)
    nx, ny = ty * side, -tx * side   # верхняя сторона (противоположна присоскам)
    cx, cy = x + nx * w * 0.18, y + ny * w * 0.18
    rx, ry = w * 0.30 * scale, w * 0.13 * scale
    ang = math.degrees(math.atan2(ty, tx))
    return (f'<ellipse class="t-spot" data-t="{t}" data-scale="{scale:.3f}" '
            f'cx="{fmt(cx)}" cy="{fmt(cy)}" rx="{fmt(rx)}" ry="{fmt(ry)}" '
            f'fill="{HI}" transform="rotate({fmt(ang)} {fmt(cx)} {fmt(cy)})"/>')

def el_band(P, T, t, w0, w1, taper=1.2):
    """Серая манжета перпендикулярно хребту (без контура, свет/тень по краям)."""
    n = len(P)
    i = int(round(t * (n - 1)))
    di = max(4, int(n * 0.045))
    def strip(j0, j1, factor):
        Lp, Rp = [], []
        for k in range(max(0,j0), min(n-1,j1) + 1):
            tt = k / (n - 1)
            w = width_at(tt, w0, w1, taper) * factor / 2
            tx, ty = T[k]
            nx, ny = -ty, tx
            x, y = P[k]
            Lp.append((x + nx*w, y + ny*w))
            Rp.append((x - nx*w, y - ny*w))
        return Lp + Rp[::-1]
    meta = f'data-t="{t}"'
    base = f'<path class="t-band" data-part="base" {meta} d="{poly_path(strip(i-di, i+di, 1.30))}" fill="{GRAY}"/>'
    lite = f'<path class="t-band" data-part="lite" {meta} d="{poly_path(strip(i-di, i-di+max(2,di//3), 1.30))}" fill="{GRAY_H}" opacity="0.9"/>'
    dark = f'<path class="t-band" data-part="dark" {meta} d="{poly_path(strip(i+di-max(2,di//3), i+di, 1.30))}" fill="{GRAY_D}" opacity="0.9"/>'
    return base + lite + dark

def spine_attr(spine):
    return " ".join(f"{fmt(x)},{fmt(y)}" for x, y in spine)

def tentacle_group(gid, name, spine, w0, w1, side, sucker_ts, spot_ts,
                   band_t=None, taper=1.2):
    outline, P, T = tentacle_outline(spine, w0, w1, taper)
    px, py = spine[0]
    parts = [f'<!-- {name} -->']
    parts.append(
        f'<g id="{gid}" class="tentacle" data-name="{name}" '
        f'data-pivot="{fmt(px)},{fmt(py)}" data-spine="{spine_attr(spine)}" '
        f'data-w0="{w0}" data-w1="{w1}" data-taper="{taper}" data-side="{side}" '
        f'style="transform-origin:{fmt(px)}px {fmt(py)}px">'
    )
    parts.append(f'<path class="t-main" d="{poly_path(outline)}" fill="{MAIN}"/>')
    parts.append(el_shade(P, T, w0, w1, side, taper))
    for k, t in enumerate(spot_ts):
        parts.append(el_spot(P, T, t, w0, w1, side, scale=1.0 - 0.18*k, taper=taper))
    for k, t in enumerate(sucker_ts):
        parts.append(el_sucker(P, T, t, w0, w1, side, scale=1.0 - 0.055*k, taper=taper))
    if band_t is not None:
        parts.append(el_band(P, T, band_t, w0, w1, taper))
    parts.append('</g>')
    return "\n".join(parts)

# ------------------------------------------------ щупальца (координаты с оригинала)

TENTACLES = {
    # id: (имя, spine, w0, w1, сторона присосок, присоски t, пятна t, манжета t, taper)
    "tentacle_up_l": ("верхняя левая рука",
        [(580,1200),(530,1130),(490,1060),(455,990),(425,925),(385,868),(325,855),
         (262,878),(226,938),(228,1002),(272,1046),(325,1050)],
        145, 52, -1, [0.05,0.16,0.27,0.38,0.50,0.64,0.78,0.90], [0.16,0.34], None, 1.2),
    "tentacle_up_r": ("верхняя правая рука (с манжетой)",
        [(1470,1235),(1510,1170),(1550,1105),(1590,1042),(1625,988),(1660,935),
         (1700,895),(1748,878),(1802,902),(1846,960),(1852,1026),(1815,1070)],
        145, 52, 1, [0.04,0.15,0.26,0.55,0.68,0.80,0.90], [0.20,0.45], 0.36, 1.2),
    "tentacle_band_l": ("левое длинное (с манжетой)",
        [(760,1140),(730,1230),(690,1300),(630,1355),(560,1398),(480,1420),
         (390,1408),(285,1375),(190,1318),(165,1250),(210,1205),(285,1200),
         (355,1230),(420,1278),(452,1318)],
        135, 46, -1, [0.46,0.55,0.86,0.94], [0.12,0.28], 0.33, 1.2),
    "tentacle_far_r": ("правое длинное",
        [(1290,1170),(1335,1265),(1400,1350),(1490,1400),(1600,1408),(1710,1380),
         (1800,1330),(1860,1285),(1916,1300),(1932,1360),(1900,1418),(1838,1432),(1805,1392)],
        140, 48, 1, [0.18,0.30,0.42,0.54,0.72,0.82], [0.12,0.38], None, 1.2),
    "tentacle_front_l": ("переднее левое",
        [(845,1180),(848,1290),(825,1395),(775,1480),(700,1548),(610,1590),
         (540,1622),(487,1655),(497,1692),(552,1692),(576,1652)],
        130, 44, -1, [0.50,0.62,0.74,0.88], [0.24], None, 1.2),
    "tentacle_front_c": ("переднее центральное",
        [(1005,1170),(1010,1290),(995,1400),(960,1495),(908,1572),(855,1620),
         (830,1672),(872,1708),(940,1697),(960,1648)],
        235, 52, -1, [], [0.30,0.76,0.88], None, 1.3),
    "tentacle_front_r": ("переднее правое",
        [(1175,1180),(1195,1290),(1200,1390),(1215,1480),(1255,1560),(1320,1630),
         (1392,1662),(1444,1638),(1452,1585),(1410,1558)],
        150, 48, -1, [0.55,0.72], [0.35], None, 1.25),
}

# порядок отрисовки: сзади → вперёд
ORDER_BACK  = ["tentacle_up_l", "tentacle_far_r", "tentacle_up_r"]
ORDER_FRONT = ["tentacle_band_l", "tentacle_front_l", "tentacle_front_r", "tentacle_front_c"]

# ------------------------------------------------ торс, голова, шлем, воротник

def body_group():
    # тело-мантия за веером щупалец: волнистая перепончатая кромка
    # (провисает между корнями щупалец), тень — лентой вдоль кромки
    return f'''<!-- тело-мантия с перепонкой (за щупальцами) -->
<g id="body" data-pivot="1005,1250" style="transform-origin:1005px 1250px">
<path fill="{MAIN}" d="M622 1122
C592 1245 615 1335 700 1400
Q772 1478 845 1495
Q925 1560 1005 1545
Q1090 1565 1175 1500
Q1252 1480 1310 1395
C1395 1318 1428 1215 1430 1122 Z"/>
<path fill="{SHADE}" opacity="0.5" d="M706 1345
Q780 1418 848 1432
Q928 1495 1005 1482
Q1085 1500 1168 1440
Q1240 1420 1295 1345
L1310 1395
Q1252 1480 1175 1500
Q1090 1565 1005 1545
Q925 1560 845 1495
Q772 1478 700 1400 Z"/>
</g>'''

def collar_shadow():
    return (f'<ellipse id="collar_shadow" cx="1034" cy="1180" rx="340" ry="52" '
            f'fill="{DARK}" opacity="0.5"/>')

def head_group():
    return f'''<!-- голова + лицо (кивает внутри шлема) -->
<g id="head_group" data-pivot="1034,1050" style="transform-origin:1034px 1050px">
<g id="head">
<ellipse cx="1033" cy="760" rx="417" ry="385" fill="{MAIN}"/>
<ellipse cx="1218" cy="506" rx="54" ry="44" fill="{HI}" transform="rotate(28 1218 506)"/>
</g>
<g id="face" data-pivot="1010,810" style="transform-origin:1010px 810px">
<g id="cheeks">
<ellipse id="cheek_l" cx="730" cy="886" rx="64" ry="66" fill="{SUCK}"/>
<ellipse id="cheek_r" cx="1259" cy="912" rx="73" ry="66" fill="{SUCK}"/>
</g>
<g id="eye_l" data-pivot="799,747" style="transform-origin:799px 747px">
<ellipse cx="799" cy="747" rx="89" ry="99" fill="{SCLERA}"/>
<g clip-path="url(#eyeClipL)">
<g id="pupil_l" data-pivot="821,749" style="transform-origin:821px 749px">
<ellipse cx="821" cy="749" rx="78" ry="80" fill="url(#eyeGrad)"/>
<circle cx="835" cy="793" r="12" fill="#FFFFFF"/>
</g>
</g>
<ellipse id="lid_l" cx="799" cy="747" rx="91" ry="101" fill="{MAIN}" opacity="0" style="transform-origin:799px 747px"/>
<ellipse id="hi_l" cx="851" cy="709" rx="26" ry="32" fill="#FFFFFF" transform="rotate(35 851 709)"/>
</g>
<g id="eye_r" data-pivot="1195,765" style="transform-origin:1195px 765px">
<ellipse cx="1195" cy="765" rx="103" ry="103" fill="{SCLERA}"/>
<g clip-path="url(#eyeClipR)">
<g id="pupil_r" data-pivot="1179,767" style="transform-origin:1179px 767px">
<ellipse cx="1179" cy="767" rx="84" ry="85" fill="url(#eyeGrad)"/>
<circle cx="1159" cy="813" r="12" fill="#FFFFFF"/>
</g>
</g>
<ellipse id="lid_r" cx="1195" cy="765" rx="105" ry="105" fill="{MAIN}" opacity="0" style="transform-origin:1195px 765px"/>
<ellipse id="hi_r" cx="1145" cy="727" rx="27" ry="33" fill="#FFFFFF" transform="rotate(-35 1145 727)"/>
</g>
<g id="brows">
<path id="brow_l" d="M732 622 Q800 590 866 616" fill="none" stroke="{DARK}" stroke-width="26" stroke-linecap="round" opacity="0" style="transform-origin:799px 610px"/>
<path id="brow_r" d="M1128 634 Q1196 602 1262 628" fill="none" stroke="{DARK}" stroke-width="26" stroke-linecap="round" opacity="0" style="transform-origin:1195px 622px"/>
</g>
<g id="mouth" data-pivot="986,900" style="transform-origin:986px 900px">
<path id="mouth_open" d="M892 858
C930 882 1042 880 1080 848
C1088 890 1066 934 1024 957
C986 976 940 968 914 940
C898 922 890 890 892 858 Z" fill="{MOUTH}"/>
<path id="tongue" d="M928 916 C958 902 1026 900 1054 914 C1044 946 1014 962 982 960 C954 958 936 940 928 916 Z" fill="{TONGUE}"/>
<ellipse id="tongue_hi" cx="962" cy="932" rx="22" ry="7" fill="{SUCK_H}" opacity="0.85"/>
</g>
</g>
</g>'''

def helmet_group():
    cx, cy, rx, ry = 1041, 722, 508, 470
    def arcpt(r_off, adeg):
        a = math.radians(adeg)
        return (cx + (rx-r_off)*math.cos(a), cy + (ry-r_off)*math.sin(a))
    big = [arcpt(54, a) for a in range(196, 254, 4)]
    small_l = [arcpt(54, a) for a in range(152, 171, 4)]
    small_r = [arcpt(54, a) for a in range(298, 319, 4)]
    def arc_d(pts):
        return "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)
    return f'''<!-- шлем (стекло) -->
<g id="helmet" data-pivot="{cx},{cy}">
<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{GLASS}" fill-opacity="0.25" stroke="{GLASS_S}" stroke-width="13"/>
<path d="{arc_d(big)}" fill="none" stroke="#FFFFFF" stroke-width="44" stroke-linecap="round" opacity="0.85"/>
<path d="{arc_d(small_l)}" fill="none" stroke="#FFFFFF" stroke-width="26" stroke-linecap="round" opacity="0.6"/>
<path d="{arc_d(small_r)}" fill="none" stroke="#FFFFFF" stroke-width="24" stroke-linecap="round" opacity="0.6"/>
<ellipse cx="742" cy="396" rx="34" ry="17" fill="#FFFFFF" opacity="0.85" transform="rotate(40 742 396)"/>
<ellipse cx="1312" cy="388" rx="29" ry="15" fill="#FFFFFF" opacity="0.7" transform="rotate(-36 1312 388)"/>
</g>'''

def collar_back_group():
    # светлая верхняя грань кольца — за головой, видна по бокам подбородка
    return f'''<!-- воротник: верхняя грань (за головой) -->
<g id="collar_back" data-pivot="1034,1030" style="transform-origin:1034px 1030px">
<path fill="{GRAY_H}" d="M628 1032
A406 34 0 0 1 1440 1032 A406 25 0 0 1 628 1032 Z"/>
</g>'''

def collar_front_group():
    # передняя труба кольца: верхний край провисает, закрывает подбородок
    return f'''<!-- воротник: передняя труба -->
<g id="collar_front" data-pivot="1034,1110" style="transform-origin:1034px 1110px">
<path fill="{GRAY}" d="M628 1030
A406 25 0 0 0 1440 1030
A30 33 0 0 1 1444 1094
A410 100 0 0 1 624 1094
A30 33 0 0 1 628 1030 Z"/>
<path fill="{GRAY_D}" opacity="0.7" d="M676 1124
A390 62 0 0 0 1392 1124 A390 22 0 0 1 676 1124 Z"/>
</g>'''

# ------------------------------------------------ сборка

def build_svg():
    parts = []
    parts.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2048 2048" width="1024" height="1024">')
    parts.append('''<defs>
<radialGradient id="eyeGrad" cx="50%" cy="45%" r="60%">
<stop offset="0%" stop-color="#46414C"/>
<stop offset="100%" stop-color="#25222A"/>
</radialGradient>
<clipPath id="eyeClipL"><ellipse cx="799" cy="747" rx="89" ry="99"/></clipPath>
<clipPath id="eyeClipR"><ellipse cx="1195" cy="765" rx="103" ry="103"/></clipPath>
</defs>''')
    parts.append('<g id="octobuss">')

    parts.append('<g id="tentacles_back">')
    for tid in ORDER_BACK:
        name, spine, w0, w1, side, s_ts, sp_ts, band, taper = TENTACLES[tid]
        parts.append(tentacle_group(tid, name, spine, w0, w1, side, s_ts, sp_ts, band, taper))
    parts.append('</g>')

    parts.append(body_group())

    parts.append('<g id="tentacles_front">')
    for tid in ORDER_FRONT:
        name, spine, w0, w1, side, s_ts, sp_ts, band, taper = TENTACLES[tid]
        parts.append(tentacle_group(tid, name, spine, w0, w1, side, s_ts, sp_ts, band, taper))
    parts.append('</g>')

    parts.append(collar_shadow())
    parts.append(collar_back_group())
    parts.append(head_group())
    parts.append(helmet_group())
    parts.append(collar_front_group())

    parts.append('</g>')
    parts.append('</svg>')
    return "\n".join(parts)

# ------------------------------------------------ превью с анимацией

PREVIEW = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><title>Octobuss — rig preview</title>
<style>
body {{ margin:0; background:#101528; display:flex; flex-direction:column;
       align-items:center; font-family:sans-serif; color:#cfd6ee; }}
h1 {{ font-size:15px; font-weight:normal; margin:12px 0 0; opacity:.7 }}
svg {{ width:92vmin; height:92vmin; }}
@keyframes swayS {{ from {{ transform:rotate(-3deg) }} to {{ transform:rotate(3deg) }} }}
@keyframes swayM {{ from {{ transform:rotate(-5deg) }} to {{ transform:rotate(5deg) }} }}
@keyframes swayL {{ from {{ transform:rotate(-7deg) }} to {{ transform:rotate(7deg) }} }}
#tentacle_up_l    {{ animation: swayM 2.9s ease-in-out -0.4s infinite alternate }}
#tentacle_up_r    {{ animation: swayM 3.3s ease-in-out -1.1s infinite alternate }}
#tentacle_band_l  {{ animation: swayS 3.6s ease-in-out -0.8s infinite alternate }}
#tentacle_far_r   {{ animation: swayS 3.1s ease-in-out -1.7s infinite alternate }}
#tentacle_front_l {{ animation: swayL 2.7s ease-in-out -0.2s infinite alternate }}
#tentacle_front_c {{ animation: swayS 3.4s ease-in-out -1.4s infinite alternate }}
#tentacle_front_r {{ animation: swayL 2.5s ease-in-out -0.6s infinite alternate }}
@keyframes bob {{ to {{ transform: translateY(16px) rotate(1.2deg) }} }}
#head_group {{ animation: bob 3.8s ease-in-out infinite alternate }}
@keyframes blink {{ 0%, 91%, 100% {{ opacity:0 }} 93%, 97% {{ opacity:1 }} }}
#lid_l, #lid_r {{ animation: blink 4.5s infinite }}
</style></head><body>
<h1>octobuss.rigged.svg — щупальца качаются, веки моргают, зрачки следят за курсором</h1>
{svg}
<script>
const svg = document.querySelector('svg');
const pupils = [
  {{ el: document.getElementById('pupil_l'), cx: 821,  cy: 749 }},
  {{ el: document.getElementById('pupil_r'), cx: 1179, cy: 767 }},
];
document.addEventListener('mousemove', e => {{
  const r = svg.getBoundingClientRect();
  const mx = (e.clientX - r.left) / r.width * 2048;
  const my = (e.clientY - r.top) / r.height * 2048;
  for (const p of pupils) {{
    let dx = mx - p.cx, dy = my - p.cy;
    const d = Math.hypot(dx, dy) || 1, max = 24;
    const k = Math.min(1, d / 500) * max / d;
    p.el.style.transform = `translate(${{dx * k}}px, ${{dy * k}}px)`;
  }}
}});
</script>
</body></html>
"""

if __name__ == "__main__":
    svg = build_svg()
    with open("octobuss.rigged.svg", "w") as f:
        f.write(svg)
    print(f"OK: octobuss.rigged.svg ({len(svg)} bytes)")
    with open("octobuss.rigged.preview.html", "w") as f:
        f.write(PREVIEW.format(svg=svg))
    print("OK: octobuss.rigged.preview.html")
