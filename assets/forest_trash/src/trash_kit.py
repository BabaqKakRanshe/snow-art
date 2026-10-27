"""forest_trash geometry: six kinds of rubbish in the generator shed's style (PSX atlas, point filter), each in two states,
as the trash heaps of Voices of the Void:
  TrashPile_<Kind>  on the ground - a low mound of small bits with recognisable things lying on and in it, ~1.1-1.4 m
                    across; origin on the ground (z = 0) at its middle, front -y
  TrashClump_<Kind> in the hands - the same rubbish pressed into a bale ~0.4 m, a few things sticking out of it; origin at
                    the bale's middle (the grip), front -y
Kinds: Paper (newspapers, cardboard, cups, crumpled balls), Plastic (PET bottles, bags, a tray, a cup, a canister), Metal
(cans, crushed cans, a bent sheet, a pipe, wire), Wood (planks with nails, slats, branches), Glass (green, brown and clear
bottles, a jar, shards), Mixed (household: a bin bag, a can, a bottle, a box, paper).
Zones: per material (painters in trash_paint)."""
import math
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix, Euler
import van2_kit as VK
import noise as N

KINDS = ['Paper', 'Plastic', 'Metal', 'Wood', 'Glass', 'Mixed']
(Z_NEWS, Z_CARD, Z_CUP, Z_CUP_IN, Z_PET, Z_PET_CAP, Z_BAG_K, Z_BAG_B, Z_TRAY, Z_YOG, Z_CANISTER, Z_CAN, Z_CAN_TOP, Z_CRUSH,
 Z_SHEET, Z_PIPE, Z_WIRE, Z_PLANK, Z_NAIL, Z_BARK, Z_WOOD_END, Z_GL_G, Z_GL_B, Z_GL_C, Z_GL_LABEL, Z_SHARD, Z_JAR_LID,
 Z_BOX) = range(300, 328)
Z_MOUND = {k: 340 + i for i, k in enumerate(KINDS)}             # the low heap of small bits under each pile
Z_BALE = {k: 350 + i for i, k in enumerate(KINDS)}              # the pressed bale of each clump
CLUMP_DZ = 100                                                 # a clump's zones: the pile's + 100 (held: twice the texel density)
PARTS = {}                                                     # name -> KB
INFO = {}                                                      # name -> dict(kind, state, ...)


def M4(loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0):
    return (Matrix.Translation(Vector(loc)) @ Euler([math.radians(a) for a in rot], 'XYZ').to_matrix().to_4x4() @
            Matrix.Diagonal((scale, scale, scale, 1.0)) if not isinstance(scale, tuple) else
            Matrix.Translation(Vector(loc)) @ Euler([math.radians(a) for a in rot], 'XYZ').to_matrix().to_4x4() @
            Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0)))


