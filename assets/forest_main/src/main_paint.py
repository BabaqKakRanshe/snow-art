"""Painters for the main building's atlases (psxbake): paint_main(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n]).
The generator shed's language at the main building: board-formed concrete facades (12 cm boards, tie holes, run-off under
the windows and the coping, algae and splash at the foot), the dark plinth, the gravel roof, the brick flue; inside the
70s finishes (oil-paint dado and the corridors' stripe, plaster, chequer and olive lino, carpet, tiles, the raised floor,
boards, painted concrete) worn where people walk (to and between the doors), scuffed low on the walls, grimy round the
handles; the station's grey-green paint on every metal (window frames, doors, the gate, the canopy's fascia), chalky
outside, chipped to primer on the edges; the furniture's steel, wood, laminate, fabric, plastic, enamel, chrome, brass and
copper, paper; the fixtures. Each zone is painted on its own texels only (the atlases are large).
Building frame: x east, y north, z up; ground floor 0.0, upper floor 3.4, basement -3.0, garage floor -0.15."""
import math
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline, seg_dist
from psxbake import lin, boards, hash1
import gen_kit as K
import main_spec as S
import main_shell as MS
import main_open as MO
import main_furn as F
import main_fx as FX

DUST, GRIME, RUST, RUST_D, OIL = lin(118, 112, 100), lin(64, 58, 48), lin(120, 62, 30), lin(70, 36, 20), lin(28, 23, 18)
GREEN, GREEN_FADE, GREEN_D = lin(104, 118, 94), lin(146, 154, 134), lin(60, 70, 56)        # the station's grey-green
PRIMER = lin(150, 76, 52)
CONC, CONC_D, CONC_L = lin(132, 130, 124), lin(84, 82, 78), lin(158, 156, 148)
ALGAE, MOSS, SOOT = lin(58, 66, 46), lin(70, 84, 46), lin(34, 32, 30)
DADO = {'brown': lin(138, 100, 62), 'olive': lin(106, 112, 70), 'grey': lin(132, 134, 128), 'cream': lin(206, 196, 164),
        'green': lin(98, 122, 96)}
TOP = {'cream': lin(226, 218, 192), 'white': lin(230, 230, 224)}
STRIPE = (lin(210, 120, 40), lin(120, 76, 40), lin(110, 112, 60))
F_OF = F.__dict__


# ---------------------------------------------------------------- the rooms around a texel
ROOMS = list(S.ROOMS.items())
RBOX = np.array([(R['x0'], R['y0'], R['f'] - 0.02, R['x1'], R['y1'], R['c'] + 0.02) for _, R in ROOMS], np.float32)


def room_index(Q):
    """index into ROOMS of the room containing each point (-1 = none)"""
    r = np.full(len(Q), -1, np.int32)
    for i, b in enumerate(RBOX):
        m = (Q[:, 0] > b[0]) & (Q[:, 0] < b[3]) & (Q[:, 1] > b[1]) & (Q[:, 1] < b[4]) & (Q[:, 2] > b[2]) & (Q[:, 2] < b[5])
        r[m & (r < 0)] = i
    return r


def facing_room(P, N, d=0.3):
    """the room a surface faces (probe d along the normal), -1 = it faces the outside"""
    return room_index(P + N * d)


def floor_of(P, N):
    ri = facing_room(P, N, 0.3)
    f = np.zeros(len(P), np.float32)
    for i, (_, R) in enumerate(ROOMS):
        f[ri == i] = R['f']
    f[ri < 0] = np.where(P[ri < 0, 2] < -0.2, S.GROUND, 0.0)
    return f, ri


def _door_points():
    pts = {}
    for name, d in S.DOORS.items():
        ax, a0, a1 = d['wall']
        um = (d['u'][0] + d['u'][1]) / 2
        am = (a0 + a1) / 2
        xy = (am, um) if ax == 'x' else (um, am)
        for rn in (d['room'], d['out']):
            pts.setdefault(rn, []).append((xy[0], xy[1], d['z'][0]))
    kp = S.KITCHEN_PASS
    for rn in ('Kueche', 'Flur_OG'):
        pts.setdefault(rn, []).append(((kp['u'][0] + kp['u'][1]) / 2, (kp['wall'][1] + kp['wall'][2]) / 2, S.OG_F))
    return pts


DOORPTS = _door_points()


def tread(P, ri):
    """wear on a floor: round the room's doors and along the lines between them (0..1)"""
    w = np.zeros(len(P), np.float32)
    for i, (rn, R) in enumerate(ROOMS):
        m = ri == i
        if not m.any():
            continue
        Q = P[m][:, :2].astype(np.float64)
        pts = [(x, y) for x, y, z in DOORPTS.get(rn, []) if abs(z - R['f']) < 0.5]
        acc = np.zeros(len(Q))
        for (x, y) in pts:
            acc = np.maximum(acc, np.exp(-(((Q[:, 0] - x) ** 2 + (Q[:, 1] - y) ** 2) / 0.9 ** 2)))
        for a_ in range(len(pts)):
            for b_ in range(a_ + 1, len(pts)):
                d = seg_dist(Q, np.array(pts[a_]), np.array(pts[b_]))
                acc = np.maximum(acc, 0.75 * np.exp(-(d / 0.55) ** 2))
        if rn.startswith('Flur'):
            acc = np.maximum(acc, 0.7 * np.exp(-((Q[:, 1] - 0.0) / 0.55) ** 2))
        w[m] = acc
    return w


def common(P, N, ao, seed):
    n_lo = fbm(P, 2.2, 3, seed=seed)
    n_mid = fbm(P, 8.0, 3, seed=seed + 1)
    n_hi = fbm(P, 40.0, 2, seed=seed + 2)
    up = np.clip(N[:, 2], 0, 1)
    cav = ss(0.62, 0.30, ao)
    edge = ss(0.86, 0.97, ao) * ss(0.70, 0.88, fbm(P, 60.0, 2, seed=seed + 3))
    return n_lo, n_mid, n_hi, up, cav, edge


def tone(c, n_lo, n_hi, a=0.20, b=0.14):
    return np.asarray(c, np.float32) * (0.88 + a * (n_lo - 0.5) * 2 + b * (n_hi - 0.5))[:, None]


def along_wall(P, N):
    return np.where(np.abs(N[:, 0]) > 0.5, P[:, 1], P[:, 0])


