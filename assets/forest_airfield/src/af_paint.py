"""Painters for the forest airfield's atlases (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
Runway: old concrete slabs of a late-60s forest strip left alone since the 80s - each slab its own grey, tyre rubber
along the middle, oil drops, joints dark with moss and weeds, hair cracks, the white paint faded and worn through to
the concrete; the worn module adds old snow in the joints, an asphalt patch and more cracks.
AFProps: grey galvanised stands and lamp bodies, a black cable, concrete pads with moss at the foot, the red-white marker
post, the station pointer (as the hut yard's). AFPlug: newer hollow concrete blocks with grey mortar, damp from below,
lime bloom, a grey-green steel door with rust at the foot.
Positions: the roots stand at af_kit.DISPLAY while baked."""
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, hash1
from gen_paint import DUST, RUST, RUST_D, _T, _common
import gen_kit as K
import af_kit as AK
import pxfont as F

CONC, CONC_D, CONC_L = lin(148, 148, 142), lin(96, 96, 92), lin(176, 174, 166)
RUBBER, OILC, MOSS, MOSS_D, WEED = lin(52, 50, 48), lin(40, 38, 34), lin(70, 86, 40), lin(46, 58, 30), lin(98, 92, 54)
SNOW, SNOW_D, PAINT, ASPH, NEEDLE = lin(206, 210, 214), lin(160, 166, 172), lin(214, 212, 202), lin(46, 46, 46), lin(120, 86, 46)
MUD = lin(92, 78, 60)
GREY_W = lin(132, 126, 112)

DRAFT_COL = {   # sRGB, roughly the painters' base colours (af_build --draft)
    AK.Z_RPLAIN: (148, 148, 142), AK.Z_RWORN: (138, 138, 132), AK.Z_RTHR: (170, 170, 164), AK.Z_RN17: (160, 160, 154),
    AK.Z_RN35: (160, 160, 154), AK.Z_RSKIRT: (100, 96, 90),
    AK.Z_PAD: (140, 138, 132), AK.Z_STAND: (150, 152, 150), AK.Z_LAMPB: (120, 124, 120), AK.Z_CABLE: (24, 24, 24),
    AK.Z_MARK: (200, 60, 50), AK.Z_SPOST: (80, 62, 46), AK.Z_SBOARD: (70, 48, 30),
    AK.Z_BLOCK: (150, 148, 140), AK.Z_PDOOR: (86, 98, 84), AK.Z_PFRAME: (60, 62, 60), K.Z_STEELBLK: (36, 36, 36)}

_NUM = {'17': np.asarray(F.text_mask('17', F.F57, 1), bool), '35': np.asarray(F.text_mask('35', F.F57, 1), bool)}


def _local_rwy(x, y):
    """runway texel -> (module x, module y): the modules stand in a row at af_kit.DISPLAY"""
    i = np.clip(np.round(x / AK.RWY_STEP) + 2, 0, len(AK.RWY) - 1).astype(int)
    offs = np.array([AK.DISPLAY[n].x for n in AK.RWY], np.float32)
    return x - offs[i], y - AK.DISPLAY[AK.RWY[0]].y, i


