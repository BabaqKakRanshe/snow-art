"""the highest vertices of the figure at a clip frame and their bone weights: python3 -I fig_top.py <fig.blend> <clip> <frame>"""
import bpy, sys
bpy.ops.wm.open_mainfile(filepath=sys.argv[1])
ob = bpy.data.objects['Apparition_Body']; arm = bpy.data.objects['Apparition_Rig']
arm.animation_data.action = bpy.data.actions[sys.argv[2]]
bpy.context.scene.frame_set(int(sys.argv[3]))
dg = bpy.context.evaluated_depsgraph_get()
e = ob.evaluated_get(dg); m = e.to_mesh()
vs = sorted(((ob.matrix_world @ v.co), v.index) for v in m.vertices) if False else [((ob.matrix_world @ v.co), v.index) for v in m.vertices]
vs.sort(key=lambda t: -t[0].z)
names = {g.index: g.name for g in ob.vertex_groups}
for p, i in vs[:8]:
    v = ob.data.vertices[i]
    print([round(c, 3) for c in p], 'rest', [round(c, 3) for c in v.co], [(names[g.group], round(g.weight, 2)) for g in v.groups])
