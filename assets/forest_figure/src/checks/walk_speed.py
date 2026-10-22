"""the left foot over the Walk clip: where its lowest vertices are per frame (the stance foot should keep still)
python3 -I walk_speed.py <fig.blend>"""
import bpy, sys, numpy as np
bpy.ops.wm.open_mainfile(filepath=sys.argv[1])
ob = bpy.data.objects['Apparition_Body']; arm = bpy.data.objects['Apparition_Rig']
arm.animation_data.action = bpy.data.actions['Walk']
sc = bpy.context.scene
gi = ob.vertex_groups['Foot.L'].index
FV = [v.index for v in ob.data.vertices if any(g.group == gi and g.weight > 0.3 for g in v.groups)]
ys = {}
for f in range(1, 32):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg); m = e.to_mesh()
    pts = np.array([tuple(ob.matrix_world @ m.vertices[i].co) for i in FV])
    e.to_mesh_clear()
    low = pts[pts[:, 2] < pts[:, 2].min() + 0.004]
    ys[f] = (round(float(low[:, 1].mean()), 4), round(float(pts[:, 2].min()), 4), round(float(low[:, 1].min()), 4), round(float(low[:, 1].max()), 4))
for f, v in ys.items():
    print(f, v)