class TB:
    """a KB with a current transform: every primitive is built in local coordinates and placed by M"""

    def __init__(self, name):
        self.k = VK.KB()
        self.M = Matrix.Identity(4)
        PARTS[name] = self.k

    def T(self, p):
        return self.M @ Vector(p)

    def R(self):
        return self.M.to_3x3()

    def poly(self, pts, zone, two=False):
        q = [self.T(p) for p in pts]
        self.k.poly(q, zone)
        if two:
            self.k.poly(list(reversed(q)), zone)

    def box(self, c, size, zone, R=None):
        R0 = self.R()
        sc = Vector([R0.col[i].length for i in range(3)])
        Rn = Matrix([R0.col[i] / max(sc[i], 1e-9) for i in range(3)]).transposed()
        s = Vector(size)
        self.k.box_m(self.T(c), (s.x * sc.x, s.y * sc.y, s.z * sc.z), zone, Rn @ (R or Matrix.Identity(3)))

    def lathe(self, c, axis, prof, zone, seg=10, cap0=True, cap1=True):
        bm = self.k.bm
        n0 = len(bm.verts)
        self.k.lathe(Vector(c), Vector(axis), prof, zone, seg=seg, cap0=cap0, cap1=cap1)
        self._xf(n0)

    def cyl(self, a, b, r, zone, seg=8, r2=None, caps=True):
        n0 = len(self.k.bm.verts)
        self.k.cyl(Vector(a), Vector(b), r, zone, seg=seg, r2=r2, caps=caps)
        self._xf(n0)

    def tube(self, pts, r, zone, seg=4, caps=True):
        n0 = len(self.k.bm.verts)
        self.k.tube([Vector(p) for p in pts], r, zone, seg=seg, caps=caps)
        self._xf(n0)

    def _xf(self, n0):
        bm = self.k.bm
        bm.verts.ensure_lookup_table()
        for v in bm.verts[n0:]:
            v.co = self.M @ v.co

    def lump(self, size, zone, seed, sub=2, amp=0.15, e=1.0, flat_bottom=None, freq=1.8):
        """a crumpled / lumpy body (paper ball, bag, mound, bale): icosphere, superellipsoid e, noise amp"""
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        P = np.array([v.co[:] for v in bm.verts], np.float64)
        F = [[v.index for v in f.verts] for f in bm.faces]
        bm.free()
        if e != 1.0:
            P = np.sign(P) * np.abs(P) ** e
        n = N.fbm(P.astype(np.float32), freq, 3, seed=seed % 12) - 0.5
        P = P * (1.0 + 2.0 * amp * n.astype(np.float64))[:, None]
        P = P * (np.asarray(size, np.float64) / 2.0)[None]
        if flat_bottom is not None:
            P[:, 2] = np.maximum(P[:, 2], flat_bottom)
        vs = [self.k.bm.verts.new(self.T(p)) for p in P]
        for f in F:
            self.k._f([vs[i] for i in f], zone)


def mound(t, a, b, h, zone, seed, rings=4, seg=14):
    """the low heap under a pile: a disc whose height falls off smoothly to the rim, an irregular outline, top side only"""
    rng = np.random.default_rng(seed)
    ang = np.linspace(0, 2 * math.pi, seg, endpoint=False) + rng.uniform(0, 0.3)
    rad = 1.0 + 0.30 * (N.fbm(np.c_[np.cos(ang), np.sin(ang), np.zeros(seg)].astype(np.float32) * 1.0, 1.3, 2, seed=seed % 12) - 0.5) * 2
    vs = [[t.k.bm.verts.new(t.T((0, 0, h)))]]
    for i in range(1, rings + 1):
        r = i / rings
        row = []
        for j in range(seg):
            x, y = a * r * rad[j] * math.cos(ang[j]), b * r * rad[j] * math.sin(ang[j])
            zz = h * (1 - r * r) ** 1.5 * (1 + 0.35 * (rng.random() - 0.5)) if i < rings else 0.0
            row.append(t.k.bm.verts.new(t.T((x, y, zz))))
        vs.append(row)
    for j in range(seg):
        t.k._f([vs[0][0], vs[1][j], vs[1][(j + 1) % seg]], zone)
    for i in range(1, rings):
        for j in range(seg):
            t.k._f([vs[i][j], vs[i + 1][j], vs[i + 1][(j + 1) % seg], vs[i][(j + 1) % seg]], zone)


# ================================================================ things (local frame: lying / standing on z = 0)
def paper_ball(t, r, seed):
    t.lump((2 * r, 2 * r * 0.9, 2 * r * 0.85), Z_NEWS, seed, sub=2, amp=0.28, freq=2.6)


def sheet(t, w, h, bends, zone=Z_NEWS):
    """a sheet of newspaper lying crumpled: strips across w with small bends (two-sided)"""
    n = len(bends) + 1
    xs = np.linspace(-w / 2, w / 2, n + 1)
    zs = [0.004] + [0.004 + b for b in bends] + [0.004]
    for i in range(n):
        t.poly([(xs[i], -h / 2, zs[i]), (xs[i + 1], -h / 2, zs[i + 1]), (xs[i + 1], h / 2, zs[i + 1]), (xs[i], h / 2, zs[i])],
               zone, two=True)


def cardboard(t, w, h, fold_deg):
    """a flattened carton: two panels with a fold, 4 mm thick"""
    t.box((-w / 4, 0, 0.004), (w / 2, h, 0.008), Z_CARD)
    a = math.radians(fold_deg)
    c = (w / 4 * math.cos(a), 0, 0.004 + w / 4 * math.sin(a))
    t.box(c, (w / 2, h, 0.008), Z_CARD, Matrix.Rotation(a, 3, 'Y').transposed())


