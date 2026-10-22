"""Painter for the generator container's building atlas Cont (psxbake): outside, inside, both in one (paint_cont_all).
painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None); positions in the container frame (cont_kit).
Outside: two boxes in weathered blue-grey (the south one a shade bluer, the north one greyer), chalky roofs with rust
rings, rusty bottom rails and castings with their apertures, forklift pockets, rust runs down the corrugation, fresher
paint round the cut-ins (window, louvre, intakes), the owner codes and the KEEP CLEAR stencil painted on; galvanised
hardware, black steel, the rusty stack, concrete pads, the chequer step, the enamel barn light.
Inside: the generator shed's own painter rules (gen_paint.paint_shed) at this room's positions: the birch-ply lining
(sheet seams, nail lines, grime low, soot by the exhaust, hand marks at the switch and the board), the stained
concrete floor (oil under the genset, the tank valve, drum 1, the separator; mud trodden in from the doors; control
joints), raw spruce, the corrugated roof's underside with rust runs, raw boards on the door leaves and the shutter,
the white window frame, the shed's metals. paint_cont_all: both in one building atlas, as the shed's."""
import numpy as np
import pxfont as F
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, boards, hash1
import gen_kit as K
import cont_kit as CK
from gen_paint import OIL, GRIME, DUST, RUST, RUST_D, _T, _common, run_m

PAINT = {CK.Z_CPAINT_S: lin(70, 100, 124), CK.Z_CPAINT_N: lin(80, 102, 112)}
PATCH = {CK.Z_CPAINT_S: lin(54, 92, 128), CK.Z_CPAINT_N: lin(62, 96, 120)}       # the repaint round the cut-ins
CHALK = lin(150, 160, 164)
WHITE_P = lin(214, 214, 204)
YEL_P = lin(214, 176, 52)
IN_GREY = lin(150, 154, 148)


def _mask(lines, font=F.F57, gap=3):
    ms = [F.text_mask(t, font) for t in lines]
    W = max(m.shape[1] for m in ms)
    H = sum(m.shape[0] for m in ms) + gap * (len(ms) - 1)
    out = np.zeros((H, W), bool)
    y = 0
    for m in ms:
        x = (W - m.shape[1]) // 2
        out[y:y + m.shape[0], x:x + m.shape[1]] = m
        y += m.shape[0] + gap
    return out


# painted markings: (axis, normal sign, plane, plane tolerance, (u centre, z centre), letter height m, lines, colour, font)
# u = the viewer's left -> right on that face
MARKS = [
    ('x', -1, -2.987, 0.02, (-1.83, 2.43), 0.090, ['OBSU 204617 2'], WHITE_P, F.F57),           # Door_R, top
    ('x', -1, -2.987, 0.02, (-1.56, 2.27), 0.065, ['22G1'], WHITE_P, F.F57),
    ('y', -1, -2.412, 0.03, (2.05, 2.50), 0.090, ['OBSU 204617 2'], WHITE_P, F.F57),             # south wall, east end
    ('y', -1, -2.412, 0.03, (2.30, 2.36), 0.065, ['22G1'], WHITE_P, F.F57),
    ('x', 1, 3.003, 0.03, (-1.22, 2.48), 0.090, ['OBSU 204617 2'], WHITE_P, F.F57),             # south box front
    ('y', 1, 2.412, 0.03, (-2.00, 2.50), 0.090, ['KRSU 381502 9'], WHITE_P, F.F57),               # north wall, west end
    ('x', 1, 3.003, 0.03, (1.22, 2.48), 0.090, ['KRSU 381502 9'], WHITE_P, F.F57),              # north box front
    ('x', -1, -2.987, 0.02, (0.612, 1.85), 0.070, ['KRSU 381502 9'], WHITE_P, F.F57),           # north box doors
    ('x', 1, 3.003, 0.03, (-1.015, 1.80), 0.070, ['FREIHALTEN'], YEL_P, F.F57),                 # over the radiator louvre
    ('x', 1, 3.003, 0.03, (-1.015, 1.70), 0.050, ['KEEP CLEAR'], YEL_P, F.F57),
]
_MASKS = [_mask(m[6], m[8]) for m in MARKS]


def _u(Pp, axis, sign):
    if axis == 'x':
        return Pp[:, 1] * sign                       # -x face: viewer's right is -y; +x face: +y
    return -Pp[:, 0] * sign                          # -y face: right is +x; +y face: -x


