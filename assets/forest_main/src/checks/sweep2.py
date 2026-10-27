"""Moving parts through their ranges: how deep does a part sink into anything else (or anything into it)?
Points on the surfaces (every vertex + area-sampled points, ~1 cm apart on small parts, ~2.5 cm on large ones) are
tested against the closed shells of the other objects: a point counts as inside when the nearest surface faces away
from it; its depth is the distance to that surface. Per part: the depth at rest and the worst depth over the range;
a part is reported when the worst depth exceeds the rest depth by more than TOL (it sinks into something while it moves).
python3 -I sweep2.py [--test] [-- Part ...] -> sweep2.json next to this script"""
import bpy, json, math, os, sys
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ARGS = sys.argv[:sys.argv.index('--')] if '--' in sys.argv else sys.argv
SUF = '_test' if '--test' in ARGS else ''
TOL = 0.003
bpy.ops.wm.open_mainfile(filepath=f'/home/claude/uaz/out/main{SUF}.blend')
for _lib in list(bpy.data.libraries):                 # 1.2: the snow_kit instances (linked) are not the building's
    bpy.data.libraries.remove(_lib)                  # geometry: checked as in 1.1, the station has main_leit_check.py
C = json.load(open(f'/home/claude/uaz/out/main_contract{SUF}.json'))
P = C['parts']
objs = {o.name: o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith(('COL_', 'LIGHT_'))}
rng_ = np.random.default_rng(7)


def world(o):
    me = o.data
    me.calc_loop_triangles()
    M = o.matrix_world
    V = np.array([tuple(M @ v.co) for v in me.vertices], float).reshape(-1, 3)
    T = np.array([tuple(t.vertices) for t in me.loop_triangles], int).reshape(-1, 3)
    za = me.attributes.get('zone')
    Z = np.array([round(za.data[t.polygon_index].value) if za else -1 for t in me.loop_triangles], int)
    mats = [s.material.name if s.material else '-' for s in o.material_slots]
    MI = [mats[t.material_index] if mats else '-' for t in me.loop_triangles]
    return V, T, Z, MI


def pseudo(V, T):
    """per triangle: its normal; per (rounded) edge and vertex position: the summed normals of the triangles around it
    (angle-weighted at the vertices) -- the pseudonormals that make the inside test hold at edges and corners"""
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    n = np.cross(b - a, c - a)
    ln = np.linalg.norm(n, axis=1)
    n = n / np.maximum(ln, 1e-12)[:, None]
    E, Vx, EC = {}, {}, {}
    key = lambda p: (round(p[0], 5), round(p[1], 5), round(p[2], 5))
    for i, t in enumerate(T):
        if ln[i] < 1e-12:
            continue
        P = [V[t[0]], V[t[1]], V[t[2]]]
        for j in range(3):
            e = tuple(sorted((key(P[j]), key(P[(j + 1) % 3]))))
            E[e] = E.get(e, 0) + n[i]
            EC[e] = EC.get(e, 0) + 1
            u, w = P[(j + 1) % 3] - P[j], P[(j + 2) % 3] - P[j]
            ang = math.acos(max(-1.0, min(1.0, float(np.dot(u, w) / (np.linalg.norm(u) * np.linalg.norm(w) + 1e-15)))))
            Vx[key(P[j])] = Vx.get(key(P[j]), 0) + n[i] * ang
    for e, c in EC.items():                                          # an open edge (the surface goes on in another
        if c == 1:                                                   # object): no side there
            E[e] = None
            Vx[e[0]] = None
            Vx[e[1]] = None
    return n, E, Vx, key
WM = {n: world(o) for n, o in objs.items()}
BV = {n: BVHTree.FromPolygons([tuple(v) for v in V], [tuple(t) for t in T]) for n, (V, T, Z, MI) in WM.items() if len(T)}
PS = {}


def ps(n):
    if n not in PS:
        PS[n] = pseudo(WM[n][0], WM[n][1])
    return PS[n]
BB = {n: (V.min(0), V.max(0)) for n, (V, T, Z, MI) in WM.items() if len(V)}


