"""Painters for the far points' atlases (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n]).
The generator shed's wear language (gen_paint / hut_paint / road_paint / base_paint: the same rules, noise and finishes)
on the far things: the dishes' white paint (the reflector in panels: seams, one tone a panel, grime run down toward its
lowest rim), the galvanised trusses and ladders, the grey telecom cabinet; the radome's white GRP panels (staggered
seams, streaks from the beacon down), the shelters' corrugated walls, the relay mast's galvanising; the weather station's
white pickets going grey at the foot, the louvred screen, the red vane, the striped snow stake, the solar panel's cells;
the lookout's galvanised frame, the steel grating of its treads, the dark-stained cab with white window frames, the
corrugated roof; the chapel's lime plaster (streaks under the sills, damp and algae at the foot), its fieldstone plinth,
wooden shingles with moss, dark boards, the stone floor, the pews, the linen with its red border, the brass candlesticks,
the iron crosses on the graves; the pump house's red brick in stretcher bond, its felt roof, the blue pump; the cabin's
weathered logs and pale ends, its tar paper, the woodpile; the campsite's faded orange tent, the charred fire ring.
Positions arrive in the bake layout (far_build: LAYOUT): each texel goes back to its prefab's own frame."""
import math
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, boards, hash1
from gen_paint import OIL, GRIME, DUST, RUST, RUST_D, _T, _common, run_m
from hut_paint import galv, steel_black, stone, end_grain, bark, weathered, trim_white, MOSS, LICHEN
from base_paint import concrete, _foot, SOIL, MUD, ALGAE, NEEDLES
import far_spec as S
import far_kit as FK

LAYOUT = {}
WHITE_P = lin(222, 222, 214)


def _locals(Pp):
    names = list(LAYOUT)
    if not names:
        return Pp.copy(), np.array([''] * len(Pp), dtype=object)
    offs = np.array([LAYOUT[n] for n in names], np.float32)
    idx = np.zeros(len(Pp), np.int64) if len(names) == 1 else np.abs(Pp[:, 0][:, None] - offs[None, :, 0]).argmin(1)
    return Pp - offs[idx], np.array(names, dtype=object)[idx]


def _ground(Pl, own):
    g = np.zeros(len(Pl), np.float32)
    for n in set(own):
        m = own == n
        if n in S.GROUND['prefabs']:
            g[m] = S.ground_v(n, Pl[m, 0], Pl[m, 1])
    return g


