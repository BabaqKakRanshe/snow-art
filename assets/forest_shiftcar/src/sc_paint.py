"""Painter of the previous shift's car 2.0 (ShiftCar atlas, psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n]).
After the references B and C: faded olive-green paint over a beige lower band (the band's edge under the black side trim), each
panel a shade apart, grime in the seams and run-down streaks, rust at the arches, sills and the tailgate's foot, mud from below,
a crust of snow on the roof, the hood line and the basket; off-road tyres with blocks, grey steel wheels with their holes and
rusty nuts; rectangular headlamps behind dirty glass, amber indicators in front, red over amber at the back; the engine bay
oily and dark. Positions: the car at the origin (sc_kit.DISPLAY)."""
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, hash1
from gen_paint import DUST, RUST, RUST_D, _T, _common
import gen_kit as K
import start_kit as SK
import sc_kit as C

GREEN, GREEN_FADE = lin(54, 64, 44), lin(84, 92, 70)
BEIGE, BEIGE_D = lin(132, 122, 96), lin(100, 90, 70)
MUD, MUD_D, SNOW = lin(92, 78, 60), lin(58, 48, 38), lin(206, 210, 214)
OIL = lin(22, 20, 18)

DRAFT_COL = {
    SK.Z_PAINT: (72, 86, 60), SK.Z_CBLACK: (34, 34, 36), SK.Z_UNDER: (36, 32, 28), SK.Z_TYRE: (30, 30, 30), SK.Z_RIM: (120, 120, 116),
    SK.Z_CHROME: (170, 170, 168), SK.Z_HEAD: (200, 204, 196), SK.Z_TAIL: (190, 110, 30), SK.Z_GRILLE: (24, 24, 26),
    SK.Z_PLATE: (196, 192, 176), SK.Z_RUBBER: (22, 22, 22), K.Z_STEELBLK: (60, 58, 54)}


