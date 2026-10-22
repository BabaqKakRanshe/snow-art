import bpy, json, math
import numpy as np
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
C = json.load(open('/home/claude/uaz/out/gen_contract.json'))
O = bpy.data.objects


def bvh(name, M=Matrix.Identity(4)):
    o = O[name]
    me = o.data
    me.calc_loop_triangles()
    W = M @ o.matrix_world
    V = [W @ v.co for v in me.vertices]
    return BVHTree.FromPolygons(V, [tuple(t.vertices) for t in me.loop_triangles]), V


def ray(name_or_bvh, org, d, dist=2.0):
    b = name_or_bvh if isinstance(name_or_bvh, BVHTree) else bvh(name_or_bvh)[0]
    return b.ray_cast(Vector(org), Vector(d).normalized(), dist)


print('--- floating checks by rays (first hit distance along the probe)')
for nm, org, d, what in (('Door_R', (-2.4795, -0.15, 1.10), (1, 0, 0), 'hasp plate back (x=-2.475) -> leaf'),
                         ('Door_R', (-2.469, -0.55, 1.80), (1, 0, 0), 'upper strap hinge back (x=-2.47) -> leaf, y=-0.55'),
                         ('Door_R', (-2.469, -0.55, 0.40), (1, 0, 0), 'lower strap hinge back -> leaf/brace, y=-0.55'),
                         ('Door_L', (-2.469, 0.55, 1.80), (1, 0, 0), 'Door_L upper strap back -> leaf, y=0.55'),
                         ('Door_R', (-2.4695, -0.25, 1.0), (1, 0, 0), 'outside D handle foot plane -> leaf')):
    loc, n, i, dist = ray(nm, org, d)
    print(f'  {what}: hit at x={loc.x:.4f} gap {dist*1000:.1f} mm' if loc else f'  {what}: no hit')
loc, n, i, dist = ray('Pallet', (1.27, 1.235, 0.249), (0, 0, -1))
print('  Drum_1 bottom (z=0.25) -> pallet deck gap %.1f mm' % ((0.25 - loc.z) * 1000))
loc, n, i, dist = ray('Shed', (-2.42, 0.55, 2.302), (1, 0, 0))
print('  key nail start x=-2.405 -> cladding at x=%.4f' % loc.x)
loc, n, i, dist = ray('Shed', (2.75, -0.13 + 0.048, 3.716), (0, 0, -1))
print('  exhaust flap hinge pin -> nothing under it? first hit z', loc.z if loc else None)
print('--- Radiator_Drain handle inside the radiator upright?')
bG, VG = bvh('Genset')
for p in ((1.54, -0.647, 0.36), (1.54, -0.64, 0.36), (1.54, -0.655, 0.36)):
    # parity test along +x, -x
    cnt = 0
    org = Vector(p)
    for d in (Vector((1, 0, 0)), Vector((-1, 0, 0)), Vector((0, 0, 1))):
        hits, o = 0, org.copy()
        while True:
            loc, n, i, dist = bG.ray_cast(o, d, 5)
            if loc is None:
                break
            hits += 1
            o = loc + d * 1e-5
        cnt += hits % 2
    print('  point', p, 'inside Genset solid (parity votes of 3):', cnt)
loc, n, i, dist = ray(bG, (1.54, -0.90, 0.36), (0, 1, 0))
print('  ray from the aisle (y=-0.90) toward the drain: first Genset hit at y=%.3f (drain handle tip y=-0.650)' % loc.y)
print('--- DayTank_Valve at 90 vs the bracket strut: penetration')
P = C['parts']['DayTank_Valve']
M = Matrix.Translation(Vector(P['pivot'])) @ Matrix.Rotation(math.radians(90), 4, Vector(P['axis'])) @ Matrix.Translation(-Vector(P['pivot']))
bV, VV = bvh('DayTank_Valve', M)
xs = [v.x for v in VV]; zs = [v.z for v in VV]; ys = [v.y for v in VV]
print('  valve at 90 bbox x %.3f..%.3f y %.3f..%.3f z %.3f..%.3f' % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
bT, VT = bvh('DayTank')
print('  overlapping tri pairs with DayTank:', len(bT.overlap(bV)))
for ang in (60, 70, 75, 80, 85, 90):
    M = Matrix.Translation(Vector(P['pivot'])) @ Matrix.Rotation(math.radians(ang), 4, Vector(P['axis'])) @ Matrix.Translation(-Vector(P['pivot']))
    b2, _ = bvh('DayTank_Valve', M)
    print('   angle', ang, 'pairs', len(bT.overlap(b2)))
print('--- roof colliders: coverage of the roof top surface and the ridge')
cols = {c['name']: c for c in C['colliders']}


def inside_box(p, c):
    ctr = Vector(c['center_body'])
    R = Euler([math.radians(a) for a in c.get('rotation', [0, 0, 0])], 'XYZ').to_matrix()
    q = R.transposed() @ (Vector(p) - ctr)
    return all(abs(q[i]) <= c['size'][i] / 2 + 1e-6 for i in range(3))


import gen_kit as K
for y in (0.0, 0.03, 0.06, 0.1, 0.5, 1.0, 1.7, 2.0):
    zt = K.z_st(y)
    for frac, lab in ((1.0, 'top'), (0.5, 'mid')):
        zz = K.z_rb(y) + (zt - K.z_rb(y)) * frac - 1e-3
        covered = any(inside_box((0.0, s * y, zz), cols[n]) for s, n in ((1, 'COL_Roof_N'), (-1, 'COL_Roof_S'), (1, 'COL_Roof_S'), (-1, 'COL_Roof_N')))
        print(f'  y={y:.2f} {lab} z={zz:.3f}: covered={covered}')
print('  ridge cap top z', K.z_st(0) + 0.025)
for z in np.arange(3.24, 3.52, 0.02):
    cov = any(inside_box((0.0, 0.0, z), cols[n]) for n in ('COL_Roof_N', 'COL_Roof_S'))
    print('   y=0 z=%.2f covered %s' % (z, cov))
print('--- gable (west) coverage: points on the gable triangle not in any collider')
unc = []
for y in np.arange(-1.69, 1.70, 0.05):
    for z in np.arange(2.46, K.z_rb(y) - 0.005, 0.02):
        p = (-2.34, y, z)
        if not any(inside_box(p, c) for c in C['colliders']):
            unc.append((round(y, 2), round(z, 2)))
print('  uncovered samples', len(unc), 'y range', (min(u[0] for u in unc), max(u[0] for u in unc)) if unc else None)
ys_ = sorted(set(u[0] for u in unc))
print('  e.g.', [u for u in unc if abs(u[0]) < 0.05][:5], [u for u in unc if abs(u[0] - 1.46) < 0.03][:5])
print('--- fan blade pitch vs spin sign')
F = O['Engine_Fan']
me = F.data
best = None
for p in me.polygons:
    c = F.matrix_world @ p.center
    r = Vector((0, c.y - (-0.25), c.z - 0.84))
    if r.length > 0.12 and p.area > 0.008:
        n = (F.matrix_world.to_3x3() @ p.normal).normalized()
        tang = Vector((1, 0, 0)).cross(r.normalized())        # +rotation direction about +x
        print('  blade face centre', tuple(round(x, 3) for x in c), 'normal', tuple(round(x, 2) for x in n), 'n.tang %.2f n.x %.2f' % (n.dot(tang), n.x))
        break
