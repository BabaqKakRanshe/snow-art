import bpy, sys, json, numpy as np
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=sys.argv[1])
dg = bpy.context.evaluated_depsgraph_get()
keys = ('Lens_', 'Lamp_Dome', 'Dome', 'Flood', 'Cargo', 'Glareshield', 'Panel', 'Light', 'Beacon', 'Strobe', 'Nav', 'Landing')
res = {}
for o in bpy.data.objects:
    if not any(k in o.name for k in keys): continue
    if o.type != 'MESH':
        print('EMPTY', o.name, o.type, tuple(round(x,4) for x in o.matrix_world.translation), o.parent.name if o.parent else None)
        continue
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    mw = o.matrix_world
    V = np.array([mw @ v.co for v in me.vertices])
    me.calc_loop_triangles()
    # area-weighted normal
    n = Vector((0,0,0)); A = 0
    for t in me.loop_triangles:
        n += (mw.to_3x3() @ t.normal) * t.area; A += t.area
    mats = [s.material.name if s.material else None for s in o.material_slots]
    print('MESH', o.name, 'parent', o.parent.name if o.parent else None, 'verts', len(V), 'tris', len(me.loop_triangles),
          'min', np.round(V.min(0),4).tolist(), 'max', np.round(V.max(0),4).tolist(), 'mats', mats,
          'origin', tuple(round(x,4) for x in mw.translation))
    ev.to_mesh_clear()