# ================================================================ Runway
def paint_runway(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    lx, ly, mi = _local_rwy(x, y)
    # each module gets its own noise offset: neighbours in the runway must not repeat the same stains
    Q = Pp + np.stack([mi * 37.0, mi * 11.0, np.zeros(n)], 1).astype(np.float32)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Q, Nn, ao, 2101)
    T = _T(n_lo, n_hi)
    col = np.tile(CONC, (n, 1))
    gr = np.zeros(n, np.float32)
    top = Z != AK.Z_RSKIRT
    worn = (Z == AK.Z_RWORN)
    # ---- the slabs: own tone per slab, stains, tyre rubber in the middle, oil drops
    sx = np.floor((lx + 9.0) / 6.0)
    sy = np.floor((ly + 5.0) / 5.0)
    tone = 0.90 + 0.16 * hash1(sx + sy * 7.0 + mi * 31.0, 5)
    c = T(CONC, 0.16, 0.10) * tone[:, None]
    c = mixc(c, CONC_L, ss(0.55, 0.80, fbm(Q, 0.35, 3, seed=2110)) * 0.35)
    c = mixc(c, CONC_D, ss(0.58, 0.82, fbm(Q, 1.1, 3, seed=2111)) * 0.35)
    tyre = np.exp(-((lx - 2.6) / 1.1) ** 2) + np.exp(-((lx + 2.6) / 1.1) ** 2) + 0.5 * np.exp(-(lx / 1.4) ** 2)
    streak = fbm(Q * np.array([3.0, 0.15, 1.0], np.float32), 1.5, 2, seed=2112)
    c = mixc(c, RUBBER, np.clip(tyre * ss(0.45, 0.75, streak) * 0.45, 0, 0.6))
    oil = ss(0.80, 0.90, fbm(Q, 3.0, 2, seed=2113)) * np.exp(-(lx / 3.0) ** 2)
    c = mixc(c, OILC, oil * 0.6)
    # ---- hair cracks (more on the worn module), the joints with moss and weeds, needles blown in at the edges
    crack_n = fbm(Q * np.array([1.0, 1.0, 1.0], np.float32), 0.7, 3, seed=2120)
    crack = gline(np.abs(crack_n - 0.5), 0.010 + 0.006 * worn, aa) * ss(0.45, 0.75, fbm(Q, 0.5, 2, seed=2121)) * (0.6 + 0.6 * worn)
    c = mixc(c, CONC_D * 0.6, np.clip(crack, 0, 1) * 0.8)
    dj = np.minimum(np.minimum(dist_periodic(lx + 9.0, 6.0), dist_periodic(ly + 5.0, 5.0)), np.minimum(9.0 - np.abs(lx), 5.0 - np.abs(ly)) + 1.0)
    joint = gline(dj, 0.035, aa)
    near = ss(0.35, 0.0, dj)
    weed = ss(0.50, 0.72, fbm(Q, 6.0, 2, seed=2122)) * near
    c = mixc(c, MOSS_D, near * ss(0.40, 0.70, fbm(Q, 2.5, 2, seed=2123)) * 0.55)
    c = mixc(c, WEED, weed * (0.55 + 0.35 * worn))
    c = mixc(c, lin(30, 30, 28), joint * 0.85)
    gr = np.where(top, joint * 0.9, gr)
    side = ss(7.6, 9.0, np.abs(lx))
    c = mixc(c, NEEDLE, side * ss(0.45, 0.75, fbm(Q, 5.0, 2, seed=2124)) * 0.6)
    c = mixc(c, MOSS, side * ss(0.55, 0.80, fbm(Q, 2.0, 2, seed=2125)) * 0.5)
    # ---- paint: the centre-line dash, the threshold, the designators; faded and worn through
    wearp = ss(0.35, 0.75, fbm(Q, 4.0, 3, seed=2130)) * (0.75 + 0.25 * ss(0.3, 0.7, n_hi))
    paint = np.zeros(n, np.float32)
    dash = (np.abs(lx) < 0.45) & (ly < 0.0) & np.isin(Z, (AK.Z_RPLAIN, AK.Z_RWORN))
    paint = np.where(dash, 1.0, paint)
    thr = Z == AK.Z_RTHR
    bar = thr & (ly < -4.25) & (np.abs(lx) < 8.6)
    key = np.zeros(n, bool)
    for i in range(4):
        xc = 1.35 + i * 2.05
        key |= (np.abs(np.abs(lx) - xc) < 0.62) & (ly > -3.7) & (ly < 4.6)
    paint = np.where(thr & (bar | key), 1.0, paint)
    for zz, txt in ((AK.Z_RN17, '17'), (AK.Z_RN35, '35')):
        m = Z == zz
        mk = _NUM[txt]
        h, w = mk.shape
        pix = 0.95
        u = np.floor((lx + w * pix / 2) / pix).astype(int)
        v = np.floor((3.4 - ly) / pix).astype(int)
        inside = m & (u >= 0) & (u < w) & (v >= 0) & (v < h)
        hit = np.zeros(n, bool)
        hit[inside] = mk[v[inside], u[inside]]
        paint = np.where(hit, 1.0, paint)
    pc = mixc(np.tile(PAINT, (n, 1)), CONC_L, np.full(n, 0.25, np.float32)) * (0.92 + 0.10 * (n_hi - 0.5))[:, None]
    pc = mixc(pc, RUBBER, np.clip(tyre * 0.25, 0, 0.3))
    c = mixc(c, pc, paint * (1 - wearp * 0.75) * top)
    # ---- the worn module: an asphalt patch, old snow in the joints and the low corners
    patch = worn & (np.abs(lx - 4.2) < 1.6) & (np.abs(ly - 1.8) < 1.1)
    pa = T(ASPH, 0.2, 0.2)
    pa = mixc(pa, lin(70, 70, 66), ss(0.55, 0.80, fbm(Q, 6.0, 2, seed=2140)) * 0.5)
    c = np.where(patch[:, None], pa, c)
    snow = worn * np.clip(ss(0.55, 0.70, fbm(Q, 0.9, 3, seed=2141)) * (0.35 + 0.65 * near) + side * 0.3 * ss(0.5, 0.7, n_mid), 0, 1)
    sc = mixc(np.tile(SNOW, (n, 1)), SNOW_D, ss(0.4, 0.8, n_hi) * 0.5 + cav * 0.3)
    sc = mixc(sc, DUST, ss(0.55, 0.8, fbm(Q, 8.0, 2, seed=2142)) * 0.35)
    c = mixc(c, sc, ss(0.45, 0.65, snow) * 0.95)
    # ---- the skirt: the slab edge in the ground, dirt and moss up from the bottom
    m = ~top
    zc = z
    s = T(CONC_D * 1.15, 0.16, 0.14)
    s = mixc(s, MUD, ss(-0.05, -0.30, zc) * 0.8)
    s = mixc(s, MOSS_D, ss(0.45, 0.7, fbm(Q, 6.0, 2, seed=2150)) * 0.5)
    c[m] = s[m]
    return c.astype(np.float32), gr


