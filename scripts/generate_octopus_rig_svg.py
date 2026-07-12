#!/usr/bin/env python3
from math import cos, sin, sqrt
from pathlib import Path

W, H = 1024, 1024


def lerp(a, b, t):
    return a + (b - a) * t


def bezier_point(p0, p1, p2, p3, t):
    u = 1.0 - t
    return (
        u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
        u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1],
    )


def bezier_tangent(p0, p1, p2, p3, t):
    u = 1.0 - t
    dx = 3 * u * u * (p1[0] - p0[0]) + 6 * u * t * (p2[0] - p1[0]) + 3 * t * t * (p3[0] - p2[0])
    dy = 3 * u * u * (p1[1] - p0[1]) + 6 * u * t * (p2[1] - p1[1]) + 3 * t * t * (p3[1] - p2[1])
    return (dx, dy)


def normalize(vx, vy):
    d = sqrt(vx * vx + vy * vy) or 1.0
    return (vx / d, vy / d)


def tentacle_outline(p0, p1, p2, p3, w0, w1, n=42):
    left = []
    right = []
    centers = []
    normals = []
    for i in range(n + 1):
        t = i / n
        x, y = bezier_point(p0, p1, p2, p3, t)
        tx, ty = bezier_tangent(p0, p1, p2, p3, t)
        tx, ty = normalize(tx, ty)
        nx, ny = -ty, tx
        w = lerp(w0, w1, t)
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
        centers.append((x, y))
        normals.append((nx, ny))
    poly = left + list(reversed(right))
    d = f"M {poly[0][0]:.2f} {poly[0][1]:.2f} " + " ".join([f"L {x:.2f} {y:.2f}" for x, y in poly[1:]]) + " Z"
    return d, centers, normals


