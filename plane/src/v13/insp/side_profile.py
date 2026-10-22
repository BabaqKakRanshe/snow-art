import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_unity_v11.blend')
O = bpy.data.objects
dg = bpy.context.evaluated_depsgraph_get()
bm = bmesh.new()
for n in ('Body',):
    ob = O[n]; me = ob.evaluated_get(dg).to_mesh()
    t = bmesh.new(); t.from_mesh(me); t.transform(ob.matrix_world)
    m = bpy.data.meshes.new('t'); t.to_mesh(m); t.free(); bm.from_mesh(m)
tree = BVHTree.FromBMesh(bm)
zs = [1.0, 1.1, 1.3, 1.6, 1.9, 2.2, 2.4, 2.5, 2.6]
print('y \\ z ' + ' '.join(f'{z:6.2f}' for z in zs))
for y in [-1.2,-0.9,-0.85,-0.6,-0.3,0.0,0.3,0.45,0.6,0.8,1.0,1.2,1.32,1.5,1.7,1.9,2.1,2.4,2.7,3.0]:
    row = []
    for z in zs:
        hit = tree.ray_cast(Vector((3.0, y, z)), Vector((-1, 0, 0)), 3.0)
        row.append(f'{hit[0].x:6.3f}' if hit[0] else '   -  ')
    print(f'{y:5.2f} ' + ' '.join(row))
