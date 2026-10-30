"""workbench views of out/smoke[_draft].blend for checking (the pager's pager_quick, the forest_smoke layout):
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_smoke/smoke2_quick.py <blend> <out_dir> [views,...]
Views: line (all, three-quarter), front (the packs and the lighter face on), back3q, lighter, cig, open (the lids opened 100
degrees, the flame shown)."""
import bpy, sys, os, math
from mathutils import Vector
a = sys.argv[1:]
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
O = bpy.data.objects
V = {   # name: eye, target, lens, res
    'line': ((0.16, -0.36, 0.20), (0.08, 0.0, 0.035), 40, (1400, 800)),
    'front': ((0.04, -0.42, 0.045), (0.04, 0.0, 0.045), 50, (1400, 700)),
    'back3q': ((-0.06, 0.34, 0.18), (0.06, 0.0, 0.035), 40, (1400, 800)),
    'lighter': ((0.22, -0.13, 0.10), (0.17, 0.0, 0.04), 50, (900, 900)),
    'cig': ((0.29, -0.09, 0.05), (0.24, -0.02, 0.004), 50, (1000, 700)),
    'open': ((0.02, -0.26, 0.24), (0.0, 0.0, 0.07), 40, (1400, 800)),
}
for nm, (e, t, lens, res) in V.items():
    if want and nm not in want:
        continue
    for o in O:
        if o.name.startswith('Pack_Lid_'):
            o.rotation_euler = (0, 0, 0) if nm != 'open' else (-math.radians(100), 0, 0)
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = Vector(e)
    cam.rotation_euler = (Vector(t) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.005
    sc.render.filepath = os.path.join(OUT, nm + '.png')
    bpy.ops.render.render(write_still=True)
print('ok')
