"""The plan of the KPP v2 package (the booth frame, as in kpp.blend: the gate stands next to the booth here, in the game it is at
the base yard): an orthographic workbench view from above, labelled.  python3 -I kpp2_plan.py -- <kpp.blend> <out.png>"""
import bpy, sys, os, json
from mathutils import Vector

a = sys.argv[sys.argv.index('--') + 1:]
BLEND, OUT = a[0], a[1]
HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=BLEND)
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
    if o.name.startswith(('COL_', 'Glow_', 'qcam')):
        o.hide_render = True
W, H = 1500, 1000
CX, CY, SCALE = 3.5, -2.2, 40.0
sc.render.resolution_x, sc.render.resolution_y = W, H
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.40))
cam = bpy.data.objects.new('plan_cam', bpy.data.cameras.new('plan_cam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = 'ORTHO'
cam.data.ortho_scale = SCALE
cam.location = (CX, CY, 60.0)
cam.rotation_euler = (0.0, 0.0, 0.0)
cam.data.clip_start, cam.data.clip_end = 1.0, 200.0
raw = OUT.replace('.png', '_raw.png')
sc.render.filepath = raw
bpy.ops.render.render(write_still=True)

from PIL import Image, ImageDraw, ImageFont
C = json.load(open(os.path.join(HERE, 'out', 'kpp_contract.json')))
KI = C['kit_instances']


def px(x, y):
    return (W / 2 + (x - CX) / SCALE * W, H / 2 - (y - CY) / SCALE * W)


def font(sz, bold=False):
    for f in (('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),):
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()


im = Image.open(raw).convert('RGB')
d = ImageDraw.Draw(im)
F, FB = font(19), font(21, True)
P = C['parts']
LAB = [   # (text, booth-frame point, label offset px)
    ('Checkpoint — будка', (0.0, 0.0), (-250, 60)),
    ('PowerCabinet (K5) на задней стене', KI['PowerCabinet']['pos_kpp'][:2], (-420, 40)),
    ('RoofStand (K9)', KI['RoofStand']['pos_kpp'][:2], (-260, -10)),
    ('Pole_1 (K8, трансформатор): ввод 4 провода на RoofStand', KI['Pole_1']['pos_kpp'][:2], (60, 0)),
    ('JunctionBox (K6)', KI['JunctionBox']['pos_kpp'][:2], (40, -40)),
    ('Cond_Bar_* (K7): кабель шлагбаума по земле', KI['Cond_Bar_S2']['pos_kpp'][:2], (-520, 30)),
    ('JunctionBox_Wall (K6) на плите забора (со стороны улицы)', KI['JunctionBox_Wall']['pos_kpp'][:2], (-640, 60)),
    ('CamPole_Barrier (K12): мачта — камера шлагбаума, прожектор', KI['CamPole_Barrier']['pos_kpp'][:2], (-660, -6)),
    ('Cond_CamBar_* (K7): кабель камеры в площадку', (1.50, -3.6), (-560, -22)),
    ('Barrier: тумба с мотором, маячок, стрела IX_BarrierArm_82', (3.10, -7.0), (60, 30)),
    ('Barrier_Manual — старый шлагбаум, отдельный префаб (на карту не ставится)', (3.10, -14.0), (-330, -48)),
    ('Gate: полотно IX_Gate_81, рельс (в игре — у двора базы)', (7.5, 0.5), (20, 40)),
    ('Pole_Gate (K8): привод → линия', KI['Pole_Gate']['pos_kpp'][:2], (40, -60)),
    ('CamPole_Gate (K12): мачта — камера ворот, прожектор', KI['CamPole_Gate']['pos_kpp'][:2], (-330, -120)),
]
for text, p, (ox, oy) in LAB:
    x, y = px(*p)
    tx, ty = x + ox, y + oy
    tw = d.textlength(text, font=F)
    ex = tx if x <= tx else (tx + tw if x >= tx + tw else x)       # the leader to the nearest point of the label
    ey = ty + 11 if ex != x else (ty if y < ty else ty + 22)
    d.line([(x, y), (ex, ey)], fill=(200, 30, 30), width=2)
    d.ellipse([x - 5, y - 5, x + 5, y + 5], outline=(200, 30, 30), width=3)
    d.rectangle([tx - 4, ty - 2, tx + tw + 4, ty + 24], fill=(255, 255, 255))
    d.text((tx, ty), text, fill=(20, 20, 20), font=F)
# the road and the line onward

x0, y0 = px(-1.5, 9.0)
d.text((x0 - 40, 14), '↑ Pole_2 (K8) — в 45 м дальше по y, оттуда линия к базе', fill=(20, 20, 20), font=F)
for gx in range(-15, 25, 5):                                  # 5 m ticks
    x, _ = px(gx, 0)
    d.line([(x, H - 12), (x, H)], fill=(60, 60, 60), width=2)
    d.text((x + 3, H - 30), f'{gx}', fill=(60, 60, 60), font=font(14))
for gy in range(-15, 15, 5):
    _, y = px(0, gy)
    d.line([(0, y), (12, y)], fill=(60, 60, 60), width=2)
    d.text((14, y - 9), f'{gy}', fill=(60, 60, 60), font=font(14))
full = Image.new('RGB', (W, H + 56), (255, 255, 255))
full.paste(im, (0, 56))
dd = ImageDraw.Draw(full)
dd.text((20, 14), 'КПП v2.1 — план пакета (кадр будки: x — к дороге, y — назад, к станции; метки по краям — через 5 м)',
        fill=(20, 20, 20), font=FB)
full.save(OUT)
im = full
print('plan', OUT, im.size)
