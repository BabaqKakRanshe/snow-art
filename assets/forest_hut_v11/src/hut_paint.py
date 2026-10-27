"""Painters for the forester's hut atlases (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
The generator shed's finishes and its wear language (gen_paint.paint_shed: the same colours, noise seeds and rules for
the birch-ply lining, the raw spruce, the white trims, the corrugated roof and its underside, the raw boards, the
metals) at the hut's own positions; the hut's own: board-and-batten in a dark stain worn to grey wood where the weather
hits, moss at the foot, stone piers with lichen, a board floor with a trodden path from the door, mud and ash, a cast-
iron stove, old pine furniture, a striped mattress, a grey army blanket, the woodpile (bark, the end grain of the logs),
weathered grey wood, the rain barrel, the chopping block; the hunting stand (HutStand: weathered boards, peeled poles,
tar paper; its positions arrive in its own frame, 2.6 m down); the small things (HutProps).
Hut frame: x to the right seen from the door side, y into the hut, z up; floor 0.33."""
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, boards, hash1
import gen_kit as K
import hut_kit as HK
from gen_paint import OIL, GRIME, DUST, RUST, RUST_D, _T, _common, run_m

DZ = HK.FLOOR - K.FLOOR                          # the shed's heights + DZ = the hut's (floor 0.10 -> 0.33)
STAIN, STAIN_WORN = lin(54, 41, 31), lin(104, 94, 80)
MOSS, LICHEN = lin(64, 80, 42), lin(150, 156, 122)

DRAFT_COL = {   # sRGB, roughly the painters' base colours (hut_build --draft)
    K.Z_CLAD: (54, 41, 31), K.Z_TRIMW: (212, 208, 194), K.Z_LINING: (178, 150, 108), K.Z_TIMBER: (150, 118, 78),
    K.Z_ROOF: (150, 154, 150), K.Z_ROOFUNDER: (118, 120, 116), K.Z_DOOR: (58, 44, 33), K.Z_DOORIN: (146, 118, 82),
    K.Z_STEELBLK: (36, 36, 36), K.Z_GALV: (150, 154, 152), K.Z_RUSTPIPE: (104, 58, 34),
    HK.Z_STONE: (118, 116, 108), HK.Z_FLOORB: (140, 110, 74), HK.Z_STOVE: (40, 38, 36), HK.Z_FURN: (132, 98, 62),
    HK.Z_MATTRESS: (150, 154, 160), HK.Z_BLANKET: (108, 104, 96), HK.Z_LOGEND: (178, 150, 110), HK.Z_BARK: (96, 80, 62),
    HK.Z_WEATHERED: (124, 118, 106), HK.Z_STAVES: (86, 66, 48), HK.Z_WATER: (24, 30, 32), HK.Z_SIGN: (58, 44, 32),
    HK.Z_PILLOW: (206, 200, 184), HK.Z_LOG: (116, 102, 84),
    HK.Z_HS_BOARD: (112, 100, 84), HK.Z_HS_LOG: (120, 108, 90), HK.Z_HS_WOOD: (128, 112, 90), HK.Z_HS_ROOF: (40, 40, 42),
    HK.Z_HS_STONE: (118, 116, 108), HK.Z_HS_END: (150, 136, 112),
    HK.Z_ENAMELW: (226, 224, 214), HK.Z_TIN: (170, 50, 40), HK.Z_GLASSJ: (120, 140, 90), HK.Z_CARDBOARD: (150, 118, 76),
    HK.Z_RUBBER: (40, 52, 38), HK.Z_JACKET: (200, 96, 30), HK.Z_ROPE: (170, 140, 96), HK.Z_ANTLER: (130, 108, 82),
    HK.Z_AXEHEAD: (70, 70, 72), HK.Z_HANDLE: (196, 160, 110), HK.Z_LANTERN: (170, 32, 26), HK.Z_BRASS: (190, 150, 70),
    HK.Z_CANDLE: (232, 226, 204), HK.Z_BOTTLE: (80, 50, 20), HK.Z_SHIELD: (70, 46, 28), HK.Z_WIREP: (40, 40, 40)}


# ---------------------------------------------------------------- shared rules (the shed's where it has one)
def steel_black(Pp, T, edge, seed=121):
    c = T(lin(36, 36, 36), 0.12, 0.2)
    return mixc(c, RUST, np.clip(edge * 0.7 + ss(0.72, 0.86, fbm(Pp, 30.0, 2, seed=seed)) * 0.5, 0, 0.8))


def galv(Pp, T, seed=122):
    spang = fbm(Pp, 90.0, 1, seed=seed)
    c = T(lin(150, 154, 152), 0.10, 0.08) * (0.88 + 0.22 * spang)[:, None]
    c = mixc(c, lin(196, 198, 192), ss(0.78, 0.90, fbm(Pp, 25.0, 2, seed=seed + 1)) * 0.4)
    return mixc(c, RUST, run_m(Pp) * 0.35)


