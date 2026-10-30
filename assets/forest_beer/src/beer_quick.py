"""workbench views of out/beer[_draft].blend for checking (the smoke pack's smoke2_quick, the forest_beer layout):
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_beer/beer_quick.py <blend> <out_dir> [views,...]
Views: line (all twelve, three-quarter), front (the six cans face on), back (their backs), lid (one lid close), open (the
cans opened: tab 12, flap 82), lever (one can at the tab's top: tab 70, flap 82), crushed (the crushed row)."""
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
sh.color_type = 'TEXTURE'
sh.show_cavity = True
sh.cavity_type = 'BOTH'
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_render = True
    if o.animation_data:
        o.animation_data.action = None                                  # the views set the hinges themselves
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
V = {   # name: eye, target, lens, res, (tab, flap)
    'line': ((0.10, -0.72, 0.38), (0.0, 0.06, 0.06), 40, (1500, 900), (0, 0)),
    'front': ((0.0, -0.95, 0.09), (0.0, 0.0, 0.08), 50, (1600, 700), (0, 0)),
    'back': ((0.0, 0.95, 0.09), (0.0, 0.0, 0.08), 50, (1600, 700), (0, 0)),
    'lid': ((0.0, -0.09, 0.30), (0.0, 0.0, 0.165), 50, (900, 900), (0, 0)),
    'open': ((0.05, -0.50, 0.48), (0.0, 0.0, 0.12), 45, (1500, 900), (12, 82)),
    'lever': ((0.07, -0.12, 0.26), (0.0, -0.004, 0.168), 50, (900, 900), (70, 82)),
    'crushed': ((0.0, 0.74, 0.34), (0.0, 0.13, 0.025), 40, (1500, 800), (0, 0)),
}
for nm, (e, t, lens, res, (tab, flap)) in V.items():
    if want and nm not in want:
        continue
    for o in O:
        if o.name.startswith('Can_Tab_'):
            o.rotation_euler = (math.radians(tab), 0, 0)
        if o.name.startswith('Can_Flap_'):
            o.rotation_euler = (math.radians(flap), 0, 0)
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = Vector(e)
    cam.rotation_euler = (Vector(t) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.005
    sc.render.filepath = os.path.join(OUT, nm + '.png')
    bpy.ops.render.render(write_still=True)
print('ok')
