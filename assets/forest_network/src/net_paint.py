"""Painter for the forest network props' atlas (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
NetProps: the snow pole (orange fibreglass gone pale in the sun, black top and rings, a white reflector, mud at the foot);
the culvert's end (old cast concrete of the 70s: shuttering lines, lime runs, moss from the damp foot, the pipe's inside
dark and wet with a rust-brown line at the water mark, a sediment crust on the apron); the compartment stones (grey granite
with feldspar speckle and lichen, the top painted white long ago, chipped). Positions: the roots stand at net_kit.DISPLAY."""
import numpy as np
from noise import ss, mixc, fbm
from psxbake import lin
from gen_paint import DUST, RUST, RUST_D, _T, _common
import gen_kit as K
import net_kit as NK

ORANGE, ORANGE_P, BLACK, REFL = lin(214, 92, 26), lin(226, 138, 74), lin(26, 26, 26), lin(226, 228, 224)
CONC, CONC_D, CONC_L, LIME = lin(140, 140, 134), lin(92, 92, 88), lin(172, 170, 162), lin(196, 194, 184)
MOSS, MOSS_D, MUD, WET = lin(70, 86, 40), lin(46, 58, 30), lin(92, 78, 60), lin(40, 40, 38)
GRAN, GRAN_D, GRAN_L, LICHEN, PAINT_W = lin(128, 126, 120), lin(86, 84, 80), lin(170, 166, 156), lin(112, 120, 84), lin(220, 220, 212)

DRAFT_COL = {NK.Z_POLE: (214, 92, 26), NK.Z_REFL: (226, 228, 224), NK.Z_HEAD: (140, 140, 134), NK.Z_PIPE_IN: (70, 70, 66),
             NK.Z_PIPE_OUT: (130, 130, 124), NK.Z_APRON: (110, 108, 100), NK.Z_PLUG: (12, 12, 12), NK.Z_STONE: (128, 126, 120),
             NK.Z_STONE_TOP: (220, 220, 212), NK.Z_SPOST: (80, 62, 46), NK.Z_SBOARD: (70, 48, 30), K.Z_STEELBLK: (36, 36, 36)}
GREY_W = lin(132, 126, 112)


