"""Compose game textures from baked helper maps (position / normal / id / AO).
Outputs Unity-ready maps per texture set:
  T_<Set>_BaseColor (sRGB), T_<Set>_Normal (OpenGL, Y+), T_<Set>_MetallicSmoothness (R=metal, A=smooth),
  T_<Set>_Occlusion, T_<Set>_MaskMap (HDRP: R metal, G AO, B detail, A smooth)
"""
import sys, os, time, math
import numpy as np
from scipy import ndimage
from PIL import Image
sys.path.insert(0, '/home/claude/plane')
import plane_geo as G

WORK = '/home/claude/plane/work'
OUT = sys.argv[2] if len(sys.argv) > 2 else '/home/claude/plane/out/Textures'
os.makedirs(OUT, exist_ok=True)
ID = G.ID
T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


# ------------------------------------------------------------------ noise
def _hash(ix, iy, iz, seed):
    h = (ix * np.int64(73856093)) ^ (iy * np.int64(19349663)) ^ (iz * np.int64(83492791)) ^ np.int64(seed * 2654435761 & 0x7fffffff)
    h = (h ^ (h >> np.int64(13))) * np.int64(1274126177)
    h = h ^ (h >> np.int64(16))
    return ((h & np.int64(0xffff)).astype(np.float32)) * np.float32(1.0 / 65535.0)


def vnoise(p, seed=0):
    i = np.floor(p).astype(np.int64)
    f = (p - i).astype(np.float32)
    u = f * f * (3 - 2 * f)
    out = np.zeros(len(p), np.float32)
    for dx in (0, 1):
        wx = u[:, 0] if dx else 1 - u[:, 0]
        for dy in (0, 1):
            wy = u[:, 1] if dy else 1 - u[:, 1]
            for dz in (0, 1):
                wz = u[:, 2] if dz else 1 - u[:, 2]
                out += wx * wy * wz * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fbm(p, freq, octaves=4, seed=0, scale=(1, 1, 1), gain=0.5):
    q = p * (np.asarray(scale, np.float32) * freq)
    tot = np.zeros(len(p), np.float32)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        tot += amp * vnoise(q + np.float32(17.3 * o), seed + o * 101)
        norm += amp
        amp *= gain
        q = q * 2.03
    tot /= norm
    # normalise so thresholds behave the same everywhere: mean 0.5, +-2 sigma -> 0..1
    return np.clip(0.5 + (tot - tot.mean()) / (4 * tot.std() + 1e-6), 0, 1).astype(np.float32)


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    t = t[:, None] if np.ndim(t) == 1 and np.ndim(a) == 2 else t
    return a * (1 - t) + b * t


def C(*rgb):
    return np.array(rgb, np.float32)


# ------------------------------------------------------------------ palette (sRGB)
RED = C(0.60, 0.16, 0.12)
RED_FADE = C(0.70, 0.30, 0.24)
WHITE = C(0.80, 0.78, 0.72)
UNDER = C(0.70, 0.69, 0.65)
ALU = C(0.64, 0.64, 0.62)
PRIMER = C(0.58, 0.58, 0.54)
COWL = C(0.105, 0.11, 0.115)
COWL_PANEL = C(0.30, 0.30, 0.29)
STRUTC = C(0.085, 0.085, 0.09)
RUST = C(0.36, 0.19, 0.09)
RUST_D = C(0.17, 0.10, 0.06)
GRIME = C(0.15, 0.12, 0.09)
DUST = C(0.46, 0.40, 0.32)
SOOT = C(0.035, 0.032, 0.03)
SPIN = C(0.16, 0.34, 0.29)
BLADE = C(0.075, 0.075, 0.075)
YELLOW = C(0.86, 0.64, 0.10)
TIRE = C(0.075, 0.072, 0.068)
MUD = C(0.30, 0.25, 0.19)
HUB = C(0.28, 0.285, 0.29)
CASE = {ID['CASE_Y']: C(0.74, 0.55, 0.17), ID['CASE_G']: C(0.30, 0.36, 0.17),
        ID['CASE_T']: C(0.11, 0.23, 0.23), ID['CASE_D']: C(0.11, 0.11, 0.115)}
