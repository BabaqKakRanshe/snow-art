"""workbench views of out/net[_draft].blend for checking: blender -b --python net_quick.py -- <blend> <out_dir> [views,...]"""
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
    if o.name.startswith(('COL_', 'Glow_')):
        o.hide_render = True
for m in bpy.data.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.002))
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
PO, CU, ST = Vector((-3.0, 0.0, 0.0)), Vector((2.0, 0.0, 0.0)), Vector((-2.0, -3.0, 0.0))
V = {
    'all': ((0.0, -9.0, 3.2), (0.0, -1.0, 0.6), 30, (1600, 900)),
    'pole': (PO + Vector((0.9, -2.6, 1.3)), PO + Vector((0, 0, 1.0)), 35, (700, 1000)),
    'culvert': (CU + Vector((1.8, -4.2, 1.6)), CU + Vector((0, 0, 0.5)), 30, (1200, 900)),
    'culvert_in': (CU + Vector((0.0, -2.2, 0.55)), CU + Vector((0, 1.0, 0.5)), 30, (1000, 800)),
    'stones': (ST + Vector((2.1, -2.2, 0.9)), ST + Vector((2.1, 0, 0.45)), 30, (1600, 700)),
    'stone_close': (ST + Vector((0.0, -0.9, 0.55)), ST + Vector((0, 0, 0.45)), 30, (800, 900)),
    'pointers': (Vector((-3.0, -0.6, 1.9)), Vector((-3.0, 3.0, 1.7)), 30, (1400, 700)),
    'stones_front': (ST + Vector((2.1, -4.2, 0.5)), ST + Vector((2.1, 0, 0.4)), 50, (1800, 600)),
    'schranke': (Vector((3.0, 8.0, 0.0)) + Vector((1.0, -6.0, 1.5)), Vector((3.0, 8.0, 0.7)), 35, (1400, 800)),
    'stake': (Vector((6.5, 6.0, 0.0)) + Vector((0.9, -1.6, 1.2)), Vector((6.7, 6.0, 0.8)), 35, (800, 900)),
    'graves': (Vector((9.5, 6.0, 0.0)) + Vector((0.6, -4.0, 1.4)), Vector((9.5, 6.0, 0.5)), 35, (1200, 800)),
    'camp': (Vector((15.5, 6.0, 0.0)) + Vector((0.5, -5.0, 2.2)), Vector((15.5, 6.0, 0.4)), 35, (1200, 800)),
    'ladder': (Vector((21.5, 6.0, 0.0)) + Vector((0.5, -9.0, 3.5)), Vector((21.5, 6.0, 3.0)), 35, (1000, 1000)),
    'hut': (Vector((27.0, 6.0, 0.0)) + Vector((2.5, -6.0, 2.2)), Vector((27.0, 6.0, 1.2)), 35, (1000, 800)),
    'abatis': (Vector((33.0, 6.0, 0.0)) + Vector((1.0, -6.0, 2.0)), Vector((33.0, 6.5, 0.6)), 35, (1200, 700)),
    'portal': (Vector((40.0, 6.0, 0.0)) + Vector((1.5, -6.5, 2.0)), Vector((40.0, 6.0, 1.3)), 35, (1000, 800)),
    'schranke_board': (Vector((3.0, 8.0, 0.0)) + Vector((-0.9, -1.6, 0.8)), Vector((2.1, 8.0, 0.7)), 35, (1000, 600)),
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
