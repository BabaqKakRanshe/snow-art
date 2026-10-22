"""Coplanar, same-facing, overlapping triangles (z-fighting candidates) between different primitives / objects."""
import bpy, math
import numpy as np
from mathutils import Vector
from mathutils.geometry import intersect_tri_tri_2d

bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
objs = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith(('COL_', 'Snow_'))]
tris = []      # (obj, polyidx, p0, p1, p2, n, d, island)
for o in objs:
    me = o.data
    me.calc_loop_triangles()
    M = o.matrix_world
    # islands by connectivity
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
    for t in me.loop_triangles:
        p = [M @ me.vertices[i].co for i in t.vertices]
        n = (p[1] - p[0]).cross(p[2] - p[0])
        if n.length < 1e-10:
            continue
        n.normalize()
        tris.append((o.name, t.polygon_index, p, n, n.dot(p[0]), f(t.vertices[0])))
print('tris', len(tris))
buckets = {}
for k, (on, pi, p, n, d, isl) in enumerate(tris):
    key = (round(n.x * 200), round(n.y * 200), round(n.z * 200), round(d / 0.0006))
    buckets.setdefault(key, []).append(k)
found = {}
seen = set()
for key, ks in buckets.items():
    nx, ny, nz, dq = key
    cand = list(ks)
    for dd in (-1, 1):
        cand += buckets.get((nx, ny, nz, dq + dd), [])
    if len(cand) < 2:
        continue
    for a in ks:
        A = tris[a]
        n = A[3]
        # 2D basis on the plane
        u = n.orthogonal().normalized()
        v = n.cross(u)
        a2 = [(q.dot(u), q.dot(v)) for q in A[2]]
        for b in cand:
            if b <= a or (a, b) in seen:
                continue
            B = tris[b]
            if B[0] == A[0] and B[5] == A[5]:
                continue                       # same primitive
            if abs(B[4] - A[4]) > 0.0006 or B[3].dot(n) < 0.9999:
                continue
            seen.add((a, b))
            b2 = [(q.dot(u), q.dot(v)) for q in B[2]]
            if intersect_tri_tri_2d(*[Vector(x) for x in a2], *[Vector(x) for x in b2]):
                # rough overlap area by sampling
                import random
                key2 = tuple(sorted((A[0], B[0])))
                c = (A[2][0] + A[2][1] + A[2][2]) / 3
                r = found.setdefault(key2, [])
                if len(r) < 400:
                    r.append((tuple(round(x, 3) for x in c), tuple(round(x, 2) for x in n), round(abs(B[4] - A[4]) * 1000, 2)))
for k, r in sorted(found.items(), key=lambda kv: -len(kv[1])):
    cs = sorted(set(x[0] for x in r))
    print(k, len(r), 'pairs; examples (centroid, normal, plane gap mm):', r[:5])
