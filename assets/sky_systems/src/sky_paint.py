"""Painters for the sky_systems atlases (SkyMachines and SkyStructures share paint_machines) (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
SkyMachines: concrete pads with the island's pale bone dust, the machines in faded olive enamel, rust-brown steel frames,
safety-yellow guards and railings, frosted black insulation on the cold loop, the condenser's fins, the hopper caked with
dust inside, the tilting deck in worn chequer plate with hazard stripes at the edge, the concrete ballast blocks with their
stencilled weight, the altitude board's dark steel back, the lattice legs.
SkyWalk: rust-brown stringers and rungs, faded yellow railings and toe boards, dark hangers, rime on the top edges.
Positions: the roots stand at sky_kit.DISPLAY while baked."""
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin
from gen_paint import RUST, RUST_D, _T, _common
import gear_tex as GT
import pxfont as F
import sky_kit as SK

CONC, CONC_D, CONC_L = lin(130, 128, 120), lin(84, 84, 80), lin(168, 166, 156)
DUSTB, DUSTB_D = lin(202, 196, 164), lin(150, 144, 118)            # bone dust
OLIVE, OLIVE_F = lin(84, 88, 64), lin(122, 124, 98)
RBROWN = lin(98, 72, 54)
YELLOW, YELLOW_F, BLACK, RED = lin(206, 164, 40), lin(186, 160, 92), lin(30, 30, 28), lin(158, 40, 30)
STEEL, STEEL_D, CHROME = lin(118, 120, 118), lin(58, 60, 58), lin(190, 192, 194)
FROST, RIME = lin(222, 232, 240), lin(206, 216, 224)
W = SK
DRAFT_COL = {
    W.Z_PAD: (130, 128, 120), W.Z_SKID: (98, 72, 54), W.Z_MOTOR: (84, 88, 64), W.Z_COMP: (70, 72, 70), W.Z_PULLEY: (58, 60, 58),
    W.Z_BELT: (30, 30, 28), W.Z_GUARD: (206, 164, 40), W.Z_COND: (84, 88, 64), W.Z_FIN: (64, 66, 62), W.Z_FAN: (50, 52, 50),
    W.Z_TANK: (84, 88, 64), W.Z_PIPE: (118, 120, 118), W.Z_INSUL: (34, 34, 34), W.Z_VALVE: (158, 40, 30), W.Z_CAB: (84, 88, 64),
    W.Z_BEACON: (50, 50, 48), W.Z_HOPPER: (84, 88, 64), W.Z_HOPIN: (180, 174, 146), W.Z_BLOWER: (84, 88, 64),
    W.Z_MAST: (118, 120, 118), W.Z_NOZZLE: (70, 72, 70), W.Z_LADDER: (98, 72, 54), W.Z_RAILY: (206, 164, 40),
    W.Z_CONC: (130, 128, 120), W.Z_DECK: (110, 108, 100), W.Z_DECKUND: (70, 52, 40), W.Z_HINGE: (58, 60, 58),
    W.Z_RAM: (206, 164, 40), W.Z_BLOCK: (140, 138, 130), W.Z_LEVER: (158, 40, 30), W.Z_HPU: (84, 88, 64), W.Z_POST: (206, 164, 40),
    W.Z_BOARD: (60, 62, 58), W.Z_TRUSS: (98, 72, 54), W.Z_LAMPB: (70, 74, 64), W.Z_DUST: (202, 196, 164), W.Z_FROST: (222, 232, 240),
    W.Z_PLATE: (150, 150, 146), W.Z_DUSTIN: (202, 196, 164), W.Z_BHID: (50, 52, 48), W.Z_PIT: (96, 94, 88),
    W.Z_WSTR: (98, 72, 54), W.Z_WRAIL: (186, 160, 92), W.Z_WTOE: (206, 164, 40), W.Z_WHANG: (58, 60, 58),
    W.Z_WPLATE: (98, 72, 54), W.Z_WLAMP: (70, 74, 64), W.Z_WRUNG: (98, 72, 54), W.Z_WCAGE: (98, 72, 54), W.Z_WROCK: (80, 78, 74)}