def timber(Pp, Nn, T, cav, up, n_mid, seed=117):
    vert = np.abs(Nn[:, 2]) < 0.6
    g2 = fbm(Pp * np.where(vert[:, None], np.array([4.0, 4.0, 0.25], np.float32), np.array([0.3, 4.0, 4.0], np.float32)), 10.0, 2,
             seed=seed)
    c = T(lin(150, 118, 78), 0.16, 0.12) * (0.86 + 0.22 * g2)[:, None]
    c = mixc(c, lin(92, 72, 50), cav * 0.55 + ss(0.6, 0.9, n_mid) * 0.2)
    return mixc(c, DUST, up * 0.25)


def trim_white(Pp, T, edge, cav, z, streak, z0=0.0):
    c = T(lin(212, 208, 194), 0.10, 0.12)
    c = mixc(c, lin(132, 124, 108), np.clip(edge * 0.9 + ss(0.7, 0.88, fbm(Pp, 18.0, 2, seed=115)) * 0.6, 0, 0.9))
    c = mixc(c, lin(96, 88, 76), ss(0.35 + z0, 0.08 + z0, z) * 0.6 + cav * 0.35)
    return mixc(c, lin(150, 140, 120), streak * 0.25)


def stone(Pp, Nn, T, cav, up, zg, seed):
    """field stone: grey granite speckle, pale lichen on the sides, moss on top, earth where it meets the ground"""
    c = T(lin(118, 116, 108), 0.18, 0.22)
    c = mixc(c, lin(70, 68, 64), ss(0.58, 0.78, fbm(Pp, 50.0, 1, seed=seed)) * 0.5)
    c = mixc(c, lin(172, 168, 158), ss(0.74, 0.90, fbm(Pp, 70.0, 1, seed=seed + 1)) * 0.45)
    c = mixc(c, LICHEN, ss(0.62, 0.80, fbm(Pp, 6.0, 3, seed=seed + 2)) * (1 - 0.5 * up) * 0.55)
    c = mixc(c, MOSS, up * ss(0.48, 0.72, fbm(Pp, 4.0, 3, seed=seed + 3)) * 0.75)
    c = mixc(c, lin(52, 46, 38), ss(0.10, -0.02, zg) * 0.8)
    return mixc(c, lin(60, 58, 54), cav * 0.4)


def end_grain(Pp, T, n_hi, seed):
    c = T(lin(176, 150, 112), 0.14, 0.18)
    rings = 0.5 + 0.5 * np.cos(2 * np.pi * fbm(Pp, 2.5, 2, seed=seed) * 14.0)
    c = c * (0.90 + 0.12 * rings)[:, None]
    return mixc(c, lin(110, 96, 78), ss(0.55, 0.85, fbm(Pp, 9.0, 2, seed=seed + 1)) * 0.45)          # greyed with age


def bark(Pp, T, up, seed):
    c = T(lin(96, 80, 62), 0.18, 0.20)
    c = mixc(c, lin(46, 38, 30), ss(0.60, 0.78, fbm(Pp, 30.0, 2, seed=seed)) * 0.6)
    c = mixc(c, LICHEN, ss(0.74, 0.88, fbm(Pp, 8.0, 2, seed=seed + 1)) * 0.45)
    return mixc(c, MOSS, up * ss(0.60, 0.80, fbm(Pp, 5.0, 2, seed=seed + 2)) * 0.5)


def weathered(Pp, Nn, T, cav, along, seed):
    """silver-grey weathered wood, dark cracks along the grain (`along`: the grain axis, 0 x / 1 y / 2 z)"""
    sc = np.ones(3, np.float32) * 6.0
    sc[along] = 0.35
    c = T(lin(124, 118, 106), 0.16, 0.18)
    c = mixc(c, lin(62, 58, 52), ss(0.66, 0.80, fbm(Pp * sc, 6.0, 2, seed=seed)) * 0.7)
    c = mixc(c, LICHEN, ss(0.76, 0.90, fbm(Pp, 9.0, 2, seed=seed + 1)) * 0.4)
    return mixc(c, lin(70, 64, 56), cav * 0.45)


