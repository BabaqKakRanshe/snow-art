"""LOD pop check: for v9 and v10 (FBX as imported), the exterior seen from 50 m (LOD0 -> LOD1 switch, Unity 60 deg
vertical fov, 1920x1080) and 155 m (LOD1 -> LOD2); fraction of the plane's pixels that change at the switch:
silhouette (hit / miss), normal > 25 deg, material. python3 lodcheck.py"""
import bpy, json, sys, os, math, numpy as np
D = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/opt/vis2/'
sys.argv = [sys.argv[0], 'x', 'x', 'x']
exec(open(D + 'viscmp.py').read().split('A = Scene(A_path)')[0])
from embreex import rtcore_scene as rtcs
from embreex.mesh_construction import TriangleMesh


def dump_level(fbx, lodjson, level):
    lj = json.load(open(lodjson))
    g = next(x for x in lj['groups'] if x['name'] == 'Exterior')
    keep = set(g['levels'][level]['renderers']) - {p['renderer'] for p in lj.get('shadowProxies', [])}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx)
    dg = bpy.context.evaluated_depsgraph_get()
    P, N, MA, mats = [], [], [], {}
    for o in bpy.data.objects:
        if o.type != 'MESH' or o.name.split('.')[0] not in keep:
            continue
        me = o.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        T = len(me.loop_triangles)
        if T == 0:
            continue
        vi = np.empty(T * 3, np.int32); me.loop_triangles.foreach_get('vertices', vi)
        li = np.empty(T * 3, np.int32); me.loop_triangles.foreach_get('loops', li)
        mi = np.empty(T, np.int32); me.loop_triangles.foreach_get('material_index', mi)
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        cn = np.empty(len(me.loops) * 3); me.corner_normals.foreach_get('vector', cn); cn = cn.reshape(-1, 3)
        M = np.array(o.matrix_world); R = M[:3, :3]
        pw = co @ R.T + M[:3, 3]; nw = cn @ np.linalg.inv(R); nw /= np.linalg.norm(nw, axis=1)[:, None]
        mn = [(m.name.split('.')[0] if m else '') for m in me.materials] or ['']
        glass = np.array(['Glass' in mn[min(k, len(mn) - 1)] for k in mi])
        for k in set(mn):
            mats.setdefault(k, len(mats))
        P.append(pw[vi].reshape(T, 3, 3)[~glass]); N.append(nw[li].reshape(T, 3, 3)[~glass])
        MA.append(np.array([mats[mn[min(k, len(mn) - 1)]] for k in mi])[~glass])
    return np.concatenate(P), np.concatenate(N), np.concatenate(MA), len(keep)


class S2:
    def __init__(self, P, N, MA):
        self.P, self.N, self.MA = P, N, MA
        self.sc = rtcs.EmbreeScene(); TriangleMesh(self.sc, P.astype(np.float32))

    def hit(self, o, d):
        r = self.sc.run(o.astype(np.float32), d.astype(np.float32), output=1)
        p = r['primID'].astype(np.int64); ok = p >= 0; pp = np.where(ok, p, 0)
        u, v = r['u'], r['v']
        b = np.stack([1 - u - v, u, v], 1)
        n = np.einsum('nk,nkj->nj', b, self.N[pp]); n /= np.maximum(np.linalg.norm(n, axis=1), 1e-20)[:, None]
        return ok, n, self.MA[pp]


res = {}
for tag, fbx, lj in (('v9', '/home/claude/plane/export/unity_v9/Assets/UtilityPlane/Models/UtilityPlane.fbx',
                      '/home/claude/plane/export/unity_v9/Assets/UtilityPlane/Data/lod.json'),
                     ('v10', '/home/claude/plane/export/unity_v10/Assets/UtilityPlane/Models/UtilityPlane.fbx',
                      '/home/claude/plane/export/unity_v10/Assets/UtilityPlane/Data/lod.json')):
    L = [S2(*dump_level(fbx, lj, l)[:3]) for l in (0, 1, 2)]
    hf = math.degrees(2 * math.atan(math.tan(math.radians(30)) * 16 / 9))
    for (la, lb, dist) in ((0, 1, 50.0), (1, 2, 155.0), (0, 2, 155.0)):
        sil = nrm = tot = 0
        for h in (1.0, 6.0):
            for i in range(12):
                a = 2 * math.pi * i / 12
                c = np.array([0.0, 0.0, 1.4])
                e = c + np.array([dist * math.sin(a), dist * math.cos(a), 0]); e[2] = h
                o, d = rays_persp(tuple(e), tuple(c - e), (0, 0, 1), hf, 1920, 1080)
                oa, na, ma = L[la].hit(o, d)
                ob, nb, mb = L[lb].hit(o, d)
                plane = oa | ob
                tot += plane.sum()
                sil += (oa != ob).sum()
                both = oa & ob
                nrm += (both & (np.degrees(np.arccos(np.clip((na * nb).sum(1), -1, 1))) > 25)).sum()
        res[(tag, la, lb)] = (tot, sil / tot, nrm / tot)
        print(f'{tag} LOD{la}->LOD{lb} at {dist:.0f} m: plane px {tot}, silhouette changes {sil/tot*100:.2f} %, normal >25deg {nrm/tot*100:.2f} %', flush=True)
