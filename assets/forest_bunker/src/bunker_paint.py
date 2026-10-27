"""Painters for the forest_bunker atlases (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
Hangar: board-formed concrete with formwork panels and tie holes, damp at the foot, rime near the gate, water and rust
runs; the floor slab with joints, oil, the yellow taxi line and the main-wheel stop bar; the weathered facade, wing walls
and apron outside (lichen, moss, rust under the top guide's brackets, drift snow on the apron).
HangarParts: the gate leaves in faded olive-grey, rust runs from the ribs, hazard stripes on the meeting stiles, TOR
FREIHALTEN / KEEP CLEAR; grey beams, green enamel shades, safety-yellow railings, the grey side door.
BlastDoor: the vestibule's whitewash over a grey-green dado, wet floor with the door's swing marked in yellow, the ring's
hazard stripes, the grey leaf with rust bleeding from the bolts, red bolts and wheel, chrome rods, colour-coded pipes,
a chequer-plate step, the dark cold tunnel behind.
Entrance: weathered concrete outside, the worn steps, a damp canopy, the dark shaft, rusty ladder, the lid's stencil
NOTAUSSTIEG / EMERGENCY EXIT, the red wheel. Tarp: olive canvas, faded and dusty on top, water stains.
Positions: the roots stand at bunker_kit.DISPLAY while baked."""
import math
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, hash1
from gen_paint import DUST, RUST, RUST_D, _T, _common
import gear_tex as GT
import pxfont as F
import bunker_kit as BK
import bunker_spec as S

CONC, CONC_D, CONC_L = lin(132, 130, 124), lin(86, 86, 84), lin(170, 168, 160)
MOSS, LICHEN, SOIL = lin(70, 84, 46), lin(150, 156, 120), lin(66, 56, 44)
SNOW, SNOW_B, RIME, ICE = lin(236, 240, 244), lin(176, 190, 206), lin(214, 224, 232), lin(196, 218, 232)
OLIVE, OLIVE_F, GREYGREEN = lin(92, 98, 80), lin(132, 136, 116), lin(96, 108, 100)
YELLOW, BLACK, RED, WHITE = lin(214, 170, 36), lin(28, 28, 28), lin(150, 40, 30), lin(226, 228, 220)
STEEL, STEEL_D, CHROME = lin(124, 126, 124), lin(60, 62, 62), lin(196, 198, 200)
DRAFT_COL = {
    BK.Z_HWALL: (132, 130, 124), BK.Z_HFLOOR: (110, 108, 104), BK.Z_HCEIL: (96, 96, 94), BK.Z_HFAC: (150, 148, 140),
    BK.Z_HWING: (140, 138, 130), BK.Z_HAPRON: (120, 118, 112), BK.Z_HHIDE: (50, 50, 50), BK.Z_HPIL: (140, 138, 132),
    BK.Z_HLAND: (124, 122, 116), BK.Z_HSNOW: (236, 240, 244), BK.Z_HICE: (196, 218, 232), BK.Z_HREVEAL: (120, 118, 112),
    BK.Z_HSTUB: (40, 40, 40),
    BK.Z_GLEAF: (92, 98, 80), BK.Z_GLEAFIN: (84, 90, 76), BK.Z_GFRAME: (80, 86, 70), BK.Z_GHAZ: (214, 170, 36),
    BK.Z_GROLL: (50, 50, 50), BK.Z_BEAM: (96, 98, 96), BK.Z_SHADE: (60, 80, 70), BK.Z_SHADEIN: (220, 218, 205),
    BK.Z_ROD: (40, 40, 40), BK.Z_RAIL: (214, 170, 36), BK.Z_TRACK: (90, 70, 56), BK.Z_GUIDE: (84, 90, 76),
    BK.Z_DOOR: (110, 116, 108), BK.Z_DOORFR: (60, 62, 62), BK.Z_HANDLE: (30, 30, 30), BK.Z_CAGE: (30, 30, 30),
    BK.Z_LAMPB: (150, 150, 146), BK.Z_PLATE: (150, 150, 146), BK.Z_VENT: (100, 100, 98),
    BK.Z_VWALL: (200, 200, 192), BK.Z_VFLOOR: (100, 100, 98), BK.Z_VCEIL: (110, 110, 106), BK.Z_VEND: (150, 150, 144),
    BK.Z_VHIDE: (50, 50, 50), BK.Z_RING: (214, 170, 36), BK.Z_LEAF: (120, 124, 118), BK.Z_LEAFRIM: (90, 90, 88),
    BK.Z_HUB: (110, 112, 108), BK.Z_CYL: (70, 72, 72), BK.Z_RODC: (196, 198, 200), BK.Z_DOG: (170, 60, 40),
    BK.Z_WHEEL: (150, 40, 30), BK.Z_HINGE: (60, 60, 60), BK.Z_TUN: (50, 50, 50), BK.Z_VOID: (5, 5, 5),
    BK.Z_PIPE: (80, 110, 80), BK.Z_BRACK: (60, 60, 60), BK.Z_TRAY: (150, 150, 146), BK.Z_CAB: (96, 108, 100),
    BK.Z_CHAN: (70, 70, 68), BK.Z_CHICE: (196, 218, 232), BK.Z_VRAIL: (214, 170, 36), BK.Z_VICE: (196, 218, 232),
    BK.Z_VLAMP: (150, 150, 146), BK.Z_SILL: (120, 122, 120), BK.Z_STEPD: (60, 60, 58),
    BK.Z_EWALL: (140, 138, 130), BK.Z_ESTEP: (128, 126, 120), BK.Z_ETOP: (140, 138, 130), BK.Z_ECEIL: (90, 90, 88),
    BK.Z_EFLOOR: (80, 80, 78), BK.Z_ESHAFT: (70, 70, 68), BK.Z_ELADDER: (110, 70, 44), BK.Z_ERAIL: (88, 104, 92),
    BK.Z_EFRAME: (150, 150, 146), BK.Z_ELID: (96, 108, 100), BK.Z_EWHEEL: (150, 40, 30), BK.Z_EHINGE: (60, 60, 60),
    BK.Z_ESNOW: (236, 240, 244), BK.Z_EHIDE: (50, 50, 50), BK.Z_ELAMP: (150, 150, 146), BK.Z_EOUT: (130, 128, 120),
    BK.Z_TARP: (74, 78, 52), BK.Z_TARPHEM: (60, 62, 42)}