INTER = C(0.17, 0.18, 0.16)
EXH = C(0.27, 0.23, 0.20)
BLACK = C(0.02, 0.02, 0.02)
JAMB = C(0.20, 0.20, 0.19)
LOGO_W = C(0.86, 0.85, 0.80)
OR1, OR2, OR3 = C(0.96, 0.62, 0.25), C(0.90, 0.45, 0.12), C(0.62, 0.27, 0.07)

ST = np.array(G.FUS_ST, np.float64)


def fus_fv(P):
    zb = np.interp(P[:, 1], ST[:, 0], ST[:, 2])
    zt = np.interp(P[:, 1], ST[:, 0], ST[:, 3])
    return ((P[:, 2] - zb) / (zt - zb)).astype(np.float32)


def seam(d, width):
    """groove profile for signed distance d to a seam line (meters) -> 0..1"""
    return np.clip(1 - np.abs(d) / width, 0, 1) ** 1.5


def rivet_row(d, s, off=0.024, spacing=0.05, rad=0.0055):
    """rivet domes on both sides of a seam. d: dist to seam, s: coordinate along seam"""
    a = (np.mod(s, spacing) - spacing / 2)
    out = np.zeros_like(d)
    for o in (-off, off):
        r2 = (a * a + (d - o) ** 2) / (rad * rad)
        out = np.maximum(out, np.clip(1 - r2, 0, 1))
    return np.sqrt(out)


def near_lines(v, lines):
    """signed distance from v to the closest value in lines"""
    lines = np.asarray(lines, np.float32)
    d = v[:, None] - lines[None, :]
    k = np.argmin(np.abs(d), axis=1)
    return d[np.arange(len(v)), k]


def rect_outline_dist(u, v, u0, u1, v0, v1, r=0.06):
    """distance to the outline of a rounded rectangle in (u,v)."""
    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    hu, hv = (u1 - u0) / 2 - r, (v1 - v0) / 2 - r
    qu, qv = np.abs(u - cu) - hu, np.abs(v - cv) - hv
    outside = np.sqrt(np.maximum(qu, 0) ** 2 + np.maximum(qv, 0) ** 2)
    inside = np.minimum(np.maximum(qu, qv), 0)
    return np.abs(outside + inside - r)


def poly_inside(x, y, poly):
    """convex polygon (counter-clockwise) point test"""
    m = np.ones(len(x), bool)
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        m &= ((x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)) >= 0
    return m


def logo(P, N):
    """white roundel with an orange isometric crate, both fuselage sides."""
    side = (np.abs(N[:, 0]) > 0.6) & (np.abs(P[:, 0]) > 0.55)
    u = (P[:, 1] + 0.30) * np.sign(P[:, 0])   # keep the icon readable (not mirrored) on the right side
    v = P[:, 2] - 1.80
    r = np.sqrt(u * u + v * v)
    disc = side & (r < 0.215)
    ring = side & (r >= 0.215) & (r < 0.228)
    s = 0.125
    c30 = math.cos(math.radians(30))
    top, ur, lr, bot, ll, ul = (0, s), (s * c30, s / 2), (s * c30, -s / 2), (0, -s), (-s * c30, -s / 2), (-s * c30, s / 2)
    ctr = (0, 0)
    f_top = poly_inside(u, v, [ctr, ur, top, ul])
    f_left = poly_inside(u, v, [ctr, ul, ll, bot])
    f_right = poly_inside(u, v, [ctr, bot, lr, ur])
    # white gaps between cube faces
    gap = (np.abs(u) < 0.006) & (v < 0) & (v > -s)
    gap |= (np.abs(v - np.abs(u) * math.tan(math.radians(30))) < 0.007) & (np.abs(u) < s * c30) & (v > -0.01)
    return disc, ring, f_top & ~gap, f_left & ~gap, f_right & ~gap


