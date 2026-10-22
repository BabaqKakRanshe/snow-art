"""Painters for the garage's atlases (psxbake): paint_gar(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n]).
The shed's wear language on the garage: the trapezoidal sheet in the station's grey-green (a tone per sheet, the laps,
rows of screws in the valleys with rust halos and runs, chalky high up and on the south / west, the cut edges and the
foot rusting, splash and algae low on the north, dark runs under the scuppers), darker trims chipped to primer, the
concrete plinth (splash, moss, lime), the felt roof (slate granules, laps, moss and needles, dried puddles); inside the
grey-white liner trays (joints, screws, tyre marks and scuffs low, hand marks by the door, condensation runs from the
deck, oil spatter by the bench), the galvanised deck, the beams in red-oxide primer, the power-floated floor (saw cuts,
oil under the quad, the drums and the bench, tyre tracks and mud from the gate, the yellow parking bay worn through,
needles blown in, damp round the drain), the apron (cracks, tracks, oil, weeds at its edges); the gate and the side door
in the grey-green (the gate repainted a shade darker), the frames dark; the yellow spill pallet. Every other zone (the
furniture, the openings' hardware, the fixtures) is the main building's painter, its room table set to the hall.
Building frame: x east, y north, z up; floor 0.0, ground -0.10."""
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline, seg_dist
from psxbake import lin, boards, hash1
import gen_kit as K
import main_spec as MSP
import main_paint as MP
import gar_spec as S
import gar_kit as GK

# ---------------------------------------------------------------- the main building's painters see the hall
MSP.GROUND = S.GROUND
_ROOM = dict(S.ROOM, c=GK.LINER_TOP, walls=dict(bare=True), layer=1)
MP.ROOMS = [('Garage', _ROOM)]
MP.RBOX = np.array([(_ROOM['x0'], _ROOM['y0'], _ROOM['f'] - 0.02, _ROOM['x1'], _ROOM['y1'], _ROOM['c'] + 0.02)],
                   np.float32)
GATE_C = ((S.GATE['u'][0] + S.GATE['u'][1]) / 2, -S.YO + 0.1)
SIDE_C = (S.XO - 0.1, (S.SIDE['u'][0] + S.SIDE['u'][1]) / 2)
MP.DOORPTS = {'Garage': [(GATE_C[0], GATE_C[1], 0.0), (SIDE_C[0], SIDE_C[1], 0.0)]}

GREEN, GREEN_FADE, GREEN_D, GREEN_GATE = lin(104, 118, 94), lin(150, 158, 138), lin(66, 76, 62), lin(96, 112, 88)
DUST, GRIME, RUST, RUST_D, OIL = MP.DUST, MP.GRIME, MP.RUST, MP.RUST_D, MP.OIL
PRIMER, CONC, CONC_D = MP.PRIMER, MP.CONC, MP.CONC_D
ALGAE, MOSS = MP.ALGAE, MP.MOSS
NEEDLE, LEAF = lin(150, 104, 52), lin(122, 82, 40)
common, tone, along_wall = MP.common, MP.tone, MP.along_wall
C = GK.CORR
VALLEY_OFF = C['crest'] + C['slope'] + (C['pitch'] - C['crest'] - 2 * C['slope']) / 2   # a valley's middle in a period


def wall_side(N):
    """+1 on faces toward north / east, -1 toward south / west (per axis), and the axis"""
    ax = np.where(np.abs(N[:, 0]) > np.abs(N[:, 1]), 0, 1)
    return ax


def u_wall(P, N):
    """the coordinate along the wall and the sheet's phase origin (walls start at -XO / -YO)"""
    ax = wall_side(N)
    s = np.where(ax == 1, P[:, 0], P[:, 1])
    s0 = np.where(ax == 1, -S.XO, -S.YO)
    return s, s - s0


