import bpy, json
from mathutils import Vector, Matrix
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_unity_v13.blend')
O = bpy.data.objects
vols = json.load(open('/home/claude/plane/export/unity_v13fx/Assets/UtilityPlane/Data/interaction_volumes.json'))
vols = vols['volumes'] if isinstance(vols, dict) else vols
def u2b(v): return Vector((-v[0], -v[2], v[1]))       # Unity (x right, y up, z fwd) -> build (x left, y aft, z up)
boxes = {}
for z in vols:
    par = z['parent']
    ob = O.get(par)
    M = ob.matrix_world if ob is not None and par != 'UtilityPlane' else Matrix()
    c = M @ u2b(z['center'])
    h = Vector((abs(z['halfExtents'][0]), abs(z['halfExtents'][2]), abs(z['halfExtents'][1])))
    boxes[z['id']] = (c - h, c + h)
def ov(a, b):
    return all(a[0][i] < b[1][i] and b[0][i] < a[1][i] for i in range(3))
for k in [k for k in boxes if 'Edge' in k]:
    hits = [o for o in boxes if o != k and ov(boxes[k], boxes[o])]
    lo, hi = boxes[k]
    print(k, 'box', tuple(round(v, 3) for v in lo), tuple(round(v, 3) for v in hi), 'overlaps:', hits)
