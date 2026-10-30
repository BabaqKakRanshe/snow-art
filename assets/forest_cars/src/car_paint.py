"""Painter of the forest's abandoned cars (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n]) for the car being
built (car_kit.S / NAME). The start car's wear language (start_paint) and ShiftCar 2.2's finish:
  StartCar  oxblood dulled to a chalky pink-brown on the tops, rust at the arches and sills, mud from below, a mat of needles and
            leaves on the roof, hood and the scuttle, moss on the roof; beige fabric with mould inside
  WreckCar  faded blue rusted through (big rust fields low and on the edges, bubbles everywhere), dull chrome going brown, an even
            crust of snow on the roof, hood and boot; grey-blue fabric inside
Both: road tyres, grey steel wheels with holes and rusty nuts, ribbed lamp glass, amber indicators in front, red over amber
behind, the grille's bars, a blank plate, black plastics faded grey, the dash cracked, carpet with dirt, a stained headliner."""
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, hash1
from gen_paint import DUST, RUST, RUST_D, _T, _common
import gen_kit as K
import start_kit as SK
import car_kit as C

MUD, MUD_D, MOSS = lin(92, 78, 60), lin(58, 48, 38), lin(70, 86, 40)
NEEDLE_A, NEEDLE_B, LEAF, SNOW = lin(132, 92, 46), lin(96, 70, 40), lin(150, 96, 44), lin(206, 210, 214)
PAL = {'StartCar': dict(base=lin(88, 26, 24), fade=lin(120, 68, 62), chalk=lin(140, 104, 96), rust=0.9, litter=1.0, snow=0.9,
                        seat=lin(124, 100, 72), mould=0.6),
       'WreckCar': dict(base=lin(40, 52, 86), fade=lin(70, 84, 110), chalk=lin(110, 118, 136), rust=1.6, litter=0.2, snow=1.0,
                        seat=lin(78, 84, 96), mould=0.3)}

DRAFT_COL = {
    SK.Z_PAINT: (112, 34, 30), SK.Z_CBLACK: (34, 34, 36), SK.Z_UNDER: (36, 32, 28), SK.Z_TYRE: (30, 30, 30), SK.Z_RIM: (120, 120, 116),
    SK.Z_CHROME: (170, 170, 168), SK.Z_HEAD: (200, 204, 196), SK.Z_TAIL: (190, 110, 30), SK.Z_GRILLE: (24, 24, 26),
    SK.Z_PLATE: (196, 192, 176), SK.Z_RUBBER: (22, 22, 22), K.Z_STEELBLK: (60, 58, 54), SK.Z_SEAT: (124, 100, 72),
    SK.Z_DASH: (40, 40, 42), SK.Z_CARPET: (60, 48, 38), SK.Z_LINER: (176, 166, 140), SK.Z_CARD: (96, 86, 72), SK.Z_GAUGE: (20, 20, 20)}