def screws(s_rel, z, aa, rows, r=0.007):
    """screw heads in the valleys on the girts' rows: mask and the halo round each"""
    dv = dist_periodic(s_rel, C['pitch'], VALLEY_OFF)
    dz = np.min(np.stack([np.abs(z - zr) for zr in rows], 1), 1)
    d = np.sqrt(dv * dv + dz * dz)
    return 1 - ss(r - aa, r + aa, d), 1 - ss(r, r * 3.5, d), dv, dz


GIRTS = (0.45, 1.55, 2.65, 3.75, 4.32)


# ================================================================ outside
def skin(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 701)
    x, y, zz = P[:, 0], P[:, 1], P[:, 2]
    s, s_rel = u_wall(P, N)
    sheet = np.floor(s_rel / (5 * C['pitch']))
    t = 0.93 + 0.12 * hash1(sheet + 17.0 * wall_side(N) + 31.0 * np.sign(N[:, 0] + N[:, 1]), 11)
    c = GREEN * (t * (0.90 + 0.14 * (n_lo - 0.5) * 2 + 0.06 * (n_hi - 0.5)))[:, None]
    south = np.clip(-N[:, 1], 0, 1)
    west = np.clip(-N[:, 0], 0, 1)
    fade = ss(1.0, 4.2, zz) * 0.35 + south * 0.30 + west * 0.15
    c = mixc(c, GREEN_FADE, np.clip(fade * (0.55 + 0.45 * n_mid), 0, 0.75))
    # laps between the sheets (a dark line on the lap's edge), screws in the valleys on the girts
    lap = gline(dist_periodic(s_rel, 5 * C['pitch'], 0.004), 0.016, aa)
    c = mixc(c, GREEN_D, lap * 0.45)
    head, halo, dv, dz = screws(s_rel, zz, aa, GIRTS)
    keyed = hash1(np.floor(s_rel / C['pitch']) * 7.0 + np.round(zz / 1.1) * 13.0, 12)
    rusty = keyed > 0.55
    c = mixc(c, RUST_D, halo * rusty * 0.55)
    below = np.zeros(len(P), np.float32)                              # runs down from the rusty screws
    for zr in GIRTS:
        run_len = 0.25 + 0.9 * hash1(np.floor(s_rel / C['pitch']) * 3.1 + zr * 7.0, 13)
        below = np.maximum(below, (1 - ss(0.004, 0.012 + 0.004 * (zr - zz), dv)) * ss(0.0, 0.03, zr - zz) *
                           ss(run_len, run_len * 0.4, zr - zz) * (hash1(np.floor(s_rel / C['pitch']) * 5.3 + zr * 3.0, 14) > 0.6))
    c = mixc(c, RUST, below * 0.55)
    c = mixc(c, lin(178, 180, 174), head * 0.85)
    # rust: the foot of the sheets, spots, scratches on the crests, round the downpipe clips
    foot = ss(0.62, 0.31, zz) * (0.5 + 0.5 * n_mid)
    spots = ss(0.74, 0.86, fbm(P, 5.0, 3, seed=702)) * 0.6
    scratch = ss(0.80, 0.90, fbm(P * np.array([1.0, 1.0, 6.0], np.float32), 14.0, 2, seed=703)) * edge
    c = mixc(c, RUST_D, np.clip(foot * 0.7 + spots * 0.5 + scratch, 0, 0.85))
    # dirt: splash at the foot, algae low on the north, dark runs under the scuppers, streaks from the soffit
    north = np.clip(N[:, 1], 0, 1)
    c = mixc(c, lin(70, 62, 50), ss(0.85, 0.30, zz) * 0.55)
    c = mixc(c, ALGAE, north * ss(1.3, 0.3, zz) * ss(0.45, 0.75, n_mid) * 0.55)
    for xs in GK.SCUPPERS_X:
        c = mixc(c, lin(46, 48, 40), north * np.exp(-((x - xs) / 0.22) ** 2) * ss(4.4, 0.4, zz) * 0.45)
    runs = ss(0.58, 0.82, fbm(P * np.array([1, 1, 0.10], np.float32), 9.0, 3, seed=704))
    c = mixc(c, lin(70, 76, 64), runs * ss(2.8, 4.3, zz) * 0.35)
    c = mixc(c, GREEN_D, cav * 0.30)
    gr = np.maximum(lap * 0.7, head * 0.4)
    return c, gr


