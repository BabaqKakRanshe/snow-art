"""Shared checks for the base and far batches (bpy as a module; a blend already open).
  solo(roots, mapm, name)    the prefab alone at the origin (its own frame), the others back at their map places
  bvh_of(name, extra=())     a BVH of the object's mesh (+ its children at rest, in the root's frame)
  backfaces(...)             rays from rings of eyes round the prefab: the first hit faces the eye (Unity culls backs)
  islands(me)                connected face islands: box, lowest point, zone
  ground_float(...)          islands of the contact zones reach the ground or touch another island
  coplanar(me)               overlapping coplanar face pairs left in one mesh (z-fighting)
  uv_range(me, mats)         PSX UVs of the atlas materials inside 0..1
  lens_points(...)           a light / halo point against the lens faces: distance, enclosed or not
  sweep(...)                 a hinged part swung through its range against the static mesh: intersecting face pairs
  images()                   the textures the materials use, their sizes"""
import math, sys
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

sys.path.insert(0, '/home/claude/uaz')
import bld_common as BC


def solo(roots, mapm, name):
    for n in roots:
        o = bpy.data.objects[n]
        o.matrix_world = Matrix.Identity(4) if n == name else mapm[n]
    bpy.context.view_layer.update()


def mesh_world(o, M=None):
    """vertices (n, 3) and polygons of an object in the frame M @ (its matrix relative to its root)"""
    me = o.data
    co = np.array([tuple(v.co) for v in me.vertices], np.float64)
    if M is not None:
        co = (np.asarray(M)[:3, :3] @ co.T).T + np.asarray(M)[:3, 3]
    return co, [list(p.vertices) for p in me.polygons]


def rel_matrix(o):
    """an object's matrix relative to its root (children at rest)"""
    M = Matrix.Identity(4)
    while o.parent is not None:
        M = o.matrix_local @ M
        o = o.parent
    return M


def bvh_of(name, children=True):
    """the root's mesh and its children's (at rest) in the root's frame; returns (tree, faces info list)"""
    o = bpy.data.objects[name]
    objs = [o] + ([c for c in o.children_recursive if c.type == 'MESH'] if children else [])
    V, Pl, info = [], [], []
    for ob in objs:
        M = np.array(rel_matrix(ob)) if ob is not o else None
        co, pls = mesh_world(ob, M)
        me = ob.data
        za = me.attributes['zone'].data if 'zone' in me.attributes else None
        base = len(V)
        V += [Vector(p) for p in co]
        for pi, p in enumerate(pls):
            Pl.append([base + i for i in p])
            mat = me.materials[me.polygons[pi].material_index].name if me.materials else '-'
            info.append((ob.name, int(round(za[pi].value)) if za is not None else -1, mat))
    return BVHTree.FromPolygons(V, Pl), info, V, Pl


def backfaces(name, tree, info, V, cutout, ground=lambda x, y: 0.0, ndir=120, seed=5, rmax=None):
    rng = np.random.default_rng(seed)
    dirs = rng.normal(size=(ndir, 3))
    dirs /= np.linalg.norm(dirs, axis=1)[:, None]
    co = np.array([tuple(v) for v in V])
    lo, hi = co.min(0), co.max(0)
    c = (lo + hi) / 2
    R = max(float(np.linalg.norm(hi - lo)) / 2, 0.6)
    if rmax:
        R = min(R, rmax)
    eyes = []
    for rr in (R * 1.2 + 1.0, R * 2.0 + 2.0):
        for zz in (lo[2] + 0.5, c[2], hi[2] + 1.0):
            for a in np.linspace(0, 2 * math.pi, 10, endpoint=False):
                eyes.append(Vector((c[0] + rr * math.cos(a), c[1] + rr * math.sin(a), zz)))
    eyes.append(Vector((c[0], c[1], hi[2] + R + 2.0)))
    bad, nray = {}, 0
    for eye in eyes:
        g = ground(eye.x, eye.y)
        if eye.z < g + 0.3:
            eye.z = g + 0.3
        for d in dirs:
            loc, nrm, idx, dist = tree.ray_cast(eye, Vector(d), 4 * R + 60.0)
            nray += 1
            if loc is None:
                continue
            ob, z, mat = info[idx]
            if mat in cutout:
                continue
            if nrm.dot(Vector(d)) > 0.05:
                # a two-sided sheet (two faces back to back, opposite normals, at most 2 mm apart: glass, the chair's
                # fabric) - fine when a face at the same place looks at the eye
                twin = any(Vector(n2).dot(Vector(d)) < -0.05 for (l2, n2, i2, d2) in tree.find_nearest_range(loc, 2e-3))
                if twin:
                    continue
                e = bad.setdefault(f'{ob}|{z}|{mat}', [0, [round(v, 3) for v in loc], [round(v, 2) for v in eye]])
                e[0] += 1
    return dict(rays=nray, bad=bad)


