#!/usr/bin/env python3
from math import sqrt
from pathlib import Path

W, H = 2048, 2048


def lerp(a, b, t):
    return a + (b - a) * t


def bez_point(p0, p1, p2, p3, t):
    u = 1 - t
    x = u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0]
    y = u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]
    return x, y


def bez_tan(p0, p1, p2, p3, t):
    u = 1 - t
    dx = 3*u*u*(p1[0]-p0[0]) + 6*u*t*(p2[0]-p1[0]) + 3*t*t*(p3[0]-p2[0])
    dy = 3*u*u*(p1[1]-p0[1]) + 6*u*t*(p2[1]-p1[1]) + 3*t*t*(p3[1]-p2[1])
    d = sqrt(dx*dx + dy*dy) or 1
    return dx/d, dy/d


def tentacle_shape(p0, p1, p2, p3, w0, w1, n=56):
    left, right, centers, normals = [], [], [], []
    for i in range(n + 1):
        t = i / n
        x, y = bez_point(p0, p1, p2, p3, t)
        tx, ty = bez_tan(p0, p1, p2, p3, t)
        nx, ny = -ty, tx
        w = lerp(w0, w1, t)
        left.append((x + nx*w, y + ny*w))
        right.append((x - nx*w, y - ny*w))
        centers.append((x, y))
        normals.append((nx, ny))
    poly = left + list(reversed(right))
    d = f'M {poly[0][0]:.2f} {poly[0][1]:.2f} ' + ' '.join(f'L {x:.2f} {y:.2f}' for x, y in poly[1:]) + ' Z'
    return d, centers, normals


