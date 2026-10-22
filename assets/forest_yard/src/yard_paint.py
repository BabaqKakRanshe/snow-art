"""Painters for the station yard's atlases (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
The generator shed's wear language (gen_paint / hut_paint / kpp_paint: the metals, dust, rust runs) on the yard's things:
  Tanks: the bund's concrete (board-formed walls with tie holes, a tide line inside, moss and earth at the foot, leaves and
  needles in the corners, a wet patch round the sump, diesel stains at the outlet, the pump and the couplings), the tanks in
  the station's grey-green (faded on top, rust runs from every fitting, the weld seams, diesel down the fill stubs, the
  stencils painted on: DIESEL, TANK 1 / 2 · 18 000 L), the saddles, plinths, black-painted lines, galvanised steel, the
  stile's grating, the drip tray;
  Trafo: the pad and the gravel sump, the transformer in cement grey (oil weeping under the bushings, rust runs from the lid
  bolts), brown porcelain, the creosoted pole (cracks, greyed toward the top, a dark ground line), the GRP cabinet (algae),
  weathered copper, black cables, the trench covers; the Trafo painter works in the Trafo's own frame;
  YardProps: the wing pump (signal red over cast iron), the lever, the hose, the brass nozzle, the extinguisher, the
  handwheels, the dials, the padlocks, the silica gel, the green-yellow earth leads."""
import math
import numpy as np
from mathutils import Matrix, Vector
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, boards, hash1
import pxfont as F
import gen_kit as K
import yard_kit as YK
import yard_tex as YT                                  # (the umlauts in the pixel font)
from gen_paint import DUST, RUST, RUST_D, _T, _common, run_m

GREEN, GREEN_FADE, GREEN_DARK = lin(108, 122, 96), lin(150, 158, 136), lin(64, 74, 58)
CONCRETE, EARTH, MOSS = lin(132, 130, 124), lin(66, 56, 44), lin(70, 84, 46)
LEAF_A, LEAF_B = lin(156, 92, 38), lin(98, 72, 42)
DIESEL = lin(44, 40, 34)
WHITE_ST = lin(222, 220, 208)

DRAFT_COL = {   # sRGB, roughly the painters' base colours (yard_build --draft)
    YK.Z_BUNDW: (132, 130, 124), YK.Z_BUNDF: (118, 116, 110), YK.Z_TANK: (108, 122, 96), YK.Z_SADDLE: (90, 100, 80),
    YK.Z_PLINTH: (126, 124, 118), YK.Z_PIPE: (46, 46, 44), YK.Z_GRATING: (150, 154, 152), YK.Z_RUBBERY: (30, 30, 30),
    YK.Z_FOOTC: (126, 124, 118), YK.Z_TRAYG: (140, 144, 142), K.Z_GALV: (150, 154, 152), K.Z_STEELBLK: (36, 36, 36),
    YK.Z_SHELL: (108, 122, 96),
    YK.Z_PAD: (128, 126, 120), YK.Z_GRAVEL: (110, 104, 96), YK.Z_TRAFO: (118, 126, 118), YK.Z_FINS: (112, 120, 112),
    YK.Z_PORC: (120, 62, 38), YK.Z_POLE: (66, 50, 36), YK.Z_CABGRP: (176, 178, 170), YK.Z_COPPER: (120, 82, 54),
    YK.Z_CABLE: (28, 28, 28), YK.Z_PORCG: (170, 172, 168), YK.Z_TRENCH: (120, 118, 112),
    YK.Z_PUMPB: (160, 40, 30), YK.Z_LEVER: (40, 40, 40), YK.Z_GRIP: (24, 24, 24), YK.Z_HOSE: (30, 30, 30),
    YK.Z_BRASS: (170, 140, 70), YK.Z_EXT: (180, 30, 24), YK.Z_WHEEL: (170, 34, 28), YK.Z_GAUGEH: (36, 36, 36),
    YK.Z_LOCK: (170, 140, 70), YK.Z_BREATH: (200, 120, 40), YK.Z_EARTH: (60, 140, 60), YK.Z_COLUMN: (50, 60, 50),
    YK.Z_CAP: (120, 122, 120), YK.Z_SENSOR: (150, 150, 146)}


