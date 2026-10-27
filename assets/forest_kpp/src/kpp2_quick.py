"""quick workbench views of the KPP v2 (draft or final): python3 -I kpp2_quick.py -- <blend> <out_dir> [views]"""
import bpy, sys, os, math
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
out = a[1]
want = a[2].split(',') if len(a) > 2 else None
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'TEXTURE'
sh.show_cavity = True
sh.cavity_type = 'BOTH'
for m in bpy.data.materials:
    if m.node_tree and m.library is None:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
sc.render.resolution_x, sc.render.resolution_y = 960, 640
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
# the kit is linked: its glow cards (halo quads, emission only) would draw as dark quads in the workbench; make the linked data
# local so that they (and the colliders) can be hidden
for coll_ in (bpy.data.collections, bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.images):
    for idb in list(coll_):
        if idb.library is not None:
            try:
                idb.make_local()
            except Exception:
                pass
for o in bpy.data.objects:
    if o.name.startswith(('COL_', 'Glow_')):
        o.hide_render = True
# ground plane for orientation
bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 10, -0.39))
VIEWS = {
    'road': ((9.0, -16.0, 3.2), (1.5, -3.5, 0.8), 35),
    'front': ((4.5, -9.0, 2.0), (1.5, -1.5, 1.3), 30),
    'back': ((-5.5, 8.0, 3.5), (-0.8, 2.0, 1.8), 30),
    'line': ((6.0, -4.0, 5.0), (-1.0, 14.0, 4.0), 24),
    'inside': ((0.2, 0.9, 1.75), (1.35, -1.0, 0.95), 22),
    'desk': ((0.9, -0.4, 1.45), (1.55, -1.05, 1.0), 26),
    'cabinet': ((-1.0, 3.6, 1.4), (-1.2, 1.6, 1.2), 32),
    'barrier': ((6.5, -12.0, 2.2), (4.5, -7.0, 0.8), 30),
    'gate_out': ((7.5, -9.0, 2.5), (8.5, 0.0, 1.2), 30),
    'gate_in': ((15.5, 6.0, 3.2), (9.0, 0.5, 1.5), 30),
    'top': ((3.0, 0.0, 40.0), (3.0, 0.0, 0.0), 30),
}
for vn, (e, t, lens) in VIEWS.items():
    if want and vn not in want:
        continue
    cam.location = Vector(e)
    cam.rotation_euler = (Vector(t) - Vector(e)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.05
    cam.data.clip_end = 300
    sc.render.filepath = os.path.join(out, vn + '.png')
    bpy.ops.render.render(write_still=True)
from PIL import Image, ImageDraw
fs = [(vn, os.path.join(out, vn + '.png')) for vn in VIEWS if (not want or vn in want)]
cols = 3
rows = (len(fs) + cols - 1) // cols
W, H = 960, 640
sheet = Image.new('RGB', (cols * W, rows * (H + 18)), (24, 24, 24))
d = ImageDraw.Draw(sheet)
for i, (vn, f) in enumerate(fs):
    x, y = (i % cols) * W, (i // cols) * (H + 18)
    sheet.paste(Image.open(f).convert('RGB'), (x, y + 18))
    d.text((x + 4, y + 3), vn, fill=(255, 255, 255))
sheet.save(os.path.join(out, 'quick.jpg'), quality=85)
print('quick', len(fs))
