"""Cycles previews of out/devices.blend: the desk things on a desk top, the tape recorder with its door open and a tape in,
the drop box and the weather screen outdoors (the screen's door open), the instruments close up.
python3 -I devices_render.py <views|all> [spp] -> rend/devices/<view>.png"""
import sys, os, math
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector, Matrix
import psxlib as P
import devices_kit as DK

HERE = P.HERE
OUT = os.path.join(HERE, 'rend', 'devices')
os.makedirs(OUT, exist_ok=True)
want = sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] != 'all' else None
spp = int(sys.argv[2]) if len(sys.argv) > 2 else 32
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'devices.blend'))
sc = bpy.context.scene
O = bpy.data.objects
for o in O:
    if o.name.startswith('COL_'):
        o.hide_render = True
for m in bpy.data.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
D = {r: Vector(v) for r, v in DK.DISPLAY.items()}


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


desk = plane('Desk', (-2.6, -0.8), (1.3, 0.7), -0.0015, (0.16, 0.11, 0.065), 0.7)        # a varnished desk top
back = plane('Module', (-0.6, -0.25), (0.6, 0.25), 0.0, (0.045, 0.05, 0.055), 0.6)        # the cabinet module behind the recorder
back.matrix_world = Matrix.Translation(DK.DISPLAY['TapeDeck'] + Vector((0, 0.0005, 0))) @ Matrix.Rotation(math.pi / 2, 4, 'X')
snow = plane('Ground', (1.2, -3.0), (6.0, 6.0), -0.0015, (0.62, 0.64, 0.68), 0.9)        # snow round the outdoor things
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.angle = math.radians(4.0)
sc.collection.objects.link(sun)
lamp = bpy.data.objects.new('lamp', bpy.data.lights.new('lamp', 'AREA'))
lamp.data.size = 0.6
lamp.data.color = (1.0, 0.86, 0.68)
sc.collection.objects.link(lamp)
P.setup_cycles((1000, 700), spp)
sc.cycles.max_bounces = 4
w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes['Background']
# a tape in the recorder for its view (a copy of the Cassette at Slot_Tape: +z to the front, the tape edge down)
cas = O['Cassette']
tape = cas.copy()
tape.data = cas.data
tape.parent = None
sc.collection.objects.link(tape)
import json
C = json.load(open(os.path.join(HERE, 'out', 'devices_contract.json')))
slot = Vector(C['sockets']['Slot_Tape']['pos'])
R = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))                  # columns: cassette x -> x, y -> z (the tape edge -y down), z -> -y
tape.matrix_world = Matrix.Translation(slot + D['TapeDeck']) @ R.to_4x4()
tape.hide_render = True
LID, TDOOR, SDOOR = O['IX_LaptopLid'], O['IX_TapeDoor'], O['IX_ScreenDoor']


def show(roots, extra=()):
    keep = set()
    for r in roots:
        for o in bpy.data.collections[r].all_objects:
            keep.add(o.name)
    if 'ObjectPC' in roots:
        keep.add('Monitor_PC')
    for o in O:
        if o.library is not None or o in (cam, sun, lamp, desk, snow, tape, back):
            continue
        if o.type in ('MESH', 'EMPTY'):
            o.hide_render = o.name.startswith('COL_') or o.name not in keep
    tape.hide_render = 'tape' not in extra


def look(e, t, lens):
    cam.location = Vector(e)
    cam.rotation_euler = (Vector(t) - Vector(e)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.01


def light(kind):
    """desk: a warm lamp over the desk, a dim cool room; out: overcast winter daylight"""
    desk.hide_render = kind != 'desk'
    back.hide_render = True
    snow.hide_render = kind != 'out'
    lamp.hide_render = kind != 'desk'
    if kind == 'desk':
        bg.inputs[0].default_value = (0.20, 0.22, 0.26, 1)
        bg.inputs[1].default_value = 0.6
        sun.data.energy = 0.0
        sun.hide_render = True
    else:
        bg.inputs[0].default_value = (0.56, 0.61, 0.70, 1)
        bg.inputs[1].default_value = 1.0
        sun.hide_render = False
        sun.data.energy = 2.2
        sun.rotation_euler = (math.radians(55), 0, math.radians(35))


V = {   # name: roots, light, eye, target, lens, (lid, tape door, screen door), extra, exposure
    'fax': (['Fax', 'FaxPaper'], 'desk', D['Fax'] + Vector((0.50, -0.78, 0.52)), D['Fax'] + Vector((0.20, -0.02, 0.03)), 34,
            (0, 0, 0), (), 0.0),
    'pc': (['ObjectPC'], 'desk', D['ObjectPC'] + Vector((0.75, -1.20, 0.80)), D['ObjectPC'] + Vector((0.06, -0.12, 0.20)), 32,
           (0, 0, 0), (), 0.0),
    'laptop': (['Laptop'], 'desk', D['Laptop'] + Vector((0.38, -0.55, 0.36)), D['Laptop'] + Vector((0.0, 0.02, 0.09)), 34,
               (105, 0, 0), (), 0.0),
    'tapes': (['Cassette', 'CassetteBox'], 'desk', D['Cassette'] + Vector((0.22, -0.34, 0.30)),
              D['Cassette'] + Vector((0.0, 0.09, 0.025)), 36, (0, 0, 0), (), 0.0),
    'deck': (['TapeDeck'], 'desk', D['TapeDeck'] + Vector((0.20, -1.05, 0.22)), D['TapeDeck'] + Vector((0.0, 0.0, 0.0)), 36,
             (0, 30, 0), ('tape',), 0.3),
    'dropbox': (['DropBox'], 'out', D['DropBox'] + Vector((1.25, -1.95, 1.55)), D['DropBox'] + Vector((0.0, 0.0, 0.85)), 30,
                (0, 0, 0), (), 0.0),
    'screen': (['MeteoScreen'], 'out', D['MeteoScreen'] + Vector((1.35, -2.40, 1.75)), D['MeteoScreen'] + Vector((0.0, 0.0, 1.1)),
               30, (0, 0, 105), (), 0.0),
    'screen_in': (['MeteoScreen'], 'out', D['MeteoScreen'] + Vector((0.10, -0.78, 1.62)),
                  D['MeteoScreen'] + Vector((-0.02, 0.05, 1.45)), 28, (0, 0, 105), (), 0.4),
}
for nm, (roots, lk, e, t, lens, (lid, td, sd), extra, ev) in V.items():
    if want and nm not in want:
        continue
    show(roots, extra)
    light(lk)
    if lk == 'desk':
        c = Vector(t)
        lamp.location = c + Vector((-0.5, -0.4, 1.4))
        lamp.rotation_euler = (c - lamp.location).to_track_quat('-Z', 'Y').to_euler()
        lamp.data.energy = 60.0 if nm != 'deck' else 90.0
    if nm == 'deck':
        back.hide_render = False
        desk.hide_render = True
    LID.rotation_euler = (math.radians(-lid), 0, 0)
    TDOOR.rotation_euler = (math.radians(td), 0, 0)
    SDOOR.rotation_euler = (0, 0, math.radians(-sd))
    sc.view_settings.exposure = ev
    look(e, t, lens)
    P.render(os.path.join(OUT, nm + '.png'))
    print('rendered', nm, flush=True)