# ================================================================ AFProps
def paint_props(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 2201)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    m = M(AK.Z_PAD)
    c = T(lin(140, 138, 132), 0.18, 0.22)
    c = mixc(c, CONC_D, cav * 0.5 + ss(0.6, 0.85, fbm(Pp, 12.0, 2, seed=2210)) * 0.3)
    c = mixc(c, MOSS, ss(0.0, -0.10, z) * 0.7 + ss(0.65, 0.85, fbm(Pp, 9.0, 2, seed=2211)) * up * 0.4)
    c = mixc(c, RUST_D, ss(0.6, 0.0, ao) * up * 0.25)
    col[m] = c[m]
    for zz, base in ((AK.Z_STAND, lin(150, 152, 150)), (AK.Z_LAMPB, lin(118, 122, 118))):
        m = M(zz)
        c = T(base, 0.14, 0.18)
        c = mixc(c, lin(100, 102, 100), ss(0.55, 0.80, fbm(Pp, 30.0, 2, seed=2220 + zz)) * 0.5)
        c = mixc(c, RUST, ss(0.74, 0.88, fbm(Pp, 50.0, 2, seed=2222 + zz)) * 0.55 + edge * 0.3)
        c = mixc(c, DUST, up * 0.25)
        col[m] = c[m]
    m = M(AK.Z_CABLE)
    col[m] = T(lin(24, 24, 24), 0.1, 0.2)[m]
    # the marker post: red-white-red bands of 0.3 m (red at the top), chipped and dirty at the foot
    m = M(AK.Z_MARK)
    band = np.floor((1.02 - z) / 0.32).astype(int)
    red = (band % 2) == 0
    c = np.where(red[:, None], T(lin(176, 34, 30), 0.14, 0.16), T(lin(220, 220, 212), 0.10, 0.12))
    c = mixc(c, lin(120, 116, 106), edge * 0.6 + ss(0.70, 0.86, fbm(Pp, 40.0, 2, seed=2230)) * 0.5)
    c = mixc(c, MUD, ss(0.30, 0.05, z) * 0.6)
    col[m] = c[m]
    m = M(AK.Z_SPOST)
    g2 = fbm(Pp * np.array([4.0, 4.0, 0.25], np.float32), 10.0, 2, seed=2240)
    c = T(lin(84, 64, 46), 0.16, 0.14) * (0.84 + 0.24 * g2)[:, None]
    c = mixc(c, GREY_W, ss(0.45, 0.80, n_lo) * 0.35)
    c = mixc(c, MOSS_D, ss(0.35, 0.02, z) * 0.7)
    col[m] = c[m]
    m = M(AK.Z_SBOARD)
    c = T(lin(70, 48, 30), 0.14, 0.14)
    c = mixc(c, lin(120, 112, 98), edge * 0.6 + ss(0.6, 0.85, n_lo) * 0.3)
    col[m] = c[m]
    m = M(K.Z_STEELBLK)
    c = T(lin(36, 36, 36), 0.12, 0.2)
    c = mixc(c, RUST, ss(0.55, 0.80, fbm(Pp, 50.0, 2, seed=2250)) * 0.7)
    col[m] = c[m]
    return col, gr