def dark_stain(Pp, Nn, T, aa, n_lo, n_mid, n_hi, z, s_wall, streak, z_foot, seed_b=3, pitch=0.20, batten=True):
    """board-and-batten (or plain boards) in a dark stain: per-board tone, stain worn off to grey-brown wood in patches
    (more low down), dark streaks from above, mud splash and moss at the foot"""
    bi, seam = boards(s_wall, pitch, aa, 0.004)
    tone = 0.86 + 0.24 * hash1(bi, seed_b)
    c = STAIN * tone[:, None] * (0.86 + 0.20 * (n_lo - 0.5) + 0.10 * (n_hi - 0.5))[:, None]
    worn = ss(0.60, 0.82, fbm(Pp * np.array([1, 1, 0.3], np.float32), 14.0, 3, seed=114)) * (0.30 + 0.70 * ss(z_foot + 0.50, z_foot + 0.05, z))
    c = mixc(c, STAIN_WORN, worn * 0.85)
    c = mixc(c, lin(30, 24, 20), streak * 0.30)
    c = mixc(c, lin(66, 56, 44), ss(z_foot + 0.35, z_foot, z) * 0.55)
    c = mixc(c, MOSS, ss(z_foot + 0.30, z_foot, z) * ss(0.52, 0.72, fbm(Pp, 7.0, 2, seed=141)) * 0.6)
    if batten:
        bat = 1 - ss(0.024 - aa, 0.024 + aa, dist_periodic(s_wall, pitch))
        c = c * (1 - 0.10 * bat * ss(0.3, 0.9, n_mid))[:, None] * (1 + 0.14 * bat)[:, None]
        g = np.maximum(gline(dist_periodic(s_wall - 0.025, pitch), 0.006, aa), gline(dist_periodic(s_wall + 0.025, pitch), 0.006, aa)) * 0.8
    else:
        g = seam * 0.8
    return c, g


def corrugated(Pp, T, top, aa, n_mid, x, y, seed=118):
    """the shed's roof sheet turned 90 degrees (the hut's ridge runs along y): corrugation and laps across y, rust
    runs down the slopes (x), heavier toward the eaves"""
    shade = 0.82 + 0.18 * np.cos(2 * np.pi * y / 0.076)
    c = T(lin(150, 154, 150) if top else lin(118, 120, 116), 0.18, 0.20) * shade[:, None]
    run = ss(0.58, 0.82, fbm(Pp * np.array([0.15, 1, 0.15], np.float32), 7.0, 3, seed=seed)) * ss(0.3, 1.5, np.abs(x))
    c = mixc(c, RUST if top else RUST_D, run * (0.75 if top else 0.45))
    c = mixc(c, lin(96, 92, 86), ss(0.65, 0.85, n_mid) * 0.35)
    if not top:
        c = mixc(c, lin(60, 58, 52), ss(0.62, 0.80, fbm(Pp, 16.0, 2, seed=119)) * 0.35)
    return c, gline(dist_periodic(y, 0.76, 0.38), 0.010, aa) * 0.8