# ================================================================ exterior
def _window_streaks(P, N):
    """run-off under the windows' sills (dirt washed down from the sill ends)"""
    s = np.zeros(len(P), np.float32)
    for w in S.WINDOWS:
        if w.get('internal'):
            continue
        ax, a0, a1 = w['wall']
        aout = a0 if abs(a0) > abs(a1) else a1
        if ax == 'x':
            onw = (np.abs(P[:, 0] - aout) < 0.02) & (np.abs(N[:, 0]) > 0.7)
            u = P[:, 1]
        else:
            onw = (np.abs(P[:, 1] - aout) < 0.02) & (np.abs(N[:, 1]) > 0.7)
            u = P[:, 0]
        if not onw.any():
            continue
        u0, u1 = w['u']
        z0 = w['z'][0]
        inu = ss(u0 - 0.12, u0 + 0.05, u) * ss(u1 + 0.12, u1 - 0.05, u)
        ends = np.exp(-((u - u0) / 0.10) ** 2) + np.exp(-((u - u1) / 0.10) ** 2)
        dz = z0 - P[:, 2]
        fall = ss(-0.01, 0.05, dz) * ss(1.6, 0.1, dz)
        s = np.maximum(s, np.where(onw, (0.35 * inu + 0.9 * ends) * fall, 0.0))
    return np.clip(s, 0, 1)


def facade(P, N, ao, aa, z):
    """board-formed concrete as the yard's bund walls: 12 cm boards (a tone per board run, the grain along it, the
    joints), tie holes, run-off down every wall (heavier under the coping and the sills), light lime streaks, algae and
    splash at the foot; the band and the parapets in smoother concrete"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 301)
    s = along_wall(P, N)
    zz = P[:, 2]
    vert = (np.abs(N[:, 2]) < 0.5).astype(np.float32)
    if z in (MS.Z_FACADE,):
        bi, seam = boards(zz + 7.0, 0.12, aa, 0.003)
        t = 0.90 + 0.14 * hash1(bi + 31.0 * np.floor(s / 2.4), 7)
        grain = fbm(np.stack([s * 0.25, bi * 3.1, zz * 5.0], 1).astype(np.float32), 3.0, 2, seed=302)   # along the board
        c = CONC * (t * (0.94 + 0.10 * (grain - 0.5)))[:, None]
        c = c * (0.88 + 0.18 * (n_lo - 0.5) * 2 + 0.10 * (n_hi - 0.5))[:, None]
        tie = (1 - ss(0.010 - aa, 0.016 + aa, np.hypot(dist_periodic(s, 0.75, 0.37), dist_periodic(zz, 0.48, 0.12))))
        c = mixc(c, CONC_D * 0.8, tie * 0.8)
        gr = np.maximum(seam * 0.55, tie * 0.6)
    else:
        c = tone(CONC_L if z == MS.Z_BAND else CONC, n_lo, n_hi, 0.16, 0.22)
        gr = None
    # weather: run-off down the walls (heavier under the coping and the sills), lime streaks, algae and splash at the foot
    runs = ss(0.55, 0.80, fbm(P * np.array([1, 1, 0.12], np.float32), 8.0, 3, seed=303)) * vert
    top = ss(S.PARAPET - 1.2, S.PARAPET - 0.05, zz) * (zz > S.EG_F)
    garage_top = ss(S.G_PARAPET - 0.9, S.G_PARAPET - 0.05, zz) * (P[:, 0] < -8.05)
    tower_top = ss(S.TOWER_TOP - 1.0, S.TOWER_TOP - 0.05, zz) * (np.abs(P[:, 0]) < 2.0) * (P[:, 1] > 0.9)
    under = np.clip(np.maximum(np.maximum(top, garage_top), tower_top) + _window_streaks(P, N), 0, 1)
    c = mixc(c, lin(88, 86, 80), np.clip(runs * (0.30 + 0.45 * under) + under * 0.25, 0, 1) * 0.6)
    c = mixc(c, lin(170, 168, 160), ss(0.80, 0.92, fbm(P * np.array([1, 1, 0.2], np.float32), 10.0, 2, seed=304)) * vert * 0.30)
    north = np.clip(N[:, 1], 0, 1)
    foot = ss(0.65, -0.1, zz - S.GROUND) * (zz < 1.5)
    c = mixc(c, ALGAE, foot * (0.25 + 0.45 * north) * ss(0.4, 0.75, n_mid))
    c = mixc(c, lin(66, 56, 44), ss(0.25, -0.05, zz - S.GROUND) * 0.6)                          # earth splash
    c = mixc(c, MOSS, vert * ss(0.45, 0.05, zz - S.GROUND) * ss(0.55, 0.80, fbm(P, 5.0, 2, seed=305)) * 0.5)
    c = mixc(c, lin(120, 124, 96), up * ss(0.62, 0.80, fbm(P, 9.0, 2, seed=306)) * 0.45)       # lichen on the tops
    c = mixc(c, CONC_D, cav * 0.35)
    return c, gr


def plinth(P, N, ao, aa, z):
    """the dark plinth and the paved concrete outside (landing, steps, ramp, apron): horizontal faces trodden and
    salted, vertical ones damp at the foot"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 311)
    c = tone(lin(88, 86, 82), n_lo, n_hi, 0.18, 0.22)
    flat = up > 0.6
    paved = tone(lin(118, 116, 110), n_lo, n_hi, 0.16, 0.24)
    paved = mixc(paved, lin(146, 144, 138), ss(0.55, 0.85, fbm(P, 3.0, 2, seed=312)) * 0.35)        # salt and dust
    paved = mixc(paved, lin(70, 66, 58), ss(0.62, 0.84, n_mid) * 0.35)
    c = np.where(flat[:, None], paved, c)
    c = mixc(c, MOSS, (1 - up) * ss(0.25, -0.05, P[:, 2] - S.GROUND) * ss(0.45, 0.75, n_mid) * 0.5)
    c = mixc(c, lin(60, 58, 54), cav * 0.45 + edge * 0.15)
    gr = gline(dist_periodic(P[:, 0], 1.5), 0.004, aa) * flat * 0.5                      # joints in the paving
    return c, gr