def circles_for_suckers(centers, normals, side, count=8):
    out = []
    start, end = int(len(centers) * 0.30), int(len(centers) * 0.90)
    step = max(1, (end - start) // count)
    idx = 0
    for i in range(start, end, step):
        if idx >= count:
            break
        cx, cy = centers[i]
        nx, ny = normals[i]
        r = lerp(10.5, 4.0, idx / max(1, count - 1))
        off = r * 1.25
        out.append((cx + nx * off * side, cy + ny * off * side, r))
        idx += 1
    return out


body_cx, body_cy, body_r = 512, 390, 250

tentacle_specs = [
    # base_x, base_y, c1x, c1y, c2x, c2y, tipx, tipy, w0, w1, underside_side
    (350, 590, 250, 650, 185, 790, 160, 935, 58, 20, -1),
    (410, 610, 330, 680, 285, 820, 300, 970, 56, 18, -1),
    (465, 620, 430, 700, 395, 845, 430, 990, 54, 17, -1),
    (520, 625, 500, 705, 490, 860, 515, 1000, 52, 16, -1),
    (570, 625, 575, 705, 600, 860, 620, 1000, 52, 16, 1),
    (620, 620, 645, 700, 695, 845, 735, 990, 54, 17, 1),
    (675, 610, 735, 680, 785, 820, 810, 970, 56, 18, 1),
    (735, 590, 825, 650, 875, 790, 890, 935, 58, 20, 1),
]

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" preserveAspectRatio="xMidYMid meet">')
svg.append('<defs>')
svg.append('<linearGradient id="bodyGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b881e9"/><stop offset="1" stop-color="#7a49a8"/></linearGradient>')
svg.append('<linearGradient id="bodyShade" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#000" stop-opacity="0.0"/><stop offset="1" stop-color="#000" stop-opacity="0.24"/></linearGradient>')
svg.append('<radialGradient id="bodyHighlight" cx="40%" cy="28%" r="50%"><stop offset="0" stop-color="#ffffff" stop-opacity="0.42"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>')
for i in range(1, 9):
    svg.append(f'<linearGradient id="tentacleGrad{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b176e5"/><stop offset="1" stop-color="#6c3f98"/></linearGradient>')
svg.append('</defs>')

svg.append('<g id="character_octopus">')

# Tentacles (back-to-front order)
for i, spec in enumerate(tentacle_specs, start=1):
    p0 = (spec[0], spec[1])
    p1 = (spec[2], spec[3])
    p2 = (spec[4], spec[5])
    p3 = (spec[6], spec[7])
    w0, w1, side = spec[8], spec[9], spec[10]
    d, centers, normals = tentacle_outline(p0, p1, p2, p3, w0, w1)
    suckers = circles_for_suckers(centers, normals, side)

    svg.append(f'<g id="tentacle_{i:02d}" data-rig="tentacle">')
    svg.append(f'<path id="tentacle_{i:02d}_fill" d="{d}" fill="url(#tentacleGrad{i})"/>')
    svg.append(f'<path id="tentacle_{i:02d}_shadow" d="{d}" fill="#2f1b47" opacity="0.18"/>')

    # Highlight line clipped by shape via duplicate with low-opacity stroke
    c = centers
    pth = f'M {c[0][0]:.2f} {c[0][1]:.2f} ' + ' '.join([f'L {x:.2f} {y:.2f}' for x, y in c[1:]])
    svg.append(f'<path id="tentacle_{i:02d}_highlight" d="{pth}" fill="none" stroke="#ffffff" stroke-opacity="0.22" stroke-width="7" stroke-linecap="round"/>')

    for j, (cx, cy, r) in enumerate(suckers, start=1):
        svg.append(f'<circle id="tentacle_{i:02d}_sucker_{j:02d}" cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="#f6c6df"/>')
        svg.append(f'<circle id="tentacle_{i:02d}_sucker_{j:02d}_core" cx="{cx:.2f}" cy="{cy:.2f}" r="{r*0.42:.2f}" fill="#d98ab2" opacity="0.9"/>')
    svg.append('</g>')

# Body / head / face as separate objects
svg.append('<g id="body">')
svg.append(f'<ellipse id="body_fill" cx="{body_cx}" cy="{body_cy}" rx="{body_r}" ry="{body_r*0.92:.1f}" fill="url(#bodyGrad)"/>')
svg.append(f'<ellipse id="body_shade" cx="{body_cx+35}" cy="{body_cy+35}" rx="{body_r*0.95:.1f}" ry="{body_r*0.84:.1f}" fill="url(#bodyShade)"/>')
svg.append(f'<ellipse id="body_highlight" cx="{body_cx-65}" cy="{body_cy-80}" rx="{body_r*0.58:.1f}" ry="{body_r*0.42:.1f}" fill="url(#bodyHighlight)"/>')
svg.append('</g>')

svg.append('<g id="face">')
svg.append('<ellipse id="eye_l_white" cx="430" cy="360" rx="62" ry="68" fill="#f6fbff"/>')
svg.append('<ellipse id="eye_r_white" cx="594" cy="360" rx="62" ry="68" fill="#f6fbff"/>')
svg.append('<circle id="eye_l_pupil" cx="430" cy="372" r="30" fill="#242633"/>')
svg.append('<circle id="eye_r_pupil" cx="594" cy="372" r="30" fill="#242633"/>')
svg.append('<circle id="eye_l_glint" cx="418" cy="360" r="9" fill="#fff"/>')
svg.append('<circle id="eye_r_glint" cx="582" cy="360" r="9" fill="#fff"/>')
svg.append('<path id="mouth" d="M 455 470 C 490 510 535 510 569 470" fill="none" stroke="#542f73" stroke-width="14" stroke-linecap="round"/>')
svg.append('</g>')

svg.append('</g>')
svg.append('</svg>')

out = Path('/Users/miguelaprossine/octopus-thorvg/octobuss.rig.svg')
out.write_text('\n'.join(svg) + '\n', encoding='utf-8')
print(out)