# ================================================================ the hut (and the sign)
def paint_hut(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 101)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    gable = np.abs(Nn[:, 1]) > 0.5                                   # front / back walls (normal +-y): boards along x
    s_wall = np.where(gable, x, y)
    streak = ss(0.55, 0.80, fbm(Pp * np.array([1, 1, 0.12], np.float32), 6.0, 3, seed=111))
    fx, fy = HK.FLUE.x, HK.FLUE.y
    # ---- outside: dark-stained board-and-batten
    m = M(K.Z_CLAD)
    c, g = dark_stain(Pp, Nn, T, aa, n_lo, n_mid, n_hi, z, s_wall, streak, HK.ZB)
    col[m] = c[m]
    gr = np.where(m, g, gr)
    m = M(HK.Z_SIGN)                                                 # the sign board's edges and back: the same stain
    c, g = dark_stain(Pp, Nn, T, aa, n_lo, n_mid, n_hi, z, x, streak, 1.30, pitch=0.34, batten=False)
    col[m] = c[m]
    # ---- the door outside: stained boards, worn round the pull
    m = M(K.Z_DOOR)
    c, g = dark_stain(Pp, Nn, T, aa, n_lo, n_mid, n_hi, z, x, streak, HK.FLOOR, seed_b=5, pitch=0.12, batten=False)
    c = mixc(c, lin(40, 32, 26), np.exp(-(((x + 0.05) / 0.10) ** 2 + ((z - 1.11) / 0.14) ** 2)) * 0.5)
    col[m] = c[m]
    gr = np.where(m, g, gr)
    # ---- white trims (the shed's)
    m = M(K.Z_TRIMW)
    col[m] = trim_white(Pp, T, edge, cav, z, streak, z0=HK.ZB - K.FLOOR)[m]
    # ---- inside: the shed's birch-ply lining; soot over the stove, hand marks at the door and the coat hooks
    m = M(K.Z_LINING)
    c = T(lin(178, 150, 108), 0.14, 0.16)
    grain = fbm(Pp * np.array([3.0, 3.0, 0.4], np.float32), 9.0, 2, seed=116)
    c = c * (0.90 + 0.14 * grain)[:, None]
    sheet = np.maximum(gline(dist_periodic(s_wall, 1.22, 0.0), 0.005, aa),
                       gline(dist_periodic(z - HK.FLOOR, 1.22), 0.005, aa) * (z < HK.FLOOR + 2.30))
    nails = (1 - ss(0.004 - aa, 0.006 + aa, dist_periodic(s_wall, 0.60, 0.30))) * (1 - ss(0.004 - aa, 0.006 + aa, dist_periodic(z, 0.15)))
    c = mixc(c, lin(96, 80, 60), ss(0.9 + DZ, 0.25 + DZ, z) * 0.45 * (0.6 + 0.4 * n_mid))
    soot = (np.exp(-(((x - fx) / 0.32) ** 2 + ((z - 2.05) / 0.55) ** 2)) * (y > 0.9)
            + np.exp(-(((y - fy) / 0.32) ** 2 + ((z - 2.05) / 0.55) ** 2)) * (x > 1.0)
            + 0.7 * np.exp(-(((x - fx) / 0.45) ** 2 + ((y - fy) / 0.45) ** 2)) * (z > 2.6))
    c = mixc(c, lin(38, 32, 26), np.clip(soot * 0.6, 0, 0.7))
    hand = (np.exp(-(((x - 0.08) / 0.09) ** 2 + ((z - 1.11) / 0.12) ** 2)) * (y < -0.9)                 # the door's edge
            + 0.6 * np.exp(-(((x - 0.63) / 0.40) ** 2 + ((z - 1.72) / 0.12) ** 2)) * (y < -0.9)        # the coat hooks
            + 0.5 * np.exp(-(((y + 0.33) / 0.10) ** 2 + ((z - 1.55) / 0.15) ** 2)) * (x > 1.0))       # the shutter's edge
    c = mixc(c, lin(90, 74, 56), np.clip(hand, 0, 1) * 0.35)
    c = mixc(c, lin(120, 98, 70), streak * 0.30)
    col[m] = c[m]
    gr = np.where(m, np.maximum(sheet * 0.75, nails * 0.6), gr)
    # ---- raw spruce (the shed's); soot on the rafters round the pipe
    m = M(K.Z_TIMBER)
    c = timber(Pp, Nn, T, cav, up, n_mid)
    c = mixc(c, lin(40, 34, 28), np.clip(0.8 * np.exp(-(((x - fx) / 0.40) ** 2 + ((y - fy) / 0.40) ** 2)) * (z > 2.3), 0, 0.6))
    col[m] = c[m]
    # ---- the roof: corrugated top (moss, needles, soot down from the pipe) and its underside
    m = M(K.Z_ROOF)
    c, g = corrugated(Pp, T, True, aa, n_mid, x, y)
    c = mixc(c, lin(72, 76, 48), ss(0.58, 0.80, fbm(Pp, 3.0, 3, seed=142)) * ss(0.8, 1.6, np.abs(x)) * 0.55)
    c = mixc(c, lin(88, 60, 36), ss(0.80, 0.92, fbm(Pp, 55.0, 1, seed=143)) * 0.55)
    c = mixc(c, lin(36, 30, 26), np.exp(-((y - fy) / 0.22) ** 2) * ss(fx - 0.05, fx + 0.12, x) * np.exp(-(x - fx) / 0.9) * 0.6)
    col[m] = c[m]
    gr = np.where(m, g, gr)
    m = M(K.Z_ROOFUNDER)
    c, g = corrugated(Pp, T, False, aa, n_mid, x, y)
    col[m] = c[m]
    gr = np.where(m, g, gr)
    # ---- raw boards: the door inside, the window shutter (the shed's)
    m = M(K.Z_DOORIN)
    bi, seam = boards(np.where(np.abs(Nn[:, 1]) > 0.5, x, y), 0.12, aa, 0.004)
    c = lin(146, 118, 82) * (0.90 + 0.16 * hash1(bi, 6))[:, None] * (0.86 + 0.2 * (n_lo - 0.5) * 2)[:, None]
    c = mixc(c, lin(92, 74, 54), cav * 0.4 + ss(0.5 + DZ, 0.12 + DZ, z) * 0.4)
    col[m] = c[m]
    gr = np.where(m, seam * 0.7, gr)
    # ---- the board floor: boards along y, a trodden path from the door, mud, ash before the stove
    m = M(HK.Z_FLOORB)
    bi, seam = boards(x, 0.145, aa, 0.003)
    g2 = fbm(Pp * np.array([4.0, 0.25, 1.0], np.float32), 10.0, 2, seed=131)
    c = lin(140, 110, 74) * (0.88 + 0.22 * hash1(bi, 9))[:, None] * (0.86 + 0.20 * g2)[:, None]
    dx_ = HK.DOOR['x0'] / 2 + HK.DOOR['x1'] / 2
    path = (np.exp(-((x - dx_) / 0.32) ** 2) * ss(0.6, -0.6, y)
            + 0.7 * np.exp(-((y + 0.05) / 0.35) ** 2) * ss(-0.9, 0.0, x) * ss(0.60, 0.30, x)
            + 0.6 * np.exp(-((y - 0.30) / 0.14) ** 2) * ss(-0.2, 0.3, x) * ss(1.0, 0.7, x))           # to the stove
    c = mixc(c, lin(100, 86, 66), np.clip(path, 0, 1) * 0.45 * (0.6 + 0.4 * n_mid))
    c = mixc(c, lin(74, 62, 48), np.exp(-(((x - dx_) / 0.45) ** 2 + ((y - HK.IY0) / 0.32) ** 2)) * 0.55)
    c = mixc(c, lin(78, 74, 70), np.exp(-(((x - fx) / 0.26) ** 2 + ((y - HK.STOVE['y0'] + 0.18) / 0.16) ** 2)) * 0.55)
    nails = (1 - ss(0.003 - aa, 0.005 + aa, dist_periodic(y, 0.60, 0.0))) * \
        (1 - ss(0.003 - aa, 0.005 + aa, np.minimum(dist_periodic(x, 0.145, 0.035), dist_periodic(x, 0.145, 0.110))))
    c = mixc(c, lin(56, 46, 36), cav * 0.5)
    col[m] = c[m]
    gr = np.where(m, np.maximum(seam * 0.8, nails * 0.6), gr)
    # ---- stone piers and the step
    m = M(HK.Z_STONE)
    col[m] = stone(Pp, Nn, T, cav, up, z, 151)[m]
    # ---- the stove: cast iron, rust at the edges, the top plate darker and smoother, ash low down
    m = M(HK.Z_STOVE)
    c = T(lin(40, 38, 36), 0.10, 0.15)
    c = mixc(c, RUST, np.clip(edge * 0.5 + ss(0.75, 0.88, fbm(Pp, 25.0, 2, seed=152)) * 0.35, 0, 0.7))
    c = np.where(((Nn[:, 2] > 0.8) & (z > HK.STOVE['z1'] - 0.01))[:, None], lin(28, 28, 30) * (0.9 + 0.2 * n_hi)[:, None], c)
    c = mixc(c, lin(118, 114, 108), ss(0.55, 0.38, z) * 0.35)
    col[m] = c[m]
    # ---- furniture: old pine, the table top worn pale in the middle with a mug ring, dust
    m = M(HK.Z_FURN)
    vert = np.abs(Nn[:, 2]) < 0.6
    g2 = fbm(Pp * np.where(vert[:, None], np.array([4.0, 4.0, 0.25], np.float32), np.array([0.25, 4.0, 4.0], np.float32)), 10.0, 2,
             seed=153)
    c = T(lin(132, 98, 62), 0.14, 0.12) * (0.86 + 0.22 * g2)[:, None]
    t = HK.TABLE
    ontop = (Nn[:, 2] > 0.8) & (np.abs(z - t['top']) < 0.01)
    c = mixc(c, lin(168, 136, 96), ontop * np.exp(-(((x - (t['x0'] + t['x1']) / 2) / 0.22) ** 2 + ((y - (t['y0'] + t['y1']) / 2) / 0.35) ** 2)) * 0.5)
    ring = ss(0.006, 0.0, np.abs(np.hypot(x - HK.MUG.x - 0.10, y - HK.MUG.y - 0.12) - 0.043)) * ontop      # an old ring by the mug
    c = mixc(c, lin(70, 50, 34), ring * 0.6)
    c = mixc(c, lin(80, 60, 40), cav * 0.5)
    col[m] = mixc(c, DUST, up * 0.2)[m]
    # ---- bedding
    m = M(HK.Z_MATTRESS)
    tick = dist_periodic(y, 0.032) < 0.007
    c = np.where(tick[:, None], lin(72, 84, 112), lin(198, 192, 174)) * (0.9 + 0.12 * n_hi)[:, None]
    c = mixc(c, lin(160, 140, 96), ss(0.62, 0.80, fbm(Pp, 4.0, 2, seed=154)) * 0.5)
    col[m] = mixc(c, lin(90, 84, 74), cav * 0.4)[m]
    m = M(HK.Z_BLANKET)
    c = T(lin(108, 104, 96), 0.12, 0.16) * (0.88 + 0.18 * fbm(Pp, 80.0, 1, seed=155))[:, None]
    stripe = (np.abs(x + 0.22) < 0.022) | (np.abs(x - 0.47) < 0.022)
    c = np.where(stripe[:, None], lin(118, 40, 34) * (0.9 + 0.15 * n_hi)[:, None], c)
    col[m] = mixc(c, lin(60, 58, 54), cav * 0.45)[m]
    m = M(HK.Z_PILLOW)
    col[m] = mixc(T(lin(206, 200, 184), 0.08, 0.10), lin(150, 140, 120), ss(0.6, 0.8, fbm(Pp, 6.0, 2, seed=156)) * 0.4 + cav * 0.4)[m]
    # ---- woodpile: bark on the sides and top (the logs lie along x: gaps between them), end grain of a stack of logs
    pile = (x < HK.X0 - 0.02) & (y > -0.99) & (y < 0.59) & (z < 1.12)
    m = M(HK.Z_BARK)
    c = bark(Pp, T, up, 157)
    LP = 0.14                                                        # split logs across the stack
    gap = np.where(np.abs(Nn[:, 2]) > 0.8, dist_periodic(y, LP, LP / 2), dist_periodic(z - 0.10, LP * 0.866, LP * 0.433)) < 0.012
    c = np.where((gap & pile)[:, None], lin(26, 20, 16), c)
    col[m] = c[m]
    m = M(HK.Z_LOGEND)
    c = end_grain(Pp, T, n_hi, 158)
    face_x = pile & (Nn[:, 0] < -0.9)
    v_ = (z - 0.10) / (LP * 0.866)
    row = np.floor(v_)
    u_ = y / LP - 0.5 * np.mod(row, 2)
    cell = np.round(u_) + row * 31
    d = np.hypot((u_ - np.round(u_)) * LP, (v_ - row - 0.5) * LP * 0.866)
    tone = (0.80 + 0.35 * hash1(cell, 17))[:, None]
    split = ss(0.004, 0.0, np.abs((u_ - np.round(u_)) * LP * np.cos(hash1(cell, 18) * 3) + (v_ - row - 0.5) * LP * 0.866 * np.sin(hash1(cell, 18) * 3)))
    endc = c * tone * (1 - 0.35 * split * (hash1(cell, 19) > 0.5))[:, None]
    bark_ring = mixc(lin(70, 56, 42) * np.ones((n, 1), np.float32), lin(26, 20, 16), ss(LP * 0.47, LP * 0.53, d))
    c = np.where(face_x[:, None], mixc(bark_ring, endc, ss(LP * 0.47, LP * 0.42, d)), c)
    cb = np.hypot(x + 1.10, y + 2.55)
    block = (cb < 0.24) & (Nn[:, 2] > 0.8)
    c = np.where(block[:, None], c * (0.88 + 0.14 * np.cos(2 * np.pi * cb / 0.014))[:, None], c)
    cut = block & (ss(0.004, 0.0, np.abs(dist_periodic((x + 1.10) * 0.8 + (y + 2.55) * 0.6, 0.05))) > 0.5) & (fbm(Pp, 9.0, 2, seed=159) > 0.55)
    c = np.where(cut[:, None], lin(70, 56, 40), c)
    col[m] = c[m]
    # ---- weathered grey wood: bench, ladder, the sign's roof board
    m = M(HK.Z_WEATHERED)
    col[m] = weathered(Pp, Nn, T, cav, 0, 160)[m]
    m = M(HK.Z_LOG)
    col[m] = weathered(Pp, Nn, T, cav, 2, 161)[m]
    # ---- the rain barrel: staves, hoops (steel), water
    m = M(HK.Z_STAVES)
    bc = (-1.66, 1.40)
    ang = np.arctan2(y - bc[1], x - bc[0])
    st_i = np.floor(ang / (2 * np.pi / 22))
    seam_s = ss(0.10, 0.0, np.abs(ang / (2 * np.pi / 22) - np.round(ang / (2 * np.pi / 22))))
    c = lin(86, 66, 48) * (0.88 + 0.22 * hash1(st_i, 12))[:, None] * (0.88 + 0.2 * n_hi)[:, None]
    c = mixc(c, lin(56, 66, 40), ss(0.40, 0.10, z) * 0.6)
    c = mixc(c, lin(40, 32, 26), np.where(np.abs(Nn[:, 2]) < 0.5, seam_s, 0.0) * 0.7)
    col[m] = c[m]
    m = M(HK.Z_WATER)
    c = lin(22, 28, 30) * np.ones((n, 1), np.float32)
    c = mixc(c, lin(90, 104, 112), ss(0.82, 0.92, fbm(Pp * np.array([1, 3, 1], np.float32), 12.0, 2, seed=162)) * 0.5)
    c = mixc(c, lin(90, 60, 36), ss(0.86, 0.94, fbm(Pp, 40.0, 1, seed=163)) * 0.6)
    col[m] = c[m]
    # ---- metals (the shed's); the flue: soot toward the top, heat-greyed at the stove
    m = M(K.Z_STEELBLK)
    col[m] = steel_black(Pp, T, edge)[m]
    m = M(K.Z_GALV)
    c = galv(Pp, T)
    c = mixc(c, lin(70, 64, 58), (np.exp(-(((x - fx) / 0.25) ** 2 + ((y - fy) / 0.25) ** 2)) * (z > 2.9)) * 0.6)
    col[m] = c[m]
    m = M(K.Z_RUSTPIPE)
    c = T(lin(104, 58, 34), 0.2, 0.25)
    c = mixc(c, lin(30, 26, 24), ss(3.0, 3.8, z) * 0.85 + ss(0.6, 0.85, n_mid) * 0.3)
    c = mixc(c, lin(70, 68, 72), ss(1.40, 1.05, z) * 0.5)
    col[m] = c[m]
    return col, gr


