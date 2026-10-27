"""Painters for the forest_devices atlases (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
Devices (the desk things: the fax, the computer, the laptop, the tapes, the tape recorder; 512 px at 256 px/m) and Outdoor
(the helipad's drop box, the weather station's screen; 512 px at 128 px/m). Office kit after years in a cold, dusty station: beige ABS gone ivory-yellow, grimy where hands
go, dust on the tops, a smoked-grey paper tray, a zinc-plated back panel; the laptop's charcoal plastic shiny at the palm
rest; a black cassette shell with its head openings; kraft cardboard and brown packing tape. The drop box in the station's
grey-green (the deck girders' paint), chipped to red primer and rust at the edges, runs under the roof and the slot, a
galvanised post with white rust and splash, a concrete footing. The screen in the weather station's white paint (as forest_far
paints it), greyer and flaking where the weather hits, dirt and moss up the legs; inside clean: a white frame, a black
recorder. Positions: the roots stand at devices_kit.DISPLAY."""
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, hash1
from gen_paint import RUST, RUST_D, _T, _common, run_m
import devices_kit as DK

BEIGE, BEIGE_Y, BEIGE_L, BEIGE_D = lin(196, 186, 160), lin(204, 186, 138), lin(214, 206, 184), lin(150, 142, 120)
HAND, GRIME_P, DUST_L = lin(118, 106, 84), lin(104, 96, 78), lin(172, 166, 152)
GREEN, GREEN_FADE, PRIMER, MUD = lin(88, 104, 92), lin(124, 136, 124), lin(128, 70, 44), lin(92, 78, 60)
MOSS = lin(70, 86, 40)

DRAFT_COL = {   # sRGB, roughly the painters' base colours (devices_build --draft)
    DK.Z_BEIGE: (196, 186, 160), DK.Z_BEIGE_D: (150, 142, 120), DK.Z_RUBBER: (30, 30, 30), DK.Z_SLOT: (14, 14, 14),
    DK.Z_CORD: (32, 32, 32), DK.Z_TRAY: (86, 88, 88), DK.Z_CASS: (36, 36, 38), DK.Z_CARDB: (170, 132, 88),
    DK.Z_TAPE: (156, 112, 58), DK.Z_GREEN: (88, 104, 92), DK.Z_GALV: (150, 154, 152), DK.Z_CONC: (134, 132, 126),
    DK.Z_STEEL: (104, 108, 108), DK.Z_METAL: (176, 178, 176), DK.Z_LAP: (58, 58, 60), DK.Z_LAP_D: (38, 38, 40),
    DK.Z_BTN_G: (64, 132, 74), DK.Z_BTN_R: (164, 52, 40), DK.Z_COIL: (180, 170, 146), DK.Z_LOCK: (172, 172, 168),
    DK.Z_MOUSE: (196, 186, 160), DK.Z_DECK: (62, 66, 70), DK.Z_SCRWHITE: (232, 232, 226), DK.Z_SCRLEG: (226, 226, 220),
    DK.Z_SCRWOOD: (150, 136, 112), DK.Z_SCRSTEEL: (110, 112, 112), DK.Z_SCRMETAL: (190, 192, 196), DK.Z_SCRBLACK: (30, 30, 32),
    DK.Z_CLOTH: (222, 220, 210), DK.Z_BOTTLE: (170, 186, 186)}


def _local(Pp, root):
    o = DK.DISPLAY[root]
    return Pp[:, 0] - o.x, Pp[:, 1] - o.y, Pp[:, 2] - o.z


def _near(Pp, root, half=(0.6, 0.6, 1.0)):
    lx, ly, lz = _local(Pp, root)
    return (np.abs(lx) < half[0]) & (np.abs(ly) < half[1]) & (np.abs(lz) < half[2])


def _spot(a, b, ra, rb):
    return np.exp(-((a / ra) ** 2 + (b / rb) ** 2))