def _local(Pp, root):
    o = BK.DISPLAY[root]
    return Pp[:, 0] - o.x, Pp[:, 1] - o.y, Pp[:, 2] - o.z


def stencil(u, v, txt, cu, cv, px, font=F.F57):
    """texels whose face coordinates (u right, v up, metres) fall on the text centred at (cu, cv); px = one font pixel"""
    m = GT.prop_mask(txt, font, 1)
    h, w = m.shape
    ci = np.floor((u - cu) / px + w / 2.0).astype(np.int64)
    ri = np.floor((cv - v) / px + h / 2.0).astype(np.int64)
    ok = (ci >= 0) & (ci < w) & (ri >= 0) & (ri < h)
    out = np.zeros(len(u), bool)
    out[ok] = m[ri[ok], ci[ok]]
    return out


def hazard(s, t, period=0.25):
    """diagonal yellow / black stripes over face coordinates (s, t): True = black"""
    return (np.floor((s + t) / (period / 2)) % 2) == 1


def concrete(Pp, T, cav, seed, base=CONC):
    c = T(base, 0.14, 0.20)
    c = mixc(c, lin(108, 106, 102), ss(0.60, 0.80, fbm(Pp, 25.0, 1, seed=seed)) * 0.30)
    c = mixc(c, CONC_L, ss(0.76, 0.90, fbm(Pp, 50.0, 1, seed=seed + 1)) * 0.25)
    return mixc(c, CONC_D, cav * 0.35)


def formwork(u, z, aa, pw=1.5, ph=0.75):
    """formwork panel joints and tie holes: (joint mask, tie mask)"""
    j = np.maximum(gline(dist_periodic(u, pw), 0.012, aa), gline(dist_periodic(z, ph), 0.010, aa) * 0.8)
    du, dz = dist_periodic(u - pw / 4, pw / 2), dist_periodic(z - ph / 2, ph)
    tie = 1.0 - ss(0.012 - aa, 0.012 + aa, np.hypot(du, dz))
    return j, tie


def runs(Pp, seed, k=0.1):
    """vertical water / rust runs"""
    return ss(0.58, 0.80, fbm(Pp * np.array([1, 1, k], np.float32), 6.0, 3, seed=seed))


