"""Painter for the forest_station atlas (psxbake): paint_props(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n]).
The control room's furniture recipe (forest_main main_paint: steel_paint / flat), light wear (indoor, years of use):
- the rack: the Leitstand monitor stand's grey steel (118, 120, 116) - tone, chipped to primer / rust on the edges where
  monitors were pushed in and feet kicked, dust on the cap and the open shelf fronts, grime in the corners; the posts carry
  the row of punched holes (12 x 18 mm slots every 38 mm, dark), bolt heads at every shelf and rail, a rust ring under each;
  the black plastic foot caps
- the table: the Leitstand desks' beige laminate (196, 176, 140) worn lighter where wrists rest at the front, a faint cup
  ring, a dark brown edge band (PVC) chipped light at the corners, raw chipboard underneath; the legs and apron in the
  same grey steel; black glides"""
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, hash1
from gen_paint import _T, _common
import station_kit as SK

DUST, GRIME, RUST, RUST_D = lin(118, 112, 100), lin(64, 58, 48), lin(120, 62, 30), lin(70, 36, 20)
PRIMER = lin(150, 76, 52)
STEEL = (118, 120, 116)                       # forest_main Z_STEELF (the Leitstand CCTV stand, desk frames)
LAMINATE = (196, 176, 140)                    # forest_main Z_DESKTOP
EDGE_BAND = (62, 54, 46)
CHIPBOARD = (150, 128, 96)
PLASTIC = (30, 30, 30)
HOLE = (26, 26, 26)
BOLT = (150, 150, 146)

DRAFT_COL = {SK.Z_POST: STEEL, SK.Z_SHELF: STEEL, SK.Z_RAIL: STEEL, SK.Z_BRACE: (108, 110, 106), SK.Z_FOOT: PLASTIC,
             SK.Z_TTOP: LAMINATE, SK.Z_TLEG: STEEL, SK.Z_TFRAME: STEEL, SK.Z_TFOOT: PLASTIC}


def steel(P, N, ao, seed, chips=0.35, dust=0.25):
    """forest_main paint() indoors: tone, chips to primer / rust on the edges, dust on top, grime in the corners"""
    n_lo, n_mid, n_hi, up, cav, edge = _common(P, N, ao, seed)
    T = _T(n_lo, n_hi)
    c = T(lin(*STEEL), 0.12, 0.14)
    ch = np.clip(edge * chips + ss(0.84, 0.94, fbm(P, 40.0, 2, seed=seed + 5)) * chips * 0.4, 0, 0.9)
    c = mixc(c, np.where((ss(0.5, 0.7, n_mid) > 0.5)[:, None], PRIMER, RUST_D), ch * 0.7)
    c = mixc(c, DUST, up * dust)
    c = mixc(c, GRIME, cav * 0.4)
    return c, n_lo, n_mid, n_hi, up, cav, edge


def flat(base, P, N, ao, seed, rough=0.10, dust=0.25, edge_l=0.25):
    n_lo, n_mid, n_hi, up, cav, edge = _common(P, N, ao, seed)
    T = _T(n_lo, n_hi)
    c = T(lin(*base), rough, rough)
    c = mixc(c, c * 1.15 + 0.02, edge * edge_l)
    c = mixc(c, DUST, up * dust)
    return mixc(c, GRIME, cav * 0.35)