def marks(Pp, Nn, sel):
    """(paint mask, colour) of the stencilled markings on the texels `sel`"""
    n = len(Pp)
    hit = np.zeros(n, bool)
    col = np.zeros((n, 3), np.float32)
    for (axis, sg, plane, tol, (uc, zc), h, lines, c, font), M in zip(MARKS, _MASKS):
        ai = 0 if axis == 'x' else 1
        px = h / font['h']
        H, W = M.shape
        u = _u(Pp, axis, sg)
        ucs = uc * sg if axis == 'x' else -uc * sg
        u0, z1 = ucs - W * px / 2, zc + H * px / 2
        cand = sel & (Nn[:, ai] * sg > 0.6) & (np.abs(Pp[:, ai] - plane) < tol)
        ci = ((u - u0) / px).astype(np.int64)
        ri = ((z1 - Pp[:, 2]) / px).astype(np.int64)
        ok = cand & (ci >= 0) & (ci < W) & (ri >= 0) & (ri < H)
        idx = np.where(ok)[0]
        on = M[ri[idx], ci[idx]]
        hit[idx[on]] = True
        col[idx[on]] = c
    return hit, col


def rect_d(a, b, a0, a1, b0, b1):
    """distance outside the rectangle (0 inside)"""
    da = np.maximum(np.maximum(a0 - a, a - a1), 0.0)
    db = np.maximum(np.maximum(b0 - b, b - b1), 0.0)
    return np.hypot(da, db)


def rect_in(a, b, a0, a1, b0, b1, wob=None, w=0.0):
    """smooth inside mask of a rectangle with a wobbly edge (wob ~ noise 0..1)"""
    e = 0.0 if wob is None else (wob - 0.5) * w
    da = np.minimum(a - a0, a1 - a) + e
    db = np.minimum(b - b0, b1 - b) + e
    return ss(-0.01, 0.01, np.minimum(da, db))


# ---------------------------------------------------------------- shared metals and odds
def steel_black(Pp, T, edge, seed):
    c = T(lin(36, 36, 36), 0.12, 0.2)
    return mixc(c, RUST, np.clip(edge * 0.7 + ss(0.72, 0.86, fbm(Pp, 30.0, 2, seed=seed)) * 0.5, 0, 0.8))


def galv(Pp, T, seed):
    spang = fbm(Pp, 90.0, 1, seed=seed)
    c = T(lin(150, 154, 152), 0.10, 0.08) * (0.88 + 0.22 * spang)[:, None]
    c = mixc(c, lin(196, 198, 192), ss(0.78, 0.90, fbm(Pp, 25.0, 2, seed=seed + 1)) * 0.4)
    return mixc(c, RUST, run_m(Pp) * 0.35)


def chequer(Pp, T, n_mid, seed_dirt=0.0):
    x, y = Pp[:, 0], Pp[:, 1]
    u_, v_ = (x + y) / 0.035, (x - y) / 0.035
    dia = (1 - ss(0.10, 0.22, np.abs(u_ - np.round(u_)))) * (1 - ss(0.25, 0.45, np.abs(v_ - np.round(v_))))
    c = T(lin(124, 124, 120), 0.12, 0.16) * (0.85 + 0.25 * dia)[:, None]
    return mixc(c, lin(70, 66, 60), ss(0.5, 0.85, n_mid) * 0.4 + seed_dirt), (1 - dia) * 0.25


def timber(Pp, Nn, T, cav, up, n_mid, seed):
    vert = np.abs(Nn[:, 2]) < 0.6
    g2 = fbm(Pp * np.where(vert[:, None], np.array([4.0, 4.0, 0.25], np.float32), np.array([0.3, 4.0, 4.0], np.float32)), 10.0, 2,
             seed=seed)
    c = T(lin(150, 118, 78), 0.16, 0.12) * (0.86 + 0.22 * g2)[:, None]
    c = mixc(c, lin(92, 72, 50), cav * 0.55 + ss(0.6, 0.9, n_mid) * 0.2)
    return mixc(c, DUST, up * 0.25)


def concrete(Pp, T, cav, up, z):
    c = T(lin(132, 130, 124), 0.16, 0.22)
    c = mixc(c, lin(86, 82, 76), ss(0.05, 0.0, z) * 0.8 + cav * 0.4)
    return mixc(c, lin(160, 158, 150), up * 0.3)