def trim(P, N, ao, aa, z):
    base = GK.DRAFT_COL.get(z, (66, 76, 62))
    c = MP.paint(lin(*base), P, N, ao, 711 + z % 7, chips=0.55)
    zz = P[:, 2]
    c = mixc(c, lin(70, 62, 50), ss(0.6, 0.2, zz) * 0.5)
    return c, None


def soffit(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 721)
    c = tone(GREEN * 0.92, n_lo, n_hi, 0.12, 0.14)
    near = np.minimum(np.abs(np.abs(P[:, 0]) - (S.XO - C['depth'])), np.abs(np.abs(P[:, 1]) - (S.YO - C['depth'])))
    c = mixc(c, lin(60, 58, 50), ss(0.10, 0.0, near) * 0.5)                          # cobwebs, dirt at the wall line
    c = mixc(c, RUST_D, ss(0.76, 0.88, fbm(P, 7.0, 2, seed=722)) * 0.5)
    return mixc(c, GRIME, cav * 0.4), None


def plinth(P, N, ao, aa, z):
    """the concrete upstand: outside splash, moss and lime at the foot; inside cleaner, oily and scuffed low"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 731)
    zz = P[:, 2]
    inside = MP.facing_room(P, N) >= 0
    c = tone(CONC, n_lo, n_hi, 0.16, 0.22)
    pores = ss(0.80, 0.92, fbm(P, 60.0, 1, seed=732))
    c = mixc(c, CONC_D, pores * 0.35)
    c = mixc(c, lin(160, 158, 150), ss(0.70, 0.88, fbm(P * np.array([1, 1, 0.3], np.float32), 4.0, 2, seed=733)) * 0.35)
    north = np.clip(N[:, 1], 0, 1)
    out = ~inside
    c = mixc(c, lin(66, 56, 44), out * ss(0.15, -0.10, zz - S.GROUND) * 0.6)
    c = mixc(c, MOSS, out * (0.3 + 0.7 * north) * ss(0.30, 0.0, zz - S.GROUND) * ss(0.45, 0.75, n_mid) * 0.6)
    lime = ss(0.76, 0.90, fbm(P * np.array([1, 1, 0.15], np.float32), 7.0, 2, seed=734))
    c = mixc(c, lin(178, 176, 168), out * lime * ss(0.35, 0.10, zz - S.GROUND) * 0.30)
    c = mixc(c, lin(78, 70, 60), inside * ss(0.20, 0.0, zz) * 0.45)
    c = mixc(c, OIL, inside * ss(0.74, 0.88, fbm(P, 3.0, 2, seed=735)) * 0.35)
    c = mixc(c, CONC_D, cav * 0.4 + edge * 0.1)
    up_ = up > 0.6
    c = np.where((up_ & out)[:, None], mixc(c, lin(108, 104, 96), np.full(len(P), 0.3)), c)
    return c, None


def felt(P, N, ao, aa, z):
    """bitumen felt with slate granules: speckle, the laps every metre, moss and lichen, needles and leaves along the
    kerb and in the dips, dried puddle rings, the granules washed off in streaks"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 741)
    x, y = P[:, 0], P[:, 1]
    g = hash1(np.floor(x * 70) + np.floor(y * 73) * 131.0, 15)
    c = mixc(lin(58, 58, 60), lin(36, 36, 38), ss(0.55, 0.95, g)) * (0.88 + 0.20 * n_lo)[:, None]
    c = mixc(c, lin(96, 94, 90), ss(0.88, 1.0, g) * 0.5)
    lap = gline(dist_periodic(y, 1.0, 0.0), 0.012, aa)
    c = mixc(c, lin(30, 30, 30), lap * 0.6)
    edge_d = np.minimum(GK.EDGE_X - GK.KERB - np.abs(x), GK.EDGE_Y - GK.KERB - np.abs(y))
    debris = ss(0.9, 0.05, edge_d) * ss(0.40, 0.70, fbm(P, 4.0, 3, seed=742))
    c = mixc(c, NEEDLE, debris * 0.55 * ss(0.4, 0.7, n_hi))
    c = mixc(c, LEAF, debris * ss(0.70, 0.85, fbm(P, 11.0, 2, seed=743)) * 0.6)
    moss = ss(0.66, 0.82, fbm(P, 1.6, 4, seed=744))
    c = mixc(c, MOSS, moss * (0.45 + 0.35 * ss(1.5, 0.0, edge_d)))
    c = mixc(c, lin(140, 146, 90), moss * ss(0.75, 0.9, n_hi) * 0.4)                  # lichen dots on the moss
    q = np.stack([x, y, np.zeros_like(x)], 1).astype(np.float32)
    b = fbm(q, 0.45, 3, seed=745)
    ring = (1 - ss(0.0, 0.012, np.abs(b - 0.70))) * ss(0.62, 0.70, b)
    c = mixc(c, lin(120, 118, 112), ring * 0.55)
    c = mixc(c, lin(84, 84, 82), ss(0.70, 0.78, b) * 0.35)
    return c, lap * 0.5


