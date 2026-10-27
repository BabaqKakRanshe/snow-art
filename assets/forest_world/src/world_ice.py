"""forest_world ice: the glaze and icicles that a blizzard leaves on the station's aerials (QUESTIONS_HORROR 41: a tower
iced over drops its radio coverage until someone knocks the ice off; BASE_THREATS B04: the roof aerial). Overlays in
their host prefab's own frame (Update 3 / forest_far / forest_main frames: z up, metres) - the game parents each root to
its host at the origin; one tiling material (M_World_Ice, box-mapped at 64 px/m).
  Ice_RelayMast   forest_far RelayMast: glaze on the legs and braces, icicles under the horizontals (root, scenery);
                  Ice_RelayMast_Panel_1..3 - rime on the three panel aerials, Ice_RelayMast_Drum - the crust on the
                  microwave drum (each removable)
  Ice_Dish_1..5   forest_far Dish_1..5 (each at its own elevation): icicles on the reflector's rim and the feed struts
                  (root); Ice_Dish_n_Feed - rime on the feed and the horn (removable), Ice_Dish_n_Bowl - the snow and ice in
                  the bottom of the reflector (removable)
  Ice_RoofMast    forest_main BaseMain: glaze and icicles on the 12 m roof mast and its platform rail (root);
                  Ice_RoofMast_Top - the rime on the top 1.6 m with the aerial and the obstruction light (removable),
                  Ice_RoofDish - the satellite dish's rime and bowl snow (removable)"""
import math
import numpy as np
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, KBS, CONTRACT
from van2_kit import ZERO
import world_kit as WK

