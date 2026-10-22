import bpy, bmesh, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_v9_final_v11.blend')
O = bpy.data.objects
DG = bpy.context.evaluated_depsgraph_get()
bm = bmesh.new()
for n in ['src_Wing']:
    ob = O[n]; me = ob.evaluated_get(DG).to_mesh(); t = bmesh.new(); t.from_mesh(me); t.transform(ob.matrix_world)
    m = bpy.data.meshes.new('_t'); t.to_mesh(m); t.free(); bm.from_mesh(m)
bmesh.ops.triangulate(bm, faces=bm.faces[:])
tree = BVHTree.FromBMesh(bm)
for x in (2.24, 2.30, 2.36):
    print('x', x)
    for k in range(17):
        z = 2.60 + 0.012 * k
        h = tree.ray_cast(Vector((x, -3.6, z)), Vector((0, 1, 0)), 3)
        if h[0] is not None:
            n = h[1]
            print(f'  z {z:.3f} y {h[0].y:+.4f} n ({n.x:+.2f},{n.y:+.2f},{n.z:+.2f}) ang {math.degrees(math.atan2(n.z, -n.y)):+.1f}')
# vertices of the wing near the LE at x 2.3
vs = [v.co for v in bm.verts if abs(v.co.x - 2.3) < 0.25 and v.co.y < -2.3]
vs.sort(key=lambda c: c.y)
print('LE verts near x 2.3:', [(round(c.x,3), round(c.y,3), round(c.z,3)) for c in vs[:24]])
