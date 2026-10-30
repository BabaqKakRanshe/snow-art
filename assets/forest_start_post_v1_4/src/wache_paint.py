"""Painter of the guard house's atlas (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
The start post's finish and wear language (start_paint, gen_paint) on a rendered-brick house: a grey-beige scratch render,
streaked under the drip edge, green bloom on the back (north) wall, grey splash and moss at the foot, hairline cracks from the
window corners, a few patches where the render fell off down to the red brick; the plinth's board-formwork concrete; white
trims, fascia and soffit gone grey; inside: whitewash over a dark green oil-paint dado, soot over the stove, the board floor
with the trodden path from the door, the ply ceiling, spruce furniture, a grey army blanket, the guard's olive coat, the
cast-iron stove, a brown radio, the log book, the calendar 1991. The house is baked at the origin (wache_kit frame)."""
import numpy as np
TAU = 2 * np.pi
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, boards, hash1
from gen_paint import DUST, RUST, RUST_D, _T, _common, run_m
import gen_kit as K
import wache_kit as W

MOSS, MOSS_D, NEEDLE_A, NEEDLE_B, LEAF = lin(70, 86, 40), lin(46, 58, 30), lin(132, 92, 46), lin(96, 70, 40), lin(150, 96, 44)
RENDER, RENDER_FADE, RENDER_STREAK = lin(152, 148, 138), lin(176, 172, 162), lin(88, 90, 82)
BRICK, BRICK_D, MORTAR = lin(136, 70, 52), lin(98, 52, 40), lin(150, 146, 134)
WASH, DADO, DADO_D = lin(200, 196, 184), lin(58, 80, 64), lin(36, 50, 40)
MUD = lin(92, 78, 60)

PATCHES = [   # render fallen off: (wall, along, z, half width, half height)
    ('-y', 1.45, 0.62, 0.30, 0.20), ('-y', -1.40, 2.66, 0.22, 0.13), ('+x', -1.72, 0.70, 0.18, 0.24),
    ('+y', 0.65, 0.82, 0.34, 0.22), ('-x', -0.40, 1.55, 0.25, 0.18)]

DRAFT_COL = {   # sRGB, roughly the painters' base colours (--draft)
    K.Z_SLAB: (132, 130, 124), K.Z_FLOOR: (124, 106, 82), K.Z_TRIMW: (200, 196, 182), K.Z_LINING: (172, 144, 104),
    K.Z_TIMBER: (142, 112, 76), K.Z_STEELBLK: (36, 36, 36), K.Z_GALV: (146, 150, 148), K.Z_RUSTPIPE: (104, 58, 34),
    W.Z_RENDER: (152, 148, 138), W.Z_RENDER_IN: (200, 196, 184), W.Z_REVEAL: (160, 156, 146), W.Z_FELT: (62, 62, 60),
    W.Z_DESK: (170, 140, 96), W.Z_BLANKET: (104, 102, 94), W.Z_PILLOW: (176, 170, 150), W.Z_COAT: (84, 90, 70),
    W.Z_PAPER: (224, 218, 196), W.Z_IRON: (46, 44, 42), W.Z_RADIO: (72, 58, 46), W.Z_BOOK: (52, 64, 74),
    W.Z_CAL: (224, 218, 196), W.Z_FLOORPLATE: (126, 126, 122), W.Z_SOFFIT: (190, 186, 172), W.Z_STEELPAINT: (92, 104, 94),
    W.Z_RTRIM: (186, 182, 170), W.Z_LOGS: (150, 120, 84), W.Z_KETTLE: (70, 92, 110), W.Z_CLOCK: (220, 216, 204), W.Z_AID: (220, 216, 206),
    W.Z_MUG: (220, 216, 204), W.Z_CORR: (146, 150, 148), W.Z_DOORSTEEL: (92, 104, 94), W.Z_RAFTER: (96, 74, 54)}
DRAFT_COL.update({W.Z_EXT: (178, 30, 24), W.Z_METER: (30, 30, 32), W.Z_PORC: (222, 220, 212), W.Z_EBOARD: (168, 170, 162)})
for i_, p_ in enumerate(W.FIREWOOD):
    DRAFT_COL[W.Z_WOOD_END + i_] = ((222, 202, 160), (226, 198, 150), (212, 176, 142), (230, 214, 184))[p_['sp']]
    DRAFT_COL[W.Z_WOOD_SPLIT + i_] = (214, 186, 140)
    DRAFT_COL[W.Z_WOOD_BARK + i_] = ((98, 82, 68), (134, 82, 56), (150, 150, 142), (228, 226, 216))[p_['sp']]


def _litter(Pp, up, seed, amount=1.0):
    x, y = Pp[:, 0], Pp[:, 1]
    m = (ss(0.52, 0.72, fbm(Pp, 5.0, 3, seed=seed)) * 0.7 + ss(0.62, 0.80, fbm(Pp, 30.0, 1, seed=seed + 1)) * 0.6) * up * amount
    pick = hash1(np.floor(x * 53.0) + np.floor(y * 47.0) * 13.0, seed)
    c = np.where((pick > 0.70)[:, None], LEAF, np.where((pick > 0.35)[:, None], NEEDLE_A, NEEDLE_B))
    return np.clip(m, 0, 1), c


