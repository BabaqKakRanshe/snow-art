"""Painters for the hut yard's atlases (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
The hut's own finish (dark stained boards, white trims) and the generator shed's wear language: faded faces to the weather,
grey wood low down, moss and splashes at the foot, rust runs and needles on the roofs; silver-grey weathered boards on the
feeder and the porch; spruce logs with bark, moss and needles, end grain with rings, cracks and the sprayed number 317.
YardProps: the pointer's post and board, the battery lantern's green body and its wire.
Positions: the roots stand at yard_kit.DISPLAY while baked."""
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, boards, hash1
from gen_paint import DUST, RUST, RUST_D, _T, _common, run_m
import gen_kit as K
import yard_kit as YK
import pxfont as F
import yard_tex                                        # noqa: F401 - patched glyphs (umlauts, m)

STAIN, STAIN_FADE, STAIN_GREY, STAIN_STREAK = lin(62, 46, 34), lin(118, 102, 84), lin(112, 108, 100), lin(36, 28, 22)
MOSS, MOSS_D, NEEDLE_A, NEEDLE_B, LEAF = lin(70, 86, 40), lin(46, 58, 30), lin(132, 92, 46), lin(96, 70, 40), lin(150, 96, 44)
GREY_W, GREY_D, LICHEN = lin(132, 126, 112), lin(82, 78, 70), lin(150, 156, 120)
BARK, BARK_D, BARK_L = lin(92, 72, 56), lin(56, 44, 36), lin(130, 112, 92)
END_L, END_D, SPRAY = lin(190, 156, 110), lin(140, 104, 70), lin(196, 40, 30)
MUD = lin(92, 78, 60)
OD = YK.DISPLAY['HutOuthouse']
PD = YK.DISPLAY['HutPolter']

DRAFT_COL = {   # sRGB, roughly the painters' base colours (yard_build --draft)
    K.Z_SLAB: (132, 130, 124), K.Z_TRIMW: (200, 196, 182), K.Z_TIMBER: (150, 118, 78), K.Z_ROOF: (150, 154, 150),
    K.Z_ROOFUNDER: (118, 120, 116), K.Z_STEELBLK: (36, 36, 36),
    YK.Z_DARK: (62, 46, 34), YK.Z_ODOOR: (62, 46, 34), YK.Z_ODOORIN: (120, 98, 74), YK.Z_ILIN: (110, 90, 66), YK.Z_SEATB: (150, 120, 84),
    YK.Z_GREY: (132, 126, 112), YK.Z_BARK: (92, 72, 56), YK.Z_END: (190, 156, 110), YK.Z_HAY: (170, 150, 90), YK.Z_STONE: (120, 118, 112),
    YK.Z_SPOST: (80, 62, 46), YK.Z_SBOARD: (70, 48, 30), YK.Z_LMETAL: (40, 64, 44), YK.Z_LWIRE: (30, 30, 30)}

_MASK = np.asarray(F.text_mask('317', F.F57, 1), bool)          # the sprayed number on the polter's road end


def _litter(Pp, up, seed, amount=1.0):
    """needles and leaves on the surfaces that face up: (mask 0..1, colour)"""
    x, y = Pp[:, 0], Pp[:, 1]
    m = (ss(0.52, 0.72, fbm(Pp, 5.0, 3, seed=seed)) * 0.7 + ss(0.62, 0.80, fbm(Pp, 30.0, 1, seed=seed + 1)) * 0.6) * up * amount
    pick = hash1(np.floor(x * 53.0) + np.floor(y * 47.0) * 13.0, seed)
    c = np.where((pick > 0.70)[:, None], LEAF, np.where((pick > 0.35)[:, None], NEEDLE_A, NEEDLE_B))
    return np.clip(m, 0, 1), c


def _heart(u, v):
    """inside the heart cut (u across, v up, both in heart radii; lobes up)"""
    X, Y = u, v
    return (X * X + Y * Y - 1.0) ** 3 - X * X * Y ** 3 <= 0.0