def make_suckers(centers, normals, side, count=10):
    out = []
    a = int(len(centers) * 0.28)
    b = int(len(centers) * 0.92)
    step = max(1, (b - a) // count)
    k = 0
    for i in range(a, b, step):
        if k >= count:
            break
        cx, cy = centers[i]
        nx, ny = normals[i]
        r = lerp(22, 8, k / max(1, count - 1))
        off = r * 1.18
        out.append((cx + nx * off * side, cy + ny * off * side, r))
        k += 1
    return out


specs = [
    ((720,1160),(500,1280),(360,1580),(320,1880),110,34,-1),
    ((840,1210),(690,1340),(570,1630),(590,1920),104,32,-1),
    ((960,1240),(880,1370),(790,1660),(860,1940),98,30,-1),
    ((1050,1250),(1020,1380),(980,1700),(1020,1970),94,28,-1),
    ((1140,1250),(1170,1380),(1210,1700),(1220,1970),94,28,1),
    ((1230,1240),(1310,1370),(1400,1660),(1470,1940),98,30,1),
    ((1350,1210),(1500,1340),(1620,1630),(1640,1920),104,32,1),
    ((1470,1160),(1690,1280),(1830,1580),(1860,1880),110,34,1),
]

L = []
A = L.append
A(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="1024" height="1024" preserveAspectRatio="xMidYMid meet">')
A('<defs>')
A('<radialGradient id="bg" cx="50%" cy="20%" r="90%"><stop offset="0" stop-color="#f0fbff"/><stop offset="1" stop-color="#d7ecf7"/></radialGradient>')
A('<linearGradient id="body_grad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#cd8cf2"/><stop offset="1" stop-color="#7a46ab"/></linearGradient>')
A('<radialGradient id="body_hi" cx="35%" cy="26%" r="58%"><stop offset="0" stop-color="#ffffff" stop-opacity="0.50"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>')
A('<linearGradient id="body_sh" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4b2a67" stop-opacity="0"/><stop offset="1" stop-color="#3b224f" stop-opacity="0.30"/></linearGradient>')
for i in range(1, 9):
    A(f'<linearGradient id="tentacle_{i:02d}_grad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#be7fe9"/><stop offset="1" stop-color="#653a92"/></linearGradient>')
A('</defs>')
A('<rect id="bg_layer" width="2048" height="2048" fill="url(#bg)"/>')
A('<g id="character_octopus" data-rig="character">')

# Tentacles: each as independent object with strict sublayers and clip-path.
for i, sp in enumerate(specs, start=1):
    p0, p1, p2, p3, w0, w1, side = sp
    d, centers, normals = tentacle_shape(p0, p1, p2, p3, w0, w1)
    suck = make_suckers(centers, normals, side)
    tid = f'tentacle_{i:02d}'
    clip = f'clip_{tid}'

    A(f'<defs><clipPath id="{clip}"><path d="{d}"/></clipPath></defs>')
    A(f'<g id="{tid}" data-rig="limb" data-pivot-x="{p0[0]}" data-pivot-y="{p0[1]}">')
    A(f'<path id="{tid}_fill" d="{d}" fill="url(#{tid}_grad)"/>')
    A(f'<path id="{tid}_shadow" d="{d}" fill="#2b173f" opacity="0.13" clip-path="url(#{clip})"/>')

    # Highlight detail (clipped)
    stroke_path = 'M ' + ' '.join(
        f'{x:.1f},{y:.1f}' if j == 0 else f'L{x:.1f},{y:.1f}'
        for j, (x, y) in enumerate(centers)
    )
    A(f'<path id="{tid}_highlight" d="{stroke_path}" fill="none" stroke="#fff" stroke-opacity="0.18" stroke-width="14" stroke-linecap="round" clip-path="url(#{clip})"/>')

    A(f'<g id="{tid}_suckers" data-rig="details" clip-path="url(#{clip})">')
    for j, (cx, cy, r) in enumerate(suck, start=1):
        sid = f'{tid}_sucker_{j:02d}'
        A(f'<circle id="{sid}" cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="#f6c7df"/>')
        A(f'<circle id="{sid}_core" cx="{cx:.2f}" cy="{cy:.2f}" r="{(r*0.43):.2f}" fill="#dc8eb5"/>')
    A('</g>')
    A('</g>')

# Body object
A('<g id="body" data-rig="object">')
A('<ellipse id="body_fill" cx="1024" cy="760" rx="520" ry="470" fill="url(#body_grad)"/>')
A('<ellipse id="body_highlight" cx="960" cy="620" rx="280" ry="190" fill="url(#body_hi)"/>')
A('<ellipse id="body_shadow" cx="1120" cy="860" rx="450" ry="360" fill="url(#body_sh)"/>')
A('</g>')

# Face object with independent controls
A('<g id="face" data-rig="object">')
A('<g id="eye_left" data-rig="eye" data-pivot-x="860" data-pivot-y="770">')
A('<ellipse id="eye_left_white" cx="860" cy="770" rx="145" ry="155" fill="#f7fbff"/>')
A('<ellipse id="eye_left_pupil" cx="860" cy="800" rx="78" ry="82" fill="#2e3040"/>')
A('<circle id="eye_left_glint" cx="835" cy="765" r="22" fill="#fff"/>')
A('</g>')
A('<g id="eye_right" data-rig="eye" data-pivot-x="1190" data-pivot-y="770">')
A('<ellipse id="eye_right_white" cx="1190" cy="770" rx="145" ry="155" fill="#f7fbff"/>')
A('<ellipse id="eye_right_pupil" cx="1190" cy="800" rx="78" ry="82" fill="#2e3040"/>')
A('<circle id="eye_right_glint" cx="1165" cy="765" r="22" fill="#fff"/>')
A('</g>')
A('<path id="brow_left" d="M 715 655 C 790 610 920 610 1005 650" fill="none" stroke="#5e2f82" stroke-width="26" stroke-linecap="round" opacity="0.45"/>')
A('<path id="brow_right" d="M 1045 650 C 1135 610 1265 610 1335 655" fill="none" stroke="#5e2f82" stroke-width="26" stroke-linecap="round" opacity="0.45"/>')
A('<g id="mouth" data-rig="mouth" data-pivot-x="1024" data-pivot-y="1040">')
A('<path id="mouth_line" d="M 875 1030 C 955 1120 1090 1120 1175 1030" fill="none" stroke="#5d2b78" stroke-width="30" stroke-linecap="round"/>')
A('<path id="mouth_inner" d="M 930 1055 C 980 1098 1065 1098 1120 1055" fill="none" stroke="#e16e92" stroke-width="18" stroke-linecap="round" opacity="0.75"/>')
A('</g>')
A('</g>')

A('</g>')
A('</svg>')

out = Path('/Users/miguelaprossine/octopus-thorvg/octobuss.beauty.rig.svg')
out.write_text('\n'.join(L) + '\n', encoding='utf-8')
print(out)
