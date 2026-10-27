"""Painters for the forest_gear atlases (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
Small (the hand things: cells, the radio, the lamps, the doll, the bulb's cap, the tag, the key, the ice axe; 512 px at
512 px/m) and Haul (the cart and the pulk; 512 px at 160 px/m). Station kit after a winter of use: the walkie's black ABS
rubbed shiny at the edges, a signal-yellow hand lamp with scuffs and grime round the foot, an orange headlamp on a grey-blue
woven band, nickel-plated cells; the doll old and handled: a faded red knitted dress with a cream border, greying stockings,
patent shoes, brown yarn hair; a varnished ash shaft darkened where hands go, a steel head bright at the pick and the adze.
The cart's enzian blue chipped to steel, the film-faced plywood deck worn in the middle, red rims, black tyres with a tread;
the pulk's red polyethylene scratched white underneath, dirty inside. Positions: the roots stand at gear_kit.DISPLAY."""
import math
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, hash1
from gen_paint import RUST, _T, _common
import gear_kit as GK
import gear_tex as GT

DRAFT_COL = {   # sRGB, roughly the painters' base colours (gear_build --draft)
    GK.Z_CELL: (190, 192, 194), GK.Z_CELLWRAP: (28, 46, 104), GK.Z_B6CHAM: (196, 62, 30), GK.Z_B6CAP: (34, 34, 36),
    GK.Z_SPRING: (190, 160, 80), GK.Z_WK: (40, 40, 42), GK.Z_WK_RUB: (30, 30, 30), GK.Z_WK_METAL: (80, 82, 86),
    GK.Z_LAMP: (228, 178, 30), GK.Z_LAMP_BK: (36, 36, 38), GK.Z_LAMP_SW: (190, 40, 30), GK.Z_CAVITY: (18, 18, 18),
    GK.Z_CHROME: (200, 202, 206), GK.Z_BAND: (52, 62, 82), GK.Z_HL: (212, 98, 30), GK.Z_HL_BEZEL: (30, 30, 30),
    GK.Z_CABLE: (28, 28, 28), GK.Z_SKIN: (236, 212, 194), GK.Z_HAIR: (86, 56, 36), GK.Z_DRESS: (150, 46, 40),
    GK.Z_COLLAR: (230, 224, 206), GK.Z_SOCK: (222, 218, 206), GK.Z_SHOE: (30, 28, 28), GK.Z_RIBBON: (190, 30, 34),
    GK.Z_BULBCAP: (196, 198, 196), GK.Z_BULBINS: (24, 24, 26), GK.Z_SOLDER: (170, 170, 168), GK.Z_BRASS: (186, 148, 72),
    GK.Z_STEEL: (150, 152, 154), GK.Z_TAGBK: (32, 32, 34), GK.Z_AXE: (88, 92, 100), GK.Z_AXEWOOD: (176, 140, 92),
    GK.Z_LEASH: (96, 60, 36),
    GK.Z_CART: (34, 72, 136), GK.Z_DECK: (88, 60, 40), GK.Z_TYRE: (30, 30, 30), GK.Z_RIM: (170, 40, 30),
    GK.Z_ZINC: (170, 172, 168), GK.Z_GRIP: (28, 28, 28), GK.Z_SLED: (186, 40, 28), GK.Z_SLED_IN: (160, 36, 26),
    GK.Z_ROPE: (214, 176, 48), GK.Z_TWOOD: (150, 110, 70)}


def _local(Pp, root):
    o = GK.DISPLAY[root]
    return Pp[:, 0] - o.x, Pp[:, 1] - o.y, Pp[:, 2] - o.z


def _near(Pp, root, half):
    lx, ly, lz = _local(Pp, root)
    return (np.abs(lx) < half[0]) & (np.abs(ly) < half[1]) & (lz > -half[2]) & (lz < half[2])


def _spot(a, b, ra, rb):
    return np.exp(-((a / ra) ** 2 + (b / rb) ** 2))


