"""figure sheet: walk filmstrip (side) + poses front/side, textured. python3 -I fig_render2.py -- <blend> <out.jpg>"""
import bpy, sys, os, math
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
out = a[1]
tmp = os.path.join(os.path.dirname(out), 'fr2_tmp')
os.makedirs(tmp, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'TEXTURE'
sh.show_cavity = True
sh.show_backface_culling = True
for m in bpy.data.materials:
    if m.use_nodes:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
sc.render.resolution_x, sc.render.resolution_y = 300, 420
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 35
# a ground strip
me = bpy.data.meshes.new('gnd')
me.from_pydata([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [], [(0, 1, 2, 3)])
g = bpy.data.objects.new('gnd', me)
sc.collection.objects.link(g)
gm = bpy.data.materials.new('gndm')
gm.diffuse_color = (0.25, 0.27, 0.22, 1)
me.materials.append(gm)
arm = bpy.data.objects['Apparition_Rig']
shots = [('Walk', f, 'side', 1.1) for f in (1, 4, 8, 12, 16, 20, 24, 28)]
shots += [('Stand', 1, 'front', 1.15), ('Stand', 1, 'side', 1.15), ('Walk', 8, 'front', 1.1), ('Sit', 1, 'front', 0.3),
          ('Sit', 1, 'side', 0.3), ('SitLook', 15, 'front', 0.3), ('SitLook', 15, 'q', 0.3), ('Stand', 1, 'face', 2.1)]
files = []
for i, (act, fr, vn, zc) in enumerate(shots):
    arm.animation_data.action = bpy.data.actions[act]
    sc.frame_set(fr)
    d = {'front': Vector((0.15, -1, 0.08)), 'side': Vector((1, 0.0, 0.05)), 'q': Vector((-0.6, -1, 0.3)),
         'face': Vector((0.2, -1, 0.0))}[vn]
    c = Vector((0, -0.1 if act.startswith('Sit') else 0, zc))
    dist = 4.0 if not act.startswith('Sit') else 3.0
    if vn == 'face':
        dist = 1.1
    e = c + d.normalized() * dist
    cam.location = e
    cam.rotation_euler = (c - e).to_track_quat('-Z', 'Y').to_euler()
    f = os.path.join(tmp, f'{i:02d}.png')
    sc.render.filepath = f
    bpy.ops.render.render(write_still=True)
    files.append((f'{act} {fr} {vn}', f))
from PIL import Image, ImageDraw
cols = 8
W, H = 300, 420
rows = (len(files) + cols - 1) // cols
sheet = Image.new('RGB', (cols * W, rows * (H + 16)), (20, 20, 20))
dr = ImageDraw.Draw(sheet)
for i, (n, f) in enumerate(files):
    im = Image.open(f).convert('RGB')
    x, y = (i % cols) * W, (i // cols) * (H + 16)
    sheet.paste(im, (x, y + 16))
    dr.text((x + 4, y + 2), n, fill=(255, 255, 255))
sheet.save(out, quality=88)
print('sheet', out)
