"""Visibility comparison of two scene dumps (dump_scene.py) with Embree ray casting, back faces culled (opaque Unity
materials are single-sided). For every view, every pixel: the first front-facing hit in A and in B; a pixel differs when
  - one hits and the other does not, or a different object / material is hit
  - the hits are apart across the surface normal by more than SEP (moved surface, hole, poke-through), or
  - the shading normals differ by more than NANG degrees, or the UVs by more than UVTX texels of that material.
Mismatch masks are eroded (3x3) to drop the 1-2 px lines that any edge moved within tolerance leaves, then labelled.
python3 viscmp.py A.npz B.npz out_dir [views.json]"""
import numpy as np, json, sys, os, math
from scipy import ndimage
from embreex import rtcore_scene as rtcs
from embreex.mesh_construction import TriangleMesh

A_path, B_path, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
SEP, NANG, UVTX = 0.006, 15.0, 3.0
RES = {'M_Cockpit': 1024, 'M_Interior': 1024, 'M_Floor': 1024, 'M_Seats': 1024, 'M_Fittings': 1024, 'M_Gauges': 2048,
       'M_Airframe': 512, 'M_Wing': 512, 'M_Details': 512, 'M_Webbing': 512, 'M_GaugeGlass': 512}


class Scene:
    def __init__(self, path):
        d = np.load(path, allow_pickle=False)
        self.P, self.N, self.UV, self.OB, self.MA = d['P'], d['N'], d['UV'], d['OB'], d['MA']
        self.names, self.mats = list(d['names']), list(d['mats'])
        self.sc = rtcs.EmbreeScene()
        TriangleMesh(self.sc, self.P.astype(np.float32))
        e1 = self.P[:, 1] - self.P[:, 0]
        e2 = self.P[:, 2] - self.P[:, 0]
        ng = np.cross(e1, e2)
        self.NG = ng / np.maximum(np.linalg.norm(ng, axis=1), 1e-20)[:, None]
        self.res = np.array([RES.get(m, 512) for m in self.mats])

    def cast(self, o, d):
        """first front-facing hit: (prim id or -1, u, v, t)"""
        n = len(o)
        prim = np.full(n, -1, np.int64)
        U = np.zeros(n, np.float32); V = np.zeros(n, np.float32); T = np.full(n, np.inf)
        org = o.astype(np.float32).copy()
        todo = np.arange(n)
        t_acc = np.zeros(n)
        for it in range(12):
            if len(todo) == 0:
                break
            r = self.sc.run(org[todo], d[todo].astype(np.float32), output=1)
            pid = r['primID'].astype(np.int64)
            hit = pid >= 0
            back = np.zeros(len(todo), bool)
            back[hit] = (self.NG[pid[hit]] * d[todo[hit]]).sum(1) > 0
            if os.environ.get('NOCULL'):
                back[:] = False
            front = hit & ~back
            idx = todo[front]
            prim[idx] = pid[front]; U[idx] = r['u'][front]; V[idx] = r['v'][front]
            T[idx] = t_acc[idx] + r['tfar'][front]
            nxt = hit & back                     # pass through back faces
            adv = r['tfar'][nxt] + 1e-5
            t_acc[todo[nxt]] += adv
            org[todo[nxt]] += d[todo[nxt]].astype(np.float32) * adv[:, None].astype(np.float32)
            todo = todo[nxt]
        return prim, U, V, T

    def attrs(self, prim, U, V):
        ok = prim >= 0
        p = np.where(ok, prim, 0)
        b = np.stack([1 - U - V, U, V], 1)
        pos = np.einsum('nk,nkj->nj', b, self.P[p])
        n = np.einsum('nk,nkj->nj', b, self.N[p])
        n /= np.maximum(np.linalg.norm(n, axis=1), 1e-20)[:, None]
        uv = np.einsum('nk,nkj->nj', b, self.UV[p])
        return ok, pos, n, uv, self.OB[p], self.MA[p]