def paint_far(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    Pl, own = _locals(Pp)
    hz = Pl[:, 2] - _ground(Pl, own)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    zs = set(np.unique(Z).tolist())
    for zones, fn in ((FK.DISH_ZONES, _dish), (FK.TOWER_ZONES, _towers), (FK.METEO_ZONES, _meteo), (FK.LOOK_ZONES, _lookout),
                      (FK.CHAPEL_ZONES, _chapel), (FK.SMALL_ZONES, _small)):
        if zs & set(zones):
            m = np.isin(Z, zones)
            c, g = fn(Pp[m], Pl[m], Nn[m], Z[m], ao[m], aa, hz[m], own[m])
            col[m] = c
            gr[m] = g
    return col, gr


def white_paint(Pp, T, cav, up, edge, seed, base=(222, 222, 214)):
    """white paint on steel: chalky, rust bleeding from edges and fixings, grime in the hollows"""
    c = T(lin(*base), 0.06, 0.10)
    c = mixc(c, lin(196, 194, 182), ss(0.5, 0.85, fbm(Pp, 3.0, 2, seed=seed)) * 0.35)
    c = mixc(c, RUST, np.clip(edge * 0.45 + run_m(Pp) * 0.30, 0, 0.7))
    return mixc(c, lin(120, 116, 104), cav * 0.45)


# ================================================================ the dishes
def _dish(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 2101)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    name = [o for o in set(own)][0] if len(set(own)) else 'Dish_1'
    g = S.dish_geom(name if name in S.DISHES else 'Dish_1')
    ax, vtx, R_ = np.array(g['axis']), np.array(g['vertex']), g['R']
    u = np.array([1.0, 0.0, 0.0])
    v = np.cross(ax, u)
    q = Pl - vtx
    ru, rv = q @ u, q @ v
    r = np.hypot(ru, rv)
    ph = np.mod(np.arctan2(rv, ru), 2 * np.pi)
    # ---- the reflector: white panels (16 sectors, rings at 0.30 / 0.54 / 0.78 R), one tone a panel, grime streaks running
    # toward the lowest rim (+v), algae and needles in the lowest sector, a darker stain round the hub
    m = M(FK.Z_DREFL)
    ring = np.digitize(r / R_, [0.30, 0.54, 0.78])
    sec = np.floor(ph / (2 * np.pi / 16))
    c = T(lin(226, 226, 220), 0.05, 0.08) * (0.94 + 0.08 * hash1(sec * 7 + ring * 31, 51))[:, None]
    low = np.clip(rv / R_, 0, 1)                                         # 0 at the centre, 1 at the lowest rim
    runs = ss(0.55, 0.85, fbm(np.stack([ph * 4.0, r * 0.3, np.zeros(n)], -1).astype(np.float32), 3.0, 3, seed=2102))
    c = mixc(c, lin(168, 160, 140), runs * (0.25 + 0.45 * low) * ss(0.2, 0.8, r / R_))
    c = mixc(c, ALGAE, ss(0.70, 0.98, low) * ss(0.85, 1.0, r / R_) * ss(0.4, 0.7, fbm(Pp, 4.0, 2, seed=2103)) * 0.55)
    c = mixc(c, lin(150, 146, 132), ss(0.12, 0.06, r / R_) * 0.5)
    seam = (np.minimum(dist_periodic(ph, 2 * np.pi / 16) * r, 1.0) < 0.012) | \
           (np.min(np.abs((r / R_)[:, None] - np.array([0.30, 0.54, 0.78])[None]), 1) * R_ < 0.012)
    col[m] = c[m]
    gr = np.where(m & seam, 0.5, gr)
    m = M(FK.Z_DBACK)                                                    # the back skin: grey-white, darker joints, grime
    c = T(lin(196, 196, 188), 0.06, 0.10)
    c = mixc(c, lin(130, 126, 112), ss(0.5, 0.85, fbm(Pp, 4.0, 2, seed=2104)) * 0.35 + cav * 0.4)
    col[m] = c[m]
    gr = np.where(m & seam, 0.4, gr)
    for zz, base, seed in ((FK.Z_DPED, (220, 220, 212), 2105), (FK.Z_DHEAD, (214, 214, 206), 2106),
                           (FK.Z_DARM, (218, 218, 210), 2107), (FK.Z_DFEED, (224, 224, 216), 2108),
                           (FK.Z_DHUB, (216, 216, 208), 2109), (FK.Z_DRIM, (226, 226, 220), 2110),
                           (FK.Z_DSTRUT, (222, 222, 214), 2111)):
        m = M(zz)
        if not m.any():
            continue
        c = white_paint(Pp, T, cav, up, edge, seed, base)
        if zz == FK.Z_DPED:
            c = mixc(c, lin(120, 112, 96), ss(2.0, 1.2, z) * 0.35)                       # splash from the plinth
            c = mixc(c, ALGAE, np.clip(-Nn[:, 1], 0, 1) * ss(0.55, 0.8, fbm(Pp, 5.0, 2, seed=2112)) * 0.35)
        col[m] = c[m]
    m = M(FK.Z_DTRUSS)
    col[m] = mixc(galv(Pp, T, seed=2113), RUST_D, edge * 0.4)[m]
    for zz, seed in ((FK.Z_DAXLE, 2114), (FK.Z_DLADDER, 2116), (FK.Z_DLPOLE, 2118), (FK.Z_DSPOST, 2120)):
        m = M(zz)
        c = galv(Pp, T, seed=seed)
        if zz == FK.Z_DLADDER:
            c = mixc(c, lin(200, 202, 196), up * 0.35)
        col[m] = _foot(mixc(c, RUST, edge * 0.35), hz, Pl, 0.35, seed + 1)[m]
    m = M(FK.Z_DHORN)
    c = T(lin(170, 172, 168), 0.06, 0.10)
    throat = np.abs(((Pl - np.array(g['focus'])) @ ax) + 0.30) < 0.03
    c = np.where(throat[:, None], lin(30, 30, 30) * np.ones((n, 1), np.float32), c)
    col[m] = mixc(c, lin(90, 90, 86), cav * 0.4)[m]
    m = M(FK.Z_DBEACB)
    col[m] = mixc(T(lin(40, 40, 40), 0.06, 0.12), lin(100, 98, 92), up * 0.4)[m]
    m = M(FK.Z_DMOTOR)                                                   # the drives: dark blue-grey paint, oil
    c = T(lin(76, 84, 92), 0.08, 0.12)
    c = mixc(c, OIL, ss(0.6, 0.85, fbm(Pp * np.array([2, 2, 0.4], np.float32), 10.0, 2, seed=2122)) * 0.35)
    col[m] = mixc(c, lin(130, 132, 128), edge * 0.5)[m]
    # ---- the cabinet: light grey (RAL 7035) powder coat, grime low, a dark bay, the modules with their front strips
    m = M(FK.Z_DCAB)
    c = T(lin(182, 186, 180), 0.06, 0.08)
    c = mixc(c, lin(120, 120, 110), ss(0.6, 0.15, z) * 0.45 + cav * 0.35)
    c = mixc(c, lin(150, 140, 120), np.clip(Nn[:, 2], 0, 1) * 0.4)
    col[m] = mixc(c, RUST, edge * 0.2)[m]
    m = M(FK.Z_DCABIN)
    col[m] = T(lin(26, 26, 26), 0.04, 0.08)[m]
    m = M(FK.Z_DMOD)
    c = T(lin(60, 64, 68), 0.06, 0.10)
    strip = dist_periodic(x - 3.60, 0.12) < 0.012
    c = np.where((strip & (Nn[:, 1] > 0.8))[:, None], lin(150, 154, 156) * np.ones((n, 1), np.float32), c)
    col[m] = c[m]
    m = M(FK.Z_DPAD)
    col[m] = _foot(concrete(Pp, T, cav, up, 2124), hz, Pl, 0.15, 2125)[m]
    m = M(FK.Z_DPLINTH)
    c = concrete(Pp, T, cav, up, 2126)
    c = mixc(c, lin(78, 78, 72), ss(0.55, 0.80, fbm(Pp * np.array([1.5, 1.5, 0.12], np.float32), 6.0, 3, seed=2127)) * (up < 0.5) * 0.5)
    c = mixc(c, MOSS, up * ss(0.5, 0.72, fbm(Pp, 4.0, 3, seed=2128)) * 0.55)
    col[m] = _foot(c, hz, Pl, 0.4, 2129)[m]
    m = M(FK.Z_DDUCT)
    c = T(lin(64, 64, 62), 0.06, 0.10)
    col[m] = mixc(c, MUD, ss(0.3, 0.0, z) * 0.4 + up * 0.2)[m]
    m = M(FK.Z_DSBACK)
    col[m] = mixc(T(lin(124, 127, 122), 0.10, 0.14), lin(96, 90, 72), up * 0.55 + cav * 0.3)[m]
    m = M(FK.Z_DLHEAD)
    c = T(lin(132, 136, 136), 0.06, 0.10)
    col[m] = mixc(c, lin(80, 82, 78), up * 0.45)[m]
    m = M(FK.Z_DLFOOT)
    col[m] = _foot(concrete(Pp, T, cav, up, 2130), hz, Pl, 0.2, 2131)[m]
    m = M(FK.Z_DBOLT)
    col[m] = mixc(galv(Pp, T, seed=2132) * 0.85, RUST, 0.25 + 0.3 * fbm(Pp, 30.0, 2, seed=2133))[m]
    return col, gr


# ================================================================ the radome and the relay mast
def _corrugated_wall(Pp, Nn, T, cav, z, along, seed, base):
    """a shelter's corrugated steel wall: vertical ribs every 0.10 m (light and shade), dirt at the foot, rust streaks"""
    rib = 0.5 + 0.5 * np.cos(2 * np.pi * along / 0.10)
    c = T(lin(*base), 0.06, 0.10) * (0.86 + 0.20 * rib)[:, None]
    c = mixc(c, RUST, ss(0.62, 0.85, fbm(Pp * np.array([1, 1, 0.15], np.float32), 8.0, 3, seed=seed)) * ss(0.8, 2.6, z) * 0.35)
    c = mixc(c, lin(96, 90, 76), ss(0.45, 0.05, z) * 0.55)
    return mixc(c, lin(90, 92, 86), cav * 0.4)


def _towers(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 2201)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    for zz, seed in ((FK.Z_TLEG, 2202), (FK.Z_TBRACE, 2204), (FK.Z_TRLEG, 2206), (FK.Z_TRBRACE, 2208), (FK.Z_TPLATE, 2210),
                     (FK.Z_TLADDER, 2212), (FK.Z_TBRIDGE, 2214), (FK.Z_TFPOST, 2216), (FK.Z_TDOMERING, 2218)):
        m = M(zz)
        if not m.any():
            continue
        c = galv(Pp, T, seed=seed)
        c = mixc(c, lin(198, 200, 194), ss(0.62, 0.82, fbm(Pp * np.array([2, 2, 0.4], np.float32), 12.0, 2, seed=seed + 1)) * 0.3)
        c = mixc(c, RUST, np.clip(edge * 0.4 + ss(0.76, 0.9, fbm(Pp, 20.0, 2, seed=seed + 2)) * 0.4, 0, 0.7))
        if zz == FK.Z_TLADDER:
            c = mixc(c, lin(200, 202, 198), up * 0.35)
        col[m] = _foot(c, hz, Pl, 0.4, seed + 3)[m]
    for zz, seed in ((FK.Z_TFOOT, 2220), (FK.Z_TCONC, 2222)):
        m = M(zz)
        c = concrete(Pp, T, cav, up, seed)
        c = mixc(c, MOSS, up * ss(0.48, 0.70, fbm(Pp, 4.0, 3, seed=seed + 1)) * 0.6)
        col[m] = _foot(c, hz, Pl, 0.3, seed + 2)[m]
    m = M(FK.Z_TDECK)
    c = concrete(Pp, T, cav, up, 2224, base=(138, 138, 132))
    col[m] = mixc(c, lin(80, 80, 74), ss(0.5, 0.8, fbm(Pp * np.array([1, 1, 0.2], np.float32), 6.0, 2, seed=2225)) * (up < 0.5) * 0.45)[m]
    m = M(FK.Z_TGIRDER)                                                  # the deck's girders: grey-green paint, rusty
    c = T(lin(96, 108, 100), 0.08, 0.12)
    col[m] = mixc(c, RUST, np.clip(edge * 0.6 + ss(0.65, 0.85, fbm(Pp, 10.0, 2, seed=2226)) * 0.5, 0, 0.8))[m]
    # ---- the radome: white GRP panels in staggered rows, grey seams, streaks from the top, algae low on the north
    m = M(FK.Z_TDOME)
    rd = S.RADOME
    q = Pl - np.array([0.0, 0.0, rd['dome_c']])
    rr = np.linalg.norm(q, axis=1) + 1e-6
    psi = np.arcsin(np.clip(q[:, 2] / rr, -1, 1))
    th = np.mod(np.arctan2(q[:, 1], q[:, 0]), 2 * np.pi)
    row = np.floor((psi + 0.6) / 0.27)
    circ = 2 * np.pi * rd['dome_r'] * np.cos(psi)
    npan = np.maximum(np.round(circ / 1.6), 3)
    colp = th / (2 * np.pi) * npan + 0.5 * (row % 2)
    c = T(lin(230, 230, 224), 0.04, 0.06) * (0.95 + 0.06 * hash1(np.floor(colp) + row * 37, 61))[:, None]
    c = mixc(c, lin(170, 166, 150), ss(0.6, 0.85, fbm(np.stack([th * 3, psi * 5, np.zeros(n)], -1).astype(np.float32), 2.0, 3,
                                                       seed=2227)) * ss(0.9, 0.2, psi) * 0.35)
    c = mixc(c, ALGAE, ss(0.1, -0.5, psi) * np.clip(-q[:, 1] / rr, 0, 1) * ss(0.4, 0.7, fbm(Pp, 4.0, 2, seed=2228)) * 0.5)
    seam = (dist_periodic(colp, 1.0) * circ / npan < 0.012) | (dist_periodic(psi + 0.6, 0.27) * rd['dome_r'] < 0.012)
    col[m] = c[m]
    gr = np.where(m & seam, 0.6, gr)
    m = M(FK.Z_TBEACB)
    col[m] = mixc(T(lin(40, 40, 40), 0.06, 0.12), lin(100, 98, 92), up * 0.4)[m]
    m = M(FK.Z_THUT)                                                     # the shelters' walls: light grey corrugated
    along = np.where(np.abs(Nn[:, 0]) > np.abs(Nn[:, 1]), y, x)
    col[m] = _corrugated_wall(Pp, Nn, T, cav, z, along, 2229, (176, 180, 174))[m]
    m = M(FK.Z_THUTROOF)
    c = galv(Pp, T, seed=2230)
    col[m] = mixc(c, NEEDLES, up * ss(0.62, 0.84, fbm(Pp, 10.0, 2, seed=2231)) * 0.4)[m]
    m = M(FK.Z_THUTDOOR)                                                 # the olive door, worn round the handle
    c = T(lin(94, 100, 72), 0.06, 0.10)
    c = mixc(c, lin(140, 140, 120), np.clip(edge * 0.6, 0, 1))
    col[m] = mixc(c, lin(70, 70, 56), ss(0.5, 0.0, z) * 0.4)[m]
    m = M(FK.Z_TAC)
    c = T(lin(214, 212, 200), 0.05, 0.08)
    fan = (up > 0.9) & (dist_periodic(x, 0.04) < 0.008)                 # the grille's bars on top
    c = np.where(fan[:, None], lin(70, 70, 68) * np.ones((n, 1), np.float32), c)
    col[m] = mixc(c, lin(140, 130, 110), cav * 0.4)[m]
    m = M(FK.Z_TCABLE)
    col[m] = mixc(T(lin(30, 30, 30), 0.06, 0.12), lin(80, 80, 78), up * 0.3)[m]
    m = M(FK.Z_TDRUM)                                                    # the microwave drum: grey body, the white cover
    c = np.where((Nn[:, 0] > 0.6)[:, None], T(lin(222, 222, 214), 0.04, 0.08), T(lin(160, 164, 164), 0.06, 0.10))
    col[m] = mixc(c, lin(110, 110, 104), cav * 0.4 + run_m(Pp) * 0.25)[m]
    m = M(FK.Z_TPANEL)
    c = T(lin(224, 224, 218), 0.04, 0.08)
    label = (np.abs(z - 39.35) < 0.04) & (np.abs(Nn[:, 2]) < 0.3)
    c = np.where(label[:, None], lin(60, 80, 130) * np.ones((n, 1), np.float32), c)
    col[m] = mixc(c, lin(150, 146, 130), ss(0.6, 0.85, fbm(Pp, 4.0, 2, seed=2232)) * 0.3)[m]
    m = M(FK.Z_TSBACK)
    col[m] = mixc(T(lin(124, 127, 122), 0.10, 0.14), lin(96, 90, 72), up * 0.55 + cav * 0.3)[m]
    m = M(FK.Z_TSTEEL)
    col[m] = steel_black(Pp, T, edge, seed=2233)[m]
    return col, gr


# ================================================================ the weather station
def _meteo(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 2301)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    for zz, seed in ((FK.Z_MPICKET, 2302), (FK.Z_MRAIL, 2305), (FK.Z_MPOST, 2308)):      # white paint going grey at the foot
        m = M(zz)
        along = np.where(np.abs(x) > 5.9, y, x)
        pk = np.floor(along / 0.16)
        c = T(lin(226, 226, 218), 0.06, 0.10) * (0.95 + 0.07 * hash1(pk, seed))[:, None]
        peel = ss(0.62, 0.80, fbm(Pp * np.array([1, 1, 0.3], np.float32), 12.0, 3, seed=seed)) * (0.35 + 0.65 * ss(0.5, 0.05, z))
        c = mixc(c, lin(124, 118, 106), peel * 0.8)
        c = mixc(c, ALGAE, ss(0.35, 0.0, z) * ss(0.45, 0.75, fbm(Pp, 6.0, 2, seed=seed + 1)) * 0.5)
        c = mixc(c, lin(110, 106, 96), cav * 0.4)
        col[m] = c[m]
    for zz, seed in ((FK.Z_MSCREEN, 2310), (FK.Z_MLOUVRE, 2312), (FK.Z_MLEG, 2314), (FK.Z_MLOGGER, 2316)):
        m = M(zz)
        c = T(lin(232, 232, 226), 0.04, 0.08)
        c = mixc(c, lin(150, 146, 132), cav * 0.55 + ss(0.65, 0.85, fbm(Pp, 5.0, 2, seed=seed)) * 0.2)
        if zz == FK.Z_MLEG:
            c = _foot(c, hz, Pl, 0.3, seed + 1)
        if zz == FK.Z_MLOGGER:                                           # the logger's label
            lab = (np.abs(z - 1.25) < 0.05) & (Nn[:, 1] < -0.8)
            c = np.where(lab[:, None], lin(40, 70, 120) * np.ones((n, 1), np.float32), c)
        col[m] = c[m]
    for zz, seed in ((FK.Z_MMAST, 2318), (FK.Z_MINSTR, 2320), (FK.Z_MGAUGE, 2322)):
        m = M(zz)
        c = galv(Pp, T, seed=seed)
        if zz == FK.Z_MGAUGE:
            c = mixc(c, lin(210, 212, 208), 0.25 * np.ones(n, np.float32))
        col[m] = _foot(c, hz, Pl, 0.25, seed + 1)[m]
    m = M(FK.Z_MVANE)
    col[m] = mixc(T(lin(186, 50, 36), 0.06, 0.10), lin(200, 120, 100), ss(0.5, 0.9, fbm(Pp, 6.0, 2, seed=2324)) * 0.3)[m]
    m = M(FK.Z_MSOLAR)                                                   # cells, the grid, the aluminium frame
    c = T(lin(36, 46, 78), 0.04, 0.06)
    grid_ = (dist_periodic(x * 0.766 + z * 0.643, 0.156) < 0.006) | (dist_periodic(y - 0.0, 0.156) < 0.006)
    c = np.where(grid_[:, None], lin(130, 136, 150) * np.ones((n, 1), np.float32), c)
    c = np.where((np.abs(Nn[:, 2]) < 0.4)[:, None], lin(170, 172, 170) * np.ones((n, 1), np.float32), c)
    col[m] = c[m]
    m = M(FK.Z_MSTAKE)                                                   # red and white every 0.1 m, black every 0.5
    band = np.floor(z / 0.1)
    c = np.where((band % 2 == 0)[:, None], lin(196, 50, 40) * np.ones((n, 1), np.float32), lin(230, 230, 224) * np.ones((n, 1), np.float32))
    c = np.where((dist_periodic(z, 0.5) < 0.012)[:, None], lin(30, 30, 30) * np.ones((n, 1), np.float32), c)
    col[m] = _foot(c, hz, Pl, 0.2, 2325)[m]
    m = M(FK.Z_MGUY)
    col[m] = mixc(T(lin(118, 122, 122), 0.06, 0.10), RUST_D, 0.15 * np.ones(n, np.float32))[m]
    m = M(FK.Z_MCONC)
    col[m] = _foot(concrete(Pp, T, cav, up, 2326), hz, Pl, 0.2, 2327)[m]
    m = M(FK.Z_MSBACK)
    col[m] = mixc(T(lin(124, 127, 122), 0.10, 0.14), lin(96, 90, 72), up * 0.55 + cav * 0.3)[m]
    return col, gr


# ================================================================ the lookout tower
def _lookout(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 2401)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    for zz, seed in ((FK.Z_LLEG, 2402), (FK.Z_LBRACE, 2405), (FK.Z_LSTRING, 2408), (FK.Z_LRAIL, 2411), (FK.Z_LPLATE, 2414)):
        m = M(zz)
        c = galv(Pp, T, seed=seed)
        c = mixc(c, RUST, np.clip(edge * 0.5 + ss(0.72, 0.88, fbm(Pp, 16.0, 2, seed=seed + 1)) * 0.45, 0, 0.8))
        if zz == FK.Z_LRAIL:
            c = mixc(c, lin(200, 202, 196), up * 0.4)
        col[m] = _foot(c, hz, Pl, 0.4, seed + 2)[m]
    m = M(FK.Z_LFOOT)
    c = concrete(Pp, T, cav, up, 2417)
    col[m] = _foot(mixc(c, MOSS, up * ss(0.48, 0.7, fbm(Pp, 4.0, 3, seed=2418)) * 0.6), hz, Pl, 0.3, 2419)[m]
    m = M(FK.Z_LTREAD)                                                   # steel grating: a grid of holes, worn bright paths
    c = T(lin(112, 116, 112), 0.06, 0.10)
    holes = (dist_periodic(x, 0.033) > 0.008) & (dist_periodic(y, 0.033) > 0.008) & (up > 0.8)
    c = np.where(holes[:, None], lin(40, 40, 38) * np.ones((n, 1), np.float32), c)
    c = mixc(c, RUST, ss(0.6, 0.85, fbm(Pp, 12.0, 2, seed=2420)) * 0.45 + edge * 0.3)
    col[m] = c[m]
    m = M(FK.Z_LFLOOR)
    bi = np.floor(y / 0.14)
    c = weathered(Pp, Nn, T, cav, 0, 2421) * (0.88 + 0.2 * hash1(bi, 71))[:, None]
    col[m] = mixc(c, lin(150, 140, 120), np.clip(Nn[:, 2], 0, 1) * np.exp(-((np.hypot(x, y) - 1.0) / 0.6) ** 2) * 0.3)[m]
    gr = np.where(m & (dist_periodic(y, 0.14) < 0.004) & (up > 0.8), 0.5, gr)
    m = M(FK.Z_LBOARD)                                                   # dark stain, vertical boards
    along = np.where(np.abs(Nn[:, 0]) > np.abs(Nn[:, 1]), y, x)
    bi = np.floor(along / 0.15)
    c = T(lin(64, 50, 38), 0.10, 0.14) * (0.88 + 0.22 * hash1(bi, 72))[:, None]
    c = mixc(c, lin(108, 98, 84), ss(0.60, 0.82, fbm(Pp * np.array([1, 1, 0.3], np.float32), 12.0, 3, seed=2422)) * 0.6)
    col[m] = mixc(c, lin(30, 24, 20), cav * 0.4)[m]
    gr = np.where(m & (dist_periodic(along, 0.15) < 0.004), 0.6, gr)
    m = M(FK.Z_LPOST)
    col[m] = trim_white(Pp, T, edge, cav, z, np.zeros(n, np.float32), z0=22.0)[m]
    m = M(FK.Z_LROOF)                                                    # corrugated galvanised: ribs down the slope, rust
    c = galv(Pp, T, seed=2423)
    rib = 0.5 + 0.5 * np.cos(2 * np.pi * (np.where(np.abs(x) > np.abs(y), y, x)) / 0.076)
    c = c * (0.86 + 0.18 * rib)[:, None]
    c = mixc(c, RUST, ss(0.55, 0.82, fbm(Pp * np.array([0.4, 0.4, 1], np.float32), 7.0, 3, seed=2424)) * 0.6)
    col[m] = c[m]
    m = M(FK.Z_LROOFIN)
    col[m] = mixc(weathered(Pp, Nn, T, cav, 0, 2425), lin(70, 56, 42), 0.4 * np.ones(n, np.float32))[m]
    m = M(FK.Z_LROD)
    c = T(lin(132, 92, 60), 0.08, 0.14)
    col[m] = mixc(c, lin(96, 140, 116), ss(0.5, 0.8, fbm(Pp, 8.0, 2, seed=2426)) * 0.5)[m]
    m = M(FK.Z_LTABLE)
    c = T(lin(118, 86, 54), 0.10, 0.14)
    col[m] = mixc(c, lin(160, 130, 90), np.clip(Nn[:, 2], 0, 1) * 0.3)[m]
    m = M(FK.Z_LSBACK)
    col[m] = mixc(T(lin(124, 127, 122), 0.10, 0.14), lin(96, 90, 72), up * 0.55 + cav * 0.3)[m]
    return col, gr


# ================================================================ the chapel
def _chapel(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 2501)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    c_ = S.CHAPEL
    # ---- the lime plaster: off-white, grey streaks from the eaves and under the sills, damp and green at the foot,
    # flaked in patches down to the stone
    m = M(FK.Z_CWALL)
    c = T(lin(226, 222, 208), 0.06, 0.10)
    streak = ss(0.55, 0.80, fbm(Pp * np.array([1.4, 1.4, 0.10], np.float32), 6.0, 3, seed=2502))
    c = mixc(c, lin(150, 148, 136), streak * ss(1.5, 3.4, z) * 0.45)
    for ya, yb in c_['windows']:
        under = (np.abs(np.abs(x) - c_['out'][0]) < 0.02) & (y > ya) & (y < yb) & (z < c_['win_z'][0]) & (z > c_['win_z'][0] - 1.0)
        c = mixc(c, lin(140, 136, 124), under * (1 - (c_['win_z'][0] - z)) * 0.6)
    c = mixc(c, lin(150, 150, 120), ss(0.9, 0.2, z) * 0.45)
    c = mixc(c, ALGAE, ss(0.6, 0.1, z) * ss(0.45, 0.72, fbm(Pp, 5.0, 2, seed=2503)) * 0.5)
    flake = ss(0.74, 0.80, fbm(Pp, 3.0, 3, seed=2504)) * ss(0.3, 1.2, z)
    c = mixc(c, lin(128, 118, 104), flake * 0.85)
    col[m] = c[m]
    m = M(FK.Z_CWALLIN)
    c = T(lin(222, 218, 202), 0.04, 0.08)
    c = mixc(c, lin(170, 160, 130), ss(0.6, 0.85, fbm(Pp, 3.0, 2, seed=2505)) * 0.35 + ss(0.8, 0.1, z) * 0.3)
    col[m] = mixc(c, lin(120, 112, 96), cav * 0.4)[m]
    m = M(FK.Z_CPLINTH)
    col[m] = stone(Pp, Nn, T, cav, up, hz, 2506)[m]
    # ---- the shingles (rows of 0.12 m down the slope, one tone each, grey with moss), the spire's darker
    for zz, seed, mossy in ((FK.Z_CROOF, 2507, 0.5), (FK.Z_CSPIRE, 2510, 0.7)):
        m = M(zz)
        if not m.any():
            continue
        row = np.floor(z / 0.07)
        shg = np.floor((np.where(np.abs(Nn[:, 0]) > np.abs(Nn[:, 1]), y, x) + 0.06 * (row % 2)) / 0.12)
        c = T(lin(104, 94, 82), 0.12, 0.16) * (0.80 + 0.32 * hash1(row * 131 + shg, seed))[:, None]
        c = mixc(c, lin(140, 136, 126), ss(0.5, 0.85, fbm(Pp, 3.0, 2, seed=seed + 1)) * 0.35)
        c = mixc(c, MOSS, ss(0.50, 0.72, fbm(Pp, 4.0, 3, seed=seed + 2)) * mossy)
        c = mixc(c, LICHEN, ss(0.72, 0.86, fbm(Pp, 9.0, 2, seed=seed + 3)) * 0.3)
        col[m] = c[m]
        gr = np.where(m & (dist_periodic(z, 0.07) < 0.004), 0.7, gr)
    for zz, base, seed in ((FK.Z_CROOFIN, (70, 56, 42), 2513), (FK.Z_CBARGE, (64, 50, 38), 2515), (FK.Z_CTURRET, (68, 54, 40), 2517),
                           (FK.Z_CCEIL, (84, 66, 48), 2519), (FK.Z_CSIGN, (66, 50, 36), 2521), (FK.Z_CFRAME, (60, 46, 34), 2523)):
        m = M(zz)
        if not m.any():
            continue
        c = T(lin(*base), 0.10, 0.14)
        c = mixc(c, lin(112, 100, 84), ss(0.60, 0.82, fbm(Pp * np.array([1, 1, 0.3], np.float32), 12.0, 3, seed=seed)) * 0.5)
        if zz in (FK.Z_CTURRET, FK.Z_CSIGN):
            c = mixc(c, LICHEN, ss(0.7, 0.86, fbm(Pp, 8.0, 2, seed=seed + 1)) * 0.35)
        col[m] = mixc(c, lin(30, 24, 20), cav * 0.4)[m]
    m = M(FK.Z_CDOOR)                                                    # vertical planks, the varnish worn
    bi = np.floor(x / 0.16)
    c = T(lin(84, 60, 40), 0.10, 0.14) * (0.88 + 0.2 * hash1(bi, 81))[:, None]
    c = mixc(c, lin(130, 112, 88), ss(0.55, 0.82, fbm(Pp * np.array([1, 1, 0.3], np.float32), 10.0, 3, seed=2525)) * 0.5)
    col[m] = c[m]
    gr = np.where(m & (dist_periodic(x, 0.16) < 0.004), 0.6, gr)
    m = M(FK.Z_CCROSS)
    col[m] = steel_black(Pp, T, edge, seed=2526)[m]
    m = M(FK.Z_CIRON)
    col[m] = steel_black(Pp, T, edge, seed=2527)[m]
    m = M(FK.Z_CFLOOR)                                                   # stone flags 0.4 m, the aisle worn
    fi, fj = np.floor(x / 0.4), np.floor(y / 0.4)
    c = T(lin(150, 146, 134), 0.10, 0.14) * (0.86 + 0.2 * hash1(fi * 17 + fj, 82))[:, None]
    c = mixc(c, lin(176, 170, 156), np.exp(-(x / 0.35) ** 2) * 0.35)
    col[m] = mixc(c, lin(80, 76, 66), cav * 0.4)[m]
    gr = np.where(m & ((dist_periodic(x, 0.4) < 0.006) | (dist_periodic(y, 0.4) < 0.006)), 0.6, gr)
    m = M(FK.Z_CPEW)
    c = T(lin(96, 70, 46), 0.10, 0.14)
    col[m] = mixc(c, lin(140, 112, 80), np.clip(Nn[:, 2], 0, 1) * 0.35)[m]
    m = M(FK.Z_CALTAR)
    c = T(lin(196, 190, 174), 0.06, 0.10)
    col[m] = mixc(c, lin(140, 132, 116), ss(0.6, 0.85, fbm(Pp, 20.0, 1, seed=2528)) * 0.3 + cav * 0.3)[m]
    m = M(FK.Z_CCLOTH)                                                   # linen, a red border embroidered with gold
    c = T(lin(226, 218, 196), 0.04, 0.08)
    ax0, ax1, ay0, ay1, az = c_['cloth']
    edge_d = np.minimum(np.minimum(np.abs(x - ax0), np.abs(x - ax1)), np.abs(z - (az - 0.45)))
    border = (edge_d < 0.06) & (y < ay0 + 0.02)
    c = np.where(border[:, None], lin(150, 30, 26) * np.ones((n, 1), np.float32), c)
    c = np.where((border & (dist_periodic(x, 0.05) < 0.01))[:, None], lin(200, 170, 80) * np.ones((n, 1), np.float32), c)
    col[m] = mixc(c, lin(140, 130, 110), cav * 0.4)[m]
    m = M(FK.Z_CCANDLE)
    col[m] = mixc(T(lin(232, 224, 200), 0.04, 0.08), lin(170, 160, 130), cav * 0.4)[m]
    m = M(FK.Z_CSTICK)
    c = T(lin(176, 140, 70), 0.06, 0.12)
    col[m] = mixc(c, lin(90, 76, 46), ss(0.5, 0.8, fbm(Pp, 40.0, 2, seed=2529)) * 0.4)[m]
    m = M(FK.Z_CICON)
    col[m] = mixc(T(lin(74, 52, 34), 0.08, 0.12), lin(120, 96, 66), edge * 0.5)[m]
    m = M(FK.Z_CGRAVE)                                                   # the mounds: moss, needles, a few cranberries
    c = T(lin(74, 82, 48), 0.18, 0.22)
    c = mixc(c, NEEDLES, ss(0.45, 0.70, fbm(Pp, 6.0, 2, seed=2530)) * 0.6)
    c = mixc(c, lin(140, 30, 30), ss(0.86, 0.92, fbm(Pp, 40.0, 1, seed=2531)) * 0.8)
    col[m] = mixc(c, SOIL, ss(0.05, -0.05, hz) * 0.5)[m]
    m = M(FK.Z_CBELL)
    col[m] = T(lin(150, 120, 60), 0.08, 0.12)[m]
    return col, gr


# ================================================================ the pump house, the cabin, the campsite
def _bricks(Pp, Nn, T, cav, z, seed):
    along = np.where(np.abs(Nn[:, 0]) > np.abs(Nn[:, 1]), Pp[:, 1], Pp[:, 0])
    course = np.floor(z / 0.0833)
    bi = np.floor((along + 0.125 * (course % 2)) / 0.25)
    c = T(lin(150, 72, 52), 0.08, 0.12) * (0.84 + 0.26 * hash1(course * 97 + bi, seed))[:, None]
    mortar = (dist_periodic(z, 0.0833) < 0.007) | (dist_periodic(along + 0.125 * (course % 2), 0.25) < 0.007)
    c = np.where(mortar[:, None], lin(176, 170, 156) * np.ones((len(z), 1), np.float32), c)
    c = mixc(c, lin(214, 210, 196), ss(0.72, 0.86, fbm(Pp, 6.0, 2, seed=seed + 1)) * ss(1.0, 0.2, z) * 0.45)   # efflorescence
    c = mixc(c, ALGAE, ss(0.6, 0.2, z) * ss(0.45, 0.7, fbm(Pp, 5.0, 2, seed=seed + 2)) * 0.45)
    return mixc(c, lin(70, 50, 40), cav * 0.4), mortar


def _small(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 2601)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    # ---- the pump house
    m = M(FK.Z_PBRICK)
    c, mortar = _bricks(Pl, Nn, T, cav, z, 2602)
    col[m] = c[m]
    gr = np.where(m & mortar, 0.4, gr)
    m = M(FK.Z_PPLASTER)
    c = T(lin(206, 202, 186), 0.06, 0.10)
    c = mixc(c, lin(150, 140, 110), ss(0.6, 0.85, fbm(Pp, 3.0, 2, seed=2603)) * 0.3 + ss(0.8, 0.25, z) * 0.35)
    col[m] = mixc(c, lin(110, 104, 90), cav * 0.4)[m]
    for zz, seed in ((FK.Z_PBASE, 2604), (FK.Z_PFLOOR, 2606)):
        m = M(zz)
        c = concrete(Pp, T, cav, up, seed, base=(144, 142, 134))
        if zz == FK.Z_PFLOOR:
            c = mixc(c, OIL, np.exp(-(((x - 0.8) / 0.6) ** 2 + ((y - 0.3) / 0.5) ** 2)) * 0.5)
        col[m] = _foot(c, hz, Pl, 0.15, seed + 1)[m]
    m = M(FK.Z_PROOF)                                                    # bitumen felt, laps every 1 m, needles
    c = T(lin(46, 46, 46), 0.06, 0.12)
    c = mixc(c, lin(90, 88, 82), ss(0.6, 0.85, fbm(Pp, 6.0, 2, seed=2608)) * 0.35)
    c = mixc(c, NEEDLES, up * ss(0.62, 0.84, fbm(Pp, 10.0, 2, seed=2609)) * 0.45)
    c = mixc(c, MOSS, up * ss(0.66, 0.84, fbm(Pp, 4.0, 2, seed=2610)) * 0.4)
    col[m] = c[m]
    gr = np.where(m & (dist_periodic(x, 1.0) < 0.006) & (up > 0.8), 0.5, gr)
    for zz, seed in ((FK.Z_PFLASH, 2611), (FK.Z_PBOX, 2613)):
        m = M(zz)
        c = galv(Pp, T, seed=seed)
        col[m] = mixc(c, RUST, run_m(Pp) * 0.4 + edge * 0.3)[m]
    m = M(FK.Z_PDOOR)                                                    # grey steel door, rust creeping up from the foot
    c = T(lin(118, 124, 120), 0.06, 0.10)
    c = mixc(c, RUST, np.clip(ss(0.9, 0.2, z) * ss(0.4, 0.75, fbm(Pp, 8.0, 2, seed=2615)) + edge * 0.4, 0, 0.85))
    col[m] = c[m]
    m = M(FK.Z_PPUMP)
    c = T(lin(40, 74, 136), 0.06, 0.10)
    c = mixc(c, OIL, ss(0.55, 0.85, fbm(Pp * np.array([2, 2, 0.5], np.float32), 10.0, 2, seed=2616)) * 0.4)
    col[m] = mixc(c, lin(140, 140, 136), edge * 0.5)[m]
    m = M(FK.Z_PMOTOR)
    c = T(lin(112, 118, 114), 0.06, 0.10)
    col[m] = mixc(c, OIL, ss(0.6, 0.85, fbm(Pp, 10.0, 2, seed=2617)) * 0.35 + cav * 0.3)[m]
    m = M(FK.Z_PPIPE)
    c = T(lin(104, 60, 36), 0.14, 0.2)
    col[m] = mixc(c, lin(60, 36, 24), ss(0.5, 0.8, fbm(Pp, 30.0, 2, seed=2618)) * 0.5 + cav * 0.3)[m]
    m = M(FK.Z_PSBACK)
    col[m] = mixc(T(lin(124, 127, 122), 0.10, 0.14), lin(96, 90, 72), up * 0.55 + cav * 0.3)[m]
    # ---- the cabin
    m = M(FK.Z_KLOG)                                                     # debarked spruce, grey on the weather side
    c = T(lin(120, 100, 78), 0.12, 0.16)
    c = mixc(c, lin(132, 126, 114), ss(0.4, 0.8, fbm(Pp, 3.0, 2, seed=2620)) * 0.5)
    c = mixc(c, lin(60, 48, 36), ss(0.66, 0.80, fbm(Pp * np.array([0.25, 0.25, 6], np.float32), 6.0, 2, seed=2621)) * 0.5)
    c = mixc(c, lin(76, 60, 44), ss(0.7, 0.86, fbm(Pp, 6.0, 2, seed=2622)) * 0.4)                       # bark left on
    c = mixc(c, lin(196, 186, 160), cav * ss(0.5, 0.75, fbm(Pp, 20.0, 1, seed=2623)) * 0.5)             # chinking
    col[m] = _foot(c, hz, Pl, 0.5, 2624)[m]
    m = M(FK.Z_KCHINK)                                                   # clay and moss in the seams
    c = T(lin(146, 136, 112), 0.10, 0.14)
    c = mixc(c, MOSS, ss(0.55, 0.80, fbm(Pp, 9.0, 2, seed=2645)) * 0.45)
    col[m] = mixc(c, lin(70, 62, 50), ss(0.6, 0.85, fbm(Pp, 20.0, 1, seed=2646)) * 0.4)[m]
    for zz, seed in ((FK.Z_KLOGEND, 2625), (FK.Z_KWOODEND, 2627)):
        m = M(zz)
        col[m] = (end_grain(Pp, T, n_hi, seed) * 0.75 + lin(120, 112, 96) * 0.25)[m]
    m = M(FK.Z_KWOOD)
    col[m] = _foot(bark(Pp, T, up, 2629), hz, Pl, 0.25, 2630)[m]
    m = M(FK.Z_KROOF)
    c = T(lin(44, 44, 44), 0.06, 0.12)
    c = mixc(c, lin(90, 88, 82), ss(0.6, 0.85, fbm(Pp, 6.0, 2, seed=2631)) * 0.35)
    c = mixc(c, MOSS, ss(0.55, 0.78, fbm(Pp, 4.0, 3, seed=2632)) * 0.55)
    c = mixc(c, NEEDLES, ss(0.66, 0.86, fbm(Pp, 10.0, 2, seed=2633)) * 0.45)
    col[m] = c[m]
    gr = np.where(m & (dist_periodic(x, 0.9) < 0.006), 0.5, gr)
    for zz, base, seed in ((FK.Z_KBOARD, (66, 52, 40), 2634), (FK.Z_KDOOR, (74, 56, 40), 2636)):
        m = M(zz)
        along = np.where(np.abs(Nn[:, 0]) > np.abs(Nn[:, 1]), y, x)
        bi = np.floor(along / 0.15)
        c = T(lin(*base), 0.10, 0.14) * (0.88 + 0.2 * hash1(bi, seed))[:, None]
        c = mixc(c, lin(112, 100, 84), ss(0.60, 0.82, fbm(Pp * np.array([1, 1, 0.3], np.float32), 12.0, 3, seed=seed)) * 0.5)
        col[m] = mixc(c, lin(30, 24, 20), cav * 0.4)[m]
    m = M(FK.Z_KFRAME)
    col[m] = trim_white(Pp, T, edge, cav, z, np.zeros(n, np.float32), z0=0.0)[m]
    m = M(FK.Z_KFLOOR)
    bi = np.floor(y / 0.16)
    c = T(lin(132, 108, 78), 0.12, 0.16) * (0.86 + 0.22 * hash1(bi, 91))[:, None]
    c = mixc(c, lin(90, 78, 60), np.exp(-(((x + 1.0) / 0.5) ** 2 + ((y + 1.4) / 0.8) ** 2)) * 0.4)
    col[m] = mixc(c, lin(70, 56, 40), cav * 0.4)[m]
    gr = np.where(m & (dist_periodic(y, 0.16) < 0.004) & (up > 0.8), 0.5, gr)
    m = M(FK.Z_KDECK)
    c = weathered(Pp, Nn, T, cav, 0, 2638)
    col[m] = mixc(c, MUD, np.exp(-(x / 0.4) ** 2) * 0.35)[m]
    m = M(FK.Z_KSTOVE)
    col[m] = steel_black(Pp, T, edge, seed=2639)[m]
    m = M(FK.Z_KPIPE)
    c = T(lin(100, 58, 34), 0.14, 0.2)
    col[m] = mixc(c, lin(40, 34, 30), ss(0.5, 0.8, fbm(Pp, 20.0, 2, seed=2640)) * 0.5)[m]
    m = M(FK.Z_KFURN)
    c = T(lin(140, 108, 70), 0.12, 0.16)
    col[m] = mixc(c, lin(90, 70, 50), cav * 0.5 + ss(0.65, 0.85, fbm(Pp, 6.0, 2, seed=2641)) * 0.3)[m]
    m = M(FK.Z_KMATT)
    tick = dist_periodic(y, 0.032) < 0.007
    c = np.where(tick[:, None], lin(72, 84, 112), lin(198, 192, 174)) * (0.9 + 0.12 * n_hi)[:, None]
    c = mixc(c, lin(160, 140, 96), ss(0.62, 0.80, fbm(Pp, 4.0, 2, seed=2642)) * 0.5)
    col[m] = mixc(c, lin(90, 84, 74), cav * 0.4)[m]
    # ---- the campsite
    m = M(FK.Z_XTENT)
    c = T(lin(216, 104, 38), 0.08, 0.12)
    c = mixc(c, lin(226, 170, 120), ss(0.5, 0.85, fbm(Pp, 3.0, 2, seed=2643)) * 0.3 * np.clip(Nn[:, 2], 0, 1))
    c = mixc(c, lin(110, 60, 30), cav * 0.5 + ss(0.06, 0.0, z) * 0.4)
    c = mixc(c, NEEDLES, ss(0.66, 0.86, fbm(Pp, 12.0, 2, seed=2644)) * 0.45 * np.clip(Nn[:, 2], 0, 1))
    col[m] = c[m]
    for zz, seed in ((FK.Z_XPOLE, 2645), (FK.Z_XCFRAME, 2646), (FK.Z_XPOT, 2647)):
        m = M(zz)
        c = T(lin(170, 172, 170), 0.06, 0.10)
        if zz == FK.Z_XPOT:
            c = mixc(c, lin(30, 28, 26), ss(0.35, 0.18, z) * 0.85)
        col[m] = mixc(c, lin(90, 90, 86), cav * 0.3)[m]
    m = M(FK.Z_XSTONE)
    c = stone(Pp, Nn, T, cav, up, hz, 2648)
    fx, fy, fr = S.CAMP['fire']
    inner = np.hypot(x - fx, y - fy) < fr
    col[m] = np.where(inner[:, None], mixc(c, lin(30, 28, 26), 0.6 * np.ones(n, np.float32)), c)[m]
    m = M(FK.Z_XASH)
    c = T(lin(70, 68, 64), 0.12, 0.18)
    col[m] = mixc(c, lin(20, 18, 16), ss(0.5, 0.8, fbm(Pp, 30.0, 1, seed=2649)) * 0.6)[m]
    m = M(FK.Z_XCHAR)
    c = T(lin(30, 26, 22), 0.08, 0.14)
    cracks = dist_periodic(np.hypot(x - fx, y - fy), 0.025) < 0.004
    c = np.where(cracks[:, None], lin(10, 9, 8) * np.ones((n, 1), np.float32), c)
    col[m] = mixc(c, lin(120, 116, 108), up * ss(0.5, 0.8, fbm(Pp, 20.0, 1, seed=2650)) * 0.5)[m]
    m = M(FK.Z_XCHAIR)
    col[m] = mixc(T(lin(40, 70, 132), 0.06, 0.10), lin(120, 140, 170), ss(0.5, 0.85, fbm(Pp, 3.0, 2, seed=2651)) * 0.35)[m]
    m = M(FK.Z_XPACK)
    c = T(lin(200, 90, 34), 0.08, 0.12)
    col[m] = mixc(c, lin(90, 60, 40), cav * 0.5 + ss(0.15, 0.0, z) * 0.4)[m]
    m = M(FK.Z_XROLL)
    col[m] = mixc(T(lin(110, 110, 104), 0.08, 0.12), lin(70, 70, 66), cav * 0.4)[m]
    m = M(FK.Z_XBOTTLE)
    c = T(lin(36, 58, 32), 0.06, 0.10)
    col[m] = mixc(c, lin(120, 150, 110), np.clip(Nn[:, 2], 0, 1) * 0.35)[m]
    m = M(FK.Z_XTORCH)
    col[m] = mixc(T(lin(36, 36, 36), 0.06, 0.10), lin(90, 90, 86), edge * 0.4)[m]
    m = M(FK.Z_XMUG)
    c = T(lin(214, 210, 200), 0.04, 0.08)
    rim = z > 0.08
    c = np.where(rim[:, None], lin(40, 70, 130) * np.ones((n, 1), np.float32), c)
    col[m] = mixc(c, lin(40, 40, 40), ss(0.75, 0.88, fbm(Pp, 40.0, 1, seed=2652)) * 0.7)[m]
    return col, gr
