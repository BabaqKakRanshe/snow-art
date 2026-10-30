"""Painter for the forest_beer Small atlas (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
The pager's recipe (hand things, 512 px / m): the tinplate of 1991 (a warm grey steel, rings turned into it, a few rust
specks at the foot), the brighter rolled rim and foot ring, the lid with its countersink groove and the score line round the
opening, the aluminium tab, the dark inside."""
import numpy as np
from noise import ss, mixc, fbm, groove as gline
from psxbake import lin
from gen_paint import _T, _common
import beer_kit as BK

DRAFT_COL = {BK.Z_METAL: (150, 148, 142), BK.Z_LID: (170, 170, 168), BK.Z_TAB: (196, 198, 200), BK.Z_INSIDE: (34, 26, 18),
             BK.Z_RIM: (190, 188, 182)}
OFFS = np.array([tuple(v) for v in BK.DISPLAY.values()], np.float32)


def local(Pp):
    """each point in its own can's frame (the nearest display offset)"""
    d = ((Pp[:, None, :2] - OFFS[None, :, :2]) ** 2).sum(2)
    o = OFFS[d.argmin(1)]
    return Pp[:, 0] - o[:, 0], Pp[:, 1] - o[:, 1], Pp[:, 2] - o[:, 2]


def paint_small(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp * 3.0, Nn, ao, 2901)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(150, 148, 142), (n, 1))
    gr = np.zeros(n, np.float32)
    x, y, z = local(Pp)
    r = np.hypot(x, y)
    scratch = ss(0.82, 0.95, fbm(Pp, 500.0, 2, seed=2902))
    rust = ss(0.78, 0.9, fbm(Pp, 260.0, 2, seed=2903)) * (z < 0.012)
    # ---- the steel shoulder, neck and bottom: turned rings, a few rust specks low down
    m = M(BK.Z_METAL)
    c = T(lin(150, 148, 142), 0.05, 0.07)
    c = mixc(c, lin(196, 194, 188), gline(np.abs(np.sin(z * 2600.0)), 0.25, aa * 2600.0) * 0.25 * (np.abs(Nn[:, 2]) < 0.9))
    c = mixc(c, lin(206, 204, 198), scratch * 0.3)
    c = mixc(c, lin(120, 72, 40), rust * 0.6)
    c = mixc(c, lin(80, 76, 70), cav * 0.4)
    col[m] = c[m]
    m = M(BK.Z_RIM)
    c = T(lin(190, 188, 182), 0.04, 0.06)
    c = mixc(c, lin(226, 224, 218), ss(0.6, 0.95, np.abs(Nn[:, 2])) * 0.35)        # the rolled edge catches the light
    c = mixc(c, lin(120, 72, 40), rust * 0.5)
    col[m] = c[m]
    # ---- the lid: silver, the countersink ring near the rim, the score line round the opening, the rivet's ring
    m = M(BK.Z_LID)
    c = T(lin(170, 170, 168), 0.04, 0.06)
    cs = gline(np.abs(r - 0.0245), 0.0005, aa)
    fx, fy = BK.FLAP['c']
    e = np.sqrt(((x - fx) / BK.FLAP['ax']) ** 2 + ((y - fy) / BK.FLAP['ay']) ** 2)
    score = gline(np.abs(e - 1.12), 0.05, aa * 140.0)
    rv = gline(np.abs(r - 0.0030), 0.0004, aa)
    g = np.maximum(np.maximum(cs, score * 0.8), rv * 0.7)
    c = mixc(c, lin(214, 214, 210), scratch * 0.3)
    col[m] = c[m]
    gr = np.where(m, g, gr)
    m = M(BK.Z_TAB)
    col[m] = mixc(T(lin(196, 198, 200), 0.04, 0.05), lin(232, 234, 236), ss(0.9, 1.0, np.abs(Nn[:, 2])) * 0.3)[m]
    m = M(BK.Z_INSIDE)                                                         # the dark inside, a glint of beer at the floor
    col[m] = mixc(lin(26, 20, 14), lin(70, 50, 20), (Nn[:, 2] > 0.9) * 0.4)[m]
    return col, gr
