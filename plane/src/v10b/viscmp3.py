"""3-way view comparison: v10 (B) against two references of v9 - the v9 FBX as imported (A1, what Unity got) and the
v9 model itself (A2). A pixel is a regression only if B differs from both: differences against the FBX alone come from
how the v9 FBX turned its quads into triangles; differences against the model alone come from the export's own
conversions (display materials, lens UVs, items in their own FBX), which v9 and v10 share.
NOOBJ=1 style object test off (names differ between model and FBX). python3 viscmp3.py A1.npz A2.npz B.npz out_dir"""
import numpy as np, json, sys, os
A1p, A2p, Bp, OUT = sys.argv[1:5]
sys.argv = [sys.argv[0], 'x', 'x', 'x']
os.environ['NOOBJ'] = '1'
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'viscmp.py')).read().split('A = Scene(A_path)')[0]
exec(src)
from scipy import ndimage
os.makedirs(OUT, exist_ok=True)
A1, A2, B = Scene(A1p), Scene(A2p), Scene(Bp)


def mism(SA, SB, o, d, cache):
    if id(SA) not in cache:
        cache[id(SA)] = SA.attrs(*SA.cast(o, d)[:3])
    if id(SB) not in cache:
        cache[id(SB)] = SB.attrs(*SB.cast(o, d)[:3])
    okA, posA, nA, uvA, obA, maA = cache[id(SA)]
    okB, posB, nB, uvB, obB, maB = cache[id(SB)]
    both = okA & okB
    sep = np.abs(((posA - posB) * nA).sum(1))
    ang = np.degrees(np.arccos(np.clip((nA * nB).sum(1), -1, 1)))
    uvd = np.linalg.norm(uvA - uvB, axis=1) * SA.res[maA]
    diff_mat = np.array(SA.mats)[maA] != np.array(SB.mats)[maB]
    return (okA != okB) | (both & (diff_mat | (sep > SEP) | (ang > NANG) | (uvd > UVTX)))


tot = bad_tot = 0
rep = []
for name, eye, fwd, up, fov, W, H in default_views():
    o, d = rays_persp(eye, fwd, up, fov, W, H)
    cache = {}
    m1 = mism(A1, B, o, d, cache).reshape(H, W)
    m2 = mism(A2, B, o, d, cache).reshape(H, W)
    reg = m1 & m2
    er = ndimage.binary_erosion(reg, structure=np.ones((3, 3)))
    lab, n = ndimage.label(ndimage.binary_dilation(er, structure=np.ones((3, 3))) & reg)
    okB, posB, nB, uvB, obB, maB = cache[id(B)]
    comps = []
    for ci in range(1, n + 1):
        ys, xs = np.nonzero(lab == ci)
        if len(ys) < 6:
            continue
        flat = ys * W + xs
        names = {}
        for f_ in flat:
            if okB[f_]:
                nm = B.names[obB[f_]]
                names[nm] = names.get(nm, 0) + 1
        k = flat[len(flat) // 2]
        comps.append(dict(px=int(len(ys)), xy=[int(xs.mean()), int(ys.mean())], B=sorted(names.items(), key=lambda x: -x[1])[:3],
                          posB=[round(float(x), 3) for x in posB[k]]))
    px = sum(c['px'] for c in comps)
    tot += W * H; bad_tot += px
    rep.append(dict(view=name, regress_px=px, comps=comps, raw_fbx=float(m1.mean()), raw_model=float(m2.mean())))
    print(f'{name:16s} vs v9 FBX {m1.mean()*100:5.2f}%  vs v9 model {m2.mean()*100:5.2f}%  both {len(comps)} comps {px} px' +
          (f'  top {comps[0]}' if comps else ''), flush=True)
json.dump(rep, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
print('TOTAL regression px', bad_tot, 'of', tot)
