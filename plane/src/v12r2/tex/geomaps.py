"""v12r2: per-texel world position / shading normal / object id of the interior atlases, rasterised from
work/geotris_v11.npz (the triangle that covers each texel centre; texels an island only grazes take the nearest
rasterised texel of the same island later, in psx_interior2.py).
python3 geomaps.py <res> -> work/geomaps_<res>.npz : <Atlas>_tri (res,res) int32 (-1 = empty), _p (res,res,3), _n, _o"""
import sys
import numpy as np
from PIL import Image, ImageDraw

R = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
G = np.load('/home/claude/plane/v12r2/work/geotris_v11.npz')
out = {}
for atlas in ('Cockpit', 'Interior', 'Floor', 'Seats', 'Fittings'):
    m = 'M_' + atlas
    uv, P, N, O = G[m + '_uv'], G[m + '_p'], G[m + '_n'], G[m + '_o']
    im = Image.new('I', (R, R), -1)
    dr = ImageDraw.Draw(im)
    px = np.stack([uv[..., 0] * R, (1 - uv[..., 1]) * R], -1)          # image coords (x right, y down)
    for i, t in enumerate(px):
        dr.polygon([tuple(v) for v in t], fill=i, outline=i)
    tri = np.asarray(im, np.int32)
    yy, xx = np.nonzero(tri >= 0)
    ti = tri[yy, xx]
    c = np.stack([xx + 0.5, yy + 0.5], -1)
    a, b, d = px[ti, 0], px[ti, 1], px[ti, 2]
    v0, v1, v2 = b - a, d - a, c - a
    d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    ok = np.abs(den) > 1e-12
    w1 = np.where(ok, (d11 * d20 - d01 * d21) / np.where(ok, den, 1), 1 / 3)
    w2 = np.where(ok, (d00 * d21 - d01 * d20) / np.where(ok, den, 1), 1 / 3)
    w1, w2 = np.clip(w1, 0, 1), np.clip(w2, 0, 1)
    s = w1 + w2
    w1, w2 = np.where(s > 1, w1 / s, w1), np.where(s > 1, w2 / s, w2)
    w0 = 1 - w1 - w2
    p = P[ti, 0] * w0[:, None] + P[ti, 1] * w1[:, None] + P[ti, 2] * w2[:, None]
    n = N[ti, 0] * w0[:, None] + N[ti, 1] * w1[:, None] + N[ti, 2] * w2[:, None]
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    Pm = np.zeros((R, R, 3), np.float32); Nm = np.zeros((R, R, 3), np.float32); Om = np.full((R, R), -1, np.int32)
    Pm[yy, xx] = p; Nm[yy, xx] = n; Om[yy, xx] = O[ti]
    out[atlas + '_tri'] = tri; out[atlas + '_p'] = Pm; out[atlas + '_n'] = Nm; out[atlas + '_o'] = Om
    # UV overlap check: sum of triangle UV areas vs the area actually covered
    e1, e2 = px[:, 1] - px[:, 0], px[:, 2] - px[:, 0]
    area = np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]).sum() / 2
    print(atlas, 'covered %.3f' % (tri >= 0).mean(), 'sum tri area / covered %.3f' % (area / max((tri >= 0).sum(), 1)), flush=True)
np.savez_compressed('/home/claude/plane/v12r2/work/geomaps_%d.npz' % R, **out)
