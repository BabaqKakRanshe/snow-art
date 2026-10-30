"""Painter for the forest_smoke 2.0 Small atlas (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
The pager's recipe (hand things, 512 px / m): the packs' chamfered edges in their brand colour rubbed to the board, the
inner board, the torn foil; the lighter's red see-through plastic with the gas level and the wick rod inside, the steel
hood with its slots, the dark ridged wheel, the red lever; the cigarette paper with its seam; the grey ash."""
import math
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin
from gen_paint import _T, _common
import smoke2_kit as SK

DRAFT_COL = {SK.Z_GOLD: (178, 140, 64), SK.Z_PAPERB: (166, 178, 188), SK.Z_GREEN: (28, 80, 62), SK.Z_BOARD: (222, 216, 200),
             SK.Z_FOIL: (184, 186, 190), SK.Z_LBODY: (150, 26, 22), SK.Z_LHOOD: (156, 156, 154), SK.Z_LWHEEL: (54, 54, 58),
             SK.Z_LBTN: (168, 32, 26), SK.Z_CPAPER: (232, 230, 222), SK.Z_ASH: (112, 108, 102)}


def local(Pp, root):
    o = SK.DISPLAY[root]
    return Pp[:, 0] - o.x, Pp[:, 1] - o.y, Pp[:, 2] - o.z


def paint_small(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp * 3.0, Nn, ao, 2701)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    worn = ss(0.45, 0.85, fbm(Pp, 140.0, 2, seed=2702))
    # ---- the packs' chamfers: the brand colour, rubbed to the board along the edge
    for z, c0, board in ((SK.Z_GOLD, (178, 140, 64), (232, 222, 196)), (SK.Z_PAPERB, (166, 178, 188), (214, 216, 214)),
                         (SK.Z_GREEN, (28, 80, 62), (170, 198, 182))):
        m = M(z)
        c = mixc(T(lin(*c0), 0.05, 0.06), lin(*board), worn * 0.7)
        col[m] = c[m]
    m = M(SK.Z_BOARD)                                                       # the white board inside
    col[m] = mixc(T(lin(222, 216, 200), 0.04, 0.05), lin(150, 140, 120), cav * 0.4)[m]
    m = M(SK.Z_FOIL)                                                        # crumpled foil: bright and dark creases
    crease = fbm(Pp, 900.0, 2, seed=2703)
    col[m] = mixc(lin(176, 178, 182), lin(236, 238, 240), ss(0.55, 0.75, crease))[m] * (0.75 + 0.35 * crease[m])[:, None]
    # ---- the lighter
    x, y, z = local(Pp, 'Item_Lighter')
    m = M(SK.Z_LBODY)
    c = T(lin(156, 28, 22), 0.05, 0.06)
    gas = z < 0.030 + 0.0006 * np.sin(x * 400.0)                            # the gas seen through the plastic: darker below
    c = np.where(gas[:, None], c * 0.62, c)
    c = mixc(c, lin(214, 70, 60), gline(np.abs(z - 0.030), 0.0005, aa) * 0.8)       # the liquid's surface line
    face = (np.abs(Nn[:, 1]) > 0.9)
    rod = face & (np.abs(x) < 0.0008) & (z > 0.004) & (z < 0.056)           # the wick rod inside
    c = mixc(c, lin(196, 60, 52), rod * 0.7)
    c = mixc(c, lin(226, 150, 140), ss(0.985, 0.94, np.abs(Nn).max(axis=1)) * 0.35)  # the chamfers catch the light
    c = mixc(c, lin(90, 18, 16), (z < 0.0012) * 0.6)                         # the dark foot
    c = mixc(c, lin(200, 190, 186), ss(0.80, 0.95, fbm(Pp, 400.0, 2, seed=2704)) * 0.18)   # fine scratches
    col[m] = c[m]
    m = M(SK.Z_LHOOD)
    c = T(lin(156, 156, 154), 0.06, 0.10)
    slots = face & (x > -0.0105) & (x < -0.003) & (z > 0.0615) & (z < 0.0695)
    g = slots * gline(dist_periodic(x + 0.0105, 0.0025, 0.0), 0.0006, aa)
    c = mixc(c, lin(70, 66, 60), cav * 0.6)
    c = mixc(c, lin(110, 92, 70), ss(0.6, 0.9, fbm(Pp, 300.0, 2, seed=2705)) * 0.25)   # a little tarnish
    col[m] = c[m]
    gr = np.where(m, g, gr)
    m = M(SK.Z_LWHEEL)
    ang = np.arctan2(z - (SK.LT['hood'] - 0.0016), x - 0.0074)
    ridge = gline(dist_periodic(ang, 2 * math.pi / 24, 0.0), 0.05, aa * 40.0)
    col[m] = mixc(T(lin(54, 54, 58), 0.05, 0.05), lin(120, 120, 124), (1 - ridge) * 0.35 * (np.abs(Nn[:, 1]) < 0.5))[m]
    m = M(SK.Z_LBTN)
    col[m] = mixc(T(lin(168, 32, 26), 0.05, 0.06), lin(220, 120, 110), ss(0.985, 0.94, np.abs(Nn).max(axis=1)) * 0.4)[m]
    # ---- the cigarette
    x, y, z = local(Pp, 'Cigarette')
    m = M(SK.Z_CPAPER)
    c = T(lin(234, 232, 224), 0.03, 0.04)
    seam = gline(np.abs(np.arctan2(z, x) - 1.2), 0.04, aa * 260.0)          # the glued seam along the paper
    c = mixc(c, lin(212, 210, 200), seam * 0.6)
    col[m] = c[m]
    m = M(SK.Z_ASH)
    col[m] = (T(lin(112, 108, 102), 0.15, 0.25) * (0.7 + 0.5 * fbm(Pp, 1200.0, 2, seed=2706))[:, None])[m]
    return col, gr