TAU = 2 * math.pi
Z = Vector((0, 0, 1))
ICE_ROOTS = ['Ice_RelayMast'] + [f'Ice_Dish_{i}' for i in range(1, 6)] + ['Ice_RoofMast']
HOSTS = {'Ice_RelayMast': ('RelayMast', 'forest_far'), 'Ice_RoofMast': ('BaseMain', 'forest_main')}
HOSTS.update({f'Ice_Dish_{i}': (f'Dish_{i}', 'forest_far') for i in range(1, 6)})
ICE_DISPLAY = {'Ice_RelayMast': Vector((24.0, 6.0, 0.0)), 'Ice_RoofMast': Vector((-20.0, 0.0, -6.6))}
ICE_DISPLAY.update({f'Ice_Dish_{i}': Vector((36.0 + 18.0 * ((i - 1) % 3), 6.0 + 20.0 * ((i - 1) // 3), 0.0)) for i in range(1, 6)})
REMOVABLE = []                    # (part, host) - the parts the players knock off
BOXES = []                        # (part, (x0, x1, y0, y1, z0, z1)) hit boxes of the removable parts, host frame


def reg(name, root):
    WK.ROOT_OF[name] = root
    return kb(name, 'ice')


def h1(i, s=0):
    return WK.hsh(i, s)


def sheath(k, a, b, r, seg=5, seed=0):
    """glaze round a member a -> b: an open prism of radius r, thicker on its top / windward side"""
    a, b = Vector(a), Vector(b)
    t = (b - a)
    if t.length < 1e-4:
        return
    k.cyl(a, b, r * (0.9 + 0.25 * h1(seed, 1)), ZERO, seg, r2=r * (0.9 + 0.25 * h1(seed, 2)), caps=False)


def icicles(k, a, b, r_under, spacing, lmax, seed, rb=(0.010, 0.024), skip_vertical=0.75, density=1.0):
    """icicles hanging (world -z) from the underside of the member a -> b"""
    a, b = Vector(a), Vector(b)
    d = b - a
    L = d.length
    if L < 1e-3 or abs(d.normalized().z) > skip_vertical:
        return 0
    n = max(1, int(L / spacing))
    cnt = 0
    for i in range(n):
        if h1(seed * 131 + i, 7) > density:
            continue
        s = (i + 0.2 + 0.6 * h1(seed * 131 + i, 3)) / n
        base = a + d * s - Z * r_under
        ln = lmax * (0.22 + 0.78 * h1(seed * 131 + i, 4) ** 2)
        r0 = rb[0] + (rb[1] - rb[0]) * h1(seed * 131 + i, 5)
        k.cyl(base + Z * 0.01, base - Z * ln, r0, ZERO, 3, r2=0.0015, caps=False)
        cnt += 1
    return cnt


def rime_slab(k, c, R3, size, thick, seed):
    """a crust of rime over a box face: a slab (size x / y, thick along z of the frame R3) with a lumpy top"""
    nx, ny = 3, 4
    sx, sy = size
    top, bot = [], []
    for j in range(ny + 1):
        rt, rbm = [], []
        for i in range(nx + 1):
            u, v = i / nx - 0.5, j / ny - 0.5
            edge = min(0.5 - abs(u), 0.5 - abs(v)) * 2
            h = thick * (0.45 + 0.55 * min(1.0, edge * 3)) * (0.8 + 0.4 * h1(seed * 17 + j * 5 + i, 9))
            rt.append(Vector(c) + R3 @ Vector((u * sx, v * sy, h)))
            rbm.append(Vector(c) + R3 @ Vector((u * sx, v * sy, 0.0)))
        top.append(rt)
        bot.append(rbm)
    nz = R3 @ Vector((0, 0, 1))
    for j in range(ny):
        for i in range(nx):
            K.face(k, [top[j][i], top[j][i + 1], top[j + 1][i + 1], top[j + 1][i]], ZERO, nz)
    ring = [(j, 0) for j in range(ny + 1)] + [(ny, i) for i in range(1, nx + 1)] + [(j, nx) for j in range(ny - 1, -1, -1)] + \
           [(0, i) for i in range(nx - 1, 0, -1)]
    cen = Vector(c)
    for (j0, i0), (j1, i1) in zip(ring, ring[1:] + ring[:1]):
        K.face(k, [bot[j0][i0], bot[j1][i1], top[j1][i1], top[j0][i0]], ZERO, (top[j0][i0] + top[j1][i1]) / 2 - cen)


def bbox_of(k):
    co = np.array([v.co[:] for v in k.bm.verts])
    lo, hi = co.min(0), co.max(0)
    return (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])


def removable(name, host, root, note):
    x0, x1, y0, y1, z0, z1 = bbox_of(KBS[name])
    K.part(name, 'static', Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)), parent=root,
           states=['iced', 'clear'], note=note + ' - knocked off (forest_gear Item_IceAxe, a pole, a thrown snowball does '
                                                 'nothing): hide it, drop a few chunks; the hit box is in the contract')
    REMOVABLE.append((name, host))
    BOXES.append((name, bbox_of(KBS[name])))


# ================================================================ the relay mast (forest_far RelayMast)
def relay():
    import far_spec as S
    m = S.RELAY
    root = 'Ice_RelayMast'
    k = reg(root, root)
    corners = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
    C = lambda z, i: Vector((corners[i][0] * S.relay_c(z), corners[i][1] * S.relay_c(z), z))
    zs = [0.125] + list(np.arange(m['bay'], m['h'] + 1e-6, m['bay']))
    seed = 0
    for i in range(4):                                                   # the legs: glaze
        for za, zb in zip(zs[:-1], zs[1:]):
            r = 0.075 - 0.025 * za / m['h']
            sheath(k, C(za, i), C(zb, i), r + 0.022, 5, seed)
            seed += 1
    for f in range(4):
        i, j = f, (f + 1) % 4
        for n, z in enumerate(zs[1:], 1):
            za = zs[n - 1]
            a, b = C(z, i), C(z, j)                                      # the horizontal: glaze and icicles
            sheath(k, a, b, 0.026 + 0.018, 4, seed)
            icicles(k, a, b, 0.040, 0.26, 0.38, seed)
            seed += 1
            p0, p1 = (C(za, i), C(z, j)) if n % 2 else (C(za, j), C(z, i))
            sheath(k, p0, p1, 0.024 + 0.014, 4, seed)                  # the diagonal: glaze, a few icicles
            icicles(k, p0, p1, 0.034, 0.40, 0.22, seed, density=0.6)
            seed += 1
    K.part(root, 'static', (0, 0, 0), note='glaze on the legs and braces of the 42 m relay mast, icicles under the horizontals '
                                           '(scenery: goes when the weather turns; host forest_far RelayMast, at its origin)',
           states=['none', 'iced'])
    pa = m['panels']                                                     # the panel aerials: rime on the face, the sides, the top
    for i in range(3):
        name = f'Ice_RelayMast_Panel_{i + 1}'
        kp = reg(name, root)
        a = TAU * i / 3
        dirn = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-dirn.y, dirn.x, 0))
        pc = dirn * pa['r']
        zc = (pa['z'][0] + pa['z'][1]) / 2
        hgt = pa['z'][1] - pa['z'][0]
        front = pc + dirn * pa['d'] + Vector((0, 0, zc))
        Rf = Matrix((side, Z, dirn)).transposed()                        # slab x along the panel's width, y up, z out
        rime_slab(kp, front, Rf, (pa['w'] + 0.04, hgt + 0.04), 0.07, 40 + i)
        for sgn in (-1, 1):
            Rs = Matrix((dirn * -sgn, Z, side * sgn)).transposed()
            rime_slab(kp, pc + dirn * (pa['d'] / 2) + side * (sgn * pa['w'] / 2) + Vector((0, 0, zc)), Rs,
                      (pa['d'] + 0.06, hgt + 0.02), 0.04, 50 + i * 2 + (sgn > 0))
        Rt = Matrix((side, -dirn, Z)).transposed()
        rime_slab(kp, pc + dirn * (pa['d'] / 2) + Vector((0, 0, pa['z'][1])), Rt, (pa['w'] + 0.06, pa['d'] + 0.08), 0.08, 60 + i)
        lo = pc + dirn * (pa['d'] / 2) + Vector((0, 0, pa['z'][0]))
        icicles(kp, lo - side * (pa['w'] / 2 + 0.02), lo + side * (pa['w'] / 2 + 0.02), 0.0, 0.07, 0.30, 70 + i,
                rb=(0.012, 0.02))
        removable(name, 'RelayMast', root, f'rime on panel aerial {i + 1} (39-41 m): coverage drops while any panel is iced')
    dr = m['drum']                                                       # the microwave drum: a crust on its cover, icicles
    kd = reg('Ice_RelayMast_Drum', root)
    cx = dr['x'] + 0.45 + 0.11
    kd.lathe(Vector((cx - 0.02, 0.0, dr['z'])), Vector((1, 0, 0)), [(0.0, dr['r'] + 0.03), (0.04, dr['r'] + 0.02),
                                                                     (0.08, dr['r'] * 0.6), (0.10, 0.0)], ZERO, 14, cap0=False,
             cap1=False)
    for i in range(9):
        a = math.radians(-160 + 140 * i / 8)
        base = Vector((cx - 0.05 + 0.04 * h1(i, 81), math.cos(a) * dr['r'] * 0.95, dr['z'] + math.sin(a) * dr['r'] * 0.95))
        ln = 0.12 + 0.28 * h1(i, 82)
        kd.cyl(base, base - Z * ln, 0.018, ZERO, 3, r2=0.0015, caps=False)
    removable('Ice_RelayMast_Drum', 'RelayMast', root, 'the crust on the microwave drum (31.5 m): the link to the base drops')