# ================================================================ YardWood
def paint_wood(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 1301)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    streak = ss(0.55, 0.80, fbm(Pp * np.array([1, 1, 0.12], np.float32), 6.0, 3, seed=1311))
    lit, lit_c = _litter(Pp, up, 1312)
    ox, oy = x - OD.x, y - OD.y
    zf = z - YK.OFL
    weather = np.where(Nn[:, 1] < -0.5, 1.0, np.where(Nn[:, 0] > 0.5, 0.7, 0.45))
    # ---- the outhouse: dark stained board-and-batten (the hut's finish)
    m = M(YK.Z_DARK)
    fb = np.abs(Nn[:, 1]) > 0.5
    s_wall = np.where(fb, ox, oy)
    bi, seam = boards(s_wall, 0.15, aa, 0.004)
    bat = 1 - ss(0.02 - aa, 0.02 + aa, dist_periodic(s_wall, 0.15))
    c = STAIN * (0.88 + 0.18 * hash1(bi + 5.0 * fb, 3))[:, None] * (0.86 + 0.20 * (n_lo - 0.5) + 0.10 * (n_hi - 0.5))[:, None]
    c = mixc(c, STAIN_FADE, weather * ss(0.30, 0.70, n_lo) * 0.40)
    grey = ss(0.58, 0.80, fbm(Pp * np.array([1, 1, 0.3], np.float32), 14.0, 3, seed=1314)) * (0.35 + 0.65 * ss(0.7, 0.10, zf))
    c = mixc(c, STAIN_GREY, grey * (0.45 + 0.35 * weather))
    c = mixc(c, STAIN_STREAK, streak * 0.40)
    c = mixc(c, MOSS_D, ss(0.40, 0.02, zf) * ss(0.45, 0.70, fbm(Pp, 12.0, 2, seed=1315)) * 0.8)
    c = mixc(c, lin(56, 50, 42), ss(0.40, 0.06, zf) * 0.45)
    c = c * (1 - 0.10 * bat * ss(0.3, 0.9, n_mid))[:, None] * (1 + 0.08 * bat)[:, None]
    col[m] = c[m]
    edge_b = np.maximum(gline(dist_periodic(s_wall - 0.02, 0.15), 0.006, aa), gline(dist_periodic(s_wall + 0.02, 0.15), 0.006, aa))
    gr = np.where(m, edge_b * 0.8, gr)
    # ---- the door: stained boards, worn at the button and the foot, the heart cut (dark: through the boards)
    lx = ox
    for zz, base in ((YK.Z_ODOOR, STAIN), (YK.Z_ODOORIN, lin(120, 98, 74))):
        m = M(zz)
        bi, seam = boards(lx, 0.11, aa, 0.004)
        c = base * (0.88 + 0.18 * hash1(bi, 7 + zz))[:, None] * (0.86 + 0.18 * (n_lo - 0.5) * 2)[:, None]
        if zz == YK.Z_ODOOR:
            c = mixc(c, STAIN_FADE, ss(0.30, 0.70, n_lo) * 0.4)
            c = mixc(c, STAIN_GREY, ss(0.58, 0.82, fbm(Pp * np.array([1, 1, 0.3], np.float32), 14.0, 3, seed=1320)) * ss(0.8, 0.15, zf) * 0.8)
            c = mixc(c, lin(40, 32, 26), np.exp(-(((lx - 0.28) / 0.08) ** 2 + ((z - 1.0) / 0.12) ** 2)) * 0.6)      # hands
            c = mixc(c, STAIN_STREAK, streak * 0.35)
        else:
            c = mixc(c, lin(70, 58, 44), cav * 0.4 + ss(0.5, 0.12, zf) * 0.4)
        hs = 0.10                                              # the heart ~20 cm wide (10 texels)
        hrt = _heart(lx / hs, (z - YK.HEART.z) / hs + 0.25) & (np.abs(Nn[:, 1]) > 0.5)
        c[hrt] = lin(14, 12, 10)
        rim = _heart(lx / (hs * 1.18), (z - YK.HEART.z) / (hs * 1.18) + 0.25) & ~hrt & (np.abs(Nn[:, 1]) > 0.5)
        c[rim] = (c[rim] * 0.6).astype(np.float32)
        col[m] = c[m]
        gr = np.where(m, seam * 0.75, gr)
    # ---- inside: rough boards, grime low down; the bench with the hole
    m = M(YK.Z_ILIN)
    bi, seam = boards(np.where(fb, ox, oy), 0.15, aa, 0.004)
    c = lin(110, 90, 66) * (0.86 + 0.18 * hash1(bi, 9))[:, None] * (0.86 + 0.2 * (n_lo - 0.5) * 2)[:, None]
    c = mixc(c, lin(62, 52, 40), ss(0.9, 0.1, zf) * 0.5 + cav * 0.4)
    c = mixc(c, lin(70, 66, 56), ss(0.70, 0.86, fbm(Pp, 6.0, 3, seed=1323)) * 0.4)
    col[m] = c[m]
    gr = np.where(m, seam * 0.7, gr)
    m = M(YK.Z_SEATB)
    c = T(lin(150, 120, 84), 0.10, 0.10)
    c = mixc(c, lin(100, 78, 54), edge * 0.6 + ss(0.65, 0.85, fbm(Pp, 14.0, 2, seed=1326)) * 0.4)
    hole = (((ox / 0.13) ** 2 + ((oy - YK.BENCH['y0'] - 0.25) / 0.10) ** 2) < 1.0) & (Nn[:, 2] > 0.5)
    ring = (((ox / 0.16) ** 2 + ((oy - YK.BENCH['y0'] - 0.25) / 0.13) ** 2) < 1.0) & ~hole & (Nn[:, 2] > 0.5)
    c[ring] = (c[ring] * 0.55).astype(np.float32)
    c[hole] = lin(8, 7, 6)
    col[m] = c[m]
    # ---- silver-grey weathered boards (the feeder, the porch), lichen and moss
    m = M(YK.Z_GREY)
    s_b = np.where(np.abs(Nn[:, 2]) > 0.5, y, np.where(np.abs(Nn[:, 1]) > 0.5, x, y))
    bi, seam = boards(s_b, 0.14, aa, 0.004)
    c = GREY_W * (0.86 + 0.20 * hash1(bi, 11))[:, None] * (0.86 + 0.18 * (n_lo - 0.5) * 2 + 0.10 * (n_hi - 0.5))[:, None]
    c = mixc(c, GREY_D, cav * 0.5 + ss(0.62, 0.82, n_mid) * 0.25)
    c = mixc(c, LICHEN, ss(0.72, 0.86, fbm(Pp, 16.0, 2, seed=1330)) * 0.45)
    c = mixc(c, MOSS, ss(0.70, 0.84, fbm(Pp, 9.0, 2, seed=1331)) * (0.3 + 0.7 * up) * 0.5)
    c = mixc(c, lit_c, lit * 0.7)
    col[m] = c[m]
    gr = np.where(m, seam * 0.75, gr)
    # ---- spruce logs: bark with flakes and resin, moss low, needles on top; end grain with rings, cracks and the number
    m = M(YK.Z_BARK)
    flake = fbm(Pp * np.array([0.25, 3.0, 3.0], np.float32), 22.0, 2, seed=1340)
    c = T(BARK, 0.18, 0.20) * (0.80 + 0.30 * flake)[:, None]
    c = mixc(c, BARK_L, ss(0.70, 0.86, fbm(Pp, 30.0, 2, seed=1341)) * 0.45)
    c = mixc(c, BARK_D, cav * 0.5)
    c = mixc(c, lin(170, 130, 60), ss(0.86, 0.94, fbm(Pp * np.array([0.3, 1, 1], np.float32), 18.0, 2, seed=1342)) * 0.6)  # resin
    c = mixc(c, MOSS_D, ss(0.30, 0.05, z) * 0.6)
    c = mixc(c, lit_c, lit * 0.8)
    col[m] = c[m]
    m = M(YK.Z_END)
    px, py, pz = x - PD.x, y - PD.y, z - PD.z
    centres = np.array([(c_[1], c_[2], c_[3]) for c_ in YK.LOGS], np.float32)
    d = np.full(n, 9.0, np.float32)
    rr = np.full(n, 0.17, np.float32)
    for cy_, cz_, r_ in centres:
        dd = np.hypot(py - cy_, pz - cz_)
        better = dd < d
        d = np.where(better, dd, d)
        rr = np.where(better, r_, rr)
    for sx in (-1.3, 1.3):                                            # the sleepers' ends (along y)
        dd = np.hypot(px - sx, pz - 0.06)
        better = (dd < d) & (np.abs(Nn[:, 1]) > 0.5)
        d = np.where(better, dd, d)
        rr = np.where(better, 0.10, rr)
    t = np.clip(d / rr, 0, 1)
    rings = 0.85 + 0.15 * np.cos(t * rr * 2 * np.pi / 0.006)
    c = END_L * rings[:, None] * (0.90 + 0.10 * (n_hi - 0.5))[:, None]
    c = mixc(c, END_D, ss(0.55, 1.0, t) * 0.6 + ss(0.15, 0.0, t) * 0.4)
    c = mixc(c, BARK_D, ss(0.90, 0.98, t))
    c = mixc(c, lin(120, 96, 70), ss(0.55, 0.85, fbm(Pp, 4.0, 2, seed=1350)) * 0.45)          # greyed by the weather
    crack = gline(np.abs(np.sin(np.arctan2(pz, py) * 3.0 + fbm(Pp, 3.0, 1, seed=1351) * 4.0)), 0.02, 0.01) * ss(0.2, 0.7, t)
    c = mixc(c, lin(70, 54, 40), crack * 0.6)
    # the number 317 sprayed across the road ends (-x), soft edges
    road = (Nn[:, 0] < -0.5) & (px < -YK.P_LEN / 2 + 0.3)
    pix = 0.045
    h, w = _MASK.shape
    u = np.floor((w * pix / 2 - py) / pix).astype(int)          # seen from -x: +y runs to the left
    v = np.floor((0.62 + h * pix / 2 - pz) / pix).astype(int)
    inside = road & (u >= 0) & (u < w) & (v >= 0) & (v < h)
    hit = np.zeros(n, bool)
    hit[inside] = _MASK[v[inside], u[inside]]
    fuzz = ss(0.3, 0.7, fbm(Pp, 60.0, 1, seed=1352))
    c = mixc(c, SPRAY, hit * (0.80 + 0.20 * fuzz))
    col[m] = c[m]
    # ---- hay, stones
    m = M(YK.Z_HAY)
    straw = fbm(Pp * np.array([4.0, 0.6, 2.0], np.float32), 30.0, 2, seed=1360)
    c = T(lin(170, 150, 90), 0.20, 0.25) * (0.78 + 0.35 * straw)[:, None]
    c = mixc(c, lin(110, 96, 60), ss(0.60, 0.82, n_mid) * 0.5 + cav * 0.4)
    col[m] = c[m]
    m = M(YK.Z_STONE)
    c = T(lin(120, 118, 112), 0.18, 0.25)
    c = mixc(c, MOSS, ss(0.45, 0.80, up) * ss(0.40, 0.70, fbm(Pp, 8.0, 3, seed=1361)) * 0.8)
    c = mixc(c, LICHEN, ss(0.75, 0.88, fbm(Pp, 20.0, 2, seed=1362)) * 0.5)
    c = mixc(c, MUD, ss(0.06, -0.06, z) * 0.6)
    col[m] = c[m]
    # ---- shared: white trims gone grey, raw spruce, the corrugated roofs, black steel
    m = M(K.Z_TRIMW)
    c = T(lin(200, 196, 182), 0.10, 0.12)
    c = mixc(c, lin(122, 114, 98), np.clip(edge * 0.9 + ss(0.62, 0.84, fbm(Pp, 18.0, 2, seed=1371)) * 0.8, 0, 0.95))
    c = mixc(c, lin(90, 84, 72), ss(0.35, 0.08, z - 0.1) * 0.6 + cav * 0.35)
    c = mixc(c, lin(130, 122, 104), streak * 0.35)
    col[m] = c[m]
    m = M(K.Z_TIMBER)
    vert = np.abs(Nn[:, 2]) < 0.6
    g2 = fbm(Pp * np.where(vert[:, None], np.array([4.0, 4.0, 0.25], np.float32), np.array([0.3, 4.0, 4.0], np.float32)), 10.0, 2,
             seed=1375)
    c = T(lin(132, 106, 76), 0.16, 0.12) * (0.86 + 0.22 * g2)[:, None]
    c = mixc(c, lin(84, 66, 48), cav * 0.55 + ss(0.6, 0.9, n_mid) * 0.25)
    c = mixc(c, GREY_W, weather * ss(0.4, 0.8, n_lo) * 0.35)
    c = mixc(c, MOSS_D, ss(0.30, 0.02, z) * 0.6)
    c = mixc(c, DUST, up * 0.2)
    col[m] = c[m]
    for zz, top in ((K.Z_ROOF, True), (K.Z_ROOFUNDER, False)):
        m = M(zz)
        ph = np.cos(2 * np.pi * x / 0.076)
        c = T(lin(146, 150, 146) if top else lin(114, 116, 112), 0.18, 0.20) * (0.82 + 0.18 * ph)[:, None]
        run = ss(0.52, 0.78, fbm(Pp * np.array([1, 0.15, 0.15], np.float32), 7.0, 3, seed=1377))
        c = mixc(c, RUST if top else RUST_D, run * (0.85 if top else 0.45))
        if top:
            l2, lc2 = _litter(Pp, np.ones(n, np.float32), 1378, 1.0)
            c = mixc(c, lc2, np.clip(l2 * (0.5 + 0.5 * ss(0.2, -0.6, ph)), 0, 1) * 0.9)
            c = mixc(c, MOSS, ss(0.62, 0.82, fbm(Pp, 6.0, 2, seed=1379)) * 0.5)
        col[m] = c[m]
        gr = np.where(m, gline(dist_periodic(x, 0.76, 0.38), 0.010, aa) * 0.8, gr)
    m = M(K.Z_STEELBLK)
    c = T(lin(36, 36, 36), 0.12, 0.2)
    c = mixc(c, RUST, np.clip(edge * 0.8 + ss(0.66, 0.84, fbm(Pp, 30.0, 2, seed=1380)) * 0.6, 0, 0.9))
    col[m] = c[m]
    m = M(K.Z_SLAB)
    c = T(lin(132, 130, 124), 0.16, 0.22)
    col[m] = c[m]
    return col, gr