def cup(t, r0, r1, h, zone=Z_CUP, lying=True):
    """a paper / plastic cup: cone, a rolled rim, a dark recessed bottom inside"""
    M0 = t.M
    if lying:
        t.M = M0 @ Matrix.Translation((0, 0, r1)) @ Matrix.Rotation(math.radians(90), 4, 'Y') @ Matrix.Translation((0, 0, -h / 2))
    t.lathe((0, 0, 0), (0, 0, 1), [(0.0, r0), (h, r1), (h + 0.003, r1 * 1.04), (h, r1 * 0.93)], zone, seg=8, cap1=False)
    t.lathe((0, 0, 0), (0, 0, 1), [(h, r1 * 0.93), (0.012, r0 * 0.92)], Z_CUP_IN, seg=8, cap0=False)
    t.M = M0


def bottle(t, r, h, zone, cap_zone, neck=0.32, lying=True, seg=8, label=None):
    """PET or glass bottle: body, shoulder, neck, cap; lying on its side by default"""
    M0 = t.M
    if lying:
        t.M = M0 @ Matrix.Translation((0, 0, r * 0.96)) @ Matrix.Rotation(math.radians(90), 4, 'Y') @ \
            Matrix.Translation((0, 0, -h / 2))
    hb = h * (1 - neck)
    prof = [(0.0, r * 0.88), (hb * 0.5, r), (hb * 0.5 + 0.001, r), (hb, r), (hb + h * neck * 0.45, r * 0.42), (h * 0.94, r * 0.32)]
    if label:
        t.lathe((0, 0, 0), (0, 0, 1), prof[:3], zone, seg=seg, cap1=False)
        t.lathe((0, 0, 0), (0, 0, 1), [prof[2], (hb * 0.82, r * 1.003)], label, seg=seg, cap0=False, cap1=False)
        t.lathe((0, 0, 0), (0, 0, 1), [(hb * 0.82, r), prof[3], prof[4], prof[5]], zone, seg=seg, cap0=False, cap1=False)
    else:
        t.lathe((0, 0, 0), (0, 0, 1), prof, zone, seg=seg, cap1=False)
    t.lathe((0, 0, 0), (0, 0, 1), [(h * 0.94, r * 0.36), (h, r * 0.36)], cap_zone, seg=6, cap0=False)
    t.M = M0


def can(t, r, h, crush=0.0, seed=0, lying=True):
    """a tin can (label band, lids); crush: flattened along its y by that share, the lids pushed in"""
    M0 = t.M
    if lying:
        s = 1.0 - crush
        t.M = M0 @ Matrix.Translation((0, 0, r * s)) @ Matrix.Diagonal((1.0, 1.0, s, 1.0)) @ \
            Matrix.Rotation(math.radians(90), 4, 'Y') @ Matrix.Translation((0, 0, -h / 2))
    z = Z_CRUSH if crush > 0.2 else Z_CAN
    t.lathe((0, 0, 0), (0, 0, 1), [(0.0, r * 0.94), (0.006, r), (h - 0.006, r), (h, r * 0.94)], z, seg=8, cap0=False, cap1=False)
    t.lathe((0, 0, 0), (0, 0, 1), [(0.0, r * 0.94), (0.0, r * 0.93)], Z_CAN_TOP, seg=8, cap0=True, cap1=False)
    t.lathe((0, 0, 0), (0, 0, 1), [(h, r * 0.93), (h, r * 0.94)], Z_CAN_TOP, seg=8, cap0=False, cap1=True)
    t.M = M0


def bag(t, size, zone, seed):
    """a tied rubbish bag: a lump, the neck and the ears of the knot on top"""
    sx, sy, sz = size
    t.lump((sx, sy, sz), zone, seed, sub=2, amp=0.16, flat_bottom=-sz * 0.38, freq=2.2)
    M0 = t.M
    t.M = M0 @ Matrix.Translation((0, 0, sz * 0.42))
    t.cyl((0, 0, 0), (0.02, 0.0, 0.09), 0.035, zone, seg=6, r2=0.02)
    t.lump((0.10, 0.05, 0.04), zone, seed + 1, sub=1, amp=0.1)
    t.M = M0


