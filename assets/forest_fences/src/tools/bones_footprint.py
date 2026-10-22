"""Ground footprint of the giant's bones (vertices below a height above the terrain), Unity frame, 2 m cells:
python3 -I bones_footprint.py -- Forest.blend out.json"""
import bpy, sys, json
from mathutils import Matrix, Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
Cinv = Matrix(((-1, 0, 0), (0, 0, 1), (0, -1, 0)))
cells = {}
for ob in bpy.data.objects:
    if ob.type != 'MESH' or not ob.name.startswith('Giant'):
        continue
    M = ob.matrix_world
    me = ob.data
    for v in me.vertices:
        u = Cinv @ (M @ v.co)
        key = (int(u.x // 2), int(u.z // 2))
        lo = cells.get(key)
        if lo is None or u.y < lo:
            cells[key] = u.y
out = [[k[0], k[1], round(h, 2)] for k, h in cells.items()]
json.dump(out, open(a[1], 'w'))
print('bone cells', len(out))
