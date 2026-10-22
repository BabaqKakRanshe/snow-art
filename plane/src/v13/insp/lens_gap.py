import bpy, bmesh, sys, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_unity_v11.blend')
O = bpy.data.objects
dg = bpy.context.evaluated_depsgraph_get()
def bvh(names):
    bm = bmesh.new()
    for n in names:
        ob = O.get(n)
        if not ob or ob.type != 'MESH': continue
        me = ob.evaluated_get(dg).to_mesh()
        tmp = bmesh.new(); tmp.from_mesh(me); tmp.transform(ob.matrix_world)
        m = bpy.data.meshes.new('t'); tmp.to_mesh(m); tmp.free()
        bm.from_mesh(m); bpy.data.meshes.remove(m)
    return BVHTree.FromBMesh(bm), bm
print('objects with Lens/Light/Fin/Rudder/Body/Wing names:')
for o in O:
    if o.type == 'MESH' and any(k in o.name for k in ('Lens_', 'Body', 'Rudder', 'Fin', 'Wing', 'Aileron', 'Elevator')) and '_LOD' not in o.name:
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        mn = Vector((min(p.x for p in bb), min(p.y for p in bb), min(p.z for p in bb)))
        mx = Vector((max(p.x for p in bb), max(p.y for p in bb), max(p.z for p in bb)))
        print(f'{o.name:28s} mats={[m.name for m in o.data.materials if m]} min={tuple(round(v,3) for v in mn)} max={tuple(round(v,3) for v in mx)} tris={len(o.data.polygons)}')
tree, bm = bvh([o.name for o in O if o.type=='MESH' and o.name in ('Body','Rudder','Aileron_L','Aileron_R','Elevator_L','Elevator_R','Flap_L','Flap_R')])
for o in O:
    if o.type=='MESH' and o.name.startswith('Lens_') and not o.name.startswith(('Lens_Dome','Lens_Cargo','Lens_Flood')) and '_LOD' not in o.name:
        vs = [o.matrix_world @ v.co for v in o.data.vertices]
        c = sum(vs, Vector())/len(vs)
        best = 9
        for v in vs:
            loc, n, i, d = tree.find_nearest(v)
            best = min(best, d)
        loc, n, i, d = tree.find_nearest(c)
        print(f'{o.name:22s} centre={tuple(round(x,3) for x in c)} nearest_body_from_centre={d:.3f} at {tuple(round(x,3) for x in loc)} n={tuple(round(x,2) for x in n)} | min vert->body {best:.3f}')