def tray(t, w, h, d=0.03, zone=Z_TRAY):
    t.box((0, 0, 0.003), (w, h, 0.006), zone)
    for sx, sy, ww, hh in ((0, h / 2, w, 0.006), (0, -h / 2, w, 0.006), (w / 2, 0, 0.006, h), (-w / 2, 0, 0.006, h)):
        t.box((sx, sy, d / 2), (ww, hh, d), zone)


def canister(t, zone=Z_CANISTER):
    t.box((0, 0, 0.13), (0.24, 0.13, 0.26), zone)
    t.cyl((0.07, 0, 0.26), (0.07, 0, 0.30), 0.022, Z_PET_CAP, seg=8)
    t.box((-0.04, 0, 0.275), (0.10, 0.03, 0.03), zone)


def plate(t, w, h, bends, thick=0.004, zone=Z_SHEET):
    """a bent sheet of steel: segments across w"""
    n = len(bends) + 1
    xs = np.linspace(-w / 2, w / 2, n + 1)
    zs = [thick / 2] + [thick / 2 + b for b in bends] + [thick / 2]
    for i in range(n):
        dx, dz = xs[i + 1] - xs[i], zs[i + 1] - zs[i]
        L = math.hypot(dx, dz)
        a = math.atan2(dz, dx)
        c = ((xs[i] + xs[i + 1]) / 2, 0, (zs[i] + zs[i + 1]) / 2)
        t.box(c, (L + 0.002, h, thick), zone, Matrix.Rotation(-a, 3, 'Y'))


def plank(t, L, w, th, zone=Z_PLANK, nails=2, broken=True, seed=0):
    """a weathered plank lying flat; a splintered end; nails sticking up"""
    rng = np.random.default_rng(seed)
    t.box((0, 0, th / 2), (L, w, th), zone)
    if broken:
        x = L / 2
        t.poly([(x, -w / 2, 0), (x + 0.06, -w * 0.1, th * 0.4), (x, w / 2, 0)], Z_WOOD_END, two=True)
        t.poly([(x, -w / 2, th), (x, w / 2, th), (x + 0.06, -w * 0.1, th * 0.4)], Z_WOOD_END, two=True)
    for i in range(nails):
        x = -L / 2 + 0.05 + i * (L - 0.1) / max(nails - 1, 1)
        y = rng.uniform(-w / 4, w / 4)
        t.cyl((x, y, th), (x + rng.uniform(-0.01, 0.01), y, th + 0.035), 0.0025, Z_NAIL, seg=4)


def branch(t, pts, r, zone=Z_BARK):
    t.tube(pts, r, zone, seg=5)


def shard(t, size, seed, zone=Z_SHARD):
    rng = np.random.default_rng(seed)
    a = [rng.uniform(0, 2 * math.pi) for _ in range(3)]
    a.sort()
    pts = [(math.cos(x) * size * rng.uniform(0.6, 1.0), math.sin(x) * size * rng.uniform(0.6, 1.0), 0.004) for x in a]
    t.poly(pts, zone, two=True)


def jar(t, r, h, lying=False):
    M0 = t.M
    if lying:
        t.M = M0 @ Matrix.Translation((0, 0, r)) @ Matrix.Rotation(math.radians(90), 4, 'Y') @ Matrix.Translation((0, 0, -h / 2))
    t.lathe((0, 0, 0), (0, 0, 1), [(0.0, r * 0.9), (0.01, r), (h * 0.8, r), (h * 0.9, r * 0.82)], Z_GL_C, seg=10, cap1=False)
    t.lathe((0, 0, 0), (0, 0, 1), [(h * 0.9, r * 0.84), (h, r * 0.84)], Z_JAR_LID, seg=10)
    t.M = M0


# ================================================================ piles and clumps
def mound_z(x, y, a, b, h):
    q = (x / a) ** 2 + (y / b) ** 2
    return h * max(1.0 - q, 0.0) ** 1.5