def roof(P, N, ao, aa, z):
    """gravel on the flat roofs: speckle, wet dark round the scuppers, moss along the parapets"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 321)
    g = hash1(np.floor(P[:, 0] * 90) + np.floor(P[:, 1] * 97) * 131.0, 5)
    c = mixc(lin(118, 112, 104), lin(70, 66, 62), ss(0.55, 0.95, g)) * (0.86 + 0.24 * n_lo)[:, None]
    c = mixc(c, lin(150, 142, 128), ss(0.85, 1.0, g) * 0.6)
    wet = np.zeros(len(P), np.float32)
    for x, y in ((-8.12, -5.55), (-8.12, 5.55), (7.82, -6.12), (7.55, 6.12), (-17.45, -5.12), (-17.45, 5.12)):
        wet = np.maximum(wet, np.exp(-(((P[:, 0] - x) ** 2 + (P[:, 1] - y) ** 2) / 1.6 ** 2)))
    c = mixc(c, lin(52, 50, 46), wet * 0.6 * (0.6 + 0.4 * n_mid))
    near = np.minimum(np.minimum(np.abs(np.abs(P[:, 0]) - S.PAR_IN), np.abs(np.abs(P[:, 1]) - S.PAR_IN_Y)), 9.0)
    c = mixc(c, MOSS, ss(0.5, 0.05, near) * ss(0.45, 0.75, n_mid) * 0.5)
    return mixc(c, lin(60, 58, 54), cav * 0.4), None


def upstand(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 331)
    c = tone(lin(34, 34, 34), n_lo, n_hi, 0.10, 0.25)
    c = mixc(c, lin(110, 108, 100), ss(0.6, 0.85, fbm(P, 12.0, 2, seed=332)) * 0.35)
    return c, gline(dist_periodic(along_wall(P, N), 1.0), 0.004, aa) * 0.4


def brick(P, N, ao, aa, z):
    """the flue: stretcher bond (24 x 7.1 cm, 1 cm joints), soot toward the top"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 341)
    s = along_wall(P, N)
    row = np.floor(P[:, 2] / 0.083)
    off = (row % 2) * 0.125
    bi = np.floor((s + off) / 0.25)
    jh = gline(dist_periodic(P[:, 2], 0.083), 0.005, aa)
    jv = gline(dist_periodic(s + off, 0.25), 0.005, aa)
    joint = np.maximum(jh, jv)
    t = 0.82 + 0.30 * hash1(bi * 7.0 + row * 13.0, 9)
    c = lin(150, 70, 50) * t[:, None] * (0.92 + 0.12 * n_hi)[:, None]
    c = mixc(c, lin(170, 164, 150), joint)
    c = mixc(c, SOOT, ss(S.ROOF + 0.6, S.ROOF + 1.6, P[:, 2]) * ss(0.4, 0.8, n_mid) * 0.7)
    c = mixc(c, lin(70, 40, 30), cav * 0.4)
    return c, joint * 0.6


def galv(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 351)
    spang = fbm(P, 90.0, 1, seed=352)
    c = tone(lin(150, 154, 152), n_lo, n_hi, 0.10, 0.08) * (0.88 + 0.22 * spang)[:, None]
    c = mixc(c, lin(196, 198, 192), ss(0.78, 0.90, fbm(P, 25.0, 2, seed=353)) * 0.4)               # white rust
    run = ss(0.6, 0.85, fbm(P * np.array([1, 1, 0.15], np.float32), 9.0, 3, seed=354))
    c = mixc(c, RUST, run * 0.25 * (facing_room(P, N) < 0))
    c = mixc(c, lin(90, 92, 90), cav * 0.4)
    return c, None


def steel_black(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 361)
    c = tone(lin(36, 36, 36), n_lo, n_hi, 0.12, 0.2)
    c = mixc(c, RUST, np.clip(edge * 0.7 + ss(0.72, 0.86, fbm(P, 30.0, 2, seed=362)) * 0.4, 0, 0.8))
    return mixc(c, DUST, up * 0.25), None


# ================================================================ interior shell
def _room_attr(ri, key, default):
    out = []
    for i in ri:
        if i < 0:
            out.append(default)
        else:
            out.append(ROOMS[i][1]['walls'].get(key, default))
    return out


def crack_lines(s, t, seed, density=0.12, width=0.012):
    """hairline cracks on a surface (s, t in metres): short jagged pieces of the ridges of a warped noise, only in a few
    places (density = the share of the surface where they may run)"""
    q = np.stack([s, t, np.zeros_like(s)], 1).astype(np.float32)
    w = fbm(q, 1.6, 2, seed=seed) - 0.5
    r = np.abs(fbm(q + (w * 0.5)[:, None], 3.2, 3, seed=seed + 1) - 0.5)
    keep = ss(1.0 - density, 1.0 - density + 0.05, fbm(q, 0.35, 2, seed=seed + 2))
    piece = ss(0.52, 0.60, fbm(q, 2.4, 2, seed=seed + 3))                     # broken into short runs
    return (1 - ss(0.0, width, r)) * keep * piece


def stains(s, t, seed, thr=0.74):
    """water stains: the blot (0..1) and its darker tide line"""
    q = np.stack([s, t, np.zeros_like(s)], 1).astype(np.float32)
    b = fbm(q, 0.55, 4, seed=seed)
    blot = ss(thr, thr + 0.06, b)
    rim = (1 - ss(0.0, 0.010, np.abs(b - thr - 0.003))) * ss(thr - 0.02, thr, b)
    return blot, rim


