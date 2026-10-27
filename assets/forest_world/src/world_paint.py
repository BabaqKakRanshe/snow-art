"""Painters for the forest_world atlases (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
World (the fire barrel, the two cars and their snow): the barrel burnt to rust with heat scale at the rim, a little of
its blue paint left low, soot over the air holes, black inside, grey ash, split logs charred at the ends; the shift car
in the station's grey-green, a season old - faded on the tops, chipped, road salt and mud low, rust starting at the arches;
the wreck faded from dark blue to a chalky blue-grey, rusted through at the sills, arches, the boot and round the
windscreen, moss in the rubbers, years of needles on the roof and the hood. Cave: Harz-like granite as forest_rocks
outside (lichen, moss, needles, soil at the foot), inside darker and damp with water streaks, soot over the candles; an
earth floor with needles, the sawdust by the saw; spruce boughs, olive army wool, wax, the saw's orange bow, leather
boots with a deep sole pattern, tins, a zinc bucket, rags. Positions: the roots stand at world_kit.DISPLAY while baked."""
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, hash1
from gen_paint import DUST, RUST, RUST_D, _T, _common
import world_kit as WK
import rocks_paint as RP

GREEN, GREEN_FADE, GREEN_D = lin(88, 104, 92), lin(132, 144, 132), lin(60, 72, 64)
BLUE, BLUE_FADE, BLUE_CHALK = lin(34, 50, 84), lin(92, 106, 128), lin(140, 150, 162)
MUD, MUD_D, SALT = lin(92, 78, 60), lin(58, 48, 38), lin(170, 168, 160)
SNOW, SNOW_B = lin(236, 240, 244), lin(176, 190, 206)
NEEDLE_A, NEEDLE_B, LEAF, MOSS = lin(132, 92, 46), lin(96, 70, 40), lin(150, 96, 44), lin(70, 86, 40)
DRAFT_COL = {
    WK.Z_DRUM: (110, 62, 36), WK.Z_DRUMIN: (26, 24, 22), WK.Z_ASH: (150, 148, 142), WK.Z_LOG: (150, 116, 80), WK.Z_CHAR: (30, 28, 26),
    WK.Z_PAINT_S: (88, 104, 92), WK.Z_PAINT_W: (60, 74, 104), WK.Z_CBLACK: (36, 36, 38), WK.Z_UNDER: (40, 34, 28),
    WK.Z_TYRE: (30, 30, 30), WK.Z_RIM: (150, 150, 146), WK.Z_CHROME: (170, 170, 168), WK.Z_HEAD: (200, 204, 196),
    WK.Z_TAIL: (170, 40, 30), WK.Z_SEAT: (100, 90, 76), WK.Z_DASH: (40, 40, 42), WK.Z_CARPET: (60, 48, 38), WK.Z_LINER: (176, 166, 140),
    WK.Z_CARD: (96, 86, 72), WK.Z_GRILLE: (28, 28, 30), WK.Z_PLATE: (40, 38, 34), WK.Z_CARGO: (32, 32, 32), WK.Z_GAUGE: (20, 20, 20),
    WK.Z_RUBBER: (22, 22, 22), WK.Z_SNOW: (236, 240, 244), WK.Z_DISC: (110, 70, 44), WK.Z_RACK: (30, 30, 30), WK.Z_AMBER: (220, 140, 30),
    WK.Z_ROCK: (126, 122, 114), WK.Z_ROCKIN: (90, 88, 84), WK.Z_CFLOOR: (80, 66, 50), WK.Z_ROCKD: (50, 41, 31),
    WK.Z_BOUGH: (52, 70, 40), WK.Z_BLANKET: (88, 92, 72), WK.Z_CANDLE: (226, 216, 190), WK.Z_WAX: (210, 200, 170),
    WK.Z_SAWB: (150, 150, 148), WK.Z_SAWF: (200, 90, 30), WK.Z_SAWDUST: (214, 184, 132), WK.Z_BOOT: (62, 44, 30),
    WK.Z_SOLE: (26, 26, 26), WK.Z_TIN: (150, 150, 146), WK.Z_NAIL: (50, 48, 46), WK.Z_RAG: (110, 100, 86), WK.Z_BUCKET: (150, 154, 152),
    WK.Z_WIRE: (140, 90, 50), WK.Z_STONE: (120, 116, 108), WK.Z_BOTTLE: (70, 46, 22)}