# ================================================================ inside
def liner(P, N, ao, aa, z):
    """grey-white liner trays (0.6 m, vertical joints, screws along them), dirty low, tyre marks and scuffs, the door's
    hand marks, condensation runs from the deck, oil spatter by the bench, cobwebs in the corners"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 751)
    x, y, zz = P[:, 0], P[:, 1], P[:, 2]
    s, s_rel = u_wall(P, N)
    tray = np.floor((s_rel + 0.10) / 0.60)
    c = lin(214, 214, 206) * (0.95 + 0.06 * hash1(tray + 9.0 * wall_side(N), 16))[:, None]
    c = c * (0.93 + 0.08 * (n_lo - 0.5) * 2 + 0.03 * (n_hi - 0.5))[:, None]
    joint = gline(dist_periodic(s_rel + 0.10, 0.60), 0.008, aa)
    scr = 1 - ss(0.004 - aa, 0.006 + aa, np.hypot(dist_periodic(s_rel + 0.10, 0.60) - 0.015, dist_periodic(zz, 0.50, 0.30)))
    c = mixc(c, lin(150, 150, 144), joint * 0.6)
    c = mixc(c, lin(120, 116, 106), scr * 0.7)
    h = zz
    c = mixc(c, lin(120, 112, 98), ss(0.9, 0.30, h) * 0.30 * (0.6 + 0.4 * n_mid))        # dirt low
    tyre = ss(0.80, 0.90, fbm(np.stack([s * 3.0, zz * 14.0, np.zeros_like(s)], 1).astype(np.float32), 1.0, 2, seed=752))
    c = mixc(c, lin(34, 32, 30), tyre * ss(0.70, 0.30, h) * 0.6)
    hands = np.exp(-(((y - 1.90) / 0.25) ** 2 + ((zz - 1.10) / 0.30) ** 2)) * (x > 5.0)
    hands += np.exp(-(((x - GATE_C[0]) / 0.6) ** 2 + ((zz - 1.10) / 0.35) ** 2)) * (y < -4.0) * 0.5
    c = mixc(c, lin(120, 108, 88), np.clip(hands, 0, 1) * 0.45 * ss(0.3, 0.7, n_mid))
    cond = ss(0.62, 0.84, fbm(P * np.array([1, 1, 0.08], np.float32), 7.0, 3, seed=753)) * ss(2.6, 4.2, zz)
    c = mixc(c, lin(156, 120, 76), cond * 0.45)
    oil = ss(0.78, 0.90, fbm(P, 18.0, 2, seed=754)) * (y > 4.0) * (x > 2.3) * (x < 4.9) * ss(0.70, 1.0, zz) * ss(1.5, 1.0, zz)
    c = mixc(c, OIL, oil * 0.6)
    c = mixc(c, lin(150, 146, 136), cav * 0.45)
    c = mixc(c, lin(90, 86, 78), ss(0.45, 0.25, ao) * 0.3)
    return c, np.maximum(joint * 0.6, scr * 0.4)


def deck(P, N, ao, aa, z):
    c, g = MP.galv(P, N, ao, aa, z)
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 761)
    drip = ss(0.70, 0.86, fbm(P, 5.0, 3, seed=762))
    c = mixc(c, lin(140, 120, 90), drip * 0.35)
    c = mixc(c, lin(60, 58, 54), np.exp(-(((P[:, 0] - GATE_C[0]) / 2.0) ** 2 + ((P[:, 1] + 3.0) / 1.6) ** 2)) * 0.25)
    return mixc(c, GRIME, cav * 0.35), None


def beam(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 771)
    c = tone(lin(128, 62, 44), n_lo, n_hi, 0.12, 0.18)
    c = mixc(c, lin(90, 46, 34), ss(0.6, 0.85, n_mid) * 0.3)
    c = mixc(c, RUST, np.clip(edge * 0.6 + ss(0.80, 0.92, fbm(P, 30.0, 2, seed=772)) * 0.5, 0, 0.8))
    c = mixc(c, DUST, up * 0.55)
    return mixc(c, GRIME, cav * 0.4), None


def floor(P, N, ao, aa, z):
    """power-floated concrete: trowel swirls, saw cuts, oil under the quad / drums / bench / where a car stood, tracks
    and mud from the gate, the yellow parking bay worn through, needles blown in, damp round the drain"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 781)
    x, y = P[:, 0], P[:, 1]
    c = tone(lin(128, 126, 120), n_lo, n_hi, 0.16, 0.18)
    sw = fbm(np.stack([x + 0.3 * np.sin(y * 3.0), y + 0.3 * np.sin(x * 3.0), np.zeros_like(x)], 1).astype(np.float32),
             2.4, 2, seed=782)
    c = c * (0.94 + 0.10 * sw)[:, None]
    cut = np.maximum(gline(np.abs(y), 0.006, aa), np.maximum(gline(np.abs(x - 2.0), 0.006, aa), gline(np.abs(x + 2.0), 0.006, aa)))
    c = mixc(c, lin(70, 68, 64), cut * 0.8)
    oil = np.zeros(len(P), np.float32)
    q = S.QUAD['c']
    oil += 0.9 * np.exp(-(((x - q[0]) / 0.45) ** 2 + ((y - q[1]) / 0.30) ** 2))
    oil += 0.6 * np.exp(-(((x - q[0] - 0.3) / 0.20) ** 2 + ((y - q[1] + 0.1) / 0.15) ** 2))
    oil += 0.7 * np.exp(-(((x - GATE_C[0]) / 0.70) ** 2 + ((y + 1.8) / 0.9) ** 2))           # where a car stood
    oil += 0.6 * np.exp(-(((x - 5.0) / 0.5) ** 2 + ((y + 1.60) / 0.12) ** 2))                # in front of the pallet
    oil += 0.4 * np.exp(-(((x - 3.6) / 1.0) ** 2 + ((y - 3.3) / 0.25) ** 2))                 # under the bench's edge
    oil *= ss(0.30, 0.65, fbm(P, 3.0, 3, seed=783))
    c = mixc(c, OIL, np.clip(oil, 0, 0.85))
    track = (np.exp(-((x - GATE_C[0] - 0.50) / 0.12) ** 2) + np.exp(-((x - GATE_C[0] + 0.50) / 0.12) ** 2)) * ss(1.2, -4.0, y)
    c = mixc(c, lin(66, 60, 52), np.clip(track, 0, 1) * 0.45 * (0.5 + 0.5 * n_mid))
    mud = ss(-2.8, -4.4, y) * (np.abs(x - GATE_C[0]) < 2.2) + 0.7 * np.exp(-(((x - 5.6) / 0.6) ** 2 + ((y - 1.5) / 0.6) ** 2))
    c = mixc(c, lin(92, 80, 62), np.clip(mud, 0, 1) * 0.45 * ss(0.35, 0.75, n_mid))
    blown = (ss(-3.6, -4.35, y) * (np.abs(x - GATE_C[0]) < 1.9) + np.exp(-(((x - 5.7) / 0.3) ** 2 + ((y - 1.5) / 0.5) ** 2)))
    nd = ss(0.86, 0.94, fbm(P, 35.0, 2, seed=784)) * np.clip(blown, 0, 1)
    c = mixc(c, NEEDLE, nd * 0.75)
    # the parking bay round the quad: yellow lines 5 cm, worn where the wheels cross
    bx0, bx1, by0, by1 = q[0] - 1.15, q[0] + 1.35, q[1] - 0.95, q[1] + 0.95
    d_line = np.minimum(np.minimum(np.abs(x - bx0), np.abs(x - bx1)) + np.where((y > by0) & (y < by1), 0, 9),
                        np.minimum(np.abs(y - by0), np.abs(y - by1)) + np.where((x > bx0) & (x < bx1), 0, 9))
    paint = (1 - ss(0.025 - aa, 0.025 + aa, d_line)) * ss(0.30, 0.55, fbm(P, 20.0, 2, seed=785))
    c = mixc(c, lin(196, 160, 40), paint * 0.85)
    dx, dy, ds = GK.DRAIN
    damp = np.exp(-(((x - dx) ** 2 + (y - dy) ** 2) / 0.8 ** 2))
    c = mixc(c, lin(84, 82, 78), damp * 0.40 * (0.6 + 0.4 * n_mid))
    c = mixc(c, GRIME, cav * 0.45)
    c = mixc(c, DUST, ss(0.6, 0.9, n_mid) * 0.12)
    return c, cut * 0.7