# ================================================================ outside
def paint_cont(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 501)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    side = np.abs(Nn[:, 2]) < 0.5
    wob = fbm(Pp, 9.0, 2, seed=511)
    # ---- container paint (both boxes): walls, posts, rails, doors outside
    pm = M(CK.Z_CPAINT_S) | M(CK.Z_CPAINT_N)
    base = np.where(M(CK.Z_CPAINT_S)[:, None], PAINT[CK.Z_CPAINT_S], PAINT[CK.Z_CPAINT_N])
    c = base * (0.86 + 0.20 * (n_lo - 0.5) + 0.10 * (n_hi - 0.5))[:, None]
    # repaint round the cut-ins (window, louvre, intakes, mast fitting)
    patch = np.zeros(n, np.float32)
    s_wall = (Nn[:, 1] < -0.6) & (y < -2.3)
    patch = np.maximum(patch, rect_in(x, z, -0.62, 0.42, 1.30, 2.22, wob, 0.10) * s_wall)
    patch = np.maximum(patch, rect_in(x, z, -1.34, -1.06, 2.18, 2.44, wob, 0.06) * s_wall)
    e_wall = (Nn[:, 0] > 0.6) & (x > 2.9)
    patch = np.maximum(patch, rect_in(y, z, -1.74, -0.29, 0.50, 1.88, wob, 0.10) * e_wall)
    w_door = (Nn[:, 0] < -0.6) & (x < -2.9) & (y > 0)
    for h in CK.INTAKES:
        patch = np.maximum(patch, rect_in(y, z, h['y0'] - 0.10, h['y1'] + 0.10, h['z0'] - 0.12, h['z1'] + 0.08, wob, 0.06) * w_door)
    pc = np.where(M(CK.Z_CPAINT_S)[:, None], PATCH[CK.Z_CPAINT_S], PATCH[CK.Z_CPAINT_N]) * (0.92 + 0.12 * (n_hi - 0.5))[:, None]
    c = mixc(c, pc, patch * 0.9)
    # fade: chalky high up and on the sunny south side
    c = mixc(c, CHALK, (ss(1.2, 2.7, z) * 0.22 + (Nn[:, 1] < -0.5) * 0.10) * (1 - 0.6 * patch) * (0.6 + 0.4 * n_mid))
    # rust: spots, runs down the corrugation, edges, the bottom band, round the cut edges
    spots = ss(0.70, 0.84, fbm(Pp, 6.0, 3, seed=512)) * (0.4 + 0.6 * ss(1.4, 0.3, z))
    runs = ss(0.60, 0.82, fbm(Pp * np.array([1, 1, 0.09], np.float32), 8.0, 3, seed=513)) * side
    runs = runs * (0.25 + 0.75 * ss(0.72, 0.55, fbm(Pp * np.array([1, 1, 0.3], np.float32), 3.0, 2, seed=514)))
    bottom = ss(0.62, 0.20, z)
    cut = np.zeros(n, np.float32)
    cut = np.maximum(cut, ss(0.06, 0.0, rect_d(x, z, CK.WIN['x0'], CK.WIN['x1'], CK.WIN['z0'], CK.WIN['z1'])) * s_wall)
    cut = np.maximum(cut, ss(0.07, 0.0, rect_d(y, z, CK.LOUV['y0'], CK.LOUV['y1'], CK.LOUV['z0'], CK.LOUV['z1'])) * e_wall)
    rust_m = np.clip(spots * 0.7 + runs * 0.45 + edge * 0.55 + bottom * (0.5 + 0.4 * n_mid) + cut * 0.6 * n_mid, 0, 1)
    rust_m *= (1 - 0.55 * patch)
    c = mixc(c, RUST_D, rust_m * 0.75)
    c = mixc(c, RUST, ss(0.5, 1.0, rust_m) * 0.5 * n_hi)
    c = mixc(c, lin(60, 56, 50), ss(0.45, 0.10, z) * 0.45)                         # splash at the foot
    # forklift pockets in the bottom side rails
    pocket = (np.abs(Nn[:, 1]) > 0.7) & (z < 0.31) & (np.abs(np.abs(x) - 1.025) < 0.178) & (z > 0.175) & (z < 0.29)
    c = np.where(pocket[:, None], lin(26, 24, 22), c)
    # door hardware wear: round the handles and catches, the bottom of the leaves
    leaf = (x < -2.95) & (Nn[:, 0] < -0.6)
    hand = np.zeros(n, np.float32)
    for yb_ in list(CK.LEAVES['Door_R'][4]) + list(CK.LEAVES['Door_L'][4]):
        hand += np.exp(-(((y - yb_ + CK.HANDLE_L) / 0.08) ** 2 + ((z - CK.HANDLE_Z) / 0.10) ** 2))
    c = mixc(c, lin(66, 58, 50), np.clip(hand, 0, 1) * leaf * 0.55)
    hit, mcol = marks(Pp, Nn, pm)
    chip = ss(0.30, 0.45, fbm(Pp, 40.0, 2, seed=515))
    c = np.where((hit & (chip > 0.5))[:, None], mcol * (0.85 + 0.2 * n_hi)[:, None] * (1 - 0.4 * rust_m)[:, None], c)
    col[pm] = c[pm]
    # ---- roofs: chalky, transverse ribs painted, rust rings where water stands, the joint
    m = M(CK.Z_CROOF)
    ribs = 0.90 + 0.10 * np.cos(2 * np.pi * x / 0.28)
    c = np.where((y < 0)[:, None], PAINT[CK.Z_CPAINT_S], PAINT[CK.Z_CPAINT_N]) * ribs[:, None]
    c = mixc(c, CHALK, 0.35 + 0.2 * n_mid)
    pool = ss(0.62, 0.78, fbm(Pp * np.array([1, 1, 0], np.float32), 1.6, 3, seed=516))
    ring = ss(0.02, 0.0, np.abs(fbm(Pp * np.array([1, 1, 0], np.float32), 1.6, 3, seed=516) - 0.66))
    c = mixc(c, RUST_D, np.clip(pool * 0.55 + ring * 0.5 + ss(0.72, 0.86, fbm(Pp, 9.0, 2, seed=517)) * 0.5, 0, 0.85))
    c = mixc(c, lin(90, 84, 76), ss(0.30, 0.0, np.abs(y)) * 0.4 + ss(0.20, 0.0, np.minimum(np.abs(x - 2.93), np.abs(x + 2.82))) * 0.3)
    col[m] = c[m]
    gr = np.where(m, gline(dist_periodic(x, 0.28, 0.14), 0.012, aa) * 0.35, gr)
    # ---- castings: paint worn to rust, the apertures
    m = M(CK.Z_CCAST)
    c = mixc(T(PAINT[CK.Z_CPAINT_S] * 0.8, 0.12, 0.2), RUST_D, np.clip(0.35 + edge * 0.6 + ss(0.6, 0.8, n_mid) * 0.3, 0, 0.9))
    xc = np.sign(x) * (CK.XO - CK.CAST[0] / 2)
    ys_ = np.array([-CK.YO + CK.CAST[1] / 2, -CK.CAST[1] / 2, CK.CAST[1] / 2, CK.YO - CK.CAST[1] / 2], np.float32)
    yc = ys_[np.abs(y[:, None] - ys_[None]).argmin(1)]
    zc = np.where(z < 1.4, CK.ZB + CK.CAST[2] / 2, CK.ZT - CK.CAST[2] / 2)
    ax_ = np.abs(Nn).argmax(1)
    r = np.where(ax_ == 0, ((y - yc) / 0.050) ** 2 + ((z - zc) / 0.032) ** 2,
                 np.where(ax_ == 1, ((x - xc) / 0.055) ** 2 + ((z - zc) / 0.032) ** 2, ((x - xc) / 0.055) ** 2 + ((y - yc) / 0.035) ** 2))
    c = mixc(c, RUST, ss(1.6, 1.0, r) * 0.6)
    c = np.where((r < 1.0)[:, None], lin(18, 16, 14), c)
    col[m] = c[m]
    # ---- inside paint (doors' room side), underside, pads
    m = M(CK.Z_CINPAINT)
    c = T(IN_GREY, 0.10, 0.14)
    c = mixc(c, RUST_D, np.clip(edge * 0.6 + ss(0.74, 0.86, fbm(Pp, 20.0, 2, seed=518)) * 0.5 + ss(0.6, 0.3, z) * 0.5, 0, 0.8))
    col[m] = c[m]
    m = M(CK.Z_UNDER)
    c = T(lin(30, 28, 26), 0.12, 0.2)
    cross = gline(dist_periodic(x, 0.30), 0.05, aa)
    c = mixc(c, lin(52, 46, 40), cross * 0.6)
    c = mixc(c, RUST_D, ss(0.6, 0.8, n_mid) * 0.5)
    col[m] = c[m]
    m = M(K.Z_SLAB)
    col[m] = concrete(Pp, T, cav, up, z)[m]
    # ---- metals and the rest
    m = M(K.Z_STEELBLK)
    col[m] = steel_black(Pp, T, edge, 521)[m]
    m = M(K.Z_GALV)
    col[m] = galv(Pp, T, 522)[m]
    m = M(K.Z_RUSTPIPE)
    c = T(lin(104, 58, 34), 0.2, 0.25)
    c = mixc(c, lin(30, 26, 24), ss(3.0, 3.6, z) * 0.85 + ss(0.6, 0.85, n_mid) * 0.3)
    c = mixc(c, lin(70, 68, 72), ss(3.12, 3.03, x) * 0.5)
    col[m] = c[m]
    m = M(K.Z_CHEQUER)
    c, g_ = chequer(Pp, T, n_mid)
    c = mixc(c, lin(60, 52, 44), up * ss(0.5, 0.8, n_hi) * 0.4)
    col[m] = c[m]
    gr = np.where(m, g_, gr)
    col[M(K.Z_INSUL)] = T(lin(222, 220, 212), 0.06, 0.06)[M(K.Z_INSUL)]
    col[M(K.Z_WIRE)] = T(lin(22, 22, 22), 0.1, 0.1)[M(K.Z_WIRE)]
    m = M(K.Z_ENAMEL)
    c = T(lin(36, 70, 50), 0.10, 0.12)
    c = mixc(c, lin(20, 20, 20), ss(0.80, 0.92, fbm(Pp, 40.0, 2, seed=523)) * 0.9 + edge * 0.5)
    col[m] = c[m]
    col[M(K.Z_ENAMEL_IN)] = T(lin(232, 230, 222), 0.06, 0.08)[M(K.Z_ENAMEL_IN)]
    m = M(K.Z_TIMBER)
    col[m] = timber(Pp, Nn, T, cav, up, n_mid, 524)[m]
    col[M(CK.Z_SEAL)] = T(lin(22, 22, 22), 0.1, 0.1)[M(CK.Z_SEAL)]
    return col, gr


