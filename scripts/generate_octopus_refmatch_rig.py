#!/usr/bin/env python3
from math import sqrt
from pathlib import Path

W, H = 1024, 1024


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


def tentacle_outline(p0, p1, p2, p3, w0, w1, n=44):
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


def make_suckers(centers, normals, side, count=8):
    out = []
    a = int(len(centers) * 0.34)
    b = int(len(centers) * 0.90)
    step = max(1, (b - a) // count)
    idx = 0
    for i in range(a, b, step):
        if idx >= count:
            break
        cx, cy = centers[i]
        nx, ny = normals[i]
        r = lerp(12, 5, idx / max(1, count - 1))
        off = r * 1.2
        out.append((cx + nx * off * side, cy + ny * off * side, r))
        idx += 1
    return out

# Curled tentacles similar to reference silhouette.
specs = [
    # base, c1, c2, tip, w0, w1, underside side
    ((356,560),(250,560),(155,640),(120,610),46,14,-1),
    ((420,584),(320,620),(210,730),(150,690),44,14,-1),
    ((468,602),(405,670),(345,790),(305,760),42,13,-1),
    ((528,610),(528,700),(500,825),(470,785),42,13,-1),
    ((592,610),(598,700),(625,825),(655,785),42,13,1),
    ((648,602),(710,670),(770,790),(810,760),42,13,1),
    ((700,584),(798,620),(905,730),(965,690),44,14,1),
    ((764,560),(870,560),(965,640),(998,610),46,14,1),
]

L = []
A = L.append
A(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" preserveAspectRatio="xMidYMid meet">')
A('<defs>')
A('<radialGradient id="bg" cx="50%" cy="42%" r="70%"><stop offset="0" stop-color="#f8fbff"/><stop offset="1" stop-color="#eaf2f7"/></radialGradient>')
A('<linearGradient id="body_grad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ab74d8"/><stop offset="1" stop-color="#915bc7"/></linearGradient>')
A('<linearGradient id="limb_grad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b77ae2"/><stop offset="1" stop-color="#8d55c6"/></linearGradient>')
A('</defs>')

A('<rect id="bg_layer" width="1024" height="1024" fill="url(#bg)"/>')
A('<g id="character_octopus" data-rig="character">')

# Tentacles behind torso
for i, sp in enumerate(specs, start=1):
    p0,p1,p2,p3,w0,w1,side = sp
    d, centers, normals = tentacle_outline(p0,p1,p2,p3,w0,w1)
    tid = f'tentacle_{i:02d}'
    clip = f'clip_{tid}'
    suckers = make_suckers(centers, normals, side)

    A(f'<defs><clipPath id="{clip}"><path d="{d}"/></clipPath></defs>')
    A(f'<g id="{tid}" data-rig="limb" data-pivot-x="{p0[0]}" data-pivot-y="{p0[1]}">')
    A(f'<path id="{tid}_fill" d="{d}" fill="url(#limb_grad)" stroke="#7643a8" stroke-width="6"/>')
    A(f'<path id="{tid}_shadow" d="{d}" fill="#4e2b73" opacity="0.16" clip-path="url(#{clip})"/>')

    # highlight line
    lp = 'M ' + ' '.join(f'{x:.1f},{y:.1f}' if j == 0 else f'L{x:.1f},{y:.1f}' for j,(x,y) in enumerate(centers))
    A(f'<path id="{tid}_highlight" d="{lp}" fill="none" stroke="#d7b9f1" stroke-opacity="0.7" stroke-width="8" stroke-linecap="round" clip-path="url(#{clip})"/>')

    # Suckers only for middle tentacles like reference emphasis
    A(f'<g id="{tid}_suckers" data-rig="details" clip-path="url(#{clip})">')
    for j, (cx,cy,r) in enumerate(suckers, start=1):
        if i in (2,3,6,7):
            A(f'<ellipse id="{tid}_sucker_{j:02d}" cx="{cx:.2f}" cy="{cy:.2f}" rx="{r:.2f}" ry="{(r*0.72):.2f}" fill="#f5b3cd" stroke="#dc89ad" stroke-width="2"/>')
    A('</g>')
    A('</g>')

# Torso + head
A('<g id="body" data-rig="object">')
A('<ellipse id="head_fill" cx="512" cy="360" rx="250" ry="245" fill="url(#body_grad)" stroke="#6e3d9f" stroke-width="6"/>')
A('<ellipse id="head_hi" cx="430" cy="275" rx="76" ry="54" fill="#cda8ea" opacity="0.45"/>')
A('<ellipse id="cheek_l" cx="408" cy="390" rx="36" ry="34" fill="#f58cb3" opacity="0.95"/>')
A('<ellipse id="cheek_r" cx="614" cy="390" rx="36" ry="34" fill="#f58cb3" opacity="0.95"/>')
A('</g>')

# Glass helmet
A('<g id="helmet" data-rig="object">')
A('<circle id="helmet_outline" cx="512" cy="360" r="274" fill="none" stroke="#8ab4cc" stroke-width="7"/>')
A('<circle id="helmet_glass" cx="512" cy="360" r="268" fill="#b8e2f2" opacity="0.18"/>')
A('<ellipse id="helmet_glare_1" cx="347" cy="238" rx="28" ry="16" fill="#ffffff" opacity="0.55" transform="rotate(-35 347 238)"/>')
A('<ellipse id="helmet_glare_2" cx="679" cy="238" rx="28" ry="16" fill="#ffffff" opacity="0.55" transform="rotate(35 679 238)"/>')
A('</g>')

# Collar ring
A('<g id="collar" data-rig="object">')
A('<ellipse id="collar_back" cx="512" cy="528" rx="216" ry="52" fill="#4e4a55"/>')
A('<ellipse id="collar_inner" cx="512" cy="516" rx="194" ry="40" fill="#6a6474"/>')
A('<ellipse id="collar_front" cx="512" cy="538" rx="214" ry="44" fill="#575360"/>')
A('</g>')

# Face controls
A('<g id="face" data-rig="object">')
A('<g id="eye_left" data-rig="eye" data-pivot-x="454" data-pivot-y="347">')
A('<circle id="eye_left_white" cx="454" cy="347" r="67" fill="#f7fbff"/>')
A('<circle id="eye_left_pupil" cx="454" cy="356" r="38" fill="#383640"/>')
A('<circle id="eye_left_glint" cx="473" cy="334" r="10" fill="#fff"/>')
A('</g>')
A('<g id="eye_right" data-rig="eye" data-pivot-x="570" data-pivot-y="347">')
A('<circle id="eye_right_white" cx="570" cy="347" r="67" fill="#f7fbff"/>')
A('<circle id="eye_right_pupil" cx="570" cy="356" r="38" fill="#383640"/>')
A('<circle id="eye_right_glint" cx="589" cy="334" r="10" fill="#fff"/>')
A('</g>')
A('<g id="mouth" data-rig="mouth" data-pivot-x="512" data-pivot-y="438">')
A('<path id="mouth_open" d="M 448 427 C 470 455 554 455 576 427 C 568 470 460 470 448 427 Z" fill="#5a2f34"/>')
A('<path id="tongue" d="M 476 455 C 495 478 529 478 548 455" fill="none" stroke="#f08ba9" stroke-width="16" stroke-linecap="round"/>')
A('</g>')
A('</g>')

A('</g>')
A('</svg>')

out = Path('/Users/miguelaprossine/octopus-thorvg/octobuss.refmatch.rig.svg')
out.write_text('\n'.join(L) + '\n', encoding='utf-8')
print(out)
