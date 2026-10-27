"""Cycles previews of out/world.blend: the fire barrel cold by day and burning at night, the shift car snowed over (front;
rear with its doors open), the wreck (front with the missing wheel; rear with the boot open), the cave outside, inside by
candlelight with stolen things on the stash places, and its nail with the Stationsleiter key; the ice on forest_far's relay
mast and Dish_1 and on forest_main's roof mast (the host models appended; BaseMain in a plain grey - its textures are not
here).
python3 -I world_render.py <views|all> [spp] -> rend/world/<view>.png"""
import sys, os, math, json
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector, Matrix
import psxlib as P
import world_kit as WK
import world_ice as WI

HERE = P.HERE
OUT = os.path.join(HERE, 'rend', 'world')
FAR = '/home/claude/far/out/forest_far/far.blend'
MAIN = '/mnt/user-data/uploads/snow/source/assets/forest_main/main.blend'
GEAR = os.path.join(HERE, 'out', 'gear.blend')
os.makedirs(OUT, exist_ok=True)
want = sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] != 'all' else None
spp = int(sys.argv[2]) if len(sys.argv) > 2 else 32
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'world.blend'))
C = json.load(open(os.path.join(HERE, 'out', 'world_contract.json')))
sc = bpy.context.scene
O, Mt = bpy.data.objects, bpy.data.materials
for o in O:
    if o.name.startswith(('COL_', 'HIT_', 'COLM_')):
        o.hide_render = True
D = {r: Vector(v) for r, v in dict(WK.DISPLAY, **WI.ICE_DISPLAY).items()}