# ================================================================ inside: the generator shed's finishes
# gen_paint.paint_shed's inside zones (same colours, noise seeds and wear rules), its positions moved to where the
# shed's things stand in the container (cont_kit's group offsets); the shed's heights + DZ
DZ = CK.FC - K.FLOOR


def _seg(x, y, a, b):
    """distance from (x, y) to the segment a-b"""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = np.clip(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy), 0.0, 1.0)
    return np.hypot(x - ax - t * dx, y - ay - t * dy)


def inside_room(Pp):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    return ((x > CK.XR - 0.005) & (x < CK.XI + 0.005) & (np.abs(y) < CK.YI + 0.005) & (z > CK.FC - 0.005)
            & (z < CK.CI + 0.005))


def paint_cont_in(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 101)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    end_w = np.abs(Nn[:, 0]) > 0.5
    s_wall = np.where(end_w, y, x)                                  # along the wall
    streak = ss(0.55, 0.80, fbm(Pp * np.array([1, 1, 0.12], np.float32), 6.0, 3, seed=111))
    g, f = CK.G_GEN, CK.G_N
    # concrete floor: trowel marks, oil under the genset, the day tank's valve, drum 1 and the water separator, mud
    # trodden in from the doors (to the control panel, the board and the fuel corner), the control joints
    m = M(K.Z_FLOOR)
    c = T(lin(116, 113, 106), 0.18, 0.20)
    trowel = fbm(Pp * np.array([1, 1, 0.0], np.float32), 1.2, 2, seed=112)
    c = c * (0.92 + 0.12 * trowel)[:, None]
    oil = np.exp(-(((x - 0.75 - g.x) / 0.55) ** 2 + ((y - K.GY - g.y) / 0.42) ** 2)) * ss(0.35, 0.65, fbm(Pp, 3.5, 3, seed=113))
    oil += 0.8 * np.exp(-(((x + 0.48 - f.x) / 0.18) ** 2 + ((y - 1.36 - f.y) / 0.16) ** 2))           # under the tank valve
    oil += 0.6 * np.exp(-(((x - 1.27 - f.x) / 0.25) ** 2 + ((y - 0.98 - f.y) / 0.10) ** 2))           # in front of drum 1
    oil += 0.5 * np.exp(-(((x - 1.20 - g.x) / 0.12) ** 2 + ((y - K.GY + 0.48 - g.y) / 0.12) ** 2))     # under the separator
    c = mixc(c, OIL, np.clip(oil, 0, 0.85))
    door_y = ((-CK.YO + CK.RPW) + (-CK.RPW)) / 2                             # the doorway's middle
    path = (np.exp(-(((y - door_y - 0.07) / 0.55) ** 2)) * ss(0.2, -2.6, x)                              # doors -> panel
            + 0.6 * np.exp(-(((y - (-1.0 + CK.G_S.y)) / 0.35) ** 2)) * ss(-0.3, -1.6, x)                    # -> the board
            + 0.5 * np.exp(-((_seg(x, y, (-2.45, -0.70), (0.10, 1.75)) / 0.40) ** 2)))                    # -> the fuel corner
    c = mixc(c, lin(78, 72, 62), np.clip(path, 0, 1) * 0.45 * (0.6 + 0.4 * n_mid))
    c = mixc(c, lin(60, 56, 50), cav * 0.5)
    col[m] = c[m]
    gr = np.where(m, np.maximum(gline(np.abs(x), 0.008, aa), gline(np.abs(y), 0.008, aa)) * 0.7, gr)
    # birch-ply lining: sheets 1.22 x 2.44 (seams), nail lines every 0.6, grime low, soot by the exhaust, hand marks
    m = M(K.Z_LINING)
    c = T(lin(178, 150, 108), 0.14, 0.16)
    grain = fbm(Pp * np.array([3.0, 3.0, 0.4], np.float32), 9.0, 2, seed=116)
    c = c * (0.90 + 0.14 * grain)[:, None]
    sheet = np.maximum(gline(dist_periodic(s_wall, 1.22, 0.0), 0.005, aa),
                       gline(dist_periodic(z - CK.FC, 1.22), 0.005, aa) * (z < CK.FC + 2.30))
    nails = (1 - ss(0.004 - aa, 0.006 + aa, dist_periodic(s_wall, 0.60, 0.30))) * (1 - ss(0.004 - aa, 0.006 + aa, dist_periodic(z, 0.15)))
    c = mixc(c, lin(96, 80, 60), ss(0.9 + DZ, 0.25 + DZ, z) * 0.45 * (0.6 + 0.4 * n_mid))
    near_e = np.exp(-(((y - CK.EXH_Y) / 0.45) ** 2 + ((z - CK.EXH_Z) / 0.35) ** 2)) * (x > CK.XI - 0.28)
    c = mixc(c, lin(30, 28, 26), np.clip(near_e * 0.9, 0, 0.9))
    hand = (np.exp(-(((y - CK.SW_Y) / 0.10) ** 2 + ((z - 1.61) / 0.10) ** 2)) * (x < -2.7)               # the light switch
            + np.exp(-(((x + 1.40) / 0.30) ** 2 + ((z - 1.45 - DZ) / 0.25) ** 2)) * (y < -2.2))            # round the board
    c = mixc(c, lin(90, 74, 56), np.clip(hand, 0, 1) * 0.35)
    c = mixc(c, lin(120, 98, 70), streak * 0.30)
    col[m] = c[m]
    gr = np.where(m, np.maximum(sheet * 0.75, nails * 0.6), gr)
    # raw spruce: joists, blocking, the ledger, sill, reveals, battens on the shutter
    m = M(K.Z_TIMBER)
    col[m] = timber(Pp, Nn, T, cav, up, n_mid, 117)[m]
    # the corrugated roof's underside: 76 mm corrugation, sheets 0.76 wide, rust runs and drips
    m = M(K.Z_ROOFUNDER)
    shade = 0.82 + 0.18 * np.cos(2 * np.pi * x / 0.076)
    c = T(lin(118, 120, 116), 0.18, 0.20) * shade[:, None]
    run = ss(0.58, 0.82, fbm(Pp * np.array([1, 0.15, 0.15], np.float32), 7.0, 3, seed=118)) * ss(0.4, 1.9, np.abs(y))
    c = mixc(c, RUST_D, run * 0.45)
    c = mixc(c, lin(96, 92, 86), ss(0.65, 0.85, n_mid) * 0.35)
    c = mixc(c, lin(60, 58, 52), ss(0.62, 0.80, fbm(Pp, 16.0, 2, seed=119)) * 0.35)
    col[m] = c[m]
    gr = np.where(m, gline(dist_periodic(x, 0.76, 0.38), 0.010, aa) * 0.8, gr)
    # raw boards: the door leaves' planks inside, the window shutter
    m = M(K.Z_DOORIN)
    bi, seam = boards(np.where(np.abs(Nn[:, 1]) > 0.5, x, y), 0.12, aa, 0.004)
    c = lin(146, 118, 82) * (0.90 + 0.16 * hash1(bi, 6))[:, None] * (0.86 + 0.2 * (n_lo - 0.5) * 2)[:, None]
    c = mixc(c, lin(92, 74, 54), cav * 0.4 + ss(0.5 + DZ, 0.12 + DZ, z) * 0.4)
    col[m] = c[m]
    gr = np.where(m, seam * 0.7, gr)
    # white trims: the window frame and its glazing bars
    m = M(K.Z_TRIMW)
    c = T(lin(212, 208, 194), 0.10, 0.12)
    c = mixc(c, lin(132, 124, 108), np.clip(edge * 0.9 + ss(0.7, 0.88, fbm(Pp, 18.0, 2, seed=115)) * 0.6, 0, 0.9))
    c = mixc(c, lin(96, 88, 76), ss(0.35, 0.08, z) * 0.6 + cav * 0.35)
    c = mixc(c, lin(150, 140, 120), streak * 0.25)
    col[m] = c[m]
    # metals and the rest (the shed's)
    m = M(K.Z_STEELBLK)
    c = T(lin(36, 36, 36), 0.12, 0.2)
    c = mixc(c, RUST, np.clip(edge * 0.7 + ss(0.72, 0.86, fbm(Pp, 30.0, 2, seed=121)) * 0.5, 0, 0.8))
    col[m] = c[m]
    m = M(K.Z_GALV)
    spang = fbm(Pp, 90.0, 1, seed=122)
    c = T(lin(150, 154, 152), 0.10, 0.08) * (0.88 + 0.22 * spang)[:, None]
    c = mixc(c, lin(196, 198, 192), ss(0.78, 0.90, fbm(Pp, 25.0, 2, seed=123)) * 0.4)
    c = mixc(c, RUST, run_m(Pp) * 0.35)
    col[m] = c[m]
    m = M(K.Z_CHEQUER)
    u_, v_ = (x + y) / 0.035, (x - y) / 0.035
    dia = (1 - ss(0.10, 0.22, np.abs(u_ - np.round(u_)))) * (1 - ss(0.25, 0.45, np.abs(v_ - np.round(v_))))
    c = T(lin(124, 124, 120), 0.12, 0.16) * (0.85 + 0.25 * dia)[:, None]
    c = mixc(c, lin(70, 66, 60), ss(0.5, 0.85, n_mid) * 0.4)
    col[m] = c[m]
    gr = np.where(m, (1 - dia) * 0.25, gr)
    col[M(K.Z_INSUL)] = T(lin(222, 220, 212), 0.06, 0.06)[M(K.Z_INSUL)]
    col[M(K.Z_WIRE)] = T(lin(22, 22, 22), 0.1, 0.1)[M(K.Z_WIRE)]
    return col, gr


# ================================================================ the building atlas: outside + inside (as the shed's)
def paint_cont_all(Pp, Nn, Z, ao, aa):
    """one atlas for the whole container: the shed's inside painter for the inside zones (and for the shared metals
    inside the room), the container's outside painter for the rest"""
    co, go = paint_cont(Pp, Nn, Z, ao, aa)
    ci, gi = paint_cont_in(Pp, Nn, Z, ao, aa)
    sel = np.isin(Z, CK.INSIDE_ZONES) | (np.isin(Z, CK.SHARED_ZONES) & inside_room(Pp))
    return np.where(sel[:, None], ci, co), np.where(sel, gi, go)
