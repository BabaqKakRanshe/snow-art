"""workbench views of out/gear[_draft].blend for checking: python3 -I gear_quick.py -- <blend> <out_dir> [views,...]
(open: the lantern's door, the headlamp tilted, the doll's head turned in the views marked open)"""
import bpy, sys, os, math
from mathutils import Vector
sys.path.insert(0, '/home/claude/uaz')
import gear_kit as GK
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
D = GK.DISPLAY
V = {   # name: eye offset, target offset (from the root), root, lens, res, open
    'all': ((0.2, -3.6, 1.6), (0.15, 0.2, 0.15), None, 30, (1800, 800), False),
    'cells': ((0.10, -0.42, 0.24), (0.10, 0.0, 0.04), 'Item_BatteryPack', 35, (1000, 700), False),
    'walkie': ((0.16, -0.30, 0.24), (0.0, 0.0, 0.09), 'Item_Walkie', 35, (900, 900), False),
    'walkie_back': ((-0.18, 0.26, 0.22), (0.0, 0.0, 0.08), 'Item_Walkie', 35, (900, 900), False),
    'lantern': ((0.24, -0.34, 0.26), (0.0, -0.01, 0.08), 'Item_Lantern', 35, (900, 900), False),
    'lantern_back': ((-0.20, 0.34, 0.26), (0.0, 0.02, 0.07), 'Item_Lantern', 35, (900, 900), True),
    'headlamp': ((0.30, -0.36, 0.28), (0.0, -0.02, 0.02), 'Item_Headlamp', 35, (1000, 800), True),
    'cart': ((1.4, -1.9, 1.3), (0.0, 0.05, 0.35), 'Item_Cart', 32, (1000, 900), False),
    'cart_low': ((-1.2, -0.9, 0.25), (0.0, 0.0, 0.18), 'Item_Cart', 32, (1000, 800), False),
    'sled': ((1.5, -2.2, 1.4), (0.0, -0.45, 0.1), 'Item_Sled', 32, (1100, 800), False),
    'doll': ((0.20, -0.62, 0.36), (0.0, -0.03, 0.15), 'Item_Doll', 32, (900, 1000), False),
    'doll_face': ((0.05, -0.30, 0.30), (0.0, 0.0, 0.25), 'Item_Doll', 35, (900, 900), False),
    'doll_turn': ((0.25, -0.55, 0.40), (0.0, -0.02, 0.18), 'Item_Doll', 32, (900, 1000), True),
    'postcard': ((0.0, -0.10, 0.30), (0.0, 0.0, 0.0), 'Item_Postcard', 35, (1000, 800), False),
    'bulb': ((0.18, -0.26, 0.16), (0.05, 0.0, 0.05), 'Item_Bulb', 35, (1000, 800), False),
    'tags': ((0.03, -0.20, -0.04), (0.035, 0.0, -0.04), 'Item_WorkerTag', 35, (1000, 800), False),
    'iceaxe': ((0.25, -1.3, 0.55), (0.04, 0.0, 0.36), 'Item_IceAxe', 32, (800, 1000), False),
    'iceaxe_head': ((0.12, -0.36, 0.78), (0.04, 0.0, 0.63), 'Item_IceAxe', 35, (1000, 800), False),
}
door, lamp, head = (bpy.data.objects.get(n) for n in ('Lantern_Door', 'Headlamp_Lamp', 'Doll_Head'))
for nm, (e, t, root, lens, res, op) in V.items():
    if want and nm not in want:
        continue
    o = D[root] if root else Vector((0, 0, 0))
    if door:
        door.rotation_euler = (math.radians(-85.0) if op else 0.0, 0.0, 0.0)
    if lamp:
        lamp.rotation_euler = (math.radians(30.0) if op else 0.0, 0.0, 0.0)
    if head:
        head.rotation_euler = (0.0, 0.0, math.radians(70.0) if op else 0.0)
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = o + Vector(e)
    cam.rotation_euler = ((o + Vector(t)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.005
    sc.render.filepath = os.path.join(OUT, nm + '.png')
    bpy.ops.render.render(write_still=True)
print('ok')