# ------------------------------------------------------------------ main compose
def compose(tset):
    log('load', tset)
    pos = np.load(f'{WORK}/{tset}_pos.npy')
    R = pos.shape[0]
    cov = np.load(f'{WORK}/{tset}_cov.npy')
    idx = np.nonzero(cov.ravel())[0]
    P = (pos.reshape(-1, 3)[idx] * 20 - 10).astype(np.float32)
    del pos
    N = np.load(f'{WORK}/{tset}_nrm.npy').reshape(-1, 3)[idx] * 2 - 1
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-6)
    N = N.astype(np.float32)
    mid = np.rint(np.load(f'{WORK}/{tset}_id.npy').ravel()[idx] * 64).astype(np.int32)
    ao_raw = np.load(f'{WORK}/{tset}_ao.npy')
    aocov = ao_raw[..., 3] > 0.5
    ind = ndimage.distance_transform_edt(~aocov, return_distances=False, return_indices=True)
    ao_small = ao_raw[..., 0][tuple(ind)]
    ao_full = ndimage.zoom(ao_small, R / ao_small.shape[0], order=1)
    AO = np.clip(ao_full.ravel()[idx], 0, 1).astype(np.float32)
    del ao_raw, ind, ao_small, ao_full
    M = len(idx)
    log(f'{tset}: {R}px, {M} covered texels, ids {np.unique(mid)}')

    col = np.zeros((M, 3), np.float32)
    metal = np.zeros(M, np.float32)
    rough = np.full(M, 0.6, np.float32)
    height = np.zeros(M, np.float32)      # metres
    paintable = np.zeros(M, bool)         # gets chipping / wear

    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    ax = np.abs(x)
    # shared noises
    n_lo = fbm(P, 1.2, 3, seed=1)
    n_mid = fbm(P, 5.0, 4, seed=2)
    n_hi = fbm(P, 22.0, 3, seed=3)
    log('noise base')

    # ---------------- airframe paint
    fus = mid == ID['FUS']
    if fus.any():
        fv = fus_fv(P)
        cowl = fus & (y < -1.05)
        body = fus & ~cowl
        c = np.tile(RED, (M, 1))
        stripe = (fv > 0.285) & (fv < 0.415)
        cross = (y > 4.25) & (y < 4.60)
        c[stripe | cross] = WHITE
        belly = fv < 0.075
        c[belly] = UNDER
        # inner face of the cargo door (points into the cabin when closed)
        door_in = (x > 0.5) & (N[:, 0] < -0.5) & (y > G.DOOR['y0'] - 0.02) & (y < G.DOOR['y1'] + 0.02)
        c[door_in] = JAMB
        disc, ring, ft, fl, fr = logo(P, N)
        c[disc] = LOGO_W
        c[ring] = C(0.2, 0.2, 0.2)
        c[ft], c[fl], c[fr] = OR1, OR2, OR3
        # cowl: dark paint + grey access panels
        cc = np.tile(COWL, (M, 1))
        pan = (y > -2.30) & (y < -1.62) & (fv > 0.38) & (fv < 0.82) & (ax > 0.4)
        cc[pan] = COWL_PANEL
        c = np.where(cowl[:, None], cc, c)
        col[fus] = c[fus]
        rough[fus] = 0.62
        paintable |= fus & ~door_in
        # ---- panel seams & rivets (fuselage)
        ylines = [-1.05, -0.54, 0.35, 1.20, 2.90, 3.80, 4.25, 4.60, 5.40, 6.15]
        dy = near_lines(y, ylines)
        fvline = near_lines(fv, [0.08, 0.60, 0.93])
        around = z + ax    # ~arc length around the boxy section
        hseam = seam(dy, 0.004) * body
        hseam = np.maximum(hseam, seam(fvline * 1.5, 0.004) * body)
        riv = rivet_row(dy, around, off=0.022, spacing=0.05) * body
        riv = np.maximum(riv, rivet_row(fvline * 1.5, y, off=0.022, spacing=0.05) * body)
        # pilot / passenger doors outline, both sides
        side = body & (ax > 0.55) & (np.abs(N[:, 0]) > 0.5)
        dd = rect_outline_dist(y, z, -0.52, 0.36, 1.29, 2.62, r=0.07)
        hseam = np.maximum(hseam, seam(dd, 0.005) * side)
        handle = side & (np.abs(y - 0.24) < 0.06) & (np.abs(z - 1.78) < 0.012)
        height[handle] += 0.002
        # small inspection hatches
        for (yc, zc) in ((5.0, 1.95), (1.55, 1.55)):
            dd2 = rect_outline_dist(y, z, yc - 0.15, yc + 0.15, zc - 0.11, zc + 0.11, r=0.03)
            hseam = np.maximum(hseam, seam(dd2, 0.004) * side * (np.sign(x) < 0 if yc < 2 else True))
        # cowl seams + latches
        cyl = near_lines(y, [-2.35, -1.62, -1.10])
        hseam = np.maximum(hseam, seam(cyl, 0.005) * cowl)
        hseam = np.maximum(hseam, seam((fv - 0.62) * 1.2, 0.005) * cowl)
        for yl in (-2.05, -1.40):
            lat = cowl & (np.abs(y - yl) < 0.05) & (np.abs(fv - 0.62) * 1.2 < 0.02)
            height[lat] += 0.0025
        height -= hseam * 0.0008
        height += riv * 0.0007
        # oil-can dents on skin panels
        height += (fbm(P, 2.5, 2, seed=9) - 0.5) * 0.0012 * body
        # exhaust soot streaks flowing aft
        t = np.clip((y + 1.55) / 2.6, 0, 1)
        zc = 1.97 - 0.10 * t
        soot = np.exp(-((z - zc) / (0.10 + 0.12 * t)) ** 2) * (1 - t) ** 1.3 * (y > -1.62) * (ax > 0.45)
        soot *= 0.6 + 0.6 * fbm(P, 3, 3, seed=11, scale=(3, 0.3, 3))
        col[fus] = mix(col[fus], SOOT, np.clip(soot[fus] * 1.2, 0, 0.92))
        rough[fus] += soot[fus] * 0.2
        # oil drips below the cowl
        oil = cowl * (fv < 0.35) * sstep(0.55, 0.8, fbm(P, 4, 3, seed=12, scale=(2, 0.4, 5)))
        col = mix(col, C(0.05, 0.045, 0.04), oil * 0.7)
        rough -= oil * 0.25

    wing = mid == ID['WING']
    if wing.any():
        top = N[:, 2] > -0.25
        c = np.tile(RED, (M, 1))
        white = ((ax > 0.68) & (ax < 1.35)) | ((ax > 2.60) & (ax < 4.45))
        c[top & white] = WHITE
        c[~top] = UNDER
        c[~top & (ax > 6.30)] = RED
        c[(ax > 6.55) & (np.abs(N[:, 0]) > 0.7)] = RED
        col[wing] = c[wing]
        rough[wing] = 0.62
        paintable |= wing
        cf = (y - G.WING_LE) / G.WING_CHORD
        xl = near_lines(ax, [0.68, 1.35, 2.0, 2.6, 3.4, 4.45, 5.3, 6.06])
        cl = near_lines(cf, [0.14, 0.45]) * G.WING_CHORD
        hs = np.maximum(seam(xl, 0.004), seam(cl, 0.004) * (cf < 0.70))
        rv = np.maximum(rivet_row(xl, y, spacing=0.05), rivet_row(cl, ax, spacing=0.05) * (cf < 0.70))
        # stiffening ribs on flaps / ailerons
        csurf = cf > 0.70
        rib = seam(near_lines(ax, list(np.arange(0.9, 6.1, 0.22))), 0.008) * csurf
        height[wing] += (-hs * 0.0008 + rv * 0.0007 + rib * 0.0006)[wing]
        height[wing] += ((fbm(P, 2.2, 2, seed=19) - 0.5) * 0.001)[wing]

    stab = mid == ID['STAB']
    if stab.any():
        top = N[:, 2] > -0.25
        c = np.tile(RED, (M, 1))
        c[top & (ax > 0.85) & (ax < 1.05)] = WHITE
        c[~top] = UNDER
        c[~top & (ax > 2.42)] = RED
        col[stab] = c[stab]
        rough[stab] = 0.62
        paintable |= stab
        cf = (y - G.STAB['le']) / (G.STAB['te'] - G.STAB['le'])
        xl = near_lines(ax, [0.23, 0.85, 1.05, 1.75])
        cl = near_lines(cf, [0.22]) * 1.4
        hs = np.maximum(seam(xl, 0.004), seam(cl, 0.004))
        rv = np.maximum(rivet_row(xl, y), rivet_row(cl, ax))
        height[stab] += (-hs * 0.0008 + rv * 0.0007)[stab]

    fin = mid == ID['FIN']
    if fin.any():
        c = np.tile(RED, (M, 1))
        c[((z > 2.80) & (z < 3.00)) | ((z > 3.36) & (z < 3.43))] = WHITE
        col[fin] = c[fin]
        rough[fin] = 0.62
        paintable |= fin
        zl = near_lines(z, [2.80, 3.00, 3.36, 3.43, 2.5])
        hs = seam(zl, 0.004)
        rv = rivet_row(zl, y)
        height[fin] += (-hs * 0.0008 + rv * 0.0007)[fin]

    strut = mid == ID['STRUT']
    col[strut] = STRUTC
    rough[strut] = 0.55
    paintable |= strut

    exh = mid == ID['EXHAUST']
    if exh.any():
        heat = fbm(P, 9, 3, seed=21)
        c = mix(np.tile(EXH, (M, 1)), C(0.30, 0.22, 0.30), sstep(0.5, 0.8, heat) * 0.5)
        c = mix(c, SOOT, sstep(0.35, 0.7, n_mid) * 0.6)
        col[exh] = c[exh]
        metal[exh] = 0.75
        rough[exh] = 0.55
    col[mid == ID['INTAKE']] = BLACK
    rough[mid == ID['INTAKE']] = 0.8
    jb = mid == ID['JAMB']
    col[jb] = JAMB
    rough[jb] = 0.7
    paintable |= jb

    # ---------------- details
    sp = mid == ID['SPINNER']
    if sp.any():
        col[sp] = SPIN
        rough[sp] = 0.42
        paintable |= sp
        dd = np.sqrt(x * x + (z - G.PROP_C.z) ** 2)
        height[sp] -= (seam(y + 2.86, 0.004) * 0.0008)[sp]
    bl = mid == ID['BLADE']
    if bl.any():
        r = np.sqrt(x * x + (z - G.PROP_C.z) ** 2)
        c = np.tile(BLADE, (M, 1))
        c[r > G.PROP_R - 0.13] = YELLOW
        c[(r > G.PROP_R - 0.27) & (r < G.PROP_R - 0.24)] = YELLOW
        col[bl] = c[bl]
        rough[bl] = 0.5
        paintable |= bl
    tire = mid == ID['TIRE']
    if tire.any():
        c = np.tile(TIRE, (M, 1))
        # mud in grooves (low AO) and on the lower half / sidewall rim
        mud = np.clip((1 - AO) * 1.6, 0, 1) * 0.8 + sstep(0.55, 0.8, fbm(P, 8, 4, seed=31)) * 0.6
        c = mix(c, MUD, np.clip(mud, 0, 0.85))
        c = mix(c, C(0.11, 0.105, 0.1), sstep(0.3, 0.7, n_hi) * 0.3)
        col[tire] = c[tire]
        rough[tire] = np.clip(0.82 + mud * 0.12, 0, 1)[tire]
        height[tire] += ((fbm(P, 60, 2, seed=33) - 0.5) * 0.0008 + (sstep(0.6, 0.75, fbm(P, 10, 3, seed=34))) * 0.0015)[tire]
    hub = mid == ID['HUB']
    if hub.any():
        col[hub] = HUB
        metal[hub] = 0.35
        rough[hub] = 0.5
        paintable |= hub
    inter = mid == ID['INTERIOR']
    if inter.any():
        c = np.tile(INTER, (M, 1))
        floor = inter & (N[:, 2] > 0.7)
        # diamond tread plate on the floor
        a1 = (x + y) * 18.0
        a2 = (x - y) * 18.0
        cell = (np.abs(np.mod(a1, 1) - 0.5) < 0.12) & (np.abs(np.mod(a2 * 3, 1) - 0.5) < 0.35)
        cell2 = (np.abs(np.mod(a2, 1) - 0.5) < 0.12) & (np.abs(np.mod(a1 * 3, 1) - 0.5) < 0.35)
        height[floor & (cell | cell2)] += 0.0012
        c[floor] = C(0.33, 0.33, 0.32)
        metal[floor] = 0.8
        rough[floor] = 0.45
        col[inter] = c[inter]
        rough[inter & ~floor] = 0.8
        paintable |= inter & ~floor
    for cid, cc in CASE.items():
        m = mid == cid
        if m.any():
            col[m] = cc
            rough[m] = 0.5
            paintable |= m
            # moulded ribs around the case
            zz = near_lines(np.mod(z - 1.30, 0.09), [0.045])
            height[m] -= (seam(zz, 0.004) * 0.0006)[m]
    cm = mid == ID['CASE_M']
    col[cm] = C(0.55, 0.55, 0.54)
    metal[cm] = 1.0
    rough[cm] = 0.38
    log('base paint')

    # ---------------- wear: chips, scratches, grime, dust, rust
    # edge exposure: leading edges (face forward), lower fuselage, door/panel edges
    fwd = np.clip(-N[:, 1], 0, 1)
    exposure = 0.10 + 0.35 * sstep(0.55, 0.95, fwd) + 0.12 * sstep(0.55, 0.2, AO)
    exposure += 0.10 * (z < 1.55) * (mid == ID['FUS'])
    exposure += 0.18 * (mid == ID['STRUT']) + 0.10 * (mid == ID['HUB'])
    exposure -= 0.06 * np.isin(mid, list(CASE)).astype(np.float32)
    chipn = fbm(P, 7.0, 5, seed=41) * 0.75 + n_hi * 0.25
    chip = sstep(1.0 - exposure, 1.0 - exposure + 0.03, chipn) * paintable
    chip_core = sstep(1.0 - exposure * 0.55, 1.0 - exposure * 0.55 + 0.02, chipn) * paintable
    # what is under the paint
    red_like = np.isin(mid, [ID['FUS'], ID['WING'], ID['STAB'], ID['FIN'], ID['JAMB']])
    under = np.where(red_like[:, None], np.tile(PRIMER, (M, 1)), np.tile(C(0.42, 0.42, 0.41), (M, 1)))
    col = mix(col, under, chip * 0.9)
    rough = rough * (1 - chip) + 0.7 * chip
    bare = chip_core * red_like
    col = mix(col, ALU, bare)
    metal = np.maximum(metal, bare * 0.95)
    rough = rough * (1 - bare) + 0.42 * bare
    height -= chip * 0.00012
    # rust on steel parts and in deep chips on painted metal
    rustn = fbm(P, 11, 4, seed=51)
    steel = np.isin(mid, [ID['STRUT'], ID['HUB'], ID['EXHAUST'], ID['CASE_M']])
    rustm = (sstep(0.62, 0.72, rustn) * (chip + 0.25 * (1 - AO)) * steel + chip_core * sstep(0.6, 0.7, rustn) * 0.8)
    rustm = np.clip(rustm, 0, 1)
    col = mix(col, mix(np.tile(RUST, (M, 1)), RUST_D, n_hi), rustm)
    metal *= (1 - rustm)
    rough = rough * (1 - rustm) + 0.9 * rustm
    # sun-faded paint on upward faces
    fade = sstep(0.3, 0.9, N[:, 2]) * red_like * (0.25 + 0.3 * n_lo)
    col = mix(col, col * 0.6 + RED_FADE * 0.4, fade * (col[:, 0] > col[:, 1] * 2))
    # large-scale colour variation
    col *= (0.92 + 0.16 * n_lo)[:, None]
    # flow streaks (aft) on airframe, gravity streaks on vertical faces
    flow = fbm(P, 3.0, 4, seed=61, scale=(3.0, 0.25, 3.0))
    drip = fbm(P, 3.0, 4, seed=62, scale=(3.0, 3.0, 0.25))
    vert = 1 - np.abs(N[:, 2])
    streak = sstep(0.55, 0.85, flow) * 0.35 + sstep(0.58, 0.85, drip) * vert * 0.35
    air = paintable & ~np.isin(mid, list(CASE) + [ID['INTERIOR'], ID['SPINNER'], ID['BLADE']])
    col = mix(col, GRIME, streak * air * 0.8)
    # cavity grime from AO + general dirt
    cav = np.clip((1 - AO) * 1.25, 0, 1) ** 1.3
    dirt = cav * 0.7 + sstep(0.5, 0.85, n_mid) * 0.25
    col = mix(col, GRIME, np.clip(dirt, 0, 0.85) * (mid != ID['INTAKE']))
    rough = np.clip(rough + dirt * 0.18, 0, 1)
    # dust & dried mud on the lower airframe and gear
    low = sstep(1.7, 0.6, z) * (N[:, 2] < 0.6) * (mid != ID['TIRE'])
    low = np.maximum(low, (mid == ID['STRUT']) * sstep(1.4, 0.3, z))
    dust = low * sstep(0.35, 0.75, fbm(P, 4.0, 4, seed=71)) * (mid != ID['INTERIOR'])
    col = mix(col, DUST, dust * 0.75)
    rough = np.clip(rough + dust * 0.25, 0, 1)
    metal *= (1 - dust)
    # fine scratches (fore-aft) on painted skin
    scr = sstep(0.83, 0.9, fbm(P, 30, 2, seed=81, scale=(1.0, 0.04, 1.0))) * red_like * sstep(0.45, 0.7, n_mid)
    col = mix(col, PRIMER, scr * 0.6)
    # soft AO baked lightly into albedo
    col *= (0.55 + 0.45 * AO)[:, None]
    log('wear')

    # ------------------------------------------------------------ write images
    def full(vals, ch, fill=0.0):
        out = np.full((R * R, ch), fill, np.float32)
        out[idx] = vals.reshape(len(idx), ch)
        return out.reshape(R, R, ch)

    # dilate into gutters (nearest covered texel)
    ind = ndimage.distance_transform_edt(~cov, return_distances=False, return_indices=True)
    def dil(img):
        return img[ind[0], ind[1]]

    col_i = dil(full(np.clip(col, 0, 1), 3))
    met_i = dil(full(np.clip(metal, 0, 1), 1))[..., 0]
    smo_i = dil(full(np.clip(1 - rough, 0, 1), 1))[..., 0]
    ao_i = dil(full(AO, 1, 1.0))[..., 0]
    # normal from height: derivative along u (columns) and v (rows) in metres of surface
    H = full(height, 1)[..., 0]
    Pf = full(P, 3)
    covf = cov.astype(np.float32)

    def deriv(A, axis):
        fwd_ = np.roll(A, -1, axis=axis); bwd_ = np.roll(A, 1, axis=axis)
        cf = np.roll(covf, -1, axis=axis); cb = np.roll(covf, 1, axis=axis)
        return fwd_, bwd_, cf, cb

    nxy = []
    for axis in (1, 0):   # u then v
        Hf, Hb, cf, cb = deriv(H, axis)
        Pfw, Pbw = np.roll(Pf, -1, axis=axis), np.roll(Pf, 1, axis=axis)
        Hf = np.where(cf > 0, Hf, H); Hb = np.where(cb > 0, Hb, H)
        dist = np.linalg.norm(np.where(cf[..., None] > 0, Pfw, Pf) - np.where(cb[..., None] > 0, Pbw, Pf), axis=-1)
        g = np.where(dist > 1e-6, (Hf - Hb) / np.maximum(dist, 1e-6), 0.0)
        nxy.append(np.clip(g, -3, 3))
    nx, ny = -nxy[0], -nxy[1]
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nrm = np.stack([nx / ln, ny / ln, nz / ln], -1) * covf[..., None] + (1 - covf[..., None]) * np.array([0, 0, 1], np.float32)
    nrm = dil(nrm)
    del Pf, H
    log('normal')

    def save(arr, name, mode, jpg=False):
        a8 = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)[::-1]   # Blender row 0 = bottom
        im = Image.fromarray(a8, mode)
        path = f'{OUT}/T_{tset}_{name}.' + ('jpg' if jpg else 'png')
        if jpg:
            im.save(path, quality=95, subsampling=0)
        else:
            im.save(path, optimize=True)
        log('  saved', os.path.basename(path), f'{os.path.getsize(path) / 1e6:.1f} MB')

    save(col_i, 'BaseColor', 'RGB')
    save(nrm * 0.5 + 0.5, 'Normal', 'RGB')
    ms = np.stack([met_i, met_i, met_i, smo_i], -1)
    save(ms, 'MetallicSmoothness', 'RGBA')
    save(ao_i, 'Occlusion', 'L')
    mask = np.stack([met_i, ao_i, np.zeros_like(ao_i), smo_i], -1)
    save(mask, 'MaskMap', 'RGBA')


if __name__ == '__main__':
    for s in sys.argv[1].split(','):
        compose(s)