def place(t, base, x, y, yaw, tilt=(0.0, 0.0), sink=0.01, mound=None):
    """the transform of a thing lying on the mound at (x, y)"""
    z = mound_z(x, y, *mound) - sink if mound else -sink
    t.M = base @ Matrix.Translation((x, y, z)) @ Euler((math.radians(tilt[0]), math.radians(tilt[1]), math.radians(yaw)), 'XYZ').to_matrix().to_4x4()


ITEMS = {}   # kind -> list of (builder, args)  used by both states


def paper_items(t, place_fn):
    place_fn(0.0, 0.05, 15, (0, -4)); sheet(t, 0.56, 0.38, [0.03, -0.01, 0.02])
    place_fn(-0.34, -0.18, -40, (3, 2)); cardboard(t, 0.62, 0.40, 25)
    place_fn(0.33, -0.12, 70, (0, 5)); sheet(t, 0.40, 0.30, [0.02, 0.04])
    place_fn(-0.08, -0.28, 0, (0, 0)); paper_ball(t, 0.07, 3)
    place_fn(0.22, 0.24, 0, (0, 0)); paper_ball(t, 0.06, 4)
    place_fn(-0.30, 0.20, 0, (0, 0)); paper_ball(t, 0.08, 5)
    place_fn(0.42, 0.12, -25, (0, 0)); cup(t, 0.028, 0.040, 0.10)
    place_fn(-0.12, 0.30, 120, (0, 0)); cup(t, 0.028, 0.040, 0.10)
    place_fn(0.10, -0.06, 200, (4, 0)); cardboard(t, 0.34, 0.24, 40)


def plastic_items(t, place_fn):
    place_fn(-0.05, 0.02, 30, (0, 0)); bottle(t, 0.042, 0.30, Z_PET, Z_PET_CAP, label=Z_YOG)
    place_fn(0.30, -0.18, -60, (0, 0)); bottle(t, 0.042, 0.30, Z_PET, Z_PET_CAP)
    place_fn(-0.36, -0.10, 0, (0, 0)); bag(t, (0.34, 0.28, 0.24), Z_BAG_B, 7)
    place_fn(0.18, 0.26, 25, (3, -2)); tray(t, 0.26, 0.18)
    place_fn(0.40, 0.14, 80, (0, 0)); cup(t, 0.030, 0.036, 0.08, zone=Z_YOG)
    place_fn(-0.20, 0.30, -15, (0, 8)); canister(t)
    place_fn(0.05, -0.30, 100, (0, 0)); bottle(t, 0.036, 0.24, Z_PET, Z_PET_CAP)
    place_fn(-0.42, 0.24, 0, (0, 0)); bag(t, (0.18, 0.16, 0.12), Z_BAG_K, 8)


def metal_items(t, place_fn):
    place_fn(-0.10, 0.04, 20, (0, -3)); plate(t, 0.50, 0.32, [0.04, 0.06, 0.02])
    place_fn(0.30, -0.16, 0, (0, 0)); can(t, 0.042, 0.11)
    place_fn(0.14, 0.24, 70, (0, 0)); can(t, 0.042, 0.11, crush=0.55, seed=2)
    place_fn(-0.36, -0.18, -30, (0, 0)); can(t, 0.050, 0.14, crush=0.35, seed=3)
    place_fn(-0.30, 0.24, 40, (0, 0)); can(t, 0.033, 0.12)
    place_fn(0.36, 0.16, -50, (0, 0)); t.cyl((-0.25, 0, 0.03), (0.25, 0, 0.03), 0.03, Z_PIPE, seg=8)
    place_fn(0.00, -0.30, 0, (0, 0)); t.tube([(0.16 * math.cos(a), 0.12 * math.sin(a), 0.01 + 0.012 * math.sin(3 * a))
                                              for a in np.linspace(0, 2 * math.pi * 1.6, 10)], 0.004, Z_WIRE, seg=3, caps=False)
    place_fn(0.42, -0.02, 15, (0, 0)); can(t, 0.042, 0.11, crush=0.7, seed=4)