# ================================================================ outside ground pieces
def apron(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 791)
    x, y = P[:, 0], P[:, 1]
    c = tone(lin(122, 120, 114), n_lo, n_hi, 0.16, 0.24)
    c = mixc(c, lin(150, 148, 140), ss(0.55, 0.85, fbm(P, 3.0, 2, seed=792)) * 0.35)
    cr = MP.crack_lines(x, y, 793, density=0.25, width=0.010)
    c = mixc(c, lin(60, 56, 50), cr * 0.7)
    track = (np.exp(-((x - GATE_C[0] - 0.50) / 0.14) ** 2) + np.exp(-((x - GATE_C[0] + 0.50) / 0.14) ** 2))
    c = mixc(c, lin(70, 66, 58), np.clip(track, 0, 1) * 0.40 * (0.5 + 0.5 * n_mid) * (up > 0.5))
    oil = np.exp(-(((x - GATE_C[0]) / 0.5) ** 2 + ((y + 5.2) / 0.5) ** 2)) * ss(0.35, 0.65, fbm(P, 4.0, 3, seed=794))
    c = mixc(c, OIL, oil * 0.6)
    edge_x = np.minimum(np.abs(x - (S.GATE['u'][0] - 0.60)), np.abs(x - (S.GATE['u'][1] + 0.60)))
    edge_d = np.minimum(edge_x, np.abs(y + 6.30))
    c = mixc(c, MOSS, ss(0.25, 0.0, edge_d) * ss(0.45, 0.75, n_mid) * 0.6)
    c = mixc(c, lin(70, 62, 50), (up < 0.5) * 0.35)
    c = mixc(c, lin(60, 56, 50), cav * 0.45)
    return c, cr * 0.6


