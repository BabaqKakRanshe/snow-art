"""workbench views of out/sc[_draft].blend for checking: blender -b --python pl_quick.py -- <blend> <out_dir> [views,...]"""
import bpy, sys, os
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
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -0.002))
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
V = {
    'front34': ((-3.6, -5.2, 2.0), (0.0, -0.2, 0.9), 35, (1400, 900)),
    'rear34': ((3.8, 5.0, 2.2), (0.0, 0.3, 0.9), 35, (1400, 900)),
    'side': ((-7.5, 0.0, 1.1), (0.0, 0.0, 0.9), 35, (1600, 800)),
    'bay': ((0.9, -3.0, 2.2), (0.3, -1.6, 0.7), 35, (1200, 900)),
    'top': ((0.0, 0.0, 9.0), (0.0, 0.001, 0.0), 35, (900, 1200)),
}
for nm, (e, t, lens, res) in V.items():
    if want and nm not in want:
        continue
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = Vector(e)
    cam.rotation_euler = (Vector(t) - Vector(e)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.02
    sc.render.filepath = os.path.join(OUT, nm + '.png')
    bpy.ops.render.render(write_still=True)
print('ok')