# ================================================================ Small: the hand things
def paint_small(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp * 3.0, Nn, ao, 2101)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    dust = up * (0.4 + 0.6 * ss(0.35, 0.85, fbm(Pp, 60.0, 2, seed=2102)))
    # ---- cells: nickel-plated steel ends, the wrapper's blue shoulder; the 4R25's red chamfers with the black foot band
    m = M(GK.Z_CELL)
    c = T(lin(192, 194, 196), 0.04, 0.05)
    c = mixc(c, lin(120, 122, 126), cav * 0.5)
    c = mixc(c, lin(230, 232, 234), edge * 0.35)
    col[m] = c[m]
    m = M(GK.Z_CELLWRAP)
    col[m] = mixc(T(lin(28, 46, 104), 0.03, 0.03), lin(80, 100, 160), edge * 0.4)[m]
    bx, by, bz = _local(Pp, 'Item_Battery6V')
    m = M(GK.Z_B6CHAM)
    c = T(lin(196, 62, 30), 0.03, 0.03)
    c = np.where((bz < 0.0235)[:, None], lin(30, 30, 32), c)
    c = np.where((np.abs(bz - 0.0238) < 0.0007)[:, None], lin(222, 172, 44), c)
    col[m] = mixc(c, lin(240, 200, 180), edge * 0.25)[m]
    m = M(GK.Z_B6CAP)
    col[m] = mixc(T(lin(34, 34, 36), 0.05, 0.05), lin(76, 76, 78), edge * 0.4)[m]
    m = M(GK.Z_SPRING)
    c = T(lin(196, 166, 86), 0.06, 0.08)
    col[m] = mixc(c, lin(110, 90, 44), cav * 0.6)[m]
    # ---- the walkie: black ABS, the edges rubbed grey-shiny, the battery pack's seam, the knobs' knurl, the clip
    wx, wy, wz = _local(Pp, 'Item_Walkie')
    m = M(GK.Z_WK)
    c = T(lin(40, 40, 42), 0.04, 0.05)
    c = mixc(c, lin(86, 86, 90), edge * 0.55)
    c = mixc(c, lin(26, 26, 28), cav * 0.5)
    c = mixc(c, lin(96, 94, 90), dust * 0.25)
    col[m] = c[m]
    seam = (np.abs(wz - 0.046) < 0.004) * (wy > -0.0165)
    g = seam * gline(np.abs(wz - 0.046), 0.0006, aa)
    tex = (np.abs(Nn[:, 0]) > 0.9) * (wz > 0.06) * (wz < 0.11) * (np.abs(wy) < 0.009)
    g = np.maximum(g, tex * gline(dist_periodic(wz, 0.004), 0.0006, aa) * 0.7)            # side grip ribs
    gr = np.where(m, g, gr)
    m = M(GK.Z_WK_RUB)
    c = T(lin(30, 30, 30), 0.05, 0.06)
    c = mixc(c, lin(64, 64, 64), edge * 0.35 + up * 0.15)
    col[m] = c[m]
    kn = np.zeros(n, np.float32)
    for key in ('ch', 'vol'):
        kc = GK.wk_top_point(*GT.WALKIE_TOP[key])
        ang = np.arctan2(wy - kc.y, wx - kc.x)
        r_ = np.hypot(wx - kc.x, wy - kc.y)
        near = (r_ < 0.009) & (wz > GK.WK['h']) & (wz < GK.WK['h'] + 0.0125) & (np.abs(Nn[:, 2]) < 0.6)
        per = 2 * math.pi * 0.0072 / 24                                                  # 24 ribs round the knob
        kn = np.maximum(kn, near * gline(dist_periodic(ang * 0.0072, per), 0.00035, aa))
    ant = (wz > GK.WK['h'] + 0.006) & (np.abs(Nn[:, 2]) < 0.8)
    kn = np.maximum(kn, ant * gline(dist_periodic(wz, 0.008), 0.0005, aa) * 0.6)
    gr = np.where(m, kn, gr)
    m = M(GK.Z_WK_METAL)
    c = T(lin(80, 82, 86), 0.05, 0.08)
    col[m] = mixc(c, lin(150, 152, 156), edge * 0.5)[m]
    # ---- the hand lamp: signal yellow, scuffed, grime round the foot and in the joints; black parts; the red switch
    lx, ly, lz = _local(Pp, 'Item_Lantern')
    m = M(GK.Z_LAMP)
    c = T(lin(230, 178, 28), 0.04, 0.04)
    c = mixc(c, lin(160, 118, 30), cav * 0.45)
    c = mixc(c, lin(248, 214, 110), edge * 0.35)
    scuff = ss(0.80, 0.92, fbm(Pp * np.array([1, 1, 3], np.float32), 40.0, 2, seed=2111)) * (1 - up)
    c = mixc(c, lin(196, 186, 150), scuff * 0.45)
    c = mixc(c, lin(96, 80, 46), ss(0.020, 0.0, lz) * 0.55)
    c = mixc(c, lin(150, 140, 110), dust * 0.25)
    col[m] = c[m]
    gr = np.where(m, (np.abs(Nn[:, 1]) < 0.3) * (np.abs(Nn[:, 2]) < 0.5) * gline(np.abs(lz - 0.110), 0.0006, aa) * 0.8, gr)
    m = M(GK.Z_LAMP_BK)
    c = T(lin(36, 36, 38), 0.05, 0.05)
    c = mixc(c, lin(80, 80, 82), edge * 0.45)
    col[m] = mixc(c, lin(90, 88, 84), dust * 0.3)[m]
    m = M(GK.Z_LAMP_SW)
    c = T(lin(192, 42, 30), 0.03, 0.03)
    col[m] = mixc(c, lin(240, 110, 90), edge * 0.4)[m]
    m = M(GK.Z_CAVITY)
    col[m] = mixc(np.tile(lin(18, 18, 18), (n, 1)), lin(40, 40, 40), up * 0.4)[m]
    m = M(GK.Z_CHROME)
    refl = 0.5 + 0.5 * np.sin(Nn[:, 2] * 5.0 + Nn[:, 0] * 2.0)
    c = np.tile(lin(70, 72, 78), (n, 1))
    c = mixc(c, lin(226, 228, 232), refl.astype(np.float32))
    col[m] = mixc(c, lin(40, 40, 42), cav * 0.4)[m]
    # ---- the headlamp: the woven band (grey-blue, two light threads), the orange housing, the ribbed black bezel
    hx, hy, hz = _local(Pp, 'Item_Headlamp')
    m = M(GK.Z_BAND)
    c = T(lin(52, 62, 82), 0.06, 0.10)
    weave = ss(0.4, 0.6, 0.5 + 0.5 * np.sin((np.arctan2(hy / GK.HL['b'], hx / GK.HL['a'])) * 260.0))
    c = c * (0.90 + 0.12 * weave)[:, None]
    stripe = (np.abs(hz - GK.HL['zc'] - 0.0065) < 0.0012) | (np.abs(hz - GK.HL['zc'] + 0.0065) < 0.0012)
    c = np.where((stripe & (np.abs(Nn[:, 2]) < 0.5))[:, None], lin(176, 180, 186), c)
    col[m] = mixc(c, lin(110, 112, 110), dust * 0.3)[m]
    m = M(GK.Z_HL)
    c = T(lin(212, 98, 30), 0.04, 0.04)
    c = mixc(c, lin(120, 60, 24), cav * 0.5)
    c = mixc(c, lin(240, 150, 90), edge * 0.35)
    col[m] = mixc(c, lin(150, 120, 96), dust * 0.25)[m]
    m = M(GK.Z_HL_BEZEL)
    yb = -GK.HL['b'] - GK.HL['t'] / 2 - 0.009
    ang = np.arctan2(hz - GK.HL['zc'], hx)
    col[m] = mixc(T(lin(30, 30, 30), 0.05, 0.05), lin(70, 70, 70), edge * 0.4)[m]
    gr = np.where(m, gline(dist_periodic(ang * 0.0212, 0.0212 * 2 * math.pi / 28), 0.0004, aa) * (np.abs(Nn[:, 1]) < 0.6), gr)
    m = M(GK.Z_CABLE)
    col[m] = mixc(T(lin(28, 28, 28), 0.05, 0.05), lin(64, 64, 64), up * 0.3)[m]
    # ---- the doll: skin, yarn hair, the knitted dress with its cream border, collar, stockings, patent shoes, ribbons
    dx, dy, dz = _local(Pp, 'Item_Doll')
    m = M(GK.Z_SKIN)
    c = T(lin(236, 212, 194), 0.03, 0.03)
    c = mixc(c, lin(196, 166, 146), cav * 0.4)
    c = mixc(c, lin(180, 160, 140), ss(0.7, 0.9, fbm(Pp, 80.0, 2, seed=2121)) * 0.25)        # handled, a little grubby
    col[m] = c[m]
    m = M(GK.Z_HAIR)
    hc = GK.DOLL['hc']
    ang = np.arctan2(dy, dx)
    strands = 0.5 + 0.5 * np.sin(ang * 46.0 + fbm(Pp, 30.0, 2, seed=2122) * 6.0 + dz * 40.0)
    c = T(lin(86, 56, 36), 0.06, 0.10) * (0.80 + 0.30 * strands)[:, None]
    c = mixc(c, lin(46, 30, 20), cav * 0.5)
    col[m] = c[m]
    m = M(GK.Z_DRESS)
    knit = 0.5 + 0.5 * np.sin(dz * 2 * math.pi / 0.0045) * np.sign(np.sin(ang * 60.0))
    c = T(lin(150, 46, 40), 0.06, 0.06) * (0.88 + 0.14 * knit)[:, None]
    band = (dz > 0.016) & (dz < 0.034) & (np.abs(Nn[:, 2]) < 0.9)                             # the cream zigzag border
    zig = np.abs(((ang * 18.0 / math.pi) % 2.0) - 1.0) * 0.012 + 0.019
    c = np.where((band & (np.abs(dz - zig) < 0.0028))[:, None], lin(222, 210, 180), c)
    c = np.where((band & ((np.abs(dz - 0.0175) < 0.0012) | (np.abs(dz - 0.0325) < 0.0012)))[:, None], lin(222, 210, 180), c)
    c = mixc(c, lin(90, 32, 28), cav * 0.45)
    c = mixc(c, lin(120, 96, 80), ss(0.012, 0.0, dz) * 0.5)                                  # the hem has sat on floors
    c = mixc(c, lin(176, 120, 110), dust * 0.2)
    col[m] = c[m]
    m = M(GK.Z_COLLAR)
    c = T(lin(230, 224, 206), 0.04, 0.04)
    col[m] = mixc(c, lin(170, 160, 140), cav * 0.5)[m]
    m = M(GK.Z_SOCK)
    c = T(lin(222, 218, 206), 0.04, 0.05)
    c = mixc(c, lin(170, 166, 154), cav * 0.4 + ss(0.6, 0.85, fbm(Pp, 50.0, 2, seed=2123)) * 0.2)
    col[m] = c[m]
    m = M(GK.Z_SHOE)
    shine = ss(0.55, 0.95, np.clip(Nn[:, 2] * 0.6 - Nn[:, 1] * 0.5, 0, 1))
    c = mixc(T(lin(30, 28, 28), 0.04, 0.04), lin(120, 118, 122), shine * 0.6)
    strap = (np.abs(dz - 0.040) < 0.0025) & (np.abs(Nn[:, 1]) > 0.5)
    c = np.where(strap[:, None], lin(16, 16, 16), c)
    btn = (np.abs(dz - 0.040) < 0.003) & (np.abs(np.abs(dx) - 0.036 - 0.011) < 0.003)
    c = np.where(btn[:, None], lin(200, 170, 90), c)
    col[m] = c[m]
    m = M(GK.Z_RIBBON)
    col[m] = mixc(T(lin(190, 30, 34), 0.04, 0.04), lin(240, 120, 120), edge * 0.4)[m]
    # ---- the bulb's cap: aluminium thread, black glass, the solder contact
    ux, uy, uz = _local(Pp, 'Item_Bulb')
    m = M(GK.Z_BULBCAP)
    c = T(lin(196, 198, 196), 0.04, 0.06)
    thr = 0.5 + 0.5 * np.cos((uz - 0.006) * 2 * math.pi / 0.0036)
    c = c * (0.78 + 0.26 * thr)[:, None]
    col[m] = mixc(c, lin(120, 110, 90), ss(0.7, 0.9, fbm(Pp, 120.0, 2, seed=2131)) * 0.3)[m]
    col[M(GK.Z_BULBINS)] = mixc(T(lin(24, 24, 26), 0.02, 0.02), lin(90, 90, 96), edge * 0.5)[M(GK.Z_BULBINS)]
    col[M(GK.Z_SOLDER)] = T(lin(176, 176, 172), 0.04, 0.06)[M(GK.Z_SOLDER)]
    # ---- brass (the tag's rim, the key), steel rings, the key's black tag
    m = M(GK.Z_BRASS)
    c = T(lin(186, 148, 72), 0.05, 0.08)
    c = mixc(c, lin(110, 84, 40), cav * 0.6)
    col[m] = mixc(c, lin(232, 204, 130), edge * 0.5)[m]
    m = M(GK.Z_STEEL)
    c = T(lin(150, 152, 154), 0.05, 0.08)
    col[m] = mixc(c, lin(210, 212, 214), edge * 0.5)[m]
    m = M(GK.Z_TAGBK)
    col[m] = mixc(T(lin(32, 32, 34), 0.04, 0.04), lin(80, 80, 82), edge * 0.5)[m]
    # ---- the ice axe: the steel head (dark, bright at the pick's point and the adze's edge), the ash shaft, the loop
    ax, ay, az = _local(Pp, 'Item_IceAxe')
    m = M(GK.Z_AXE)
    c = T(lin(88, 92, 100), 0.06, 0.08)
    bright = ss(0.12, 0.17, ax) + ss(-0.07, -0.095, ax) + ss(0.012, 0.0, az)
    c = mixc(c, lin(200, 204, 210), np.clip(bright, 0, 1) * 0.7 + edge * 0.35)
    c = mixc(c, RUST, ss(0.82, 0.94, fbm(Pp, 70.0, 2, seed=2141)) * 0.35)
    col[m] = c[m]
    m = M(GK.Z_AXEWOOD)
    grain = fbm(Pp * np.array([6.0, 6.0, 0.35], np.float32), 30.0, 2, seed=2142)
    c = T(lin(176, 140, 92), 0.05, 0.05) * (0.86 + 0.24 * grain)[:, None]
    hands = ss(0.06, 0.12, az) * ss(0.30, 0.22, az)
    c = mixc(c, lin(96, 70, 44), hands * 0.55)
    col[m] = c[m]
    m = M(GK.Z_LEASH)
    col[m] = mixc(T(lin(96, 60, 36), 0.06, 0.08), lin(140, 100, 70), edge * 0.4)[m]
    return col, gr


