"""Cycles preview of the old spare van: python3 -I vanold_render.py <vanold.blend> <out.png> [spp]"""
import sys, os, math
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector
import psxlib as P
a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
spp = int(a[2]) if len(a) > 2 else 32
sc = bpy.context.scene
for o in bpy.data.objects:
    if o.name.startswith(('COL_', 'LIGHT_', 'Snow_')) or o.name in ('StoveGlow',):
        o.hide_render = True
for m in bpy.data.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
me = bpy.data.meshes.new('G')
me.from_pydata([(-30, -30, 0.0), (30, -30, 0.0), (30, 30, 0.0), (-30, 30, 0.0)], [], [(0, 1, 2, 3)])
g = bpy.data.objects.new('G', me)
m = bpy.data.materials.new('M_G')
m.use_nodes = True
pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
pb.inputs['Base Color'].default_value = (0.62, 0.64, 0.68, 1)
pb.inputs['Roughness'].default_value = 0.9
me.materials.append(m)
sc.collection.objects.link(g)
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.angle = math.radians(4.0)
sun.data.energy = 2.4
sun.rotation_euler = (math.radians(55), 0, math.radians(40))
sc.collection.objects.link(sun)
w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.56, 0.61, 0.70, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.location = Vector((6.2, -4.6, 2.1))
cam.rotation_euler = (Vector((0.2, 0.0, 1.0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = 32
P.setup_cycles((1100, 750), spp)
sc.cycles.max_bounces = 5
P.render(a[1])
print('rendered', a[1])
