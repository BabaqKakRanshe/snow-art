"""Overall dimensions of each concept from the saved .blend (objects of the Vehicle collection, without the
mannequin, smoke, antenna, mirrors and lights). python3 dims.py -> rend/dims.json"""
import bpy, json, os, sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
out = {}
for mod in ('c1_kung', 'c2_vahta', 'c3_balloon', 'c4_tracked'):
    p = os.path.join(HERE, 'rend', mod, mod + '.blend')
    if not os.path.exists(p):
        continue
    bpy.ops.wm.open_mainfile(filepath=p)
    lo = Vector((1e9, 1e9, 1e9)); hi = -lo
    lo_np = lo.copy(); hi_np = hi.copy()
    col = bpy.data.collections['Vehicle']
    for o in col.objects:
        if o.type != 'MESH' or o.name.startswith(('human', 'smoke', 'antenna', 'rcan', 'spare', 'tarp', 'shovel', 'fcan')):
            continue
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            for k in range(3):
                lo[k] = min(lo[k], w[k]); hi[k] = max(hi[k], w[k])
            if not o.name.startswith(('mirror', 'stove')):
                for k in range(3):
                    lo_np[k] = min(lo_np[k], w[k]); hi_np[k] = max(hi_np[k], w[k])
    out[mod] = dict(L=round(hi_np.x - lo_np.x, 2), W=round(hi_np.y - lo_np.y, 2), H=round(hi_np.z, 2),
                    H_pipe=round(hi.z, 2), x0=round(lo_np.x, 2), x1=round(hi_np.x, 2))
    print(mod, out[mod])
json.dump(out, open(os.path.join(HERE, 'rend', 'dims.json'), 'w'), indent=1, ensure_ascii=False)