# ================================================================ Devices: the desk things
def paint_devices(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp * 2.5, Nn, ao, 1401)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    dust = up * (0.5 + 0.5 * ss(0.30, 0.80, fbm(Pp, 40.0, 2, seed=1402)))
    fx, fy, fz = _local(Pp, 'Fax')
    px, py, pz = _local(Pp, 'ObjectPC')
    lx, ly, lz = _local(Pp, 'Laptop')
    cx, cy, cz = _local(Pp, 'Cassette')
    is_fax = _near(Pp, 'Fax', (0.25, 0.30, 0.3))
    is_pc = _near(Pp, 'ObjectPC', (0.45, 0.62, 0.4))
    side = np.abs(Nn[:, 2]) < 0.5
    # ---- beige ABS (the fax, the handset, the computer, the keyboard, the mouse) gone ivory, grime where hands go
    m = M(DK.Z_BEIGE) | M(DK.Z_MOUSE)
    c = T(BEIGE, 0.04, 0.015)
    c = mixc(c, BEIGE_Y, 0.20 + 0.20 * ss(0.30, 0.80, fbm(Pp, 5.0, 2, seed=1403)) + 0.12 * up)
    c = mixc(c, GRIME_P, cav * 0.45)
    c = mixc(c, BEIGE_L, edge * 0.25)
    c = mixc(c, DUST_L, dust * 0.18)
    hand = is_fax * (_spot(fx + 0.130, fy, 0.022, 0.055) * (fz > 0.084)                     # the handset's bar
                     + ss(-0.105, -0.120, fy) * ss(0.045, 0.058, fz) * (fx > -0.06) * 0.6)  # the panel's front edge
    hand = hand + is_pc * ss(-0.47, -0.495, py) * (pz < 0.03) * (np.abs(px) < 0.23) * 0.7   # the keyboard's front
    mx, my = px - DK.MOUSE.x, py - DK.MOUSE.y
    mouse = M(DK.Z_MOUSE)
    hand = hand + mouse * ss(0.016, 0.026, pz) * ss(-0.01, 0.02, my) * 0.55                  # the mouse buttons
    c = mixc(c, HAND, np.clip(hand, 0, 1) * 0.50)
    col[m] = c[m]
    g = is_fax * side * gline(np.abs(fz - 0.030), 0.0012, aa)                               # the fax's cover seam
    vent = is_pc * (np.abs(Nn[:, 0]) > 0.9) * (py > -0.17) * (py < -0.09) * (pz > 0.04) * (pz < 0.12)
    g = np.maximum(g, vent * gline(dist_periodic(pz, 0.008), 0.0016, aa) * 0.9)              # the case's side vents
    top_seam = is_pc * side * (np.abs(py) < 0.21) * gline(np.abs(pz - (DK.PC['h'] - 0.012)), 0.0012, aa)
    g = np.maximum(g, top_seam * 0.7)                                                        # the cover over the chassis
    btn = mouse * (pz > 0.014) * (np.maximum(gline(np.abs(mx), 0.0012, aa) * (my > 0.012),
                                             gline(np.abs(my - 0.012), 0.0012, aa) * (np.abs(mx) < 0.03)))
    g = np.maximum(g, btn)
    gr = np.where(m, g, gr)
    # ---- darker beige-grey: bottoms, the bezel, the switch, the handset's cups
    m = M(DK.Z_BEIGE_D)
    c = T(BEIGE_D, 0.06, 0.08)
    c = mixc(c, GRIME_P * 0.7, cav * 0.45)
    c = mixc(c, DUST_L, dust * 0.25)
    col[m] = c[m]
    m = M(DK.Z_COIL)                                                                         # the coiled cord
    c = T(lin(178, 168, 144), 0.06, 0.08)
    c = mixc(c, lin(96, 88, 70), cav * 0.6 + ss(0.012, 0.0, fz) * 0.4)
    col[m] = c[m]
    m = M(DK.Z_RUBBER)
    c = T(lin(30, 30, 30), 0.08, 0.10)
    c = mixc(c, lin(70, 68, 64), up * 0.25)
    col[m] = c[m]
    col[M(DK.Z_SLOT)] = lin(14, 14, 14)
    m = M(DK.Z_CORD)
    c = T(lin(32, 32, 32), 0.06, 0.08)
    c = mixc(c, lin(72, 72, 72), up * 0.30)
    col[m] = c[m]
    m = M(DK.Z_TRAY)                                                                         # smoked grey paper guides
    c = T(lin(64, 66, 68), 0.04, 0.02)
    c = mixc(c, lin(112, 114, 116), edge * 0.35)
    c = mixc(c, DUST_L, dust * 0.12)
    col[m] = c[m]
    for zz, base in ((DK.Z_BTN_G, lin(64, 132, 74)), (DK.Z_BTN_R, lin(164, 52, 40))):
        m = M(zz)
        c = T(base, 0.05, 0.06)
        c = mixc(c, base * 1.35, edge * 0.4)
        c = mixc(c, base * 0.6, cav * 0.5)
        col[m] = c[m]
    # ---- the cassette: black shell, the tape edge with the head openings (-y)
    m = M(DK.Z_CASS)
    c = T(lin(36, 36, 38), 0.05, 0.06)
    c = mixc(c, lin(76, 76, 80), edge * 0.35)
    front = Nn[:, 1] < -0.9
    hole = front & (cz > 0.0025) & (cz < 0.0095) & ((np.abs(cx) < 0.012) | (np.abs(np.abs(cx) - 0.030) < 0.005))
    small = front & (cz > 0.0040) & (cz < 0.0080) & (np.abs(np.abs(cx) - 0.043) < 0.0025)
    tape = hole & (cz > 0.0042) & (cz < 0.0078)
    c[hole | small] = lin(12, 12, 12)
    c[tape] = lin(70, 44, 26)
    col[m] = c[m]
    gr = np.where(m & ~front, gline(np.abs(cz - 0.006), 0.0008, aa) * 0.8, gr)               # the two halves
    # ---- the carton: kraft board, scuffed corners, a darker foot; the packing tape
    m = M(DK.Z_CARDB)
    c = T(lin(170, 132, 88), 0.12, 0.10)
    c = mixc(c, lin(124, 94, 62), ss(0.45, 0.75, fbm(Pp, 24.0, 2, seed=1404)) * 0.35)
    c = mixc(c, lin(198, 166, 122), edge * 0.40)
    c = mixc(c, lin(96, 76, 54), ss(0.010, 0.0, Pp[:, 2]) * 0.5 + cav * 0.3)
    col[m] = c[m]
    m = M(DK.Z_TAPE)
    c = T(lin(156, 112, 58), 0.05, 0.08)
    c = mixc(c, lin(204, 164, 108), ss(0.55, 0.85, fbm(Pp, 80.0, 1, seed=1405)) * 0.35)
    col[m] = c[m]
    # ---- the computer's back: zinc-plated sheet, the PSU fan grille, the mains socket, slot covers and ports
    m = M(DK.Z_METAL)
    c = T(lin(176, 178, 176), 0.06, 0.08)
    c = mixc(c, lin(120, 122, 118), cav * 0.4 + ss(0.5, 0.85, fbm(Pp, 20.0, 2, seed=1406)) * 0.15)
    r = np.sqrt((px + 0.15) ** 2 + (pz - 0.075) ** 2)
    grille = (r < 0.040) & (r > 0.011)
    c[grille] = mixc(c, lin(34, 34, 34), (dist_periodic(r, 0.007) > 0.0015).astype(np.float32))[grille]
    for (a0, a1, b0, b1, colr) in ((-0.095, -0.072, 0.098, 0.122, (28, 28, 28)), (-0.092, -0.075, 0.066, 0.084, (40, 40, 40)),
                                   (-0.040, -0.020, 0.100, 0.120, (36, 36, 36))):
        q = (px > a0) & (px < a1) & (pz > b0) & (pz < b1)
        c[q] = lin(*colr)
    slots = (px > 0.030) & (px < 0.170) & (pz > 0.020) & (pz < 0.126)
    ports = slots & (np.abs(dist_periodic(px - 0.041, 0.022)) < 0.005) & (pz > 0.055) & (pz < 0.090) & (px < 0.075)
    c[ports] = lin(30, 30, 30)
    col[m] = c[m]
    g = slots * gline(dist_periodic(px - 0.030, 0.022), 0.0014, aa)
    for sx in (-0.200, 0.200):
        for sz in (0.022, 0.128):
            g = np.maximum(g, ss(0.0035, 0.0025, np.sqrt((px - sx) ** 2 + (pz - sz) ** 2)))
    gr = np.where(m, g * 0.9, gr)
    # ---- the tape recorder's faceplate edges: dark grey powder coat like the cabinet's modules
    m = M(DK.Z_DECK)
    c = T(lin(62, 66, 70), 0.04, 0.03)
    c = mixc(c, lin(104, 108, 112), edge * 0.35)
    c = mixc(c, lin(40, 42, 44), cav * 0.4)
    col[m] = c[m]
    # ---- the laptop: charcoal plastic, the palm rest polished by wrists, a dusty lid
    m = M(DK.Z_LAP)
    c = T(lin(58, 58, 60), 0.04, 0.02)
    palm = (up > 0.9) * (lz < 0.04) * ss(-0.03, -0.07, ly) * (_spot(np.abs(lx) - 0.075, ly + 0.085, 0.045, 0.03))
    c = mixc(c, lin(84, 84, 88), palm * 0.55)
    c = mixc(c, lin(96, 94, 90), dust * (lz > 0.04) * 0.20)
    c = mixc(c, lin(84, 84, 86), edge * 0.30)
    col[m] = c[m]
    m = M(DK.Z_LAP_D)
    c = T(lin(38, 38, 40), 0.05, 0.06)
    c = mixc(c, lin(70, 70, 72), edge * 0.30)
    col[m] = c[m]
    return col, gr