def paint_car(Pp, Nn, Z, ao, aa):
    S, P = C.S, PAL[C.NAME]
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 3101)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    side = np.abs(x) > S.CW - 0.04
    streak = ss(0.55, 0.80, fbm(Pp * np.array([1, 1, 0.10], np.float32), 7.0, 3, seed=3111))
    topside = ss(0.55, 0.9, up) * (z > S.Z_BELT - 0.08)
    pick = hash1(np.floor(x * 53.0) + np.floor(y * 47.0) * 13.0, 3112)
    lit_c = np.where((pick > 0.70)[:, None], LEAF, np.where((pick > 0.35)[:, None], NEEDLE_A, NEEDLE_B))
    lit = np.clip(ss(0.52, 0.74, fbm(Pp, 5.0, 3, seed=3113)) * 0.8 + ss(0.66, 0.84, fbm(Pp, 30.0, 1, seed=3114)) * 0.5, 0, 1) * topside
    cowl = np.exp(-(((y - S.Y_WS - 0.02) / 0.12) ** 2)) * (z > S.Z_BELT - 0.06)
    lit = np.clip((lit + cowl * 0.8) * P['litter'], 0, 0.95)
    # 1.2 (user: «не видно, что она заснеженная»): a white crust on every face that looks up - roof, hood, boot, bumpers, sills,
    # arch lips - thick on the tops, thinner low down; soft drifts, the paint shows only at the edges
    drift = 0.75 + 0.25 * ss(0.30, 0.60, fbm(Pp, 2.0, 2, seed=3115))
    snow = ss(0.55, 0.85, up) * drift * np.where(z > S.Z_BELT - 0.08, 1.0, 0.75) * (z > 0.26) * P['snow']
    cuts = np.array([S.FRONT, S.Y_WS + 0.04, S.PILLARS['B'][0] + 0.04, S.PILLARS['C'][0] + 0.04, S.REAR + 1])
    pid = np.searchsorted(cuts, y) + 7 * (x > 0)
    tint = (hash1(pid.astype(np.float32), 3116) - 0.5) * 0.10

    # ---- paint
    m = M(SK.Z_PAINT)
    c = P['base'] * (0.88 + 0.16 * (n_lo - 0.5) + 0.08 * (n_hi - 0.5) + tint)[:, None]
    c = mixc(c, P['fade'], ss(0.15, 0.85, up) * (0.55 + 0.35 * n_lo))
    c = mixc(c, P['chalk'], ss(0.6, 0.95, up) * ss(0.35, 0.75, fbm(Pp, 1.2, 2, seed=3120)) * 0.35)   # broad, no blotches
    arch = np.zeros(n, np.float32)
    for yc in (S.YFA, S.YRA):
        d = np.hypot(y - yc, z - S.RW)
        arch = np.maximum(arch, ss(S.RA + 0.12, S.RA + 0.01, d) * side)
    sill = ss(0.40, 0.28, z) * side
    tail = ss(0.70, 0.40, z) * (y > S.REAR - 0.03)
    rust_mask = np.clip((arch + sill + tail * 0.8 + edge * 0.4) * P['rust'], 0, 1) * ss(0.36, 0.66, fbm(Pp, 22.0, 3, seed=3121))
    bubbles = ss(0.84 - 0.06 * P['rust'], 0.93, fbm(Pp, 55.0, 2, seed=3122)) * (0.3 + 0.7 * ss(0.9, 0.4, z))
    fields = ss(0.62, 0.80, fbm(Pp, 6.0, 3, seed=3123)) * max(P['rust'] - 1.0, 0.0) * (1 - topside * 0.5)
    c = mixc(c, RUST, np.clip(rust_mask * 1.2 + bubbles * 0.5 + fields, 0, 1))
    c = mixc(c, RUST_D, np.clip(rust_mask - 0.55 + fields * 0.4, 0, 1) * 1.5)
    c = mixc(c, MUD, ss(0.60, 0.30, z) * (0.5 + 0.5 * ss(0.3, 0.7, fbm(Pp, 8.0, 2, seed=3124))) * 0.85)
    c = mixc(c, MUD_D, ss(0.40, 0.28, z) * 0.6)
    c = mixc(c, lin(66, 58, 50), streak * 0.30 * (1 - up))
    c = mixc(c, lin(40, 34, 30), cav * 0.4)
    c = mixc(c, MOSS, ss(0.70, 0.86, fbm(Pp, 10.0, 2, seed=3125)) * topside * (z > S.ZR - 0.05) * 0.6 * P['litter'])
    c = mixc(c, lit_c, lit)
    c = mixc(c, SNOW, np.clip(snow, 0, 0.95))
    col[m] = c[m]
    seams = np.zeros(n, np.float32)
    for yy in (S.Y_WS + 0.04, S.PILLARS['B'][0] + 0.04, S.PILLARS['C'][0] + 0.04):
        seams = np.maximum(seams, gline(np.abs(y - yy), 0.004, aa) * side * (z > S.Z_SILL + 0.02) * (z < S.Z_BELT))
    hood = (Nn[:, 2] > 0.7) & (y < S.Y_WS) & (y > S.FRONT + S.CC)
    seams = np.maximum(seams, gline(np.abs(np.abs(x) - (S.CW - 0.07)), 0.004, aa) * hood)
    seams = np.maximum(seams, gline(np.abs(y - (S.Y_WS - 0.02)), 0.004, aa) * (Nn[:, 2] > 0.7) * (np.abs(x) < S.CW - 0.07))
    gr = np.where(m, seams * 0.9, gr)
    # ---- black plastics, rubbers, chrome
    for zz, b in ((SK.Z_CBLACK, lin(34, 34, 36)), (SK.Z_RUBBER, lin(22, 22, 22))):
        m = M(zz)
        c = T(b, 0.12, 0.16)
        c = mixc(c, lin(92, 90, 86), up * ss(0.4, 0.8, n_lo) * 0.45)
        c = mixc(c, MUD, ss(0.55, 0.30, z) * 0.6)
        c = mixc(c, lit_c, lit * 0.6)
        c = mixc(c, SNOW, np.clip(snow * 0.8, 0, 0.85))
        col[m] = c[m]
    m = M(SK.Z_CHROME)
    c = T(lin(160, 160, 156), 0.10, 0.2)
    c = mixc(c, RUST, (ss(0.45, 0.75, fbm(Pp, 30.0, 2, seed=3130)) * 0.7 + cav * 0.3) * min(P['rust'], 1.3))
    c = mixc(c, MUD, ss(0.50, 0.30, z) * 0.4)
    c = mixc(c, SNOW, np.clip(snow, 0, 0.85))
    col[m] = c[m]
    m = M(SK.Z_UNDER)
    c = T(lin(40, 36, 30), 0.15, 0.2)
    c = mixc(c, RUST_D, ss(0.55, 0.85, fbm(Pp, 12.0, 2, seed=3131)) * 0.7)
    c = mixc(c, MUD_D, ss(0.60, 0.30, z) * 0.5)
    col[m] = c[m]
    m = M(K.Z_STEELBLK)
    c = T(lin(62, 60, 56), 0.12, 0.18)
    c = mixc(c, RUST, ss(0.4, 0.7, fbm(Pp, 18.0, 2, seed=3132)) * 0.7)
    col[m] = c[m]
    # ---- wheels (the brake drum of the missing wheel is a rim zone too: all rust)
    yc = np.where(y < 0, S.YFA, S.YRA)
    ang = np.arctan2(z - S.RW, y - yc)
    rad = np.hypot(z - S.RW, y - yc)
    m = M(SK.Z_TYRE)
    block = np.mod(np.floor(ang * 14 / np.pi), 2)
    c = T(lin(32, 32, 32), 0.12, 0.18) * (0.86 + 0.14 * block)[:, None]
    c = mixc(c, MUD, ss(0.22, 0.02, z) * 0.85 + ss(0.6, 0.8, fbm(Pp, 20.0, 2, seed=3133)) * 0.3)
    col[m] = c[m]
    m = M(SK.Z_RIM)
    c = T(lin(116, 116, 112), 0.10, 0.14)
    holes = (rad > 0.085) & (rad < 0.13) & (np.abs(np.mod(ang * 4 / (2 * np.pi), 1.0) - 0.5) < 0.15)
    nuts = (rad > 0.04) & (rad < 0.065) & (np.abs(np.mod(ang * 4 / (2 * np.pi) + 0.5, 1.0) - 0.5) < 0.12)
    c = np.where(holes[:, None], lin(14, 14, 14), c)
    c = np.where(nuts[:, None], RUST, c)
    c = mixc(c, RUST, ss(0.50, 0.80, fbm(Pp, 30.0, 2, seed=3134)) * 0.6 * P['rust'] + cav * 0.3)
    drum = (np.abs(np.abs(x) - S.TRK) < 0.10) & (rad < 0.14) & (np.abs(y - S.YFA) < 0.15) & (x < 0) & (C.NAME == 'WreckCar')
    c = np.where(drum[:, None], RUST_D * 0.9, c)
    col[m] = c[m]
    # ---- lamps, grille, plate
    m = M(SK.Z_HEAD)
    rib = 0.86 + 0.14 * np.mod(np.floor(x / 0.014), 2)
    c = lin(196, 198, 188) * rib[:, None] * (0.75 + 0.25 * n_hi)[:, None]
    c = mixc(c, MUD, 0.25 + ss(0.6, 0.8, n_mid) * 0.35)
    c = mixc(c, RUST, ss(0.6, 0.8, fbm(Pp, 25.0, 2, seed=3135)) * 0.3 * (P['rust'] > 1))
    col[m] = c[m]
    m = M(SK.Z_TAIL)
    back = np.where((z > 0.66)[:, None], lin(156, 30, 24), np.where((z > 0.58)[:, None], lin(196, 120, 30), lin(176, 172, 160)))
    c = np.where((y < 0)[:, None], lin(200, 120, 30), back)
    c = c * (0.80 + 0.2 * (np.mod(np.floor(z / 0.01), 2)))[:, None]
    c = mixc(c, MUD, 0.30 + ss(0.6, 0.85, n_mid) * 0.3)
    col[m] = c[m]
    m = M(SK.Z_GRILLE)
    bars = np.mod(np.floor((z - 0.48) / 0.03), 2)
    c = np.where((bars > 0)[:, None], lin(40, 40, 42), lin(10, 10, 12)) * (0.9 + 0.1 * n_hi)[:, None]
    c = mixc(c, RUST, ss(0.5, 0.8, fbm(Pp, 30.0, 2, seed=3136)) * 0.4 * (P['rust'] > 1))
    col[m] = c[m]
    gr = np.where(m & (y < S.FRONT + 0.01), gline(dist_periodic(z - 0.48, 0.03), 0.003, aa) * 0.6, gr)
    m = M(SK.Z_PLATE)
    c = T(lin(196, 192, 176), 0.08, 0.08)
    c = mixc(c, lin(40, 40, 40), (1 - ss(0.0, 0.012, np.minimum(np.abs(np.abs(x) - 0.20), np.abs(np.abs(z - 0.62) - 0.05)))) * 0.8)
    c = mixc(c, MUD, 0.35 + ss(0.6, 0.8, n_mid) * 0.3)
    col[m] = c[m]
    # ---- inside
    m = M(SK.Z_SEAT)
    weave = 0.9 + 0.1 * np.mod(np.floor(x / 0.006) + np.floor(z / 0.006), 2)
    c = T(P['seat'], 0.12, 0.14) * weave[:, None]
    c = mixc(c, lin(70, 74, 56), ss(0.62, 0.82, fbm(Pp, 9.0, 3, seed=3140)) * P['mould'])
    c = mixc(c, lin(160, 150, 120), ss(0.75, 0.9, fbm(Pp, 20.0, 2, seed=3141)) * 0.3)
    col[m] = c[m]
    m = M(SK.Z_DASH)
    c = T(lin(42, 42, 44), 0.12, 0.16)
    crack = gline(np.abs(fbm(Pp, 6.0, 2, seed=3142) - 0.5), 0.004, aa) * up
    c = mixc(c, lin(90, 88, 84), up * 0.30 + crack * 0.6)
    c = mixc(c, DUST, up * 0.25)
    col[m] = c[m]
    m = M(SK.Z_GAUGE)
    col[m] = lin(18, 18, 18)
    m = M(SK.Z_CARPET)
    c = T(lin(56, 46, 38), 0.14, 0.2)
    c = mixc(c, lit_c, ss(0.62, 0.82, fbm(Pp, 10.0, 2, seed=3143)) * up * 0.6 * P['litter'])
    c = mixc(c, MUD_D, ss(0.6, 0.8, n_mid) * 0.4)
    col[m] = c[m]
    m = M(SK.Z_LINER)
    c = T(lin(170, 162, 138), 0.10, 0.12)
    c = mixc(c, lin(120, 108, 86), ss(0.55, 0.80, fbm(Pp, 4.0, 3, seed=3144)) * 0.6)
    col[m] = c[m]
    m = M(SK.Z_CARD)
    c = T(lin(92, 84, 72) if C.NAME == 'StartCar' else lin(70, 74, 84), 0.12, 0.14)
    c = mixc(c, lin(60, 56, 48), ss(0.6, 0.85, fbm(Pp, 12.0, 2, seed=3145)) * 0.5)
    col[m] = c[m]
    return col, gr