# ---------------------------------------------------------------- the shed's metals (as kpp_paint has them)
def steel_black(Pp, T, edge, seed=121):
    c = T(lin(36, 36, 36), 0.12, 0.2)
    return mixc(c, RUST, np.clip(edge * 0.7 + ss(0.72, 0.86, fbm(Pp, 30.0, 2, seed=seed)) * 0.5, 0, 0.8))


def galv(Pp, T, seed=122):
    spang = fbm(Pp, 90.0, 1, seed=seed)
    c = T(lin(150, 154, 152), 0.10, 0.08) * (0.88 + 0.22 * spang)[:, None]
    c = mixc(c, lin(196, 198, 192), ss(0.78, 0.90, fbm(Pp, 25.0, 2, seed=seed + 1)) * 0.4)
    return mixc(c, RUST, run_m(Pp) * 0.35)


def hash2(a, b, seed):
    """a 2D cell hash (float64): no runs of equal values along a + k b = const as with hash1(a + k b)"""
    return hash1(hash1(np.asarray(a, np.float64), seed) * 1013.0 + np.asarray(b, np.float64) * 1.618, seed + 1)


def _leaves(Pp, up, seed):
    x, y = Pp[:, 0], Pp[:, 1]
    m = ss(0.74, 0.86, fbm(Pp, 7.0, 2, seed=seed)) * ss(0.55, 0.90, fbm(Pp, 40.0, 1, seed=seed + 1)) * up
    pick = hash2(np.floor(x * 41.0), np.floor(y * 43.0), seed)
    return m, np.where((pick > 0.55)[:, None], LEAF_A, LEAF_B)


# ---------------------------------------------------------------- stencils painted on the tanks
def _stencils():
    out = []
    for tname, yc in YK.TANK_Y.items():
        front = yc < 0
        right = np.array((1.0, 0.0, 0.0)) if front else np.array((-1.0, 0.0, 0.0))
        xc = -1.15 if front else 1.15
        for deg, txt, font, scale, h in ((270 if front else 90, 'DIESEL', F.F57, 2, 0.235),
                                         (285 if front else 75, f'TANK {tname[1]} • 18 000 L', F.F35, 2, 0.15)):
            p = math.radians(deg)
            n = np.array((0.0, math.sin(p), -math.cos(p)))
            up = np.array((0.0, -math.cos(p), -math.sin(p))) if front else np.array((0.0, math.cos(p), math.sin(p)))
            c = np.array((xc, yc + YK.TIN * math.sin(p), YK.TZ - YK.TIN * math.cos(p)))
            m = F.text_mask(txt, font, scale)
            out.append((c, n, right, up, h, m))
    return out


STENCILS = _stencils()


def stencil_mask(Pp, Nn):
    """1 where a stencil letter is painted (the tanks' sides)"""
    res = np.zeros(len(Pp), np.float32)
    for c, n, right, up, h, m in STENCILS:
        H, W = m.shape
        s = h / H
        d = Pp - c[None, :].astype(np.float32)
        on = (np.abs(d @ n) < 0.03) & ((Nn @ n) > 0.985)
        u = (d @ right) / (W * s) + 0.5
        v = (d @ up) / h + 0.5
        ins = on & (u >= 0) & (u < 1) & (v >= 0) & (v < 1)
        if not ins.any():
            continue
        col_ = np.clip((u[ins] * W).astype(int), 0, W - 1)
        row_ = np.clip(((1 - v[ins]) * H).astype(int), 0, H - 1)
        res[np.where(ins)[0]] = m[row_, col_].astype(np.float32)
    return res