def paint_car(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 2801)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    side = np.abs(x) > C.CW - 0.03
    bay = (np.abs(x) < C.FENDER_IN + 0.01) & (y < C.HOOD_Y1 + 0.01) & (z < C.ZH1 - 0.005)
    snow = ss(0.80, 0.97, up) * ss(0.30, 0.55, fbm(Pp, 1.6, 2, seed=2870)) * 0.8 * ((z > 1.5) | (np.abs(y - C.Y_WS + 0.03) < 0.10))  # a thin even crust, no blotches
    streak = ss(0.55, 0.80, fbm(Pp * np.array([1, 1, 0.10], np.float32), 7.0, 3, seed=2811))
    # every panel a shade apart (door, fender, tailgate)
    cuts = np.array([C.FRONT, C.Y_WS + 0.04, C.PILLARS['B'][0] + 0.05, C.PILLARS['C'][0] + 0.05, 1.70, C.REAR + 1])
    pid = np.searchsorted(cuts, y) + 7 * (x > 0)
    tint = (hash1(pid.astype(np.float32), 2815) - 0.5) * 0.10

    # ---- paint: green above the band, beige below; fade on the tops, rust low, mud, streaks, snow
    m = M(SK.Z_PAINT)
    low = z < C.Z_BAND
    base = np.where(low[:, None], BEIGE, GREEN)
    c = base * (0.90 + 0.14 * (n_lo - 0.5) + 0.06 * (n_hi - 0.5) + tint)[:, None]
    c = mixc(c, np.where(low[:, None], lin(176, 168, 140), GREEN_FADE), ss(0.15, 0.85, up) * (0.45 + 0.35 * n_lo))
    arch = np.zeros(n, np.float32)
    for yc in (C.YFA, C.YRA):
        d = np.hypot(y - yc, z - C.RW)
        arch = np.maximum(arch, ss(C.RA + 0.12, C.RA + 0.01, d) * side)
    sill = ss(0.56, 0.46, z) * side
    tail = ss(0.80, 0.50, z) * (y > C.REAR - 0.03)
    rust_mask = np.clip(arch + sill + tail * 0.8 + edge * 0.35, 0, 1) * ss(0.38, 0.68, fbm(Pp, 22.0, 3, seed=2841))
    bubbles = ss(0.84, 0.93, fbm(Pp, 55.0, 2, seed=2842)) * ss(1.0, 0.5, z)
    c = mixc(c, RUST, np.clip(rust_mask * 1.1 + bubbles * 0.4, 0, 1))
    c = mixc(c, RUST_D, np.clip(rust_mask - 0.60, 0, 1) * 1.4)
    c = mixc(c, MUD, ss(0.78, 0.45, z) * (0.45 + 0.55 * ss(0.3, 0.7, fbm(Pp, 8.0, 2, seed=2843))) * 0.85)
    c = mixc(c, MUD_D, ss(0.54, 0.44, z) * 0.6)
    c = mixc(c, MUD, (y > C.REAR - 0.02) * ss(1.1, 0.6, z) * 0.5)
    c = mixc(c, lin(52, 56, 44), streak * 0.35 * (1 - up) * (z > C.Z_BAND))
    c = mixc(c, lin(40, 40, 34), cav * 0.5)
    c = mixc(c, SNOW, np.clip(snow, 0, 0.92))
    col[m] = c[m]
    # seams: the doors, the tailgate, the fuel flap, the band's edge (a dark line under the trim)
    seams = np.zeros(n, np.float32)
    for yy in (C.Y_WS + 0.04, C.PILLARS['B'][0] + 0.05, C.PILLARS['C'][0] + 0.05):
        seams = np.maximum(seams, gline(np.abs(y - yy), 0.004, aa) * side * (z > C.Z_SILL + 0.02) * (z < C.Z_BELT))
    seams = np.maximum(seams, gline(np.abs(np.abs(x) - 0.70), 0.004, aa) * (y > C.REAR - 0.01) * (z > 0.50))
    seams = np.maximum(seams, gline(np.abs(z - (C.Z_BAND - 0.045)), 0.003, aa) * side)
    fuel = (np.abs(y - 1.52) < 0.08) & (np.abs(z - 0.88) < 0.07) & (x < -C.CW + 0.02)
    seams = np.maximum(seams, gline(np.minimum(np.abs(np.abs(y - 1.52) - 0.08), np.abs(np.abs(z - 0.88) - 0.07)), 0.003, aa) * fuel)
    gr = np.where(m, seams * 0.9, gr)
    # ---- black plastics (flares, trim, bumpers, basket, ladder, mirrors), the rubbers
    for zz, b in ((SK.Z_CBLACK, lin(34, 34, 36)), (SK.Z_RUBBER, lin(22, 22, 22))):
        m = M(zz)
        c = T(b, 0.12, 0.16)
        c = mixc(c, lin(88, 86, 82), up * ss(0.4, 0.8, n_lo) * 0.4)
        c = mixc(c, RUST, (z > C.Z_ROOF) * ss(0.5, 0.8, fbm(Pp, 30.0, 2, seed=2850)) * 0.5)
        c = mixc(c, MUD, ss(0.70, 0.35, z) * 0.6)
        c = mixc(c, SNOW, np.clip(snow * 0.8, 0, 0.85))
        col[m] = c[m]
    m = M(SK.Z_UNDER)
    c = T(lin(40, 36, 30), 0.15, 0.2)
    c = mixc(c, RUST_D, ss(0.6, 0.85, fbm(Pp, 12.0, 2, seed=2851)) * 0.6)
    c = mixc(c, MUD_D, ss(0.75, 0.40, z) * 0.5)
    c = mixc(c, OIL, bay * ss(0.4, 0.7, fbm(Pp, 9.0, 2, seed=2852)) * 0.6)
    c = np.where(((z > 0.5) & ~bay & (np.abs(x) < C.WR))[:, None], lin(10, 10, 10), c)      # the shell behind the glass
    col[m] = c[m]
    m = M(K.Z_STEELBLK)
    c = T(lin(62, 60, 56), 0.12, 0.18)
    c = mixc(c, RUST, ss(0.5, 0.8, fbm(Pp, 18.0, 2, seed=2853)) * 0.55 + cav * 0.3)
    c = mixc(c, OIL, ss(0.85, 0.65, z) * 0.6)
    col[m] = c[m]
    # ---- wheels: off-road tread blocks, grey steel wheels with five holes and rusty nuts
    yc = np.where(y < 0, C.YFA, C.YRA)
    ang = np.arctan2(z - C.RW, y - yc)
    rad = np.hypot(z - C.RW, y - yc)
    m = M(SK.Z_TYRE)
    block = np.mod(np.floor(ang * 16 / np.pi) + np.floor(np.abs(np.abs(x) - C.TRK) / 0.045), 2)
    c = T(lin(30, 30, 30), 0.12, 0.18) * (0.78 + 0.22 * block)[:, None]
    c = mixc(c, MUD, ss(0.28, 0.02, z) * 0.85 + ss(0.6, 0.8, fbm(Pp, 20.0, 2, seed=2854)) * 0.35)
    col[m] = c[m]
    m = M(SK.Z_RIM)
    c = T(lin(118, 118, 114), 0.10, 0.14)
    holes = (rad > 0.11) & (rad < 0.17) & (np.abs(np.mod(ang * 5 / (2 * np.pi), 1.0) - 0.5) < 0.16)
    nuts = (rad > 0.055) & (rad < 0.085) & (np.abs(np.mod(ang * 5 / (2 * np.pi) + 0.5, 1.0) - 0.5) < 0.12)
    c = np.where(holes[:, None], lin(14, 14, 14), c)
    c = np.where(nuts[:, None], RUST, c)
    c = mixc(c, RUST, ss(0.55, 0.80, fbm(Pp, 30.0, 2, seed=2855)) * 0.5 + cav * 0.3)
    c = mixc(c, MUD, ss(0.40, 0.10, z) * 0.6)
    col[m] = c[m]
    m = M(SK.Z_CHROME)
    c = T(lin(160, 160, 158), 0.10, 0.2)
    c = mixc(c, RUST, ss(0.5, 0.8, fbm(Pp, 40.0, 2, seed=2856)) * 0.6)
    col[m] = c[m]
    # ---- lamps: rectangular headlamps (ribbed dirty glass), amber indicators in front, red over amber behind, the grille
    m = M(SK.Z_HEAD)
    rib = 0.86 + 0.14 * np.mod(np.floor(x / 0.016), 2)
    c = lin(196, 198, 188) * rib[:, None] * (0.75 + 0.25 * n_hi)[:, None]
    c = mixc(c, MUD, 0.25 + ss(0.6, 0.8, n_mid) * 0.3)
    col[m] = c[m]
    m = M(SK.Z_TAIL)
    back = np.where((z > 0.86)[:, None], lin(156, 30, 24), np.where((z > 0.76)[:, None], lin(196, 120, 30), lin(176, 172, 160)))
    c = np.where((y < 0)[:, None], lin(200, 120, 30), back)
    c = np.where((bay & (z > C.BATT_Z))[:, None], lin(150, 30, 24), c)                               # the red battery lead
    c = c * (0.80 + 0.2 * (np.mod(np.floor(z / 0.01), 2)))[:, None]
    c = mixc(c, MUD, 0.30 + ss(0.6, 0.85, n_mid) * 0.3)
    col[m] = c[m]
    m = M(SK.Z_GRILLE)
    bars = np.mod(np.floor((z - 0.62) / 0.04), 2)
    c = np.where((bars > 0)[:, None], lin(40, 40, 42), lin(10, 10, 12)) * (0.9 + 0.1 * n_hi)[:, None]
    col[m] = c[m]
    gr = np.where(m & (y < C.FRONT + 0.01), gline(dist_periodic(z - 0.62, 0.04), 0.003, aa) * 0.6, gr)
    m = M(SK.Z_PLATE)
    c = T(lin(196, 192, 176), 0.08, 0.08)
    c = mixc(c, lin(40, 40, 40), (1 - ss(0.0, 0.012, np.minimum(np.abs(np.abs(x) - 0.22), np.abs(np.abs(z - 0.73) - 0.06)))) * 0.8)
    c = mixc(c, MUD, 0.3 + ss(0.6, 0.8, n_mid) * 0.3)
    col[m] = c[m]
    return col, gr
