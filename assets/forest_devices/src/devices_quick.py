"""workbench views of out/devices[_draft].blend for checking: python3 -I devices_quick.py -- <blend> <out_dir> [views,...]
(lid: the laptop's IX_LaptopLid opened to 105 deg in the views laptop_open)"""
import bpy, sys, os, math
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
OUT = a[1]
want = a[2].split(',') if len(a) > 2 else None
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'TEXTURE' if 'draft' not in a[0] else 'MATERIAL'
sh.show_cavity = True
sh.cavity_type = 'BOTH'
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_render = True
for m in bpy.data.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, -0.0005))
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
F, PA, CS, CB, DB, PC, LP, TD, SC = (Vector(v) for v in ((0, 0, 0), (0.45, 0, 0), (0.85, -0.05, 0), (0.85, 0.15, 0), (2.2, 0, 0),
                                                         (-1, 0, 0), (-2, 0, 0), (0, 1.0, 0.3), (2.2, 1.6, 0)))
V = {
    'all': ((0.0, -4.6, 2.2), (0.1, 0.0, 0.35), 30, (1600, 800), False),
    'fax_fr': (F + Vector((0.32, -0.50, 0.36)), F + Vector((0.0, 0.0, 0.05)), 35, (1000, 800), False),
    'fax_bl': (F + Vector((-0.40, 0.45, 0.40)), F + Vector((0.0, 0.0, 0.06)), 35, (1000, 800), False),
    'fax_panel': (F + Vector((0.05, -0.30, 0.26)), F + Vector((0.045, -0.045, 0.075)), 40, (1000, 700), False),
    'tapes': (CS + Vector((0.25, -0.40, 0.35)), Vector((0.80, 0.05, 0.03)), 35, (1000, 800), False),
    'paper': (PA + Vector((0.20, -0.40, 0.35)), PA + Vector((0.0, 0.0, 0.01)), 35, (1000, 800), False),
    'dropbox': (DB + Vector((1.1, -1.6, 1.6)), DB + Vector((0.0, 0.0, 0.8)), 32, (900, 1000), False),
    'dropbox_slot': (DB + Vector((0.25, -0.60, 1.45)), DB + Vector((0.0, -0.15, 1.25)), 35, (1000, 900), False),
    'pc': (PC + Vector((0.65, -1.15, 0.75)), PC + Vector((0.05, -0.10, 0.18)), 32, (1000, 900), False),
    'pc_back': (PC + Vector((-0.55, 0.75, 0.35)), PC + Vector((0.0, 0.10, 0.08)), 35, (1000, 800), False),
    'laptop': (LP + Vector((0.40, -0.50, 0.40)), LP + Vector((0.0, 0.0, 0.03)), 35, (1000, 800), False),
    'laptop_open': (LP + Vector((0.35, -0.55, 0.40)), LP + Vector((0.0, 0.02, 0.10)), 35, (1000, 900), True),
    'deck': (TD + Vector((0.30, -0.75, 0.20)), TD + Vector((0.0, 0.0, 0.0)), 35, (1200, 600), False),
    'deck_door': (TD + Vector((-0.20, -0.30, 0.10)), TD + Vector((-0.35, -0.02, 0.02)), 35, (1000, 800), True),
    'screen': (SC + Vector((1.2, -2.2, 1.9)), SC + Vector((0.0, 0.0, 1.1)), 32, (900, 1000), False),
    'screen_open': (SC + Vector((0.6, -1.3, 1.75)), SC + Vector((0.0, 0.0, 1.50)), 32, (1000, 1000), True),
    'screen_in': (SC + Vector((0.12, -0.75, 1.60)), SC + Vector((0.0, 0.05, 1.45)), 30, (1000, 1000), True),
}
lid = bpy.data.objects.get('IX_LaptopLid')
doors = [(bpy.data.objects.get('IX_TapeDoor'), (math.radians(30.0), 0.0, 0.0)),
         (bpy.data.objects.get('IX_ScreenDoor'), (0.0, 0.0, math.radians(-105.0)))]
for nm, (e, t, lens, res, open_lid) in V.items():
    if want and nm not in want:
        continue
    if lid:
        lid.rotation_euler = (math.radians(-105.0) if open_lid else 0.0, 0.0, 0.0)
    for o, rot in doors:
        if o:
            o.rotation_euler = rot if open_lid else (0.0, 0.0, 0.0)
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = Vector(e)
    cam.rotation_euler = (Vector(t) - Vector(e)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.005
    sc.render.filepath = os.path.join(OUT, nm + '.png')
    bpy.ops.render.render(write_still=True)
print('ok')