# ================================================================ Hangar (the shell)
def paint_hangar(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 5101)
    T = _T(n_lo, n_hi)
    x, y, z = _local(Pp, 'BunkerHangar')
    H = S.H
    u = np.where(np.abs(Nn[:, 0]) > np.abs(Nn[:, 1]), y, x)
    gate = ss(5.5, 0.8, y)                                        # near the gate: rime, snow blown in
    # ---- walls inside, pilasters, reveals
    for zz, base, seed in ((BK.Z_HWALL, CONC, 5102), (BK.Z_HPIL, lin(140, 138, 132), 5103), (BK.Z_HREVEAL, lin(126, 124, 118), 5104)):
        m = M(zz)
        if not m.any():
            continue
        c = concrete(Pp, T, cav, seed, base)
        j, tie = formwork(u, z, aa)
        c = mixc(c, CONC_D, j * 0.55 + tie * 0.8)
        gr = np.where(m, j * 0.6, gr)
        c = mixc(c, lin(70, 68, 62), ss(0.45, 0.0, z) * 0.55)                               # damp at the foot
        c = mixc(c, lin(92, 88, 80), runs(Pp, seed + 10) * ss(1.0, 6.0, z) * 0.40)
        c = mixc(c, lin(196, 196, 186), ss(0.80, 0.92, fbm(Pp, 4.0, 3, seed=seed + 11)) * ss(0.6, 2.0, z) * 0.35)   # efflorescence
        c = mixc(c, RIME, gate ** 2 * ss(0.50, 0.78, fbm(Pp, 2.0, 3, seed=seed + 12)) * 0.40)
        if zz == BK.Z_HREVEAL:
            c = mixc(c, RUST, runs(Pp, seed + 13, 0.06) * 0.5 * ss(4.6, 5.2, z))
            c = mixc(c, CONC_L, edge * 0.7)
        col[m] = c[m]
    # ---- the floor: slab joints, oil, the taxi line and the stop bar, rime and snow at the gate
    m = M(BK.Z_HFLOOR)
    c = concrete(Pp, T, cav, 5110, lin(118, 116, 110))
    jt = np.maximum(gline(dist_periodic(x, 4.5), 0.012, aa), gline(dist_periodic(y - 0.8, 3.75), 0.012, aa))
    c = mixc(c, lin(60, 58, 54), jt * 0.8)
    gr = np.where(m, jt, gr)
    oil = ss(0.62, 0.76, fbm(Pp, 1.6, 3, seed=5111)) * ss(0.4, 0.8, fbm(Pp, 9.0, 2, seed=5112))
    c = mixc(c, lin(40, 38, 34), oil * 0.75 * ss(2.0, 4.0, y))
    line = (np.abs(x) < 0.07) & (y > 1.2) & (y < 14.6)
    stop = (np.abs(y - (S.PLANE['y_main'] - 0.55)) < 0.08) & (np.abs(x) < 1.6)
    worn = ss(0.3, 0.7, fbm(Pp, 12.0, 2, seed=5113))
    c = np.where(((line | stop) & (worn > 0.25))[:, None], mixc(c, lin(214, 176, 50), np.full(n, 0.85)), c)
    c = mixc(c, lin(70, 70, 70), ss(0.55, 0.75, fbm(Pp, 3.0, 2, seed=5114)) * 0.35)        # wet patches
    c = mixc(c, RIME, gate ** 2 * ss(0.50, 0.75, fbm(Pp, 2.0, 3, seed=5115)) * 0.45)
    c = mixc(c, SNOW, ss(1.4, 0.2, y) * ss(0.45, 0.65, fbm(Pp, 2.5, 3, seed=5116)) * 0.9)
    col[m] = c[m]
    # ---- the ceiling: dark, soot over the lamps, water stains
    m = M(BK.Z_HCEIL)
    c = concrete(Pp, T, cav, 5120, lin(100, 100, 96))
    j, tie = formwork(x, y, aa, 2.4, 1.2)
    c = mixc(c, CONC_D, j * 0.4)
    soot = np.zeros(n, np.float32)
    for lx, ly in H['lamps']:
        soot = np.maximum(soot, ss(0.9, 0.1, np.hypot(x - lx, y - ly)))
    c = mixc(c, lin(40, 38, 36), soot * 0.6)
    c = mixc(c, lin(140, 120, 90), ss(0.70, 0.85, fbm(Pp, 2.0, 3, seed=5121)) * 0.35)
    col[m] = c[m]
    # ---- outside: facade, wing walls, apron
    for zz, seed in ((BK.Z_HFAC, 5130), (BK.Z_HWING, 5131)):
        m = M(zz)
        if not m.any():
            continue
        c = concrete(Pp, T, cav, seed, lin(150, 148, 140))
        along = np.where(zz == BK.Z_HWING, np.hypot(x, y), x)
        j, tie = formwork(along, z, aa, 2.0, 1.0)
        c = mixc(c, CONC_D, j * 0.45 + tie * 0.7)
        gr = np.where(m, j * 0.5, gr)
        c = mixc(c, lin(86, 84, 78), runs(Pp, seed + 1) * 0.55)
        c = mixc(c, LICHEN, ss(0.66, 0.84, fbm(Pp, 4.0, 3, seed=seed + 2)) * 0.45)
        c = mixc(c, MOSS, ss(1.2, 0.0, z) * ss(0.5, 0.7, fbm(Pp, 5.0, 2, seed=seed + 3)) * 0.6)
        c = mixc(c, lin(64, 64, 62), ss(H['z_par'] - 0.8, H['z_par'], z) * 0.45)            # wet under the snow
        if zz == BK.Z_HFAC:
            br = np.zeros(n, np.float32)
            for i in range(15):
                bx = -H['fac_x'] + 0.4 + i * (2 * H['fac_x'] - 0.8) / 14
                g0 = H['guide_z'][0]
                ln = 1.2 + 1.6 * float(hash1(np.float64(i), 77))                # each bracket's run, its own length
                br = np.maximum(br, ss(0.09, 0.03, np.abs(x - bx)) * ss(g0 - ln, g0 - 0.25, z) * (z < g0 + 0.1) *
                                (0.45 + 0.55 * float(hash1(np.float64(i), 78))))
            c = mixc(c, RUST, br * 0.75)
            c = mixc(c, SNOW, up * 0.9)
        col[m] = c[m]
    m = M(BK.Z_HAPRON)
    c = concrete(Pp, T, cav, 5140, lin(128, 126, 120))
    jt = np.maximum(gline(dist_periodic(x, 4.0), 0.014, aa), gline(dist_periodic(y, 3.0), 0.014, aa))
    c = mixc(c, lin(60, 58, 54), jt * 0.7)
    c = mixc(c, RUST, ss(0.25, 0.05, np.abs(y - H['rail_y'])) * 0.45)
    drift = ss(0.40, 0.62, fbm(Pp, 0.9, 3, seed=5141) + ss(0.0, -6.0, y) * 0.25)
    c = mixc(c, SNOW, drift * 0.95 * (Nn[:, 2] > 0.5))
    c = mixc(c, SNOW_B, drift * ss(0.6, 0.8, fbm(Pp, 4.0, 2, seed=5142)) * 0.3 * (Nn[:, 2] > 0.5))
    col[m] = c[m]
    m = M(BK.Z_HHIDE)
    col[m] = T(lin(70, 68, 64), 0.1, 0.1)[m]
    m = M(BK.Z_HSTUB)
    c = concrete(Pp, T, cav, 5150, lin(70, 70, 68))
    col[m] = mixc(c, lin(20, 20, 20), ss(-9.8, -11.0, x))[m]
    # ---- the landing and steps: worn concrete, hazard paint on the risers
    m = M(BK.Z_HLAND)
    c = concrete(Pp, T, cav, 5160, lin(126, 124, 118))
    riser = (Nn[:, 0] > 0.7) & (x > -7.95)
    hz = hazard(y, z, 0.20)
    c = np.where(riser[:, None], np.where(hz[:, None], BLACK, YELLOW) * (0.8 + 0.3 * n_hi)[:, None], c)
    c = mixc(c, lin(150, 148, 142), up * ss(0.5, 0.2, np.abs(y - 2.2)) * 0.35)
    col[m] = mixc(c, CONC_L, edge * 0.5)[m]
    # ---- snow and ice
    m = M(BK.Z_HSNOW)
    c = np.tile(SNOW, (n, 1)) * (0.94 + 0.08 * n_hi)[:, None]
    col[m] = mixc(c, SNOW_B, ss(0.6, 0.2, Nn[:, 2]) * 0.5 + cav * 0.4)[m]
    m = M(BK.Z_HICE)
    c = np.tile(ICE, (n, 1)) * (0.9 + 0.15 * n_hi)[:, None]
    col[m] = mixc(c, WHITE, ss(0.6, 0.9, fbm(Pp, 30.0, 1, seed=5170)) * 0.5)[m]
    return col, gr


