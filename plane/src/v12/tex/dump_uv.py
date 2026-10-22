"""Dump UV triangles per material from the v11 Unity-hierarchy scene (what the FBX carries).
blender -b -P dump_uv.py  -> /home/claude/plane/v12/work/uvtris_v11.npz  (key = material name, (n, 3, 2) float32)"""
import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_unity_v11.blend')
WANT = ('M_Cockpit', 'M_Interior', 'M_Floor', 'M_Seats', 'M_Fittings', 'M_Webbing', 'M_Gauges', 'M_Annunciator',
        'M_RadioDisplay', 'M_Survival', 'M_Details')
acc = {m: [] for m in WANT}
objs = {m: set() for m in WANT}
for o in bpy.data.objects:
    if o.type != 'MESH' or not o.data.uv_layers:
        continue
    me = o.data
    me.calc_loop_triangles()
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers[0].data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2)
    mats = [s.material.name if s.material else '' for s in o.material_slots]
    for lt in me.loop_triangles:
        mn = mats[lt.material_index] if lt.material_index < len(mats) else ''
        if mn in acc:
            acc[mn].append(uv[list(lt.loops)])
            objs[mn].add(o.name)
out = {m: np.asarray(v, np.float32).reshape(-1, 3, 2) for m, v in acc.items() if v}
np.savez_compressed('/home/claude/plane/v12/work/uvtris_v11.npz', **out)
for m, v in out.items():
    print(m, len(v), 'tris', len(objs[m]), 'objects', 'uv range', v.min((0, 1)).round(3), v.max((0, 1)).round(3))
