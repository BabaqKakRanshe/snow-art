"""Cycles previews of out/parts.blend: the dosing pump on the store floor and installed in forest_far's pump house (its
placement, the hose on the house pipe), the sodium lamp lit beside its carton, the radar tube standing and lying with its
face up, the relay unit's front (LEDs on, the fuse cap off with a burnt fuse) and back, the generator on snow, the lake
sensor at the shore and its open box with a 4R25 in it.
python3 -I parts_render.py <views|all> [spp] -> rend/parts/<view>.png
(the pump house comes from ../forest_far/far.blend, the 4R25 from ../forest_gear/gear.blend - here out/forest_far, out/gear)"""
import sys, os, math, json
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector, Matrix
import psxlib as P
import parts_kit as PK

HERE = P.HERE
OUT = os.path.join(HERE, 'rend', 'parts')
FAR = '/home/claude/far/out/forest_far/far.blend'
GEAR = os.path.join(HERE, 'out', 'gear.blend')
os.makedirs(OUT, exist_ok=True)
want = sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] != 'all' else None
spp = int(sys.argv[2]) if len(sys.argv) > 2 else 32
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'parts.blend'))
C = json.load(open(os.path.join(HERE, 'out', 'parts_contract.json')))
sc = bpy.context.scene
O, Mt = bpy.data.objects, bpy.data.materials
for o in O:
    if o.name.startswith('COL_'):
        o.hide_render = True
D = {r: Vector(v) for r, v in PK.DISPLAY.items()}


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


floor = plane('Floor', (-2.2, -2.0), (2.0, 1.4), -0.0015, (0.22, 0.21, 0.20), 0.85)          # concrete store floor
desk = plane('Desk', (-1.8, -0.6), (-0.6, 0.6), -0.0012, (0.16, 0.11, 0.065), 0.7)
snow = plane('Snow', (-1.0, -3.5), (5.0, 3.0), -0.0018, (0.62, 0.64, 0.68), 0.9)
ice = plane('Ice', (1.4, -3.5), (3.8, D['LakeSensor'].y - 1.25), 0.0, (0.30, 0.36, 0.42), 0.25)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.angle = math.radians(4.0)
sc.collection.objects.link(sun)
lamp = bpy.data.objects.new('lamp', bpy.data.lights.new('lamp', 'AREA'))
lamp.data.size = 0.8
lamp.data.color = (1.0, 0.90, 0.76)
sc.collection.objects.link(lamp)
bulb = bpy.data.objects.new('bulb', bpy.data.lights.new('bulb', 'POINT'))
bulb.data.color = (1.0, 0.62, 0.25)
bulb.data.shadow_soft_size = 0.02
sc.collection.objects.link(bulb)
P.setup_cycles((1000, 700), spp)
sc.cycles.max_bounces = 5
w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes['Background']
EXTRA = []


def tag(objs, t):
    for o in objs:
        o['view'] = t
        EXTRA.append(o)


def copy_root(root, M4, t):
    src = [o for o in bpy.data.collections[root].all_objects if not o.name.startswith('COL_')]
    base = Matrix.Translation(D[root])
    mp = {}
    for o in src:
        c = o.copy()
        sc.collection.objects.link(c)
        mp[o] = c
    for o, c in mp.items():
        if o.parent in mp:
            c.parent = mp[o.parent]
            c.matrix_parent_inverse = o.matrix_parent_inverse.copy()     # (setting .parent resets it)
        else:
            c.parent = None
            c.matrix_world = M4 @ base.inverted() @ o.matrix_world
    tag(mp.values(), t)
    return mp


def append(path, names):
    """objects appended from another package's blend, its textures resolved next to it"""
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in names if n in src.objects]
    d = os.path.dirname(path)
    for im in bpy.data.images:
        if im.filepath.startswith('//tex/') and not os.path.exists(bpy.path.abspath(im.filepath)):
            im.filepath = os.path.join(d, 'tex', os.path.basename(im.filepath))
    out = []
    for o in dst.objects:
        if o is None:
            continue
        sc.collection.objects.link(o)
        out.append(o)
    return out


