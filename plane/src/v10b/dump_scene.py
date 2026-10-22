"""Dump the rendered triangles of a blend (world space, evaluated) for the visibility comparison:
python3 dump_scene.py <blend> <out.npz>
Hidden for the comparison (as in the comparison renders): removable cargo / ladder / key, prop blur & disc,
glass triangles (any material with 'Glass' in the name: see-through)."""
import bpy, sys, os, numpy as np
blend, out = sys.argv[1], sys.argv[2]
HIDE = ('src_Case', 'src_PlaneKey', 'src_StepLadder', 'Ladder_RearLegs', 'PropBlur', 'PropDisc')
FBX = blend.lower().endswith('.fbx')
HIDE = HIDE + tuple(x for x in os.environ.get('DUMP_HIDE', '').split(',') if x)
if FBX:          # what Unity gets: the exported FBX re-imported (LOD1/2, shadow copies, colliders, zones left out)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=blend)
    HIDE = HIDE + ('COL_', 'IV_', 'SM_Case', 'SM_StepLadder', 'SM_PlaneKey')
else:
    bpy.ops.wm.open_mainfile(filepath=blend)
dg = bpy.context.evaluated_depsgraph_get()
P, N, UV, OB, MA = [], [], [], [], []
names, mats = [], []
mat_id = {}
skipped = []
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    if o.hide_render or o.name.startswith(HIDE) or o.display_type in ('WIRE', 'BOUNDS') or \
            (FBX and o.name.endswith(('_LOD1', '_LOD2', '_Shadow'))):
        skipped.append(o.name)
        continue
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    lt = me.loop_triangles
    T = len(lt)
    if T == 0:
        ev.to_mesh_clear()
        continue
    vi = np.empty(T * 3, np.int32); lt.foreach_get('vertices', vi)
    li = np.empty(T * 3, np.int32); lt.foreach_get('loops', li)
    mi = np.empty(T, np.int32); lt.foreach_get('material_index', mi)
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    cn = np.empty(len(me.loops) * 3); me.corner_normals.foreach_get('vector', cn); cn = cn.reshape(-1, 3)
    uv = np.zeros(len(me.loops) * 2)
    if me.uv_layers:
        me.uv_layers[0].data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2)
    M = np.array(o.matrix_world)
    R = M[:3, :3]
    Rn = np.linalg.inv(R).T
    pw = co @ R.T + M[:3, 3]
    nw = cn @ Rn.T
    nw /= np.maximum(np.linalg.norm(nw, axis=1), 1e-20)[:, None]
    mnames = [(m.name.rsplit('.', 1)[0] if m else '') for m in me.materials] or ['']
    keep = np.array(['Glass' not in mnames[min(m, len(mnames) - 1)] for m in mi])
    oid = len(names)
    names.append(o.name)
    for k, mn in enumerate(mnames):
        if mn not in mat_id:
            mat_id[mn] = len(mat_id)
    mglob = np.array([mat_id[mnames[min(m, len(mnames) - 1)]] for m in mi])
    P.append(pw[vi].reshape(T, 3, 3)[keep]); N.append(nw[li].reshape(T, 3, 3)[keep]); UV.append(uv[li].reshape(T, 3, 2)[keep])
    OB.append(np.full(keep.sum(), oid, np.int32)); MA.append(mglob[keep].astype(np.int32))
    ev.to_mesh_clear()
P = np.concatenate(P); N = np.concatenate(N); UV = np.concatenate(UV); OB = np.concatenate(OB); MA = np.concatenate(MA)
np.savez_compressed(out, P=P.astype(np.float32), N=N.astype(np.float32), UV=UV.astype(np.float32), OB=OB, MA=MA,
                    names=np.array(names), mats=np.array(sorted(mat_id, key=mat_id.get)))
print('dumped', out, 'tris', len(P), 'objects', len(names), 'skipped', len(skipped), 'bounds', P.reshape(-1, 3).min(0), P.reshape(-1, 3).max(0))
