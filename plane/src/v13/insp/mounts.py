import bpy, bmesh, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_v9_final_v11.blend')
O = bpy.data.objects
print('src objects:', sorted(o.name for o in O if o.name.startswith('src_')))
dg = bpy.context.evaluated_depsgraph_get()
def tree(names):
    bm = bmesh.new()
    for n in names:
        ob = O[n]; me = ob.evaluated_get(dg).to_mesh()
        t = bmesh.new(); t.from_mesh(me); t.transform(ob.matrix_world)
        m = bpy.data.meshes.new('t'); t.to_mesh(m); t.free(); bm.from_mesh(m)
    return BVHTree.FromBMesh(bm)
srcs = [o.name for o in O if o.name.startswith('src_') and o.type == 'MESH' and 'Light' not in o.name]
T = tree(srcs + ['Rudder'])
def ray(o, d, dist=2.0):
    h = T.ray_cast(Vector(o), Vector(d).normalized(), dist)
    return (tuple(round(v,4) for v in h[0]), tuple(round(v,3) for v in h[1])) if h[0] else None
print('fin top z at y=4.25..4.55 (ray down at x=0):')
for y in [4.2,4.25,4.3,4.35,4.4,4.45,4.5,4.55,4.6]:
    print(' y', y, ray((0, y, 4.5), (0,0,-1)))
print('fin top width at z=3.88 (ray from +x/-x):')
for y in [4.25,4.35,4.45,4.55]:
    print(' y', y, ray((0.5, y, 3.88), (-1,0,0)), ray((-0.5, y, 3.88), (1,0,0)))
print('belly z (ray up at x=0):')
for y in [1.4,1.5,1.55,1.6,1.65,1.7,1.75,1.8,1.9]:
    print(' y', y, ray((0, y, 0.3), (0,0,1)))
print('belly across x at y=1.65:')
for x in [-0.15,-0.1,-0.05,0,0.05,0.1,0.15]:
    print(' x', x, ray((x, 1.65, 0.3), (0,0,1)))
print('wingtip face (ray from outboard at x=7.5 toward -x):')
for y in [-2.6,-2.5,-2.45,-2.4,-2.35,-2.3,-2.2,-2.1,-2.05,-2.0,-1.9]:
    for z in [2.84,2.868,2.89]:
        print(' y', y, 'z', z, ray((7.5, y, z), (-1,0,0)))
print('wingtip LE (ray from front):')
for z in [2.82,2.85,2.87,2.89,2.91]:
    print(' z', z, ray((7.05, -3.2, z), (0,1,0)), ray((6.9, -3.2, z), (0,1,0)))
print('wing thickness at x=7.0,y=-2.3:', ray((7.0,-2.3,3.5),(0,0,-1)), ray((7.0,-2.3,2.0),(0,0,1)))
print('tail cone end (ray from aft toward -y) at x=0:')
for z in [2.2,2.23,2.26,2.29,2.32]:
    print(' z', z, ray((0, 6.0, z), (0,-1,0)))
for x in [-0.04,0,0.04]:
    print(' x', x, ray((x, 6.0, 2.26), (0,-1,0)))
print('landing LE (ray from front toward +y) around (2.3, z 2.69):')
for x in [2.2,2.25,2.3,2.35,2.4]:
    for z in [2.63,2.66,2.69,2.72,2.75]:
        print(' x', x, 'z', z, ray((x, -3.5, z), (0,1,0)))