def wall_paint(P, N, ao, aa, z):
    """plaster above the dado, the oil-paint dado and the corridors' stripe, per room colours: the roller's texture and
    repainted patches on the plaster, hairline cracks, water stains with tide lines under the ceiling, yellowed areas;
    on the dado the brush's streaks, the hand-painted edge, black scuffs and kicks low down, chips to the plaster; hand
    marks by the doors, grime along the floor and in the corners"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 371)
    f, ri = floor_of(P, N)
    h = P[:, 2] - f
    s = along_wall(P, N)
    t = P[:, 2]
    q2 = np.stack([s, t, np.zeros_like(s)], 1).astype(np.float32)
    dado = np.array(_room_attr(ri, 'dado', 1.5), np.float32)
    if z == MS.Z_DADO:
        cols = np.array([DADO.get(c_, DADO['grey']) for c_ in _room_attr(ri, 'dado_col', 'grey')], np.float32)
        brush = fbm(np.stack([s * 9.0, t * 0.35, np.zeros_like(s)], 1).astype(np.float32), 1.0, 2, seed=372)
        c = cols * (0.92 + 0.10 * (n_lo - 0.5) * 2 + 0.07 * (brush - 0.5) + 0.04 * (n_hi - 0.5))[:, None]
        c = mixc(c, c * 1.16, ss(0.58, 0.85, fbm(P, 5.0, 2, seed=373)) * 0.22)                   # the gloss's sheen
        wav = 0.004 * (fbm(q2 * np.array([6.0, 1.0, 1.0], np.float32), 1.0, 2, seed=374) - 0.5)
        c = mixc(c, c * 0.72, gline(np.abs(h - dado + 0.004 + wav), 0.007, aa))                   # the painted edge
        scuff = ss(0.66, 0.80, fbm(np.stack([s * 2.5, t * 11.0, np.zeros_like(s)], 1).astype(np.float32), 1.0, 2,
                                   seed=375)) * ss(0.50, 0.12, h)
        c = mixc(c, lin(40, 36, 32), scuff * 0.55)
        kick = ss(0.74, 0.86, fbm(P, 9.0, 2, seed=376)) * ss(0.32, 0.05, h)
        c = mixc(c, lin(90, 80, 66), kick * 0.5)
        chip = ss(0.84, 0.93, fbm(P, 42.0, 2, seed=377)) * ss(1.3, 0.1, h)
        c = mixc(c, lin(196, 190, 176), chip * 0.7)
    elif z == MS.Z_STRIPE:
        k = np.clip(((h - dado - MS.STRIPE[0]) / MS.STRIPE[1]).astype(np.int32), 0, 2)
        c = np.array(STRIPE, np.float32)[k] * (0.92 + 0.12 * (n_lo - 0.5) + 0.05 * (n_hi - 0.5))[:, None]
        chip = ss(0.86, 0.94, fbm(P, 42.0, 2, seed=378))
        c = mixc(c, lin(214, 206, 186), chip * 0.6)
    else:
        cols = np.array([TOP.get(c_, TOP['cream']) for c_ in _room_attr(ri, 'top', 'cream')], np.float32)
        roller = fbm(q2, 22.0, 2, seed=379)
        c = cols * (0.93 + 0.08 * (n_lo - 0.5) * 2 + 0.05 * (roller - 0.5) + 0.03 * (n_hi - 0.5))[:, None]
        c = mixc(c, lin(196, 186, 160), ss(0.58, 0.88, fbm(P, 1.3, 3, seed=380)) * 0.30)              # yellowed areas
        patch = ss(0.665, 0.675, fbm(q2, 0.7, 2, seed=381))                                          # repainted patches
        c = mixc(c, c * 1.06 + 0.01, patch * 0.8)
        blot, rim = stains(s, t, 382)
        top_ = np.zeros(len(P), np.float32)
        for i, (rn, R) in enumerate(ROOMS):
            m = ri == i
            top_[m] = ss(1.4, 0.2, R['c'] - P[m, 2])
        c = mixc(c, lin(178, 150, 104), blot * top_ * 0.45)
        c = mixc(c, lin(130, 100, 64), rim * top_ * 0.6)
    cr = crack_lines(s, t, 383, density=0.10)
    c = mixc(c, c * 0.72, cr * 0.6)
    hands = np.zeros(len(P), np.float32)
    for rn, pts in DOORPTS.items():
        for x, y, zf in pts:
            d2 = (P[:, 0] - x) ** 2 + (P[:, 1] - y) ** 2
            hands = np.maximum(hands, np.exp(-d2 / 0.35 ** 2) * np.exp(-((P[:, 2] - zf - 1.1) / 0.35) ** 2))
    c = mixc(c, lin(96, 84, 66), hands * 0.40 * ss(0.3, 0.7, n_mid))
    c = mixc(c, GRIME, ss(0.22, 0.0, h) * 0.30 + cav * 0.30)
    ceil_near = np.zeros(len(P), np.float32)
    for i, (rn, R) in enumerate(ROOMS):
        m = ri == i
        ceil_near[m] = ss(0.25, 0.0, R['c'] - P[m, 2])
    c = mixc(c, lin(150, 140, 120), ceil_near * cav * 0.6)
    return c, cr * 0.5


def tiles(P, N, ao, aa, z):
    """wall tiles 15 x 15 (to 2 m) and floor tiles 20 x 20 / 30 x 30: grout lines, per-tile tone, stains"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 381)
    floor = up > 0.6
    s = np.where(floor, P[:, 0], along_wall(P, N))
    t_ = np.where(floor, P[:, 1], P[:, 2])
    pitch = np.where(floor, 0.30, 0.15)
    bi = np.floor(s / pitch) * 37.0 + np.floor(t_ / pitch) * 101.0
    v = hash1(bi, 3)
    f, ri = floor_of(P, N)
    kitchen = np.isin(ri, [i for i, (n, _) in enumerate(ROOMS) if n == 'Kueche'])
    base_w = lin(232, 232, 226)
    base_f = np.where(kitchen[:, None], lin(176, 150, 112), lin(196, 190, 176))
    c = np.where(floor[:, None], base_f, base_w) * (0.93 + 0.10 * v)[:, None]
    c = np.where((floor & ~kitchen & ((np.floor(s / 0.30) + np.floor(t_ / 0.30)) % 2 == 1))[:, None], c * 0.92, c)
    joint = np.maximum(gline(dist_periodic(s, pitch), 0.0025, aa), gline(dist_periodic(t_, pitch), 0.0025, aa))
    c = mixc(c, lin(150, 146, 136), joint * 0.85)
    c = mixc(c, lin(140, 120, 90), ss(0.70, 0.90, fbm(P, 4.0, 3, seed=382)) * 0.25)               # limescale / stains
    if floor.any():
        w = tread(P, ri)
        c = mixc(c, lin(140, 128, 108), w * 0.35 * floor)
    c = mixc(c, GRIME, cav * 0.35)
    return c, joint * 0.6


def veneer(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 391)
    s = along_wall(P, N)
    bi, seam = boards(s, 0.60, aa, 0.002)
    g = fbm(P * np.array([1.0, 1.0, 0.05], np.float32) + (bi * 2.7)[:, None], 18.0, 2, seed=392)
    c = lin(150, 100, 60) * (0.82 + 0.20 * hash1(bi, 4) + 0.18 * (g - 0.5))[:, None]
    c = mixc(c, lin(90, 60, 38), cav * 0.4)
    return c, seam * 0.6


