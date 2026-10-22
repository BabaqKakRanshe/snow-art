"""Wipe map of the windscreen for the Unity glass shader: Textures/T_Van_WipeMap.png in the UV0 space of lob (the same
space as T_Van_Frost / T_Van_Snow). R = the angle of Wiper_L (0..100 deg, / 100) at which its blade first passes over
the texel, G = the same for Wiper_R, 255 = never wiped. The blade (the rubber line from the inner end to the tip of the
arm) is turned about the wiper's hinge axis in 0.25 deg steps and laid on the glass (closest point on lob, within 3 cm).
A texel counts as wiped when the blade line passes within 1.2 cm of it.
python3 -I van_wipe_map.py -- <out_png> [sheet_png]"""
import bpy, sys, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
from PIL import Image

W, H = 256, 128
a = sys.argv[sys.argv.index('--') + 1:]
OUT = a[0]
SHEET = a[1] if len(a) > 1 else None
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/van3.blend')
C = json.load(open('/home/claude/uaz/out/van3_contract.json'))
lob = bpy.data.objects['lob']
me = lob.data
mw = lob.matrix_world
verts = [mw @ v.co for v in me.vertices]
uvl = me.uv_layers['PSX'].data
tris, tri_uv = [], []
for p in me.polygons:
    li = list(p.loop_indices)
    for k in range(1, len(li) - 1):                              # fan (lob faces are triangles / quads)
        ids = [li[0], li[k], li[k + 1]]
        tris.append([me.loops[i].vertex_index for i in ids])
        tri_uv.append([Vector((uvl[i].uv[0], uvl[i].uv[1], 0.0)) for i in ids])
bvh = BVHTree.FromPolygons(verts, tris)


def uv_at(q):
    loc, nrm, idx, dist = bvh.find_nearest(q)
    if loc is None:
        return None, 1e9
    t = tris[idx]
    uv = barycentric_transform(loc, verts[t[0]], verts[t[1]], verts[t[2]], *tri_uv[idx])
    return (uv.x, uv.y), dist


out = np.full((H, W, 2), 255, np.uint8)
best = np.full((H, W, 2), 1e9)
yy, xx = np.mgrid[0:H, 0:W]
# metres per uv unit (lob spans about 1.48 m in u, 0.5 m in v): radius in texels for 1.2 cm
us = np.array([[c[0] for c in tri_uv[i]] for i in range(len(tris))])
umin = min(min(c.x for c in t) for t in tri_uv)
umax = max(max(c.x for c in t) for t in tri_uv)
ymin = min(v.y for v in verts)
ymax = max(v.y for v in verts)
m_per_u = (ymax - ymin) / max(umax - umin, 1e-6)
R_TEX = max(1.0, 0.012 / m_per_u * W)
stats = {}
for ch, wn in enumerate(('Wiper_L', 'Wiper_R')):
    o = bpy.data.objects[wn]
    piv = Vector(C['parts'][wn]['pivot'])
    ax = Vector(C['parts'][wn]['axis']).normalized()
    vs = [o.matrix_world @ v.co for v in o.data.vertices]

    def rad(v):
        d = v - piv
        return (d - ax * d.dot(ax)).length
    inner = [v for v in vs if 0.15 < rad(v) < 0.19]
    outer = [v for v in vs if rad(v) > 0.44]
    # blade line: from the inner end (r ~ 0.17) to the tip (r ~ 0.45), the points nearest the glass
    pa = min(inner, key=lambda v: uv_at(v)[1])
    pb = min(outer, key=lambda v: uv_at(v)[1])
    n_hit = 0
    for step in range(0, 401):
        th = step * 0.25
        R = Matrix.Rotation(math.radians(th), 3, ax)
        A = piv + R @ (pa - piv)
        B = piv + R @ (pb - piv)
        for k in range(61):
            q = A.lerp(B, k / 60)
            uv, dist = uv_at(q)
            if uv is None or dist > 0.03:
                continue
            cx, cy = uv[0] * W, uv[1] * H
            x0, x1 = int(max(0, cx - R_TEX - 1)), int(min(W - 1, cx + R_TEX + 1))
            y0, y1 = int(max(0, cy - R_TEX - 1)), int(min(H - 1, cy + R_TEX + 1))
            sub_x, sub_y = xx[y0:y1 + 1, x0:x1 + 1] + 0.5, yy[y0:y1 + 1, x0:x1 + 1] + 0.5
            hit = (sub_x - cx) ** 2 + (sub_y - cy) ** 2 <= R_TEX ** 2
            blk = best[y0:y1 + 1, x0:x1 + 1, ch]
            upd = hit & (th < blk)
            blk[upd] = th
            n_hit += int(upd.sum())
    sel = best[..., ch] < 1e8
    out[..., ch][sel] = np.round(best[..., ch][sel] / 100.0 * 254).astype(np.uint8)
    stats[wn] = dict(texels=int(sel.sum()), share=round(float(sel.mean()), 3), inner=list(map(lambda x: round(x, 3), pa)),
                     tip=list(map(lambda x: round(x, 3), pb)))
rgba = np.zeros((H, W, 4), np.uint8)
rgba[..., 0] = out[..., 0]
rgba[..., 1] = out[..., 1]
rgba[..., 2] = 255
rgba[..., 3] = 255
# texture rows: v = 0 at the bottom of the image in Unity / Blender UV space -> flip for PNG (row 0 = top)
Image.fromarray(rgba[::-1]).save(OUT)
print('[wipe] texel radius', round(R_TEX, 2), 'm per u', round(m_per_u, 3), stats)
if SHEET:
    vis = np.zeros((H, W, 3), np.uint8)
    for ch, col in ((0, (255, 80, 40)), (1, (40, 160, 255))):
        sel = out[..., ch] < 255
        shade = 1.0 - out[..., ch].astype(float) / 255.0 * 0.6
        for c in range(3):
            vis[..., c] = np.where(sel, np.maximum(vis[..., c], (col[c] * shade).astype(np.uint8)), vis[..., c])
    Image.fromarray(vis[::-1]).resize((W * 3, H * 3), Image.NEAREST).save(SHEET)