# ================================================================ the dishes (forest_far Dish_1..5)
def dish(name):
    import far_spec as S
    g = S.dish_geom(name)
    root = 'Ice_' + name
    k = reg(root, root)
    ax = Vector(tuple(g['axis']))
    u = Vector((1, 0, 0))
    v = ax.cross(u).normalized()
    vtx = Vector(tuple(g['vertex']))
    f = g['focal']
    R_ = g['R']
    P = lambda r, ph, off=0.0: vtx + ax * (r * r / (4 * f) + off) + (u * math.cos(ph) + v * math.sin(ph)) * r
    seed = int(name[-1]) * 1000
    # icicles round the rim (the lower half hangs them longer) and on the four feed struts
    for i in range(48):
        ph = TAU * i / 48
        p = P(R_ * 1.002, ph, -0.06)
        low = max(0.0, -(math.sin(ph) * v.z))                           # how far down this part of the rim faces
        ln = (0.12 + 0.55 * low) * (0.3 + 0.7 * h1(seed + i, 2) ** 2)
        k.cyl(p + Z * 0.01, p - Z * ln, 0.02 + 0.015 * h1(seed + i, 3), ZERO, 3, r2=0.0015, caps=False)
    fc = Vector(tuple(g['focus']))
    for i in range(4):
        ph = TAU * (i + 0.5) / 4
        a_ = P(R_ * 0.62, ph, 0.02)
        b_ = fc + ax * 0.25 + (u * math.cos(ph) + v * math.sin(ph)) * 0.26
        sheath(k, a_, b_, 0.05 + 0.025, 5, seed + 100 + i)
        icicles(k, a_, b_, 0.07, 0.24, 0.30, seed + 110 + i, skip_vertical=0.9)
    K.part(root, 'static', (0, 0, 0), states=['none', 'iced'],
           note=f'icicles on the reflector\'s rim and glaze on the feed struts of {name} (scenery; host forest_far {name}, at its '
                'origin, built for its own elevation)')
    # the feed: a rime coat over its body and the horn's rim, icicles under it
    kf = reg(root + '_Feed', root)
    kf.lathe(fc + ax * 0.03, ax, [(0.0, 0.33), (0.62, 0.34), (0.68, 0.24), (0.70, 0.0)], ZERO, 12, cap0=False, cap1=False)
    kf.lathe(fc - ax * 0.47, ax, [(0.0, 0.38), (0.05, 0.37), (0.10, 0.34)], ZERO, 12, cap0=False, cap1=False)
    w = v.cross(ax)
    for i in range(10):
        s = 0.08 + 0.55 * i / 9
        side = (h1(seed + 200 + i, 1) - 0.5) * 0.4
        base = fc + ax * s + u * side * 0.6 - Z * 0.31
        ln = 0.10 + 0.32 * h1(seed + 200 + i, 2) ** 2
        kf.cyl(base + Z * 0.02, base - Z * ln, 0.022, ZERO, 3, r2=0.0015, caps=False)
    removable(root + '_Feed', name, root, f'rime on {name}\'s feed and horn (at the focus): the dish is deaf while iced')
    # the bowl: snow and ice lying in the lowest part of the reflector's face (a crescent, thick at the rim)
    kb_ = reg(root + '_Bowl', root)
    low_ph = math.atan2(-v.z, 0.0) if abs(v.z) > 1e-6 else -math.pi / 2     # the rim's lowest point: along -v (v up-ish)
    nr, nph = 5, 9
    grid_t, grid_b = [], []
    for jj in range(nr + 1):
        r = R_ * (0.50 + 0.50 * jj / nr)
        rt, rb = [], []
        for ii in range(nph + 1):
            ph = low_ph + math.radians(-60 + 120 * ii / nph)
            wedge = math.cos(math.radians(-60 + 120 * ii / nph) * 1.5) ** 2
            th = (0.04 + 0.20 * (jj / nr) ** 1.5) * max(wedge, 0.0) * (0.85 + 0.3 * h1(seed + jj * 17 + ii, 6)) + 0.005
            q = P(r, ph, 0.01)
            rt.append(q + Z * th)
            rb.append(q)
        grid_t.append(rt)
        grid_b.append(rb)
    for jj in range(nr):
        for ii in range(nph):
            K.face(kb_, [grid_t[jj][ii], grid_t[jj][ii + 1], grid_t[jj + 1][ii + 1], grid_t[jj + 1][ii]], ZERO, Z)
    for ii in range(nph):
        a, b = grid_t[nr][ii], grid_t[nr][ii + 1]
        K.face(kb_, [grid_b[nr][ii], grid_b[nr][ii + 1], b, a], ZERO, (a + b) / 2 - vtx)
    removable(root + '_Bowl', name, root, f'snow and ice in the bottom of {name}\'s reflector: weak signal while it lies there '
                                          '(shovel / knock out)')


