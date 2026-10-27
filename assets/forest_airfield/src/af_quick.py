"""workbench views of out/af[_draft].blend for checking: blender -b --python af_quick.py -- <blend> <out_dir> [views,...]"""
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
bpy.ops.mesh.primitive_plane_add(size=160, location=(0, 0, -0.002))
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
EL, TL, MK, SG, PG = Vector((-8, -6, 0)), Vector((-6, -6, 0)), Vector((-4, -6, 0)), Vector((-1.5, -6, 0)), Vector((8, -4, 0))
V = {
    'runway_top': ((0.0, 14.0, 70.0), (0.0, 14.0, 0.0), 30, (1800, 500)),
    'runway_low': ((0.0, -6.0, 3.0), (0.0, 14.0, 0.0), 26, (1800, 700)),
    'slab_close': ((-22.0, 6.0, 1.7), (-22.0, 12.0, 0.0), 40, (1200, 800)),
    'num17': ((22.0, 2.0, 6.0), (22.0, 14.0, 0.0), 40, (1000, 800)),
    'props': ((-4.5, -9.5, 1.4), (-4.5, -6.0, 0.5), 30, (1400, 800)),
    'light': (EL + Vector((0.5, -0.9, 0.55)), EL + Vector((0, 0, 0.22)), 40, (900, 900)),
    'sign': (SG + Vector((0.6, -2.4, 1.8)), SG + Vector((0.35, 0, 1.72)), 30, (1000, 800)),
    'plug': (PG + Vector((0.0, -5.5, 2.3)), PG + Vector((0.0, 0.0, 2.2)), 30, (1000, 1000)),
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