def _local(Pp, root):
    o = SK.DISPLAY[root]
    return Pp[:, 0] - o.x, Pp[:, 1] - o.y, Pp[:, 2] - o.z


def stencil(u, v, txt, cu, cv, px, font=F.F57):
    """texels whose face coordinates (u right, v up, metres) fall on the text centred at (cu, cv); px = one font pixel"""
    m = GT.prop_mask(txt, font, 1)
    h, w = m.shape
    ci = np.floor((u - cu) / px + w / 2.0).astype(np.int64)
    ri = np.floor((cv - v) / px + h / 2.0).astype(np.int64)
    ok = (ci >= 0) & (ci < w) & (ri >= 0) & (ri < h)
    out = np.zeros(len(u), bool)
    out[ok] = m[ri[ok], ci[ok]]
    return out


def hazard(s, t, period=0.25):
    return (np.floor((s + t) / (period / 2)) % 2) == 1


def runs(Pp, seed, k=0.1):
    return ss(0.58, 0.80, fbm(Pp * np.array([1, 1, k], np.float32), 6.0, 3, seed=seed))


def paint_metal(Pp, T, cav, edge, up, seed, base, faded=None, rust=0.35, chips=0.5, dust=0.25, n_hi=None):
    """enamelled steel: fades where the sun gets it, rust in the cavities and runs, chipped edges, dust on the tops"""
    c = T(base, 0.10, 0.14)
    if faded is not None:
        c = mixc(c, faded, 0.14 + ss(0.40, 0.75, fbm(Pp, 7.0, 2, seed=seed)) * 0.08 + up * 0.18)
    c = mixc(c, RUST, cav * rust * ss(0.35, 0.65, fbm(Pp, 9.0, 2, seed=seed + 1)))
    c = mixc(c, RUST_D, runs(Pp, seed + 2) * rust * 0.6)
    c = mixc(c, STEEL_D, edge * chips)
    c = mixc(c, DUSTB, up * dust * (0.35 + 0.35 * ss(0.35, 0.70, fbm(Pp, 9.0, 2, seed=seed + 3))))
    return c


def paint_conc(Pp, T, cav, up, seed, base=CONC, dust=0.5):
    c = T(base, 0.14, 0.20)
    c = mixc(c, lin(108, 106, 100), ss(0.60, 0.80, fbm(Pp, 25.0, 1, seed=seed)) * 0.30)
    c = mixc(c, CONC_L, ss(0.76, 0.90, fbm(Pp, 50.0, 1, seed=seed + 1)) * 0.25)
    c = mixc(c, CONC_D, cav * 0.35)
    return mixc(c, DUSTB, up * dust * (0.30 + 0.25 * ss(0.30, 0.75, fbm(Pp, 6.0, 2, seed=seed + 2))))