def ceiling(P, N, ao, aa, z):
    """plaster ceilings (water stains), the suspended mineral-fibre tiles (62.5 cm grid, speckle), the garage's wood-wool
    boards, bare concrete"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 401)
    if z == MS.Z_CEILT:
        bi = np.floor(P[:, 0] / 0.625) * 37.0 + np.floor(P[:, 1] / 0.625) * 101.0
        c = lin(226, 224, 216) * (0.95 + 0.06 * hash1(bi, 5))[:, None]
        dots = ss(0.72, 0.86, fbm(P, 220.0, 1, seed=402))
        c = mixc(c, lin(160, 158, 150), dots * 0.5)
        stain = ss(0.80, 0.95, hash1(bi, 6)) * ss(0.35, 0.75, fbm(P, 5.0, 3, seed=403))
        c = mixc(c, lin(176, 150, 100), stain * 0.45)
        joint = np.maximum(gline(dist_periodic(P[:, 0], 0.625), 0.006, aa), gline(dist_periodic(P[:, 1], 0.625), 0.006, aa))
        c = mixc(c, lin(200, 200, 196), joint)
        return c, joint * 0.5
    if z == MS.Z_CEILB:
        bi, seam = boards(P[:, 1], 0.50, aa, 0.004)
        fib = fbm(P * np.array([1, 3.0, 1], np.float32), 60.0, 2, seed=404)
        c = lin(176, 164, 136) * (0.82 + 0.30 * fib + 0.08 * hash1(bi, 7))[:, None]
        return mixc(c, GRIME, cav * 0.4), seam * 0.6
    if z == MS.Z_CONCIN:
        c = tone(lin(150, 148, 140), n_lo, n_hi, 0.18, 0.2)
        c = mixc(c, lin(120, 118, 110), ss(0.6, 0.85, fbm(P, 2.0, 3, seed=405)) * 0.3)
        tie = (1 - ss(0.010 - aa, 0.016 + aa, np.hypot(dist_periodic(along_wall(P, N), 0.75, 0.37),
                                                         dist_periodic(P[:, 2], 0.60, 0.20)))) * (up < 0.5)
        return mixc(mixc(c, CONC_D, tie * 0.7), GRIME, cav * 0.4), tie * 0.5
    roller = fbm(P, 22.0, 2, seed=405)
    c = lin(232, 230, 222) * (0.93 + 0.08 * (n_lo - 0.5) * 2 + 0.05 * (roller - 0.5) + 0.03 * (n_hi - 0.5))[:, None]
    blot, rim = stains(P[:, 0], P[:, 1], 406, thr=0.70)
    c = mixc(c, lin(196, 172, 124), blot * 0.5)
    c = mixc(c, lin(140, 112, 72), rim * 0.65)
    cr = crack_lines(P[:, 0], P[:, 1], 407, density=0.12)
    c = mixc(c, c * 0.72, cr * 0.6)
    c = mixc(c, lin(120, 112, 98), ss(0.70, 0.90, fbm(P, 3.0, 2, seed=408)) * 0.15)              # soot over the lamps
    return mixc(c, lin(170, 166, 156), cav * 0.5), cr * 0.4


def floors(P, N, ao, aa, z):
    """the floor finishes, worn to and between the doors"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 411)
    f, ri = floor_of(P, N)
    w = tread(P, ri)
    x, y = P[:, 0], P[:, 1]
    gr = None
    if z == MS.Z_FL_LINO:                                            # chequer lino 30 cm: beige / brown
        chk = ((np.floor(x / 0.30) + np.floor(y / 0.30)) % 2).astype(np.float32)
        c = np.where((chk > 0)[:, None], lin(150, 110, 76), lin(206, 190, 160)) * (0.94 + 0.10 * n_lo)[:, None]
        c = mixc(c, lin(168, 140, 110), w * 0.45)
        gr = np.maximum(gline(dist_periodic(x, 0.30), 0.0015, aa), gline(dist_periodic(y, 0.30), 0.0015, aa)) * 0.4
    elif z == MS.Z_FL_LINOG:                                         # olive lino, marbled
        marb = fbm(P * np.array([1, 2.5, 1], np.float32), 4.0, 4, seed=412)
        c = lin(100, 108, 70) * (0.86 + 0.24 * marb)[:, None]
        c = mixc(c, lin(130, 132, 100), w * 0.4)
    elif z == MS.Z_FL_CARPET:                                        # blue-grey needle felt, worn grey
        c = tone(lin(82, 92, 112), n_lo, n_hi, 0.10, 0.30) * (0.9 + 0.2 * fbm(P, 120.0, 1, seed=413))[:, None]
        c = mixc(c, lin(120, 120, 120), w * 0.45)
        cof = ss(0.86, 0.95, fbm(P, 2.5, 2, seed=414))
        c = mixc(c, lin(60, 50, 40), cof * 0.5)
    elif z == MS.Z_FL_RAISED:                                        # raised floor 60 cm panels
        bi = np.floor(x / 0.60) * 37.0 + np.floor(y / 0.60) * 101.0
        c = lin(166, 168, 166) * (0.92 + 0.10 * hash1(bi, 8))[:, None]
        jt = np.maximum(gline(dist_periodic(x, 0.60), 0.003, aa), gline(dist_periodic(y, 0.60), 0.003, aa))
        c = mixc(c, lin(60, 62, 62), jt)
        c = mixc(c, lin(130, 130, 126), w * 0.3)
        gr = jt * 0.8
    elif z == MS.Z_FL_BOARDS:                                        # varnished boards along x
        bi, seam = boards(y, 0.12, aa, 0.0015)
        g = fbm(P * np.array([0.08, 1.0, 1.0], np.float32) + (bi * 3.3)[:, None], 20.0, 2, seed=415)
        c = lin(140, 92, 54) * (0.80 + 0.20 * hash1(bi, 9) + 0.16 * (g - 0.5))[:, None]
        c = mixc(c, lin(170, 130, 90), w * 0.45)
        gr = seam * 0.6
    elif z == MS.Z_FL_GARAGE:                                        # garage concrete: oil, tyre tracks, mud from the gate
        c = tone(lin(126, 124, 118), n_lo, n_hi, 0.18, 0.22)
        oil = ss(0.70, 0.88, fbm(P, 0.9, 3, seed=416)) * np.exp(-((x + 12.4) / 2.0) ** 2)
        c = mixc(c, OIL, oil * 0.6)
        track = (np.exp(-((x + 15.6) / 0.15) ** 2) + np.exp(-((x + 14.0) / 0.15) ** 2)) * ss(4.5, -4.5, y)
        c = mixc(c, lin(70, 64, 54), np.clip(track, 0, 1) * 0.35 * n_mid)
        c = mixc(c, lin(96, 84, 66), ss(-3.0, -4.7, y) * 0.4 * ss(0.4, 0.8, n_mid))
    else:                                                            # concrete floors, painted grey in the plant rooms
        painted = np.isin(ri, [i for i, (n, _) in enumerate(ROOMS) if n in ('Heizung', 'Schaltraum', 'Flur_UG', 'Lager')])
        c = np.where(painted[:, None], tone(lin(140, 142, 138), n_lo, n_hi, 0.10, 0.12), tone(lin(128, 126, 120), n_lo, n_hi))
        c = mixc(c, lin(112, 110, 104), w * 0.4)
        c = mixc(c, lin(160, 158, 150), ss(0.55, 0.80, fbm(P, 2.0, 3, seed=417)) * 0.25 * (1 - painted))
        boiler = np.exp(-(((x - 6.2) / 0.9) ** 2 + ((y + 1.9) / 0.6) ** 2)) * (P[:, 2] < -2.5)
        c = mixc(c, OIL, boiler * 0.45 * ss(0.3, 0.7, n_mid))
    c = mixc(c, GRIME, cav * 0.45)
    c = mixc(c, DUST, ss(0.6, 0.9, n_mid) * 0.12)
    return c, gr


def stair(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 421)
    c = tone(lin(150, 148, 142), n_lo, n_hi, 0.14, 0.2)
    c = mixc(c, lin(120, 116, 108), up * ss(0.5, 0.8, n_mid) * 0.4)
    c = mixc(c, lin(176, 174, 166), edge * 0.5)
    c = mixc(c, GRIME, cav * 0.5)
    return c, None


def skirting(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 431)
    c = tone(lin(52, 42, 34), n_lo, n_hi, 0.10, 0.2)
    c = mixc(c, lin(120, 110, 96), ss(0.75, 0.92, fbm(P, 30.0, 2, seed=432)) * 0.35)
    return c, None