# ================================================================ YardProps: the pointer's post and board, the lantern
def paint_props(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 1401)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    m = M(YK.Z_SPOST)
    g2 = fbm(Pp * np.array([4.0, 4.0, 0.25], np.float32), 10.0, 2, seed=1410)
    c = T(lin(84, 64, 46), 0.16, 0.14) * (0.84 + 0.24 * g2)[:, None]
    c = mixc(c, GREY_W, ss(0.45, 0.80, n_lo) * 0.35)
    c = mixc(c, MOSS_D, ss(0.35, 0.02, z) * 0.7)
    c = mixc(c, lin(56, 50, 42), ss(0.30, 0.0, z) * 0.5)
    col[m] = c[m]
    m = M(YK.Z_SBOARD)
    c = T(lin(70, 48, 30), 0.14, 0.14)
    c = mixc(c, lin(120, 112, 98), edge * 0.6 + ss(0.6, 0.85, n_lo) * 0.3)
    col[m] = c[m]
    m = M(YK.Z_LMETAL)
    c = T(lin(40, 64, 44), 0.12, 0.14)
    c = mixc(c, lin(110, 112, 100), edge * 0.6)
    c = mixc(c, RUST, ss(0.70, 0.86, fbm(Pp, 40.0, 2, seed=1420)) * 0.5)
    col[m] = c[m]
    for zz in (YK.Z_LWIRE, K.Z_STEELBLK):
        m = M(zz)
        c = T(lin(32, 32, 32), 0.12, 0.2)
        c = mixc(c, RUST, ss(0.55, 0.80, fbm(Pp, 50.0, 2, seed=1421)) * 0.7)
        col[m] = c[m]
    return col, gr
