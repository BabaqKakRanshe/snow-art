"""z-fighting candidates that are actually exposed: sample points inside the overlap of coplanar same-facing triangles
from different primitives, then ray-cast from in front along -n; keep those where the first hit lies on the plane."""
import bpy, math, random
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_point_tri_2d

bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
objs = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith(('COL_', 'Snow_'))]
tris, V, TT = [], [], []
for o in objs:
    me = o.data
    me.calc_loop_triangles()
    M = o.matrix_world
    nv = len(me.vertices)
    par = list(range(nv))
    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for e in me.edges:
        a, b = f(e.vertices[0]), f(e.vertices[1])
        if a != b:
            par[a] = b
    za = me.attributes.get('zone')
    for t in me.loop_triangles:
        p = [M @ me.vertices[i].co for i in t.vertices]
        n = (p[1] - p[0]).cross(p[2] - p[0])
        if n.length < 1e-10:
            continue
        n.normalize()
        off = len(V)
        V += p
        TT.append((off, off + 1, off + 2))
        tris.append((o.name, round(za.data[t.polygon_index].value) if za else -1, p, n, n.dot(p[0]), f(t.vertices[0])))
G = BVHTree.FromPolygons(V, TT)
buckets = {}
for k, tr in enumerate(tris):
    n, d = tr[3], tr[4]
    buckets.setdefault((round(n.x * 200), round(n.y * 200), round(n.z * 200), round(d / 0.0006)), []).append(k)
random.seed(1)
hits = {}
for key, ks in buckets.items():
    cand = list(ks)
    for dd in (-1, 1):
        cand += buckets.get((key[0], key[1], key[2], key[3] + dd), [])
    for a in ks:
        A = tris[a]
        n = A[3]
        u = n.orthogonal().normalized(); v = n.cross(u)
        A2 = [Vector((q.dot(u), q.dot(v))) for q in A[2]]
        for b in cand:
            if b <= a:
                continue
            B = tris[b]
            if (B[0] == A[0] and B[5] == A[5]) or abs(B[4] - A[4]) > 0.0006 or B[3].dot(n) < 0.9999:
                continue
            B2 = [Vector((q.dot(u), q.dot(v))) for q in B[2]]
            for s in range(12):
                r1, r2 = random.random(), random.random()
                if r1 + r2 > 1:
                    r1, r2 = 1 - r1, 1 - r2
                P2 = A2[0] + (A2[1] - A2[0]) * r1 + (A2[2] - A2[0]) * r2
                if not intersect_point_tri_2d(P2, *B2):
                    continue
                P3 = A[2][0] + (A[2][1] - A[2][0]) * r1 + (A[2][2] - A[2][0]) * r2
                loc, nrm, idx, dist = G.ray_cast(P3 + n * 0.05, -n, 0.2)
                if loc is None or abs((loc - P3).dot(n)) > 0.0008:
                    continue
                k2 = (A[0], A[1], B[0], B[1])
                hits.setdefault(k2, []).append(tuple(round(x, 3) for x in P3) + (tuple(round(x, 2) for x in n),))
                break
for k, r in sorted(hits.items(), key=lambda kv: -len(kv[1])):
    xs = [p[0] for p in r]; ys = [p[1] for p in r]; zs = [p[2] for p in r]
    print(k, len(r), 'bbox x %.3f..%.3f y %.3f..%.3f z %.3f..%.3f' % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)), 'eg', r[:3])
