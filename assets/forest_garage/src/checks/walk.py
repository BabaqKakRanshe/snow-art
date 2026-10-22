"""Walkability of the rebuilt garage (out/garage.blend posed from the contract: the gate and the side door open):
Snow's player capsule (r 0.34, h 1.80, step 0.35) on a 5 cm grid: the floor under each cell by a ray down, the cell free
when the capsule's spine (step + r .. h - r above that floor) keeps r from everything; neighbours joined when their floors
differ by <= the step. Flood fill from the asphalt in front of the gate; then the hall reached, through the gate and
through the side door alone (gate shut), and every IX part within Snow's use range (2.0 m from the eye, clear line).
python3 -I walk.py [--draft|--test]  -> walk.json + walk_*.png next to this script"""
import bpy, sys, os, json, math
import numpy as np
from collections import deque
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0, '/home/claude/uaz')
import gar_spec as S

SFX = '_draft' if '--draft' in sys.argv else '_test' if '--test' in sys.argv else ''
HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=f'/home/claude/uaz/out/garage{SFX}.blend')
C = json.load(open(f'/home/claude/uaz/out/garage_contract{SFX}.json'))
R, H, STEP = 0.34, 1.80, 0.35
REST = {o.name: o.matrix_world.copy() for o in bpy.data.objects}


def pose(open_):
    for n, p in C['parts'].items():
        o = bpy.data.objects.get(n)
        if o is None or p['kind'] != 'hinge':
            continue
        piv, ax = Vector(p['pivot']), Vector(p['axis']).normalized()
        a = p['range'][1] if open_.get(n) else 0.0
        o.matrix_world = (Matrix.Translation(piv) @ Matrix.Rotation(math.radians(a), 4, ax) @ Matrix.Translation(-piv) @
                          REST[n])
    bpy.context.view_layer.update()


def scene_bvh():
    dg = bpy.context.evaluated_depsgraph_get()
    V, T, TOBJ, PARTV = [], [], [], {}
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        me = o.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        M = o.matrix_world
        off = len(V)
        V += [M @ v.co for v in me.vertices]
        T += [tuple(i + off for i in t.vertices) for t in me.loop_triangles]
        TOBJ += [o.name] * len(me.loop_triangles)
        if o.name.startswith('IX_'):
            PARTV[o.name] = (np.array([tuple(M @ v.co) for v in me.vertices]),
                             [tuple(M @ v.co for v in (me.vertices[i] for i in t.vertices)) for t in me.loop_triangles])
        o.evaluated_get(dg).to_mesh_clear()
    nobj = len(T)
    for gx in np.arange(-16.0, 16.0, 0.5):                           # the asphalt round the garage (outside the plinth)
        for gy in np.arange(-14.0, 14.0, 0.5):
            cx, cy = gx + 0.25, gy + 0.25
            if abs(cx) < S.PLX + 0.25 and abs(cy) < S.PLY + 0.25:
                continue
            g0 = len(V)
            V += [Vector((gx, gy, S.GROUND)), Vector((gx + 0.5, gy, S.GROUND)), Vector((gx + 0.5, gy + 0.5, S.GROUND)),
                  Vector((gx, gy + 0.5, S.GROUND))]
            T += [(g0, g0 + 1, g0 + 2), (g0, g0 + 2, g0 + 3)]
    return BVHTree.FromPolygons(V, T), TOBJ, nobj, PARTV


res = 0.05
xs = np.arange(-9.0, 9.0, res)
ys = np.arange(-9.0, 7.0, res)


def flood(BV, start):
    fl = np.full((len(xs), len(ys)), np.nan, np.float32)
    free = np.zeros((len(xs), len(ys)), bool)
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            hit = BV.ray_cast(Vector((x, y, 2.0)), Vector((0, 0, -1)), 4.0)
            if hit[0] is None or hit[1].z < 0.7:
                continue
            f = hit[0].z
            fl[i, j] = f
            free[i, j] = all(BV.find_nearest(Vector((x, y, f + h)), R)[0] is None for h in (STEP + R, 0.88, 1.07, 1.27, H - R))
    s = (int(round((start[0] - xs[0]) / res)), int(round((start[1] - ys[0]) / res)))
    reach = np.zeros_like(free)
    if free[s]:
        q = deque([s])
        reach[s] = True
        while q:
            i, j = q.popleft()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                if 0 <= a < free.shape[0] and 0 <= b < free.shape[1] and free[a, b] and not reach[a, b] and \
                        abs(fl[a, b] - fl[i, j]) <= STEP:
                    reach[a, b] = True
                    q.append((a, b))
    return fl, free, reach


