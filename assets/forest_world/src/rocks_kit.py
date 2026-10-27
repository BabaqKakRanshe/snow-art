"""forest_rocks geometry: the granite of the Forest map in the generator shed's style (PSX atlas, point filter).
6 stones (0.3-1.2 m above the ground), 3 boulders, 3 cliffs - granite tors of rounded 'woolsack' blocks, as in the Harz.
Each model is one mesh in its own frame: z up, front -y, origin on the ground line (z = 0); the foot goes into the ground
(BURY m) so that it sits on uneven terrain. A rock: an ellipsoid or a pillow (superellipsoid) with low-frequency noise,
flattened by random planar cuts (fracture facets); coplanar faces are dissolved, the rest triangulated. A cliff: blocks
of that kind stacked in tiers; faces buried inside another block are dropped.
Zones: Z0 + 2 i - the rock of model i, Z0 + 2 i + 1 - its faces wholly under the ground (shrunk in the atlas)."""
import math
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix
from scipy.spatial import ConvexHull
import noise as N

Z0 = 200
MODELS = []          # dict(name, kind, idx, parts, bury, note)


def ico(sub):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    P = np.array([v.co[:] for v in bm.verts], np.float64)
    F = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    return P, F


def pillow(P, e):
    """unit-sphere points -> superellipsoid: e = 1 sphere, e < 1 a rounded box (woolsack)"""
    return np.sign(P) * np.abs(P) ** e


def disp(P, amp, freq, seed):
    if amp <= 0:
        return P
    n = N.fbm(P.astype(np.float32), freq, 3, seed=seed % 12) - 0.5
    return P * (1.0 + 2.0 * amp * n.astype(np.float64))[:, None]


def cuts(P, rng, k, depth=(0.80, 0.93), nz=(-0.15, 0.95), keep=None):
    """k planar cuts: the points beyond a random plane go onto it (a fracture facet); depth - where the plane sits along its
    normal, as a share of the extent (1 = the outermost point); keep: unit normals not to cut along (the joints)"""
    for _ in range(k):
        th = rng.uniform(0, 2 * math.pi)
        z = rng.uniform(*nz)
        r = math.sqrt(max(0.0, 1 - z * z))
        n = np.array([r * math.cos(th), r * math.sin(th), z])
        pr = P @ n
        d = pr.min() + (pr.max() - pr.min()) * rng.uniform(*depth)
        over = pr - d
        m = over > 0
        P[m] -= over[m, None] * n[None]
    return P


def rot(rx=0.0, ry=0.0, rz=0.0):
    return np.array(Matrix.Rotation(math.radians(rz), 3, 'Z') @ Matrix.Rotation(math.radians(ry), 3, 'Y') @
                    Matrix.Rotation(math.radians(rx), 3, 'X'))


def chunk(seed, size, sub=2, e=1.0, amp=0.06, freq=1.6, ncut=5, depth=(0.80, 0.93), nz=(-0.15, 0.95), R=None, c=(0, 0, 0),
          hull=False):
    """one rock body: (points (n, 3), faces) in the model frame; hull: the convex hull of the cut points (deep cuts on a
    noisy body can fold the surface)"""
    rng = np.random.default_rng(seed)
    P, F = ico(sub)
    P = pillow(P, e) if e != 1.0 else P
    P = disp(P, amp, freq, seed)
    P = P * (np.asarray(size, np.float64) / 2.0)[None]
    P = cuts(P, rng, ncut, depth, nz)
    if hull:
        h = ConvexHull(P)
        keep = np.unique(h.simplices)
        remap = -np.ones(len(P), np.int64)
        remap[keep] = np.arange(len(keep))
        P, F = P[keep], [list(remap[t]) for t in h.simplices]
    if R is not None:
        P = P @ np.asarray(R).T
    return P + np.asarray(c, np.float64)[None], F


