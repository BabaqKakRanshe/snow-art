"""Cycles previews of out/pager.blend (adapted from forest_gear's gear_render): on the desk by day (as the walkie's view) and
at night with the screen and the LED lit.
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_pager/pager_render.py [views|all] [spp]
-> rend/pager/<view>.png"""
import sys, os, math
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'rend', 'pager')
os.makedirs(OUT, exist_ok=True)
want = sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] != 'all' else None
spp = int(sys.argv[2]) if len(sys.argv) > 2 else 48
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'pager.blend'))
sc = bpy.context.scene
O, M = bpy.data.objects, bpy.data.materials
for o in O:
    if o.name.startswith('COL_'):
        o.hide_render = True
for m in M:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'


def plane(name, lo, hi, z, rgb, rough):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(lo[0], lo[1], z), (hi[0], lo[1], z), (hi[0], hi[1], z), (lo[0], hi[1], z)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new(name, me)
    m = bpy.data.materials.new('M_' + name)
    m.use_nodes = True
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Base Color'].default_value = (*rgb, 1)
    pb.inputs['Roughness'].default_value = rough
    me.materials.append(m)
    sc.collection.objects.link(ob)
    return ob


plane('Desk', (-0.4, -0.4), (0.4, 0.4), -0.0015, (0.16, 0.11, 0.065), 0.7)          # a varnished desk top, as the walkie's
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.angle = math.radians(4.0)
sc.collection.objects.link(sun)
lamp = bpy.data.objects.new('lamp', bpy.data.lights.new('lamp', 'AREA'))
lamp.data.size = 0.4
lamp.data.color = (1.0, 0.86, 0.68)
sc.collection.objects.link(lamp)
try:
    sc.render.engine = 'CYCLES'
except TypeError:
    pass
sc.cycles.samples = spp
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1000, 800
sc.view_settings.view_transform = 'Standard'
world = bpy.data.worlds.new('w')
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
sc.world = world
lcd, led = O.get('Pager_LCD'), O.get('Pager_LED')
V = {   # name: eye, target, sun (strength, rot), lamp (energy, pos), world, lit
    'desk': ((0.12, -0.24, 0.17), (0.0, 0.0, 0.026), (2.5, (math.radians(50), 0, math.radians(30))), (6.0, (0.3, -0.3, 0.5)),
             (0.35, 0.36, 0.38), False),
    'night': ((-0.04, -0.20, 0.10), (0.0, 0.0, 0.03), (0.02, (math.radians(60), 0, math.radians(-40))), (0.15, (0.4, 0.2, 0.6)),
              (0.004, 0.005, 0.008), True),
}
for nm, (e, t, (ss, sr), (le, lp), wc, lit) in V.items():
    if want and nm not in want:
        continue
    cam.location = Vector(e)
    cam.rotation_euler = (Vector(t) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 50
    cam.data.clip_start = 0.005
    sun.data.energy, sun.rotation_euler = ss, sr
    lamp.data.energy, lamp.location = le, Vector(lp)
    lamp.rotation_euler = (Vector((0, 0, 0.03)) - lamp.location).to_track_quat('-Z', 'Y').to_euler()
    bg.inputs['Color'].default_value = (*wc, 1)
    if lcd:
        lcd.data.materials[0] = M['M_Pager_LCD'] if lit else M['M_Pager_LCD_Off']
    if led:
        led.data.materials[0] = M['M_Pager_LEDR'] if lit else M['M_Pager_LED_Off']
    sc.render.filepath = os.path.join(OUT, nm + '.png')
    bpy.ops.render.render(write_still=True)
print('ok')
