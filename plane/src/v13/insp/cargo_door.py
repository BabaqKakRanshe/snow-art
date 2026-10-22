import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_unity_v11.blend')
O = bpy.data.objects
def bb(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return (tuple(round(min(p[i] for p in pts),3) for i in range(3)), tuple(round(max(p[i] for p in pts),3) for i in range(3)))
for o in sorted(O, key=lambda o: o.name):
    if any(k in o.name for k in ('CargoDoor', 'Step', 'Strut', 'Window', 'Handle_Cargo', 'Exit_Cargo', 'Barrier', 'COL_Wall', 'COL_Side', 'Fog')) and '_LOD' not in o.name:
        piv = o.matrix_world.translation
        par = o.parent.name if o.parent else None
        print(f'{o.name:34s} {o.type:5s} parent={par} pivot={tuple(round(v,3) for v in piv)} bb={bb(o) if o.type=="MESH" else ""} tris={len(o.data.polygons) if o.type=="MESH" else ""}')