def rays_persp(eye, fwd, up, fov_deg, W, H):
    f = np.array(fwd, float); f /= np.linalg.norm(f)
    r = np.cross(f, up); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    t = math.tan(math.radians(fov_deg) / 2)
    xs = (np.arange(W) + 0.5) / W * 2 - 1
    ys = 1 - (np.arange(H) + 0.5) / H * 2
    X, Y = np.meshgrid(xs * t, ys * t * H / W)
    d = f[None, None, :] + X[..., None] * r + Y[..., None] * u
    d /= np.linalg.norm(d, axis=2, keepdims=True)
    return np.repeat(np.array(eye, float)[None, :], W * H, 0), d.reshape(-1, 3)


def cube_views(name, eye, size):
    dirs = {'f': ((0, -1, 0), (0, 0, 1)), 'b': ((0, 1, 0), (0, 0, 1)), 'l': ((1, 0, 0), (0, 0, 1)),
            'r': ((-1, 0, 0), (0, 0, 1)), 'u': ((0, 0, 1), (0, -1, 0)), 'd': ((0, 0, -1), (0, -1, 0))}
    return [(f'{name}_{k}', eye, fw, up, 90.0, size, size) for k, (fw, up) in dirs.items()]


def default_views():
    V = []
    S = 512
    interior = {'pilotP': (0.33, -2.24, 2.22), 'pilotC': (-0.33, -2.24, 2.22), 'leanP': (0.22, -2.10, 2.12),
                'leanC': (-0.22, -2.10, 2.12), 'bayF_st': (0.0, -1.35, 2.05), 'bayM_st': (0.0, -0.4, 2.05),
                'bayA_st': (0.0, 0.85, 2.05), 'bayF_cr': (0.0, -1.3, 1.45), 'bayM_cr': (0.1, -0.3, 1.45),
                'bayA_cr': (-0.1, 0.9, 1.45), 'paxL1': (0.42, -1.25, 1.85), 'paxR2': (-0.42, 0.75, 1.85),
                'paxR1': (-0.42, -1.25, 1.85), 'paxL2': (0.42, 0.75, 1.85), 'bayL_st': (0.4, -0.2, 2.0),
                'bayR_st': (-0.4, 0.3, 2.0)}
    for k, e in interior.items():
        V += cube_views(k, e, S)
    c = np.array([0.0, 0.0, 1.4])
    for h, z in (('lo', 0.35), ('mid', 1.8), ('hi', 4.5)):
        for i in range(12):
            a = 2 * math.pi * i / 12
            e = c + np.array([7.5 * math.sin(a), 7.5 * math.cos(a), 0]); e[2] = z
            V.append((f'ext_{h}{i:02d}', tuple(e), tuple(c - e), (0, 0, 1), 70.0, 900, 600))
    close = {'wheelL': ((2.7, -4.4, 0.85), (1.25, -2.85, 0.40)), 'wheelR': ((-2.7, -4.4, 0.85), (-1.25, -2.85, 0.40)),
             'nose': ((1.6, -6.4, 1.6), (0.0, -4.3, 1.4)), 'tailw': ((1.2, 6.2, 0.6), (0.0, 4.6, 0.3)),
             'doorL': ((1.75, -2.35, 2.05), (0.0, -2.45, 1.65)), 'doorR': ((-1.75, -2.35, 2.05), (0.0, -2.45, 1.65)),
             'cargoL': ((1.9, -0.2, 1.7), (0.0, -0.2, 1.6)), 'cargoR': ((-1.9, -0.2, 1.7), (0.0, -0.2, 1.6)),
             'under': ((0.8, -1.0, -0.05), (0.0, -1.0, 1.0)), 'strutL': ((3.2, -2.0, 0.9), (1.6, -1.4, 1.8))}
    for k, (e, t) in close.items():
        V.append((f'close_{k}', e, tuple(np.array(t) - np.array(e)), (0, 0, 1), 55.0, 900, 600))
    return V


