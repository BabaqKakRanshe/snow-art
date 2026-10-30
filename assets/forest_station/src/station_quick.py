"""workbench views of out/station[_draft].blend for checking (adapted from forest_pager's pager_quick):
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_station/station_quick.py <blend> <out_dir> [views,...] [empty]
'empty': without the preview monitors / computer"""
import bpy, sys, os
from mathutils import Vector
import station_view as SV

a = sys.argv[1:]
SV.open_built(a[0])
OUT = a[1]
want = a[2].split(',') if len(a) > 2 and a[2] != 'all' else None
os.makedirs(OUT, exist_ok=True)
if 'empty' not in a:
    SV.furnish()
SV.figure((-1.05, -0.9))
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'TEXTURE' if 'draft' not in a[0] else 'MATERIAL'
sh.show_cavity = True
sh.cavity_type = 'BOTH'
bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.0005))
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
T = Vector((1.45, -0.26, 0.0))                     # the table's display offset
V = {   # name: eye, target, lens, res
    'rack_front': ((0.0, -3.2, 1.0), (0.0, -0.26, 0.92), 35, (900, 1000)),
    'rack_3q': ((1.7, -2.4, 1.6), (0.0, -0.26, 0.90), 32, (1000, 900)),
    'rack_back3q': ((-1.6, 1.9, 1.5), (0.0, -0.26, 0.90), 32, (1000, 900)),
    'rack_post': ((0.95, -1.0, 1.15), (0.6, -0.5, 1.0), 40, (900, 900)),
    'rack_low': ((0.5, -1.6, 0.35), (0.0, -0.26, 0.45), 30, (1000, 800)),
    'table_3q': (tuple(T + Vector((1.1, -1.4, 1.5))), tuple(T + Vector((0, 0, 0.55))), 35, (1000, 800)),
    'table_low': (tuple(T + Vector((0.9, -1.2, 0.35))), tuple(T + Vector((0, 0, 0.45))), 35, (1000, 800)),
    'both': ((2.6, -4.2, 1.7), (0.6, -0.3, 0.85), 30, (1100, 700)),
}
for nm, (e, t, lens, res) in V.items():
    if want and nm not in want:
        continue
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = Vector(e)
    cam.rotation_euler = (Vector(t) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.01
    sc.render.filepath = os.path.join(OUT, nm + '.png')
    bpy.ops.render.render(write_still=True)
print('ok')