def sill_in(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 441)
    sp = hash1(np.floor(P[:, 0] * 160) + np.floor(P[:, 1] * 167) * 131.0 + np.floor(P[:, 2] * 151) * 17.0, 2)
    c = lin(214, 210, 200) * (0.94 + 0.06 * n_lo)[:, None]
    c = mixc(c, lin(120, 110, 100), ss(0.80, 0.95, sp) * 0.6)
    c = mixc(c, DUST, up * 0.2 + cav * 0.3)
    return c, None


# ================================================================ painted metal, wood, the furniture's materials
def paint(base, P, N, ao, seed, chips=0.6, outdoor_fade=True, dust=0.25):
    """a painted surface: tone, chalky where it faces the outside, chipped to primer / rust on the edges, dust on top"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, seed)
    c = tone(base, n_lo, n_hi, 0.12, 0.14)
    if outdoor_fade:
        out = (facing_room(P, N) < 0).astype(np.float32)
        c = mixc(c, c * 1.25 + 0.04, out * ss(0.4, 0.8, n_lo) * 0.45)
        c = mixc(c, lin(70, 66, 56), out * ss(0.5, 0.85, fbm(P * np.array([1, 1, 0.12], np.float32), 6.0, 3,
                                                                seed=seed + 7)) * 0.35)
    ch = np.clip(edge * chips + ss(0.82, 0.93, fbm(P, 40.0, 2, seed=seed + 5)) * chips * 0.5, 0, 0.9)
    c = mixc(c, np.where((ss(0.5, 0.7, n_mid) > 0.5)[:, None], PRIMER, RUST_D), ch * 0.7)
    c = mixc(c, DUST, up * dust)
    c = mixc(c, GRIME, cav * 0.4)
    return c


def steel_paint(P, N, ao, aa, z):
    base = MO.DRAFT_COL.get(z) or F.DRAFT_COL.get(z) or (120, 120, 116)
    if z in (MO.Z_WINFRAME, MO.Z_SASH, MO.Z_DOORFRAME, MO.Z_LEAF_S, MO.Z_LEAF_F, MO.Z_GATE, F.Z_FASCIA):
        base = (104, 118, 94)
    return paint(lin(*base), P, N, ao, 451 + (z % 37)), None


def wood_door(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 461)
    c = tone(lin(224, 218, 200), n_lo, n_hi, 0.08, 0.08)
    f, ri = floor_of(P, N)
    c = mixc(c, lin(150, 140, 120), ss(0.35, 0.0, P[:, 2] - f) * ss(0.4, 0.75, n_mid) * 0.5)        # kicked low down
    c = mixc(c, lin(140, 126, 100), ss(0.10, 0.0, np.abs(P[:, 2] - f - 1.05)) * 0.25)               # round the handle
    c = mixc(c, lin(120, 108, 90), edge * 0.6)
    return mixc(c, GRIME, cav * 0.4), None


def alu(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 471)
    br = fbm(P * np.array([1.0, 1.0, 12.0], np.float32), 30.0, 1, seed=472)
    c = lin(176, 178, 176) * (0.84 + 0.22 * br)[:, None]
    c = mixc(c, lin(120, 122, 120), cav * 0.5 + ss(0.7, 0.9, n_mid) * 0.2)
    return mixc(c, DUST, up * 0.2), None


def shutter(P, N, ao, aa, z):
    """the roller shutter's slats (5 cm, a dark groove between), grey, grime in the grooves"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 481)
    sl = gline(dist_periodic(P[:, 2], 0.05), 0.004, aa)
    c = tone(lin(150, 152, 146), n_lo, n_hi, 0.10, 0.12) * (0.94 + 0.08 * np.cos(2 * np.pi * P[:, 2] / 0.05))[:, None]
    c = mixc(c, lin(70, 70, 66), sl * 0.8)
    c = mixc(c, lin(100, 96, 86), ss(0.6, 0.85, fbm(P * np.array([1, 1, 0.2], np.float32), 6.0, 2, seed=482)) * 0.3)
    return c, sl * 0.7


def rubber(P, N, ao, aa, z, base=(30, 30, 30)):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 491)
    c = tone(lin(*base), n_lo, n_hi, 0.08, 0.25)
    return mixc(c, DUST, up * 0.2 + edge * 0.15), None


def chrome(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 501)
    refl = 0.5 + 0.5 * np.clip(N[:, 2] * 0.8 + 0.3 * N[:, 0], -1, 1)
    c = mixc(lin(70, 74, 80), lin(226, 228, 230), refl * (0.7 + 0.3 * n_hi))
    c = mixc(c, lin(120, 100, 80), ss(0.75, 0.92, fbm(P, 30.0, 2, seed=502)) * 0.3)
    return mixc(c, DUST, up * 0.15), None


def metal_tone(base, seed, oxide=None):
    def fn(P, N, ao, aa, z):
        n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, seed)
        c = tone(lin(*base), n_lo, n_hi, 0.12, 0.20)
        if oxide is not None:
            c = mixc(c, lin(*oxide), ss(0.55, 0.85, fbm(P, 12.0, 3, seed=seed + 1)) * 0.5 + cav * 0.3)
        c = mixc(c, c * 1.3, edge * 0.5)
        return mixc(c, DUST, up * 0.2), None
    return fn


def woodgrain(base, seed, along=0):
    def fn(P, N, ao, aa, z):
        n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, seed)
        st = np.array([1.0, 1.0, 1.0], np.float32)
        st[along] = 0.06
        g = fbm(P * st, 22.0, 2, seed=seed + 1)
        c = lin(*base) * (0.84 + 0.30 * (g - 0.5) + 0.10 * (n_lo - 0.5))[:, None]
        c = mixc(c, lin(70, 50, 34), cav * 0.4 + ss(0.75, 0.92, n_hi) * 0.15)
        c = mixc(c, c * 1.2, edge * 0.4)
        return mixc(c, DUST, up * 0.2), None
    return fn


def flat(base, seed, rough=0.10, dust=0.25, edge_l=0.25, stain=None):
    """plastics, enamel, laminate, paper: a flat colour, tone, dust on top, grime in the corners, lighter worn edges"""
    def fn(P, N, ao, aa, z):
        n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, seed)
        c = tone(lin(*base), n_lo, n_hi, rough, rough)
        if stain is not None:
            c = mixc(c, lin(*stain), ss(0.70, 0.90, fbm(P, 6.0, 3, seed=seed + 1)) * 0.35)
        c = mixc(c, c * 1.15 + 0.02, edge * edge_l)
        c = mixc(c, DUST, up * dust)
        return mixc(c, GRIME, cav * 0.35), None
    return fn


