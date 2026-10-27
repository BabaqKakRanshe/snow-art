"""workbench views of out/bunker[_draft].blend for checking: python3 -I bunker_quick.py -- <blend> <out_dir> [views,...]"""
import bpy, sys, os, math
from mathutils import Vector
sys.path.insert(0, '/home/claude/uaz')
import bunker_kit as BK
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
sh.show_backface_culling = True
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
D = BK.DISPLAY
V = {   # name: eye offset, target offset (from the root), root, lens, res
    'hangar': ((14.0, -22.0, 7.0), (0.0, 4.0, 3.0), 'BunkerHangar', 24, (1400, 900)),
    'hangar_in': ((-5.0, 1.5, 2.2), (2.0, 12.0, 2.0), 'BunkerHangar', 16, (1400, 900)),
    'hangar_back': ((5.0, 14.8, 3.0), (-3.0, 2.0, 2.2), 'BunkerHangar', 16, (1400, 900)),
    'sidedoor': ((-3.5, 6.0, 1.9), (-8.5, 2.2, 1.8), 'BunkerHangar', 22, (1200, 900)),
    'vest': ((0.6, 0.6, 1.7), (0.0, 7.8, 2.0), 'BlastDoor', 18, (1200, 900)),
    'door': ((0.9, 4.2, 1.8), (0.0, 7.8, 1.95), 'BlastDoor', 22, (1200, 900)),
    'door_back': ((1.5, 12.5, 1.6), (0.0, 7.8, 1.6), 'BlastDoor', 18, (1200, 900)),
    'entr': ((0.3, -2.6, 2.3), (0.0, 5.5, -2.6), 'BunkerEntrance', 18, (1200, 900)),
    'entr_low': ((0.6, 4.6, -1.4), (0.0, 6.6, -3.0), 'BunkerEntrance', 20, (1200, 900)),
    'entr_shaft': ((0.3, 6.25, -3.3), (0.0, 6.8, -7.0), 'BunkerEntrance', 16, (900, 1100)),
    'tarp': ((-6.0, -6.0, 4.0), (0.0, -1.5, 1.8), 'PlaneTarp', 24, (1200, 900)),
}
for nm, (e, t, root, lens, res) in V.items():
    if want and nm not in want:
        continue
    o = D[root]
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = o + Vector(e)
    cam.rotation_euler = ((o + Vector(t)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.02
    cam.data.clip_end = 300
    sc.render.filepath = os.path.join(OUT, nm + '.png')
    bpy.ops.render.render(write_still=True)
print('ok')
