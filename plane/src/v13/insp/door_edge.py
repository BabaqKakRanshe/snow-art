import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_v9_final_v11.blend')
O = bpy.data.objects
door = O['CargoDoor_L']
W = door.matrix_world
vs = [W @ v.co for v in door.data.vertices]
front = [p for p in vs if p.y < -0.80 and 1.5 < p.z < 1.9]
print('door verts near front edge (y<-0.80, z 1.5-1.9):', sorted({(round(p.x, 3), round(p.y, 3)) for p in front})[:40])
# faces whose normal points forward (-y) near the front edge
me = door.data
fr = []
for poly in me.polygons:
    c = W @ poly.center; n = (W.to_3x3() @ poly.normal).normalized()
    if c.y < -0.80 and n.y < -0.7:
        fr.append((round(c.x, 3), round(c.y, 3), round(c.z, 3), round(poly.area, 4), me.materials[poly.material_index].name))
print('forward-facing faces at the front edge:', len(fr)); print(sorted(fr)[:30])
DG = bpy.context.evaluated_depsgraph_get()
me2 = O['src_Fuselage'].evaluated_get(DG).to_mesh(); bm = bmesh.new(); bm.from_mesh(me2); bm.transform(O['src_Fuselage'].matrix_world)
bmesh.ops.triangulate(bm, faces=bm.faces[:]); T = BVHTree.FromBMesh(bm)
for x in (0.66, 0.70, 0.74):
    h = T.ray_cast(Vector((x, -0.6, 1.70)), Vector((0, -1, 0)), 1.0)
    print('front jamb at x', x, '->', tuple(round(v, 4) for v in h[0]) if h[0] else None)