def samples(names, spacing):
    pts = []
    for n in names:
        V, T, Z, MI = WM[n]
        if not len(T):
            continue
        pts.append(V)
        a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        k = np.minimum(np.ceil(area / spacing ** 2).astype(int), 400)
        for i in np.nonzero(k > 0)[0]:
            r = rng_.random((k[i], 2))
            f = r.sum(1) > 1
            r[f] = 1 - r[f]
            pts.append(a[i] + r[:, :1] * (b[i] - a[i]) + r[:, 1:] * (c[i] - a[i]))
    return np.concatenate(pts) if pts else np.zeros((0, 3))


def xform(kind, piv, ax, val):
    piv, ax = Vector(piv), Vector(ax).normalized()
    if kind in ('hinge', 'twist', 'spin'):
        return Matrix.Translation(piv) @ Matrix.Rotation(math.radians(val), 4, ax) @ Matrix.Translation(-piv)
    return Matrix.Translation(ax * val)


def inside_depth(bvh, pts, V, T, PSD, near=0.06):
    """the depth of each point inside the closed shells of a mesh (0 = outside or farther than near from any surface):
    the sign from the pseudonormal at the nearest point (face, edge or corner)"""
    n, E, Vx, key = PSD
    d = np.zeros(len(pts))
    loc = [None] * len(pts)
    for i, p in enumerate(pts):
        P = Vector(p)
        q = bvh.find_nearest(P, near)
        if q[0] is None or q[3] < 1e-7:
            continue
        t = T[q[2]]
        A, B, Cc = V[t[0]], V[t[1]], V[t[2]]
        Q = np.array(q[0])
        nn, where = None, 'face'
        for X in (A, B, Cc):                                         # at a corner?
            if np.linalg.norm(Q - X) < 1e-5:
                nn, where = Vx.get(key(X), 0), 'corner'
                break
        if where == 'face':
            for X, Y in ((A, B), (B, Cc), (Cc, A)):                    # on an edge?
                e = Y - X
                tt = float(np.dot(Q - X, e) / max(np.dot(e, e), 1e-15))
                if np.linalg.norm(Q - (X + tt * e)) < 1e-5:
                    nn, where = E.get(tuple(sorted((key(X), key(Y)))), 0), 'edge'
                    break
        if where != 'face' and nn is None:
            continue                                                 # an open edge: unknown
        if where == 'face':
            nn = n[q[2]]
        if float(np.dot(np.array(p) - Q, nn)) < -1e-6:
            d[i] = q[3]
            loc[i] = q[2]
    return d, loc


def apply(M, pts):
    A = np.array(M)
    return pts @ A[:3, :3].T + A[:3, 3]