A = Scene(A_path)
B = Scene(B_path)
views = default_views() if len(sys.argv) < 5 else [tuple(v) for v in json.load(open(sys.argv[4]))]
report = []
tot_px = tot_bad = 0
for name, eye, fwd, up, fov, W, H in views:
    o, d = rays_persp(eye, fwd, up, fov, W, H)
    pa, ua, va, ta = A.cast(o, d)
    pb, ub, vb, tb = B.cast(o, d)
    okA, posA, nA, uvA, obA, maA = A.attrs(pa, ua, va)
    okB, posB, nB, uvB, obB, maB = B.attrs(pb, ub, vb)
    both = okA & okB
    sep = np.abs(((posA - posB) * nA).sum(1))
    ang = np.degrees(np.arccos(np.clip((nA * nB).sum(1), -1, 1)))
    uvd = np.linalg.norm(uvA - uvB, axis=1) * A.res[maA]
    nameA = np.array(A.names)[obA]; nameB = np.array(B.names)[obB]
    diff_obj = (nameA != nameB) & (not os.environ.get('NOOBJ'))
    diff_mat = np.array(A.mats)[maA] != np.array(B.mats)[maB]
    bad = (okA != okB) | (both & (diff_obj | diff_mat | (sep > SEP) | (ang > NANG) | (uvd > UVTX)))
    m = bad.reshape(H, W)
    er = ndimage.binary_erosion(m, structure=np.ones((3, 3)))
    lab, nlab = ndimage.label(ndimage.binary_dilation(er, structure=np.ones((3, 3))) & m)
    comps = []
    for ci in range(1, nlab + 1):
        ys, xs = np.nonzero(lab == ci)
        if len(ys) < 6:
            continue
        k = ys[len(ys) // 2] * W + xs[len(xs) // 2]
        flat = ys * W + xs
        why = []
        for cond, tag in ((okA[flat] != okB[flat], 'hit/miss'), (diff_obj[flat] & both[flat], 'object'),
                          (diff_mat[flat] & both[flat], 'material'), ((sep[flat] > SEP) & both[flat], 'sep'),
                          ((ang[flat] > NANG) & both[flat], 'normal'), ((uvd[flat] > UVTX) & both[flat], 'uv')):
            if cond.mean() > 0.2:
                why.append(f'{tag} {cond.mean():.0%}')
        objsB = {}
        for f_ in flat:
            if okB[f_]:
                objsB[nameB[f_]] = objsB.get(nameB[f_], 0) + 1
        objsA = {}
        for f_ in flat:
            if okA[f_]:
                objsA[nameA[f_]] = objsA.get(nameA[f_], 0) + 1
        comps.append(dict(px=int(len(ys)), xy=[int(xs.mean()), int(ys.mean())],
                          posA=[round(float(x), 3) for x in posA[k]], posB=[round(float(x), 3) for x in posB[k]],
                          A=sorted(objsA.items(), key=lambda x: -x[1])[:3], B=sorted(objsB.items(), key=lambda x: -x[1])[:3],
                          why=why, primB=sorted(set(int(x) for x in pb[flat] if x >= 0))[:400],
                          primA=sorted(set(int(x) for x in pa[flat] if x >= 0))[:400]))
    comps.sort(key=lambda c: -c['px'])
    nbad = int(sum(c['px'] for c in comps))
    tot_px += W * H; tot_bad += nbad
    report.append(dict(view=name, eye=list(map(float, eye)), raw=float(m.mean()), defect_px=nbad, comps=comps))
    if comps or os.environ.get('SAVE'):
        from PIL import Image
        img = np.zeros((H, W, 3), np.uint8)
        shade = (np.clip(np.abs((nA * d).sum(1)), 0, 1) * 160 + 40).astype(np.uint8).reshape(H, W)
        img[..., 0] = img[..., 1] = img[..., 2] = np.where(okA.reshape(H, W), shade, 255)
        img[m] = (255, 200, 0)
        img[lab > 0] = (255, 0, 0)
        Image.fromarray(img).save(os.path.join(OUT, f'{name}.png'))
    print(f'{name:16s} raw {m.mean()*100:5.2f}%  defects {len(comps):3d} comps {nbad:6d} px' +
          (f'  top: {comps[0]["px"]}px {comps[0]["why"]} A {comps[0]["A"][:1]} B {comps[0]["B"][:1]}' if comps else ''), flush=True)
json.dump(report, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
print('TOTAL defect px', tot_bad, 'of', tot_px, f'({tot_bad / tot_px * 1e6:.1f} ppm)')
