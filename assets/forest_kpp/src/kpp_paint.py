"""Painters for the checkpoint atlases (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
The generator shed's finishes and its wear language (gen_paint / hut_paint: the birch-ply lining, the raw spruce, the white
trims, the corrugated roof and its underside, the raw boards, the metals) at the checkpoint's positions; the KPP's own:
board-and-batten in the station's grey-green paint (chalky and worn to grey wood where the weather hits, low down and on
the road side; dark streaks, splash at the foot), the concrete pad (joints, the drip line under the back eave, a path to the
door, leaves and needles) and floor (a trodden path door -> desk -> key cabinet, castor scuffs), yellow-black bollards, the
varnished ply desk, the grey filing cabinet, the cream key cabinet, cork, the convector, the red-white boom, the barrier
posts, the gate's concrete, wheels and barbed wire; the small things (KppProps).
Booth frame: x toward the road, y toward the back, z up; floor 0.15; the barrier and the gate stand 0.38 m lower."""
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, boards, hash1
import gen_kit as K
import kpp_kit as KK
from gen_paint import DUST, RUST, RUST_D, _T, _common, run_m

GREEN, GREEN_FADE, GREEN_WORN, GREEN_STREAK = lin(108, 122, 96), lin(150, 158, 136), lin(126, 118, 104), lin(60, 68, 54)
CONCRETE, EARTH, MOSS = lin(132, 130, 124), lin(66, 56, 44), lin(70, 84, 46)
LEAF_A, LEAF_B = lin(156, 92, 38), lin(98, 72, 42)
GROUND = KK.BARRIER_PLACE[0].z                     # the road / ground level at the barrier and the gate

DRAFT_COL = {   # sRGB, roughly the painters' base colours (kpp_build --draft)
    K.Z_SLAB: (132, 130, 124), K.Z_FLOOR: (118, 116, 110), K.Z_CLAD: (108, 122, 96), K.Z_TRIMW: (212, 208, 194),
    K.Z_LINING: (178, 150, 108), K.Z_TIMBER: (150, 118, 78), K.Z_ROOF: (150, 154, 150), K.Z_ROOFUNDER: (118, 120, 116),
    K.Z_DOOR: (108, 122, 96), K.Z_DOORIN: (146, 118, 82), K.Z_STEELBLK: (36, 36, 36), K.Z_GALV: (150, 154, 152),
    K.Z_ENAMEL_IN: (232, 230, 222),
    KK.Z_BOLLARD: (228, 186, 40), KK.Z_DESK: (176, 146, 100), KK.Z_CABGREY: (128, 132, 128), KK.Z_KEYBOX: (196, 188, 158),
    KK.Z_CORK: (166, 118, 70), KK.Z_BOOM: (196, 36, 26), KK.Z_BARPOST: (226, 224, 216), KK.Z_HEATER: (214, 210, 198),
    KK.Z_RUBBER_K: (34, 34, 34), KK.Z_GATEROLL: (70, 70, 72), KK.Z_CONC: (126, 124, 118), KK.Z_BARBED: (100, 100, 96),
    KK.Z_PHONE: (196, 96, 42), KK.Z_VEST: (230, 110, 30), KK.Z_EXTP: (180, 30, 24), KK.Z_CRT: (196, 186, 160),
    KK.Z_CHAIR: (60, 66, 80), KK.Z_BLACKP: (32, 32, 34), KK.Z_BELLP: (170, 30, 26), KK.Z_PAPERP: (226, 222, 204),
    KK.Z_MUGP: (226, 224, 214), KK.Z_FLASK: (60, 100, 70), KK.Z_BINDER: (60, 80, 140), KK.Z_RADIO: (88, 96, 68),
    KK.Z_CAMP: (200, 200, 196), KK.Z_CHROMEP: (170, 172, 176), KK.Z_FAID: (226, 226, 220),
    KK.Z_BARCAB: (200, 204, 198), KK.Z_GATEP: (84, 100, 78)}


# ---------------------------------------------------------------- the shed's rules (as hut_paint has them)
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


def _leaves(Pp, up, outside, seed):
    """fallen leaves and needles on the horizontal surfaces outside: (mask 0..1, colour)"""
    x, y = Pp[:, 0], Pp[:, 1]
    m = ss(0.74, 0.86, fbm(Pp, 7.0, 2, seed=seed)) * ss(0.55, 0.90, fbm(Pp, 40.0, 1, seed=seed + 1)) * up * outside
    pick = hash1(np.floor(x * 41.0) + np.floor(y * 43.0) * 13.0, seed)
    return m, np.where((pick > 0.55)[:, None], LEAF_A, LEAF_B)


