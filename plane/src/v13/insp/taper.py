import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_v9_final_v11.blend')
O = bpy.data.objects
DG = bpy.context.evaluated_depsgraph_get()
def surf(names):
    bm = bmesh.new()
    for n in names:
        ob = O[n]; me = ob.evaluated_get(DG).to_mesh(); t = bmesh.new(); t.from_mesh(me); t.transform(ob.matrix_world)
        m = bpy.data.meshes.new('_t'); t.to_mesh(m); t.free(); bm.from_mesh(m)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    return BVHTree.FromBMesh(bm)
F = surf(['src_Fuselage'])
print('y     ' + '  '.join(f'z{z:.2f}' for z in (1.08, 1.40, 1.77, 2.10, 2.47)))
for k in range(0, 26):
    y = -0.9 + 0.12 * k
    row = []
    for z in (1.08, 1.40, 1.77, 2.10, 2.47):
        h = F.ray_cast(Vector((1.5, y, z)), Vector((-1, 0, 0)), 1.5)
        row.append(f'{h[0].x:.3f}' if h[0] else '  -  ')
    print(f'{y:+.2f} ' + '  '.join(row))
