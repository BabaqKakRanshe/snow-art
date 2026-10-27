"""workbench views of out/pager[_draft].blend for checking (adapted from forest_gear's gear_quick):
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_pager/pager_quick.py -- <blend> <out_dir> [views,...]"""
import bpy, sys, os, math
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
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
bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, -0.0005))
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
V = {   # name: eye, target, lens, res
    'front': ((0.0, -0.30, 0.028), (0.0, 0.0, 0.028), 50, (1000, 760)),
    'front3q': ((0.13, -0.22, 0.11), (0.0, 0.0, 0.026), 45, (1000, 800)),
    'back3q': ((-0.14, 0.20, 0.12), (0.0, 0.0, 0.026), 45, (1000, 800)),
    'side': ((0.26, -0.02, 0.05), (0.0, 0.0, 0.028), 50, (900, 800)),
    'top': ((0.02, -0.06, 0.26), (0.0, 0.0, 0.03), 50, (1000, 760)),
    'hand': ((-0.05, -0.20, 0.13), (0.0, 0.0, 0.03), 40, (1000, 800)),
}
for nm, (e, t, lens, res) in V.items():
    if want and nm not in want:
        continue
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = Vector(e)
    cam.rotation_euler = (Vector(t) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.005
    sc.render.filepath = os.path.join(OUT, nm + '.png')
    bpy.ops.render.render(write_still=True)
print('ok')