# ================================================================ the roof mast and the satellite dish (forest_main BaseMain)
def roofmast():
    root = 'Ice_RoofMast'
    k = reg(root, root)
    zr = 6.60
    mc = Vector((5.45, 2.95, zr))
    top = 18.50
    legs = [mc + Vector((0.45 * math.cos(a), 0.45 * math.sin(a), 0.12)) for a in (0.5236, 2.618, 4.712)]
    shrink = 0.35

    def at(i, z):
        fr = 1.0 - (1.0 - shrink) * (z - zr) / (top - zr)
        p = legs[i]
        return Vector((mc.x + (p.x - mc.x) * fr, mc.y + (p.y - mc.y) * fr, z))
    nseg = 14
    ztop = top - 1.6
    kt = reg('Ice_RoofMast_Top', root)
    seed = 5000
    for s in range(nseg):
        z0 = zr + 0.12 + s * (top - zr - 0.12) / nseg
        z1 = z0 + (top - zr - 0.12) / nseg
        kk = kt if z0 >= ztop - 1e-6 else k
        for i in range(3):
            j = (i + 1) % 3
            sheath(kk, at(i, z0), at(i, z1), 0.03 + 0.02, 5, seed)
            sheath(kk, at(i, z0), at(j, z1), 0.008 + 0.014, 4, seed + 1)
            sheath(kk, at(i, z0), at(j, z0), 0.008 + 0.016, 4, seed + 2)
            icicles(kk, at(i, z0), at(j, z0), 0.022, 0.12, 0.22, seed + 3, rb=(0.008, 0.016))
            icicles(kk, at(i, z0), at(j, z1), 0.02, 0.18, 0.14, seed + 4, rb=(0.007, 0.012), density=0.5)
            seed += 5
    zp = zr + 6.0                                                         # the platform: icicles off the grating and the rail
    c = Vector((mc.x, mc.y, zp))
    for i in range(30):
        a = TAU * i / 30
        for rr, zz, ln in ((0.56, zp, 0.25), (0.555, zp + 1.0, 0.18)):
            p = c + Vector((rr * math.cos(a), rr * math.sin(a), zz - zp))
            l_ = ln * (0.25 + 0.75 * h1(seed + i, 1) ** 2)
            k.cyl(p, p - Z * l_, 0.014, ZERO, 3, r2=0.0015, caps=False)
    ring = [c + Vector((0.555 * math.cos(TAU * i / 20), 0.555 * math.sin(TAU * i / 20), 1.0)) for i in range(21)]
    k.tube(ring, 0.03, ZERO, 4, caps=False)
    # the top: the feeder's end and the obstruction light under a rime cap
    kt.lathe(Vector((mc.x, mc.y, top - 0.02)), Z, [(0.0, 0.16), (0.10, 0.15), (0.20, 0.09), (0.26, 0.0)], ZERO, 10, cap0=False,
             cap1=False)
    fx, fy = mc.x + 0.10, mc.y - 0.30
    sheath(kt, (fx, fy, ztop), (fx, fy, top - 0.5), 0.012 + 0.022, 5, seed + 9)
    K.part(root, 'static', (0, 0, 0), states=['none', 'iced'],
           note='glaze and icicles on the BaseMain roof mast below its top and on the platform\'s rail (scenery; host forest_main '
                'BaseMain, at its origin)')
    removable('Ice_RoofMast_Top', 'BaseMain', root, 'rime on the top 1.6 m of the roof mast - the aerial and the obstruction '
                                                     'light: the base radio is poor while it is iced (B04); from the platform')
    # the satellite dish on its post: rime on the rim, snow in its bottom, icicles
    kd = reg('Ice_RoofDish', root)
    axis = Vector((-0.55, -0.40, 0.73)).normalized()
    dc = Vector((3.05, -4.18, 7.80))
    e1 = axis.cross(Z).normalized()
    e2 = e1.cross(axis).normalized()                                     # 'up' in the dish's plane
    rim = [dc + axis * 0.15 + (e1 * math.cos(TAU * i / 16) + e2 * math.sin(TAU * i / 16)) * 0.49 for i in range(17)]
    kd.tube(rim, 0.03, ZERO, 4, caps=False)
    for i in range(16):
        ang = TAU * i / 16
        if math.sin(ang) > 0.2:
            continue
        p = dc + axis * 0.15 + (e1 * math.cos(ang) + e2 * math.sin(ang)) * 0.49
        kd.cyl(p, p - Z * (0.06 + 0.16 * h1(i, 91)), 0.012, ZERO, 3, r2=0.0015, caps=False)
    pts = []
    for i in range(7):                                                    # the bowl snow: a wedge in its lower part
        ang = math.radians(-150 + 120 * i / 6)
        pts.append(dc + axis * 0.13 + (e1 * math.cos(ang) + e2 * math.sin(ang)) * 0.46)
    cen = dc + axis * 0.05 + e2 * -0.25
    for a, b in zip(pts[:-1], pts[1:]):
        K.face(kd, [cen, a, b], ZERO, Z)
        K.face(kd, [a + Z * 0.0, b + Z * 0.0, b + Z * 0.05, a + Z * 0.05], ZERO, (a + b) / 2 - cen)
    for i in range(len(pts) - 1):
        a, b = pts[i] + Z * 0.05, pts[i + 1] + Z * 0.05
        K.face(kd, [cen + Z * 0.06, a, b], ZERO, Z)
    removable('Ice_RoofDish', 'BaseMain', root, 'rime and snow on the roof\'s satellite dish')


def build_ice():
    relay()
    for i in range(1, 6):
        dish(f'Dish_{i}')
    roofmast()