def fabric(base, seed):
    def fn(P, N, ao, aa, z):
        n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, seed)
        weave = fbm(P, 160.0, 1, seed=seed + 1)
        c = tone(lin(*base), n_lo, n_hi, 0.10, 0.12) * (0.90 + 0.18 * weave)[:, None]
        c = mixc(c, lin(70, 60, 50), ss(0.75, 0.92, fbm(P, 3.0, 3, seed=seed + 2)) * 0.25)
        return mixc(c, GRIME, cav * 0.45), None
    return fn


def books(P, N, ao, aa, z):
    """book spines: a colour per book (the book's own box), titles as light bands"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 511)
    key = np.floor(P[:, 0] * 25.0) + np.floor(P[:, 2] * 2.8) * 57.0
    pal = np.array([lin(120, 40, 34), lin(40, 60, 110), lin(60, 90, 60), lin(150, 120, 60), lin(80, 60, 50),
                    lin(170, 160, 140), lin(30, 30, 34), lin(110, 70, 90)], np.float32)
    c = pal[(hash1(key, 3) * 8).astype(np.int32) % 8] * (0.9 + 0.1 * n_hi)[:, None]
    band = (np.abs(np.mod(P[:, 2] + 0.03, 0.36) - 0.18) < 0.012).astype(np.float32)
    c = mixc(c, lin(210, 196, 150), band * 0.7 * (N[:, 1] < -0.5))
    return mixc(c, DUST, up * 0.35), None


def console(P, N, ao, aa, z):
    """the control consoles: grey-green steel, on the sloped panel rows of lamps, square meters and labels"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 521)
    c = paint(lin(140, 146, 138), P, N, ao, 522, chips=0.25, outdoor_fade=False, dust=0.15)
    if z == F.Z_CONSOLEP:
        u = P[:, 0]
        v = P[:, 2]
        cell = (np.abs(dist_periodic(u, 0.05)) < 0.012) & (np.abs(dist_periodic(v, 0.06)) < 0.010)
        lampcol = np.array([lin(180, 40, 30), lin(60, 140, 70), lin(200, 160, 40), lin(220, 220, 210)], np.float32)
        pick = (hash1(np.floor(u / 0.05) * 7.0 + np.floor(v / 0.06) * 31.0, 4) * 4).astype(np.int32) % 4
        c = np.where(cell[:, None], lampcol[pick] * 0.8, c)
        meter = (np.abs(dist_periodic(u, 0.60, 0.15)) < 0.09) & (np.abs(dist_periodic(v - 1.25, 1.0)) < 0.05)
        c = np.where(meter[:, None], lin(226, 222, 206), c)
        lab = (np.abs(dist_periodic(v, 0.06, 0.03)) < 0.004) & ~cell
        c = mixc(c, lin(200, 200, 190), lab * 0.4)
    return c, None


def radiator(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 531)
    c = tone(lin(236, 234, 226), n_lo, n_hi, 0.06, 0.06)
    c = mixc(c, lin(196, 186, 160), up * 0.5 + ss(0.75, 0.92, n_mid) * 0.2)                        # yellowed, dusty top
    c = mixc(c, lin(150, 110, 80), edge * 0.35)
    return mixc(c, lin(140, 136, 126), cav * 0.6), None


def screen(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 541)
    refl = 0.5 + 0.5 * np.clip(N[:, 2] * 0.6 + N[:, 0] * 0.3, -1, 1)
    c = mixc(lin(16, 22, 22), lin(60, 70, 72), refl * 0.6)
    return mixc(c, DUST, up * 0.3 + ss(0.7, 0.9, n_mid) * 0.15), None


def crate(P, N, ao, aa, z):
    """army-green crates (painted planks, stencil band) and raw pallet wood"""
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 551)
    s = np.where(np.abs(N[:, 2]) > 0.6, P[:, 0], along_wall(P, N))
    bi, seam = boards(P[:, 2] if True else s, 0.10, aa, 0.003)
    if z == F.Z_PALLET:
        g = fbm(P * np.array([1, 0.08, 1], np.float32), 20.0, 2, seed=552)
        c = lin(170, 140, 98) * (0.82 + 0.24 * (g - 0.5) + 0.1 * hash1(bi, 3))[:, None]
    else:
        c = tone(lin(90, 100, 66), n_lo, n_hi, 0.12, 0.2) * (0.94 + 0.08 * hash1(bi, 5))[:, None]
        sten = (np.abs(dist_periodic(P[:, 2], 0.5, 0.2)) < 0.02) & (np.abs(dist_periodic(s, 0.08)) < 0.025)
        c = mixc(c, lin(220, 216, 196), sten * 0.7 * (np.abs(N[:, 2]) < 0.5))
    c = mixc(c, lin(60, 56, 44), edge * 0.4 + cav * 0.4)
    return mixc(c, DUST, up * 0.3), seam * 0.5


def drum(P, N, ao, aa, z):
    base = F.DRAFT_COL.get(z, (128, 128, 128))
    c = paint(lin(*base), P, N, ao, 561, chips=0.8, outdoor_fade=False)
    return c, None


def gauge_face(P, N, ao, aa, z):
    return flat((236, 236, 230), 571, rough=0.04, dust=0.1)(P, N, ao, aa, z)


def lens_tile(P, N, ao, aa, z):
    return np.tile(lin(240, 240, 236), (len(P), 1)), None


def grating(P, N, ao, aa, z):
    n_lo, n_mid, n_hi, up, cav, edge = common(P, N, ao, 581)
    holes = (np.abs(dist_periodic(P[:, 0], 0.03)) > 0.004) & (np.abs(dist_periodic(P[:, 1], 0.03)) > 0.004)
    c = np.where(holes[:, None], lin(40, 40, 40), lin(150, 152, 148))
    return c, None