# ================================================================ HangarParts
def paint_parts(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 5201)
    T = _T(n_lo, n_hi)
    x, y, z = _local(Pp, 'BunkerHangar')
    H = S.H
    # ---- the gate leaves
    m = M(BK.Z_GLEAF) | M(BK.Z_GLEAFIN) | M(BK.Z_GFRAME)
    c = T(OLIVE, 0.14, 0.12)
    c = mixc(c, OLIVE_F, ss(0.35, 0.75, n_lo) * 0.18 + up * 0.3)
    rib = np.zeros(n, np.float32)
    for zr in (1.55, 2.75, 3.95, 0.25):
        rib = np.maximum(rib, ss(zr - 1.1, zr - 0.05, z) * (z < zr))
    c = mixc(c, RUST, rib * runs(Pp, 5202, 0.05) * 0.8)
    c = mixc(c, RUST_D, ss(0.6, 0.05, z) * ss(0.4, 0.7, fbm(Pp, 6.0, 3, seed=5203)) * 0.8)
    chips = ss(0.84, 0.92, fbm(Pp, 40.0, 2, seed=5204)) * (0.3 + 0.7 * edge)
    c = mixc(c, RUST, chips * 0.8)
    c = mixc(c, RIME, ss(0.6, 0.0, z) * ss(0.45, 0.70, fbm(Pp, 2.5, 2, seed=5205)) * 0.5 * (y < -0.45))
    out = (Nn[:, 1] < -0.7) & M(BK.Z_GLEAF)
    lab = np.zeros(n, bool)
    for cx in (-4.15, 4.15):
        lab |= stencil(x, z, 'TOR FREIHALTEN', cx, 2.30, 0.034, F.F57)
        lab |= stencil(x, z, 'KEEP CLEAR', cx, 1.92, 0.030, F.F57)
    c = mixc(c, lin(222, 222, 210), (lab & out) * 0.85 * ss(0.85, 0.55, fbm(Pp, 12.0, 2, seed=5206)))
    col[m] = c[m]
    m = M(BK.Z_GLEAFIN)
    col[m] = (col * 0.85)[m]
    m = M(BK.Z_GHAZ)
    hz = hazard(x * np.sign(x + 1e-6), z, 0.30)
    c = np.where(hz[:, None], BLACK, YELLOW) * (0.85 + 0.25 * n_hi)[:, None]
    c = mixc(c, RUST, ss(0.80, 0.92, fbm(Pp, 30.0, 2, seed=5207)) * 0.7 + ss(0.5, 0.0, z) * 0.5)
    col[m] = c[m]
    m = M(BK.Z_GROLL)
    c = T(STEEL_D, 0.2, 0.2)
    col[m] = mixc(c, RUST, ss(0.4, 0.75, fbm(Pp, 10.0, 2, seed=5208)) * 0.7)[m]
    # ---- steel: beams, guide, rail, rods, vents
    m = M(BK.Z_BEAM)
    c = T(lin(98, 100, 98), 0.14, 0.16)
    c = mixc(c, RUST, ss(0.70, 0.88, fbm(Pp, 8.0, 3, seed=5210)) * 0.6)
    c = mixc(c, DUST, up * 0.5)
    col[m] = mixc(c, lin(150, 150, 146), edge * 0.4)[m]
    m = M(BK.Z_GUIDE)
    c = T(OLIVE, 0.14, 0.12)
    c = mixc(c, RUST, runs(Pp, 5211, 0.08) * 0.7 + edge * 0.4)
    col[m] = mixc(c, SNOW, up * 0.8)[m]
    m = M(BK.Z_TRACK)
    c = T(lin(90, 70, 56), 0.2, 0.2)
    col[m] = mixc(c, lin(150, 148, 140), up * ss(0.5, 0.7, fbm(Pp, 20.0, 1, seed=5212)) * 0.6)[m]
    m = M(BK.Z_ROD) | M(BK.Z_HANDLE) | M(BK.Z_CAGE)
    c = T(lin(36, 36, 36), 0.2, 0.2)
    col[m] = mixc(c, RUST, ss(0.6, 0.85, fbm(Pp, 20.0, 2, seed=5213)) * 0.5)[m]
    m = M(BK.Z_VENT) | M(BK.Z_PLATE) | M(BK.Z_LAMPB)
    c = T(lin(140, 140, 136), 0.12, 0.14)
    col[m] = mixc(c, RUST, ss(0.7, 0.9, fbm(Pp, 15.0, 2, seed=5214)) * 0.5 + cav * 0.3)[m]
    # ---- lamps: green enamel outside, white inside
    m = M(BK.Z_SHADE)
    c = T(lin(58, 82, 70), 0.1, 0.12)
    c = mixc(c, BLACK, ss(0.85, 0.93, fbm(Pp, 40.0, 2, seed=5215)) * 0.8)
    col[m] = mixc(c, DUST, up * 0.6)[m]
    m = M(BK.Z_SHADEIN)
    c = T(lin(220, 218, 205), 0.06, 0.08)
    col[m] = mixc(c, lin(150, 140, 110), cav * 0.4)[m]
    # ---- railings: safety yellow, worn on the top rail
    m = M(BK.Z_RAIL)
    c = T(YELLOW, 0.1, 0.12)
    c = mixc(c, RUST, ss(0.78, 0.9, fbm(Pp, 25.0, 2, seed=5216)) * 0.6)
    col[m] = mixc(c, lin(130, 128, 120), up * ss(0.4, 0.7, fbm(Pp, 15.0, 2, seed=5217)) * 0.5)[m]
    # ---- the side door and its frame
    m = M(BK.Z_DOOR)
    c = T(lin(110, 116, 108), 0.12, 0.12)
    c = mixc(c, lin(60, 60, 56), ss(0.35, 0.0, np.hypot(y - (H['door_y'] + 0.45), z - (H['door_sill'] + 1.05))) * 0.5)
    c = mixc(c, RUST, ss(0.80, 0.92, fbm(Pp, 30.0, 2, seed=5218)) * 0.6 + edge * 0.3)
    col[m] = c[m]
    m = M(BK.Z_DOORFR)
    c = T(lin(64, 66, 66), 0.15, 0.15)
    col[m] = mixc(c, RUST, edge * 0.5 + ss(0.75, 0.9, fbm(Pp, 20.0, 2, seed=5219)) * 0.4)[m]
    return col, gr