# ================================================================ the leaves, frames, the pallet
def gate(P, N, ao, aa, z):
    """the gate: repainted a shade darker than the walls, chipped on the ribs, dirty at the foot, handled round the
    T-handle; inside (the frame and the sheet's back) the old paint, dusty"""
    zz = P[:, 2]
    if z == GK.Z_GATEIN:
        c = MP.paint(lin(92, 104, 86), P, N, ao, 801, chips=0.4, outdoor_fade=False, dust=0.35)
        return c, None
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 802)
    c = MP.paint(GREEN_GATE / 1.0, P, N, ao, 803, chips=0.45)
    c = mixc(c, lin(72, 64, 52), ss(0.55, 0.05, zz) * 0.6)
    hx = (S.GATE['u'][0] + S.GATE['u'][1]) / 2
    hand = np.exp(-(((P[:, 0] - hx) / 0.30) ** 2 + ((zz - 1.05) / 0.25) ** 2))
    c = mixc(c, lin(70, 66, 56), hand * 0.45 * ss(0.3, 0.7, n_mid))
    c = mixc(c, RUST, ss(0.74, 0.88, fbm(P * np.array([1, 1, 4.0], np.float32), 12.0, 2, seed=804)) * 0.4)
    return c, None


def leaf(P, N, ao, aa, z):
    zz = P[:, 2]
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 811)
    c = MP.paint(GREEN, P, N, ao, 812, chips=0.5)
    c = mixc(c, lin(72, 64, 52), ss(0.40, 0.02, zz) * 0.55)
    hand = np.exp(-(((P[:, 1] - 1.895) / 0.12) ** 2 + ((zz - 1.05) / 0.16) ** 2))
    c = mixc(c, lin(70, 64, 54), hand * 0.5 * ss(0.3, 0.7, n_mid))
    return c, None