def _local(Pp, root):
    o = WK.DISPLAY[root]
    return Pp[:, 0] - o.x, Pp[:, 1] - o.y, Pp[:, 2] - o.z


def _litter(Pp, up, seed, amount=1.0):
    x, y = Pp[:, 0], Pp[:, 1]
    m = (ss(0.52, 0.72, fbm(Pp, 5.0, 3, seed=seed)) * 0.7 + ss(0.62, 0.80, fbm(Pp, 30.0, 1, seed=seed + 1)) * 0.6) * up * amount
    pick = hash1(np.floor(x * 53.0) + np.floor(y * 47.0) * 13.0, seed)
    c = np.where((pick > 0.70)[:, None], LEAF, np.where((pick > 0.35)[:, None], NEEDLE_A, NEEDLE_B))
    return np.clip(m, 0, 1), c


def _car_paint(Pp, Nn, ao, aa, S, root, base, fade, chalk, rust_k, seed):
    """car paint at the car's own positions: fade on the tops, rust at arches / sills / edges (rust_k 0..1), mud low"""
    x, y, z = _local(Pp, root)
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, seed)
    c = base * (0.88 + 0.16 * (n_lo - 0.5) + 0.08 * (n_hi - 0.5))[:, None]
    c = mixc(c, fade, ss(0.15, 0.85, up) * (0.45 + 0.35 * n_lo))
    c = mixc(c, chalk, ss(0.6, 0.95, up) * ss(0.45, 0.80, fbm(Pp, 4.0, 3, seed=seed + 10)) * (0.25 + 0.5 * rust_k))
    arch = np.zeros(n, np.float32)
    for yc in (S['YFA'], S['YRA']):
        d = np.hypot(y - yc, z - S['RW'])
        arch = np.maximum(arch, ss(S['RA'] + 0.10, S['RA'] + 0.01, d) * (np.abs(x) > S['CW'] - 0.06))
    sill = ss(S['ZSILL'] + 0.12, S['ZSILL'], z) * (np.abs(x) > S['CW'] - 0.06)
    tail = ss(S['ZBR'] - 0.15, S['ZRB'], z) * (y > S['YR'] - 0.05)
    ws = np.exp(-(((y - S['YWS']) / 0.10) ** 2)) * (z > S['ZHW'] - 0.05)
    mask = np.clip(arch + sill + tail * 0.8 + edge * 0.5 + ws * 0.6 * rust_k, 0, 1) * ss(0.35, 0.65, fbm(Pp, 22.0, 3, seed=seed + 11))
    bubbles = ss(0.80 - 0.12 * rust_k, 0.90 - 0.12 * rust_k, fbm(Pp, 55.0, 2, seed=seed + 12)) * (0.3 + 0.7 * ss(0.9, 0.4, z))
    c = mixc(c, RUST, np.clip((mask * 1.2 + bubbles * 0.5) * (0.35 + 0.65 * rust_k), 0, 1))
    c = mixc(c, RUST_D, np.clip(mask - 0.55, 0, 1) * 1.5 * rust_k)
    chips = ss(0.86, 0.92, fbm(Pp, 70.0, 2, seed=seed + 13)) * (0.4 + 0.6 * edge)
    c = mixc(c, lin(150, 150, 146), chips * (1 - rust_k) * 0.6)
    c = mixc(c, MUD, ss(S['ZSILL'] + 0.30, S['ZSILL'], z) * (0.5 + 0.5 * ss(0.3, 0.7, fbm(Pp, 8.0, 2, seed=seed + 14))) * 0.85)
    c = mixc(c, SALT, ss(S['ZSILL'] + 0.25, S['ZSILL'], z) * ss(0.5, 0.75, fbm(Pp, 7.5, 3, seed=seed + 15)) * 0.4 * (1 - rust_k))
    streak = ss(0.55, 0.80, fbm(Pp * np.array([1, 1, 0.12], np.float32), 6.0, 3, seed=seed + 16))
    c = mixc(c, lin(70, 60, 50), streak * 0.25 * (1 - up))
    return c, x, y, z, up, cav, n_hi, n_mid