def model(name, kind, bodies, bury, note, ground=None, cull=True):
    """bodies: [(P, F)]; ground: z of the ground line in the bodies' frame (default: 1.5 bury above the lowest point); the
    foot is flattened at -bury; faces inside another body are dropped (cull)"""
    zmin = min(P[:, 2].min() for P, _ in bodies)
    g = zmin + 1.5 * bury if ground is None else ground          # the lowest half-bury becomes a flat cap at -bury
    out = []
    for P, F in bodies:
        Q = P.copy()
        Q[:, 2] -= g
        Q[:, 2] = np.maximum(Q[:, 2], -bury)
        out.append((Q, F))
    MODELS.append(dict(name=name, kind=kind, idx=len(MODELS), parts=out, bury=bury, note=note, cull=cull and len(out) > 1))


# ================================================================ stones (0.3-1.2 m above the ground)
def build_stones():
    model('ForestStone_1', 'stone', [chunk(11, (0.50, 0.42, 0.40), ncut=3, depth=(0.86, 0.95), amp=0.07)], 0.08,
          'обкатанный булыжник')
    model('ForestStone_2', 'stone', [chunk(12, (0.80, 0.62, 0.62), ncut=9, depth=(0.55, 0.82), amp=0.04, hull=True)], 0.10,
          'угловатый обломок с плоскими сколами')
    model('ForestStone_3', 'stone', [chunk(13, (1.20, 0.82, 0.36), e=0.75, ncut=6, depth=(0.72, 0.90), nz=(-0.1, 0.35),
                                           amp=0.05, R=rot(rx=5, ry=-4))], 0.10, 'плоская плита')
    model('ForestStone_4', 'stone', [chunk(14, (0.62, 0.52, 1.00), ncut=6, depth=(0.72, 0.90), nz=(-0.1, 0.6), amp=0.05,
                                           R=rot(ry=6), hull=True)], 0.14, 'стоячий клин')
    model('ForestStone_5', 'stone', [chunk(15, (0.40, 0.34, 0.30), ncut=4, depth=(0.78, 0.92), c=(0.0, 0.0, 0.0)),
                                     chunk(16, (0.32, 0.28, 0.24), ncut=4, depth=(0.75, 0.92), c=(0.30, 0.14, -0.03),
                                           R=rot(rz=35)),
                                     chunk(17, (0.30, 0.26, 0.22), ncut=5, depth=(0.70, 0.90), c=(-0.16, 0.27, 0.0),
                                           R=rot(rz=-20))], 0.07, 'три камня кучкой')
    model('ForestStone_6', 'stone', [chunk(18, (1.45, 1.15, 1.10), e=0.85, ncut=5, depth=(0.80, 0.93), amp=0.06)], 0.40,
          'большой камень, ушедший в землю, во мху')


# ================================================================ boulders (1.5-3.5 m)
def build_boulders():
    model('ForestBoulder_1', 'boulder', [chunk(21, (2.5, 2.0, 1.95), sub=3, e=0.72, ncut=4, depth=(0.85, 0.95), amp=0.07,
                                               freq=1.3)], 0.30, 'круглый гранитный «мешок»')
    # the split boulder: one body cut in two along a crack, the halves leaning apart
    P, F = chunk(22, (3.1, 2.5, 2.3), sub=3, e=0.80, ncut=5, depth=(0.84, 0.94), amp=0.06, freq=1.2)
    n = np.array([math.cos(math.radians(78)), math.sin(math.radians(78)), 0.0])
    halves = []
    for s in (1, -1):
        Q = P.copy()
        pr = (Q @ n) * s
        over = pr - 0.07
        m = over < 0
        Q[m] -= (over[m, None] * n[None]) * s
        ang = 4.0 * s
        Rm = np.asarray(Matrix.Rotation(math.radians(ang), 3, Vector((-n[1], n[0], 0.0))))
        Q = (Q - np.array([0, 0, -1.15])) @ Rm.T + np.array([0, 0, -1.15]) + n * 0.06 * s
        halves.append((Q, F))
    model('ForestBoulder_2', 'boulder', halves, 0.32, 'расколотый валун: две половины с трещиной', cull=False)
    model('ForestBoulder_3', 'boulder', [chunk(23, (3.7, 2.7, 1.55), sub=3, e=0.55, ncut=6, depth=(0.80, 0.93), amp=0.05,
                                               freq=1.2, nz=(-0.1, 0.5))], 0.28, 'плоская глыба')


