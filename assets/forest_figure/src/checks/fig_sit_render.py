"""Sit / SitLook in a van-bench mock: floor -0.425, bench (y -0.20..0.25, top 0), wall y 0.25, roof 0.709 (figure frame)"""
import bpy, sys, os, math
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
out = a[1]
tmp = os.path.join(os.path.dirname(out), 'sit_tmp')
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
sc.render.resolution_x, sc.render.resolution_y = 420, 360


def box(name, lo, hi, col):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector([lo[i] + (v.co[i] + 0.5) * (hi[i] - lo[i]) for i in range(3)])
    bm.to_mesh(me)
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    m = bpy.data.materials.new(name + 'm')
    m.diffuse_color = col
    me.materials.append(m)
    return o


box('floor', (-1.2, -1.0, -0.445), (1.2, 0.30, -0.425), (0.3, 0.3, 0.28, 1))
box('bench', (-1.2, -0.20, -0.03), (1.2, 0.25, 0.0), (0.35, 0.25, 0.18, 1))
box('wall', (-1.2, 0.25, -0.445), (1.2, 0.30, 0.709), (0.4, 0.42, 0.4, 1))
roof = box('roof', (-1.2, -1.0, 0.709), (1.2, 0.30, 0.74), (0.5, 0.5, 0.5, 1))
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 28
arm = bpy.data.objects['Apparition_Rig']
files = []
for act, fr in (('Sit', 1), ('SitLook', 8), ('SitLook', 15)):
    for vn, d in (('front', Vector((0.25, -1, 0.1))), ('side', Vector((1, -0.05, 0.02))), ('mirror', None)):
        arm.animation_data.action = bpy.data.actions[act]
        sc.frame_set(fr)
        roof.hide_render = vn == 'front'
        if vn == 'mirror':                     # van3's MirrorCam seen from the left bench's Sit_L2 (fov 32 deg)
            e = Vector((2.158, -0.659, 0.650))
            cam.location = e
            cam.rotation_euler = Vector((-0.998, 0.0, -0.067)).to_track_quat('-Z', 'Y').to_euler()
            cam.data.angle = math.radians(32)
        else:
            c = Vector((0, -0.25, 0.1))
            e = c + d.normalized() * 2.4
            cam.location = e
            cam.rotation_euler = (c - e).to_track_quat('-Z', 'Y').to_euler()
            cam.data.lens = 28
        f = os.path.join(tmp, f'{act}_{fr}_{vn}.png')
        sc.render.filepath = f
        bpy.ops.render.render(write_still=True)
        files.append((f'{act} {fr} {vn}', f))
from PIL import Image, ImageDraw
W, H = 420, 360
cols = 3
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