# ================================================================ Haul: the cart and the pulk
def paint_haul(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 2201)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    cx, cy, cz = _local(Pp, 'Item_Cart')
    m = M(GK.Z_CART)                                         # enzian blue, chipped to steel at the edges, rust in the chips
    c = T(lin(34, 72, 136), 0.06, 0.05)
    chips = np.clip(edge * 1.4 + ss(0.82, 0.94, fbm(Pp, 30.0, 2, seed=2202)) * 0.5, 0, 1)
    c = mixc(c, lin(120, 124, 126), ss(0.40, 0.65, chips) * 0.8)
    c = mixc(c, RUST, ss(0.62, 0.90, chips) * 0.4)
    c = mixc(c, lin(20, 40, 76), cav * 0.4)
    grip = (cz > 0.85)
    c = mixc(c, lin(130, 140, 150), grip * edge * 0.6)
    col[m] = c[m]
    m = M(GK.Z_DECK)                                         # film-faced plywood: dark brown, a mesh print, worn pale in the middle
    top = Nn[:, 2] > 0.9
    hexp = (dist_periodic(cx + 0.5 * np.floor(cy / 0.006) * 0.006, 0.006) < 0.0012) & (dist_periodic(cy, 0.006) < 0.0012)
    c = T(lin(88, 60, 40), 0.06, 0.05)
    c = np.where((hexp & top)[:, None], c * 1.18, c)
    wear = _spot(cx, cy, 0.20, 0.32) * top
    c = mixc(c, lin(132, 104, 76), wear * 0.55)
    c = mixc(c, lin(70, 66, 60), ss(0.55, 0.85, fbm(Pp, 6.0, 2, seed=2203)) * top * 0.3)
    side = ~top & (Nn[:, 2] > -0.9)
    ply = dist_periodic(cz, 0.0026) < 0.0007
    c = np.where(side[:, None], np.where(ply[:, None], lin(130, 100, 64), lin(196, 162, 112)), c)
    col[m] = c[m]
    m = M(GK.Z_TYRE)
    c = T(lin(30, 30, 30), 0.06, 0.08)
    c = mixc(c, lin(70, 66, 60), up * 0.25 + ss(0.6, 0.9, fbm(Pp, 30.0, 2, seed=2204)) * 0.15)
    col[m] = c[m]
    run = np.abs(Nn[:, 0]) < 0.45
    tread = np.zeros(n, np.float32)
    wr = GK.CT['wr']
    for wxs in (-1, 1):                                       # the tread: chevrons round each wheel's running surface
        for wyc in (-GK.CT['wy_f'], GK.CT['wy_b'] + GK.CT['trail']):
            wxc = wxs * GK.CT['wx']
            near = (np.abs(cx - wxc) < 0.05) & (np.hypot(cy - wyc, cz - wr) < wr + 0.01)
            ang = np.arctan2(cz - wr, cy - wyc)
            tread = np.maximum(tread, near * run * gline(dist_periodic(ang * wr + np.abs(cx - wxc) * 0.6, 0.020), 0.0025, aa))
    gr = np.where(m, tread * 0.9, gr)
    m = M(GK.Z_RIM)
    c = T(lin(170, 40, 30), 0.05, 0.05)
    c = mixc(c, lin(110, 90, 80), ss(0.8, 0.92, fbm(Pp, 40.0, 2, seed=2205)) * 0.4 + edge * 0.3)
    col[m] = c[m]
    m = M(GK.Z_ZINC)
    c = T(lin(170, 172, 168), 0.06, 0.08)
    c = mixc(c, lin(206, 200, 170), ss(0.6, 0.8, fbm(Pp, 20.0, 2, seed=2206)) * 0.3)
    c = mixc(c, RUST, ss(0.82, 0.95, fbm(Pp, 50.0, 2, seed=2207)) * 0.35 + cav * 0.2)
    col[m] = c[m]
    m = M(GK.Z_GRIP)
    col[m] = mixc(T(lin(28, 28, 28), 0.05, 0.05), lin(70, 70, 70), edge * 0.4)[m]
    gr = np.where(m, gline(dist_periodic(cx, 0.008), 0.0012, aa) * 0.8, gr)
    # ---- the pulk
    sx, sy, sz = _local(Pp, 'Item_Sled')
    m = M(GK.Z_SLED)
    c = T(lin(186, 40, 28), 0.05, 0.05)
    c = mixc(c, lin(214, 96, 80), up * 0.30 * (sz > 0.15))                                   # sun-faded rims
    under = Nn[:, 2] < -0.5
    scratch = ss(0.55, 0.75, fbm(Pp * np.array([6.0, 0.3, 6.0], np.float32), 40.0, 2, seed=2211))
    c = mixc(c, lin(226, 196, 186), under * scratch * 0.75)
    c = mixc(c, lin(120, 30, 24), cav * 0.4)
    c = mixc(c, lin(240, 200, 190), edge * 0.25)
    col[m] = c[m]
    m = M(GK.Z_SLED_IN)
    c = T(lin(160, 36, 26), 0.06, 0.05)
    stains = ss(0.55, 0.80, fbm(Pp, 5.0, 3, seed=2212)) * up
    c = mixc(c, lin(120, 96, 80), stains * 0.45)
    c = mixc(c, lin(90, 26, 20), cav * 0.5)
    col[m] = c[m]
    m = M(GK.Z_ROPE)
    c = T(lin(214, 176, 48), 0.06, 0.08)
    tracer = ss(0.45, 0.55, 0.5 + 0.5 * np.sin((x + y + z) * 260.0))
    c = mixc(c, lin(40, 50, 110), tracer * 0.7)
    c = mixc(c, lin(120, 100, 60), cav * 0.4 + ss(0.04, 0.0, sz) * 0.3)
    col[m] = c[m]
    m = M(GK.Z_TWOOD)
    grain = fbm(Pp * np.array([0.3, 6.0, 6.0], np.float32), 30.0, 2, seed=2213)
    col[m] = (T(lin(150, 110, 70), 0.05, 0.05) * (0.86 + 0.24 * grain)[:, None])[m]
    return col, gr
