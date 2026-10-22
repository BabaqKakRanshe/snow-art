import bpy, sys, numpy as np
bpy.ops.wm.open_mainfile(filepath=sys.argv[1])
dg = bpy.context.evaluated_depsgraph_get()
rows = []
for o in bpy.data.objects:
    if o.type != 'MESH' or o.name.endswith(('_LOD1','_LOD2','_Shadow')) or o.name.startswith(('COL_','IV_')): continue
    mw = o.matrix_world
    bb = np.array([mw @ __import__('mathutils').Vector(c) for c in o.bound_box])
    U = np.stack([-bb[:,0], bb[:,2], -bb[:,1]], 1)   # Unity frame
    mn, mx = U.min(0), U.max(0)
    # overlap with the glareshield / panel top region
    if mx[2] > 2.6 and mn[2] < 3.5 and mx[1] > 1.85 and mn[1] < 2.4 and mn[0] < 0.5 and mx[0] > -0.5:
        rows.append((o.name, np.round(mn,3).tolist(), np.round(mx,3).tolist(), len(o.data.polygons)))
for r in sorted(rows, key=lambda r: -r[3])[:40]: print(r)
