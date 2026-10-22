"""v10 textures: interior atlases (Cockpit, Interior, Floor, Seats, Fittings) -> 1024 px; gauges / displays -> 2048 px.
Interior atlases are filtered with UV-coverage weights (premultiplied Lanczos, colour in linear light, normals
renormalised), so island edges do not pick up the black gutter, then re-dilated 16 px. Everything else is copied.
python3 tex_v10.py"""
import bpy, os, shutil, sys, json
import numpy as np
from PIL import Image, ImageDraw

SRC = '/home/claude/plane/export/unity_v9/Assets/UtilityPlane/Textures'
OUT = '/home/claude/plane/export/unity_v10/Assets/UtilityPlane/Textures'
ATLAS = {'Cockpit': 'M_Cockpit', 'Interior': 'M_Interior', 'Floor': 'M_Floor', 'Seats': 'M_Seats', 'Fittings': 'M_Fittings'}
TARGET = 1024
TWO_K = ('T_Gauges_BC', 'T_Gauges_Emission', 'T_Displays_Emission')
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(SRC):
    shutil.copy2(os.path.join(SRC, f), os.path.join(OUT, f))

# ---------------------------------------------------------------- UV triangles per material (full v9 meshes)
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_v9_final_v9.blend')
uvtris = {m: [] for m in ATLAS.values()}
for o in bpy.data.objects:
    if o.type != 'MESH' or not o.data.uv_layers:
        continue
    me = o.data
    me.calc_loop_triangles()
    uv = me.uv_layers[0].data
    for lt in me.loop_triangles:
        mat = o.material_slots[lt.material_index].material if lt.material_index < len(o.material_slots) else None
        if mat is None or mat.name not in uvtris:
            continue
        uvtris[mat.name].append([tuple(uv[l].uv) for l in lt.loops])


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def resize_f(a, n):
    """float array (H, W) -> (n, n), Lanczos"""
    return np.asarray(Image.fromarray(a.astype(np.float32), 'F').resize((n, n), Image.LANCZOS), np.float32)


def blur3(a):
    p = np.pad(a, 1, mode='edge')
    return sum(p[1 + dy:1 + dy + a.shape[0], 1 + dx:1 + dx + a.shape[1]] for dy in (-1, 0, 1) for dx in (-1, 0, 1))


def dilate(vals, w, steps=16):
    """vals (n, n, C) valid where w > 0: grow valid texels outwards by `steps` texels (neighbour average)."""
    vals = vals.copy()
    w = (w > 0).astype(np.float32)
    for _ in range(steps):
        s = blur3(w)
        grow = (w == 0) & (s > 0)
        if not grow.any():
            break
        for c in range(vals.shape[2]):
            acc = blur3(vals[:, :, c] * w)
            vals[:, :, c][grow] = acc[grow] / s[grow]
        w[grow] = 1.0
    return vals, w


report = {}
for atlas, mat in ATLAS.items():
    base = Image.open(os.path.join(SRC, f'T_{atlas}_BaseColor.png'))
    S = base.size[0]
    mask = Image.new('L', (S, S), 0)
    dr = ImageDraw.Draw(mask)
    for tri in uvtris[mat]:
        pts = [(u * S, (1 - v) * S) for u, v in tri]
        dr.polygon(pts, fill=255, outline=255)
    m = np.asarray(mask, np.float32) / 255.0
    m = np.minimum(1.0, blur3(m))                         # 1 texel conservative growth
    w = resize_f(m, TARGET)
    w = np.clip(w, 0, None)
    valid = w > 0.05
    cov = float(m.mean())
    for kind in ('BaseColor', 'MaskMap', 'Normal'):
        path = os.path.join(SRC, f'T_{atlas}_{kind}.png')
        if not os.path.exists(path):
            continue
        im = Image.open(path)
        mode = im.mode
        a = np.asarray(im.convert('RGBA' if mode == 'RGBA' else 'RGB'), np.float32) / 255.0
        C = a.shape[2]
        if kind == 'BaseColor':
            a = srgb_to_lin(a)
        if kind == 'Normal':
            a = a * 2 - 1
        plain = np.stack([resize_f(a[:, :, c], TARGET) for c in range(C)], 2)       # gutter / background
        pre = np.stack([resize_f(a[:, :, c] * m, TARGET) for c in range(C)], 2)
        vals = np.where(valid[:, :, None], pre / np.maximum(w, 1e-6)[:, :, None], 0)
        vals, grown = dilate(vals, valid.astype(np.float32), 16)
        out = np.where(grown[:, :, None] > 0, vals, plain)
        if kind == 'Normal':
            n = out / np.maximum(np.linalg.norm(out, axis=2, keepdims=True), 1e-6)
            out = n * 0.5 + 0.5
        if kind == 'BaseColor':
            out = lin_to_srgb(out)
        out = np.clip(np.round(out * 255), 0, 255).astype(np.uint8)
        Image.fromarray(out, 'RGBA' if C == 4 else 'RGB').save(os.path.join(OUT, f'T_{atlas}_{kind}.png'), optimize=True)
        report[f'T_{atlas}_{kind}'] = dict(src=S, out=TARGET, coverage=round(cov, 3))
        print(atlas, kind, S, '->', TARGET, 'coverage', round(cov, 3), flush=True)

for n in TWO_K:
    im = Image.open(os.path.join(SRC, n + '.png'))
    a = srgb_to_lin(np.asarray(im.convert('RGB'), np.float32) / 255.0)
    out = np.stack([resize_f(a[:, :, c], 2048) for c in range(3)], 2)
    out = np.clip(np.round(lin_to_srgb(out) * 255), 0, 255).astype(np.uint8)
    Image.fromarray(out, 'RGB').save(os.path.join(OUT, n + '.png'), optimize=True)
    report[n] = dict(src=im.size[0], out=2048)
    print(n, im.size[0], '-> 2048', flush=True)
json.dump(report, open('/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/opt/tex_v10_report.json', 'w'),
          indent=1)