def paint_props(Pp, Nn, Z, ao, aa):
    n = len(Z)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    M = lambda *zz: np.isin(Z, zz)
    # ------------------------------------------------------------ the rack (its own frame)
    o = SK.DISPLAY[SK.RACK]
    P = Pp - np.array(o, np.float32)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    hx, d, h, a = SK.RK['hx'], SK.RK['d'], SK.RK['h'], SK.RK['a']
    m = M(SK.Z_POST, SK.Z_SHELF, SK.Z_RAIL, SK.Z_BRACE)
    if m.any():
        c, n_lo, n_mid, n_hi, up, cav, edge = steel(P, Nn, ao, 7101)
        # kicked and mopped low down: scuffs, a grey film; dirt where the feet stand
        low = ss(0.22, 0.0, z)
        c = mixc(c, lin(96, 94, 88), low * ss(0.4, 0.8, fbm(P, 9.0, 2, seed=7103)) * 0.5)
        c = mixc(c, PRIMER, low * ss(0.86, 0.95, fbm(P, 30.0, 2, seed=7104)) * 0.5)
        # the shelves' front lips: scraped where the monitors were slid in (each cell's middle), dust on the open tops
        front = (Nn[:, 1] < -0.7) & M(SK.Z_SHELF)
        cell = np.exp(-(dist_periodic(x, SK.RK['pitch']) / 0.10) ** 2)
        c = mixc(c, lin(150, 152, 146), front * cell * ss(0.55, 0.85, fbm(P * np.array([1, 1, 6], np.float32), 30.0, 2,
                                                                          seed=7105)) * 0.45)
        top = (Nn[:, 2] > 0.7) & M(SK.Z_SHELF)
        cap = top & (z > h - 0.01)
        c = mixc(c, DUST, cap * (0.25 + 0.25 * ss(0.4, 0.8, fbm(P, 5.0, 2, seed=7106))))          # nobody dusts the top
        c = mixc(c, DUST, top * ss(-d + 0.06, -d + 0.01, y) * 0.25)                              # the open strip in front
        # the posts: the row of punched slots on both flanges (through holes: both faces), the bolt heads
        post = M(SK.Z_POST)
        sx = np.sign(x)
        front_c = y < -d / 2
        side_face = np.abs(Nn[:, 0]) > 0.7
        fb_face = np.abs(Nn[:, 1]) > 0.7
        yc = np.where(front_c, -d + a / 2, -a / 2)
        across = np.where(side_face, y - yc, x - sx * (hx - a / 2))
        on = post & (side_face | fb_face) & (z > 0.045) & (z < h - 0.025)
        dz = dist_periodic(z, 0.038, 0.019)
        hole = on & (np.abs(across) < 0.006) & (dz < 0.009)
        c = np.where(hole[:, None], lin(*HOLE), c)
        gr = np.where(on & ~hole, np.maximum(gr, gline(np.hypot(np.maximum(np.abs(across) - 0.006, 0),
                                                                np.maximum(dz - 0.009, 0)), 0.0025, aa) * 0.5), gr)
        # bolts: one per shelf (its flange's middle) and rail on each flange, through the nearest slot
        zb = np.array([zt - SK.RK['fl'] / 2 for zt in SK.RK['shelves'] + (SK.RK['cap'],)] + [SK.RK['rail_z']], np.float32)
        zbs = np.round((zb - 0.019) / 0.038) * 0.038 + 0.019
        dzb = np.min(np.abs(z[:, None] - zbs[None, :]), axis=1)
        r = np.hypot(across, dzb)
        bolt = on & (r < 0.0075)
        c = np.where(bolt[:, None], mixc(lin(*BOLT) * (0.9 + 0.2 * n_hi)[:, None], lin(90, 90, 86), ss(0.004, 0.0075, r)), c)
        rust = on & ~bolt & (np.abs(across) < 0.008) & (z < zbs[np.argmin(np.abs(z[:, None] - zbs[None, :]), axis=1)]) & \
            (dzb < 0.022) & (hash1(np.round(z / 0.038) + np.round(x * 7) * 13 + np.round(y * 7) * 29, 5) > 0.45)
        c = mixc(c, lin(120, 64, 30), rust * ss(0.022, 0.006, dzb) * 0.45)
        # the X brace a shade darker (another batch), with bolts at the crossing
        br = M(SK.Z_BRACE)
        c = np.where(br[:, None], c * 0.92, c)
        col[m] = c[m]
    m = M(SK.Z_FOOT)
    if m.any():
        col[m] = flat(PLASTIC, P, Nn, ao, 7111, rough=0.08, dust=0.3, edge_l=0.4)[m]
    # ------------------------------------------------------------ the table (its own frame)
    o = SK.DISPLAY[SK.TABLE]
    P = Pp - np.array(o, np.float32)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    w, dd, th = SK.TB['w'], SK.TB['d'], SK.TB['h']
    m = M(SK.Z_TTOP)
    if m.any():
        n_lo, n_mid, n_hi, up, cav, edge = _common(P, Nn, ao, 7121)
        T = _T(n_lo, n_hi)
        topf = Nn[:, 2] > 0.7
        under = Nn[:, 2] < -0.7
        # laminate: a fine speckle, rubbed lighter where the wrists rest at the front, a faint cup ring right of centre
        c = T(lin(*LAMINATE), 0.06, 0.10) * (0.97 + 0.06 * fbm(P, 90.0, 1, seed=7122))[:, None]
        rub = ss(-dd / 2 + 0.22, -dd / 2 + 0.03, y) * ss(w / 2 - 0.02, w / 2 - 0.20, np.abs(x))
        c = mixc(c, lin(214, 198, 166), rub * 0.35 * (0.6 + 0.4 * n_mid))
        ring = np.abs(np.hypot(x - 0.21, y + 0.17) - 0.034)
        c = mixc(c, lin(150, 126, 92), ss(0.004, 0.0015, ring) * 0.30 * ss(0.3, 0.7, fbm(P, 50.0, 1, seed=7123)))
        c = mixc(c, DUST, topf * ss(0.55, 0.80, fbm(P, 6.0, 2, seed=7124)) * 0.12)                    # a little dust
        # the edge band (the sides and the rounded corners of the top): dark brown PVC, chipped / rubbed at the front edge
        band = ~topf & ~under
        cb = T(lin(*EDGE_BAND), 0.06, 0.12)
        chip = ss(0.80, 0.92, fbm(P, 45.0, 2, seed=7125)) * (0.4 + 0.6 * (Nn[:, 1] < -0.5))
        cb = mixc(cb, lin(150, 132, 104), chip * 0.6)
        cb = mixc(cb, lin(96, 86, 72), ss(0.6, 0.9, n_hi) * (Nn[:, 1] < -0.5) * 0.3)
        c = np.where(band[:, None], cb, c)
        # the underside: raw chipboard, speckled
        cu = T(lin(*CHIPBOARD), 0.10, 0.25) * (0.85 + 0.3 * fbm(P, 160.0, 1, seed=7126))[:, None]
        c = np.where(under[:, None], mixc(cu, GRIME, cav * 0.4), c)
        col[m] = c[m]
    m = M(SK.Z_TLEG, SK.Z_TFRAME)
    if m.any():
        c, n_lo, n_mid, n_hi, up, cav, edge = steel(P, Nn, ao, 7131, chips=0.30, dust=0.2)
        low = ss(0.20, 0.0, z)
        c = mixc(c, lin(96, 94, 88), low * ss(0.4, 0.8, fbm(P, 9.0, 2, seed=7133)) * 0.5)
        c = mixc(c, PRIMER, low * ss(0.85, 0.95, fbm(P, 30.0, 2, seed=7134)) * 0.6)                 # chair and shoe kicks
        col[m] = c[m]
    m = M(SK.Z_TFOOT)
    if m.any():
        col[m] = flat(PLASTIC, P, Nn, ao, 7141, rough=0.08, dust=0.2, edge_l=0.4)[m]
    return col, gr
