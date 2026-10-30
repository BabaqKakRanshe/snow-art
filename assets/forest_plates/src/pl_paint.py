"""Painter of the plates' PLProps atlas (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
Grey-green painted steel behind the plates (rust at the edges, dust on top), the map board's grey weathered spruce posts with
moss at the foot, its brown frame and battens, a darker plank roof with moss and old needles (as the airfield's pointer).
Positions: the roots stand at pl_kit.DISPLAY while baked."""
import numpy as np
from noise import ss, mixc, fbm
from psxbake import lin
from gen_paint import DUST, RUST, RUST_D, _T, _common
import pl_kit as PK

MOSS, MOSS_D, GREY_W, NEEDLE = lin(70, 86, 40), lin(46, 58, 30), lin(132, 126, 112), lin(120, 86, 46)

DRAFT_COL = {PK.Z_PSTEEL: (86, 98, 84), PK.Z_POST: (84, 64, 46), PK.Z_BOARD: (70, 48, 30), PK.Z_ROOF: (56, 44, 34)}


def paint_props(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 2401)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    m = M(PK.Z_PSTEEL)
    c = T(lin(86, 98, 84), 0.12, 0.16)
    c = mixc(c, RUST, edge * 0.45 + ss(0.72, 0.88, fbm(Pp, 60.0, 2, seed=2410)) * 0.4)
    c = mixc(c, RUST_D, ss(0.55, 0.0, ao) * 0.3)
    c = mixc(c, DUST, up * 0.25)
    col[m] = c[m]
    m = M(PK.Z_POST)
    g2 = fbm(Pp * np.array([4.0, 4.0, 0.25], np.float32), 10.0, 2, seed=2420)
    c = T(lin(84, 64, 46), 0.16, 0.14) * (0.84 + 0.24 * g2)[:, None]
    c = mixc(c, GREY_W, ss(0.45, 0.80, n_lo) * 0.35)
    c = mixc(c, MOSS_D, ss(0.35, 0.02, z) * 0.7)
    col[m] = c[m]
    m = M(PK.Z_BOARD)
    c = T(lin(70, 48, 30), 0.14, 0.14)
    c = mixc(c, lin(120, 112, 98), edge * 0.6 + ss(0.6, 0.85, n_lo) * 0.3)
    col[m] = c[m]
    m = M(PK.Z_ROOF)
    g3 = fbm(Pp * np.array([0.3, 4.0, 4.0], np.float32), 8.0, 2, seed=2430)
    c = T(lin(56, 44, 34), 0.16, 0.14) * (0.86 + 0.2 * g3)[:, None]
    c = mixc(c, MOSS, up * ss(0.55, 0.80, fbm(Pp, 12.0, 2, seed=2431)) * 0.6)
    c = mixc(c, NEEDLE, up * ss(0.70, 0.85, fbm(Pp, 30.0, 2, seed=2432)) * 0.4)
    col[m] = c[m]
    return col, gr