# ================================================================ BlastDoor
def paint_blastdoor(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 5301)
    T = _T(n_lo, n_hi)
    x, y, z = _local(Pp, 'BlastDoor')
    Vv = S.V
    cz = Vv['door_c']
    r = np.hypot(x, z - cz)
    th = np.arctan2(z - cz, x)
    near = ss(4.0, 7.8, y)
    # ---- walls: whitewash over a grey-green dado, damp, frost by the door
    for zz, seed in ((BK.Z_VWALL, 5302), (BK.Z_VEND, 5303)):
        m = M(zz)
        if not m.any():
            continue
        c = concrete(Pp, T, cav, seed, lin(196, 196, 188))
        dado = z < 1.40
        c = np.where(dado[:, None], mixc(T(GREYGREEN, 0.12, 0.12), CONC_D, cav * 0.3), c)
        c = mixc(c, lin(40, 46, 42), (np.abs(z - 1.40) < 0.03) * 0.9)
        u = np.where(np.abs(Nn[:, 0]) > 0.5, y, x)
        j, tie = formwork(u, z, aa, 1.5, 0.75)
        c = mixc(c, CONC_D, (j * 0.35 + tie * 0.5) * (~dado))
        c = mixc(c, lin(120, 110, 90), runs(Pp, seed + 1) * 0.45)
        c = mixc(c, lin(90, 90, 84), ss(0.5, 0.0, z) * 0.5)
        c = mixc(c, RIME, near ** 2 * ss(0.55, 0.80, fbm(Pp, 1.8, 3, seed=seed + 2)) * 0.45)
        col[m] = c[m]
    m = M(BK.Z_VCEIL)
    c = concrete(Pp, T, cav, 5304, lin(150, 150, 144))
    c = mixc(c, lin(90, 84, 70), ss(0.6, 0.8, fbm(Pp, 2.5, 3, seed=5305)) * 0.4)
    col[m] = mixc(c, RIME, near * 0.4)[m]
    # ---- the floor: wet, a puddle at the door, the swing arc in yellow
    m = M(BK.Z_VFLOOR)
    c = concrete(Pp, T, cav, 5306, lin(112, 112, 108))
    wet = np.clip(ss(0.45, 0.70, fbm(Pp, 1.8, 3, seed=5307)) + ss(5.5, 7.6, y) * 0.6, 0, 1)
    c = mixc(c, lin(56, 58, 60), wet * 0.7)
    rp = np.hypot(x - Vv['hinge_x'], y - (Vv['L'] + Vv['hinge_dy']))
    arc = (np.abs(rp - 3.72) < 0.05) & (y < Vv['L'] + Vv['hinge_dy']) & (x > Vv['hinge_x'] - 0.6)
    dash = (np.floor(np.arctan2(y - (Vv['L'] + Vv['hinge_dy']), x - Vv['hinge_x']) / 0.08) % 2) == 0
    c = np.where((arc & dash)[:, None], mixc(c, lin(200, 166, 44), np.full(n, 0.8)), c)
    jt = np.maximum(gline(dist_periodic(x, 2.5), 0.010, aa), gline(dist_periodic(y, 2.0), 0.010, aa))
    c = mixc(c, lin(60, 58, 54), jt * 0.6)
    col[m] = c[m]
    # ---- the ring: hazard stripes on its face, plain dark steel on the bands
    m = M(BK.Z_RING)
    face_ = Nn[:, 1] < -0.7
    s_ = th / (2 * np.pi) * 26.0 + (r - Vv['ring_r'][0]) * 2.5
    blk = (np.floor(s_ * 2) % 2) == 1
    c = np.where(blk[:, None], BLACK, YELLOW) * (0.82 + 0.25 * n_hi)[:, None]
    c = mixc(c, RUST, ss(0.78, 0.90, fbm(Pp, 25.0, 2, seed=5310)) * 0.7)
    c = mixc(c, RIME, ss(0.62, 0.85, fbm(Pp, 2.0, 2, seed=5311)) * 0.30)
    c = np.where(face_[:, None], c, mixc(T(STEEL_D, 0.2, 0.2), RUST, ss(0.5, 0.8, fbm(Pp, 12.0, 2, seed=5312)) * 0.6))
    col[m] = c[m]
    # ---- the leaf, its hub, cylinders, bolts, wheel, hinge
    m = M(BK.Z_LEAF) | M(BK.Z_LEAFRIM) | M(BK.Z_HUB)
    c = T(lin(118, 122, 116), 0.12, 0.14)
    bleed = np.zeros(n, np.float32)
    for i in range(Vv['arms']):
        a = math.pi / 2 + i * 2 * math.pi / Vv['arms']
        bx, bz = 1.40 * math.cos(a), cz + 1.40 * math.sin(a)
        bleed = np.maximum(bleed, ss(0.14, 0.02, np.abs(x - bx)) * ss(bz + 0.05, bz - 0.70, z) * (z < bz + 0.05))
    c = mixc(c, RUST, bleed * 0.8 * (Nn[:, 1] < -0.5))                  # (the bolts are on the front)
    c = mixc(c, RUST_D, ss(0.75, 0.88, fbm(Pp, 10.0, 3, seed=5313)) * 0.5 + edge * 0.3)
    c = mixc(c, lin(90, 94, 90), ss(0.4, 0.8, n_lo) * 0.3)
    c = mixc(c, RIME, ss(0.62, 0.85, fbm(Pp, 2.0, 2, seed=5314)) * 0.25)
    plate = M(BK.Z_LEAF) & (Nn[:, 1] < -0.7) & (np.abs(x + 0.0) < 0.22) & (np.abs(z - (cz - 0.95)) < 0.10)
    c = np.where(plate[:, None], lin(180, 170, 140), c)                        # a riveted maker's plate under the hub
    col[m] = c[m]
    m = M(BK.Z_CYL)
    c = T(lin(70, 74, 74), 0.15, 0.15)
    col[m] = mixc(c, lin(30, 26, 20), ss(0.55, 0.8, fbm(Pp, 12.0, 2, seed=5315)) * 0.6)[m]
    m = M(BK.Z_RODC)
    c = T(CHROME, 0.1, 0.2)
    col[m] = mixc(c, RUST, ss(0.80, 0.92, fbm(Pp, 40.0, 1, seed=5316)) * 0.7)[m]
    m = M(BK.Z_DOG) | M(BK.Z_WHEEL)
    c = T(RED, 0.12, 0.14)
    c = mixc(c, STEEL, edge * 0.7 + ss(0.82, 0.92, fbm(Pp, 30.0, 2, seed=5317)) * 0.6)
    col[m] = mixc(c, RUST, ss(0.7, 0.9, fbm(Pp, 15.0, 2, seed=5318)) * 0.4)[m]
    m = M(BK.Z_HINGE) | M(BK.Z_BRACK)
    c = T(STEEL_D, 0.2, 0.2)
    col[m] = mixc(c, RUST, ss(0.45, 0.8, fbm(Pp, 10.0, 2, seed=5319)) * 0.7)[m]
    # ---- behind the door: dark, frosted; the void
    m = M(BK.Z_TUN) | M(BK.Z_STEPD)
    c = concrete(Pp, T, cav, 5320, lin(78, 78, 76))
    c = mixc(c, lin(18, 18, 18), ss(Vv['L'] + 0.6, Vv['L'] + 3.4, y))
    col[m] = mixc(c, RIME, ss(0.6, 0.85, fbm(Pp, 2.0, 2, seed=5321)) * 0.30 * ss(Vv['L'] + 2.5, Vv['L'] + 0.5, y))[m]
    m = M(BK.Z_VOID)
    col[m] = lin(4, 4, 5)
    # ---- fittings
    m = M(BK.Z_PIPE)
    pc = np.where((np.abs(x - 2.20) < 0.12)[:, None], lin(70, 104, 76), np.where((np.abs(x - 1.92) < 0.09)[:, None],
                  lin(80, 96, 120), lin(150, 46, 36)))
    c = pc * (0.85 + 0.25 * n_hi)[:, None]
    c = mixc(c, RUST, ss(0.75, 0.9, fbm(Pp, 12.0, 2, seed=5322)) * 0.6)
    col[m] = mixc(c, RIME, up * 0.6 + near * 0.3)[m]
    m = M(BK.Z_TRAY) | M(BK.Z_VLAMP)
    c = T(lin(146, 148, 146), 0.1, 0.15)
    col[m] = mixc(c, lin(30, 30, 30), (M(BK.Z_TRAY) & (z > 4.07)) * 0.8)[m]
    m = M(BK.Z_CAB)
    c = T(GREYGREEN, 0.1, 0.12)
    c = mixc(c, RUST, edge * 0.5 + ss(0.82, 0.92, fbm(Pp, 25.0, 2, seed=5323)) * 0.5)
    col[m] = mixc(c, DUST, up * 0.5)[m]
    m = M(BK.Z_CHAN)
    c = concrete(Pp, T, cav, 5324, lin(80, 80, 78))
    col[m] = mixc(c, lin(50, 60, 50), ss(0.5, 0.8, fbm(Pp, 6.0, 2, seed=5325)) * 0.5)[m]
    m = M(BK.Z_CHICE) | M(BK.Z_VICE)
    c = np.tile(ICE, (n, 1)) * (0.88 + 0.16 * n_hi)[:, None]
    crack = gline(dist_periodic(fbm(Pp, 3.0, 2, seed=5326), 0.2), 0.02, 0.01)
    col[m] = mixc(c, WHITE, crack * 0.6 + ss(0.7, 0.9, fbm(Pp, 20.0, 1, seed=5327)) * 0.4)[m]
    m = M(BK.Z_VRAIL)
    c = T(YELLOW, 0.1, 0.12)
    col[m] = mixc(c, RUST, ss(0.76, 0.9, fbm(Pp, 25.0, 2, seed=5328)) * 0.6)[m]
    m = M(BK.Z_SILL)
    chq = (dist_periodic(x + y * 0.0 + z, 0.06) < 0.012) | (dist_periodic(x - z, 0.06) < 0.012)
    c = T(lin(124, 126, 124), 0.12, 0.14)
    c = mixc(c, lin(170, 170, 166), chq * up * 0.6)
    col[m] = mixc(c, RUST, ss(0.6, 0.85, fbm(Pp, 12.0, 2, seed=5329)) * 0.5)[m]
    m = M(BK.Z_VHIDE)
    col[m] = lin(60, 60, 58)
    return col, gr