def _inside(x, y, z):
    return ((x > KK.IX0 - 0.01) & (x < KK.IX1 + 0.01) & (y > KK.IY0 - 0.01) & (y < KK.IY1 + 0.01) & (z < 2.95)).astype(np.float32)


# ================================================================ the Kpp atlas (the booth) and KppYard (the barrier, the gate)
def paint_kpp(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 601)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    inside = _inside(x, y, z)
    outside = 1.0 - inside
    zf = z - KK.FLOOR
    fb = np.abs(Nn[:, 1]) > 0.5                                     # faces toward +-y: boards run along x
    s_wall = np.where(fb, x, y)
    streak = ss(0.55, 0.80, fbm(Pp * np.array([1, 1, 0.12], np.float32), 6.0, 3, seed=611))
    lv, lv_c = _leaves(Pp, up, outside, 612)
    # ---- outside: board-and-batten in the station grey-green (the shed's boards, the shed's wear rules)
    m = M(K.Z_CLAD)
    bi, seam = boards(s_wall, 0.20, aa, 0.004)
    bat = 1 - ss(0.024 - aa, 0.024 + aa, dist_periodic(s_wall, 0.20))
    tone = 0.92 + 0.14 * hash1(bi + 7.0 * fb, 3)
    c = GREEN * tone[:, None] * (0.86 + 0.20 * (n_lo - 0.5) + 0.10 * (n_hi - 0.5))[:, None]
    weather = np.where(Nn[:, 1] < -0.5, 1.0, np.where(Nn[:, 0] > 0.5, 0.7, 0.35))     # the front (the road's approach) most
    c = mixc(c, GREEN_FADE, weather * ss(0.35, 0.75, n_lo) * 0.40)                      # chalky, faded paint
    bare = ss(0.62, 0.82, fbm(Pp * np.array([1, 1, 0.3], np.float32), 14.0, 3, seed=614)) * (0.30 + 0.70 * ss(0.6, 0.15, zf))
    c = mixc(c, GREEN_WORN, bare * (0.55 + 0.35 * weather))
    c = mixc(c, GREEN_STREAK, streak * 0.35)
    c = mixc(c, lin(70, 40, 26), np.exp(-((y - KK.BELL.y) / 0.05) ** 2) * (x > KK.X1 - 0.01) * ss(2.55, 1.9, z) * 0.6)  # rust under the bell
    c = mixc(c, lin(70, 40, 26), np.exp(-((x - KK.BULK.x) / 0.05) ** 2) * (y > KK.Y1 - 0.01) * ss(2.40, 2.0, z) * (z > 2.37) * 0.5)
    c = mixc(c, lin(60, 52, 44), ss(0.45, 0.08, zf) * 0.55)                              # splash at the foot
    c = c * (1 - 0.10 * bat * ss(0.3, 0.9, n_mid))[:, None] * (1 + 0.08 * bat)[:, None]
    col[m] = c[m]
    edge_b = np.maximum(gline(dist_periodic(s_wall - 0.025, 0.20), 0.006, aa), gline(dist_periodic(s_wall + 0.025, 0.20), 0.006, aa))
    gr = np.where(m, edge_b * 0.8, gr)
    # ---- the door outside: grey-green boards, worn at the lever and the foot
    m = M(K.Z_DOOR)
    bi, seam = boards(x, 0.12, aa, 0.004)
    c = GREEN * (0.92 + 0.14 * hash1(bi, 5))[:, None] * (0.88 + 0.18 * (n_lo - 0.5) * 2)[:, None]
    c = mixc(c, GREEN_WORN, ss(0.62, 0.84, fbm(Pp * np.array([1, 1, 0.3], np.float32), 14.0, 3, seed=620)) * ss(0.7, 0.15, zf) * 0.9)
    c = mixc(c, lin(66, 58, 48), ss(0.40, 0.11, zf) * 0.6)
    c = mixc(c, lin(52, 60, 50), np.exp(-(((x - KK.LEAF['x0'] - 0.10) / 0.10) ** 2 + ((z - 1.0) / 0.14) ** 2)) * 0.6)
    col[m] = c[m]
    gr = np.where(m, seam * 0.8, gr)
    m = M(K.Z_DOORIN)                                               # the door inside: the shed's raw boards
    bi, seam = boards(np.where(fb, x, y), 0.12, aa, 0.004)
    c = lin(146, 118, 82) * (0.90 + 0.16 * hash1(bi, 6))[:, None] * (0.86 + 0.2 * (n_lo - 0.5) * 2)[:, None]
    c = mixc(c, lin(92, 74, 54), cav * 0.4 + ss(0.5, 0.12, zf) * 0.4)
    col[m] = c[m]
    gr = np.where(m, seam * 0.7, gr)
    # ---- white trims (the shed's), leaves on the sills
    m = M(K.Z_TRIMW)
    c = trim_white(Pp, T, edge, cav, z, streak, z0=KK.FLOOR - K.FLOOR)
    col[m] = mixc(c, lv_c, lv * 0.8)[m]
    # ---- inside: the shed's birch-ply lining; grime low, nicotine toward the roof, hands at the key cabinet, the pass window
    # and the door, a paler patch where a notice hung on the left wall
    m = M(K.Z_LINING)
    c = T(lin(178, 150, 108), 0.14, 0.16)
    grain = fbm(Pp * np.array([3.0, 3.0, 0.4], np.float32), 9.0, 2, seed=616)
    c = c * (0.90 + 0.14 * grain)[:, None]
    sheet = np.maximum(gline(dist_periodic(s_wall, 1.22, 0.0), 0.005, aa),
                       gline(dist_periodic(zf, 1.22), 0.005, aa) * (zf < 2.30))
    nails = (1 - ss(0.004 - aa, 0.006 + aa, dist_periodic(s_wall, 0.60, 0.30))) * (1 - ss(0.004 - aa, 0.006 + aa, dist_periodic(z, 0.15)))
    c = mixc(c, lin(96, 80, 60), ss(0.75, 0.10, zf) * 0.45 * (0.6 + 0.4 * n_mid))
    c = mixc(c, lin(150, 120, 62), ss(1.85, 2.70, z) * 0.35)
    hand = (np.exp(-(((x + 0.51) / 0.30) ** 2 + ((z - 1.80) / 0.25) ** 2)) * (y > KK.IY1 - 0.05)
            + np.exp(-(((y + 0.60) / 0.35) ** 2 + ((z - 1.35) / 0.15) ** 2)) * (x > KK.IX1 - 0.05)
            + np.exp(-(((x - KK.DOOR['x0']) / 0.08) ** 2 + ((z - 1.05) / 0.18) ** 2)))
    c = mixc(c, lin(92, 76, 58), np.clip(hand, 0, 1) * 0.35)
    ghost = (x < KK.IX0 + 0.02) & (y > -1.32) & (y < -0.74) & (z > 1.44) & (z < 2.06)
    c = np.where(ghost[:, None], c * 1.12 + lin(10, 8, 4), c)
    c = mixc(c, lin(120, 98, 70), streak * 0.30)
    col[m] = c[m]
    gr = np.where(m, np.maximum(sheet * 0.75, nails * 0.6), gr)
    # ---- raw spruce (the shed's): rafters, purlins, sills, the counter board, tracks; leaves outside
    m = M(K.Z_TIMBER)
    c = timber(Pp, Nn, T, cav, up, n_mid)
    c = mixc(c, lin(110, 104, 92), outside * ss(0.4, 0.8, n_lo) * 0.45 * (z < 2.5))     # greyed outside
    col[m] = mixc(c, lv_c, lv * 0.8)[m]
    # ---- the roof: corrugations down the slope (along y), laps every 0.76 m, rust runs toward the low back eave, moss,
    # needles and leaves; the underside (the shed's)
    for zz, top in ((K.Z_ROOF, True), (K.Z_ROOFUNDER, False)):
        m = M(zz)
        shade = 0.82 + 0.18 * np.cos(2 * np.pi * x / 0.076)
        c = T(lin(150, 154, 150) if top else lin(118, 120, 116), 0.18, 0.20) * shade[:, None]
        run = ss(0.58, 0.82, fbm(Pp * np.array([1, 0.15, 0.15], np.float32), 7.0, 3, seed=618)) * ss(-1.2, 1.9, y)
        c = mixc(c, RUST if top else RUST_D, run * (0.75 if top else 0.45))
        c = mixc(c, lin(96, 92, 86), ss(0.65, 0.85, n_mid) * 0.35)
        if top:
            c = mixc(c, lin(72, 76, 48), ss(0.58, 0.80, fbm(Pp, 3.0, 3, seed=619)) * ss(-0.5, 1.5, y) * 0.5)
            lt, lc = _leaves(Pp, np.ones(n, np.float32), np.ones(n, np.float32), 621)
            c = mixc(c, lc, lt * 0.9)
        else:
            c = mixc(c, lin(60, 58, 52), ss(0.62, 0.80, fbm(Pp, 16.0, 2, seed=622)) * 0.35)
        col[m] = c[m]
        gr = np.where(m, gline(dist_periodic(x, 0.76, 0.38), 0.010, aa) * 0.8, gr)
    # ---- the pad: concrete, joints, a darker drip line under the back eave, a worn path round to the door, leaves
    m = M(K.Z_SLAB)
    c = T(CONCRETE, 0.16, 0.22)
    c = mixc(c, lin(86, 82, 76), ss(0.0, -0.12, z) * 0.6 + cav * 0.4)
    c = mixc(c, EARTH, ss(-0.22, -0.40, z) * 0.75)
    top = (Nn[:, 2] > 0.8).astype(np.float32)
    c = mixc(c, lin(98, 96, 90), top * np.exp(-((y - KK.YB) / 0.09) ** 2) * (np.abs(x) < KK.XS) * 0.6)
    c = mixc(c, lin(108, 100, 88), top * (np.exp(-((y - 2.0) / 0.35) ** 2) * ss(-3.2, -2.0, x) * ss(1.3, 0.6, x)
                                          + np.exp(-((x + 2.6) / 0.30) ** 2) * ss(-2.6, -1.0, y)) * 0.35)
    c = mixc(c, MOSS, top * ss(0.66, 0.84, fbm(Pp, 5.0, 2, seed=623)) * ss(1.8, 2.5, np.maximum(np.abs(x) - 0.6, np.abs(y))) * 0.5)
    c = mixc(c, lv_c, lv * 0.85)
    col[m] = c[m]
    jt = np.maximum(gline(np.abs(x), 0.006, aa), gline(np.abs(y), 0.006, aa)) * top
    gr = np.where(m, jt * 0.7, gr)
    # ---- the floor inside: concrete, a trodden path door -> desk -> key cabinet, castor scuffs, dirt by the door
    m = M(K.Z_FLOOR)
    c = T(lin(116, 113, 106), 0.18, 0.20)
    c = c * (0.92 + 0.12 * fbm(Pp * np.array([1, 1, 0.0], np.float32), 1.2, 2, seed=624))[:, None]
    dx_ = (KK.DOOR['x0'] + KK.DOOR['x1']) / 2
    path = (np.exp(-((x - dx_) / 0.32) ** 2) * ss(-0.6, 1.2, y)
            + np.exp(-(((x - KK.CHAIR.x) / 0.45) ** 2 + ((y - KK.CHAIR.y) / 0.40) ** 2))
            + 0.6 * np.exp(-((y - 1.15) / 0.22) ** 2) * ss(-0.9, -0.5, x) * ss(1.2, 0.6, x))
    c = mixc(c, lin(84, 78, 68), np.clip(path, 0, 1) * 0.45 * (0.6 + 0.4 * n_mid))
    c = mixc(c, lin(70, 62, 50), np.exp(-(((x - dx_) / 0.45) ** 2 + ((y - KK.IY1) / 0.30) ** 2)) * 0.55)
    rr = np.hypot(x - KK.CHAIR.x, y - KK.CHAIR.y)
    c = mixc(c, lin(78, 76, 72), ss(0.08, 0.0, np.abs(rr - 0.30)) * ss(0.4, 0.7, fbm(Pp, 30.0, 1, seed=625)) * 0.5)
    lt, lc = _leaves(Pp, np.ones(n, np.float32), np.ones(n, np.float32), 626)
    c = mixc(c, lc, lt * ss(0.3, 1.3, y) * 0.8)
    c = mixc(c, lin(60, 56, 50), cav * 0.5)
    col[m] = c[m]
    gr = np.where(m, gline(dist_periodic(x, 1.32, 0.0), 0.006, aa) * 0.6, gr)
    # ---- metals (the shed's)
    m = M(K.Z_STEELBLK)
    col[m] = steel_black(Pp, T, edge)[m]
    m = M(K.Z_GALV)
    c = galv(Pp, T)
    c = mixc(c, EARTH, ss(GROUND + 0.25, GROUND + 0.02, z) * (outside > 0.5) * 0.45)
    col[m] = c[m]
    m = M(K.Z_ENAMEL_IN)
    c = T(lin(232, 230, 222), 0.06, 0.08)
    col[m] = mixc(c, lin(150, 140, 110), ss(0.6, 0.9, fbm(Pp, 20.0, 2, seed=627)) * 0.4 + up * 0.3)[m]
    # ---- yellow-black bollards: bands, chips to steel, rust low down
    m = M(KK.Z_BOLLARD)
    band = np.mod(np.floor((z - KK.FLOOR) / 0.15), 2) == 0
    c = np.where(band[:, None], lin(228, 186, 40), lin(30, 30, 30)) * (0.88 + 0.18 * n_hi)[:, None]
    c = np.where((z > KK.FLOOR + 0.80)[:, None], lin(30, 30, 30) * (0.9 + 0.2 * n_hi)[:, None], c)
    c = mixc(c, lin(90, 86, 80), np.clip(ss(0.80, 0.92, fbm(Pp, 30.0, 2, seed=628)) * 0.8 + edge * 0.4, 0, 1))
    c = mixc(c, RUST, ss(KK.FLOOR + 0.20, KK.FLOOR, z) * 0.6)
    col[m] = c[m]
    # ---- the desk: varnished birch ply; worn pale where the arms rest, mug rings, an ink stain
    m = M(KK.Z_DESK)
    vert = np.abs(Nn[:, 2]) < 0.6
    g2 = fbm(Pp * np.where(vert[:, None], np.array([4.0, 4.0, 0.3], np.float32), np.array([0.3, 4.0, 4.0], np.float32)), 9.0, 2, seed=629)
    c = T(lin(176, 146, 100), 0.12, 0.12) * (0.88 + 0.18 * g2)[:, None]
    ontop = (Nn[:, 2] > 0.8) & (np.abs(z - KK.DESK_TOP) < 0.005)
    rub = (np.exp(-(((x - 1.50) / 0.18) ** 2 + ((y + 0.45) / 0.30) ** 2)) + np.exp(-(((x + 1.05) / 0.35) ** 2 + ((y + 0.98) / 0.10) ** 2)))
    c = mixc(c, lin(204, 180, 136), ontop * np.clip(rub, 0, 1) * 0.5)
    ring_ = ss(0.006, 0.0, np.abs(np.hypot(x - 0.52, y + 1.18) - 0.042)) + ss(0.006, 0.0, np.abs(np.hypot(x - 1.75, y + 0.20) - 0.040))
    c = mixc(c, lin(96, 70, 44), ontop * np.clip(ring_, 0, 1) * 0.6)
    c = mixc(c, lin(40, 46, 80), ontop * ss(0.035, 0.02, np.hypot(x + 0.62, y + 1.05)) * 0.7)
    c = mixc(c, lin(120, 94, 62), (~ontop & ~vert) * 0.25 + cav * 0.45)
    c = mixc(c, lin(90, 72, 50), np.exp(-(((y - 0.745) / 0.08) ** 2)) * (Nn[:, 0] < -0.8) * (x < 1.43) * 0.3)    # drawer pulls
    col[m] = c[m]
    # ---- the filing cabinet: office grey, chipped edges, dust on top
    m = M(KK.Z_CABGREY)
    c = T(lin(128, 132, 128), 0.10, 0.12)
    c = mixc(c, lin(70, 72, 70), np.clip(edge * 0.8 + ss(0.82, 0.92, fbm(Pp, 30.0, 2, seed=630)) * 0.5, 0, 0.8))
    col[m] = mixc(c, DUST, up * 0.3)[m]
    # ---- the key cabinet: cream steel, darker round the lock
    m = M(KK.Z_KEYBOX)
    c = T(lin(196, 188, 158), 0.08, 0.10)
    c = mixc(c, lin(110, 104, 90), np.clip(edge * 0.7 + ss(0.84, 0.94, fbm(Pp, 30.0, 2, seed=631)) * 0.5, 0, 0.8))
    c = mixc(c, lin(120, 110, 90), np.exp(-(((x + 0.29) / 0.06) ** 2 + ((z - 1.80) / 0.08) ** 2)) * 0.5)
    col[m] = c[m]
    # ---- cork
    m = M(KK.Z_CORK)
    c = T(lin(166, 118, 70), 0.10, 0.14) * (0.80 + 0.35 * fbm(Pp, 120.0, 1, seed=632))[:, None]
    col[m] = mixc(c, lin(110, 76, 46), ss(0.7, 0.9, fbm(Pp, 12.0, 2, seed=633)) * 0.4)[m]
    # ---- the convector: white enamel, a grille of slots on top and high on the front, rust spots low
    m = M(KK.Z_HEATER)
    c = T(lin(214, 210, 198), 0.06, 0.08)
    slots = (dist_periodic(y, 0.04) < 0.012) & (((Nn[:, 2] > 0.8)) | ((Nn[:, 0] > 0.8) & (z > KK.HEATER['z1'] - 0.10)))
    c = np.where(slots[:, None], lin(40, 40, 38), c)
    c = mixc(c, RUST, ss(0.80, 0.92, fbm(Pp, 25.0, 2, seed=634)) * ss(0.45, 0.30, z) * 0.6)
    col[m] = mixc(c, DUST, up * 0.25)[m]
    # ---- the boom: red and white bands every 0.5 m, chipped edges, dirt on the underside
    m = M(KK.Z_BOOM)
    bx = x - KK.BARRIER_PLACE[0].x
    red = np.mod(np.floor((bx - 0.04) / 0.5), 2) == 0
    c = np.where(red[:, None], lin(196, 36, 26), lin(230, 228, 220)) * (0.88 + 0.16 * n_hi)[:, None]
    c = mixc(c, lin(70, 66, 60), np.clip(edge * 0.8 + ss(0.84, 0.94, fbm(Pp, 30.0, 2, seed=635)) * 0.6, 0, 0.9))
    c = mixc(c, lin(96, 88, 76), np.clip(-Nn[:, 2], 0, 1) * 0.35 + streak * 0.2)
    col[m] = c[m]
    # ---- the barrier posts: white enamel with red bands (the post, the rest post), chips, earth at the foot
    m = M(KK.Z_BARPOST)
    zl = z - GROUND
    redb = ((zl > 0.55) & (zl < 0.70)) | ((zl > 0.95) & (zl < 1.08))
    c = np.where(redb[:, None], lin(196, 36, 26), lin(226, 224, 216)) * (0.90 + 0.14 * n_hi)[:, None]
    c = mixc(c, lin(80, 76, 70), np.clip(edge * 0.7 + ss(0.84, 0.94, fbm(Pp, 30.0, 2, seed=636)) * 0.5, 0, 0.9))
    c = mixc(c, EARTH, ss(0.40, 0.15, zl) * 0.6)
    col[m] = c[m]
    m = M(KK.Z_RUBBER_K)
    col[m] = mixc(T(lin(34, 34, 34), 0.10, 0.16), lin(90, 88, 82), up * 0.3 + edge * 0.3)[m]
    m = M(KK.Z_GATEROLL)
    c = T(lin(70, 70, 72), 0.12, 0.18)
    c = mixc(c, RUST, ss(0.55, 0.80, fbm(Pp, 25.0, 2, seed=637)) * 0.6)
    col[m] = mixc(c, lin(150, 150, 146), edge * 0.6)[m]
    # ---- footings and the rail strip: concrete, earth at the ground line, moss and leaves on top
    m = M(KK.Z_CONC)
    zl = z - GROUND
    c = T(lin(126, 124, 118), 0.16, 0.22)
    c = mixc(c, EARTH, ss(0.06, -0.06, zl) * 0.8)
    c = mixc(c, MOSS, up * ss(0.62, 0.82, fbm(Pp, 6.0, 2, seed=638)) * 0.5)
    col[m] = mixc(c, lv_c, lv * 0.8)[m]
    m = M(KK.Z_BARBED)
    c = T(lin(100, 100, 96), 0.12, 0.2)
    col[m] = mixc(c, RUST, ss(0.5, 0.8, fbm(Pp, 12.0, 2, seed=639)) * 0.7)[m]
    # ---- v2: the motor cabinets (the barrier's, the gate drive): light grey powder coat, chips with rust at the edges,
    # splash and earth at the foot, dust on the top, grime runs under the black cover
    m = M(KK.Z_BARCAB)
    if m.any():
        zl = z - GROUND
        c = T(lin(200, 204, 198), 0.06, 0.08)
        c = mixc(c, lin(168, 170, 162), ss(0.35, 0.75, n_lo) * 0.35)
        c = mixc(c, lin(120, 118, 108), streak * 0.30 * (np.abs(Nn[:, 2]) < 0.5))
        c = mixc(c, RUST, np.clip(edge * 0.55 + ss(0.86, 0.95, fbm(Pp, 30.0, 2, seed=641)) * 0.6, 0, 0.8) * 0.6)
        c = mixc(c, lin(92, 84, 72), ss(0.30, 0.05, zl) * 0.65)
        c = mixc(c, DUST, up * 0.35)
        col[m] = c[m]
    # ---- the gate leaf: the station's green on steel, a pressed rib every 0.2 m on the outer sheet, rust runs from the top
    # rail and the barbed arms, chipped edges, the splash at the foot, the outer face weathered most
    m = M(KK.Z_GATEP)
    if m.any():
        zl = z - GROUND
        outer = (Nn[:, 1] < -0.5).astype(np.float32)
        rib = 0.5 + 0.5 * np.cos(2 * np.pi * x / 0.20)
        c = lin(84, 100, 78) * (0.90 + 0.10 * rib * outer + 0.12 * (n_lo - 0.5))[:, None]
        c = mixc(c, lin(120, 132, 108), outer * ss(0.40, 0.80, n_lo) * 0.40)
        runs = ss(0.55, 0.80, fbm(Pp * np.array([3.0, 3.0, 0.12], np.float32), 8.0, 3, seed=642)) * ss(1.0, 2.3, zl)
        c = mixc(c, RUST, np.clip(runs * 0.65 + edge * 0.5 + ss(0.86, 0.95, fbm(Pp, 25.0, 2, seed=643)) * 0.5, 0, 0.85))
        c = mixc(c, lin(70, 62, 50), ss(0.45, 0.12, zl) * 0.6)
        col[m] = c[m]
        gr = np.where(m, gline(dist_periodic(x, 0.20, 0.10), 0.004, aa) * 0.35 * outer, gr)
    return col, gr