# ================================================================ the zone table
def _table():
    T = {}
    for z in (MS.Z_FACADE, MS.Z_BAND, MS.Z_PARIN, MS.Z_REVEALX, MS.Z_SLABEDGE):
        T[z] = facade
    T[MS.Z_PLINTH] = plinth
    T[MS.Z_ROOF] = roof
    T[MS.Z_UPSTAND] = upstand
    T[MS.Z_BRICK] = brick
    for z in (MS.Z_PLASTER, MS.Z_DADO, MS.Z_STRIPE):
        T[z] = wall_paint
    T[MS.Z_TILEW] = tiles
    T[MS.Z_FL_TILE] = tiles
    T[MS.Z_VENEERW] = veneer
    for z in (MS.Z_CEIL, MS.Z_CEILT, MS.Z_CEILB, MS.Z_CONCIN):
        T[z] = ceiling
    for z in (MS.Z_FL_LINO, MS.Z_FL_LINOG, MS.Z_FL_CARPET, MS.Z_FL_RAISED, MS.Z_FL_BOARDS, MS.Z_FL_CONC, MS.Z_FL_GARAGE):
        T[z] = floors
    T[MS.Z_STAIR] = stair
    T[MS.Z_SOFFIT] = stair
    T[MS.Z_BASEB] = skirting
    T[MS.Z_SILLIN] = sill_in
    T[K.Z_GALV] = galv
    T[K.Z_STEELBLK] = steel_black
    # openings
    for z in (MO.Z_WINFRAME, MO.Z_SASH, MO.Z_DOORFRAME, MO.Z_LEAF_S, MO.Z_LEAF_F, MO.Z_GATE, MO.Z_SHUTEND, MO.Z_CLOSER,
              MO.Z_HINGE, MO.Z_PANIC):
        T[z] = steel_paint
    T[MO.Z_LEAF_W] = wood_door
    for z in (MO.Z_WINHANDLE, MO.Z_HANDLE, MO.Z_ALUFRAME, MO.Z_KICK, MO.Z_THRESH, MO.Z_SHUTRAIL, MO.Z_TRACK):
        T[z] = alu
    T[MO.Z_SHUTTER] = shutter
    T[MO.Z_SILLOUT] = galv
    T[MO.Z_RUBBER] = rubber
    T[MO.Z_STRAP] = lambda P, N, ao, aa, z: rubber(P, N, ao, aa, z, (90, 90, 86))
    T[MO.Z_BOXCOVER] = flat((230, 226, 214), 591)
    T[MO.Z_WINDER] = flat((220, 216, 204), 592)
    T[MO.Z_LOCK] = metal_tone((190, 170, 90), 593, (110, 90, 50))
    # furniture: painted steel
    for z in (F.Z_STEELF, F.Z_CABGREY, F.Z_DRAWER, F.Z_LOCKER, F.Z_OLIVE, F.Z_BOARDC, F.Z_SAFE, F.Z_RACK, F.Z_RACKDOOR,
              F.Z_RACKEQ, F.Z_CHAIRBASE, F.Z_EXTING, F.Z_CALLPT, F.Z_BELL, F.Z_TANKG, F.Z_PUMPG, F.Z_BURNER, F.Z_BOILER,
              F.Z_QUAD, F.Z_TOOL, F.Z_JERRY, F.Z_MAINSW, F.Z_BAR, F.Z_FASCIA, F.Z_CABGREY):
        T[z] = steel_paint
    for z in (F.Z_DRUM_R, F.Z_DRUM_B):
        T[z] = drum
    T[F.Z_CONSOLE] = console
    T[F.Z_CONSOLEP] = console
    T[F.Z_RADIATOR] = radiator
    T[F.Z_SCREEN] = screen
    T[F.Z_SCREENP] = screen
    T[F.Z_MIRROR] = lambda P, N, ao, aa, z: (mixc(screen(P, N, ao, aa, z)[0], lin(170, 186, 196), np.full(len(P), 0.6)),
                                             None)
    for z in (F.Z_CRATE, F.Z_PALLET):
        T[z] = crate
    T[F.Z_BOOKS] = books
    T[F.Z_GAUGE] = gauge_face
    T[F.Z_GRATING] = grating
    T[F.Z_CHROME] = chrome
    T[F.Z_HANDLEB] = chrome
    T[F.Z_SINK] = chrome
    T[F.Z_TRAY] = galv
    T[F.Z_BRASS] = metal_tone((200, 170, 80), 601, (110, 100, 50))
    T[F.Z_COPPER] = metal_tone((190, 110, 60), 602, (90, 120, 90))
    T[F.Z_VALVE] = flat((220, 220, 216), 603)
    T[F.Z_PIPE_W] = flat((226, 224, 216), 604)
    for z, base in ((F.Z_RUBBERB, (30, 30, 30)), (F.Z_TYRE, (24, 24, 24)), (F.Z_BOOT, (30, 30, 28)),
                    (F.Z_CABLE, (28, 28, 28)), (F.Z_BREAKER, (34, 34, 34)), (F.Z_MAT, (60, 60, 56)),
                    (F.Z_QUADSEAT, (30, 30, 30))):
        T[z] = (lambda b: (lambda P, N, ao, aa, z: rubber(P, N, ao, aa, z, b)))(base)
    for z, base, sd in ((F.Z_WOODF, (150, 104, 62), 0), (F.Z_WOODSHELF, (150, 110, 70), 0), (F.Z_PEGBOARD, (190, 160, 110), 2),
                        (F.Z_MAPTABLE, (140, 110, 80), 0)):
        T[z] = woodgrain(base, 611 + z % 13, sd)
    for z in (F.Z_CHAIRSEAT, F.Z_MATTRESS, F.Z_BLANKET, F.Z_PILLOW, F.Z_FABRIC_B, F.Z_FABRIC_G, F.Z_JACKET, F.Z_BAG,
              F.Z_TOWEL, F.Z_CURTAIN):
        T[z] = fabric(F.DRAFT_COL[z], 621 + z % 17)
    for z in (F.Z_DESKTOP, F.Z_LAMINATE, F.Z_TILESPL, F.Z_TV, F.Z_ENAMELW, F.Z_STOVE, F.Z_SHOWER, F.Z_TROUGH, F.Z_WASHM,
              F.Z_CUBICLE, F.Z_CYL, F.Z_INSUL, F.Z_PCBEIGE, F.Z_KEYB, F.Z_CRT, F.Z_PHONE, F.Z_SOCKET, F.Z_SWITCHP,
              F.Z_ROCKER, F.Z_SMOKE, F.Z_SPEAKER, F.Z_CLOCK, F.Z_BOARD, F.Z_SIGN, F.Z_FIRSTAID, F.Z_LED, F.Z_PAPER,
              F.Z_BINDER, F.Z_CARDBOX, F.Z_MAP, F.Z_MUG, F.Z_PLATE, F.Z_DISH):
        T[z] = flat(F.DRAFT_COL[z], 631 + z % 19, stain=(150, 130, 100) if z in (F.Z_PAPER, F.Z_CARDBOX, F.Z_INSUL) else None)
    # fixtures
    for z in (FX.Z_FX_WHITE, FX.Z_FX_ENAMELW, FX.Z_FX_POLY, FX.Z_FX_REFL, FX.Z_FX_LOUVRE):
        T[z] = flat(FX.DRAFT_COL[z], 641 + z % 7, dust=0.35)
    for z in (FX.Z_FX_ALU, FX.Z_FX_CAGE, FX.Z_FX_FLOOD, FX.Z_FX_GREEN):
        T[z] = (lambda b: (lambda P, N, ao, aa, z: (paint(lin(*b), P, N, ao, 651, chips=0.4), None)))(FX.DRAFT_COL[z])
    T[FX.Z_FX_CHROME] = chrome
    T[FX.Z_FX_CABLE] = T[F.Z_CABLE]
    return T


TABLE = _table()


def paint_main(Pp, Nn, Z, ao, aa):
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
