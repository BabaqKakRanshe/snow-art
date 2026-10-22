# ================================================================== v6: the gauge atlas is 4096 x 4096 now. Every builder wrote v5-space
# UVs (u = px/4096, v = 1 - py/2048, negative v = new bottom half); remap them once: v' = 0.5 + 0.5 v (= 1 - py/4096)
_n = 0
for _ob in bpy.data.objects:
    if _ob.type != 'MESH' or not _ob.data.uv_layers:
        continue
    _names = [m.name if m else '' for m in _ob.data.materials]
    _idx = {i for i, n in enumerate(_names) if n in ('src_CP_Gauges', 'src_CP_Annun')}
    if not _idx:
        continue
    _uv = _ob.data.uv_layers[0].data
    for _p in _ob.data.polygons:
        if _p.material_index in _idx:
            _n += 1
            for _li in _p.loop_indices:
                _u, _v = _uv[_li].uv
                assert -1.0001 <= _v <= 1.0001 and -0.0001 <= _u <= 1.0001, (_ob.name, _u, _v)
                _uv[_li].uv = (_u, 0.5 + 0.5 * _v)
print('v6 gauge-atlas faces remapped to 4096 x 4096:', _n)
# ================================================================== sockets + summary
SOCKETS = {'Socket_PilotEye': LY.PILOT_EYE, 'Socket_CopilotEye': LY.COPILOT_EYE}
for i, p in enumerate(sorted(TIEDOWNS, key=lambda q: (q[1], -q[0])), 1):     # front to back, left to right
    SOCKETS[f'Socket_TieDown_{i:02d}'] = tuple(round(v, 4) for v in p)
_dome = [v for v in bpy.data.objects['CP_Overhead'].data.vertices]
SOCKETS['_dome_z'] = (0.0, 0.0, round(min((bpy.data.objects['CP_Overhead'].matrix_world @ v.co).z for v in _dome), 4))
json.dump(dict(rig=RIG, static=STATIC, sockets={k: list(v) for k, v in SOCKETS.items()}),
          open(os.path.join(HERE, 'out', 'cockpit_rig.json'), 'w'), indent=1)
tris = 0
dg = bpy.context.evaluated_depsgraph_get()
per = {}
for ob in CP.objects:
    if ob.type != 'MESH':
        continue
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    tris += len(me.loop_triangles)
    per[ob.name] = len(me.loop_triangles)
    ob.evaluated_get(dg).to_mesh_clear()
for k, v in sorted(per.items(), key=lambda kv: -kv[1])[:25]:
    print(f'  {k:28s} {v}')
print('COCKPIT objects', len(CP.objects), 'tris', tris, 'moving parts', len(RIG))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v2.blend'))
print('saved')