# ================================================================ the small things
def paint_props(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 701)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(120, 120, 120), (n, 1))
    chip = ss(0.80, 0.92, fbm(Pp, 40.0, 2, seed=711))
    m = M(KK.Z_PHONE)                                               # 70s orange plastic, greasy where the hand goes
    c = T(lin(196, 96, 42), 0.08, 0.12)
    c = mixc(c, lin(120, 64, 34), cav * 0.5 + np.exp(-(((x - KK.PHONE.x - 0.05) / 0.05) ** 2 + ((y - KK.PHONE.y) / 0.06) ** 2)) * up * 0.3)
    col[m] = c[m]
    m = M(KK.Z_VEST)                                                # hi-vis orange, two silver bands
    c = T(lin(232, 112, 30), 0.08, 0.12)
    bands = (np.abs(z - 1.42) < 0.025) | (np.abs(z - 1.55) < 0.025)
    c = np.where(bands[:, None], lin(196, 198, 192) * (0.85 + 0.2 * n_hi)[:, None], c)
    col[m] = mixc(c, lin(120, 70, 30), ss(0.6, 0.85, n_mid) * 0.35 + cav * 0.4)[m]
    m = M(KK.Z_EXTP)                                                # red extinguisher, a white label band
    c = T(lin(180, 30, 24), 0.08, 0.12)
    lab = (z > 0.82) & (z < 0.98) & (np.abs(Nn[:, 2]) < 0.5) & (y < KK.IY1 - 0.10)
    c = np.where(lab[:, None], lin(226, 222, 206), c)
    col[m] = mixc(c, lin(90, 30, 24), chip * 0.5 + edge * 0.3)[m]
    m = M(KK.Z_CRT)                                                 # beige plastic, yellowed, vents on the back
    c = T(lin(196, 186, 160), 0.08, 0.10)
    c = mixc(c, lin(170, 150, 100), ss(0.4, 0.8, n_lo) * 0.4)
    vent = (y < KK.MONITOR.y - 0.12) & (dist_periodic(z, 0.03) < 0.008)
    col[m] = mixc(np.where(vent[:, None], lin(50, 48, 44), c), lin(110, 100, 80), cav * 0.4)[m]
    m = M(KK.Z_CHAIR)                                               # blue-grey fabric, worn shiny on the seat front
    c = T(lin(60, 66, 80), 0.10, 0.16) * (0.85 + 0.25 * fbm(Pp, 120.0, 1, seed=712))[:, None]
    c = mixc(c, lin(96, 100, 110), up * np.exp(-((x - KK.CHAIR.x - 0.12) / 0.12) ** 2) * 0.4)
    col[m] = mixc(c, lin(30, 32, 40), cav * 0.4)[m]
    m = M(KK.Z_BLACKP)
    c = T(lin(32, 32, 34), 0.10, 0.16)
    col[m] = mixc(c, lin(90, 90, 90), edge * 0.4 + up * 0.15)[m]
    m = M(KK.Z_BELLP)
    c = T(lin(170, 30, 26), 0.10, 0.14)
    col[m] = mixc(mixc(c, lin(150, 150, 146), chip * 0.6), RUST, ss(0.7, 0.9, n_mid) * 0.4)[m]
    m = M(KK.Z_PAPERP)                                              # papers: typed lines on the top sheet
    c = T(lin(226, 222, 204), 0.04, 0.06)
    lines = (dist_periodic(y, 0.012) < 0.002) & (Nn[:, 2] > 0.8)
    col[m] = np.where(lines[:, None], lin(130, 128, 120), c)[m]
    m = M(KK.Z_MUGP)                                                # white enamel mug, a blue rim, chipped
    c = T(lin(226, 224, 214), 0.06, 0.08)
    c = np.where((z > KK.DESK_TOP + 0.082)[:, None], lin(40, 60, 120), c)
    col[m] = mixc(c, lin(20, 20, 22), np.clip(chip * 0.9 + edge * 0.5, 0, 1))[m]
    m = M(KK.Z_FLASK)                                               # green thermos, a steel cup on top
    c = T(lin(60, 100, 70), 0.08, 0.12)
    c = np.where((z > KK.DESK_TOP + 0.25)[:, None], lin(170, 172, 168) * (0.85 + 0.2 * n_hi)[:, None], c)
    col[m] = mixc(c, lin(30, 50, 34), chip * 0.4)[m]
    m = M(KK.Z_BINDER)                                              # binders: blue, red, grey; a white spine label
    k_ = np.floor((y + 2.0) / 0.07)
    bc = np.where((np.mod(k_, 3) == 0)[:, None], lin(50, 70, 140), np.where((np.mod(k_, 3) == 1)[:, None], lin(150, 40, 36), lin(90, 92, 96)))
    c = bc * (0.88 + 0.16 * n_hi)[:, None]
    spine = (Nn[:, 0] > 0.8) & (z > KK.DESK_TOP + 0.12) & (z < KK.DESK_TOP + 0.24)
    col[m] = np.where(spine[:, None], lin(226, 222, 204), c)[m]
    m = M(KK.Z_RADIO)                                               # olive drab, worn to dark metal on the edges
    c = T(lin(88, 96, 68), 0.10, 0.14)
    col[m] = mixc(c, lin(46, 46, 42), np.clip(edge * 0.8 + chip * 0.4, 0, 0.9))[m]
    m = M(KK.Z_CAMP)                                                # CCTV housing: off-white, dirty, streaked
    c = T(lin(200, 200, 196), 0.08, 0.12)
    col[m] = mixc(c, lin(110, 106, 96), ss(0.5, 0.8, n_mid) * 0.4 + cav * 0.4)[m]
    m = M(KK.Z_CHROMEP)
    c = T(lin(170, 172, 176), 0.10, 0.20)
    col[m] = mixc(c, lin(60, 60, 62), ss(0.4, 0.8, n_hi) * 0.4)[m]
    m = M(KK.Z_FAID)                                                # first-aid box: white plastic, yellowed, a green stripe
    c = T(lin(226, 226, 220), 0.06, 0.08)
    c = np.where((np.abs(z - (KK.FAID['z0'] + 0.03)) < 0.012)[:, None], lin(0, 120, 66), c)
    col[m] = mixc(c, lin(170, 160, 120), ss(0.5, 0.8, n_lo) * 0.3 + cav * 0.4)[m]
    return col, None