# the pump house round the installed pump: its frame placed so that the pump stands at its placement
ph = append(FAR, ['PumpHouse', 'IX_PumpDoor_7'])
house = next(o for o in ph if o.name.startswith('PumpHouse'))
place = C['placements']['Item_DosingPump'][0]
house.matrix_world = Matrix.Translation(D['Item_DosingPump'] - Vector(place['pos']))      # its door follows (parented)
tag(ph, 'pump_installed')
# a 4R25 from forest_gear in the lake sensor's box and one copy lying by the radar's view; the tube lying face up
b6 = append(GEAR, ['Item_Battery6V'])
for o in b6:
    o.matrix_world = Matrix.Translation(D['LakeSensor'] + Vector(C['sockets']['Slot_Battery']['pos']))
tag(b6, 'sensor_box')
crt2 = copy_root('Item_RadarCRT', Matrix.Translation(D['Item_RadarCRT'] + Vector((0.62, 0.15, 0.215))) @
                 Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Rotation(math.radians(180), 4, 'Y'), 'crt')
relay2 = copy_root('Item_RelayUnit', Matrix.Translation(D['Item_RelayUnit'] + Vector((0.0, 0.62, 0.0))) @
                   Matrix.Rotation(math.radians(180), 4, 'Z'), 'relay')


def show(roots, tags=()):
    keep = set()
    for r in roots:
        for o in bpy.data.collections[r].all_objects:
            keep.add(o.name)
    for o in O:
        if o.library is not None or o in (cam, sun, lamp, bulb, floor, desk, snow, ice):
            continue
        if o.get('view'):
            o.hide_render = o['view'] not in tags
            continue
        if o.type in ('MESH', 'EMPTY'):
            o.hide_render = o.name.startswith('COL_') or o.name not in keep


