"""detail views of kit items (workbench): python3 -I snowkit_detail.py -- <blend> <out_dir> [tex]
each view: (item root, target offset in the item frame, view direction, radius, pose {part: value})"""
import bpy, sys, os, math, json
from mathutils import Vector, Matrix
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
out = a[1]
tex = len(a) > 2 and a[2] == '1'
os.makedirs(out, exist_ok=True)
sys.path.insert(0, '/home/claude/uaz')
C = json.load(open(a[0].replace('.blend', '_contract.json').replace('snow_kit_draft_contract', 'snow_kit_contract_draft')))
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'TEXTURE' if tex else 'MATERIAL'
sh.show_cavity = True
sh.cavity_type = 'BOTH'
for m in bpy.data.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
sc.render.resolution_x, sc.render.resolution_y = 640, 480
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 50
for o in bpy.data.objects:
    if o.name.startswith(('COL_', 'Glow_')):
        o.hide_render = True


def pose(name, v):
    p = C['parts'][name]
    o = bpy.data.objects[name]
    if 'rest_mw' not in o:
        o['rest_mw'] = [list(r) for r in o.matrix_world]
    mw0 = Matrix(o['rest_mw'])
    par = o.parent
    # pivot / axis are in the item frame: to world through the root
    root = bpy.data.objects[p['item']]
    piv = root.matrix_world @ Vector(p['pivot'])
    ax = (root.matrix_world.to_3x3() @ Vector(p['axis'])).normalized()
    if p['kind'] in ('hinge', 'twist'):
        M = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(v), 4, ax) @ Matrix.Translation(-piv)
    else:
        M = Matrix.Translation(ax * v)
    o.matrix_world = M @ mw0


VIEWS = [
    ('pole_top', 'Kit_Pole', (0, 0, 8.0), (-0.6, -0.8, 0.25), 1.4, {}),
    ('pole_base', 'Kit_Pole', (0, 0, 2.2), (-0.6, -0.8, 0.15), 1.6, {}),
    ('trafo', 'Kit_Pole_Trafo', (0.2, -0.4, 5.6), (-0.7, -0.7, 0.2), 2.4, {}),
    ('trafo_top', 'Kit_Pole_Trafo', (0.0, -0.2, 7.6), (0.5, -0.8, 0.3), 1.6, {}),
    ('roofstand_top', 'Kit_RoofStand', (0, -0.12, 2.0), (-0.6, -0.8, 0.3), 0.6, {}),
    ('cabinet_open', 'Kit_Cabinet_Power', (0, -0.15, 0.0), (0.25, -1.0, 0.2), 0.75, {'IX_CabinetDoor': 105}),
    ('cabinet_clamps', 'Kit_Cabinet_Power', (0, -0.15, -0.12), (0.1, -1.0, 0.45), 0.35, {'IX_CabinetDoor': 105}),
    ('cabinet_front', 'Kit_Cabinet_Power', (0, -0.3, 0.0), (0.0, -1.0, 0.05), 0.7, {}),
    ('phone_front', 'Kit_Phone', (0, -0.01, 0.07), (-0.3, -1.0, 0.6), 0.22, {}),
    ('camera_front', 'Kit_Camera_Head', (0, -0.08, 0.08), (-0.4, -1.0, 0.25), 0.25, {}),
    ('monitor_front', 'Kit_Monitor_CRT', (0, -0.05, 0.16), (-0.25, -1.0, 0.2), 0.36, {}),
    ('console_2', 'Kit_Console_2', (0, 0, 0.06), (-0.2, -1.0, 0.8), 0.28, {}),
    ('campole_base', 'Kit_Mast', (0, 0.06, 0.44), (0.42, 1.0, 0.30), 0.56, {}),
]
for vname, root, tgt, d, rad, pz in VIEWS:
    r = bpy.data.objects[root]
    for n, v in pz.items():
        pose(n, v)
    c = r.matrix_world @ Vector(tgt)
    e = c + Vector(d).normalized() * rad * 2.4
    cam.location = e
    cam.rotation_euler = (c - e).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_start = 0.01
    cam.data.clip_end = 200
    sc.render.filepath = os.path.join(out, vname + '.png')
    bpy.ops.render.render(write_still=True)
    for n in pz:
        pose(n, 0.0)
from PIL import Image, ImageDraw
fs = [os.path.join(out, v[0] + '.png') for v in VIEWS]
cols = 4
rows = (len(fs) + cols - 1) // cols
sheet = Image.new('RGB', (cols * 640, rows * 496), (24, 24, 24))
dr = ImageDraw.Draw(sheet)
for i, f in enumerate(fs):
    im = Image.open(f).convert('RGB')
    x, y = (i % cols) * 640, (i // cols) * 496
    sheet.paste(im, (x, y + 16))
    dr.text((x + 4, y + 2), VIEWS[i][0], fill=(255, 255, 255))
sheet = sheet.resize((sheet.width // 2 * 2 // 2 * 1, sheet.height // 2 * 2 // 2 * 1)) if False else sheet
sheet.save(os.path.join(out, 'details.jpg'), quality=88)
print('details', len(fs))
