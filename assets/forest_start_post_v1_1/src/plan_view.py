"""orthographic plan of a .blend in the start frame (image up = +v, right = +u), all trees, no fog, 5 m (u, v) grid and marks:
python3.11 -I plan_view.py in.blend out.png [uc vc size px]   (env HIDE=prefix,...)"""
import bpy, sys, math, os
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frame import uv_to_blender_xy, ROTZ
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
uc, vc, size, px = (float(argv[2]), float(argv[3]), float(argv[4]), int(argv[5])) if len(argv) > 5 else (-4.0, -14.0, 80.0, 1600)
sc = bpy.context.scene
sc['fog_k'] = 0.0
for o in bpy.data.objects:
    if any(o.name.startswith(p) for p in os.environ.get('HIDE', '').split(',') if p):
        o.hide_render = True
for o in (bpy.data.collections['Trees'].objects if 'Trees' in bpy.data.collections else []):
    o.hide_render = False
cd = bpy.data.cameras.new('Plan'); cd.type = 'ORTHO'; cd.ortho_scale = size; cd.clip_end = 2000
co = bpy.data.objects.new('Plan', cd); sc.collection.objects.link(co)
bx, by = uv_to_blender_xy(uc, vc)
co.location = Vector((float(bx), float(by), 400)); co.rotation_euler = (0, 0, ROTZ)
sc.camera = co
sc.render.resolution_x = sc.render.resolution_y = px
sc.cycles.samples = int(os.environ.get('SPP', '4'))
sc.render.filepath = argv[1]
bpy.ops.render.render(write_still=True)
from PIL import Image, ImageDraw
im = Image.open(argv[1]).convert('RGB'); d = ImageDraw.Draw(im)
s = px / size
u0, v1 = uc - size / 2, vc + size / 2
def P(u, v):
    return ((u - u0) * s, (v1 - v) * s)
if os.environ.get('GRID', '1') == '1':
    for g in range(int(math.ceil(u0 / 5)) * 5, int(u0 + size) + 1, 5):
        X = (g - u0) * s; d.line([(X, 0), (X, px)], fill=(255, 220, 0) if g % 10 else (255, 90, 0), width=1)
        if g % 10 == 0: d.text((X + 2, 2), 'u%d' % g, fill=(255, 255, 0))
    for g in range(int(math.ceil((vc - size / 2) / 5)) * 5, int(vc + size / 2) + 1, 5):
        Y = (v1 - g) * s; d.line([(0, Y), (px, Y)], fill=(255, 220, 0) if g % 10 else (255, 90, 0), width=1)
        if g % 10 == 0: d.text((2, Y + 2), 'v%d' % g, fill=(255, 255, 0))
    for name, (u, v) in {'spawn': (1, -8), 'van': (1, -14), 'L01_arrive': (-2, -34), 'L01_booth': (-6, -17.8)}.items():
        x, y = P(u, v); d.ellipse([x - 5, y - 5, x + 5, y + 5], outline=(0, 255, 255), width=2); d.text((x + 7, y - 6), name, fill=(0, 255, 255))
im.save(argv[1])
