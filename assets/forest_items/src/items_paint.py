"""Painter for the Forest items' atlas Props (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n]).
The generator shed's wear language (gen_paint.paint_props, base_paint) on the station's small things: paper going
yellow and grey at the edges, cardboard with water stains and printed stencils, enamel chipped to black iron at the
rims, tinplate with rust spots, galvanised spangle, aluminium dulled and sooted where it stood on a stove, paint
chipped to primer and steel on the edges, plastics scuffed pale, rubber and leather with dust and mud, glass dark
with one hard highlight, fabrics with their weave, the rug's pattern, mould on the bread.
Positions arrive in the bake layout (items_build: LAYOUT / CELLS): each texel goes back to its item's own frame."""
import math
import numpy as np
from noise import ss, fbm, dist_periodic, groove as gline
from noise import mixc as _mixc


def mixc(c, col, t):
    return _mixc(c, col, np.broadcast_to(np.asarray(t, np.float32), (c.shape[0],)))
from psxbake import lin, hash1
from gen_paint import OIL, GRIME, DUST, RUST, RUST_D, _T, _common
import pxfont as F
import road_tex as RTX
import items_kit as IK

LAYOUT, CELLS = {}, {}
PRIO = (IK.Z_PAINT_R, IK.Z_PL_R, IK.Z_PAINT_Y, IK.Z_PL_BL, IK.Z_PL_GR, IK.Z_ENBL, IK.Z_CABLE_O, IK.Z_FILTER, IK.Z_PP_R,
        IK.Z_PP_B, IK.Z_CLOTH_R, IK.Z_PAINT_B, IK.Z_GLASS_GR, IK.Z_BRASS, IK.Z_RUG,
        IK.Z_ENG, IK.Z_PAINT_G, IK.Z_CLOTH_G)            # the greens apart from the olive of the can and the pack
BASE = {IK.Z_PAPER: (226, 222, 208), IK.Z_PAPERY: (212, 202, 172), IK.Z_CARD: (176, 144, 100), IK.Z_CARDG: (130, 126, 116),
        IK.Z_CLOTH_R: (124, 42, 36), IK.Z_CLOTH_G: (52, 82, 58), IK.Z_CLOTH_B: (44, 58, 96), IK.Z_PP_B: (48, 74, 132),
        IK.Z_PP_R: (160, 44, 36), IK.Z_TIN: (176, 178, 174), IK.Z_RUSTT: (120, 70, 40), IK.Z_ENW: (226, 226, 218),
        IK.Z_ENG: (70, 110, 72), IK.Z_ENBK: (32, 36, 48), IK.Z_ENBL: (52, 86, 150), IK.Z_STEELB: (44, 44, 44),
        IK.Z_STEEL: (170, 172, 170), IK.Z_GALV: (150, 154, 152), IK.Z_ALU: (180, 182, 184), IK.Z_BRASS: (182, 148, 72),
        IK.Z_CHROME: (196, 198, 200), IK.Z_PAINT_R: (170, 36, 28), IK.Z_PAINT_O: (84, 90, 58), IK.Z_PAINT_B: (36, 76, 150),
        IK.Z_PAINT_Y: (222, 182, 40), IK.Z_PAINT_G: (48, 92, 60), IK.Z_PL_BK: (28, 28, 28), IK.Z_PL_BE: (196, 182, 150),
        IK.Z_PL_R: (176, 40, 32), IK.Z_PL_BL: (44, 84, 160), IK.Z_PL_GR: (52, 120, 64), IK.Z_PL_W: (226, 226, 220),
        IK.Z_RUBBER: (34, 34, 32), IK.Z_WOOD: (150, 108, 64), IK.Z_PINE: (188, 156, 108), IK.Z_FAB_O: (88, 96, 62),
        IK.Z_FAB_B: (52, 70, 104), IK.Z_FAB_G: (118, 116, 110), IK.Z_JUTE: (170, 140, 92), IK.Z_LEATHER: (30, 28, 26),
        IK.Z_GLASS_BR: (70, 36, 14), IK.Z_GLASS_GR: (36, 70, 40), IK.Z_GLASS_CL: (150, 162, 158), IK.Z_BREAD: (150, 98, 52),
        IK.Z_CRUMB: (210, 186, 140), IK.Z_SOAP: (220, 196, 170), IK.Z_ROPE: (168, 140, 96), IK.Z_STRAW: (180, 150, 90),
        IK.Z_MOPS: (196, 190, 170), IK.Z_BAG: (24, 24, 26), IK.Z_FOAM: (40, 40, 42), IK.Z_CIG: (226, 222, 210),
        IK.Z_FILTER: (196, 120, 60), IK.Z_ASH: (110, 108, 104), IK.Z_TERRY: (60, 90, 140), IK.Z_RUG: (150, 60, 46),
        IK.Z_PICKLE: (96, 118, 58), IK.Z_FOOD: (156, 110, 60), IK.Z_CABLE_O: (210, 100, 30), IK.Z_TAPE: (176, 140, 80),
        IK.Z_HARDB: (112, 82, 56), IK.Z_GLASS_ASH: (120, 150, 130), IK.Z_TISSUE: (232, 230, 224), IK.Z_GREYM: (104, 110, 108),
        IK.Z_ENBL_IN: (222, 224, 220), IK.Z_COFFEE: (60, 40, 26)}
