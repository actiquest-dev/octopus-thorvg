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
    a = int(len(centers)*0.28)
    b = int(len(centers)*0.92)
    step = max(1, (b-a)//count)
    k = 0
    for i in range(a, b, step):
        if k >= count:
            break
        cx, cy = centers[i]
        nx, ny = normals[i]
        r = lerp(22, 8, k/max(1,count-1))
        off = r * 1.18
        out.append((cx + nx*off*side, cy + ny*off*side, r))
        k += 1
    return out

specs = [
    # p0 p1 p2 p3 w0 w1 side
    ((720,1160),(500,1280),(360,1580),(320,1880),110,34,-1),
    ((840,1210),(690,1340),(570,1630),(590,1920),104,32,-1),
    ((960,1240),(880,1370),(790,1660),(860,1940),98,30,-1),
    ((1050,1250),(1020,1380),(980,1700),(1020,1970),94,28,-1),
    ((1140,1250),(1170,1380),(1210,1700),(1220,1970),94,28,1),
    ((1230,1240),(1310,1370),(1400,1660),(1470,1940),98,30,1),
    ((1350,1210),(1500,1340),(1620,1630),(1640,1920),104,32,1),
    ((1470,1160),(1690,1280),(1830,1580),(1860,1880),110,34,1),
]

lines = []
A = lines.append
A(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="1024" height="1024" preserveAspectRatio="xMidYMid meet">')
A('<defs>')
A('<radialGradient id="bg" cx="50%" cy="20%" r="90%"><stop offset="0" stop-color="#f0fbff"/><stop offset="1" stop-color="#d7ecf7"/></radialGradient>')
A('<linearGradient id="bodyGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#cd8cf2"/><stop offset="1" stop-color="#7a46ab"/></linearGradient>')
A('<radialGradient id="bodyHi" cx="35%" cy="26%" r="58%"><stop offset="0" stop-color="#ffffff" stop-opacity="0.50"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>')
A('<linearGradient id="bodyLow" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4b2a67" stop-opacity="0"/><stop offset="1" stop-color="#3b224f" stop-opacity="0.30"/></linearGradient>')
for i in range(1,9):
    A(f'<linearGradient id="tg{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#be7fe9"/><stop offset="1" stop-color="#653a92"/></linearGradient>')
A('</defs>')

A('<rect width="2048" height="2048" fill="url(#bg)"/>')
A('<g id="octopus_beauty">')

# Tentacles back to front
for i, sp in enumerate(specs, start=1):
    p0,p1,p2,p3,w0,w1,side = sp
    d, c, n = tentacle_shape(p0,p1,p2,p3,w0,w1)
    suck = make_suckers(c,n,side)
    A(f'<g id="tentacle_{i:02d}">')
    A(f'<path d="{d}" fill="url(#tg{i})"/>')
    A(f'<path d="{d}" fill="#2b173f" opacity="0.13"/>')
    path = 'M ' + ' '.join(f'{x:.1f},{y:.1f}' if j==0 else f'L{x:.1f},{y:.1f}' for j,(x,y) in enumerate(c))
    A(f'<path d="{path}" fill="none" stroke="#fff" stroke-opacity="0.18" stroke-width="14" stroke-linecap="round"/>')
    for j,(cx,cy,r) in enumerate(suck, start=1):
        A(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="#f6c7df"/>')
        A(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{(r*0.43):.2f}" fill="#dc8eb5"/>')
    A('</g>')

# Body
A('<g id="body">')
A('<ellipse cx="1024" cy="760" rx="520" ry="470" fill="url(#bodyGrad)"/>')
A('<ellipse cx="960" cy="620" rx="280" ry="190" fill="url(#bodyHi)"/>')
A('<ellipse cx="1120" cy="860" rx="450" ry="360" fill="url(#bodyLow)"/>')
A('</g>')

# Eyes
A('<g id="eyes">')
A('<ellipse cx="860" cy="770" rx="145" ry="155" fill="#f7fbff"/>')
A('<ellipse cx="1190" cy="770" rx="145" ry="155" fill="#f7fbff"/>')
A('<ellipse cx="860" cy="800" rx="78" ry="82" fill="#2e3040"/>')
A('<ellipse cx="1190" cy="800" rx="78" ry="82" fill="#2e3040"/>')
A('<circle cx="835" cy="765" r="22" fill="#fff"/>')
A('<circle cx="1165" cy="765" r="22" fill="#fff"/>')
A('<path d="M 715 655 C 790 610 920 610 1005 650" fill="none" stroke="#5e2f82" stroke-width="26" stroke-linecap="round" opacity="0.45"/>')
A('<path d="M 1045 650 C 1135 610 1265 610 1335 655" fill="none" stroke="#5e2f82" stroke-width="26" stroke-linecap="round" opacity="0.45"/>')
A('</g>')

# Mouth
A('<g id="mouth">')
A('<path d="M 875 1030 C 955 1120 1090 1120 1175 1030" fill="none" stroke="#5d2b78" stroke-width="30" stroke-linecap="round"/>')
A('<path d="M 930 1055 C 980 1098 1065 1098 1120 1055" fill="none" stroke="#e16e92" stroke-width="18" stroke-linecap="round" opacity="0.75"/>')
A('</g>')

A('</g>')
A('</svg>')

out = Path('/Users/miguelaprossine/octopus-thorvg/octobuss.beauty.svg')
out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(out)