# ================================================================ Tanks
def paint_tanks(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 801)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    inside = ((np.abs(x) < YK.IX) & (np.abs(y) < YK.IY)).astype(np.float32)
    lv, lv_c = _leaves(Pp, up, 811)
    # ---- the bund walls: board-formed concrete, tie holes, water runs under the top, the tide line inside, moss and
    # earth at the foot outside, lichen and needles on the top
    m = M(YK.Z_BUNDW)
    c = T(CONCRETE, 0.16, 0.22)
    vert = np.abs(Nn[:, 2]) < 0.5
    s_w = np.where(np.abs(Nn[:, 1]) > 0.5, x, y)
    board = gline(dist_periodic(z - 0.05, 0.20), 0.006, aa) * vert
    tie = (1 - ss(0.012 - aa, 0.016 + aa, np.hypot(dist_periodic(s_w, 0.75, 0.375), dist_periodic(z, 0.40, 0.33)))) * vert
    c = c * (0.92 + 0.10 * hash1(np.floor((z - 0.05) / 0.20) + 3.0 * np.floor(s_w / 2.4), 5))[:, None]
    c = mixc(c, lin(70, 68, 64), tie * 0.8)
    runs = ss(0.55, 0.80, fbm(Pp * np.array([1, 1, 0.12], np.float32), 8.0, 3, seed=812)) * vert * ss(0.2, 0.75, z)
    c = mixc(c, lin(92, 90, 84), runs * 0.45)
    c = mixc(c, lin(170, 168, 160), ss(0.80, 0.92, fbm(Pp * np.array([1, 1, 0.2], np.float32), 10.0, 2, seed=813)) * vert * 0.35)
    tide = inside * vert * np.exp(-((z - 0.27) / 0.02) ** 2)
    c = mixc(c, lin(96, 94, 86), np.clip(tide + inside * vert * ss(0.30, 0.16, z) * 0.5, 0, 1) * 0.55)
    c = mixc(c, EARTH, (1 - inside) * ss(0.10, -0.06, z) * 0.85)
    c = mixc(c, MOSS, (1 - inside) * vert * ss(0.35, 0.05, z) * ss(0.55, 0.80, fbm(Pp, 5.0, 2, seed=814)) * 0.6)
    top = (Nn[:, 2] > 0.6).astype(np.float32)
    c = mixc(c, lin(120, 124, 96), top * ss(0.62, 0.80, fbm(Pp, 9.0, 2, seed=815)) * 0.45)          # lichen
    c = mixc(c, lv_c, lv * 0.8 * top)
    c = mixc(c, DIESEL, np.exp(-(((x - YK.OUT_X) / 0.10) ** 2 + ((z - 1.0) / 0.5) ** 2)) * (y < -YK.IY + 0.01) * 0.35)
    col[m] = c[m]
    gr = np.where(m, np.maximum(board * 0.6, tie * 0.3), gr)
    # ---- the floor: darker concrete, needles and leaves along the walls and in the corners, the wet patch at the sump,
    # diesel under the outlet valve
    m = M(YK.Z_BUNDF)
    c = T(lin(114, 112, 106), 0.18, 0.20)
    wall_d = np.minimum(YK.IX - np.abs(x), YK.IY - np.abs(y))
    sx0, sx1, sy0, sy1 = YK.SUMP
    sump_d = np.hypot(np.clip(x - (sx0 + sx1) / 2, -0.2, 0.2) - (x - (sx0 + sx1) / 2), np.clip(y - (sy0 + sy1) / 2, -0.2, 0.2) - (y - (sy0 + sy1) / 2))
    c = mixc(c, lin(72, 72, 68), ss(0.9, 0.0, sump_d) * 0.7)
    c = mixc(c, lin(84, 82, 76), ss(0.25, 0.0, wall_d) * 0.4)
    lt, lc = _leaves(Pp * np.array([1.3, 1.3, 1.0], np.float32), np.ones(n, np.float32), 816)
    c = mixc(c, lc, np.clip(lt * 0.9 + ss(0.45, 0.05, wall_d) * ss(0.55, 0.75, fbm(Pp, 12.0, 2, seed=817)) * 0.8, 0, 1))
    c = mixc(c, DIESEL, ss(0.35, 0.0, np.hypot(x - YK.OUT_X, y - YK.TANK_Y['T1'])) * 0.6)
    c = mixc(c, lin(60, 58, 52), cav * 0.5)
    col[m] = c[m]
    gr = np.where(m, gline(dist_periodic(x, 2.05, 0.0), 0.006, aa) * 0.5, gr)
    # ---- the tanks: station grey-green, faded on top, rust runs from the fittings, diesel down the fill stubs, weld
    # seams, dust and a few bird droppings on top, the stencils
    m = M(YK.Z_TANK) | M(YK.Z_SADDLE) | M(YK.Z_SHELL)
    c = GREEN * (0.92 + 0.10 * hash1(np.floor((x + 2.5) / 1.25) + 7.0 * np.sign(y), 9))[:, None] * \
        (0.86 + 0.20 * (n_lo - 0.5) + 0.10 * (n_hi - 0.5))[:, None]
    c = mixc(c, GREEN_FADE, np.clip(Nn[:, 2], 0, 1) * ss(0.30, 0.70, n_lo) * 0.55)
    fit_x = np.array([YK.MAN_X, YK.VENT_X, YK.FILL_X, -1.90, 1.90])
    dfit = np.min(np.abs(x[:, None] - fit_x[None, :]), axis=1)
    side = (Nn[:, 2] < 0.95) & (Nn[:, 2] > -0.4)
    run = ss(0.12, 0.0, dfit) * ss(0.55, 0.85, fbm(Pp * np.array([3.0, 1.0, 0.25], np.float32), 9.0, 2, seed=821)) * side
    c = mixc(c, RUST, np.clip(run * 0.8 + ss(0.82, 0.92, fbm(Pp, 22.0, 2, seed=822)) * 0.5, 0, 0.85))
    c = mixc(c, RUST_D, ss(-0.55, -0.95, Nn[:, 2]) * ss(0.45, 0.75, fbm(Pp, 6.0, 2, seed=823)) * 0.6)       # condensation rust
    dsl = ss(0.10, 0.0, np.abs(x - YK.FILL_X)) * ss(0.2, 0.9, Nn[:, 2] + 0.5) * ss(0.4, 0.8, fbm(Pp, 14.0, 2, seed=824))
    c = mixc(c, DIESEL, np.clip(dsl, 0, 1) * 0.55)
    c = mixc(c, DUST, np.clip(Nn[:, 2], 0, 1) ** 2 * 0.30)
    # (the head welds are drawn 3 cm in on the shell: the shell / head island border stays clean)
    seam = np.maximum.reduce([gline(np.abs(x - s), 0.004, aa) for s in (-2.47, -1.25, 0.0, 1.25, 2.47)])
    c = mixc(c, GREEN_DARK, seam * 0.5 * M(YK.Z_SHELL))
    birds = (hash2(np.floor(x * 30.0), np.floor(y * 31.0), 13) > 0.997) & (Nn[:, 2] > 0.9)
    c = np.where(birds[:, None], lin(214, 212, 200), c)
    st = stencil_mask(Pp, Nn) * M(YK.Z_SHELL)
    wear = ss(0.55, 0.80, fbm(Pp, 30.0, 2, seed=825))
    c = mixc(c, WHITE_ST * (0.92 + 0.10 * n_hi)[:, None], st * (0.88 - 0.55 * wear))
    c = np.where(M(YK.Z_SADDLE)[:, None], mixc(c * 0.86, RUST, ss(0.9, 0.5, z) * 0.45), c)
    col[m] = c[m]
    gr = np.where(M(YK.Z_SHELL), seam * 0.6, gr)
    # ---- the plinths and the pump's footing: concrete, rust run-off from the base plates, diesel on the footing
    for zz in (YK.Z_PLINTH, YK.Z_FOOTC):
        m = M(zz)
        c = T(lin(126, 124, 118), 0.16, 0.22)
        c = mixc(c, lin(120, 74, 44), (Nn[:, 2] < 0.5) * ss(0.30, 0.45, z) * ss(0.45, 0.75, fbm(Pp, 10.0, 2, seed=826)) * 0.5)
        c = mixc(c, EARTH, ss(0.06, -0.06, z) * 0.8)
        if zz == YK.Z_FOOTC:
            c = mixc(c, DIESEL, ss(0.70, 0.40, fbm(Pp, 6.0, 2, seed=827)) * 0.6)
        col[m] = c[m]
    # ---- the lines: black paint, rust at the bends and the bottom, diesel at the couplings' ends
    m = M(YK.Z_PIPE)
    c = T(lin(46, 46, 44), 0.10, 0.16)
    c = mixc(c, RUST, np.clip(ss(0.74, 0.88, fbm(Pp, 26.0, 2, seed=828)) * 0.7 + ss(-0.3, -0.9, Nn[:, 2]) * 0.3, 0, 0.8))
    c = mixc(c, DUST, np.clip(Nn[:, 2], 0, 1) * 0.25)
    col[m] = c[m]
    # ---- galvanised steel and the grating (a 6 x 4 cm mesh on the treads)
    m = M(K.Z_GALV)
    c = galv(Pp, T)
    c = mixc(c, EARTH, ss(0.25, 0.02, z) * (1 - inside) * 0.45)
    col[m] = c[m]
    m = M(YK.Z_GRATING)
    c = galv(Pp, T, 123)
    hole = (dist_periodic(x, 0.06) > 0.006) & (dist_periodic(y, 0.04) > 0.005) & (Nn[:, 2] > 0.8)
    c = np.where(hole[:, None], lin(40, 40, 38), c)
    col[m] = mixc(c, EARTH, ss(0.4, 0.0, z) * 0.3)[m]
    m = M(K.Z_STEELBLK)
    col[m] = steel_black(Pp, T, edge)[m]
    m = M(YK.Z_RUBBERY)
    col[m] = T(lin(30, 30, 30), 0.1, 0.1)[m]
    # ---- the drip tray: galvanised, black with old diesel at the bottom
    m = M(YK.Z_TRAYG)
    c = galv(Pp, T, 124)
    c = mixc(c, DIESEL, ss(0.02, 0.006, z) * (Nn[:, 2] > 0.8) * 0.85)
    c = mixc(c, lin(70, 64, 50), ss(0.04, 0.01, z) * 0.4)
    col[m] = c[m]
    return col, gr


