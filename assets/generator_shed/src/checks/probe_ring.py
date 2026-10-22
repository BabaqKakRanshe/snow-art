import bpy, bmesh
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
o = bpy.data.objects['Genset']
M = o.matrix_world
for cx in (-0.73, 1.83):
    for cy in (-0.63, 0.13):
        c = Vector((cx, cy, 0.22))
        out = inn = 0
        for p in o.data.polygons:
            w = M @ p.center
            if (w - c).length < 0.045:
                n = (M.to_3x3() @ p.normal)
                # tube centre line: circle radius 0.03 around c in the x-z plane
                d = w - c
                d.y = 0
                ring_pt = c + d.normalized() * 0.03 if d.length > 1e-6 else c
                radial = (w - ring_pt)
                if radial.length > 1e-6:
                    if n.dot(radial) > 0: out += 1
                    else: inn += 1
        print('eye', cx, cy, 'outward', out, 'inward', inn)