# ================================================================ SkyMachines
def paint_machines(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 6101)
    T = _T(n_lo, n_hi)
    near_spray = ss(4.5, 1.5, np.hypot(Pp[:, 0] - SK.DISPLAY['SkySprayer'].x, Pp[:, 1] - SK.DISPLAY['SkySprayer'].y))

    def put(zz, c):
        m = M(zz)
        col[m] = c[m]

    # concrete: pads, the ballast foundation and its face down the cliff
    for zz, seed in ((W.Z_PAD, 6102), (W.Z_CONC, 6103)):
        if M(zz).any():
            c = paint_conc(Pp, T, cav, up, seed, dust=0.35 + 0.25 * float(zz == W.Z_PAD))
            c = mixc(c, DUSTB, near_spray * up * 0.45)
            if zz == W.Z_CONC:
                bx, by, bz = _local(Pp, 'SkyBallast')
                c = mixc(c, lin(92, 90, 84), runs(Pp, seed + 5) * ss(-0.2, -2.6, bz) * 0.5)   # the cliff face: water runs
                c = mixc(c, lin(70, 68, 64), ss(-1.6, -2.6, bz) * 0.4)
            put(zz, c)
    # steel frames: rust-brown, olive enamel machines, yellow guards
    put(W.Z_SKID, paint_metal(Pp, T, cav, edge, up, 6110, RBROWN, rust=0.55, chips=0.3, dust=0.4))
    put(W.Z_TRUSS, paint_metal(Pp, T, cav, edge, up, 6111, RBROWN, rust=0.6, chips=0.2, dust=0.2))
    put(W.Z_LADDER, paint_metal(Pp, T, cav, edge, up, 6112, RBROWN, rust=0.6, chips=0.4, dust=0.3))
    for zz, seed in ((W.Z_MOTOR, 6120), (W.Z_COND, 6121), (W.Z_TANK, 6122), (W.Z_CAB, 6123), (W.Z_HOPPER, 6124),
                     (W.Z_BLOWER, 6125), (W.Z_HPU, 6126)):
        if M(zz).any():
            c = paint_metal(Pp, T, cav, edge, up, seed, OLIVE, OLIVE_F, rust=0.35, chips=0.45, dust=0.35)
            if zz in (W.Z_HOPPER, W.Z_BLOWER):
                c = mixc(c, DUSTB, (0.08 + 0.30 * up + 0.06 * ss(0.4, 0.7, fbm(Pp, 12.0, 2, seed=seed + 7))) * near_spray)
            if zz == W.Z_MOTOR:
                fins = gline(dist_periodic(Pp[:, 1], 0.08), 0.010, aa) * (np.abs(Nn[:, 1]) < 0.6)
                c = mixc(c, lin(50, 52, 42), fins * 0.4)
            put(zz, c)
    put(W.Z_GUARD, paint_metal(Pp, T, cav, edge, up, 6130, YELLOW, YELLOW_F, rust=0.3, chips=0.6, dust=0.3))
    put(W.Z_RAILY, paint_metal(Pp, T, cav, edge, up, 6131, YELLOW, YELLOW_F, rust=0.35, chips=0.6, dust=0.25))
    # the ram: yellow barrel, chrome rod (by height above its base)
    if M(W.Z_RAM).any():
        bx, by, bz = _local(Pp, 'SkyBallast')
        c = paint_metal(Pp, T, cav, edge, up, 6132, YELLOW, YELLOW_F, rust=0.3, chips=0.5, dust=0.2)
        ram = np.hypot(np.abs(bx) - 1.2, by - 3.5) < 0.115
        rod = ram & (bz > -0.425)
        c = np.where(rod[:, None], mixc(T(CHROME, 0.05, 0.1), RUST, ss(0.6, 0.8, fbm(Pp, 30.0, 2, seed=6133)) * 0.3), c)
        c = np.where((~ram)[:, None], T(lin(36, 36, 34), 0.05, 0.1), c)      # the hoses from the unit: black
        put(W.Z_RAM, c)
    # the compressor's cast iron, pulleys, hinges, the fan, belts
    put(W.Z_COMP, paint_metal(Pp, T, cav, edge, up, 6140, lin(70, 74, 72), rust=0.4, chips=0.3, dust=0.2))
    for zz, seed in ((W.Z_PULLEY, 6141), (W.Z_HINGE, 6142), (W.Z_FAN, 6143), (W.Z_BEACON, 6144), (W.Z_LAMPB, 6145)):
        if M(zz).any():
            put(zz, paint_metal(Pp, T, cav, edge, up, seed, STEEL_D if zz != W.Z_LAMPB else lin(70, 74, 64),
                                rust=0.45, chips=0.5, dust=0.2))
    put(W.Z_BELT, T(lin(34, 32, 30), 0.06, 0.12))
    # the condenser's fins: dark grey, fine horizontal lines, dust caught in them
    if M(W.Z_FIN).any():
        c = T(lin(72, 74, 70), 0.03, 0.06)
        fl = gline(dist_periodic(Pp[:, 2], 0.025), 0.004, aa)
        c = mixc(c, lin(44, 46, 44), fl * 0.5)
        gr = np.where(M(W.Z_FIN), fl * 0.5, gr)
        put(W.Z_FIN, c)
    # the cold loop: steel pipes, the black insulation furred with frost, icicles; the red handwheel
    put(W.Z_PIPE, paint_metal(Pp, T, cav, edge, up, 6160, STEEL, rust=0.3, chips=0.2, dust=0.15))
    if M(W.Z_INSUL).any():
        c = T(lin(34, 34, 34), 0.06, 0.12)
        fr = (0.50 + 0.20 * ss(0.40, 0.70, fbm(Pp, 16.0, 2, seed=6161))) * (0.30 + 0.70 * up)
        c = mixc(c, FROST, np.clip(fr, 0, 1) * 0.70)
        put(W.Z_INSUL, c)
    put(W.Z_FROST, T(FROST, 0.04, 0.08))
    put(W.Z_VALVE, paint_metal(Pp, T, cav, edge, up, 6162, RED, rust=0.3, chips=0.5, dust=0.0))
    put(W.Z_LEVER, paint_metal(Pp, T, cav, edge, up, 6163, RED, rust=0.25, chips=0.5, dust=0.0))
    # the sprayer: the hopper's inside caked with dust, the heap, the mast and nozzle dusted
    put(W.Z_HOPIN, mixc(T(DUSTB_D, 0.12, 0.2), DUSTB, ss(0.3, 0.7, fbm(Pp, 5.0, 3, seed=6170)) * 0.7))
    for zz in (W.Z_DUSTIN, W.Z_DUST):
        put(zz, mixc(T(DUSTB, 0.10, 0.18), DUSTB_D, cav * 0.5 + ss(0.6, 0.8, fbm(Pp, 12.0, 2, seed=6171)) * 0.25))
    for zz, seed in ((W.Z_MAST, 6172), (W.Z_NOZZLE, 6173)):
        c = paint_metal(Pp, T, cav, edge, up, seed, STEEL if zz == W.Z_MAST else lin(70, 72, 70), rust=0.35, chips=0.2, dust=0.6)
        c = mixc(c, DUSTB, ss(0.4, 0.7, fbm(Pp * np.array([1, 1, 0.2], np.float32), 8.0, 2, seed=seed + 1)) * 0.35)
        put(zz, c)
    # the tilting deck: worn chequer plate, hazard stripes along the edge and on the kerbs; its ribs underneath
    if M(W.Z_DECK).any():
        bx, by, bz = _local(Pp, 'SkyBallast')
        c = paint_metal(Pp, T, cav, edge, up, 6180, lin(112, 110, 102), rust=0.5, chips=0.3, dust=0.3)
        lug = (np.abs(dist_periodic(bx + by, 0.06)) < 0.008) | (np.abs(dist_periodic(bx - by, 0.06)) < 0.008)
        c = mixc(c, lin(150, 148, 140), (lug & (up > 0.7)) * 0.35)
        wear = ss(0.35, 0.65, fbm(Pp, 3.0, 3, seed=6181)) * up
        c = mixc(c, lin(150, 146, 136), wear * 0.25)
        strip = ((by < 0.65) & (up > 0.7)) | ((np.abs(bx) > 2.38) & (up < 0.7))
        hz = hazard(bx, by + bz, 0.30)
        c = np.where(strip[:, None], mixc(np.where(hz[:, None], BLACK, YELLOW) * (0.85 + 0.2 * n_hi)[:, None], RUST,
                                          ss(0.55, 0.8, fbm(Pp, 10.0, 2, seed=6182)) * 0.5), c)
        put(W.Z_DECK, c)
    put(W.Z_DECKUND, paint_metal(Pp, T, cav, edge, up, 6183, lin(70, 54, 42), rust=0.7, chips=0.1, dust=0.0))
    # the ballast blocks: concrete, yellow-black tops' edges, the weight stencilled on the long sides
    if M(W.Z_BLOCK).any():
        bx, by, bz = _local(Pp, 'SkyBallast')
        c = paint_conc(Pp, T, cav, up, 6190, lin(146, 144, 136), dust=0.4)
        txt = np.zeros(n, bool)
        dz = 0.30
        for i, xx in enumerate((-1.6, 0.0, 1.6)):
            cy = 2.2 + 0.15 * float(SK.hsh(i, 61))
            side = (np.abs(bx - xx) < 0.62) & (np.abs(Nn[:, 1]) > 0.7)
            right = -np.sign(Nn[:, 1])
            u = (bx - xx) * right
            txt |= side & stencil(u, bz - dz, '3,5 t', 0.0, 0.55, 0.035)
            txt |= (np.abs(bx - xx) < 0.62) & (np.abs(Nn[:, 0]) > 0.7) & stencil((by - cy) * np.sign(Nn[:, 0]), bz - dz,
                                                                                    f'{i + 1}', 0.0, 0.5, 0.05)
        c = np.where(txt[:, None], T(lin(40, 40, 38), 0.05, 0.1), c)
        top_edge = (bz > dz + 0.88) & (up < 0.5)
        c = np.where(top_edge[:, None], np.where(hazard(bx + by, bz, 0.20)[:, None], BLACK, YELLOW), c)
        put(W.Z_BLOCK, c)
    # the lever post: yellow-black bands; the altitude board's back; sign plates' backs
    if M(W.Z_POST).any():
        c = np.where((np.floor(Pp[:, 2] / 0.25) % 2 == 0)[:, None], YELLOW, BLACK)
        c = mixc(c, RUST, cav * 0.4 + edge * 0.3)
        put(W.Z_POST, c)
    put(W.Z_BOARD, paint_metal(Pp, T, cav, edge, up, 6195, lin(62, 64, 60), rust=0.55, chips=0.2, dust=0.1))
    put(W.Z_BHID, T(lin(50, 52, 48), 0.05, 0.05))
    if M(W.Z_PIT).any():
        bx, by, bz = _local(Pp, 'SkyBallast')
        c = paint_conc(Pp, T, cav, up, 6197, lin(104, 102, 96), dust=0.0)
        c = mixc(c, lin(62, 60, 56), ss(-0.5, -1.0, bz) * 0.5)                           # damp and dark at the bottom
        c = mixc(c, lin(70, 50, 36), ss(0.25, 0.0, np.hypot(np.abs(bx) - 1.2, by - 3.5)) * 0.5 * (up > 0.5))  # oil under the rams
        put(W.Z_PIT, c)
    put(W.Z_PLATE, paint_metal(Pp, T, cav, edge, up, 6196, lin(150, 150, 146), rust=0.4, chips=0.4, dust=0.1))
    return col, gr