# ================================================================ Entrance
def paint_entrance(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 5401)
    T = _T(n_lo, n_hi)
    x, y, z = _local(Pp, 'BunkerEntrance')
    E = S.E
    zl = -S.E_DROP
    for zz, seed in ((BK.Z_EWALL, 5402), (BK.Z_ETOP, 5403), (BK.Z_EOUT, 5404)):
        m = M(zz)
        if not m.any():
            continue
        c = concrete(Pp, T, cav, seed, lin(144, 142, 134))
        u = np.where(np.abs(Nn[:, 0]) > 0.5, y, x)
        j, tie = formwork(u, z, aa, 1.2, 0.6)
        c = mixc(c, CONC_D, j * 0.4 + tie * 0.6)
        gr = np.where(m, j * 0.5, gr)
        c = mixc(c, lin(84, 82, 76), runs(Pp, seed + 1) * 0.5)
        c = mixc(c, LICHEN, ss(0.62, 0.82, fbm(Pp, 4.0, 3, seed=seed + 2)) * 0.5 * ss(-2.0, 0.0, z))
        c = mixc(c, MOSS, ss(0.55, 0.75, fbm(Pp, 6.0, 2, seed=seed + 3)) * 0.5 * (ss(0.3, -0.3, z) * (zz == BK.Z_EOUT) +
                                                                                up))
        c = mixc(c, ICE, ss(zl + 0.6, zl + 0.05, z) * ss(0.3, 0.6, fbm(Pp, 8.0, 2, seed=seed + 4)) * 0.6)
        c = mixc(c, SOIL, ss(0.05, -0.3, z) * (zz == BK.Z_EOUT) * 0.8)
        col[m] = c[m]
    m = M(BK.Z_ESTEP)
    c = concrete(Pp, T, cav, 5410, lin(132, 130, 122))
    path = ss(0.55, 0.15, np.abs(x)) * up
    c = mixc(c, lin(160, 158, 150), path * 0.35)
    c = mixc(c, MOSS, ss(0.75, 0.95, np.abs(x)) * up * ss(0.5, 0.7, fbm(Pp, 8.0, 2, seed=5411)) * 0.6)
    c = mixc(c, CONC_L, edge * 0.6)
    c = mixc(c, SNOW, up * ss(-2.0, -0.4, z) * ss(0.45, 0.65, fbm(Pp, 6.0, 2, seed=5412)) * 0.8)
    col[m] = c[m]
    m = M(BK.Z_ECEIL)
    c = concrete(Pp, T, cav, 5413, lin(104, 104, 100))
    c = mixc(c, lin(36, 34, 32), ss(0.8, 0.1, np.hypot(x, y - (E['land_y1'] - 0.1))) * 0.6)
    col[m] = mixc(c, lin(196, 196, 186), ss(0.78, 0.9, fbm(Pp, 6.0, 2, seed=5414)) * 0.4)[m]
    m = M(BK.Z_EFLOOR)
    c = concrete(Pp, T, cav, 5415, lin(96, 96, 92))
    col[m] = mixc(c, lin(50, 52, 54), ss(0.4, 0.7, fbm(Pp, 3.0, 2, seed=5416)) * 0.6)[m]
    m = M(BK.Z_ESHAFT)
    c = concrete(Pp, T, cav, 5417, lin(110, 110, 106))
    c = mixc(c, lin(20, 20, 20), ss(zl, zl - E['shaft_d'], z) * 0.75)
    c = mixc(c, RUST, ss(0.6, 0.85, fbm(Pp * np.array([1, 1, 0.1], np.float32), 8.0, 2, seed=5418)) * 0.4 *
             (np.abs(x) < 0.3) * (y < E['hatch_c'] - E['hatch_in'] + 0.05))
    col[m] = c[m]
    m = M(BK.Z_ELADDER) | M(BK.Z_EHINGE)
    c = T(lin(110, 70, 44), 0.2, 0.2)
    col[m] = mixc(c, RUST_D, ss(0.4, 0.8, fbm(Pp, 12.0, 2, seed=5419)) * 0.7)[m]
    m = M(BK.Z_ERAIL)
    c = T(lin(88, 104, 92), 0.12, 0.12)
    c = mixc(c, RUST, ss(0.6, 0.85, fbm(Pp, 15.0, 2, seed=5420)) * 0.7 + edge * 0.3)
    col[m] = mixc(c, SNOW, up * 0.6)[m]
    m = M(BK.Z_EFRAME)
    c = T(lin(150, 150, 146), 0.12, 0.14)
    col[m] = mixc(c, lin(200, 200, 196), ss(0.7, 0.9, fbm(Pp, 20.0, 2, seed=5421)) * 0.5)[m]
    m = M(BK.Z_ELID)
    c = T(GREYGREEN, 0.12, 0.12)
    c = mixc(c, RUST, ss(0.74, 0.88, fbm(Pp, 14.0, 2, seed=5422)) * 0.7 + edge * 0.3)
    top = Nn[:, 2] > 0.7
    hc = E['hatch_c']
    lab = stencil(x, -(y - hc), 'NOTAUSSTIEG', 0.0, 0.16, 0.018, F.F35) | stencil(x, -(y - hc), 'EMERGENCY EXIT', 0.0, -0.17,
                                                                                    0.016, F.F35)
    c = mixc(c, lin(226, 226, 214), (lab & top) * 0.9)
    col[m] = c[m]
    m = M(BK.Z_EWHEEL)
    c = T(RED, 0.1, 0.12)
    col[m] = mixc(c, STEEL, edge * 0.6 + ss(0.8, 0.92, fbm(Pp, 30.0, 2, seed=5423)) * 0.5)[m]
    m = M(BK.Z_ELAMP)
    col[m] = T(lin(146, 148, 146), 0.1, 0.12)[m]
    m = M(BK.Z_ESNOW)
    c = np.tile(SNOW, (n, 1)) * (0.94 + 0.08 * n_hi)[:, None]
    col[m] = mixc(c, SNOW_B, ss(0.6, 0.2, Nn[:, 2]) * 0.5 + cav * 0.4)[m]
    m = M(BK.Z_EHIDE)
    col[m] = lin(60, 60, 58)
    return col, gr