def islands(objs_frames):
    """face islands over several (object, matrix) pairs: lo, hi, lowest point, zone, faces"""
    out = []
    for o, M in objs_frames:
        me = o.data
        bm = bmesh.new()
        bm.from_mesh(me)
        if M is not None:
            bm.transform(Matrix(M))
        zl = bm.faces.layers.float.get('zone')
        seen = set()
        for f0 in bm.faces:
            if f0.index in seen:
                continue
            comp, st = [], [f0]
            seen.add(f0.index)
            while st:
                f = st.pop()
                comp.append(f)
                for e in f.edges:
                    for h in e.link_faces:
                        if h.index not in seen:
                            seen.add(h.index)
                            st.append(h)
            vs = {v for f in comp for v in f.verts}
            co = np.array([tuple(v.co) for v in vs])
            out.append(dict(obj=o.name, lo=co.min(0), hi=co.max(0), low=co[co[:, 2].argmin()],
                            zone=int(round(comp[0][zl])) if zl else -1, faces=len(comp)))
        bm.free()
    return out


def ground_float(isl, contact, ground_fns, tol=0.03, touch_tol=0.012):
    """islands of the contact zones: the lowest point within tol of the ground (every placement's ground in
    ground_fns), or touching another island; returns the floating ones (worst gap first)"""
    LO = np.array([i['lo'] for i in isl]) - touch_tol
    HI = np.array([i['hi'] for i in isl]) + touch_tol
    worst = []
    for k_, i in enumerate(isl):
        if i['zone'] not in contact:
            continue
        low = i['low']
        gap = max(float(low[2]) - g(float(low[0]), float(low[1])) for g in ground_fns)
        if gap <= tol:
            continue
        touch = np.all((LO <= i['hi'] + touch_tol) & (HI >= i['lo'] - touch_tol), axis=1)
        touch[k_] = False
        if touch.any():
            continue
        worst.append(dict(obj=i['obj'], zone=i['zone'], gap_m=round(gap, 3), at=[round(float(a), 2) for a in low],
                          faces=i['faces']))
    return sorted(worst, key=lambda w: -w['gap_m'])


def coplanar(me):
    Fs, buckets = [], {}
    for pg in me.polygons:
        if pg.area < 1e-6:
            continue
        nn = pg.normal.copy()
        pts = [me.vertices[i].co.copy() for i in pg.vertices]
        d_ = nn.dot(pg.center)
        Fs.append((pg.index, nn, d_, pts, pg.material_index))
        buckets.setdefault((round(nn.x * 100), round(nn.y * 100), round(nn.z * 100), round(d_ * 1000)), []).append(len(Fs) - 1)
    cnt, where = 0, []
    for key, ids in buckets.items():
        cand = list(ids)
        for dk in (-1, 1):
            cand += buckets.get((key[0], key[1], key[2], key[3] + dk), [])
        for i in ids:
            a_ = Fs[i]
            for j in cand:
                if j <= i:
                    continue
                b_ = Fs[j]
                if a_[1].dot(b_[1]) < 0.999 or abs(a_[2] - b_[2]) > 0.0005:
                    continue
                inter = BC._clip(BC._to2d(a_[3], a_[1]), BC._to2d(b_[3], a_[1]))
                if len(inter) >= 3:
                    ar = abs(sum(inter[q][0] * inter[(q + 1) % len(inter)][1] - inter[(q + 1) % len(inter)][0] * inter[q][1]
                                 for q in range(len(inter)))) / 2
                    if ar > 1e-5:
                        cnt += 1
                        if len(where) < 6:
                            where.append([round(float(v), 3) for v in me.polygons[a_[0]].center])
    return cnt, where