def spill(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 821)
    c = MP.paint(lin(214, 170, 40), P, N, ao, 822, chips=0.5, outdoor_fade=False, dust=0.3)
    c = mixc(c, OIL, ss(0.70, 0.86, fbm(P, 6.0, 3, seed=823)) * 0.5 * (up > 0.5))
    return c, None


def hook(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 831)
    return tone(lin(40, 40, 40), n_lo, n_hi, 0.1, 0.1), None


def _table():
    T = dict(MP.TABLE)
    T[GK.Z_SKIN] = skin
    for zz in (GK.Z_TRIM, GK.Z_FRAME, GK.Z_WINFRAME, GK.Z_FASCIA):
        T[zz] = trim
    T[GK.Z_SOFFIT] = soffit
    T[GK.Z_PLINTH] = plinth
    T[GK.Z_FELT] = felt
    T[GK.Z_LINER] = liner
    T[GK.Z_DECK] = deck
    T[GK.Z_BEAM] = beam
    T[GK.Z_FLOOR] = floor
    T[GK.Z_APRON] = apron
    T[GK.Z_GATE] = gate
    T[GK.Z_GATEIN] = gate
    T[GK.Z_LEAF] = leaf
    T[GK.Z_SPILL] = spill
    T[GK.Z_HOOK] = hook
    return T


TABLE = _table()


def paint_gar(Pp, Nn, Z, ao, aa):
    n = len(Z)
    col = np.zeros((n, 3), np.float32)
    gr = np.zeros(n, np.float32)
    for z in np.unique(Z):
        m = np.nonzero(Z == z)[0]
        fn = TABLE.get(int(z))
        if fn is None:
            col[m] = lin(255, 0, 255)
            continue
        c, g = fn(Pp[m], Nn[m], ao[m], aa, int(z))
        col[m] = c
        if g is not None:
            gr[m] = g
    return col, gr
