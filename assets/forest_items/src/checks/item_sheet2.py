"""contact sheet of the items in a blend: python3 item_sheet.py -- <blend> <out.jpg> [cull] [texture]"""
import bpy, sys, os, math
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
out = a[1]
cull = len(a) > 2 and a[2] == '1'
tex = len(a) > 3 and a[3] == '1'
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'TEXTURE' if tex else 'MATERIAL'
for m in bpy.data.materials:
    if m.use_nodes:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
sh.show_cavity = True
sh.show_backface_culling = cull
sc.render.resolution_x, sc.render.resolution_y = 300, 225
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 50
items = sorted((o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('Item_') and o.parent is None), key=lambda o: o.name)
tmp = os.path.join(os.path.dirname(out), 'isheet_tmp')
os.makedirs(tmp, exist_ok=True)
files = []
for o in items:
    for p in items:
        p.hide_render = p != o
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    lo = Vector([min(v[i] for v in vs) for i in range(3)]); hi = Vector([max(v[i] for v in vs) for i in range(3)])
    c = (lo + hi) / 2
    r = max((hi - lo).length / 2, 0.02)
    d = Vector((-0.55, -0.85, 0.55)).normalized()
    e = c + d * r * 3.0
    cam.location = e
    cam.rotation_euler = (c - e).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_start = r * 0.05
    cam.data.clip_end = r * 20
    f = os.path.join(tmp, o.name + '.png')
    sc.render.filepath = f
    bpy.ops.render.render(write_still=True)
    files.append((o.name, f))
from PIL import Image, ImageDraw
cols = 6
per = int(os.environ.get('SHEET_PER', '1000'))
W, H = 300, 225
for k in range(0, len(files), per):
    chunk = files[k:k + per]
    rows = (len(chunk) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * W, rows * (H + 16)), (24, 24, 24))
    dr = ImageDraw.Draw(sheet)
    for i, (n, f) in enumerate(chunk):
        im = Image.open(f).convert('RGB')
        x, y = (i % cols) * W, (i // cols) * (H + 16)
        sheet.paste(im, (x, y + 16))
        dr.text((x + 4, y + 2), n[5:], fill=(255, 255, 255))
    o2 = out.replace('.jpg', f'_{k // per}.jpg')
    sheet.save(o2, quality=88)
    print('sheet', o2, len(chunk))