def uv_range(me, mats):
    """per material: the PSX UV box (only the atlas materials must stay inside 0..1)"""
    uv = me.uv_layers.get('PSX')
    if uv is None:
        return {'-': 'no PSX uv'}
    a = np.zeros(len(me.loops) * 2)
    uv.data.foreach_get('uv', a)
    a = a.reshape(-1, 2)
    res = {}
    for pg in me.polygons:
        m = me.materials[pg.material_index].name if me.materials else '-'
        if m not in mats:
            continue
        q = a[pg.loop_start:pg.loop_start + pg.loop_total]
        r = res.setdefault(m, [1e9, 1e9, -1e9, -1e9])
        r[0], r[1] = min(r[0], q[:, 0].min()), min(r[1], q[:, 1].min())
        r[2], r[3] = max(r[2], q[:, 0].max()), max(r[3], q[:, 1].max())
    return {m: dict(box=[round(float(v), 4) for v in r], ok=bool(r[0] >= -1e-4 and r[1] >= -1e-4 and r[2] <= 1 + 1e-4
                                                                and r[3] <= 1 + 1e-4)) for m, r in res.items()}


def lens_points(tree, info, V, Pl, pts, lens_mats):
    """each point: the nearest lens face (distance), and whether the prefab's mesh closes round it (rays in 14
    directions all hit)"""
    LV, LP = [], []
    for k, (ob, z, mat) in enumerate(info):
        if mat in lens_mats:
            base = len(LV)
            LV += [V[i] for i in Pl[k]]
            LP.append(list(range(base, base + len(Pl[k]))))
    if not LP:
        return [dict(p=list(map(float, p)), dist=None) for p in pts]
    lt = BVHTree.FromPolygons(LV, LP)
    dirs = [Vector(d).normalized() for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1),
                                             (1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1), (-1, 1, 1), (-1, 1, -1),
                                             (-1, -1, 1), (-1, -1, -1))]
    out = []
    for p in pts:
        pv = Vector(p)
        loc, nrm, idx, dist = lt.find_nearest(pv)
        hits = sum(1 for d in dirs if tree.ray_cast(pv, d, 2.0)[0] is not None)
        lens_hits = sum(1 for d in dirs if lt.ray_cast(pv, d, 2.0)[0] is not None)
        out.append(dict(p=[round(float(v), 3) for v in p], lens_dist=round(float(dist), 3) if dist is not None else None,
                        enclosed=hits == len(dirs), lens_rays=lens_hits))
    return out


def sweep(static_tree, static_info, part_obj, pivot_M, axis, angles, ignore_zones=()):
    """swing a child mesh about its pivot: pivot_M (its rest matrix in the root's frame), the axis in its local
    frame, angles (deg); returns {angle: [(part zone, static zone), ...]} for intersecting faces"""
    co, pls = mesh_world(part_obj)
    me = part_obj.data
    za = me.attributes['zone'].data if 'zone' in me.attributes else None
    res = {}
    for ang in angles:
        R = Matrix.Rotation(math.radians(ang), 4, Vector(axis))
        M = np.array(pivot_M @ R)
        c2 = (M[:3, :3] @ co.T).T + M[:3, 3]
        t = BVHTree.FromPolygons([Vector(p) for p in c2], pls)
        pairs = t.overlap(static_tree)
        hit = set()
        for a, b in pairs:
            za_ = int(round(za[a].value)) if za is not None else -1
            zb_ = static_info[b][1]
            if za_ in ignore_zones and zb_ in ignore_zones:
                continue
            hit.add((za_, zb_))
        if hit:
            res[ang] = sorted(hit)
    return res


def images():
    out = {}
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image is not None:
                out.setdefault(m.name, []).append([n.image.name, list(n.image.size)])
    return out