def paint_world(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 4101)
    T = _T(n_lo, n_hi)
    # ================================================================ the fire barrel
    bx, by, bz = _local(Pp, 'FireBarrel')
    m = M(WK.Z_DRUM)
    c = T(RUST, 0.18, 0.2)
    c = mixc(c, RUST_D, ss(0.55, 0.80, fbm(Pp, 9.0, 3, seed=4102)) * 0.7)
    c = mixc(c, lin(40, 58, 96), ss(0.30, 0.10, bz) * ss(0.40, 0.65, fbm(Pp, 6.0, 2, seed=4103)) * 0.8)      # its blue paint, low
    scale = ss(0.55, 0.86, bz)                                                                              # heat scale at the rim
    c = mixc(c, lin(58, 54, 56), scale * (0.5 + 0.4 * fbm(Pp, 14.0, 2, seed=4104)))
    c = mixc(c, lin(96, 92, 100), scale * ss(0.6, 0.8, fbm(Pp, 30.0, 2, seed=4105)) * 0.5)
    ang = np.arctan2(by, bx)
    soot = np.zeros(n, np.float32)
    for zh, k_, ph in WK.DR['holes']:
        a0 = 2 * np.pi * ph / k_
        da = np.abs(((ang - a0) / (2 * np.pi / k_) + 0.5) % 1.0 - 0.5) * (2 * np.pi / k_) * WK.DR['r']
        soot = np.maximum(soot, ss(0.045, 0.012, da) * ss(zh - 0.02, zh + 0.03, bz) * ss(zh + 0.30, zh + 0.04, bz))
    c = mixc(c, lin(22, 20, 18), np.clip(soot * 0.9 + ss(0.80, 0.88, bz) * 0.5, 0, 1))
    col[m] = c[m]
    m = M(WK.Z_DRUMIN)
    c = T(lin(26, 24, 22), 0.2, 0.3)
    c = mixc(c, RUST_D, ss(0.6, 0.8, fbm(Pp, 12.0, 2, seed=4106)) * 0.5)
    col[m] = c[m]
    m = M(WK.Z_ASH)
    c = T(lin(150, 148, 142), 0.15, 0.25)
    c = mixc(c, lin(40, 38, 36), ss(0.55, 0.75, fbm(Pp, 40.0, 2, seed=4107)) * 0.8)
    col[m] = c[m]
    m = M(WK.Z_LOG)
    bark = ss(0.35, 0.65, fbm(Pp, 18.0, 2, seed=4108))
    c = np.where((bark > 0.5)[:, None], lin(72, 58, 46), lin(176, 140, 92)) * (0.85 + 0.25 * n_hi)[:, None]
    c = mixc(c, lin(30, 26, 22), ss(0.7, 0.9, fbm(Pp, 10.0, 2, seed=4109)) * 0.7)
    col[m] = c[m]
    m = M(WK.Z_CHAR)
    c = T(lin(26, 24, 22), 0.2, 0.3)
    c = mixc(c, lin(120, 118, 112), ss(0.6, 0.8, fbm(Pp, 30.0, 2, seed=4110)) * 0.6)
    crack = gline(dist_periodic(fbm(Pp, 25.0, 1, seed=4111), 0.25), 0.03, 0.01)
    c = mixc(c, lin(10, 10, 10), crack * 0.6)
    col[m] = c[m]
    # ================================================================ the cars
    for root, S, pz, base, fade, chalk, rust_k, seed in (('ShiftCar', WK.SHIFT, WK.Z_PAINT_S, GREEN, GREEN_FADE, lin(160, 168, 156), 0.25, 4200),
                                                          ('WreckCar', WK.WRECK, WK.Z_PAINT_W, BLUE, BLUE_FADE, BLUE_CHALK, 1.0, 4300)):
        m = M(pz)
        if not m.any():
            continue
        c, x, y, z, upc, cavc, nh, nm = _car_paint(Pp, Nn, ao, aa, S, root, base, fade, chalk, rust_k, seed)
        if root == 'WreckCar':                                                  # years under the trees: needles, moss
            lit, lit_c = _litter(Pp, upc, seed + 20, 1.2)
            cowl = np.exp(-(((y - S['YWS'] + 0.10) / 0.16) ** 2)) * (z > S['ZHW'] - 0.06)
            heavy = ss(0.30, 0.62, fbm(Pp, 7.0, 3, seed=seed + 21)) * ss(0.35, 0.95, upc) * (0.45 + 0.55 * np.clip(cowl * 2, 0, 1))
            c = mixc(c, lit_c, np.clip(lit * 0.8 + heavy, 0, 0.95))
            c = mixc(c, MOSS, ss(0.70, 0.86, fbm(Pp, 10.0, 2, seed=seed + 22)) * upc * 0.5)
        else:
            lit, lit_c = _litter(Pp, upc, seed + 20, 0.25)
            c = mixc(c, lit_c, lit * 0.6)
        col[m] = c[m]
        side = (np.abs(x) > S['CW'] - 0.02) & m
        seams = np.zeros(n, np.float32)
        for yy in (S['door']['y0'], S['door']['y1']) + tuple(p[1] for p in S['pillars'][:1]):
            seams = np.maximum(seams, gline(np.abs(y - yy), 0.004, aa) * side * (z > S['ZSILL'] + 0.03) * (z < S['ZB']))
        seams = np.maximum(seams, gline(np.abs(y - S['YWS'] - 0.01), 0.004, aa) * (Nn[:, 2] > 0.8) * m)
        gr = np.where(m, seams * 0.9, gr)
    shift_m = np.abs(Pp[:, 0] - WK.DISPLAY['ShiftCar'].x) < 1.6
    rk = np.where(shift_m, 0.25, 1.0)
    for zz, base in ((WK.Z_CBLACK, lin(38, 38, 40)), (WK.Z_RUBBER, lin(24, 24, 24)), (WK.Z_RACK, lin(30, 30, 32))):
        m = M(zz)
        c = T(base, 0.12, 0.16)
        c = mixc(c, lin(96, 94, 90), up * ss(0.4, 0.8, n_lo) * 0.5)
        c = mixc(c, RUST, ss(0.72, 0.86, fbm(Pp, 20.0, 2, seed=4401)) * rk * 0.8)
        c = mixc(c, MUD, ss(0.55, 0.30, Pp[:, 2]) * 0.6)
        if zz == WK.Z_RUBBER:
            c = mixc(c, MOSS, ss(0.55, 0.80, fbm(Pp, 14.0, 2, seed=4402)) * (1 - shift_m) * 0.6)
        col[m] = c[m]
    m = M(WK.Z_UNDER)
    c = T(lin(44, 38, 32), 0.15, 0.2)
    c = mixc(c, RUST_D, ss(0.6, 0.85, fbm(Pp, 12.0, 2, seed=4403)) * (0.4 + 0.6 * rk))
    c = mixc(c, MUD_D, np.full(n, 0.4, np.float32))
    col[m] = c[m]
    m = M(WK.Z_TYRE)
    c = T(lin(32, 32, 32), 0.12, 0.18)
    c = mixc(c, MUD, ss(0.18, 0.02, Pp[:, 2]) * 0.8 + ss(0.7, 0.9, fbm(Pp, 20.0, 2, seed=4404)) * 0.3)
    c = mixc(c, lin(70, 70, 68), ss(0.4, 0.6, fbm(Pp * 3, 30.0, 1, seed=4405)) * 0.25 * rk)
    col[m] = c[m]
    m = M(WK.Z_RIM)
    c = np.where(shift_m[:, None], T(lin(130, 136, 128), 0.12, 0.16), T(lin(150, 150, 146), 0.12, 0.16))
    c = mixc(c, RUST, ss(0.5, 0.75, fbm(Pp, 30.0, 2, seed=4406)) * (0.3 + 0.6 * rk) + cav * 0.3)
    col[m] = c[m]
    m = M(WK.Z_DISC)
    c = T(RUST, 0.2, 0.3)
    c = mixc(c, RUST_D, ss(0.5, 0.7, fbm(Pp, 30.0, 2, seed=4407)) * 0.7)
    col[m] = c[m]
    m = M(WK.Z_CHROME)
    c = T(lin(168, 168, 166), 0.10, 0.2)
    c = mixc(c, RUST, ss(0.5, 0.8, fbm(Pp, 40.0, 2, seed=4408)) * (0.2 + 0.6 * rk))
    col[m] = c[m]
    m = M(WK.Z_HEAD)
    c = lin(190, 196, 188) * (0.80 + 0.2 * np.mod(np.floor(Pp[:, 0] / 0.012), 2))[:, None] * (0.75 + 0.25 * n_hi)[:, None]
    c = mixc(c, MUD, 0.15 + ss(0.6, 0.8, n_mid) * 0.35)
    col[m] = c[m]
    m = M(WK.Z_AMBER)
    col[m] = (lin(214, 132, 32) * (0.85 + 0.2 * n_hi)[:, None])[m]
    m = M(WK.Z_TAIL)
    zt = Pp[:, 2]
    c = np.where((np.mod(np.floor(zt / 0.06), 3) == 0)[:, None], lin(196, 120, 30), lin(156, 30, 24))
    c = c * (0.80 + 0.2 * (np.mod(np.floor(zt / 0.01), 2)))[:, None]
    c = mixc(c, MUD, 0.30 + ss(0.6, 0.85, n_mid) * 0.3)
    col[m] = c[m]
    m = M(WK.Z_GRILLE)
    bars = np.mod(np.floor(Pp[:, 2] / 0.022), 2)
    col[m] = (np.where((bars > 0)[:, None], lin(52, 52, 54), lin(14, 14, 16)) * (0.9 + 0.1 * n_hi)[:, None])[m]
    gr = np.where(m, gline(dist_periodic(Pp[:, 2], 0.022), 0.003, aa) * 0.6, gr)
    m = M(WK.Z_PLATE)
    col[m] = T(lin(52, 48, 42), 0.1, 0.1)[m]
    m = M(WK.Z_SEAT)
    weave = 0.9 + 0.1 * np.mod(np.floor(Pp[:, 0] / 0.006) + np.floor(Pp[:, 2] / 0.006), 2)
    c = np.where(shift_m[:, None], T(lin(70, 72, 66), 0.12, 0.14), T(lin(96, 84, 112), 0.12, 0.14)) * weave[:, None]
    c = mixc(c, lin(70, 74, 56), ss(0.62, 0.82, fbm(Pp, 9.0, 3, seed=4409)) * 0.6 * (1 - shift_m))
    col[m] = c[m]
    m = M(WK.Z_DASH)
    c = T(lin(42, 42, 44), 0.12, 0.16)
    c = mixc(c, DUST, up * 0.25)
    col[m] = c[m]
    m = M(WK.Z_GAUGE)
    col[m] = lin(18, 18, 18)
    m = M(WK.Z_CARPET)
    lit, lit_c = _litter(Pp, up, 4410, 0.8)
    c = T(lin(62, 50, 40), 0.14, 0.2)
    c = mixc(c, lit_c, lit * (1 - shift_m) * 0.7)
    c = mixc(c, MUD_D, ss(0.6, 0.8, n_mid) * 0.4)
    col[m] = c[m]
    m = M(WK.Z_LINER)
    c = T(lin(176, 166, 140), 0.10, 0.12)
    c = mixc(c, lin(120, 108, 86), ss(0.55, 0.80, fbm(Pp, 4.0, 3, seed=4411)) * 0.6 * (1 - shift_m * 0.7))
    col[m] = c[m]
    m = M(WK.Z_CARD)
    col[m] = T(lin(96, 86, 72), 0.12, 0.14)[m]
    m = M(WK.Z_CARGO)
    rib = np.mod(np.floor(Pp[:, 0] / 0.03), 2)
    col[m] = (np.where((rib > 0)[:, None], lin(36, 36, 36), lin(26, 26, 26)) * (0.9 + 0.1 * n_hi)[:, None])[m]
    m = M(WK.Z_SNOW)
    c = SNOW * (0.94 + 0.08 * n_hi)[:, None]
    c = mixc(c, SNOW_B, ss(0.85, 0.40, ao) * 0.6 + (1 - up) * 0.35)
    c = mixc(c, lin(255, 255, 255), ss(0.93, 0.97, fbm(Pp, 90.0, 1, seed=4412)) * up * 0.5)
    col[m] = c[m]
    return col, gr