# ================================================================ SkyWalk
def paint_walk(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 6201)
    T = _T(n_lo, n_hi)
    rime = up * ss(0.40, 0.70, fbm(Pp, 5.0, 2, seed=6202)) * 0.55

    def put(zz, c):
        m = M(zz)
        col[m] = mixc(c, RIME, rime)[m]

    put(W.Z_WSTR, paint_metal(Pp, T, cav, edge, up, 6210, RBROWN, rust=0.75, chips=0.2, dust=0.0))
    put(W.Z_WRUNG, paint_metal(Pp, T, cav, edge, up, 6211, RBROWN, rust=0.6, chips=0.5, dust=0.0))
    put(W.Z_WCAGE, paint_metal(Pp, T, cav, edge, up, 6212, RBROWN, rust=0.6, chips=0.3, dust=0.0))
    put(W.Z_WPLATE, paint_metal(Pp, T, cav, edge, up, 6213, lin(84, 70, 58), rust=0.8, chips=0.1, dust=0.0))
    put(W.Z_WRAIL, paint_metal(Pp, T, cav, edge, up, 6214, YELLOW_F, rust=0.5, chips=0.6, dust=0.0))
    put(W.Z_WTOE, paint_metal(Pp, T, cav, edge, up, 6215, YELLOW, YELLOW_F, rust=0.45, chips=0.5, dust=0.0))
    put(W.Z_WHANG, paint_metal(Pp, T, cav, edge, up, 6216, STEEL_D, rust=0.4, chips=0.3, dust=0.0))
    put(W.Z_WLAMP, paint_metal(Pp, T, cav, edge, up, 6217, lin(70, 74, 64), rust=0.4, chips=0.4, dust=0.0))
    put(W.Z_WROCK, T(lin(80, 78, 74), 0.1, 0.2))
    return col, None
