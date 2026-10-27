"""workbench views of out/world[_draft].blend for checking: python3 -I world_quick.py -- <blend> <out_dir> [views,...]"""
import bpy, sys, os, math
from mathutils import Vector
sys.path.insert(0, '/home/claude/uaz')
import world_kit as WK
import world_ice as WI
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
    if o.name.startswith(('COL_', 'HIT_', 'COLM_')):
        o.hide_render = True
for m in bpy.data.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
D = dict(WK.DISPLAY, **WI.ICE_DISPLAY)
V = {   # name: eye offset, target offset (from the root), root, lens, res
    'barrel': ((1.3, -1.8, 1.5), (0.0, 0.0, 0.5), 'FireBarrel', 35, (900, 900)),
    'shift': ((4.2, -5.6, 2.4), (0.0, 0.0, 0.9), 'ShiftCar', 32, (1200, 800)),
    'shift_rear': ((-3.8, 5.6, 2.6), (0.0, 0.3, 0.9), 'ShiftCar', 32, (1200, 800)),
    'wreck': ((-4.2, -5.8, 2.2), (0.0, 0.0, 0.7), 'WreckCar', 32, (1200, 800)),
    'wreck_rear': ((4.0, 6.0, 2.4), (0.0, 0.3, 0.7), 'WreckCar', 32, (1200, 800)),
    'cave': ((5.0, -9.5, 4.0), (0.0, 2.5, 1.2), 'ForesterCave', 24, (1200, 800)),
    'cave_in': ((0.3, 0.6, 1.5), (-0.6, 4.2, 0.5), 'ForesterCave', 14, (1200, 800)),
    'cave_in2': ((-1.6, 5.4, 1.6), (1.0, 2.6, 0.6), 'ForesterCave', 14, (1200, 800)),
    'ice_relay': ((7.0, -9.0, 44.0), (0.0, 0.0, 37.0), 'Ice_RelayMast', 30, (900, 1100)),
    'ice_dish': ((9.0, -14.0, 10.0), (0.0, 2.0, 9.5), 'Ice_Dish_1', 30, (1100, 900)),
    'ice_roof': ((9.5, -4.0, 18.5), (5.45, 2.0, 15.0), 'Ice_RoofMast', 30, (900, 1100)),
}
cut = '--cut' in a
for nm, (e, t, root, lens, res) in V.items():
    if want and nm not in want:
        continue
    o = D[root]
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = o + Vector(e)
    cam.rotation_euler = ((o + Vector(t)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.02
    sc.render.filepath = os.path.join(OUT, nm + '.png')
    bpy.ops.render.render(write_still=True)
print('ok')