# ================================================================ cliffs: granite tors of woolsack blocks
def blk(seed, c, size, rz=0.0, e=0.42, amp=0.08, ncut=5, tilt=(0.0, 0.0)):
    sub = 3 if max(size) > 2.4 else 2
    return chunk(seed, size, sub=sub, e=e, amp=amp, freq=1.8, ncut=ncut, depth=(0.78, 0.93), nz=(-0.2, 0.8),
                 R=rot(rx=tilt[0], ry=tilt[1], rz=rz), c=c)


def build_cliffs():
    b = []                                         # Cliff_1: a wall of three tiers, ~10 m along x, the blocks fused, joints between
    for i, (x, w, h, d, rz) in enumerate([(-3.5, 3.8, 2.5, 3.8, 5), (-0.3, 3.0, 2.2, 3.4, -3), (3.0, 4.0, 2.6, 3.9, 7)]):
        b.append(blk(31 + i, (x, 0.0, 1.0), (w, d, h), rz=rz, tilt=(0, 2 * (1 - i))))
    for i, (x, w, h, d, rz, y) in enumerate([(-2.3, 3.6, 2.0, 3.2, -6, 0.3), (1.2, 3.2, 1.8, 3.0, 4, 0.1), (3.9, 1.8, 1.5, 2.4, 15, 0.5)]):
        b.append(blk(41 + i, (x, y, 2.75), (w, d, h), rz=rz, tilt=(4, -2 + 2 * i)))
    for i, (x, w, h, d, rz) in enumerate([(-1.6, 3.0, 1.5, 2.6, 9), (1.3, 2.2, 1.2, 2.2, -12)]):
        b.append(blk(51 + i, (x, 0.5, 4.05), (w, d, h), rz=rz, tilt=(0, -4 + 7 * i)))
    model('ForestCliff_1', 'cliff', b, 0.45, 'скальная стенка: три яруса сросшихся гранитных блоков')
    b = []                                         # Cliff_2: a tor - a pillar of five tiers, the top block askew
    tiers = [((0.0, 0.0, 0.9), (5.0, 4.4, 2.4), 0), ((0.55, -0.35, 2.55), (4.0, 3.6, 1.8), 14),
             ((0.05, 0.35, 3.95), (3.6, 2.9, 1.6), -11), ((0.75, -0.05, 5.10), (2.9, 2.6, 1.4), 27),
             ((0.55, 0.45, 6.05), (2.1, 1.7, 1.1), 41)]
    for i, (c, s, rz) in enumerate(tiers):
        b.append(blk(61 + i, c, s, rz=rz, e=0.45 + 0.03 * i, tilt=((-1) ** i * 3.0, -2.0 - 1.2 * i)))
    b.append(blk(66, (-1.7, -0.6, 2.4), (1.9, 2.4, 1.9), rz=-20, e=0.5))
    b.append(blk(67, (2.4, 1.2, 0.6), (2.2, 1.9, 1.5), rz=25, e=0.55))
    b.append(blk(68, (-2.5, -1.2, 0.5), (1.8, 2.0, 1.2), rz=-15, e=0.6))
    b.append(blk(69, (-0.6, 2.1, 1.3), (2.6, 1.6, 2.0), rz=5, e=0.5))
    model('ForestCliff_2', 'cliff', b, 0.45, 'останец (Klippe): столб из пяти блоков с боковыми глыбами')
    b = []                                         # Cliff_3: a ledge - a broad base, a slab overhanging the front, a side block
    b.append(blk(71, (0.0, 0.6, 1.1), (6.2, 4.8, 2.6), rz=0, e=0.5))
    b.append(blk(72, (-1.9, 1.3, 3.0), (3.4, 3.4, 1.7), rz=8, e=0.5))
    b.append(blk(73, (0.6, -0.6, 3.25), (5.2, 3.6, 1.05), rz=-6, e=0.45, tilt=(-4, 2)))
    b.append(blk(74, (2.6, 1.6, 2.6), (2.4, 2.6, 1.6), rz=-20, e=0.55))
    b.append(blk(75, (3.3, -1.6, 0.6), (1.9, 1.6, 1.3), rz=30, e=0.65))
    model('ForestCliff_3', 'cliff', b, 0.45, 'уступ с нависающей плитой')