def look(e, t, lens):
    cam.location = Vector(e)
    cam.rotation_euler = (Vector(t) - Vector(e)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.01


def light(kind, target):
    floor.hide_render = kind not in ('store', 'house')
    desk.hide_render = kind != 'desk'
    snow.hide_render = kind != 'out'
    ice.hide_render = kind != 'out'
    lamp.hide_render = kind not in ('store', 'desk', 'house', 'dark')
    sun.hide_render = kind != 'out'
    bulb.hide_render = True
    c = Vector(target)
    lamp.location = c + Vector((-0.6, -0.7, 1.6))
    lamp.rotation_euler = (c - lamp.location).to_track_quat('-Z', 'Y').to_euler()
    lamp.data.energy = 70.0
    if kind in ('store', 'desk', 'house', 'dark'):
        bg.inputs[0].default_value = (0.20, 0.22, 0.26, 1)
        bg.inputs[1].default_value = 0.5 if kind != 'dark' else 0.05
        if kind == 'house':
            lamp.location = c + Vector((0.3, -0.9, 1.7))
            lamp.rotation_euler = (c - lamp.location).to_track_quat('-Z', 'Y').to_euler()
            lamp.data.energy = 60.0
        if kind == 'dark':
            lamp.data.energy = 8.0
    else:
        bg.inputs[0].default_value = (0.56, 0.61, 0.70, 1)
        bg.inputs[1].default_value = 1.0
        sun.data.energy = 2.2
        sun.rotation_euler = (math.radians(55), 0, math.radians(35))


def set_mat(obj_name, old, new):
    o = O[obj_name]
    for i, m in enumerate(o.data.materials):
        if m and m.name == old:
            o.data.materials[i] = Mt[new]


V = {   # name: roots, light, eye, target, lens, tags, exposure
    'pump': (['Item_DosingPump'], 'store', D['Item_DosingPump'] + Vector((0.95, -1.25, 0.95)),
             D['Item_DosingPump'] + Vector((0.02, 0.0, 0.26)), 36, (), 0.0),
    'pump_installed': (['Item_DosingPump'], 'house', D['Item_DosingPump'] + Vector((0.55, -0.95, 1.55)),
                       D['Item_DosingPump'] + Vector((0.75, 0.55, 0.25)), 22, ('pump_installed',), 0.6),
    'lamp': (['Item_SodiumLamp', 'Item_SodiumLampBox'], 'dark', D['Item_SodiumLamp'] + Vector((0.18, -0.48, 0.30)),
             D['Item_SodiumLamp'] + Vector((0.07, 0.0, 0.15)), 38, (), 0.0),
    'crt': (['Item_RadarCRT'], 'store', D['Item_RadarCRT'] + Vector((0.95, -1.15, 0.85)),
            D['Item_RadarCRT'] + Vector((0.30, 0.05, 0.22)), 34, ('crt',), 0.0),
    'relay': (['Item_RelayUnit'], 'desk', D['Item_RelayUnit'] + Vector((0.32, -0.80, 0.42)),
              D['Item_RelayUnit'] + Vector((0.0, 0.22, 0.06)), 34, ('relay',), 0.0),
    'gen': (['Item_BackupGenerator'], 'out', D['Item_BackupGenerator'] + Vector((1.05, -1.35, 0.85)),
            D['Item_BackupGenerator'] + Vector((0.0, 0.0, 0.22)), 34, (), 0.0),
    'sensor': (['LakeSensor'], 'out', D['LakeSensor'] + Vector((1.45, -2.85, 1.55)), D['LakeSensor'] + Vector((0.0, -0.75, 0.62)),
               32, (), 0.0),
    'sensor_box': (['LakeSensor'], 'out', D['LakeSensor'] + Vector((0.28, -0.70, 1.32)),
                   D['LakeSensor'] + Vector((0.0, -0.09, 1.08)), 34, ('sensor_box',), 0.2),
}
HOSE, LID, CAP = O['DosingPump_Hose'], O['LakeSensor_Lid'], O['RelayUnit_FuseCap']
cap_mw = CAP.matrix_world.copy()
for nm, (roots, lk, e, t, lens, tags, ev) in V.items():
    if want and nm not in want:
        continue
    show(roots, tags)
    light(lk, t)
    HOSE.hide_render = HOSE.hide_render or nm != 'pump_installed'
    for v in ('V1', 'V2', 'V3'):
        O['DosingPump_' + v].rotation_euler = (0, 0, math.radians(90) if nm == 'pump_installed' else 0.0)
    LID.rotation_euler = (0, 0, math.radians(-115) if nm == 'sensor_box' else 0.0)
    O['RelayUnit_Power'].rotation_euler = (math.radians(-40) if nm == 'relay' else 0.0, 0, 0)
    O['RelayUnit_Needle'].rotation_euler = (0, math.radians(62) if nm == 'relay' else 0.0, 0)
    O['DosingPump_Needle'].rotation_euler = (0, math.radians(27 * 2.5) if nm == 'pump_installed' else 0.0, 0)
    for led, on in (('RelayUnit_LED_PWR', 'M_Parts_LEDG'), ('RelayUnit_LED_RX', 'M_Parts_LEDG'), ('RelayUnit_LED_ALM', 'M_Parts_LEDR')):
        o = O[led]
        o.data.materials[0] = Mt[on if nm == 'relay' else 'M_Parts_LED_Off']
    O['LakeSensor_LED'].data.materials[0] = Mt['M_Parts_LEDG' if nm in ('sensor', 'sensor_box') else 'M_Parts_LED_Off']
    O['SodiumLamp_ArcTube'].data.materials[0] = Mt['M_Parts_ArcTube' if nm == 'lamp' else 'M_Parts_ArcTube_Off']
    if nm == 'relay':                                     # the fuse cap off, lying on the desk with its burnt fuse
        CAP.matrix_world = Matrix.Translation(D['Item_RelayUnit'] + Vector((0.12, -0.26, 0.0076))) @ \
            Matrix.Rotation(math.radians(90), 4, 'Z')
        O['RelayUnit_Fuse'].data.materials[0] = Mt['M_Parts_FuseBurnt']
    else:
        CAP.matrix_world = cap_mw
        O['RelayUnit_Fuse'].data.materials[0] = Mt['M_Parts_FuseOK']
    if nm == 'lamp':
        bulb.hide_render = False
        bulb.location = D['Item_SodiumLamp'] + Vector((0.0, -0.015, 0.176))
        bulb.data.energy = 6.0
    sc.view_settings.exposure = ev
    look(e, t, lens)
    P.render(os.path.join(OUT, nm + '.png'))
    print('rendered', nm, flush=True)
