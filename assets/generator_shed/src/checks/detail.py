"""Focused checks: door meeting-edge clash (fine sweep), Board_Door vs cabinet, shutter at 180, buried parts (containment)."""
import bpy, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
C = json.load(open('/home/claude/uaz/out/gen_contract.json'))
P = C['parts']
objs = {o.name: o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith(('COL_',))}


def wm(o, M=Matrix.Identity(4)):
    me = o.data
    me.calc_loop_triangles()
    W = M @ o.matrix_world
    V = [W @ v.co for v in me.vertices]
    T = [tuple(t.vertices) for t in me.loop_triangles]
    return V, T


def bvh(names, M=Matrix.Identity(4)):
    V, T = [], []
    for n in names:
        v, t = wm(objs[n], M)
        off = len(V)
        V += v
        T += [(a + off, b + off, c + off) for a, b, c in t]
    return BVHTree.FromPolygons(V, T), V, T


def rot(piv, ax, deg):
    piv = Vector(piv)
    return Matrix.Translation(piv) @ Matrix.Rotation(math.radians(deg), 4, Vector(ax)) @ Matrix.Translation(-piv)


def max_pen(movV, other_bvh):
    """deepest vertex of movV inside other (nearest-face normal test)"""
    best = 0.0
    arg = None
    for v in movV:
        loc, nrm, idx, d = other_bvh.find_nearest(v)
        if loc is None:
            continue
        if (v - loc).dot(nrm) < 0 and d > best:
            best, arg = d, v
    return best, arg


print('--- (a) Door_R opening with Door_L shut: fine sweep')
bL, VL, TL = bvh(['Door_L'])
for deg in np.arange(0.5, 10.01, 0.5):
    M = rot(P['Door_R']['pivot'], P['Door_R']['axis'], deg)
    bR, VR, TR = bvh(['Door_R'], M)
    pairs = bL.overlap(bR)
    pen, at = max_pen(VR, bL)
    if pairs:
        print(f'  Door_R {deg:4.1f} deg: {len(pairs)} tri pairs with Door_L, deepest Door_R vertex inside Door_L {pen*1000:.1f} mm at',
              tuple(round(x, 3) for x in at) if at else None)
print('--- (a2) Door_L opening with Door_R shut')
bR0, VR0, _ = bvh(['Door_R'])
for deg in np.arange(0.5, 10.01, 0.5):
    M = rot(P['Door_L']['pivot'], P['Door_L']['axis'], deg)
    b, V, T = bvh(['Door_L'], M)
    pairs = bR0.overlap(b)
    pen, at = max_pen(V, bR0)
    if pairs:
        print(f'  Door_L {deg:4.1f}: {len(pairs)} pairs, deepest {pen*1000:.1f} mm at', tuple(round(x, 3) for x in at) if at else None)

print('--- (b) Board_Door vs Switchboard (excluding the hinge strip x < -1.86)')
bS, VS, TS = bvh(['Switchboard'])
for deg in [0, 1, 2, 3, 5, 8, 12, 20, 30, 45, 60, 80, 100]:
    M = rot(P['Board_Door']['pivot'], P['Board_Door']['axis'], deg)
    b, V, T = bvh(['Board_Door'], M)
    pairs = bS.overlap(b)
    pts = []
    for i, j in pairs:
        a, bb, c = TS[i]
        cen = (VS[a] + VS[bb] + VS[c]) / 3
        if cen.x > -1.86:
            pts.append(cen)
    Vd = [v for v in V if v.x > -1.86]
    pen, at = max_pen(Vd, bS)
    if pts or pen > 1e-4:
        xs = [p.x for p in pts]
        print(f'  {deg:5.1f} deg: {len(pts)} rim tris hit, x {min(xs) if xs else 0:.3f}..{max(xs) if xs else 0:.3f}, '
              f'deepest door vertex inside cabinet {pen*1000:.1f} mm at', tuple(round(x, 3) for x in at) if at else None)

print('--- (c) Window_Shutter at 180 vs Shed: hit regions')
bSh, VSh, TSh = bvh(['Shed'])
M = rot(P['Window_Shutter']['pivot'], P['Window_Shutter']['axis'], 180)
b, V, T = bvh(['Window_Shutter'], M)
pairs = bSh.overlap(b)
cl = {}
for i, j in pairs:
    a, bb, c = TSh[i]
    cen = (VSh[a] + VSh[bb] + VSh[c]) / 3
    key = (round(cen.z, 2), round(cen.y, 2))
    cl[key] = cl.get(key, 0) + 1
print('  shed tri centroids (z, y): count', sorted(cl.items())[:30])
pen, at = max_pen(V, bSh)
print('  deepest shutter vertex inside shed geometry', round(pen * 1000, 1), 'mm at', at)
for deg in (0, 90, 150, 170, 180):
    M = rot(P['Window_Shutter']['pivot'], P['Window_Shutter']['axis'], deg)
    b, V, T = bvh(['Window_Shutter'], M)
    lo = Vector((min(v.x for v in V), min(v.y for v in V), min(v.z for v in V)))
    hi = Vector((max(v.x for v in V), max(v.y for v in V), max(v.z for v in V)))
    print(f'  shutter at {deg}: bbox', tuple(round(x, 3) for x in lo), tuple(round(x, 3) for x in hi))

print('--- (d) containment: vertices of each part inside another object (nearest-normal test, depth > 1 mm)')
allb = {n: bvh([n]) for n in objs if not n.startswith('Snow_')}
for name in objs:
    if name.startswith('Snow_') or name in ('Shed',):
        continue
    V, T = wm(objs[name])
    for other, (bo, Vo, To) in allb.items():
        if other == name:
            continue
        inside = 0
        deep = 0.0
        for v in V:
            loc, nrm, idx, d = bo.find_nearest(v, 0.06)
            if loc is None:
                continue
            if (v - loc).dot(nrm) < -1e-4:
                inside += 1
                deep = max(deep, d)
        frac = inside / max(1, len(V))
        if frac > 0.5 and deep > 0.001:
            print(f'  {name}: {inside}/{len(V)} verts ({frac:.0%}) inside {other}, max depth {deep*1000:.1f} mm')
