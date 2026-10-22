"""area-weighted centroid and coarse occupancy of each item: Update 3's FBX vs the new blend"""
import bpy, sys, os, json
import numpy as np
blend, u3dir = sys.argv[sys.argv.index('--') + 1:]


def samples(objs):
    pts, ws = [], []
    for o in objs:
        me = o.data
        me.calc_loop_triangles()
        for t in me.loop_triangles:
            vs = [o.matrix_world @ me.vertices[i].co for i in t.vertices]
            a = t.area * (o.matrix_world.to_3x3().determinant() ** (2 / 3))
            c = (vs[0] + vs[1] + vs[2]) / 3
            pts.append(tuple(c)); ws.append(a)
    return np.array(pts), np.array(ws)


bpy.ops.wm.open_mainfile(filepath=blend)
new = {}
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.startswith('Item_') and o.parent is None:
        new[o.name] = samples([o])
res = {}
for n, (pn, wn) in sorted(new.items()):
    fp = os.path.join(u3dir, n + '.fbx')
    if not os.path.exists(fp):
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fp)
    pu, wu = samples([o for o in bpy.data.objects if o.type == 'MESH'])
    lo = np.minimum(pu.min(0), pn.min(0)); hi = np.maximum(pu.max(0), pn.max(0))
    diag = np.linalg.norm(hi - lo)
    cu = (pu * wu[:, None]).sum(0) / wu.sum(); cn = (pn * wn[:, None]).sum(0) / wn.sum()
    def occ(p):
        g = np.clip(((p - lo) / np.maximum(hi - lo, 1e-6) * 6).astype(int), 0, 5)
        return set(map(tuple, g))
    ou, on = occ(pu), occ(pn)
    iou = len(ou & on) / max(1, len(ou | on))
    res[n] = dict(dc=round(float(np.linalg.norm(cn - cu) / diag), 3), iou=round(iou, 2),
                  cu=np.round(cu, 3).tolist(), cn=np.round(cn, 3).tolist())
bad = {n: r for n, r in res.items() if r['dc'] > 0.12 or r['iou'] < 0.35}
print('checked', len(res))
for n, r in sorted(res.items(), key=lambda kv: -kv[1]['dc']):
    flag = ' <<' if n in bad else ''
    print(n, r['dc'], r['iou'], r['cu'], r['cn'], flag)