# ================================================================ Outdoor: the drop box on the helipad, the weather screen
def paint_outdoor(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 1501)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    bx, by, bz = _local(Pp, 'DropBox')
    m = M(DK.Z_GREEN)                                       # grey-green enamel, chalky on top, chipped and rusty at the edges
    c = T(GREEN, 0.08, 0.05)
    c = mixc(c, GREEN_FADE, up * 0.45 + ss(0.4, 0.8, n_lo) * 0.15)
    chips = np.clip(edge * 1.3 + ss(0.80, 0.92, fbm(Pp, 30.0, 2, seed=1502)) * 0.5 * (0.4 + 0.6 * ss(1.25, 1.0, bz)), 0, 1)
    c = mixc(c, PRIMER, ss(0.35, 0.60, chips) * 0.8)
    c = mixc(c, RUST, ss(0.55, 0.85, chips) * 0.7)
    runs = run_m(Pp) * (1 - up)
    c = mixc(c, RUST_D, runs * 0.35 * ss(1.0, 1.42, bz))
    slot_run = ss(0.09, 0.05, np.abs(bx)) * ss(1.30, 1.26, bz) * ss(1.04, 1.20, bz) * (Nn[:, 1] < -0.5) * \
        ss(0.45, 0.75, fbm(Pp * np.array([1, 1, 0.15], np.float32), 20.0, 2, seed=1503))
    c = mixc(c, lin(58, 64, 56), slot_run * 0.45)
    c = mixc(c, lin(56, 60, 52), (Nn[:, 2] < -0.5) * 0.35 + cav * 0.35)
    col[m] = c[m]
    m = M(DK.Z_GALV)                                        # the post: galvanised, white rust, splash at the foot
    spang = hash1(np.floor(x * 140.0) + np.floor(y * 140.0) * 31.0 + np.floor(z * 140.0) * 57.0, 1504)
    c = T(lin(150, 154, 152), 0.08, 0.10) * (0.94 + 0.10 * spang)[:, None]
    c = mixc(c, lin(196, 198, 192), ss(0.60, 0.80, fbm(Pp, 12.0, 2, seed=1505)) * 0.45)
    c = mixc(c, RUST, ss(0.16, 0.06, bz) * ss(0.4, 0.7, fbm(Pp, 30.0, 2, seed=1506)) * 0.6)
    c = mixc(c, MUD, ss(0.30, 0.06, bz) * ss(0.35, 0.65, fbm(Pp, 18.0, 2, seed=1507)) * 0.55)
    col[m] = c[m]
    m = M(DK.Z_CONC)                                        # the footing: stained concrete, earth below the ground line
    c = T(lin(134, 132, 126), 0.14, 0.18)
    c = mixc(c, lin(96, 92, 84), ss(0.55, 0.85, fbm(Pp, 9.0, 2, seed=1508)) * 0.35 + cav * 0.3)
    c = mixc(c, lin(90, 82, 66), ss(0.06, -0.01, bz) * 0.6)
    c = mixc(c, lin(66, 56, 44), ss(0.0, -0.05, bz) * 0.85)
    c = mixc(c, MOSS, ss(0.62, 0.82, fbm(Pp, 14.0, 2, seed=1509)) * up * 0.35)
    col[m] = c[m]
    m = M(DK.Z_STEEL)                                       # the flap, the hinges: bare steel gone rusty
    c = T(lin(104, 108, 108), 0.08, 0.12)
    c = mixc(c, RUST, ss(0.45, 0.75, fbm(Pp, 50.0, 2, seed=1510)) * 0.55 + edge * 0.25)
    col[m] = c[m]
    m = M(DK.Z_LOCK)                                        # the cylinder lock: dull chrome
    c = T(lin(172, 172, 168), 0.06, 0.10)
    c = mixc(c, lin(70, 70, 66), cav * 0.6)
    col[m] = c[m]
    col[M(DK.Z_SLOT)] = lin(12, 12, 12)
    # ---- the weather screen: white paint on wood (forest_far's white), grey and flaking outside, dirt and moss up the legs
    sx, sy, sz = _local(Pp, 'MeteoScreen')
    outside = (np.abs(sx) > 0.33) | (np.abs(sy) > 0.27) | (sz > 1.87) | (sz < 1.2)
    for zz, seed in ((DK.Z_SCRWHITE, 1520), (DK.Z_SCRLEG, 1523)):
        m = M(zz)
        c = T(lin(232, 232, 226), 0.04, 0.06)
        c = mixc(c, lin(150, 146, 132), cav * 0.55 + ss(0.65, 0.85, fbm(Pp, 5.0, 2, seed=seed)) * 0.2)
        flake = ss(0.70, 0.86, fbm(Pp, 26.0, 2, seed=seed + 1)) * outside * (0.5 + 0.5 * up)
        c = mixc(c, lin(132, 124, 108), flake * 0.7)                    # grey wood where the paint has gone
        c = mixc(c, lin(178, 176, 166), up * outside * 0.25)
        if zz == DK.Z_SCRLEG:
            c = mixc(c, MUD, ss(0.35, 0.02, sz) * 0.75)
            c = mixc(c, MOSS, ss(0.30, 0.05, sz) * ss(0.5, 0.75, fbm(Pp, 12.0, 2, seed=seed + 2)) * 0.6)
            c = mixc(c, lin(66, 56, 44), ss(0.0, -0.05, sz) * 0.9)
        col[m] = c[m]
    m = M(DK.Z_SCRWOOD)                                                 # the step, the frame inside, the knob: grey-brown wood
    vert = np.abs(Nn[:, 2]) < 0.6
    g2 = fbm(Pp * np.where(vert[:, None], np.array([4.0, 4.0, 0.25], np.float32), np.array([0.3, 4.0, 4.0], np.float32)), 10.0, 2,
             seed=1526)
    c = T(lin(150, 136, 112), 0.12, 0.10) * (0.86 + 0.22 * g2)[:, None]
    c = mixc(c, lin(96, 86, 70), cav * 0.5)
    c = mixc(c, MUD, ss(0.10, 0.0, sz) * 0.6)
    c = mixc(c, MOSS, ss(0.66, 0.84, fbm(Pp, 10.0, 2, seed=1527)) * up * (sz < 0.4) * 0.5)
    col[m] = c[m]
    m = M(DK.Z_SCRSTEEL)
    c = T(lin(110, 112, 112), 0.08, 0.10)
    c = mixc(c, RUST, ss(0.45, 0.75, fbm(Pp, 60.0, 2, seed=1528)) * 0.5)
    col[m] = c[m]
    m = M(DK.Z_SCRMETAL)
    col[m] = T(lin(190, 192, 196), 0.04, 0.06)[m]
    m = M(DK.Z_SCRBLACK)                                                # the recorder: black crackle enamel, brass screws
    c = T(lin(30, 30, 32), 0.05, 0.08)
    c = mixc(c, lin(70, 70, 72), edge * 0.4)
    col[m] = c[m]
    m = M(DK.Z_CLOTH)
    c = T(lin(222, 220, 210), 0.04, 0.06)
    c = mixc(c, lin(160, 156, 140), cav * 0.5)
    col[m] = c[m]
    m = M(DK.Z_BOTTLE)                                                  # the water bottle: pale glass, the water line
    c = T(lin(170, 186, 186), 0.04, 0.06)
    c = mixc(c, lin(120, 140, 146), (sz < 1.255).astype(np.float32) * 0.5)
    col[m] = c[m]
    return col, gr
