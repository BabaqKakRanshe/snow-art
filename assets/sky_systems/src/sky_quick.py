"""workbench views of out/sky[_draft].blend for checking: python3 -I sky_quick.py -- <blend> <out_dir> [views,...]"""
import bpy, sys, os, math
from mathutils import Vector
sys.path.insert(0, '/home/claude/uaz')
import sky_kit as SK
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
sh.show_backface_culling = False
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_render = True
for m in bpy.data.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
D = SK.DISPLAY
V = {   # name: eye offset, target offset (from the root), root, lens, res
    'chiller': ((5.5, -7.0, 4.0), (0.0, 0.0, 0.8), 'SkyChiller', 24, (1400, 900)),
    'chiller_b': ((-5.0, 6.0, 3.5), (0.0, 0.0, 0.8), 'SkyChiller', 24, (1400, 900)),
    'chiller_belt': ((-2.6, -1.4, 1.6), (-0.9, 0.2, 0.8), 'SkyChiller', 24, (1200, 900)),
    'sprayer': ((5.0, -7.0, 4.5), (0.0, 0.0, 2.6), 'SkySprayer', 24, (1200, 1000)),
    'sprayer_top': ((2.5, -2.5, 6.0), (0.0, 0.0, 2.8), 'SkySprayer', 24, (1200, 900)),
    'ballast': ((7.0, -7.0, 5.0), (0.0, 2.5, 0.0), 'SkyBallast', 24, (1400, 900)),
    'ballast_pit': ((0.0, -4.0, 1.5), (0.0, 3.0, -0.6), 'SkyBallast', 20, (1200, 900)),
    'altimeter': ((4.0, -12.0, 5.0), (0.0, 0.0, 6.0), 'SkyAltimeter', 28, (1000, 1200)),
    'walks': ((-4.0, -6.0, 4.0), (7.0, 3.0, -1.0), 'SkyWalk_Landing', 22, (1600, 900)),
    'walk_s': ((2.5, -2.0, 1.4), (0.0, 2.0, -0.2), 'SkyWalk_Straight', 24, (1200, 900)),
    'walk_under': ((2.5, -1.5, -2.5), (0.0, 2.0, 0.0), 'SkyWalk_Straight', 24, (1200, 900)),
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