LIGHT = np.array([-0.40, -0.60, 0.70], np.float32) / np.linalg.norm([-0.40, -0.60, 0.70])
PRIMER = lin(126, 122, 112)
IRON = lin(40, 40, 42)
MUD = lin(84, 72, 56)


def draft_colour(z):
    return BASE.get(z, (128, 128, 128))


def _locals(Pp):
    names = list(CELLS)
    if not names:
        return Pp.copy(), np.array([''] * len(Pp), dtype=object)
    own = np.array([''] * len(Pp), dtype=object)
    off = np.zeros((len(Pp), 3), np.float32)
    for n in names:
        x0, x1, y0, y1 = CELLS[n]
        m = (Pp[:, 0] >= x0) & (Pp[:, 0] < x1) & (Pp[:, 1] >= y0) & (Pp[:, 1] < y1)
        own[m] = n
        off[m] = LAYOUT[n]
    return Pp - off, own


def stencil(u, v, lines, cu, cv, px, font=F.F57):
    """texels whose face coordinates (u right, v up, metres) fall on the text lines (centred at cu, cv; px = one font pixel)"""
    out = np.zeros(len(u), bool)
    ms = [RTX.prop_mask(t, font, 1) for t in lines]
    H = sum(m.shape[0] for m in ms) + 2 * (len(ms) - 1)
    top = cv + H * px / 2
    for m in ms:
        h, w = m.shape
        ci = np.floor((u - cu) / px + w / 2.0).astype(np.int64)
        ri = np.floor((top - v) / px).astype(np.int64)
        ok = (ci >= 0) & (ci < w) & (ri >= 0) & (ri < h)
        out[ok] |= m[ri[ok], ci[ok]]
        top -= (h + 2) * px
    return out


