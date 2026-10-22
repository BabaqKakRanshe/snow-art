"""v12r2: per-material triangles with UV, world position and shading normal from the v11 Unity-hierarchy scene (the
FBX the package carries): input of the per-texel position / normal maps for the stronger PSX interior.
python3 dump_geo.py -> /home/claude/plane/v12r2/work/geotris_v11.npz (keys <mat>_uv (n,3,2), <mat>_p (n,3,3) metres,
<mat>_n (n,3,3), <mat>_o (n,) object index; objects = names)"""
import bpy
import numpy as np
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_unity_v11.blend')
WANT = ('M_Cockpit', 'M_Interior', 'M_Floor', 'M_Seats', 'M_Fittings', 'M_Webbing')
acc = {m: ([], [], [], []) for m in WANT}
names = []
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type != 'MESH' or not o.data.uv_layers:
        continue
    mats = [s.material.name if s.material else '' for s in o.material_slots]
    if not any(m in WANT for m in mats) or o.name.endswith(('_LOD1', '_LOD2', '_Shadow')):
        continue                                     # LODs and shadow proxies share the LOD0 UVs
    me = o.data
    me.calc_loop_triangles()
    try:
        me.calc_normals_split()
    except AttributeError:
        pass
    nl = len(me.loops)
    uv = np.empty(nl * 2, np.float32); me.uv_layers[0].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    ln = np.empty(nl * 3, np.float32)
    try:
        me.corner_normals.foreach_get('vector', ln)
    except AttributeError:
        me.loops.foreach_get('normal', ln)
    ln = ln.reshape(-1, 3)
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    lv = np.empty(nl, np.int32); me.loops.foreach_get('vertex_index', lv)
    mw = np.array(o.matrix_world, np.float64)
    nm = np.linalg.inv(mw[:3, :3]).T
    P = co @ mw[:3, :3].T + mw[:3, 3]
    N = ln @ nm.T
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    oi = len(names); names.append(o.name)
    tl = np.array([lt.loops[:] for lt in me.loop_triangles], np.int32).reshape(-1, 3)
    tm = np.array([lt.material_index for lt in me.loop_triangles], np.int32)
    for mi, mn in enumerate(mats):
        if mn not in acc:
            continue
        sel = tl[tm == mi]
        if not len(sel):
            continue
        a = acc[mn]
        a[0].append(uv[sel]); a[1].append(P[lv[sel]]); a[2].append(N[sel]); a[3].append(np.full(len(sel), oi, np.int32))
out = {}
for m, (u, p, n, oo) in acc.items():
    if not u:
        continue
    out[m + '_uv'] = np.concatenate(u).astype(np.float32)
    out[m + '_p'] = np.concatenate(p).astype(np.float32)
    out[m + '_n'] = np.concatenate(n).astype(np.float32)
    out[m + '_o'] = np.concatenate(oo)
    print(m, len(out[m + '_uv']), 'tris', 'z range %.2f .. %.2f' % (out[m + '_p'][..., 2].min(), out[m + '_p'][..., 2].max()))
out['objects'] = np.array(names)
np.savez_compressed('/home/claude/plane/v12r2/work/geotris_v11.npz', **out)