def wood_items(t, place_fn):
    place_fn(0.0, 0.0, 10, (0, 0)); plank(t, 0.80, 0.10, 0.022, seed=1)
    place_fn(-0.06, 0.12, 35, (0, -3)); plank(t, 0.62, 0.09, 0.020, seed=2)
    place_fn(0.10, -0.16, -20, (3, 0)); plank(t, 0.56, 0.08, 0.020, nails=1, seed=3)
    place_fn(-0.30, -0.06, 75, (0, 0)); plank(t, 0.40, 0.07, 0.018, nails=1, broken=False, seed=4)
    place_fn(0.30, 0.22, -55, (0, 0)); branch(t, [(-0.30, 0, 0.025), (-0.05, 0.02, 0.03), (0.12, -0.03, 0.028), (0.32, 0.01, 0.02)], 0.022)
    place_fn(-0.24, 0.30, 15, (0, 0)); branch(t, [(-0.22, 0, 0.018), (0.0, 0.03, 0.02), (0.20, 0.0, 0.016)], 0.016)
    place_fn(0.38, -0.20, 100, (0, 0)); t.box((0, 0, 0.03), (0.12, 0.10, 0.06), Z_WOOD_END)


def glass_items(t, place_fn):
    place_fn(-0.05, 0.05, 25, (0, 0)); bottle(t, 0.036, 0.29, Z_GL_G, Z_PET_CAP, neck=0.38, label=Z_GL_LABEL)
    place_fn(0.28, -0.16, -50, (0, 0)); bottle(t, 0.033, 0.25, Z_GL_B, Z_PET_CAP, neck=0.35)
    place_fn(-0.32, -0.14, 70, (0, 0)); bottle(t, 0.036, 0.29, Z_GL_G, Z_PET_CAP, neck=0.38)
    place_fn(0.20, 0.24, 0, (0, 0)); jar(t, 0.045, 0.12)
    place_fn(-0.28, 0.24, 140, (0, 0)); bottle(t, 0.030, 0.22, Z_GL_C, Z_PET_CAP, neck=0.30)
    for i, (x, y) in enumerate([(0.05, -0.30), (0.40, 0.08), (-0.45, 0.04), (0.10, 0.34), (-0.12, -0.22), (0.36, -0.30)]):
        place_fn(x, y, 37 * i, (0, 0)); shard(t, 0.05 + 0.01 * (i % 3), 20 + i)


def mixed_items(t, place_fn):
    place_fn(-0.20, 0.02, 0, (0, 0)); bag(t, (0.42, 0.36, 0.34), Z_BAG_K, 9)
    place_fn(0.28, -0.14, 40, (0, 0)); can(t, 0.042, 0.11, crush=0.4, seed=5)
    place_fn(0.20, 0.22, -30, (0, 0)); bottle(t, 0.036, 0.29, Z_GL_B, Z_PET_CAP, neck=0.38)
    place_fn(0.40, 0.06, 15, (3, 0)); t.box((0, 0, 0.04), (0.18, 0.12, 0.08), Z_BOX)
    place_fn(-0.02, -0.28, 60, (0, 0)); sheet(t, 0.36, 0.26, [0.02, -0.01])
    place_fn(0.10, 0.32, 0, (0, 0)); paper_ball(t, 0.06, 6)
    place_fn(-0.42, -0.22, 0, (0, 0)); bottle(t, 0.036, 0.24, Z_PET, Z_PET_CAP)


BUILDERS = dict(Paper=paper_items, Plastic=plastic_items, Metal=metal_items, Wood=wood_items, Glass=glass_items, Mixed=mixed_items)
MOUND = dict(Paper=(0.58, 0.46, 0.15), Plastic=(0.60, 0.48, 0.13), Metal=(0.56, 0.44, 0.10), Wood=(0.58, 0.44, 0.08),
             Glass=(0.54, 0.42, 0.08), Mixed=(0.62, 0.50, 0.15))
BITS = dict(Paper=(Z_NEWS, Z_CARD), Plastic=(Z_PET, Z_BAG_B, Z_TRAY), Metal=(Z_CRUSH, Z_SHEET), Wood=(Z_WOOD_END, Z_PLANK, Z_BARK),
            Glass=(Z_SHARD, Z_GL_G, Z_GL_B), Mixed=(Z_NEWS, Z_BAG_K, Z_CAN, Z_CARD))