# ================================================================ Trafo (painted in the Trafo's own frame)
_TP, _TY = YK.TRAFO_PLACE
_RT = np.array(Matrix.Rotation(math.radians(_TY), 3, 'Z'), np.float32)


def to_trafo(Pp, Nn):
    """world (FuelTanks frame) -> Trafo frame"""
    q = (Pp - np.array(_TP, np.float32)[None, :]) @ _RT                    # R^T applied to row vectors: p @ R
    return q.astype(np.float32), (Nn @ _RT).astype(np.float32)


def paint_trafo(Pp, Nn, Z, ao, aa):
    Pp, Nn = to_trafo(Pp, Nn)
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 901)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    lv, lv_c = _leaves(Pp, up, 911)
    # ---- the pad and the trench covers: concrete, oil round the transformer, moss at the edges, leaves
    for zz in (YK.Z_PAD, YK.Z_TRENCH):
        m = M(zz)
        c = T(lin(128, 126, 120), 0.16, 0.22)
        c = mixc(c, EARTH, ss(0.08, -0.08, z) * 0.85)
        topf = (Nn[:, 2] > 0.8).astype(np.float32)
        c = mixc(c, lin(70, 66, 58), topf * ss(1.1, 0.5, np.hypot(np.maximum(np.abs(x) - 0.6, 0), np.maximum(np.abs(y - 0.3) - 0.4, 0) * 1.5)) * 0.45)
        edge_d = np.minimum(2.6 - np.abs(x), 2.1 - np.abs(y))
        c = mixc(c, MOSS, topf * ss(0.35, 0.05, edge_d) * ss(0.55, 0.80, fbm(Pp, 6.0, 2, seed=912)) * 0.6)
        c = mixc(c, lv_c, lv * 0.85)
        if zz == YK.Z_TRENCH:
            c = c * (0.92 + 0.10 * hash1(np.floor(x / 0.5) + np.floor(y / 0.5) * 5.0, 7))[:, None]
        col[m] = c[m]
        if zz == YK.Z_TRENCH:
            gr = np.where(m, np.maximum(gline(dist_periodic(x, 0.5), 0.006, aa), gline(dist_periodic(y, 0.5), 0.006, aa)) * 0.7, gr)
    m = M(YK.Z_GRAVEL)                                                        # grey-brown chippings, oily in places
    h_ = hash2(np.floor(x * 70.0), np.floor(y * 73.0), 17)
    c = np.where((h_ > 0.66)[:, None], lin(150, 146, 136), np.where((h_ > 0.33)[:, None], lin(112, 104, 94), lin(80, 74, 66)))
    c = mixc(c, lin(46, 42, 36), ss(0.6, 0.85, fbm(Pp, 4.0, 2, seed=913)) * 0.5)
    col[m] = mixc(c, lv_c, lv * 0.7)[m]
    # ---- the transformer: cement grey, rust runs from the lid's bolts and the lugs, oil weeping under the bushings and
    # the drain valve, dirt low down, chalky on top
    for zz in (YK.Z_TRAFO, YK.Z_FINS):
        m = M(zz)
        c = T(lin(118, 126, 118), 0.10, 0.14)
        c = mixc(c, lin(160, 166, 158), np.clip(Nn[:, 2], 0, 1) * ss(0.35, 0.75, n_lo) * 0.40)
        vert = np.abs(Nn[:, 2]) < 0.5
        runs = ss(0.56, 0.84, fbm(Pp * np.array([2.5, 2.5, 0.2], np.float32), 10.0, 2, seed=914)) * vert * ss(0.6, 1.4, z)
        c = mixc(c, RUST, np.clip(runs * 0.6 + edge * 0.4 * (zz == YK.Z_FINS), 0, 0.8))
        oil = (np.exp(-((x - 0.0) / 0.45) ** 2) * ss(1.55, 0.9, z) * (np.abs(y - 0.3) < 0.35) * vert
               + np.exp(-(((y - 0.15) / 0.06) ** 2 + ((z - 0.42) / 0.10) ** 2)) * (x > 0.5))
        c = mixc(c, lin(58, 52, 38), np.clip(oil, 0, 1) * ss(0.4, 0.75, fbm(Pp, 12.0, 2, seed=915)) * 0.6)
        c = mixc(c, EARTH, ss(0.75, 0.30, z) * 0.35)
        c = mixc(c, lin(70, 74, 70), cav * 0.4)
        col[m] = c[m]
    m = M(YK.Z_PORC)                                                          # brown glaze, dirty under the sheds
    c = T(lin(120, 62, 38), 0.06, 0.10) * (0.85 + 0.30 * n_hi)[:, None]
    c = mixc(c, lin(200, 150, 120), ss(0.55, 0.95, np.clip(Nn[:, 2] * 0.5 + 0.5, 0, 1)) * 0.25)
    col[m] = mixc(c, lin(60, 40, 30), ss(-0.2, -0.8, Nn[:, 2]) * 0.4)[m]
    m = M(YK.Z_PORCG)
    c = T(lin(170, 172, 168), 0.06, 0.10) * (0.88 + 0.20 * n_hi)[:, None]
    col[m] = mixc(c, lin(90, 90, 86), ss(-0.2, -0.8, Nn[:, 2]) * 0.35 + cav * 0.3)[m]
    # ---- the pole: creosote brown, long cracks, greyed toward the top and on the crossarm, a dark ground line
    m = M(YK.Z_POLE)
    ang = np.arctan2(y - YK.POLE.y, x - YK.POLE.x)
    onpole = (np.hypot(x - YK.POLE.x, y - YK.POLE.y) < 0.16)
    crack = np.maximum(gline(dist_periodic(ang * 0.13, 0.11, 0.03), 0.004, aa), gline(dist_periodic(ang * 0.13, 0.11, 0.08), 0.003, aa))
    crack = crack * ss(0.45, 0.70, fbm(Pp * np.array([1, 1, 0.08], np.float32), 4.0, 2, seed=916)) * onpole
    c = T(lin(66, 50, 36), 0.14, 0.18) * (0.86 + 0.24 * fbm(Pp * np.array([4, 4, 0.2], np.float32), 12.0, 2, seed=917))[:, None]
    c = mixc(c, lin(112, 106, 96), ss(4.0, 8.6, z) * 0.45 + (z > 8.10) * (~onpole) * 0.35)
    c = mixc(c, lin(30, 24, 20), np.exp(-((z - 0.08) / 0.18) ** 2) * 0.6)
    c = mixc(c, lin(26, 22, 18), crack * 0.8)
    col[m] = c[m]
    gr = np.where(m, crack * 0.6, gr)
    # ---- the GRP cabinet: light grey, algae on the top and back, dirt low, the door gap
    m = M(YK.Z_CABGRP)
    c = T(lin(176, 178, 170), 0.06, 0.08)
    c = mixc(c, lin(96, 116, 76), np.clip(np.clip(Nn[:, 2], 0, 1) * 0.6 + (Nn[:, 1] > 0.5) * 0.4, 0, 1) *
             ss(0.50, 0.80, fbm(Pp, 8.0, 2, seed=918)) * 0.45)
    c = mixc(c, lin(120, 114, 100), ss(0.55, 0.25, z) * 0.45)
    col[m] = c[m]
    m = M(YK.Z_COPPER)                                                        # weathered copper, green patina in spots
    c = T(lin(110, 74, 50), 0.12, 0.16)
    col[m] = mixc(c, lin(80, 130, 110), ss(0.62, 0.84, fbm(Pp, 30.0, 2, seed=919)) * 0.6)[m]
    m = M(YK.Z_CABLE)
    c = T(lin(28, 28, 28), 0.08, 0.12)
    col[m] = mixc(c, DUST, np.clip(Nn[:, 2], 0, 1) * 0.3)[m]
    m = M(K.Z_GALV)
    c = galv(Pp, T, 131)
    col[m] = mixc(c, EARTH, ss(0.35, 0.02, z) * 0.45)[m]
    m = M(K.Z_STEELBLK)
    col[m] = steel_black(Pp, T, edge, 132)[m]
    return col, gr


