"""Per-item renders of the kit (workbench, studio light, cavity; texture colours when baked):
python3 -I snowkit_sheet.py -- <blend> <out_dir> [tex] [size] [view]  -> <out_dir>/<item>.png and contact.jpg
view: 'fl' (front-left, default), 'fr', 'back', 'top'"""
import bpy, sys, os, math, json
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
out = a[1]
tex = len(a) > 2 and a[2] == '1'
SZ = int(a[3]) if len(a) > 3 else 360
view = a[4] if len(a) > 4 else 'fl'
os.makedirs(out, exist_ok=True)
sys.path.insert(0, '/home/claude/uaz')
import snowkit_spec as S
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'TEXTURE' if tex else 'MATERIAL'
sh.show_cavity = True
sh.cavity_type = 'BOTH'
sh.show_object_outline = False
for m in bpy.data.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
sc.render.resolution_x, sc.render.resolution_y = SZ, int(SZ * 0.75)
sc.render.film_transparent = False
sc.world = sc.world or bpy.data.worlds.new('W')
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 50
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_render = True


def desc(o):
    out_, st = [], [o]
    while st:
        p = st.pop()
        out_.append(p)
        st.extend(p.children)
    return out_


files = []
roots = [bpy.data.objects[n] for n in S.ITEM_NAMES if n in bpy.data.objects]
D = {'fl': (-0.55, -0.85, 0.50), 'fr': (0.6, -0.8, 0.45), 'back': (0.5, 0.85, 0.45), 'top': (0.0, -0.25, 1.0)}[view]
for r in roots:
    keep = set(desc(r))
    for o in bpy.data.objects:
        if o.type in ('MESH', 'CURVE'):
            o.hide_render = (o not in keep) or o.name.startswith(('COL_', 'Glow_'))
    vs = [o.matrix_world @ v.co for o in keep if o.type == 'MESH' and not o.name.startswith(('COL_', 'Glow_')) for v in o.data.vertices]
    if r.name.startswith('Kit_Wire_'):                  # a 10 / 40 m span is a hair at that size: frame its first 2.5 m
        x0_ = r.matrix_world.translation.x
        vs = [v for v in vs if v.x < x0_ + 2.5]
    lo = Vector([min(v[i] for v in vs) for i in range(3)])
    hi = Vector([max(v[i] for v in vs) for i in range(3)])
    c = (lo + hi) / 2
    rad = max((hi - lo).length / 2, 0.02)
    d = Vector(D).normalized()
    e = c + d * rad * 3.1
    cam.location = e
    cam.rotation_euler = (c - e).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_start = rad * 0.05
    cam.data.clip_end = rad * 30
    f = os.path.join(out, r.name + '.png')
    sc.render.filepath = f
    bpy.ops.render.render(write_still=True)
    files.append((r.name, f))
from PIL import Image, ImageDraw
cols = 6
W, H = SZ, int(SZ * 0.75)
rows = (len(files) + cols - 1) // cols
sheet = Image.new('RGB', (cols * W, rows * (H + 16)), (24, 24, 24))
dr = ImageDraw.Draw(sheet)
for i, (n, f) in enumerate(files):
    im = Image.open(f).convert('RGB')
    x, y = (i % cols) * W, (i // cols) * (H + 16)
    sheet.paste(im, (x, y + 16))
    dr.text((x + 4, y + 2), n, fill=(255, 255, 255))
sheet.save(os.path.join(out, f'contact_{view}.jpg'), quality=88)
print('sheet', len(files))
