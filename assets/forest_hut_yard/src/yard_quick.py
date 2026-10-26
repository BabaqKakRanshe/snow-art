"""workbench views of out/yard[_draft].blend for checking: python3 -I yard_quick.py -- <blend> <out_dir> [views,...]"""
import bpy, sys, os, math
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
    if o.name.startswith(('COL_', 'Glow_')):
        o.hide_render = True
for m in bpy.data.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, -0.001))
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
SI, OH, FE, PO, PL, MP = Vector((-8, 0, 0)), Vector((-5.5, 0, 0)), Vector((-2.6, 0, 0)), Vector((1.0, 0.8, 0)), Vector((6.6, 0, 0)), Vector((10, 0, 0))
V = {
    'all': ((1.0, -17.0, 7.0), (1.0, 0.0, 0.8), 26, (1800, 800)),
    'outhouse_fr': (OH + Vector((1.9, -3.2, 1.7)), OH + Vector((0.0, 0, 1.05)), 30, (1000, 1000)),
    'outhouse_in': (OH + Vector((0.0, -1.6, 1.5)), OH + Vector((0.0, 0.3, 0.6)), 24, (1000, 1000)),
    'feeder': (FE + Vector((2.4, -2.8, 1.9)), FE + Vector((0.0, 0, 1.0)), 30, (1000, 1000)),
    'porch': (PO + Vector((2.4, -4.2, 2.0)), PO + Vector((0.0, -0.6, 1.0)), 30, (1000, 1000)),
    'polter': (PL + Vector((-4.8, -3.6, 1.8)), PL + Vector((-1.0, 0, 0.5)), 30, (1200, 900)),
    'sign': (SI + Vector((0.6, -2.4, 1.8)), SI + Vector((0.35, 0, 1.75)), 30, (1000, 1000)),
    'map': (MP + Vector((0.0, -0.25, 0.55)), MP + Vector((0, 0, 0)), 30, (1000, 800)),
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