# ================================================================ YardProps
def paint_props(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 1001)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(120, 120, 120), (n, 1))
    chip = ss(0.80, 0.92, fbm(Pp, 40.0, 2, seed=1011))
    m = M(YK.Z_PUMPB)                                                         # signal red over cast iron, chipped, oily below
    c = T(lin(160, 40, 30), 0.08, 0.12)
    c = mixc(c, lin(40, 38, 36), np.clip(chip * 0.8 + edge * 0.5, 0, 0.9))
    col[m] = mixc(c, DIESEL, ss(-0.3, -0.9, Nn[:, 2]) * 0.4 + cav * 0.3)[m]
    m = M(YK.Z_LEVER)
    c = T(lin(40, 40, 40), 0.10, 0.14)
    col[m] = mixc(c, lin(120, 120, 116), edge * 0.5 + chip * 0.3)[m]
    m = M(YK.Z_GRIP)
    col[m] = mixc(T(lin(24, 24, 24), 0.08, 0.12), lin(60, 58, 54), ss(0.5, 0.8, n_mid) * 0.4)[m]
    m = M(YK.Z_HOSE)                                                          # black rubber, dusty, wet with diesel low down
    c = T(lin(30, 30, 30), 0.08, 0.14)
    c = mixc(c, lin(96, 92, 84), np.clip(Nn[:, 2], 0, 1) * ss(0.4, 0.8, n_lo) * 0.45)
    col[m] = c[m]
    m = M(YK.Z_BRASS)                                                         # the nozzle: dull aluminium, a brass spout
    c = T(lin(150, 148, 140), 0.08, 0.12)
    c = np.where((z < 0.805)[:, None], lin(150, 120, 64) * (0.85 + 0.2 * n_hi)[:, None], c)
    col[m] = mixc(c, lin(60, 56, 46), cav * 0.5 + ss(0.5, 0.85, n_mid) * 0.35)[m]
    m = M(YK.Z_EXT)                                                           # red extinguisher, a white label band
    c = T(lin(180, 30, 24), 0.08, 0.12)
    lab = (np.abs(z - 0.86) < 0.08) & (np.abs(Nn[:, 2]) < 0.5) & (Nn[:, 1] < -0.3)
    c = np.where(lab[:, None], lin(226, 222, 206), c)
    col[m] = mixc(c, lin(90, 30, 24), chip * 0.5 + edge * 0.3)[m]
    m = M(YK.Z_WHEEL)
    c = T(lin(170, 34, 28), 0.10, 0.14)
    col[m] = mixc(c, RUST, np.clip(chip * 0.7 + edge * 0.5, 0, 0.9))[m]
    m = M(YK.Z_GAUGEH)
    col[m] = mixc(T(lin(36, 36, 36), 0.08, 0.12), lin(110, 110, 106), edge * 0.4)[m]
    m = M(YK.Z_LOCK)
    c = T(lin(170, 140, 70), 0.10, 0.16)
    col[m] = mixc(c, lin(70, 90, 70), ss(0.6, 0.85, n_mid) * 0.45)[m]
    m = M(YK.Z_BREATH)                                                        # silica gel seen through the glass: orange
    h_ = hash2(np.floor(x * 300.0), np.floor(z * 290.0), 21)
    c = np.where((h_ > 0.5)[:, None], lin(210, 128, 40), lin(170, 96, 30))
    col[m] = mixc(c, lin(230, 230, 220), ss(0.6, 0.95, np.abs(Nn[:, 0])) * 0.25)[m]
    m = M(YK.Z_EARTH)                                                         # green-yellow stripes along the lead
    stripe = np.mod(np.floor((x + y + z) / 0.03), 2) == 0
    col[m] = np.where(stripe[:, None], lin(40, 130, 50), lin(210, 190, 40))[m] * (0.85 + 0.2 * n_hi)[m][:, None]
    m = M(YK.Z_COLUMN)                                                        # the pump post: dark green paint, rust low
    c = T(lin(50, 60, 50), 0.10, 0.14)
    col[m] = mixc(c, RUST, ss(0.35, 0.05, z) * 0.6 + chip * 0.3)[m]
    m = M(YK.Z_CAP)
    c = T(lin(120, 122, 120), 0.10, 0.14)
    col[m] = mixc(c, lin(60, 60, 58), cav * 0.5 + chip * 0.3)[m]
    m = M(YK.Z_SENSOR)
    c = T(lin(150, 150, 146), 0.06, 0.10)
    col[m] = mixc(c, lin(200, 180, 40), (Nn[:, 1] < -0.8) * (np.abs(z - 0.52) < 0.02) * 0.8)[m]
    return col, None