# ================================================================ the hunting stand (positions in its own frame, 2.6 m down)
def paint_stand(Pp, Nn, Z, ao, aa):
    Pl = Pp.copy()
    Pl[:, 2] -= HK.HS_BAKE_DZ                                        # back to the stand's own heights
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pl, Nn, ao, 401)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    streak = ss(0.55, 0.80, fbm(Pl * np.array([1, 1, 0.12], np.float32), 6.0, 3, seed=411))
    # cabin boards: upright boards, weathered spruce, darker and greener low on the walls, streaks from the roof
    m = M(HK.Z_HS_BOARD)
    s_w = np.where(np.abs(Nn[:, 1]) > 0.5, x, y)
    bi, seam = boards(s_w, 0.13, aa, 0.005)
    c = T(lin(112, 100, 84), 0.16, 0.18) * (0.86 + 0.24 * hash1(bi, 13))[:, None]
    c = mixc(c, lin(62, 58, 52), ss(0.66, 0.80, fbm(Pl * np.array([6, 6, 0.35], np.float32), 6.0, 2, seed=412)) * 0.6)
    c = mixc(c, lin(44, 40, 34), streak * 0.35)
    c = mixc(c, LICHEN, ss(0.74, 0.88, fbm(Pl, 7.0, 2, seed=413)) * 0.4)
    c = mixc(c, lin(70, 76, 50), ss(HK.HS['cz0'] + 0.5, HK.HS['cz0'], z) * 0.45)
    col[m] = c[m]
    gr = np.where(m, seam * 0.8, gr)
    m = M(HK.Z_HS_LOG)
    c = weathered(Pl, Nn, T, cav, 2, 414)
    c = mixc(c, lin(70, 62, 50), ss(0.8, 0.0, z) * 0.5)
    c = mixc(c, MOSS, ss(0.6, 0.0, z) * ss(0.5, 0.7, fbm(Pl, 6.0, 2, seed=415)) * 0.6)
    col[m] = c[m]
    m = M(HK.Z_HS_WOOD)
    col[m] = (weathered(Pl, Nn, T, cav, 0, 416) * 0.75 + lin(150, 136, 110) * 0.25)[m]
    m = M(HK.Z_HS_ROOF)                                              # tar paper: sanded black, laps across the slope, battens
    c = T(lin(36, 36, 38), 0.14, 0.2) * (0.85 + 0.3 * fbm(Pl, 90.0, 1, seed=417))[:, None]
    lap = dist_periodic(y - HK.HS['ry0'], 0.80) < 0.02
    c = np.where(lap[:, None], c * 0.6, c)
    c = mixc(c, lin(84, 86, 80), ss(0.6, 0.85, fbm(Pl, 4.0, 2, seed=418)) * 0.4)
    c = mixc(c, lin(70, 76, 46), ss(0.66, 0.82, fbm(Pl, 3.0, 3, seed=419)) * 0.5)
    col[m] = c[m]
    gr = np.where(m, lap * 0.5, gr)
    m = M(HK.Z_HS_STONE)
    col[m] = stone(Pl, Nn, T, cav, up, z, 420)[m]
    m = M(HK.Z_HS_END)
    col[m] = (end_grain(Pl, T, n_hi, 421) * 0.5 + lin(110, 100, 86) * 0.5)[m]
    return col, gr


