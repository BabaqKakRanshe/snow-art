"""which faces of the road kit lie coplanar and overlapping (before the separation)"""
import sys
sys.path.insert(0, '/home/claude/uaz')
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
import road_tex as RT
import gen_kit as K
import road_kit as RK
import bld_common as BC
import collections
RK.build_road()
_IJ = BC.is_joined
BC.is_joined = lambda a: _IJ(a) or a in ('chainlink', 'barbed')
BC.prepare_kbs({RK.Z_SCLAMP, RK.Z_STEEL, RK.Z_DSTEEL, RK.Z_GHINGE, RK.Z_CHAIN, RK.Z_TBRANCH, RK.Z_TBREAK, RK.Z_SAWDUST,
                RK.Z_DRAG, RK.Z_SOIL})
names = [n for n in K.KBS if not BC.is_joined(K.ATLAS[n])]
# replicate the adjacency search
from mathutils import Vector
Fs, buckets = [], {}
for name in names:
    k = K.KBS[name]
    k.bm.normal_update()
    k.bm.faces.ensure_lookup_table()
    for f in k.bm.faces:
        a = f.calc_area()
        if a < 1e-6:
            continue
        nn = f.normal.copy()
        pts = [v.co.copy() for v in f.verts]
        d = nn.dot(f.calc_center_median())
        Fs.append((name, f.index, nn, d, pts, int(round(f[k.zl])), a))
        key = (round(nn.x * 100), round(nn.y * 100), round(nn.z * 100), round(d * 1000))
        buckets.setdefault(key, []).append(len(Fs) - 1)
cnt = collections.Counter()
ex = {}
for key, ids in buckets.items():
    cand = list(ids)
    for dk in (-1, 1):
        cand += buckets.get((key[0], key[1], key[2], key[3] + dk), [])
    for i in ids:
        a = Fs[i]
        for j in cand:
            if j <= i:
                continue
            b = Fs[j]
            if a[2].dot(b[2]) < 0.999 or abs(a[3] - b[3]) > 0.001:
                continue
            inter = BC._clip(BC._to2d(a[4], a[2]), BC._to2d(b[4], a[2]))
            if len(inter) >= 3:
                ar = abs(sum(inter[q][0] * inter[(q + 1) % len(inter)][1] - inter[(q + 1) % len(inter)][0] * inter[q][1] for q in range(len(inter)))) / 2
                if ar > 1e-5:
                    kk = (a[0], a[5], b[5])
                    cnt[kk] += 1
                    ex.setdefault(kk, (tuple(round(v, 3) for v in a[4][0]), tuple(round(v, 3) for v in a[2])))
for kk, v in cnt.most_common(40):
    print(v, kk, ex[kk])