def mat(name, rgb, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Base Color'].default_value = (*rgb, 1)
    pb.inputs['Roughness'].default_value = rough
    return m


def plane(name, c, half, z, m):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(c.x - half, c.y - half, z), (c.x + half, c.y - half, z), (c.x + half, c.y + half, z), (c.x - half, c.y + half, z)],
                   [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new(name, me)
    me.materials.append(m)
    sc.collection.objects.link(ob)
    return ob


m_snow = mat('M_RSnow', (0.62, 0.64, 0.68), 0.9)
m_grey = mat('M_RGrey', (0.30, 0.30, 0.29), 0.8)
grounds = {r: plane('G_' + r, D[r], 40.0 if r != 'ForesterCave' else 30.0, -0.002, m_snow) for r in WK.ROOTS}
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.angle = math.radians(4.0)
sc.collection.objects.link(sun)
fire = bpy.data.objects.new('fire', bpy.data.lights.new('fire', 'POINT'))
fire.data.color = (1.0, 0.55, 0.22)
fire.data.shadow_soft_size = 0.15
sc.collection.objects.link(fire)
torch = bpy.data.objects.new('torch', bpy.data.lights.new('torch', 'SPOT'))
torch.data.energy = 60.0
torch.data.spot_size = math.radians(40)
torch.data.spot_blend = 0.6
torch.data.color = (1.0, 0.92, 0.80)
torch.data.shadow_soft_size = 0.02
sc.collection.objects.link(torch)
candles = []
for i in range(4):
    lc = bpy.data.objects.new(f'cand{i}', bpy.data.lights.new(f'cand{i}', 'POINT'))
    lc.data.color = (1.0, 0.62, 0.30)
    lc.data.shadow_soft_size = 0.02
    sc.collection.objects.link(lc)
    candles.append(lc)
P.setup_cycles((1100, 750), spp)
sc.cycles.max_bounces = 6
w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes['Background']
EXTRA = []


def append(path, names, plain=None):
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
        if plain is not None and o.type == 'MESH':
            o.data.materials.clear()
            o.data.materials.append(plain)
        out.append(o)
    return out


def tag(objs, t):
    for o in objs:
        o['view'] = t
        EXTRA.append(o)


# the hosts of the ice at the ice roots' display places; the key and some stolen things in the cave
relay = append(FAR, ['RelayMast', 'RelayMast_Beacon'])
for o in relay:
    if o.parent is None:
        o.matrix_world = Matrix.Translation(D['Ice_RelayMast'])
tag(relay, 'ice_relay')
dish = append(FAR, ['Dish_1', 'Dish_1_Beacon', 'Dish_1_LED', 'Dish_1_Lamp', 'Dish_1_Sign', 'IX_CabinetDoor_2'])
for o in dish:
    if o.parent is None:
        o.matrix_world = Matrix.Translation(D['Ice_Dish_1'])
tag(dish, 'ice_dish')
bm = append(MAIN, ['BaseMain', 'FX_Obstruction_64'], plain=m_grey)
for o in bm:
    if o.parent is None:
        o.matrix_world = Matrix.Translation(D['Ice_RoofMast'])
tag(bm, 'ice_roof')
key = append(GEAR, ['Item_Key_Stationsleiter'])
sk = C['sockets']['Slot_Key']
kd = Vector(sk['dir'])
for o in key:                                           # hangs from its ring (its origin), the tag to the room
    if o.parent is None:
        o.matrix_world = Matrix.Translation(D['ForesterCave'] + Vector(sk['pos'])) @ \
            Matrix.Rotation(math.atan2(kd.x, -kd.y), 4, 'Z')
tag(key, 'cave')
stolen = append(GEAR, ['Item_Walkie', 'Item_Lantern', 'Item_BatteryPack', 'Item_Battery6V', 'Item_Battery'])
roots_st = [o for o in stolen if o.parent is None]
for i, o in enumerate(roots_st):
    s = C['sockets'][f'Slot_Stash_{i + 1}']
    o.matrix_world = Matrix.Translation(D['ForesterCave'] + Vector(s['pos'])) @ Matrix.Rotation(0.7 * i, 4, 'Z')
tag(stolen, 'cave')
for o in list(O):
    if o.name.startswith(('COL_', 'HIT_')) and o.library is None:
        o.hide_render = True


def show(roots, tags=()):
    keep = set()
    for r in roots:
        for o in bpy.data.collections[r].all_objects:
            keep.add(o.name)
    for o in O:
        if o.library is not None or o in [cam, sun, fire, torch] + candles:
            continue
        if o.get('view'):
            o.hide_render = o['view'] not in tags
            continue
        if o.name.startswith('G_'):
            continue
        if o.type in ('MESH', 'EMPTY'):
            o.hide_render = o.name.startswith(('COL_', 'HIT_', 'COLM_')) or o.name not in keep


def look(e, t, lens):
    cam.location = Vector(e)
    cam.rotation_euler = (Vector(t) - Vector(e)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.02
    cam.data.clip_end = 400.0


def light(kind):
    sun.hide_render = kind == 'night'
    fire.hide_render = True
    for lc in candles:
        lc.hide_render = True
    if kind == 'day':
        bg.inputs[0].default_value = (0.56, 0.61, 0.70, 1)
        bg.inputs[1].default_value = 1.0
        sun.data.energy = 2.4
        sun.rotation_euler = (math.radians(58), 0, math.radians(35))
    elif kind == 'overcast':
        bg.inputs[0].default_value = (0.62, 0.66, 0.72, 1)
        bg.inputs[1].default_value = 1.3
        sun.data.energy = 0.8
        sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
    else:
        bg.inputs[0].default_value = (0.03, 0.04, 0.07, 1)
        bg.inputs[1].default_value = 0.35


def set_mat(obj_name, old, new):
    o = O[obj_name]
    for i, m in enumerate(o.data.materials):
        if m and m.name == old:
            o.data.materials[i] = Mt[new]


B, S_, W_, CV = D['FireBarrel'], D['ShiftCar'], D['WreckCar'], D['ForesterCave']
V = {   # name: roots, light, eye, target, lens, tags, exposure
    'barrel': (['FireBarrel'], 'day', B + Vector((1.35, -1.75, 1.35)), B + Vector((0.0, 0.0, 0.50)), 36, (), 0.0),
    'barrel_night': (['FireBarrel'], 'night', B + Vector((1.45, -1.95, 1.25)), B + Vector((0.0, 0.0, 0.65)), 34, (), 0.4),
    'shift': (['ShiftCar'], 'day', S_ + Vector((4.4, -5.8, 2.3)), S_ + Vector((0.0, -0.1, 0.95)), 34, (), 0.0),
    'shift_rear': (['ShiftCar'], 'day', S_ + Vector((-3.9, 6.0, 2.5)), S_ + Vector((0.2, 0.4, 0.95)), 34, (), 0.0),
    'wreck': (['WreckCar'], 'day', W_ + Vector((-4.4, -5.8, 2.1)), W_ + Vector((0.0, -0.2, 0.65)), 34, (), 0.0),
    'wreck_rear': (['WreckCar'], 'day', W_ + Vector((4.2, 6.2, 2.4)), W_ + Vector((0.0, 0.4, 0.70)), 34, (), 0.0),
    'cave': (['ForesterCave'], 'day', CV + Vector((5.5, -10.0, 3.2)), CV + Vector((0.0, 2.5, 1.3)), 24, (), 0.0),
    'cave_in': (['ForesterCave'], 'night', CV + Vector((0.35, 0.9, 1.45)), CV + Vector((-0.6, 4.5, 0.35)), 16, ('cave',), 1.4),
    'cave_key': (['ForesterCave'], 'night', CV + Vector((1.05, 2.95, 1.45)), CV + Vector((1.92, 2.24, 1.18)), 30, ('cave',), 0.6),
    'ice_relay': (['Ice_RelayMast'], 'overcast', D['Ice_RelayMast'] + Vector((6.5, -8.5, 43.5)),
                  D['Ice_RelayMast'] + Vector((0.0, 0.0, 37.5)), 32, ('ice_relay',), 0.0),
    'ice_dish': (['Ice_Dish_1'], 'overcast', D['Ice_Dish_1'] + Vector((9.0, 20.0, 15.0)), D['Ice_Dish_1'] + Vector((0.0, 3.0, 9.0)),
                 30, ('ice_dish',), 0.0),
    'ice_roof': (['Ice_RoofMast'], 'overcast', D['Ice_RoofMast'] + Vector((8.6, -0.6, 17.2)),
                 D['Ice_RoofMast'] + Vector((5.45, 2.95, 15.6)), 32, ('ice_roof',), 0.0),
}
OPEN = {'shift_rear': [('IX_ShiftCarRearDoor', (0, 0, math.radians(80))), ('IX_ShiftCarDoor', (0, 0, math.radians(-50)))],
        'wreck_rear': [('IX_WreckCarBoot', (math.radians(60), 0, 0))],
        'wreck': [('IX_WreckCarBoot', (math.radians(12), 0, 0))]}
MOVERS = ['IX_ShiftCarRearDoor', 'IX_ShiftCarDoor', 'IX_WreckCarBoot', 'IX_WreckCarDoor']
for nm, (roots, lk, e, t, lens, tags, ev) in V.items():
    if want and nm not in want:
        continue
    show(roots, tags)
    for r, g in grounds.items():
        g.hide_render = r not in roots
    if nm.startswith('ice_'):
        for g in grounds.values():
            g.hide_render = True
    light(lk)
    for mv in MOVERS:
        O[mv].rotation_euler = (0.0, 0.0, 0.0)
    for on, rot in OPEN.get(nm, []):
        O[on].rotation_euler = rot
    lit = nm == 'barrel_night'
    O['FireBarrel_Glow'].data.materials[0] = Mt['M_World_Embers' if lit else 'M_World_Embers_Off']
    O['FireBarrel_Flames'].hide_render = not lit or 'FireBarrel' not in roots
    if lit:
        fire.hide_render = False
        fire.location = B + Vector((0.0, 0.0, 1.05))
        fire.data.energy = 260.0
    torch.hide_render = nm != 'cave_key'
    if nm == 'cave_key':                                     # a torch from the eye (the player's flashlight)
        torch.location = Vector(e) + Vector((0.0, 0.0, -0.15))
        torch.rotation_euler = (Vector(t) - torch.location).to_track_quat('-Z', 'Y').to_euler()
    if nm in ('cave_in', 'cave_key'):
        for i, lc in enumerate(candles):
            lc.hide_render = False
            lc.location = CV + Vector(C['sockets'][f'Light_Candle_{i + 1}']['pos'])
            lc.data.energy = 9.0
    sc.view_settings.exposure = ev
    look(e, t, lens)
    P.render(os.path.join(OUT, nm + '.png'))
    print('rendered', nm, flush=True)
