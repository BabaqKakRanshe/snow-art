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
