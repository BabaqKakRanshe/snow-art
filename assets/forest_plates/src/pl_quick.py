"""workbench views of out/pl[_draft].blend for checking: blender -b --python pl_quick.py -- <blend> <out_dir> [views,...]"""
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
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -0.002))
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
NS, GS, HK, MB = Vector((-1.6, 0, 1.2)), Vector((-0.9, 0, 1.2)), Vector((0.1, 0, 1.2)), Vector((1.6, 0, 0))
V = {
    'all': ((0.0, -6.5, 2.2), (0.0, 0.0, 1.1), 35, (1600, 900)),
    'plates': ((-0.8, -2.2, 1.35), (-0.8, 0.0, 1.2), 35, (1400, 700)),
    'board': (MB + Vector((0.5, -2.6, 1.6)), MB + Vector((0.0, 0.0, 1.35)), 35, (1000, 1100)),
    'board_back': (MB + Vector((-1.2, 2.4, 1.8)), MB + Vector((0.0, 0.0, 1.2)), 35, (1000, 900)),
    'tag': (NS + Vector((0.1, -0.6, 0.05)), NS, 40, (900, 500)),
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
