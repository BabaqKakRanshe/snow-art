"""workbench views of out/parts[_draft].blend for checking: python3 -I parts_quick.py -- <blend> <out_dir> [views,...]
(open: the valves open, the sensor's lid open, the fuse cap off in the views marked open)"""
import bpy, sys, os, math
from mathutils import Vector
sys.path.insert(0, '/home/claude/uaz')
import parts_kit as GK
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
    'all': ((0.6, -4.2, 2.2), (0.6, -0.1, 0.25), None, 30, (1800, 900), False),
    'pump': ((0.55, -1.05, 0.75), (0.02, 0.0, 0.25), 'Item_DosingPump', 32, (1100, 900), False),
    'pump_valves': ((0.25, -0.55, 0.45), (0.15, -0.08, 0.28), 'Item_DosingPump', 35, (1100, 900), True),
    'pump_back': ((-0.70, 0.85, 0.65), (0.0, 0.0, 0.25), 'Item_DosingPump', 32, (1000, 800), False),
    'lamp': ((0.16, -0.30, 0.22), (0.07, 0.0, 0.14), 'Item_SodiumLamp', 35, (900, 900), False),
    'crt': ((0.55, -0.85, 0.65), (0.0, 0.0, 0.24), 'Item_RadarCRT', 32, (900, 900), False),
    'crt_low': ((0.40, -0.55, 0.05), (0.0, 0.0, 0.10), 'Item_RadarCRT', 32, (900, 700), False),
    'relay': ((0.25, -0.75, 0.30), (0.0, -0.05, 0.06), 'Item_RelayUnit', 34, (1100, 700), False),
    'relay_back': ((-0.30, 0.75, 0.35), (0.0, 0.05, 0.06), 'Item_RelayUnit', 34, (1100, 700), True),
    'gen': ((0.65, -1.05, 0.75), (0.0, 0.0, 0.22), 'Item_BackupGenerator', 32, (1000, 900), False),
    'gen_back': ((-0.70, 0.90, 0.70), (0.0, 0.0, 0.22), 'Item_BackupGenerator', 32, (1000, 900), False),
    'sensor': ((0.9, -2.6, 1.6), (0.0, -0.6, 0.7), 'LakeSensor', 30, (900, 1000), False),
    'sensor_box': ((0.30, -0.80, 1.35), (0.0, -0.09, 1.10), 'LakeSensor', 32, (900, 900), True),
}
OPEN = [('DosingPump_V1', (0, 0, math.radians(90))), ('DosingPump_V2', (0, 0, math.radians(90))),
        ('DosingPump_V3', (0, 0, math.radians(90))), ('LakeSensor_Lid', (0, 0, math.radians(-110))),
        ('RelayUnit_Power', (math.radians(-40), 0, 0))]
for nm, (e, t, root, lens, res, op) in V.items():
    if want and nm not in want:
        continue
    o = D[root] if root else Vector((0, 0, 0))
    for on, rot in OPEN:
        ob = bpy.data.objects.get(on)
        if ob:
            ob.rotation_euler = rot if op else (0.0, 0.0, 0.0)
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = o + Vector(e)
    cam.rotation_euler = ((o + Vector(t)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.005
    sc.render.filepath = os.path.join(OUT, nm + '.png')
    bpy.ops.render.render(write_still=True)
print('ok')