# ================================================================ the cave
def paint_cave(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    x, y, z = _local(Pp, 'ForesterCave')
    up, down = np.clip(Nn[:, 2], 0, 1), np.clip(-Nn[:, 2], 0, 1)
    steep = 1.0 - np.abs(Nn[:, 2])
    n_lo = fbm(Pp, 0.55, 3, seed=1)
    n_mid = fbm(Pp, 2.8, 3, seed=2)
    n_hi = fbm(Pp, 22.0, 2, seed=3)
    _, _, _, _, cav, edge = _common(Pp, Nn, ao, 4501)
    T = _T(n_lo, n_hi)
    # granite (forest_rocks' palette): blotches, warm cast, specks, streaks, lichen, moss, needles, soil at the foot
    g = mixc(np.tile(RP.GRANITE, (n, 1)), RP.GRANITE_C, ss(0.38, 0.66, n_lo) * 0.8)
    g = mixc(g, RP.GRANITE_W, ss(0.56, 0.80, n_mid) * 0.45)
    g = g * (0.90 + 0.16 * (n_mid - 0.5) * 2 + 0.10 * (n_hi - 0.5))[:, None]
    sp = fbm(Pp, 26.0, 1, seed=4)                                       # (forest_rocks' 68/m specks alias at this atlas' 37 px/m)
    g = mixc(g, RP.MICA, ss(0.30, 0.22, sp) * 0.30)
    g = mixc(g, RP.QUARTZ, ss(0.72, 0.80, sp) * 0.22)
    st = fbm(Pp, 4.5, 2, seed=5, stretch=(1.0, 1.0, 0.13))
    g = mixc(g, RP.STREAK, ss(0.60, 0.74, st) * ss(0.35, 0.75, steep) * (1 - up) * 0.45)
    out = g.copy()
    lc = fbm(Pp, 4.2, 3, seed=7)
    patch = ss(0.60, 0.72, lc) * 0.65 * (0.35 + 0.65 * (1 - down))
    out = mixc(out, RP.LICHEN, patch * 0.42)
    out = mixc(out, RP.LICHEN_O, ss(0.80, 0.86, fbm(Pp, 8.0, 2, seed=9)) * ss(0.2, 0.6, up) * 0.5)
    m_top = ss(0.45, 0.80, up) * ss(0.44, 0.62, fbm(Pp, 2.0, 3, seed=10))
    m_foot = ss(0.40, 0.02, z) * ss(0.38, 0.60, fbm(Pp, 3.6, 2, seed=11))
    moss = np.clip((m_top + m_foot + ss(0.58, 0.32, ao) * 0.5) * 0.7, 0, 1)
    mv = fbm(Pp, 14.0, 2, seed=13)
    mcol = np.where((mv > 0.62)[:, None], RP.MOSS_L, np.where((mv < 0.40)[:, None], RP.MOSS_D, RP.MOSS))
    out = mixc(out, mcol, ss(0.25, 0.60, moss))
    ndl = ss(0.74, 0.94, up) * ss(0.48, 0.68, fbm(Pp, 6.0, 2, seed=14)) * 0.75
    pick = fbm(Pp, 40.0, 1, seed=15)
    ncol = np.where((pick > 0.58)[:, None], RP.NEEDLE_A, np.where((pick > 0.36)[:, None], RP.NEEDLE_B, RP.NEEDLE_C))
    out = mixc(out, ncol, ss(0.30, 0.65, ndl))
    out = mixc(out, RP.SOIL, ss(0.20, 0.0, z) * (0.55 + 0.35 * fbm(Pp, 7.0, 2, seed=16)))
    out = out * (0.93 + 0.12 * up - 0.12 * down)[:, None]
    m = M(WK.Z_ROCK)
    col[m] = out[m]
    # inside: the same stone darker and damp, water streaks, soot over the candle stone, a little moss toward the mouth
    inn = g * 0.72
    inn = mixc(inn, lin(48, 50, 46), ss(0.58, 0.72, fbm(Pp, 3.0, 2, seed=4502, stretch=(1, 1, 0.15))) * 0.55)
    soot = np.exp(-(((x + 0.70) / 0.9) ** 2 + ((y - 5.10) / 0.8) ** 2)) * ss(0.6, 1.6, z)
    inn = mixc(inn, lin(22, 20, 18), soot * 0.85)
    mouth = ss(1.2, -0.6, y)
    inn = mixc(inn, mcol, mouth * ss(0.55, 0.75, fbm(Pp, 5.0, 2, seed=4503)) * 0.6)
    inn = inn * (0.95 + 0.08 * up - 0.10 * down)[:, None]
    m = M(WK.Z_ROCKIN)
    col[m] = inn[m]
    # the floor: packed earth, needles blown in toward the mouth, stones, the sawdust by the saw, trodden paths
    fl = T(lin(80, 66, 50), 0.18, 0.2)
    fl = mixc(fl, lin(56, 46, 36), ss(0.5, 0.75, fbm(Pp, 6.0, 2, seed=4504)) * 0.6)
    lit, lit_c = _litter(Pp, up, 4505, 1.0)
    fl = mixc(fl, lit_c, lit * (0.3 + 0.7 * mouth))
    stones = ss(0.80, 0.86, fbm(Pp, 25.0, 1, seed=4506))
    fl = mixc(fl, lin(110, 106, 98), stones * 0.8)
    dust = np.exp(-(((x - 0.55) / 0.35) ** 2 + ((y - 1.40) / 0.30) ** 2))
    fl = mixc(fl, lin(206, 176, 126), ss(0.2, 0.6, dust) * ss(0.3, 0.6, fbm(Pp, 30.0, 1, seed=4507)))
    path = np.exp(-((x - 0.15 * np.sin(y)) / 0.45) ** 2) * (y < 3.0)
    fl = mixc(fl, lin(66, 56, 44), path * 0.4)
    m = M(WK.Z_CFLOOR)
    col[m] = fl[m]
    m = M(WK.Z_ROCKD)
    col[m] = RP.SOIL_D
    # the dressing
    m = M(WK.Z_BOUGH)
    c = T(lin(52, 70, 40), 0.15, 0.3)
    c = mixc(c, lin(120, 86, 46), ss(0.55, 0.75, fbm(Pp, 12.0, 2, seed=4508)) * 0.7)
    c = c * (0.8 + 0.3 * np.mod(np.floor(x / 0.02) + np.floor(y / 0.02), 2))[:, None]
    col[m] = c[m]
    m = M(WK.Z_BLANKET)
    c = T(lin(88, 92, 72), 0.12, 0.16)
    stripe = (dist_periodic(x * 0.7 + y * 0.7, 0.9) < 0.04)
    c = np.where(stripe[:, None], c * 0.75, c)
    c = mixc(c, lin(60, 56, 46), ss(0.55, 0.80, fbm(Pp, 8.0, 2, seed=4509)) * 0.5)
    c = mixc(c, lin(130, 124, 104), ss(0.80, 0.90, fbm(Pp, 40.0, 1, seed=4510)) * 0.4)
    col[m] = c[m]
    for zz, base in ((WK.Z_CANDLE, lin(226, 216, 190)), (WK.Z_WAX, lin(214, 202, 168))):
        m = M(zz)
        c = T(base, 0.06, 0.08)
        c = mixc(c, lin(40, 34, 28), ss(0.7, 0.9, fbm(Pp, 50.0, 1, seed=4511)) * 0.3)
        col[m] = c[m]
    m = M(WK.Z_SAWB)
    c = T(lin(150, 150, 148), 0.1, 0.2)
    c = mixc(c, RUST, ss(0.5, 0.75, fbm(Pp, 40.0, 2, seed=4512)) * 0.5)
    col[m] = c[m]
    m = M(WK.Z_SAWF)
    c = T(lin(200, 90, 30), 0.1, 0.12)
    c = mixc(c, lin(60, 60, 60), ss(0.80, 0.92, fbm(Pp, 50.0, 2, seed=4513)) * 0.7)
    col[m] = c[m]
    m = M(WK.Z_SAWDUST)
    c = T(lin(214, 184, 132), 0.12, 0.25)
    col[m] = c[m]
    m = M(WK.Z_BOOT)
    c = T(lin(62, 44, 30), 0.15, 0.2)
    c = mixc(c, lin(120, 106, 88), ss(0.6, 0.85, fbm(Pp, 20.0, 2, seed=4514)) * 0.4 + edge * 0.3)
    col[m] = c[m]
    m = M(WK.Z_SOLE)
    lug = (dist_periodic(x + y, 0.03) < 0.008) | (dist_periodic(x - y, 0.03) < 0.008)
    c = np.where(lug[:, None], lin(14, 14, 14), lin(40, 38, 36))
    c = mixc(c, MUD, ss(0.6, 0.8, fbm(Pp, 30.0, 2, seed=4515)) * 0.4)
    col[m] = c[m]
    m = M(WK.Z_TIN)
    band = hash1(np.floor(x * 7.0) + np.floor(y * 7.0) * 3.0, 4516)
    lab = np.where((band > 0.66)[:, None], lin(160, 40, 30), np.where((band > 0.33)[:, None], lin(40, 90, 50), lin(200, 180, 60)))
    c = np.where((np.abs(np.mod(z, 0.11) - 0.055) < 0.035)[:, None], lab, lin(160, 160, 156))
    c = mixc(c, RUST, ss(0.55, 0.8, fbm(Pp, 30.0, 2, seed=4517)) * 0.6)
    col[m] = c[m]
    m = M(WK.Z_NAIL)
    col[m] = T(lin(50, 48, 46), 0.1, 0.1)[m]
    m = M(WK.Z_RAG)
    c = T(lin(110, 100, 86), 0.15, 0.2)
    c = mixc(c, lin(50, 44, 38), ss(0.55, 0.8, fbm(Pp, 10.0, 2, seed=4518)) * 0.5)
    col[m] = c[m]
    m = M(WK.Z_BUCKET)
    c = T(lin(150, 154, 152), 0.1, 0.18)
    c = mixc(c, lin(180, 182, 176), ss(0.7, 0.85, fbm(Pp, 60.0, 1, seed=4519)) * 0.4)
    c = mixc(c, RUST, ss(0.65, 0.85, fbm(Pp, 20.0, 2, seed=4520)) * 0.5)
    col[m] = c[m]
    m = M(WK.Z_WIRE)
    col[m] = T(lin(140, 90, 50), 0.1, 0.2)[m]
    m = M(WK.Z_STONE)
    c = g * 0.85
    c = mixc(c, lin(214, 202, 168), ss(0.62, 0.72, fbm(Pp, 30.0, 2, seed=4521)) * up * 0.7)      # wax drips
    col[m] = c[m]
    m = M(WK.Z_BOTTLE)
    col[m] = T(lin(70, 46, 22), 0.1, 0.2)[m]
    return col, None
