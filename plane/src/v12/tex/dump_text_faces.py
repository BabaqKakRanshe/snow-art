"""For every triangle of the text-atlas materials (M_Gauges, M_Annunciator, M_RadioDisplay): object, UVs, world
positions (Unity frame, level pose). -> /home/claude/plane/v12/work/text_faces.npz"""
import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_unity_v11.blend')
WANT = ('M_Gauges', 'M_Annunciator', 'M_RadioDisplay')
M = np.array([[-1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0]])      # Blender -> Unity
UV, P, OB, MT = [], [], [], []
names = []
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type != 'MESH' or not o.data.uv_layers:
        continue
    mats = [s.material.name if s.material else '' for s in o.material_slots]
    if not any(m in WANT for m in mats):
        continue
    me = o.data
    me.calc_loop_triangles()
    uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers[0].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    mw = np.array(o.matrix_world)
    wco = (co @ mw[:3, :3].T + mw[:3, 3]) @ M.T
    oi = len(names); names.append(o.name)
    for lt in me.loop_triangles:
        mn = mats[lt.material_index] if lt.material_index < len(mats) else ''
        if mn not in WANT:
            continue
        UV.append(uv[list(lt.loops)]); P.append(wco[list(lt.vertices)]); OB.append(oi); MT.append(WANT.index(mn))
np.savez_compressed('/home/claude/plane/v12/work/text_faces.npz', uv=np.array(UV, np.float32), p=np.array(P, np.float32),
                    obj=np.array(OB), mat=np.array(MT), names=np.array(names), mats=np.array(WANT))
print(len(UV), 'tris', len(names), 'objects:', names)