# ================================================================ AFPlug
def paint_plug(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 2301)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    lx = x - AK.DISPLAY['AF_HangarPlug'].x
    # hollow concrete blocks 0.50 x 0.25 in running bond, grey mortar; damp from the floor, lime bloom, dirty hand marks
    m = M(AK.Z_BLOCK)
    row = np.floor(z / 0.25)
    off = (row % 2) * 0.25
    col_i = np.floor((lx + off) / 0.50)
    tone = 0.90 + 0.14 * hash1(col_i * 3.0 + row * 17.0, 9)
    c = T(lin(150, 148, 140), 0.12, 0.18) * tone[:, None]
    jd = np.minimum(dist_periodic(z, 0.25), dist_periodic(lx + off, 0.50))
    mortar = gline(jd, 0.012, aa)
    c = mixc(c, lin(120, 118, 112), mortar * 0.8)
    damp = ss(0.9, 0.05, z) * (0.6 + 0.4 * fbm(Pp, 3.0, 2, seed=2310))
    c = mixc(c, lin(84, 84, 80), damp * 0.6)
    c = mixc(c, lin(196, 196, 186), ss(0.75, 0.88, fbm(Pp, 10.0, 2, seed=2311)) * ss(0.3, 1.0, z) * ss(1.8, 1.0, z) * 0.5)
    c = mixc(c, lin(62, 58, 52), ss(0.80, 0.92, fbm(Pp * np.array([1, 1, 0.2], np.float32), 8.0, 2, seed=2312)) * 0.5)
    col[m] = c[m]
    gr = np.where(m, mortar * 0.8, gr)
    m = M(AK.Z_PDOOR)
    c = T(lin(86, 98, 84), 0.14, 0.14)
    c = mixc(c, lin(130, 134, 120), edge * 0.5)
    c = mixc(c, RUST, ss(0.45, 0.05, z) * ss(0.4, 0.7, fbm(Pp, 20.0, 2, seed=2320)) * 0.8 + ss(0.78, 0.90, fbm(Pp, 30.0, 2, seed=2321)) * 0.4)
    c = mixc(c, lin(50, 48, 44), np.exp(-(((lx - (AK.DOOR['x1'] - 0.12)) / 0.10) ** 2 + ((z - 1.02) / 0.15) ** 2)) * 0.6)
    col[m] = c[m]
    for zz in (AK.Z_PFRAME, K.Z_STEELBLK):
        m = M(zz)
        c = T(lin(56, 58, 56), 0.12, 0.2)
        c = mixc(c, RUST, ss(0.55, 0.80, fbm(Pp, 40.0, 2, seed=2330 + zz)) * 0.6 + ss(0.3, 0.0, z) * 0.4)
        col[m] = c[m]
    return col, gr