BALE = dict(Paper=(0.44, 0.36, 0.34), Plastic=(0.42, 0.38, 0.36), Metal=(0.36, 0.32, 0.30), Wood=(0.48, 0.30, 0.30),
            Glass=(0.36, 0.34, 0.32), Mixed=(0.42, 0.38, 0.36))


def build_pile(kind, i):
    name = f'TrashPile_{kind}'
    t = TB(name)
    a, b, h = MOUND[kind]
    t.M = Matrix.Identity(4)
    mound(t, a, b, h, Z_MOUND[kind], 60 + i)
    base = Matrix.Identity(4)

    def pf(x, y, yaw, tilt):
        place(t, base, x, y, yaw, tilt, sink=0.012, mound=(a, b, h))
    BUILDERS[kind](t, pf)
    rng = np.random.default_rng(90 + i)                     # small bits of the same rubbish scattered over the heap
    zs = BITS[kind]
    for j in range(7):
        ang, rr = rng.uniform(0, 2 * math.pi), math.sqrt(rng.uniform(0.05, 0.9))
        x, y = a * rr * math.cos(ang), b * rr * math.sin(ang)
        place(t, base, x, y, rng.uniform(0, 360), (rng.uniform(-20, 20), rng.uniform(-20, 20)), sink=0.008, mound=(a, b, h))
        sz = rng.uniform(0.04, 0.08)
        t.lump((sz, sz * 0.8, sz * 0.45), zs[j % len(zs)], 100 + 10 * i + j, sub=1, amp=0.3, freq=3.0)
    INFO[name] = dict(kind=kind, state='ground', mound=(a, b, h))


def build_clump(kind, i):
    """the bale (a squashed rounded box) and a few of the pile's things sticking out of its faces"""
    name = f'TrashClump_{kind}'
    t = TB(name)
    sx, sy, sz = BALE[kind]
    t.M = Matrix.Identity(4)
    t.lump((sx, sy, sz), Z_BALE[kind], 70 + i, sub=2, amp=0.10, e=0.42, freq=2.6)
    rng = np.random.default_rng(80 + i)
    faces = [(Vector((1, 0, 0)), sx), (Vector((-1, 0, 0)), sx), (Vector((0, 1, 0)), sy), (Vector((0, -1, 0)), sy),
             (Vector((0, 0, 1)), sz)]
    order = [0, 2, 4, 1, 3]
    count = [0]

    def pf2(x, y, yaw, tilt):
        k = count[0]
        count[0] += 1
        if k >= 4:
            t.M = Matrix.Translation((0, 0, -50))             # beyond the first four: parked far below, deleted later
            return
        n, s = faces[order[k]]
        up = n
        side = Vector((0, 0, 1)) if abs(n.z) < 0.5 else Vector((1, 0, 0))
        xax = side.cross(up).normalized()
        yax = up.cross(xax).normalized()
        R = Matrix((xax, yax, up)).transposed().to_4x4()
        off = rng.uniform(-0.25, 0.25)
        c = n * (s * 0.45) + (yax * off * min(sx, sy, sz))
        t.M = Matrix.Translation(c) @ R @ Matrix.Rotation(math.radians(yaw + rng.uniform(-20, 20)), 4, 'Z') @ \
            Matrix.Rotation(math.radians(rng.uniform(-25, 25)), 4, 'X') @ Matrix.Diagonal((0.55, 0.55, 0.55, 1.0))
    BUILDERS[kind](t, pf2)
    bm = t.k.bm
    far = [v for v in bm.verts if v.co.z < -10]
    bmesh.ops.delete(bm, geom=far, context='VERTS')
    zl = t.k.zl
    for f in bm.faces:                                      # the clump's own zones (+100): painted alike, finer in the atlas
        f[zl] = f[zl] + CLUMP_DZ
    INFO[name] = dict(kind=kind, state='held', bale=(sx, sy, sz))


def build_trash():
    PARTS.clear()
    INFO.clear()
    for i, k in enumerate(KINDS):
        build_pile(k, i)
        build_clump(k, i)
    return PARTS, INFO