def hall_area(m, fl):
    ia, ib = np.searchsorted(xs, -S.XI), np.searchsorted(xs, S.XI)
    ja, jb = np.searchsorted(ys, -S.YI), np.searchsorted(ys, S.YI)
    lvl = np.abs(fl[ia:ib, ja:jb]) < 0.05
    return round(float((m[ia:ib, ja:jb] & lvl).sum() * res * res), 2)


def png(name, fl, free, reach):
    from PIL import Image
    img = np.zeros((len(ys), len(xs), 3), np.uint8)
    img[...] = (30, 30, 30)
    img[(~np.isnan(fl)).T] = (90, 90, 90)
    img[free.T] = (150, 150, 150)
    img[reach.T] = (60, 170, 80)
    Image.fromarray(img[::-1]).resize((len(xs) * 2, len(ys) * 2), Image.NEAREST).save(os.path.join(HERE, name))


out = {}
START = ((S.GATE['u'][0] + S.GATE['u'][1]) / 2, -8.0)
for case, op in (('both_open', {S.GATE['name']: 1, S.SIDE['name']: 1}), ('side_only', {S.SIDE['name']: 1}),
                 ('gate_only', {S.GATE['name']: 1})):
    pose(op)
    BV, TOBJ, NOBJ, PARTV = scene_bvh()
    fl, free, reach = flood(BV, START)
    out[case] = dict(hall_free_m2=hall_area(free, fl), hall_reached_m2=hall_area(reach, fl),
                     reached_m2=round(float(reach.sum() * res * res), 1))
    print(case, out[case], flush=True)
    png(f'walk_{case}.png', fl, free, reach)
    if case == 'both_open':
        EYE, USE = (1.65, 0.75), 2.0
        far = {}
        for n, p in C['parts'].items():
            if not n.startswith('IX_') or n not in PARTV:
                continue
            verts, tris = PARTV[n]
            pb = BVHTree.FromPolygons([v for t in tris for v in t], [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tris))])
            lo, hi = verts.min(0), verts.max(0)
            best = 99.0
            ia, ib = np.searchsorted(xs, lo[0] - USE), np.searchsorted(xs, hi[0] + USE)
            ja, jb = np.searchsorted(ys, lo[1] - USE), np.searchsorted(ys, hi[1] + USE)
            ii, jj = np.nonzero(reach[ia:ib, ja:jb])
            keep = ((ii % 2) == 0) & ((jj % 2) == 0)
            for i_, j_ in zip(ii[keep], jj[keep]):
                x, y, f = xs[ia + i_], ys[ja + j_], fl[ia + i_, ja + j_]
                for e in EYE:
                    eye = Vector((x, y, f + e))
                    q = pb.find_nearest(eye, USE)
                    if q[0] is None or q[3] >= best:
                        continue
                    d = q[3]
                    hit = BV.ray_cast(eye, (q[0] - eye).normalized(), d + 0.02)
                    if hit[0] is not None and hit[3] < d - 0.02:
                        idx = hit[2]
                        if idx is None or idx >= NOBJ or not TOBJ[idx].startswith(n):
                            continue
                    best = d
            out.setdefault('ix_nearest_eye_m', {})[n] = round(best, 2)
            if best > USE:
                far[n] = round(best, 2)
        out['ix_out_of_reach'] = far
        print('IX parts out of use range:', len(far), far, out['ix_nearest_eye_m'], flush=True)
# the headroom under the open gate (the leaf at 85 deg) over the tracks' area
pose({S.GATE['name']: 1})
BV, TOBJ, NOBJ, PARTV = scene_bvh()
heads = []
for x in np.arange(S.GATE['u'][0] + 0.1, S.GATE['u'][1] - 0.05, 0.25):
    for y in np.arange(-4.2, -1.2, 0.25):
        up = BV.ray_cast(Vector((x, y, 0.05)), Vector((0, 0, 1)), 5.0)
        if up[0] is not None:
            heads.append(up[0].z)
out['gate_open_min_headroom'] = round(min(heads), 3)
print('headroom under the open gate', out['gate_open_min_headroom'])
json.dump(out, open(os.path.join(HERE, 'walk.json'), 'w'), indent=1)