# ================================================================ the small things
def paint_props(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 501)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(120, 120, 120), (n, 1))
    gr = np.zeros(n, np.float32)
    chip = ss(0.80, 0.92, fbm(Pp, 40.0, 2, seed=511))
    # enamel: white (mug, candle holder, the lamp's shade), the kettle teal; black chips and rims
    m = M(HK.Z_ENAMELW)
    kettle = np.hypot(x - 1.00, y - 0.80) < 0.25
    c = np.where(kettle[:, None], lin(48, 96, 110), lin(226, 224, 214)) * (0.92 + 0.1 * n_hi)[:, None]
    c = mixc(c, lin(20, 20, 22), np.clip(chip * 0.9 + edge * 0.6, 0, 1))
    c = mixc(c, lin(40, 36, 32), kettle * ss(0.3, 0.05, z - HK.STOVE['z1']) * 0.6)
    col[m] = c[m]
    m = M(HK.Z_TIN)                                                  # tins: a printed paper label round the middle, tin rims
    k = np.floor((y + 2) / 0.12) + np.floor((z + 2) / 0.30) * 7
    lab_c = np.where((hash1(k, 14) > 0.5)[:, None], lin(170, 50, 40), lin(60, 110, 60))
    side = np.abs(Nn[:, 2]) < 0.6
    zrel = z - np.where(z > 1.5, HK.SHELF['tops'][1], HK.SHELF['tops'][0])
    label = side & (zrel > 0.016) & (zrel < 0.09)
    c = np.where(label[:, None], lab_c * (0.9 + 0.15 * n_hi)[:, None], lin(170, 172, 168) * (0.85 + 0.2 * n_hi)[:, None])
    c = np.where((label & (np.abs(zrel - 0.053) < 0.008))[:, None], lin(226, 220, 196), c)
    col[m] = mixc(c, RUST, ss(0.78, 0.9, fbm(Pp, 30.0, 2, seed=512)) * (~label) * 0.5)[m]
    m = M(HK.Z_GLASSJ)
    c = np.where((zrel < 0.10)[:, None], lin(120, 60, 40), lin(150, 170, 150))
    c = np.where((zrel > 0.13)[:, None], lin(150, 150, 140), c)
    col[m] = (c * (0.85 + 0.25 * n_hi)[:, None])[m]
    m = M(HK.Z_CARDBOARD)
    c = T(lin(150, 118, 76), 0.12, 0.14)
    c = np.where((side & (np.abs(z - (HK.SHELF['tops'][1] + 0.075)) < 0.02))[:, None], lin(60, 50, 36), c)
    col[m] = mixc(c, lin(96, 76, 50), cav * 0.4 + edge * 0.3)[m]
    m = M(HK.Z_RUBBER)
    c = T(lin(40, 52, 38), 0.12, 0.14)
    c = mixc(c, lin(86, 70, 50), ss(HK.FLOOR + 0.12, HK.FLOOR + 0.02, z) * 0.7)
    col[m] = mixc(c, lin(90, 96, 80), edge * 0.3)[m]
    m = M(HK.Z_JACKET)                                               # orange forestry jacket, a grey reflective band; the hat green loden
    hat = (x < 0.53) & (z > 1.665)
    c = np.where(hat[:, None], lin(70, 80, 56), lin(184, 88, 32)) * (0.86 + 0.18 * n_hi)[:, None]
    band = (~hat) & (np.abs(z - 1.24) < 0.022)
    c = np.where(band[:, None], lin(170, 172, 168), c)
    c = mixc(c, lin(90, 70, 46), ss(0.55, 0.8, n_mid) * 0.35 + cav * 0.4)
    col[m] = c[m]
    m = M(HK.Z_ROPE)
    tw = 0.5 + 0.5 * np.cos(2 * np.pi * (np.arctan2(y - 0.08, x + 1.05) * 0.10 / 0.012 + z / 0.012))
    col[m] = (T(lin(170, 140, 96), 0.1, 0.12) * (0.82 + 0.22 * tw)[:, None])[m]
    m = M(HK.Z_ANTLER)
    c = T(lin(120, 98, 74), 0.14, 0.16)
    tips = ss(2.78, 2.96, z)
    col[m] = mixc(mixc(c, lin(220, 210, 188), tips * 0.8), lin(70, 56, 42), cav * 0.5)[m]
    m = M(HK.Z_SHIELD)
    col[m] = mixc(T(lin(70, 46, 28), 0.1, 0.14), lin(120, 90, 60), edge * 0.6)[m]
    m = M(HK.Z_AXEHEAD)
    c = T(lin(64, 64, 66), 0.12, 0.2)
    c = mixc(c, RUST, ss(0.6, 0.85, fbm(Pp, 30.0, 2, seed=513)) * 0.5)
    c = mixc(c, lin(196, 198, 200), ss(0.48, 0.452, z) * 0.9)                                  # the bit, sunk in the block
    col[m] = c[m]
    m = M(HK.Z_HANDLE)
    c = T(lin(196, 160, 110), 0.12, 0.12) * (0.88 + 0.18 * fbm(Pp * np.array([1, 1, 0.2], np.float32), 12.0, 2, seed=514))[:, None]
    col[m] = mixc(c, lin(96, 78, 56), ss(0.9, 1.05, z) * 0.6)[m]
    m = M(HK.Z_LANTERN)                                              # Feuerhand red: chipped to bare tin, soot at the cap
    c = T(lin(170, 32, 26), 0.10, 0.14)
    c = mixc(c, lin(150, 150, 146), np.clip(chip * 0.8 + edge * 0.5, 0, 1))
    c = mixc(c, lin(30, 26, 24), ss(HK.LANTERN.z + 0.06, HK.LANTERN.z + 0.13, z) * 0.6)
    col[m] = c[m]
    m = M(HK.Z_BRASS)
    col[m] = mixc(T(lin(190, 150, 70), 0.12, 0.18), lin(90, 74, 44), cav * 0.6 + ss(0.6, 0.85, n_mid) * 0.3)[m]
    m = M(HK.Z_CANDLE)
    c = T(lin(232, 226, 204), 0.06, 0.1)
    col[m] = np.where((z > HK.TABLE['top'] + 0.105)[:, None], lin(30, 26, 22), c)[m]
    m = M(HK.Z_BOTTLE)
    c = lin(80, 50, 20) * (0.8 + 0.4 * n_hi)[:, None]
    lab = side & (np.abs(z - (HK.SHELF['tops'][1] + 0.09)) < 0.04)
    col[m] = np.where(lab[:, None], lin(214, 204, 176), c)[m]
    m = M(HK.Z_WIREP)
    col[m] = steel_black(Pp, T, edge, 515)[m]
    return col, gr


def paint_hut_all(Pp, Nn, Z, ao, aa):
    """the Hut atlas: the hut and the sign (paint_hut) and the stand (paint_stand: its texels arrive in its own frame)"""
    st = np.isin(Z, HK.STAND_ZONES)
    col, gr = paint_hut(Pp, Nn, Z, ao, aa)
    if st.any():
        cs, gs = paint_stand(Pp[st], Nn[st], Z[st], ao[st], aa)
        col[st] = cs
        gr[st] = gs if gs is not None else 0.0
    return col, gr