def paint_props(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 2601)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    # ---- the snow pole: orange, black top 0.25 m and rings at 1.05 / 1.35 m, bleached on the sunny side, mud at the foot
    m = M(NK.Z_POLE)
    black = (z > NK.POLE_TOP - 0.25) | (np.abs(z - 1.05) < 0.06) | (np.abs(z - 1.35) < 0.06)
    c = np.where(black[:, None], T(BLACK, 0.10, 0.14), T(ORANGE, 0.10, 0.12))
    c = mixc(c, ORANGE_P, (~black) * ss(0.3, 0.9, -Nn[:, 1] * 0.5 + 0.5) * 0.35)
    c = mixc(c, lin(120, 112, 100), edge * 0.25 + ss(0.72, 0.88, fbm(Pp, 30.0, 2, seed=2610)) * 0.25)
    c = mixc(c, MUD, ss(0.35, 0.0, z) * 0.75)
    col[m] = c[m]
    m = M(NK.Z_REFL)
    col[m] = mixc(T(REFL, 0.06, 0.08), DUST, ss(0.6, 0.85, fbm(Pp, 40.0, 2, seed=2611)) * 0.3)[m]
    # ---- the culvert: cast concrete, shuttering lines every 0.3 m, lime runs from the coping, moss and damp at the foot
    for zz in (NK.Z_HEAD, NK.Z_PIPE_OUT, NK.Z_APRON):
        m = M(zz)
        c = T(CONC, 0.14, 0.18)
        c = mixc(c, CONC_L, ss(0.55, 0.80, fbm(Pp, 0.8, 3, seed=2620 + zz)) * 0.3)
        c = mixc(c, CONC_D, ss(0.60, 0.85, fbm(Pp, 3.0, 2, seed=2622 + zz)) * 0.35 + cav * 0.4)
        shut = np.abs(((z + 0.15) / 0.30) % 1.0 - 0.5) > 0.47
        c = mixc(c, CONC_D, shut * up.__rsub__(1.0) * 0.35)
        runs = ss(0.62, 0.80, fbm(Pp * np.array([6.0, 6.0, 0.4], np.float32), 4.0, 2, seed=2624)) * ss(0.6, 1.5, z)
        c = mixc(c, LIME, runs * 0.45)
        damp = ss(0.45, -0.05, z) * (0.6 + 0.4 * fbm(Pp, 4.0, 2, seed=2625))
        c = mixc(c, WET, damp * 0.5)
        c = mixc(c, MOSS, damp * ss(0.45, 0.75, fbm(Pp, 6.0, 2, seed=2626)) * 0.7 + up * ss(0.6, 0.85, fbm(Pp, 5.0, 2, seed=2627)) * 0.35)
        if zz == NK.Z_APRON:
            c = mixc(c, MUD, ss(0.35, 0.70, fbm(Pp, 2.0, 2, seed=2628)) * 0.6)
        col[m] = c[m]
    m = M(NK.Z_PIPE_IN)
    c = T(lin(70, 70, 66), 0.12, 0.16)
    c = mixc(c, WET, ss(0.35, 0.10, z) * 0.7)
    c = mixc(c, RUST_D, np.exp(-((z - 0.28) / 0.04) ** 2) * 0.6)                 # the water mark
    c = mixc(c, lin(20, 20, 20), ss(0.1, 1.0, y - NK.DISPLAY['NET_CulvertHead'].y) * 0.8)   # darker into the pipe
    col[m] = c[m]
    m = M(NK.Z_PLUG)
    col[m] = lin(8, 8, 8)
    # ---- the stones: grey granite, speckle, lichen on the north and up, the white top chipped
    m = M(NK.Z_STONE)
    c = T(GRAN, 0.16, 0.18)
    spk = fbm(Pp, 60.0, 1, seed=2640)
    c = mixc(c, GRAN_L, ss(0.68, 0.80, spk) * 0.6)
    c = mixc(c, GRAN_D, ss(0.32, 0.20, spk) * 0.6 + cav * 0.3)
    c = mixc(c, LICHEN, ss(0.55, 0.80, fbm(Pp, 9.0, 2, seed=2641)) * (0.4 + 0.4 * ss(0.0, 0.8, Nn[:, 1])) * 0.6)
    c = mixc(c, MUD, ss(0.15, -0.05, z) * 0.7)
    col[m] = c[m]
    m = M(NK.Z_STONE_TOP)
    c = T(PAINT_W, 0.08, 0.10)
    c = mixc(c, GRAN, ss(0.62, 0.80, fbm(Pp, 25.0, 2, seed=2650)) * 0.8)     # chipped to the granite
    c = mixc(c, LICHEN, ss(0.75, 0.88, fbm(Pp, 12.0, 2, seed=2651)) * 0.4)
    col[m] = c[m]
    # ---- the pointers: weathered spruce post with moss at the foot, the stained arrow board (as the airfield's)
    m = M(NK.Z_SPOST)
    g2 = fbm(Pp * np.array([4.0, 4.0, 0.25], np.float32), 10.0, 2, seed=2670)
    c = T(lin(84, 64, 46), 0.16, 0.14) * (0.84 + 0.24 * g2)[:, None]
    c = mixc(c, GREY_W, ss(0.45, 0.80, n_lo) * 0.35)
    c = mixc(c, MOSS_D, ss(0.35, 0.02, z) * 0.7)
    col[m] = c[m]
    m = M(NK.Z_SBOARD)
    c = T(lin(70, 48, 30), 0.14, 0.14)
    c = mixc(c, lin(120, 112, 98), edge * 0.6 + ss(0.6, 0.85, n_lo) * 0.3)
    col[m] = c[m]
    # ---- the barrier tape: red and white diagonal bands 0.10 m, a little dirty
    m = M(NK.Z_TAPE)
    band = (((x + z) / 0.10) % 2.0) < 1.0
    c = np.where(band[:, None], T(lin(196, 32, 30), 0.06, 0.08), T(lin(232, 230, 224), 0.05, 0.06))
    c = mixc(c, lin(120, 112, 100), ss(0.7, 0.9, fbm(Pp, 30.0, 2, seed=2680)) * 0.3)
    col[m] = c[m]
    # ---- the tent's canvas: faded olive, darker seams and damp at the hem; the fire pit's ash and charcoal
    m = M(NK.Z_CANVAS)
    c = T(lin(86, 90, 62), 0.10, 0.14)
    c = mixc(c, lin(120, 120, 96), ss(0.55, 0.85, fbm(Pp, 6.0, 2, seed=2690)) * 0.4)
    c = mixc(c, lin(52, 54, 40), ss(0.25, 0.0, z) * 0.6)
    col[m] = c[m]
    m = M(NK.Z_ASH)
    c = T(lin(40, 38, 36), 0.12, 0.2)
    c = mixc(c, lin(110, 108, 104), ss(0.5, 0.8, fbm(Pp, 30.0, 2, seed=2691)) * 0.5)
    col[m] = c[m]
    # ---- the weather hut: grey-brown planks (horizontal boards), dull tin, the window warm and bright
    m = M(NK.Z_PLANK)
    board = np.abs(((z + 0.07) / 0.14) % 1.0 - 0.5) > 0.46
    c = T(lin(96, 82, 66), 0.12, 0.16)
    c = mixc(c, lin(60, 50, 40), board * 0.6)
    c = mixc(c, GREY_W, ss(0.5, 0.85, n_lo) * 0.35)
    col[m] = c[m]
    m = M(NK.Z_TIN)
    c = T(lin(112, 116, 118), 0.10, 0.14)
    c = mixc(c, RUST, ss(0.6, 0.85, fbm(Pp, 8.0, 2, seed=2701)) * 0.5)
    col[m] = c[m]
    m = M(NK.Z_WINLIT)
    col[m] = T(lin(255, 196, 110), 0.04, 0.05)[m]
    m = M(K.Z_STEELBLK)
    col[m] = mixc(T(lin(36, 36, 36), 0.12, 0.2), RUST, ss(0.55, 0.80, fbm(Pp, 50.0, 2, seed=2660)) * 0.7)[m]
    return col, gr