# ================================================================ Tarp
def paint_tarp(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    M = lambda zz: (Z == zz)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 5501)
    T = _T(n_lo, n_hi)
    weave = (dist_periodic(Pp[:, 0] + Pp[:, 1], 0.03) < 0.008) ^ (dist_periodic(Pp[:, 0] - Pp[:, 1] + Pp[:, 2], 0.03) < 0.008)
    c = T(lin(74, 78, 52), 0.16, 0.14)
    c = mixc(c, lin(62, 66, 44), weave * 0.35)
    c = mixc(c, lin(112, 112, 82), up * (0.35 + 0.3 * n_lo))
    c = mixc(c, DUST, up * ss(0.5, 0.8, fbm(Pp, 3.0, 3, seed=5502)) * 0.45)
    c = mixc(c, lin(46, 48, 34), ss(0.62, 0.80, fbm(Pp, 2.0, 3, seed=5503)) * 0.45)
    patch = (dist_periodic(Pp[:, 0] - 0.4, 2.3) < 0.22) & (dist_periodic(Pp[:, 1] + 0.7, 3.1) < 0.18)
    c = np.where(patch[:, None], c * np.array([0.92, 0.95, 0.84], np.float32), c)
    c = mixc(c, RIME, up * ss(0.6, 0.85, fbm(Pp, 6.0, 2, seed=5504)) * 0.35)
    hem = M(BK.Z_TARPHEM)
    c = np.where(hem[:, None], c * 0.82, c)
    return c, None
