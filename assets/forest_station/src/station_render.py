"""Cycles previews of out/station.blend (the golden sample's setup, lib start_render: day world (0.56, 0.62, 0.72) 0.85 + sun 3.0,
Standard view, 1100 x 700, 24 spp, denoise): the rack with its nine monitors and empty, a post up close, the table with the
object computer, both with a 1.8 m figure, a room-like view against a Leitstand wall (cream plaster over a brown dado, blue
carpet) lit by a ceiling lamp, and a 320 x 240 frame (the game's lines).
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_station/station_render.py [views|all] [spp]
-> rend/station/<view>.png"""
import sys, os, math
import bpy
from mathutils import Vector, Euler
import psxlib as P
import station_view as SV

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'rend', 'station')
os.makedirs(OUT, exist_ok=True)
want = sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] != 'all' else None
spp = int(sys.argv[2]) if len(sys.argv) > 2 else 24
SV.open_built(os.path.join(HERE, 'out', 'station.blend'))
sc = bpy.context.scene
prev = SV.furnish()
fig = SV.figure((-1.10, -0.95))
O = bpy.data.objects
for o in O:
    if o.type == 'EMPTY' and o.name.startswith('Slot_'):
        o.hide_render = True


def plane(name, pts, rgb, rough=0.95):
    me = bpy.data.meshes.new(name)
    me.from_pydata(pts, [], [tuple(range(len(pts)))])
    ob = bpy.data.objects.new(name, me)
    m = bpy.data.materials.new('M_' + name)
    m.use_nodes = True
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Base Color'].default_value = (*rgb, 1)
    pb.inputs['Roughness'].default_value = rough
    me.materials.append(m)
    sc.collection.objects.link(ob)
    return ob


ground = plane('Ground', [(-40, -40, -0.002), (40, -40, -0.002), (40, 40, -0.002), (-40, 40, -0.002)], (0.055, 0.050, 0.038))
# the room set (only for 'room'): carpet, the wall behind the rack with a dado, a ceiling lamp
lin = lambda *c: tuple((v / 255.0) ** 2.2 for v in c)
room = [plane('Carpet', [(-3, -4, -0.001), (3, -4, -0.001), (3, 0.0, -0.001), (-3, 0.0, -0.001)], lin(52, 60, 82)),
        plane('Wall', [(-3, 0.002, 0), (-3, 0.002, 2.8), (3, 0.002, 2.8), (3, 0.002, 0)], lin(206, 198, 172)),
        plane('Dado', [(-3, 0.0015, 0), (-3, 0.0015, 1.15), (3, 0.0015, 1.15), (3, 0.0015, 0)], lin(138, 100, 62))]
lamp = bpy.data.objects.new('ceiling', bpy.data.lights.new('ceiling', 'AREA'))
lamp.data.size, lamp.data.size_y, lamp.data.shape = 1.2, 0.3, 'RECTANGLE'
lamp.data.color = (1.0, 0.95, 0.86)
lamp.data.energy = 120.0
lamp.location = (0.5, -1.6, 2.75)
sc.collection.objects.link(lamp)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.angle = math.radians(3.0)
sc.collection.objects.link(sun)
T = Vector((1.45, -0.26, 0.0))
VIEWS = {   # name: eye, target, lens, room, monitors+pc shown, res
    'rack': (Vector((1.9, -3.1, 1.65)), Vector((0.0, -0.26, 0.90)), 30, False, True, (1100, 700)),
    'rack_empty': (Vector((-0.35, -3.4, 1.5)), Vector((0.1, -0.26, 0.85)), 30, False, False, (1100, 700)),
    'post': (Vector((1.05, -1.05, 1.20)), Vector((0.62, -0.52, 1.02)), 35, False, True, (1100, 700)),
    'table': (T + Vector((1.25, -1.55, 1.45)), T + Vector((0.0, 0.0, 0.62)), 32, False, True, (1100, 700)),
    'both': (Vector((3.0, -4.6, 1.75)), Vector((0.55, -0.35, 0.85)), 30, False, True, (1100, 700)),
    'room': (Vector((0.9, -2.6, 1.62)), Vector((0.0, -0.3, 1.05)), 28, True, True, (1100, 700)),
    'game': (Vector((0.6, -2.2, 1.62)), Vector((0.0, -0.3, 1.0)), 30, True, True, (320, 240)),
}
P.setup_cycles((1100, 700), spp)
sc.cycles.max_bounces = 4
for nm, (e, t, lens, rm, furn, resl) in VIEWS.items():
    if want and nm not in want:
        continue
    sc.render.resolution_x, sc.render.resolution_y = resl
    for o in room:
        o.hide_render = not rm
    ground.hide_render = rm
    lamp.hide_render = not rm
    for o in prev:
        o.hide_render = not furn
    for o in fig:
        o.hide_render = rm
    tb = O['Station_SideTable']
    tb.hide_render = rm
    if 'prev_PC' in O:
        O['prev_PC'].hide_render = rm or not furn
        O['prev_PC_Mon'].hide_render = rm or not furn
    if rm:
        bg.inputs['Color'].default_value = (0.04, 0.045, 0.06, 1)
        bg.inputs['Strength'].default_value = 0.5
        sun.hide_render = True
    else:
        bg.inputs['Color'].default_value = (0.56, 0.62, 0.72, 1)
        bg.inputs['Strength'].default_value = 0.85
        sun.hide_render = False
        sun.data.energy = 3.0
        sun.rotation_euler = Euler((math.radians(52), 0, math.radians(35)))
    cam.location = e
    cam.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.03
    P.render(os.path.join(OUT, nm + '.png'))
    print('rendered', nm, flush=True)