def _brick(s, z, aa):
    """running bond NF bricks (0.25 x 0.0625 with the joint): colour per brick and the joints' mask"""
    row = np.floor(z / 0.0625)
    sh = s + 0.125 * np.mod(row, 2)
    bi = np.floor(sh / 0.25) + row * 37.0
    joint = np.maximum(gline(dist_periodic(z, 0.0625), 0.010, aa), gline(dist_periodic(sh, 0.25), 0.010, aa))
    tone = 0.82 + 0.30 * hash1(bi, 41)
    return tone, joint


def paint_wache(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 1201)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    zf = z - W.FL
    streak = ss(0.55, 0.80, fbm(Pp * np.array([1, 1, 0.12], np.float32), 6.0, 3, seed=1211))
    lit, lit_c = _litter(Pp, up, 1212)
    fb = np.abs(Nn[:, 1]) > 0.5                                       # faces across y (front / back) vs across x
    s_wall = np.where(fb, x, y)
    inside = (np.abs(x) < W.IX1 + 0.005) & (np.abs(y) < W.IY1 + 0.005) & (z > W.FL - 0.01) & (z < W.z_ci(y) + 0.01)

    # ---- outside: the scratch render (Kratzputz) of the brick walls and the reveals
    for zz, k_ in ((W.Z_RENDER, 1.0), (W.Z_REVEAL, 0.6)):
        m = M(zz)
        grain = fbm(Pp, 180.0, 1, seed=1213)
        c = T(RENDER, 0.16, 0.10) * (0.90 + 0.16 * grain + 0.08 * (n_mid - 0.5))[:, None]
        weather = np.where(Nn[:, 1] < -0.5, 1.0, np.where(Nn[:, 0] > 0.5, 0.7, 0.45))
        c = mixc(c, RENDER_FADE, weather * ss(0.35, 0.75, n_lo) * 0.40)
        ztop = W.z_rt(np.clip(y, -W.HY, W.HY))
        top = ss(ztop - 0.9, ztop - 0.05, z)                                                       # run-off under the roof's edge
        c = mixc(c, RENDER_STREAK, np.clip(streak * (0.25 + 0.75 * top) * 0.55 * k_, 0, 0.6))
        north = ss(0.0, 0.8, Nn[:, 1])                                                             # the back wall: green bloom
        c = mixc(c, lin(104, 116, 84), north * ss(0.45, 0.75, fbm(Pp, 3.0, 3, seed=1214)) * 0.55 * k_)
        c = mixc(c, lin(96, 94, 86), ss(0.45, 0.05, zf) * 0.55 * k_)                              # splash at the foot
        c = mixc(c, MOSS_D, ss(0.30, 0.0, zf) * ss(0.45, 0.70, fbm(Pp, 12.0, 2, seed=1215)) * 0.65 * k_)
        # under the window sills: two dirty streaks from the sill ends
        for (h, axis) in (((W.WIN_F['u0'], W.WIN_F['u1'], W.WIN_F['z0']), 'y'), ((W.WIN_S['u0'], W.WIN_S['u1'], W.WIN_S['z0']), 'x')):
            u0, u1, z0 = h
            sel = (fb if axis == 'y' else ~fb) & (z < z0)
            d = np.minimum(np.abs(s_wall - u0), np.abs(s_wall - u1))
            c = mixc(c, RENDER_STREAK, sel * np.exp(-(d / 0.05) ** 2) * ss(z0 - 1.0, z0 - 0.05, z) * 0.6 * k_)
        # cracks from the windows' corners, a long one from the roof edge
        crack = np.zeros(n, np.float32)
        for (cx, cz, dirx) in ((W.WIN_F['u0'], W.WIN_F['z0'], -1), (W.WIN_F['u1'], W.WIN_F['z1'], 1), (W.WIN_S['u0'], W.WIN_S['z0'], -1)):
            wig = (fbm(Pp, 9.0, 2, seed=1216) - 0.5) * 0.08
            line = np.abs((s_wall - cx) - dirx * np.abs(z - cz) * 0.6 - wig)
            crack = np.maximum(crack, gline(line, 0.006, aa) * ss(0.55, 0.0, np.abs(z - cz)))
        m_out = m & (zz == W.Z_RENDER)
        # render fallen off in a few places (corners low down, under the roof edge, beside the door): the brick shows
        patch = np.zeros(n, np.float32)
        wob = (fbm(Pp, 4.0, 3, seed=1217) - 0.5) * 0.9
        for (side, s0, z0, rx, rz) in PATCHES:
            sel = {'-y': Nn[:, 1] < -0.5, '+y': Nn[:, 1] > 0.5, '+x': Nn[:, 0] > 0.5, '-x': Nn[:, 0] < -0.5}[side]
            d = np.sqrt(((s_wall - s0) / rx) ** 2 + ((z - z0) / rz) ** 2) + wob
            patch = np.maximum(patch, sel * np.clip(1.25 - d, 0, 1.25))
        tone, joint = _brick(s_wall, z, aa)
        bc = BRICK * tone[:, None]
        bc = mixc(bc, MORTAR, joint * 0.85)
        bc = mixc(bc, BRICK_D, cav * 0.4)
        p_ = (patch > 0.25).astype(np.float32) * m_out
        rim = ((patch > 0.08) & (patch <= 0.25)).astype(np.float32) * m_out
        c = mixc(c, lin(104, 100, 92), rim * 0.8)                                               # the broken edge of the render
        c = np.where((p_ > 0.6)[:, None], bc, c)
        c = mixc(c, RENDER_STREAK, crack * 0.8 * m_out)
        col[m] = c[m]
        gr = np.where(m, np.maximum(np.maximum(crack * 0.6, np.where(p_ > 0.6, joint * 0.5, 0.0)), rim * 0.5), gr)
    # ---- the plinth and the steps: concrete cast against boards, moss and dirt at the foot, needles on the steps
    m = M(K.Z_SLAB)
    c = T(lin(132, 130, 124), 0.16, 0.22)
    bi, seam = boards(z, 0.15, aa, 0.004)
    c = c * (0.92 + 0.10 * hash1(bi, 43))[:, None]
    c = mixc(c, lin(86, 82, 76), ss(0.12, -0.15, z) * 0.6 + cav * 0.4)
    c = mixc(c, MOSS, ss(0.55, 0.78, fbm(Pp, 9.0, 3, seed=1218)) * (0.3 + 0.7 * cav) * ss(0.25, 0.0, z) * 0.7)
    c = mixc(c, lit_c, lit * 0.7)
    c = mixc(c, lin(160, 158, 150), up * ss(W.FL - 0.03, W.FL, z) * 0.25)                    # the ledge's top
    col[m] = c[m]
    gr = np.where(m, seam * (1 - up) * 0.6, gr)
    # ---- white trims and the fascia gone grey, peeling; the soffit boards
    m = M(K.Z_TRIMW)
    c = T(lin(200, 196, 182), 0.10, 0.12)
    c = mixc(c, lin(122, 114, 98), np.clip(edge * 0.9 + ss(0.62, 0.84, fbm(Pp, 18.0, 2, seed=1219)) * 0.8, 0, 0.95))
    c = mixc(c, lin(90, 84, 72), ss(0.35, 0.08, zf) * 0.6 + cav * 0.35)
    c = mixc(c, lin(130, 122, 104), streak * 0.35)
    col[m] = c[m]
    m = M(W.Z_SOFFIT)
    bi, seam = boards(np.where(np.abs(x) > W.HX, y, x), 0.10, aa, 0.004)
    c = T(lin(186, 182, 168), 0.10, 0.12) * (0.92 + 0.10 * hash1(bi, 44))[:, None]
    c = mixc(c, lin(110, 104, 92), ss(0.6, 0.85, fbm(Pp, 10.0, 2, seed=1220)) * 0.35 + cav * 0.3)
    col[m] = c[m]
    gr = np.where(m, seam * 0.7, gr)
    m = M(W.Z_FELT)
    c = T(lin(62, 62, 60), 0.14, 0.2)
    c = mixc(c, lin(120, 116, 106), ss(0.72, 0.86, fbm(Pp, 60.0, 1, seed=1221)) * 0.5)
    c = mixc(c, lit_c, lit * 0.8)
    col[m] = c[m]

    # ---- inside: whitewash over the dark green dado (1.35 above the floor), soot over the stove, grime low and by the door
    m = M(W.Z_RENDER_IN)
    dado = zf < 1.35
    c = np.where(dado[:, None], T(DADO, 0.10, 0.10), T(WASH, 0.10, 0.08))
    c = mixc(c, DADO_D, gline(np.abs(zf - 1.35), 0.012, aa) * 0.9)                              # the dark line on the dado's top
    c = mixc(c, lin(140, 136, 124), (~dado) * ss(0.62, 0.84, fbm(Pp, 4.0, 3, seed=1222)) * 0.35)  # damp shadows in the wash
    knock = np.clip(ss(0.30, 0.0, zf) + np.exp(-((y - (W.DOOR['u0'] + W.DOOR['u1']) / 2) / 0.7) ** 2) * (x > W.IX1 - 0.01) * 0.8
                    + np.exp(-((zf - 0.75) / 0.12) ** 2) * 0.5, 0, 1)
    c = mixc(c, lin(104, 108, 96), dado * np.clip(edge * 0.6 + ss(0.66, 0.84, fbm(Pp, 20.0, 2, seed=1223)) * knock * 0.9, 0, 0.9))  # chipped oil paint
    soot = np.exp(-(((x - W.PIPE.x) / 0.45) ** 2 + ((y - W.PIPE.y) / 0.45) ** 2)) * ss(1.0, 2.6, z)
    c = mixc(c, lin(40, 38, 36), np.clip(soot * 0.9, 0, 0.85))
    door = np.exp(-(((y - (W.DOOR['u0'] + W.DOOR['u1']) / 2) / 0.6) ** 2 + ((z - 1.2) / 0.6) ** 2)) * (x > W.IX1 - 0.01)
    c = mixc(c, lin(70, 66, 58), door * 0.35)
    c = mixc(c, lin(60, 56, 48), ss(0.25, 0.0, zf) * 0.5)
    col[m] = c[m]
    m = M(K.Z_FLOOR)
    bi, seam = boards(y, 0.14, aa, 0.004)
    c = lin(124, 106, 82) * (0.86 + 0.18 * hash1(bi, 49))[:, None] * (0.86 + 0.2 * (n_lo - 0.5) * 2)[:, None]
    dc = np.array(((W.DOOR['u0'] + W.DOOR['u1']) / 2), np.float32)
    path = np.exp(-((y - dc) / 0.35) ** 2) * ss(-0.6, 0.9, x)                                   # door -> the room
    path += 0.8 * np.exp(-((x + 0.15) / 0.40) ** 2) * ss(0.2, -1.3, y)                          # -> the desk
    path += 0.6 * np.exp(-(((x + 0.7) / 0.35) ** 2 + ((y - 1.2) / 0.3) ** 2))                    # -> the stove
    c = mixc(c, lin(78, 66, 52), np.clip(path, 0, 1) * 0.55)
    c = mixc(c, MUD, ss(0.9, 1.6, x) * np.exp(-((y - dc) / 0.4) ** 2) * 0.5)                    # snow-melt mud at the door
    c = mixc(c, lin(70, 64, 58), np.exp(-(((x - W.PIPE.x) / 0.6) ** 2 + ((y - W.PIPE.y) / 0.5) ** 2)) * 0.45)   # ash by the stove
    col[m] = c[m]
    gr = np.where(m, seam * 0.8, gr)
    m = M(K.Z_LINING)
    c = T(lin(172, 144, 104), 0.14, 0.16)
    grain = fbm(Pp * np.array([3.0, 3.0, 0.4], np.float32), 9.0, 2, seed=1224)
    c = c * (0.90 + 0.14 * grain)[:, None]
    c = mixc(c, lin(46, 42, 38), np.clip(np.exp(-(((x - W.PIPE.x) / 0.7) ** 2 + ((y - W.PIPE.y) / 0.7) ** 2)) * 1.1, 0, 0.9))
    c = mixc(c, lin(120, 100, 76), np.exp(-(((x - 0.0) / 0.5) ** 2 + ((y + 0.2) / 0.5) ** 2)) * 0.35)
    col[m] = c[m]
    gr = np.where(m, np.maximum(gline(dist_periodic(x, 1.22, 0.0), 0.005, aa), gline(dist_periodic(y, 1.22, 0.3), 0.005, aa)) * 0.7, gr)
    m = M(K.Z_TIMBER)
    vert = np.abs(Nn[:, 2]) < 0.6
    g2 = fbm(Pp * np.where(vert[:, None], np.array([4.0, 4.0, 0.25], np.float32), np.array([0.3, 4.0, 4.0], np.float32)), 10.0, 2,
             seed=1225)
    c = T(lin(142, 112, 76), 0.16, 0.12) * (0.86 + 0.22 * g2)[:, None]
    c = mixc(c, lin(84, 66, 48), cav * 0.55 + ss(0.6, 0.9, n_mid) * 0.25)
    c = mixc(c, DUST, up * 0.25)
    col[m] = c[m]
    m = M(W.Z_DESK)
    c = T(lin(170, 140, 96), 0.10, 0.10)
    c = mixc(c, lin(110, 84, 56), edge * 0.6 + ss(0.65, 0.85, fbm(Pp, 14.0, 2, seed=1226)) * 0.4)
    c = mixc(c, lin(60, 48, 36), np.exp(-(((x - 0.12) / 0.06) ** 2 + ((y + 1.38) / 0.05) ** 2)) * up * 0.6)      # a mug ring
    c = mixc(c, lin(40, 46, 70), np.exp(-(((x + 0.30) / 0.05) ** 2 + ((y + 1.60) / 0.04) ** 2)) * up * 0.6)      # ink
    c = mixc(c, DUST, up * 0.25)
    col[m] = c[m]
    # ---- the bunk's blanket (grey army wool, two dark stripes at the foot), the pillow, the coat
    m = M(W.Z_BLANKET)
    c = T(lin(104, 102, 94), 0.14, 0.16) * (0.9 + 0.1 * (hash1(np.floor(x / 0.006) + np.floor(y / 0.006) * 7, 51) > 0.5))[:, None]
    yb0 = W.BUNK['y0']
    stripe = (np.abs(y - (yb0 + 0.25)) < 0.035) | (np.abs(y - (yb0 + 0.36)) < 0.035)
    c = np.where(stripe[:, None], lin(52, 50, 48), c)
    c = mixc(c, lin(70, 68, 62), ss(0.55, 0.80, fbm(Pp, 7.0, 3, seed=1227)) * 0.45)            # folds
    col[m] = c[m]
    m = M(W.Z_PILLOW)
    c = T(lin(176, 170, 150), 0.10, 0.12)
    c = mixc(c, lin(120, 112, 90), ss(0.6, 0.85, fbm(Pp, 9.0, 2, seed=1228)) * 0.5)
    col[m] = c[m]
    m = M(W.Z_COAT)
    c = T(lin(84, 90, 70), 0.14, 0.16)
    c = mixc(c, lin(50, 54, 42), cav * 0.6 + ss(0.55, 0.8, fbm(Pp * np.array([1, 1, 0.3], np.float32), 12.0, 2, seed=1229)) * 0.4)
    c = mixc(c, lin(120, 122, 104), edge * 0.4)
    col[m] = c[m]
    # ---- the stove, its plate; the radio, the log book, the calendar
    m = M(W.Z_IRON)
    c = T(lin(46, 44, 42), 0.10, 0.16)
    c = mixc(c, RUST, np.clip(edge * 0.6 + ss(0.72, 0.88, fbm(Pp, 26.0, 2, seed=1230)) * 0.45, 0, 0.7))
    c = mixc(c, lin(150, 146, 138), up * ss(0.5, 0.8, fbm(Pp, 30.0, 1, seed=1231)) * 0.35)     # ash dust on the top
    c = mixc(c, lin(110, 104, 96), edge * up * 0.5)
    col[m] = c[m]
    gr = np.where(m, gline(np.abs(z - (W.FL + 0.30)), 0.008, aa) * (1 - up) * 0.6, gr)
    m = M(W.Z_FLOORPLATE)
    c = T(lin(126, 126, 122), 0.10, 0.12)
    c = mixc(c, lin(70, 68, 64), ss(0.55, 0.80, fbm(Pp, 6.0, 2, seed=1232)) * 0.5)
    c = mixc(c, lin(160, 156, 148), ss(0.75, 0.90, fbm(Pp * np.array([6, 1, 1], np.float32), 30.0, 1, seed=1233)) * 0.4)   # scratches
    col[m] = c[m]
    m = M(W.Z_RADIO)
    c = T(lin(72, 58, 46), 0.08, 0.10)
    front = Nn[:, 1] > 0.5
    rx = x + 0.805
    grille = front & (rx > -0.13) & (rx < 0.02) & (z > W.DESK['z'] + 0.025) & (z < W.DESK['z'] + 0.145)
    dots = (np.mod(np.floor(rx / 0.008) + np.floor(z / 0.008), 2) > 0)
    c = np.where((grille & dots)[:, None], lin(30, 28, 26), np.where(grille[:, None], lin(96, 92, 84), c))
    dial = front & (rx > 0.04) & (rx < 0.135) & (z > W.DESK['z'] + 0.095) & (z < W.DESK['z'] + 0.14)
    c = np.where(dial[:, None], lin(206, 190, 130), c)
    c = np.where((dial & (np.abs(rx - 0.085) < 0.004))[:, None], lin(180, 40, 30), c)          # the needle
    c = mixc(c, DUST, up * 0.4)
    col[m] = c[m]
    m = M(W.Z_BOOK)
    c = T(lin(52, 64, 74), 0.08, 0.10)
    label = (Nn[:, 2] > 0.5) & (np.abs(x - 0.63) < 0.07) & (np.abs(y + 1.415) < 0.04)
    c = np.where(label[:, None], lin(214, 206, 180), c)
    c = np.where((label & (np.mod(np.floor((y + 1.455) / 0.012), 2) > 0) & (np.abs(x - 0.63) < 0.05))[:, None], lin(90, 86, 80), c)
    pages = Nn[:, 2] < 0.5
    c = np.where((pages & (z < W.DESK['z'] + 0.028) & (z > W.DESK['z'] + 0.004) & (x < 0.775))[:, None], lin(218, 212, 192), c)
    col[m] = c[m]
    m = M(W.Z_CAL)
    cu = (x - 0.45) / 0.30                                                                      # 0..1 across, 0..1 up
    cv = (z - 1.42) / 0.44
    c = np.tile(lin(224, 218, 196), (n, 1))
    c = np.where((cv > 0.84)[:, None], lin(176, 36, 30), c)                                    # the red head
    pic = (cv > 0.48) & (cv < 0.82) & (cu > 0.08) & (cu < 0.92)
    sky = pic & (cv > 0.68)
    c = np.where(pic[:, None], lin(70, 96, 70), c)                                             # a winter forest picture
    c = np.where(sky[:, None], lin(150, 170, 186), c)
    c = np.where((pic & ~sky & (hash1(np.floor(cu * 12), 52) > 0.55) & (cv < 0.68))[:, None], lin(220, 224, 228), c)
    grid = (cv < 0.44) & (cv > 0.05) & ((np.mod(cu * 7, 1.0) < 0.12) | (np.mod(cv * 14, 1.0) < 0.14))
    c = np.where(grid[:, None], lin(150, 146, 134), c)
    c = mixc(c, lin(150, 136, 100), ss(0.6, 0.85, fbm(Pp, 12.0, 2, seed=1234)) * 0.4)       # yellowed
    col[m] = c[m]
    # ---- the window bands (smoother lime render, cleaner), the rafters (dark stained), the roof boards' underside
    m = M(W.Z_RTRIM)
    c = T(lin(188, 184, 172), 0.10, 0.08)
    c = mixc(c, lin(120, 118, 108), streak * 0.45 + cav * 0.3)
    c = mixc(c, lin(104, 100, 92), ss(0.72, 0.88, fbm(Pp, 16.0, 2, seed=1240)) * 0.4)
    col[m] = c[m]
    m = M(W.Z_RAFTER)
    vert = np.abs(Nn[:, 2]) < 0.6
    g3 = fbm(Pp * np.array([0.3, 4.0, 4.0], np.float32), 10.0, 2, seed=1241)
    c = T(lin(96, 74, 54), 0.14, 0.12) * (0.86 + 0.22 * g3)[:, None]
    endg = np.abs(Nn[:, 1]) > 0.7                                                             # the cut ends: end grain, weathered grey
    c = np.where(endg[:, None], T(lin(120, 108, 92), 0.14, 0.14), c)
    c = mixc(c, lin(60, 46, 36), cav * 0.4)
    c = mixc(c, lin(140, 138, 130), (np.abs(y) > W.HY) * ss(0.55, 0.85, fbm(Pp, 6.0, 2, seed=1242)) * 0.35)   # weathered tails
    col[m] = c[m]
    # ---- the station's grey-green paint on steel (the door and its frame, brackets, rails, the telephone box)
    for zz in (W.Z_STEELPAINT, W.Z_DOORSTEEL):
        m = M(zz)
        c = T(lin(92, 104, 94), 0.12, 0.14)
        c = mixc(c, lin(132, 140, 126), up * 0.25 + ss(0.6, 0.85, n_lo) * 0.2)                    # chalky where the weather hits
        prim = np.clip(edge * 0.9 + ss(0.70, 0.86, fbm(Pp, 26.0, 2, seed=1243)) * 0.5, 0, 1)
        c = mixc(c, lin(122, 64, 44), prim * 0.6)                                                  # chipped to the red primer
        c = mixc(c, RUST, np.clip(prim - 0.4, 0, 1) * 0.9)
        low = ss(W.FL + 0.35, W.FL, z) if zz == W.Z_DOORSTEEL else ss(0.4, 0.0, z)
        c = mixc(c, RUST_D, low * ss(0.4, 0.7, fbm(Pp, 12.0, 2, seed=1244)) * 0.8)
        c = mixc(c, lin(60, 64, 56), streak * 0.3)
        if zz == W.Z_DOORSTEEL:                                                                    # worn bare round the lever
            hand = np.exp(-(((y - (W.DOOR['u0'] + 0.08)) / 0.09) ** 2 + ((z - (W.FL + 1.05)) / 0.12) ** 2))
            c = mixc(c, lin(70, 70, 66), hand * 0.55)
            c = mixc(c, MUD, ss(W.FL + 0.25, W.FL, z) * 0.5)
        col[m] = c[m]
    # ---- the canopy's corrugated sheet: ribs along the slope, rust at the laps and the edge
    m = M(W.Z_CORR)
    ph = np.cos(2 * np.pi * y / 0.076)
    c = T(lin(146, 150, 148), 0.16, 0.18) * (0.82 + 0.18 * ph)[:, None]
    c = mixc(c, RUST, ss(0.55, 0.80, fbm(Pp * np.array([0.15, 1, 1], np.float32), 7.0, 3, seed=1245)) * 0.75)
    col[m] = c[m]
    gr = np.where(m, gline(dist_periodic(y, 0.76, 0.38), 0.010, aa) * 0.8, gr)
    # ---- the firewood, piece by piece (zones W.Z_WOOD_* + its index): the end grain round the piece's own pith (sapwood,
    # pine's red heart, growth rings, radial checks, the pith, the bark's rim, greyed by the weather), split faces with the
    # fibre along the piece, the bark by species (spruce scaly grey-brown, pine plated red-brown, beech smooth grey, birch
    # white with black lenticels)
    fw = W.FIREWOOD
    NW = len(fw)
    if NW:
        Oa = np.array([tuple(p_['o']) for p_ in fw], np.float32)
        Aa = np.array([tuple(p_['A']) for p_ in fw], np.float32)
        Ua = np.array([tuple(p_['U']) for p_ in fw], np.float32)
        Va = np.array([tuple(p_['V']) for p_ in fw], np.float32)
        Ra = np.array([p_['R'] for p_ in fw], np.float32)
        SPa = np.array([p_['sp'] for p_ in fw], np.int32)
        FRa = np.array([p_['fresh'] for p_ in fw], np.float32)
        JIa = hash1(np.arange(NW, dtype=np.float32) * 7.31 + 3.0, 71)
        tone = lambda tab, sp: np.array(tab, np.float32)[sp]
        for base, what in ((W.Z_WOOD_END, 'end'), (W.Z_WOOD_SPLIT, 'split'), (W.Z_WOOD_BARK, 'bark')):
            m = (Z >= base) & (Z < base + NW)
            if not m.any():
                continue
            i = Z[m] - base
            q = Pp[m] - Oa[i]
            u, v, sa = (q * Ua[i]).sum(1), (q * Va[i]).sum(1), (q * Aa[i]).sum(1)
            r = np.hypot(u, v)
            th = np.arctan2(v, u)
            R_, sp, fr, jt = Ra[i], SPa[i], FRa[i], JIa[i]
            t = r / R_
            nz = fbm(np.stack([r * 9.0 + i * 1.37, sa * 9.0, jt * 5.0], 1).astype(np.float32), 1.0, 2, seed=1250)
            if what == 'end':
                sap = tone([lin(222, 202, 160), lin(226, 198, 150), lin(212, 176, 142), lin(230, 214, 184)], sp)
                heart = tone([lin(214, 192, 150), lin(192, 120, 74), lin(198, 158, 126), lin(222, 204, 172)], sp)
                ht = np.array([0.30, 0.62, 0.40, 0.20], np.float32)[sp] * (0.85 + 0.3 * jt)
                c = mixc(sap, heart, ss(ht + 0.04, ht - 0.04, t))
                ring = np.cos(r * TAU / (0.030 + 0.016 * jt) + jt * 9.0)
                c = c * (0.94 + 0.06 * ring)[:, None] * (0.90 + 0.18 * jt)[:, None]
                c = mixc(c, lin(204, 154, 98), hash1(i * 3.0 + 1.0, 75) * 0.35)                          # fresher, warmer
                bt = np.array([0.018, 0.022, 0.012, 0.014], np.float32)[sp] / R_                           # the bark, read at 1 px
                c = mixc(c, c * 0.72, ss(1.0 - bt - 0.10, 1.0 - bt - 0.02, t) * 0.5)                     # the cambium's line
                ncr = 2 + np.floor(jt * 3.0)
                crk = np.zeros(len(i), np.float32)
                for kk in range(4):
                    a_k = jt * 40.0 + kk * 2.39996
                    dth = np.abs(np.mod(th - a_k + np.pi, TAU) - np.pi)
                    crk = np.maximum(crk, (kk < ncr) * gline(dth * r, 0.004, aa) * ss(0.03, 0.10, t)
                                     * ss(0.55 + 0.35 * hash1(i * 4.0 + kk, 72), 0.45, t))
                c = mixc(c, lin(72, 56, 42), crk * 0.85)
                c = mixc(c, lin(96, 74, 52), ss(0.012, 0.004, r) * 0.8)                                  # the pith
                c = mixc(c, lin(150, 144, 132), (1.0 - fr) * (0.50 + 0.12 * nz))                           # greyed by the weather
                bark_c = tone([lin(62, 50, 42), lin(84, 54, 40), lin(104, 104, 98), lin(196, 194, 184)], sp)
                c = mixc(c, bark_c, ss(1.0 - bt - 0.03, 1.0 - bt + 0.005, t))
            elif what == 'split':
                fib = fbm(np.stack([r * 70.0 + i * 3.1, sa * 3.0, th * 0.5 + i * 0.7], 1).astype(np.float32), 1.0, 2, seed=1251)
                c = tone([lin(218, 194, 150), lin(212, 178, 130), lin(206, 170, 136), lin(226, 210, 178)], sp)
                c = c * (0.80 + 0.30 * fib)[:, None] * (0.92 + 0.12 * jt)[:, None]
                c = mixc(c, lin(150, 142, 128), (1.0 - fr) * (0.35 + 0.30 * nz))
            else:
                al = th * R_
                n1 = fbm(np.stack([al * 30.0, sa * 18.0, i * 0.37 + 0.0 * al], 1).astype(np.float32), 1.0, 2, seed=1252)
                n2 = fbm(np.stack([al * 9.0, sa * 9.0, i * 0.53 + 0.0 * al], 1).astype(np.float32), 1.0, 2, seed=1253)
                ca = tone([lin(98, 82, 68), lin(134, 82, 56), lin(150, 150, 142), lin(228, 226, 216)], sp)
                cb = tone([lin(62, 52, 44), lin(76, 64, 56), lin(112, 114, 104), lin(36, 36, 36)], sp)
                lim = np.array([0.55, 0.58, 0.70, 2.0], np.float32)[sp]
                c = mixc(ca * (0.88 + 0.20 * n2)[:, None], cb, ss(lim - 0.08, lim + 0.06, n1))
                row = np.floor(sa / 0.032 + jt * 7.0)
                dash = (sp == 3) & (hash1(row * 13.0 + np.floor(al / 0.045 + hash1(row, 73) * 3.0) + i * 101.0, 74) > 0.62) \
                    & (np.abs(np.mod(sa / 0.032 + jt * 7.0, 1.0) - 0.5) < 0.16)
                c = mixc(c, cb, dash * 0.9 + (sp == 3) * ss(0.70, 0.84, n2) * 0.7)
                c = mixc(c, lin(132, 138, 112), (sp != 3) * ss(0.74, 0.86, n2) * 0.45)                    # lichen
            col[m] = c
    # ---- the fire extinguisher: flame red, the white label to the room (text lines, the red pictogram), the foot ring darker
    m = M(W.Z_EXT)
    if m.any():
        e = W.EXT
        c = T(lin(178, 30, 24), 0.05, 0.06)
        dy = np.abs(y - e['y'])
        lab = (Nn[:, 0] < -0.55) & (z > e['z0'] + 0.12) & (z < e['z0'] + 0.33) & (dy < 0.046)
        c = np.where(lab[:, None], lin(226, 222, 210), c)
        rows = lab & (z < e['z0'] + 0.25) & (np.mod((z - e['z0'] - 0.135) / 0.024, 1.0) < 0.38) & (dy < 0.034)
        c = np.where(rows[:, None], lin(40, 38, 36), c)
        pict = lab & (z > e['z0'] + 0.265) & (z < e['z0'] + 0.315) & (dy < 0.022)
        c = np.where(pict[:, None], lin(178, 30, 24), c)
        c = mixc(c, lin(70, 22, 18), ss(e['z0'] + 0.03, e['z0'], z) * 0.6)
        c = mixc(c, lin(110, 26, 22), edge * 0.5)
        col[m] = c[m]
    # ---- the meter board: grey paint, four screws; the meter's face: black, the window (the counter, the disc with its red
    # mark), the rating plate; the porcelain strip and the fuse caps with their coloured eyes (10 A red, 16 A grey, 20 A blue)
    m = M(W.Z_EBOARD)
    if m.any():
        eb = W.EBOARD
        c = T(lin(168, 170, 162), 0.08, 0.10)
        scr = (np.minimum(np.abs(x - eb['x0'] - 0.03), np.abs(x - eb['x1'] + 0.03)) < 0.007) \
            & (np.minimum(np.abs(z - eb['z0'] - 0.03), np.abs(z - eb['z1'] + 0.03)) < 0.007) & (Nn[:, 1] > 0.5)
        c = np.where(scr[:, None], lin(60, 58, 54), c)
        c = mixc(c, lin(112, 112, 106), edge * 0.6 + cav * 0.3)
        col[m] = c[m]
    m = M(W.Z_METER)
    if m.any():
        mt = W.METER
        c = np.tile(lin(30, 30, 32), (n, 1))
        win = (x > mt['x0'] + 0.018) & (x < mt['x1'] - 0.018) & (z > mt['z0'] + 0.10) & (z < mt['z1'] - 0.022)
        c = np.where(win[:, None], lin(206, 202, 188), c)
        dig = win & (z > mt['z1'] - 0.058) & (z < mt['z1'] - 0.038) & (x > mt['x0'] + 0.028) & (x < mt['x1'] - 0.028) \
            & (np.mod((x - mt['x0'] - 0.028) / 0.017, 1.0) < 0.7)
        c = np.where(dig[:, None], lin(24, 24, 26), c)
        disc = win & (np.abs(z - (mt['z0'] + 0.122)) < 0.0045)
        c = np.where(disc[:, None], lin(150, 150, 146), c)
        c = np.where((disc & (np.abs(x - (mt['x0'] + mt['x1']) / 2) < 0.007))[:, None], lin(190, 30, 24), c)
        plate = (x > mt['x0'] + 0.03) & (x < mt['x1'] - 0.03) & (z > mt['z0'] + 0.03) & (z < mt['z0'] + 0.07)
        c = np.where(plate[:, None], lin(200, 196, 182), c)
        col[m] = c[m]
    m = M(W.Z_PORC)
    if m.any():
        c = T(lin(222, 220, 212), 0.05, 0.06)
        c = mixc(c, lin(150, 148, 140), cav * 0.5 + edge * 0.3)
        for fx, eye in zip(W.FUSES_X, (lin(190, 34, 28), lin(130, 130, 128), lin(40, 80, 170))):
            on = (Nn[:, 1] > 0.6) & (np.hypot(x - fx, z - W.FUSE_Z) < 0.0075) & (y > W.IY0 + 0.08)
            c = np.where(on[:, None], eye, c)
        col[m] = c[m]
    # ---- the kettle (blue-grey enamel, chipped black), the mug, the clock, the first-aid box
    m = M(W.Z_KETTLE)
    c = T(lin(70, 92, 110), 0.08, 0.10)
    c = mixc(c, lin(24, 24, 26), np.clip(edge * 0.8 + ss(0.75, 0.88, fbm(Pp, 40.0, 2, seed=1247)) * 0.6, 0, 0.9))
    c = mixc(c, lin(40, 36, 32), ss(W.FL + 0.80, W.FL + 0.77, z) * 0.6)                          # soot at the bottom
    col[m] = c[m]
    m = M(W.Z_MUG)
    c = T(lin(220, 216, 204), 0.06, 0.08)
    c = mixc(c, lin(30, 50, 110), ss(W.DESK['z'] + 0.085, W.DESK['z'] + 0.092, z) * 0.9)          # the blue rim
    c = mixc(c, lin(24, 24, 26), edge * 0.6)
    col[m] = c[m]
    m = M(W.Z_CLOCK)
    cr = np.hypot(x + 0.20, z - 2.12)
    face_ = Nn[:, 1] < -0.5
    c = np.where((face_ & (cr < 0.112))[:, None], lin(224, 220, 206), lin(36, 36, 36))
    ang = np.degrees(np.arctan2(z - 2.12, x + 0.20))
    tick = face_ & (cr > 0.085) & (cr < 0.105) & (np.mod(ang + 3.0, 30.0) < 6.0)
    c = np.where(tick[:, None], lin(30, 30, 30), c)
    hands = face_ & (((np.abs(x + 0.20) < 0.006) & (z > 2.12) & (z < 2.20)) | ((np.abs(z - 2.12) < 0.006) & (x > -0.20) & (x < -0.14)))
    c = np.where(hands[:, None], lin(30, 30, 30), c)
    col[m] = c[m]
    m = M(W.Z_AID)
    c = T(lin(220, 216, 206), 0.06, 0.08)
    front = Nn[:, 0] > 0.5
    rc = front & (((np.abs(y + 1.37) < 0.022) & (np.abs(z - 1.575) < 0.07)) | ((np.abs(y + 1.37) < 0.07) & (np.abs(z - 1.575) < 0.022)))
    c = np.where(rc[:, None], lin(190, 34, 26), c)
    c = mixc(c, DUST, up * 0.4)
    col[m] = c[m]
    # ---- metals
    m = M(K.Z_STEELBLK)
    c = T(lin(36, 36, 36), 0.12, 0.2)
    c = mixc(c, RUST, np.clip(edge * 0.8 + ss(0.66, 0.84, fbm(Pp, 30.0, 2, seed=1235)) * 0.6, 0, 0.9) * (1 - inside * 0.6))
    col[m] = c[m]
    m = M(K.Z_GALV)
    spang = fbm(Pp, 90.0, 1, seed=1236)
    c = T(lin(146, 150, 148), 0.10, 0.08) * (0.88 + 0.22 * spang)[:, None]
    c = mixc(c, lin(196, 198, 192), ss(0.78, 0.90, fbm(Pp, 25.0, 2, seed=1237)) * 0.4)
    c = mixc(c, RUST, run_m(Pp) * 0.4 * (1 - inside))
    col[m] = c[m]
    m = M(K.Z_RUSTPIPE)
    c = T(lin(104, 58, 34), 0.2, 0.25)
    c = mixc(c, lin(30, 26, 24), ss(W.PIPE_TOP - 0.8, W.PIPE_TOP + 0.1, z) * 0.85 + ss(0.6, 0.85, n_mid) * 0.3)
    col[m] = c[m]
    return col, gr