def build_rocks():
    MODELS.clear()
    build_stones()
    build_boulders()
    build_cliffs()
    return MODELS


def _inside(hull, X, margin=0.02):
    eq = hull.equations
    return np.all(X @ eq[:, :3].T + eq[:, 3][None] <= -margin, axis=1)


FUSE = {'cliff': dict(voxel=0.10, tris=1500)}
HIDE = 0.05                # faces wholly below -HIDE (under the ground) go to the shrunk underside zone


def _evaluated(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)


def fuse(ob, bury, zr, zh, voxel, tris):
    """the blocks fused into one mass (voxel remesh: joints stay as creases), decimated to ~tris, the foot flattened"""
    rm = ob.modifiers.new('fuse', 'REMESH')
    rm.mode, rm.voxel_size, rm.adaptivity = 'VOXEL', voxel, 0.0
    _evaluated(ob)
    n = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    dm = ob.modifiers.new('dec', 'DECIMATE')
    dm.decimate_type, dm.ratio, dm.use_collapse_triangulate = 'COLLAPSE', min(1.0, tris / max(n, 1)), True
    _evaluated(ob)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for v in bm.verts:
        if v.co.z < -bury:
            v.co.z = -bury
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
    zl = bm.faces.layers.float.get('zone') or bm.faces.layers.float.new('zone')
    for f in bm.faces:
        f[zl] = zh if all(v.co.z <= -HIDE for v in f.verts) else zr
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()


def to_object(m, coll, dissolve_deg=3.0):
    """the model as one mesh object (zone per face), coplanar faces dissolved, triangulated; cliffs fused"""
    zr, zh = Z0 + 2 * m['idx'], Z0 + 2 * m['idx'] + 1
    fz = FUSE.get(m['kind'])
    if fz:
        m = dict(m, cull=False)
    hulls = [ConvexHull(P) for P, _ in m['parts']] if m['cull'] else []
    bm = bmesh.new()
    zl = bm.faces.layers.float.new('zone')
    for bi, (P, F) in enumerate(m['parts']):
        vs = [bm.verts.new(Vector(p)) for p in P]
        for f in F:
            X = P[f]
            if m['cull'] and any(_inside(h, X).all() for hj, h in enumerate(hulls) if hj != bi):
                continue
            try:
                face = bm.faces.new([vs[i] for i in f])
            except ValueError:
                continue
            hidden = bool(np.all(X[:, 2] <= -HIDE))
            face.material_index = 1 if hidden else 0
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(dissolve_deg), use_dissolve_boundaries=False, verts=bm.verts,
                             edges=bm.edges, delimit={'MATERIAL'})
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges)
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    for f in bm.faces:
        f[zl] = zh if f.material_index == 1 else zr
        f.material_index = 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(m['name'])
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new(m['name'], me)
    coll.objects.link(ob)
    if fz:
        fuse(ob, m['bury'], zr, zh, fz['voxel'], fz['tris'])
    return ob
