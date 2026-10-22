"""Bone occupancy along lines (Unity frame) from the giant's meshes in Forest.blend (U3), with Blender's BVH:
python3 -I bone_probe.py -- <Forest.blend> <queries.json> <out.json>
queries.json: {"lines": [[[x0, z0], [x1, z1]], ...], "step": 0.1, "half": 0.55, "zlo": 0.15, "zhi": 2.2,
               "ground": "<map_big.json>"}
out: per line a list of [s, occupied(0/1)] runs: the occupied intervals along the line [[s0, s1], ...]"""
import bpy, sys, json, math
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
Q = json.load(open(a[1]))
Cinv = Matrix(((-1, 0, 0), (0, 0, 1), (0, -1, 0)))            # Blender map -> Unity
verts, polys = [], []
dg = bpy.context.evaluated_depsgraph_get()
nob = 0
for ob in bpy.data.objects:
    if ob.type != 'MESH' or not ob.name.startswith('Giant'):
        continue
    M = ob.matrix_world
    me = ob.data
    base = len(verts)
    for v in me.vertices:
        u = Cinv @ (M @ v.co)
        verts.append((u.x, u.y, u.z))
    for p in me.polygons:
        polys.append([base + i for i in p.vertices])
    nob += 1
print('bone objects', nob, 'verts', len(verts), 'polys', len(polys))
bvh = BVHTree.FromPolygons(verts, polys)
B = json.load(open(Q['ground']))
from scipy.interpolate import LinearNDInterpolator
T = np.array(B['terrain'])
g = LinearNDInterpolator(T[:, [0, 2]], T[:, 1])
V = np.array(verts)
lo_xz, hi_xz = V[:, [0, 2]].min(0), V[:, [0, 2]].max(0)
step, half, zlo, zhi = Q.get('step', 0.1), Q.get('half', 0.55), Q.get('zlo', 0.15), Q.get('zhi', 2.2)
res = []
for line in Q['lines']:
    A, Bp = np.array(line[0], float), np.array(line[1], float)
    D = Bp - A
    Lr = float(np.linalg.norm(D))
    D /= Lr
    n = np.array([D[1], -D[0]])
    ss = np.arange(0.0, Lr + 1e-9, step)
    occ = np.zeros(len(ss), bool)
    for k, s in enumerate(ss):
        c = A + D * s
        if not (lo_xz[0] - 2 < c[0] < hi_xz[0] + 2 and lo_xz[1] - 2 < c[1] < hi_xz[1] + 2):
            continue
        hit = False
        for off in (-half, 0.0, half):
            p = c + n * off
            gy = float(g(p[0], p[1]))
            top = Vector((p[0], gy + zhi, p[1]))
            h = bvh.ray_cast(top, Vector((0, -1, 0)), zhi - zlo)
            if h[0] is not None:
                hit = True
                break
            # inside a thick bone: parity of hits going up from the middle of the range
            o = Vector((p[0], gy + (zlo + zhi) / 2, p[1]))
            cnt, start = 0, o
            for _ in range(12):
                h = bvh.ray_cast(start, Vector((0, 1, 0)), 400.0)
                if h[0] is None:
                    break
                cnt += 1
                start = h[0] + Vector((0, 1e-3, 0))
            if cnt % 2 == 1:
                hit = True
                break
        occ[k] = hit
    runs, s0 = [], None
    for k in range(len(ss)):
        if occ[k] and s0 is None:
            s0 = ss[k]
        if (not occ[k] or k == len(ss) - 1) and s0 is not None:
            runs.append([round(float(s0), 2), round(float(ss[k]), 2)])
            s0 = None
    res.append(dict(length=round(Lr, 3), occupied=runs))
    print('line %.1f m: %d bone runs, %.1f m occupied' % (Lr, len(runs), sum(b - a_ for a_, b in runs)))
json.dump(dict(lines=res, step=step, half=half, zlo=zlo, zhi=zhi), open(a[2], 'w'))
