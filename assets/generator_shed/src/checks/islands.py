"""Floating islands: every connected component (shared vertices) of every mesh; report those that neither intersect nor
come within TOL of any other component (of any object). Also a few targeted ray probes."""
import bpy, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
TOL = 0.0025
objs = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith(('COL_', 'Snow_'))]
V, T, own = [], [], []          # global triangles; own = (obj name, island id)
isl_tris = {}
isl_verts = {}
for o in objs:
    me = o.data
    me.calc_loop_triangles()
    M = o.matrix_world
    nv = len(me.vertices)
    # union-find over vertices by edges (KB creates new verts per primitive, so islands = primitives)
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
    # also merge vertices at identical positions (welded primitives)
    pos = {}
    for v in me.vertices:
        k = tuple(round(c, 5) for c in v.co)
        if k in pos:
            a, b = f(v.index), f(pos[k])
            if a != b:
                par[a] = b
        else:
            pos[k] = v.index
    off = len(V)
    V += [M @ v.co for v in me.vertices]
    for t in me.loop_triangles:
        isl = (o.name, f(t.vertices[0]))
        T.append(tuple(i + off for i in t.vertices))
        own.append(isl)
        isl_tris.setdefault(isl, []).append(len(T) - 1)
    for v in me.vertices:
        isl_verts.setdefault((o.name, f(v.index)), []).append(off + v.index)
G = BVHTree.FromPolygons(V, T)
print('islands', len(isl_tris), 'tris', len(T))
floating = []
for isl, tris in isl_tris.items():
    tv = sorted({i for t in tris for i in T[t]})
    remap = {g: k for k, g in enumerate(tv)}
    b = BVHTree.FromPolygons([V[g] for g in tv], [tuple(remap[i] for i in T[t]) for t in tris])
    hit = any(own[i] != isl for i, j in G.overlap(b))
    if hit:
        continue
    # nearest other-island surface from this island's vertices
    best = 1e9
    who = None
    for g in tv:
        for loc, nrm, idx, d in G.find_nearest_range(V[g], 0.05):
            if own[idx] != isl and d < best:
                best, who = d, own[idx]
    if best > TOL:
        lo = Vector((min(V[g].x for g in tv), min(V[g].y for g in tv), min(V[g].z for g in tv)))
        hi = Vector((max(V[g].x for g in tv), max(V[g].y for g in tv), max(V[g].z for g in tv)))
        floating.append((best, isl, lo, hi, who))
floating.sort(key=lambda r: -r[0])
for best, isl, lo, hi, who in floating:
    print(f'FLOAT {isl[0]:22s} gap {best*1000 if best < 1e8 else 999:6.1f} mm  bbox', tuple(round(x, 3) for x in lo),
          tuple(round(x, 3) for x in hi), 'nearest', who[0] if who else None)
