import bpy, json, math
import numpy as np
from mathutils import Vector, Euler
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
C = json.load(open('/home/claude/uaz/out/gen_contract.json'))
boxes = []
for c in C['colliders']:
    R = Euler([math.radians(a) for a in c.get('rotation', [0, 0, 0])], 'XYZ').to_matrix()
    boxes.append((np.array(c['center_body']), np.array(R), np.array(c['size']) / 2, c['name']))
def outside_dist(p):
    best = 1e9
    for ctr, R, h, n in boxes:
        q = R.T @ (p - ctr)
        d = np.maximum(np.abs(q) - h, 0)
        best = min(best, float(np.linalg.norm(d)))
    return best
roots = ['Genset', 'Switchboard', 'DayTank', 'Shelf', 'Drum_1', 'Drum_2', 'Drum_3', 'Pallet']
res = {}
for r in roots:
    o = bpy.data.objects[r]
    group = [o] + [c for c in o.children_recursive if c.type == 'MESH']
    for g in group:
        if g.name.startswith(('Needle_', 'GLamp_', 'BLamp_')):
            continue
        for v in g.data.vertices:
            p = np.array(g.matrix_world @ v.co)
            if p[2] < 0.40 or p[2] > 1.9:       # only the capsule's band above the step height
                continue
            d = outside_dist(p)
            if d > 0.03:
                key = g.name
                if d > res.get(key, (0,))[0]:
                    res[key] = (round(d, 3), tuple(round(x, 3) for x in p))
for k, v in sorted(res.items(), key=lambda kv: -kv[1][0]):
    print(f'{k:24s} sticks out of every collider by {v[0]*100:.1f} cm at {v[1]}')
