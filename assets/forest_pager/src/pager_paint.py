"""Painter for the forest_pager atlas (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
Small (the pager, 256 px at 512 px/m, as forest_gear's hand things). Station kit after a winter of use, the walkie's
recipe: black ABS rubbed grey-shiny at the edges and corners where the hand holds it, grime in the joints, the battery
door's seam and a grip texture on the back, dark grey rubber keys worn lighter in the middle, a steel hinge pin."""
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin
from gen_paint import _T, _common
import pager_kit as PK

DRAFT_COL = {PK.Z_PG: (46, 46, 50), PK.Z_PG_RUB: (60, 60, 64), PK.Z_PG_METAL: (150, 152, 156)}


def paint_small(Pp, Nn, Z, ao, aa):
    o = PK.DISPLAY['Item_Pager']
    x, y, z = Pp[:, 0] - o.x, Pp[:, 1] - o.y, Pp[:, 2] - o.z
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp * 3.0, Nn, ao, 2601)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    dust = up * (0.4 + 0.6 * ss(0.35, 0.85, fbm(Pp, 60.0, 2, seed=2602)))
    w, h, d = PK.PG['w'], PK.PG['h'], PK.PG['d']
    # ---- the body: dark grey ABS (26.10: black sank into the night), the edges rubbed light (most where the left hand holds
    # it: the lower left), grime in the joints
    m = M(PK.Z_PG)
    c = T(lin(46, 46, 50), 0.04, 0.05)                                  # 1.2: charcoal as the reference, the chamfers worn light
    held = ss(0.030, 0.0, z) * ss(0.02, -0.03, x)                       # the lower left corner: the thumb and the palm
    # 1.2: the wear sits on the chamfers only (normals off the axes); the shared AO edge mask spotted flat faces like camo
    chamfer = ss(0.985, 0.94, np.abs(Nn).max(axis=1)) * (0.75 + 0.25 * n_hi)
    c = mixc(c, lin(140, 140, 144), chamfer * (0.60 + 0.30 * held))
    c = mixc(c, lin(22, 22, 24), cav * 0.5)
    c = mixc(c, lin(96, 94, 90), dust * 0.25)
    col[m] = c[m]
    back = (Nn[:, 1] > 0.9) & (y > d / 2 - 0.0005)
    door = back & (np.abs(x) < 0.026) & (z > 0.006) & (z < 0.036)          # the battery door's seam on the back
    g = door * np.maximum(gline(np.abs(np.abs(x) - 0.026), 0.0005, aa) * (z > 0.006) * (z < 0.036),
                          gline(np.minimum(np.abs(z - 0.006), np.abs(z - 0.036)), 0.0005, aa) * (np.abs(x) < 0.026))
    grip = back & (np.abs(x) > 0.028) & (z > 0.008) & (z < h - 0.012)       # ribs either side of the door
    g = np.maximum(g, grip * gline(dist_periodic(z, 0.003), 0.0005, aa) * 0.7)
    gr = np.where(m, g, gr)
    # ---- the keys and the switch: light grey rubber (they must read against the body), the middle worn lighter by the thumb
    m = M(PK.Z_PG_RUB)
    c = T(lin(60, 60, 64), 0.05, 0.06)                                  # 1.2: dark rubber, the signs are printed on the faces
    c = mixc(c, lin(104, 104, 108), ss(0.985, 0.94, np.abs(Nn).max(axis=1)) * 0.45)
    col[m] = c[m]
    # ---- the clip's hinge pin
    m = M(PK.Z_PG_METAL)
    c = T(lin(150, 152, 156), 0.05, 0.08)
    col[m] = mixc(c, lin(90, 90, 92), cav * 0.5)[m]
    return col, gr
