"""Ray probes: back-face hits (inverted / single-sided faces seen from the wrong side -> invisible in Unity with culling)
from viewpoints inside and outside the shed; escaping rays from inside (holes)."""
import bpy, json, math, sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
WITH_SNOW = '--snow' in sys.argv
objs = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('COL_')
        and (WITH_SNOW or not o.name.startswith('Snow_'))]
V, T, own = [], [], []
for o in objs:
    me = o.data
    me.calc_loop_triangles()
    za = me.attributes.get('zone')
    M = o.matrix_world
    off = len(V)
    V += [M @ v.co for v in me.vertices]
    for t in me.loop_triangles:
        T.append(tuple(i + off for i in t.vertices))
        own.append((o.name, round(za.data[t.polygon_index].value) if za else -1))
G = BVHTree.FromPolygons(V, T)


def sphere(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = math.pi * (1 + 5 ** 0.5) * i
    return [Vector((math.cos(t) * math.sin(p), math.sin(t) * math.sin(p), math.cos(p))) for t, p in zip(th, phi)]


DIRS = sphere(6000)
inside = [(-1.9, 0.0, 1.7), (-1.6, -1.0, 1.7), (-1.6, 0.6, 1.7), (-0.9, -0.6, 1.7), (-0.2, 0.55, 1.7), (-0.2, -1.15, 1.7),
          (0.9, 0.6, 1.7), (0.9, -1.15, 1.7), (1.95, 0.6, 1.0), (-1.9, 0.0, 0.6), (0.4, 0.5, 0.5), (-0.5, -1.2, 0.5),
          (-1.0, 0.0, 2.3), (0.5, -1.0, 2.3)]
outside = [(-5.0, 0.0, 1.6), (-4.0, -3.0, 1.6), (-4.0, 3.0, 1.6), (0.0, -5.0, 1.6), (0.0, 5.0, 1.6), (4.0, -3.0, 1.6),
           (4.0, 3.0, 1.6), (5.0, 0.0, 1.6), (0.0, -6.0, 5.0), (0.0, 6.0, 5.0), (-6.0, 0.0, 5.0), (6.0, 0.0, 5.0),
           (-3.2, 0.0, 0.4), (0.0, -2.3, 2.2), (2.9, -0.6, 2.2), (-3.0, -1.0, 2.2), (0.0, 2.3, 2.2), (3.3, 0.0, 4.0)]
back = {}
esc = []
for tag, pts in (('in', inside), ('out', outside)):
    for p in pts:
        o = Vector(p)
        for d in DIRS:
            loc, nrm, idx, dist = G.ray_cast(o, d, 30.0)
            if loc is None:
                if tag == 'in':
                    esc.append((p, tuple(round(x, 2) for x in d)))
                continue
            if nrm.dot(d) > 1e-6:      # hit the back of a face
                key = own[idx]
                b = back.setdefault(key, dict(n=0, ex=[], views=set()))
                b['n'] += 1
                b['views'].add(tag)
                if len(b['ex']) < 4:
                    b['ex'].append((p, tuple(round(x, 3) for x in loc)))
print('BACK-FACE HITS (object, zone): count, views, examples (viewpoint, hit)')
for k, b in sorted(back.items(), key=lambda kv: -kv[1]['n']):
    print(' ', k, b['n'], sorted(b['views']), b['ex'][:3])
print('ESCAPING RAYS FROM INSIDE:', len(esc))
for p, d in esc[:60]:
    print('  from', p, 'dir', d)