ONLY = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None
report = {}
for name, p in P.items():
    if p['kind'] not in ('hinge', 'twist', 'slide', 'spin') or name not in objs or not name.startswith('IX_'):
        continue
    if ONLY and name not in ONLY:
        continue
    lo, hi = p['range']
    if lo == hi:
        continue
    vals = np.linspace(lo, hi, 25 if p['kind'] != 'slide' else 11)
    grp = [name] + [c.name for c in objs[name].children_recursive if c.name in objs and not c.name.endswith('_Glass')]
    gV = np.concatenate([WM[n][0] for n in grp if len(WM[n][0])])
    size = float(np.linalg.norm(gV.max(0) - gV.min(0)))
    pts0 = samples(grp, 0.01 if size < 0.5 else 0.025)
    if p['kind'] in ('hinge', 'twist', 'spin'):                      # the part's own barrel round the axis: in its pins
        pv, av = np.array(p['pivot']), np.array(p['axis']) / np.linalg.norm(p['axis'])
        rel = pts0 - pv
        pts0 = pts0[np.linalg.norm(rel - np.outer(rel @ av, av), axis=1) > 0.015]
    # the moving shell itself, as a BVH at rest (for the static points sinking into the part)
    gT, gVV, off = [], [], 0
    for n in grp:
        V, T, Z, MI = WM[n]
        gVV += [tuple(v) for v in V]
        gT += [tuple(t + off) for t in T]
        off += len(V)
    # the swept box -> the static objects near it
    corners = []
    for v in vals:
        M = xform(p['kind'], p['pivot'], p['axis'], float(v))
        corners.append(apply(M, gV))
    allc = np.concatenate(corners)
    slo, shi = allc.min(0) - 0.05, allc.max(0) + 0.05
    others = [n for n, (a, b) in BB.items() if n not in grp and not n.endswith('_Glass') and
              not any(n == c.name for c in objs[name].children_recursive) and np.all(b >= slo) and np.all(a <= shi)]
    gbv = BVHTree.FromPolygons(gVV, gT)
    gPS = pseudo(np.array(gVV), np.array(gT))
    spts = {}
    for o in others:                                                 # static points near the swept box
        V, T, Z, MI = WM[o]
        sp = samples([o], 0.01)
        f = np.all((sp >= slo) & (sp <= shi), axis=1)
        if p['kind'] in ('hinge', 'twist', 'spin'):                  # pins and knuckles round the axis turn in place
            pv, av = np.array(p['pivot']), np.array(p['axis']) / np.linalg.norm(p['axis'])
            rel = sp - pv
            dist = np.linalg.norm(rel - np.outer(rel @ av, av), axis=1)
            f &= dist > 0.015
        spts[o] = sp[f]
    worst = {}
    rest1, rest2 = {}, {}
    for k, v in enumerate([0.0] + list(vals)):
        M = xform(p['kind'], p['pivot'], p['axis'], float(v))
        mp = apply(M, pts0)
        Mi = M.inverted()
        for o in others:
            dd, loc = inside_depth(BV[o], mp, WM[o][0], WM[o][1], ps(o))  # the part's points inside o
            sp = spts[o]
            if len(sp):                                              # o's points inside the (moved) part
                d2, loc2 = inside_depth(gbv, apply(Mi, sp), np.array(gVV), np.array(gT), gPS)
            else:
                d2 = np.zeros(0)
            w = worst.setdefault(o, dict(rest=0.0, max=0.0, at=None, zone=None, where=None))
            if k == 0:
                rest1[o], rest2[o] = dd, d2
                w['rest'] = max(float(dd.max()) if len(dd) else 0.0, float(d2.max()) if len(d2) else 0.0)
                continue
            i1 = dd - rest1[o]                                       # deeper than at rest, point by point
            i2 = d2 - rest2[o]
            m1 = float(i1.max()) if len(i1) else 0.0
            m2 = float(i2.max()) if len(i2) else 0.0
            m = max(m1, m2)
            if m > w['max']:
                w['max'] = m
                w['at'] = round(float(v), 3)
                if m1 >= m2:
                    i = int(i1.argmax())
                    w['zone'] = int(WM[o][2][loc[i]]) if loc[i] is not None else None
                    w['where'] = [round(float(x), 3) for x in mp[i]]
                else:
                    i = int(i2.argmax())
                    w['zone'] = 'part'
                    w['where'] = [round(float(x), 3) for x in sp[i]]
    bad = {o: w for o, w in worst.items() if w['max'] > TOL}
    report[name] = dict(kind=p['kind'], range=[lo, hi], others=len(others),
                        worst={o: dict(rest_mm=round(w['rest'] * 1000, 1), deeper_mm=round(w['max'] * 1000, 1), at=w['at'],
                                       zone=w['zone'], where=w['where']) for o, w in bad.items()})
    if bad:
        print('==', name, p['kind'], [lo, hi], flush=True)
        for o, w in sorted(bad.items(), key=lambda kv: -kv[1]['max']):
            print('   %-22s rest %5.1f mm  deeper by %5.1f mm at %s  zone %s  %s' % (o, w['rest'] * 1000, w['max'] * 1000, w['at'],
                                                                           w['zone'], w['where']), flush=True)
n_bad = sum(1 for r in report.values() if r['worst'])
print('parts swept', len(report), 'sinking deeper than %.0f mm while moving: %d' % (TOL * 1000, n_bad))
json.dump(report, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f'sweep2{SUF}.json'), 'w'), indent=1)