def paint_items(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    Pl, own = _locals(Pp)
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 3101)
    n_fine = fbm(Pp, 140.0, 2, seed=3105)
    edge2 = np.clip(edge + ss(0.80, 0.92, n_fine) * ss(0.88, 0.98, ao) * 0.6, 0, 1)        # finer chips for small things
    T = _T(n_lo, n_hi)
    gr = np.zeros(n, np.float32)
    col = np.tile(lin(128, 128, 128), (n, 1))
    for zz, rgb in BASE.items():
        m = Z == zz
        if m.any():
            col[m] = T(lin(*rgb), 0.10, 0.12)[m]
    M = lambda zz: Z == zz
    I = lambda name: own == name
    spec = ss(0.78, 0.96, Nn @ LIGHT)
    side = np.abs(Nn[:, 2]) < 0.5

    # ---- paper, card: yellowing, grime at the edges and in folds, water stains
    for zz in (IK.Z_PAPER, IK.Z_PAPERY):
        m = M(zz)
        c = mixc(col, lin(196, 184, 150), ss(0.55, 0.85, n_mid) * 0.35)
        c = mixc(c, lin(120, 112, 96), np.clip(cav * 0.55 + edge * 0.25, 0, 0.7))
        c = mixc(c, lin(150, 140, 120), ss(0.62, 0.80, fbm(Pp, 70.0, 2, seed=3111)) * 0.25)      # creases
        col[m] = c[m]
    m = M(IK.Z_CARD)
    c = mixc(col, lin(140, 112, 76), ss(0.55, 0.80, fbm(Pp, 6.0, 3, seed=3121)) * 0.45)            # water stains
    c = mixc(c, lin(196, 170, 128), edge * 0.35)                                                 # scuffed corners
    c = mixc(c, lin(98, 78, 56), cav * 0.4)
    c = mixc(c, DUST, up * 0.25)
    flute = gline(dist_periodic(np.where(np.abs(Nn[:, 0]) > 0.6, y, x) + 0.0 * z, 0.006), 0.0012, aa) * side
    col[m] = c[m]
    gr = np.where(m, flute * 0.2, gr)
    m = M(IK.Z_CARDG)
    col[m] = mixc(col, lin(90, 88, 82), cav * 0.4)[m]
    m = M(IK.Z_TAPE)
    c = col * (0.9 + 0.25 * spec)[:, None]
    col[m] = mixc(c, lin(140, 110, 60), ss(0.6, 0.85, n_hi) * 0.4)[m]
    m = M(IK.Z_HARDB)
    col[m] = mixc(col, lin(80, 58, 40), cav * 0.5 + edge * 0.2)[m]

    # ---- book cloth, binders
    for zz in (IK.Z_CLOTH_R, IK.Z_CLOTH_G, IK.Z_CLOTH_B):
        m = M(zz)
        weave = 0.92 + 0.10 * ((np.floor(x / 0.003) + np.floor(y / 0.003) + np.floor(z / 0.003)) % 2)
        c = col * weave[:, None]
        c = mixc(c, lin(178, 166, 140), np.clip(edge * 0.75, 0, 0.7))                            # frayed corners
        c = mixc(c, GRIME, cav * 0.35 + up * ss(0.6, 0.9, n_mid) * 0.2)
        col[m] = c[m]
    for zz in (IK.Z_PP_B, IK.Z_PP_R):
        m = M(zz)
        c = col * (0.92 + 0.15 * spec)[:, None]
        c = mixc(c, lin(200, 196, 190), ss(0.86, 0.96, fbm(Pp * np.array([1, 6, 1], np.float32), 60.0, 2, seed=3131)) * 0.3)
        col[m] = mixc(c, DUST, up * 0.25 + cav * 0.2)[m]

    # ---- metals
    m = M(IK.Z_TIN) | M(IK.Z_RUSTT)
    spang = fbm(Pp, 160.0, 1, seed=3141)
    c = col * (0.88 + 0.22 * spang)[:, None] * (0.9 + 0.2 * spec)[:, None]
    rusty = ss(0.62, 0.80, n_mid) * (0.6 + 0.4 * edge)
    rusty = np.where(I('Item_PaintCan') | I('Item_TinLying') | I('Item_TinOpen'), rusty, rusty * 0.5)
    c = mixc(c, RUST, np.clip(rusty * 0.8 + cav * 0.25, 0, 0.85))
    c = mixc(c, lin(70, 66, 60), cav * 0.4)
    col[m] = c[m]
    m = M(IK.Z_RUSTT)
    col[m] = mixc(col, RUST_D, 0.6)[m]
    for zz in (IK.Z_ENW, IK.Z_ENG, IK.Z_ENBL, IK.Z_ENBK, IK.Z_ENBL_IN):                          # enamel, chipped to iron
        m = M(zz)
        c = col * (0.94 + 0.12 * spec)[:, None]
        chips = np.clip(edge2 * 0.9 + ss(0.88, 0.95, fbm(Pp, 90.0, 2, seed=3151)) * 0.6, 0, 1)
        c = mixc(c, IRON, chips * (0.9 if zz != IK.Z_ENBK else 0.3))
        c = mixc(c, lin(150, 140, 110), cav * 0.35)
        col[m] = c[m]
    m = M(IK.Z_ENBL_IN)                                                                       # the enamel bucket inside: a waterline
    line = np.exp(-((z - 0.215) / 0.006) ** 2)
    c = mixc(col, lin(190, 186, 170), line * 0.6)
    c = mixc(c, lin(150, 156, 160), ss(0.215, 0.18, z) * 0.35)
    col[m] = c[m]
    m = M(IK.Z_STEELB)
    c = col * (0.9 + 0.35 * spec)[:, None]
    c = mixc(c, RUST, np.clip(edge2 * 0.6 + ss(0.72, 0.86, n_mid) * 0.3, 0, 0.7))
    c = np.where(I('Item_Pan')[:, None], mixc(c, lin(30, 26, 22), up * 0.5), c)               # seasoned, oily inside
    col[m] = c[m]
    m = M(IK.Z_STEEL)
    c = col * (0.85 + 0.30 * spec)[:, None]
    scratch = ss(0.86, 0.95, fbm(Pp * np.array([1, 8, 1], np.float32), 50.0, 2, seed=3161)) * 0.4
    c = mixc(c, lin(220, 222, 220), scratch)
    c = mixc(c, RUST, ss(0.74, 0.88, n_mid) * 0.45 + cav * 0.2)
    col[m] = c[m]
    m = M(IK.Z_GALV)
    spang = fbm(Pp, 120.0, 1, seed=3171)
    c = col * (0.86 + 0.24 * spang)[:, None]
    c = mixc(c, lin(196, 198, 192), ss(0.78, 0.90, fbm(Pp, 40.0, 2, seed=3172)) * 0.35)        # white rust
    c = mixc(c, lin(70, 70, 66), cav * 0.5)
    c = np.where(I('Item_Funnel')[:, None], mixc(c, OIL, ss(0.4, 0.75, n_mid) * 0.45), c)       # diesel-stained funnel
    col[m] = c[m]
    m = M(IK.Z_ALU)
    c = col * (0.84 + 0.25 * spec)[:, None]
    c = mixc(c, lin(120, 120, 118), ss(0.55, 0.85, n_mid) * 0.35 + cav * 0.3)
    soot = (I('Item_Kettle') | I('Item_Pot')) * ss(0.045, 0.0, z)
    c = mixc(c, lin(26, 24, 22), np.clip(soot * (0.6 + 0.4 * n_hi), 0, 0.9))
    can = I('Item_CanCrushed')                                                              # a drinks can: the print in rags
    band_ = (np.floor(fbm(Pp, 30.0, 2, seed=3175) * 6) % 3)
    c = np.where(can[:, None], np.where((band_ == 0)[:, None], lin(40, 110, 60) * np.ones((n, 1), np.float32),
                                        np.where((band_ == 1)[:, None], lin(220, 220, 214) * np.ones((n, 1), np.float32), c)), c)
    col[m] = c[m]
    m = M(IK.Z_BRASS)
    c = col * (0.9 + 0.3 * spec)[:, None]
    c = mixc(c, lin(96, 84, 52), ss(0.5, 0.8, n_mid) * 0.5 + cav * 0.4)
    col[m] = mixc(c, lin(222, 192, 110), edge * 0.6)[m]
    m = M(IK.Z_CHROME)
    c = col * (0.65 + 0.55 * spec)[:, None]
    col[m] = mixc(c, RUST, ss(0.80, 0.92, n_mid) * 0.35)[m]

    # ---- paints: chipped at the edges to primer, then steel; dust on top, mud low down
    for zz in (IK.Z_PAINT_R, IK.Z_PAINT_O, IK.Z_PAINT_B, IK.Z_PAINT_Y, IK.Z_PAINT_G, IK.Z_GREYM):
        m = M(zz)
        c = col
        if zz == IK.Z_GREYM:                                                                 # hammered finish
            c = c * (0.86 + 0.24 * fbm(Pp, 220.0, 1, seed=3181))[:, None]
        c = mixc(c, PRIMER, np.clip(edge2 * 0.75, 0, 0.75))
        c = mixc(c, lin(80, 76, 70), ss(0.80, 0.95, edge2) * 0.6)
        c = mixc(c, DUST, up * ss(0.5, 0.85, n_mid) * 0.35)
        c = mixc(c, MUD, ss(0.06, 0.0, z) * 0.5 * ~(I('Item_Flashlight') | I('Item_Key_Generator')))
        col[m] = c[m]
    m = M(IK.Z_PAINT_B) & I('Item_OilCan')                                                    # oil run from the cap
    run = ss(0.15, 0.0, np.abs(x - 0.068)) * ss(0.25, 0.10, z) * ss(0.4, 0.8, fbm(Pp * np.array([1, 1, 0.2], np.float32), 30.0, 2, seed=3183))
    col[m] = mixc(col, OIL, np.clip(run * 0.8 + up * 0.25, 0, 0.8))[m]
    m = M(IK.Z_PAINT_O) & I('Item_Jerrycan20')                                                # fuel spills down from the spout
    run = ss(0.06, 0.0, np.abs(x - 0.13)) * ss(0.48, 0.30, z) * (np.abs(Nn[:, 0]) > 0.5)
    col[m] = mixc(col, OIL, np.clip(run * 0.7, 0, 0.7))[m]
    m = M(IK.Z_TIN) & I('Item_PaintCan')                                                      # paint dripped over the rim
    drip = (z > 0.12) & (ss(0.55, 0.70, fbm(Pp * np.array([3, 3, 0.25], np.float32), 25.0, 2, seed=3185)) > 0.5)
    col[m & drip] = lin(40, 96, 70) * (0.9 + 0.1 * n_hi[m & drip])[:, None]

    # ---- plastics, rubber
    for zz in (IK.Z_PL_BK, IK.Z_PL_BE, IK.Z_PL_R, IK.Z_PL_BL, IK.Z_PL_GR, IK.Z_PL_W):
        m = M(zz)
        c = col * (0.92 + 0.18 * spec)[:, None]
        c = mixc(c, lin(150, 148, 140) if zz == IK.Z_PL_BK else lin(240, 236, 226), edge * 0.35)
        c = mixc(c, GRIME, cav * 0.45)
        if zz == IK.Z_PL_BE:
            c = mixc(c, lin(180, 160, 110), ss(0.5, 0.8, n_mid) * 0.35)                       # yellowed
        col[m] = c[m]
    m = M(IK.Z_RUBBER)
    col[m] = mixc(mixc(col, DUST, up * 0.35), MUD, ss(0.03, 0.0, z) * 0.5)[m]
    m = M(IK.Z_FOAM)
    col[m] = (col * (0.8 + 0.4 * (fbm(Pp, 300.0, 1, seed=3191) > 0.5)[:, None]))[m]

    # ---- wood
    m = M(IK.Z_WOOD)
    g = fbm(Pp * np.array([0.25, 0.25, 6.0], np.float32), 30.0, 2, seed=3201)
    gx = fbm(Pp * np.array([6.0, 0.25, 0.25], np.float32), 30.0, 2, seed=3202)
    along_z = (I('Item_Broom') | I('Item_Mop') | I('Item_Bucket') | I('Item_BucketWater'))
    grain = np.where(along_z, g, gx)
    c = col * (0.85 + 0.25 * grain)[:, None] * (0.95 + 0.15 * spec)[:, None]
    held = along_z * ss(0.7, 1.1, z) * ss(1.4, 1.2, z)
    c = mixc(c, lin(70, 50, 34), np.clip(held * 0.5 + cav * 0.4, 0, 0.7))
    col[m] = c[m]
    m = M(IK.Z_PINE)
    g = fbm(Pp * np.array([6.0, 0.3, 0.3], np.float32), 25.0, 2, seed=3211)
    c = col * (0.86 + 0.24 * g)[:, None]
    c = mixc(c, lin(140, 132, 116), ss(0.5, 0.8, n_lo) * 0.35)
    c = mixc(c, lin(96, 80, 58), cav * 0.5)
    col[m] = c[m]
    gr = np.where(m, gline(dist_periodic(z - 0.02, 0.13), 0.004, aa) * 0.5 * side, gr)

    # ---- fabrics, fibres
    weave = ((np.floor(x / 0.004) + np.floor(y / 0.004) + np.floor(z / 0.004)) % 2).astype(np.float32)
    for zz in (IK.Z_FAB_O, IK.Z_FAB_B, IK.Z_FAB_G, IK.Z_JUTE, IK.Z_TERRY):
        m = M(zz)
        c = col * (0.90 + 0.14 * weave)[:, None]
        c = mixc(c, lin(160, 160, 150), up * ss(0.4, 0.8, n_mid) * (0.25 if zz == IK.Z_FAB_B else 0.12))   # worn pale
        c = mixc(c, GRIME, cav * 0.5)
        c = mixc(c, MUD, ss(0.05, 0.0, z) * 0.35 * (I('Item_Backpack') | I('Item_Sack')))
        col[m] = c[m]
    m = M(IK.Z_FAB_G) & I('Item_Rag')
    col[m] = mixc(col, OIL, ss(0.45, 0.75, n_mid) * 0.7)[m]
    m = M(IK.Z_TERRY) & I('Item_Towel')
    stripe = (np.abs(np.abs(x) - 0.12) < 0.012)
    col[m & stripe] = lin(226, 226, 220) * (0.9 + 0.1 * weave[m & stripe])[:, None]
    m = M(IK.Z_LEATHER)
    crease = ss(0.62, 0.75, fbm(Pp * np.array([1, 1, 3], np.float32), 70.0, 2, seed=3231))
    c = mixc(col, lin(90, 82, 74), crease * 0.4 + edge * 0.35)
    c = mixc(c, MUD, ss(0.06, 0.02, z) * 0.7)
    col[m] = c[m]
    m = M(IK.Z_ROPE)
    tw = dist_periodic(x * 0.7 + y * 0.7 + z * 3.0, 0.012) / 0.006
    col[m] = mixc(col * (0.82 + 0.25 * tw)[:, None], GRIME, cav * 0.4)[m]
    m = M(IK.Z_STRAW) | M(IK.Z_MOPS)
    streak = fbm(Pp * np.array([3, 3, 0.3], np.float32), 120.0, 1, seed=3241)
    c = col * (0.8 + 0.35 * streak)[:, None]
    c = mixc(c, lin(90, 84, 70), ss(0.04, 0.0, z) * 0.6)
    col[m] = c[m]
    m = M(IK.Z_MOPS)
    col[m] = mixc(col, lin(120, 114, 100), 0.35 + 0.3 * n_mid)[m]
    m = M(IK.Z_CABLE_O)
    wind = gline(dist_periodic(y, 0.0125), 0.002, aa)
    c = mixc(col * (0.92 + 0.12 * spec)[:, None], GRIME, cav * 0.5 + ss(0.6, 0.85, n_mid) * 0.25)
    col[m] = c[m]
    gr = np.where(m, wind * 0.6, gr)
    m = M(IK.Z_RUG)                                                                           # the kitchen rug: border, diamonds
    ax_, ay_ = np.abs(x) / 0.86, np.abs(y) / 0.45
    border = np.maximum(ax_, ay_) > 0.86
    line_ = np.abs(np.maximum(ax_, ay_) - 0.80) < 0.02
    dia = (dist_periodic(x, 0.22) + dist_periodic(y, 0.22)) < 0.085
    medal = (np.abs(x) / 0.30 + np.abs(y) / 0.17) < 1.0
    c = np.where(border[:, None], lin(104, 38, 32) * np.ones((n, 1), np.float32), lin(176, 132, 96) * np.ones((n, 1), np.float32))
    c = np.where((dia & ~border)[:, None], lin(52, 58, 92) * np.ones((n, 1), np.float32), c)
    c = np.where((medal & ~border)[:, None], np.where(dia[:, None], lin(176, 132, 96), lin(104, 38, 32)) * np.ones((n, 1), np.float32), c)
    c = np.where(line_[:, None], lin(214, 196, 150) * np.ones((n, 1), np.float32), c)
    c = c * (0.86 + 0.18 * weave)[:, None]
    c = mixc(c, lin(150, 132, 108), np.exp(-((x / 0.5) ** 2 + (y / 0.25) ** 2)) * 0.35)     # walked pale in the middle
    c = mixc(c, GRIME, ss(0.55, 0.85, n_mid) * 0.3)
    col[m] = c[m]

    # ---- glass: dark, one hard highlight, contents
    for zz in (IK.Z_GLASS_BR, IK.Z_GLASS_GR, IK.Z_GLASS_CL, IK.Z_GLASS_ASH):
        m = M(zz)
        hl = {IK.Z_GLASS_BR: lin(176, 126, 70), IK.Z_GLASS_GR: lin(120, 176, 124), IK.Z_GLASS_CL: lin(226, 232, 230),
              IK.Z_GLASS_ASH: lin(200, 220, 206)}[zz]
        c = mixc(col, hl, spec * 0.75)
        c = mixc(c, col * 1.35, edge * 0.4)
        c = mixc(c, DUST, up * ss(0.6, 0.9, n_mid) * 0.3)
        col[m] = c[m]
    m = M(IK.Z_GLASS_CL) & I('Item_Jar') & (z < 0.105) & (spec < 0.5)                         # gherkins in brine
    blob = ss(0.45, 0.62, fbm(Pp, 60.0, 2, seed=3251))
    col[m] = mixc(lin(120, 132, 76) * np.ones((n, 1), np.float32), lin(66, 86, 40), blob)[m]
    m = M(IK.Z_GLASS_ASH)
    bowl = np.hypot(x - 0.008, y + 0.006) < 0.05
    col[m] = mixc(col, lin(60, 58, 56), (bowl * up * 0.6 + cav * 0.3))[m]

    # ---- food, smokes, soap, bag
    m = M(IK.Z_BREAD) | M(IK.Z_CRUMB)
    c = col
    c = mixc(c, lin(112, 70, 36), M(IK.Z_BREAD) * up * 0.5)
    holes = ss(0.62, 0.70, fbm(Pp, 160.0, 1, seed=3261)) * M(IK.Z_CRUMB)
    c = mixc(c, lin(150, 126, 90), holes * 0.6)
    mould = ss(0.58, 0.72, fbm(Pp, 25.0, 3, seed=3262))
    fuzz = ss(0.66, 0.80, fbm(Pp, 70.0, 2, seed=3263))
    c = mixc(c, lin(104, 136, 102), mould * 0.85)
    c = mixc(c, lin(206, 210, 196), mould * fuzz * 0.8)
    col[m] = c[m]
    m = M(IK.Z_FOOD)
    col[m] = mixc(col, lin(110, 60, 30), ss(0.45, 0.8, n_hi) * 0.6)[m]
    m = M(IK.Z_ENW) & I('Item_PlateDirty') & (z > 0.006) & (np.hypot(x, y) < 0.095) & (Nn[:, 2] > 0.6)
    smear = ss(0.48, 0.70, fbm(Pp, 30.0, 2, seed=3271))
    col[m] = mixc(col, lin(150, 96, 52), smear * 0.75)[m]
    m = M(IK.Z_CIG)
    col[m] = mixc(col, lin(150, 140, 120), ss(0.5, 0.8, n_hi) * 0.4)[m]
    m = M(IK.Z_FILTER)
    col[m] = (col * (0.85 + 0.25 * (fbm(Pp, 400.0, 1, seed=3281) > 0.55)[:, None]))[m]
    m = M(IK.Z_ASH)
    col[m] = mixc(col, lin(40, 38, 36), ss(0.5, 0.8, n_hi) * 0.6)[m]
    m = M(IK.Z_SOAP)
    col[m] = mixc(col, lin(240, 226, 210), up * 0.3)[m]
    m = M(IK.Z_BAG)
    wr = ss(0.55, 0.75, fbm(Pp, 50.0, 2, seed=3291))
    col[m] = mixc(col, lin(96, 96, 104), np.clip(spec * 0.8 + wr * 0.15, 0, 0.85))[m]
    m = M(IK.Z_TISSUE)
    col[m] = mixc(col, lin(196, 192, 184), cav * 0.4 + side * ss(0.6, 0.8, n_hi) * 0.15)[m]
    m = M(IK.Z_COFFEE)
    col[m] = mixc(col, lin(30, 20, 12), ss(0.4, 0.8, n_hi) * 0.5)[m]
    return col, gr
