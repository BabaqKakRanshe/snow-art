"""Cycles previews of out/gear.blend: the cells and the radio on a desk, the hand lamp lit at night with its spot and
opened with a 4R25 in it, the headlamp lit, the cart and the pulk on snow, the doll with the postcard and her head turned,
both faces of the postcard, the bulb with its carton, the brass tag and the chief's key, the ice axe in the snow.
python3 -I gear_render.py <views|all> [spp] -> rend/gear/<view>.png"""
import sys, os, math, json
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector, Matrix
import psxlib as P
import gear_kit as GK

HERE = P.HERE
OUT = os.path.join(HERE, 'rend', 'gear')
os.makedirs(OUT, exist_ok=True)
want = sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] != 'all' else None
spp = int(sys.argv[2]) if len(sys.argv) > 2 else 32
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'gear.blend'))
C = json.load(open(os.path.join(HERE, 'out', 'gear_contract.json')))
sc = bpy.context.scene
O = bpy.data.objects
M = bpy.data.materials
for o in O:
    if o.name.startswith('COL_'):
        o.hide_render = True
for m in M:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
D = {r: Vector(v) for r, v in GK.DISPLAY.items()}


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


desk = plane('Desk', (-0.3, -0.6), (2.6, 0.6), -0.0015, (0.16, 0.11, 0.065), 0.7)         # a varnished desk top
floor = plane('Floor', (1.2, -0.8), (2.4, 0.8), -0.0012, (0.20, 0.19, 0.17), 0.8)         # boards under the doll
snow = plane('Snow', (-4.0, -3.0), (4.0, 4.0), -0.0018, (0.62, 0.64, 0.68), 0.9)
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
spot = bpy.data.objects.new('spot', bpy.data.lights.new('spot', 'SPOT'))
sc.collection.objects.link(spot)
P.setup_cycles((1000, 700), spp)
sc.cycles.max_bounces = 4
w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes['Background']
EXTRA = []                                    # copies made for a view (a battery in the lamp, the card turned over)


def copy_root(root, M4, tag):
    """a linked copy of a root's objects (the whole hierarchy) placed by M4 (from the root's own frame)"""
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
        else:
            c.parent = None
            c.matrix_world = M4 @ base.inverted() @ o.matrix_world
        c['view'] = tag
        c.hide_render = True
        EXTRA.append(c)
    return list(mp.values())


bat = copy_root('Item_Battery6V', Matrix.Translation(D['Item_Lantern'] + Vector(C['sockets']['Slot_Battery']['pos'])),
                'lantern_battery')
card_back = copy_root('Item_Postcard', Matrix.Translation(D['Item_Postcard'] + Vector((0.0, -0.13, 0.0035))) @
                      Matrix.Rotation(math.pi, 4, 'Y'), 'postcard')
card_doll = copy_root('Item_Postcard', Matrix.Translation(D['Item_Doll'] + Vector((0.13, -0.19, 0.0))) @
                      Matrix.Rotation(math.radians(-15), 4, 'Z'), 'doll')
axe_lean = copy_root('Item_IceAxe', Matrix.Translation(D['Item_IceAxe'] + Vector((0.0, 0.0, -0.06))) @
                     Matrix.Rotation(math.radians(14), 4, 'Y'), 'iceaxe')


def show(roots, tags=()):
    keep = set()
    for r in roots:
        for o in bpy.data.collections[r].all_objects:
            keep.add(o.name)
    for o in O:
        if o.library is not None or o in (cam, sun, lamp, spot, desk, snow, floor):
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
    cam.data.clip_start = 0.005


def light(kind, target):
    """desk: a warm lamp over the desk, a dim cool room; out: overcast winter daylight; night: a dark blue night"""
    desk.hide_render = kind != 'desk'
    floor.hide_render = kind != 'floor'
    snow.hide_render = kind not in ('out', 'night')
    lamp.hide_render = kind not in ('desk', 'floor')
    spot.hide_render = True
    sun.hide_render = kind not in ('out', 'night')
    c = Vector(target)
    lamp.location = c + Vector((-0.5, -0.4, 1.4))
    lamp.rotation_euler = (c - lamp.location).to_track_quat('-Z', 'Y').to_euler()
    lamp.data.energy = 45.0
    if kind in ('desk', 'floor'):
        bg.inputs[0].default_value = (0.20, 0.22, 0.26, 1)
        bg.inputs[1].default_value = 0.6
    elif kind == 'out':
        bg.inputs[0].default_value = (0.56, 0.61, 0.70, 1)
        bg.inputs[1].default_value = 1.0
        sun.data.energy = 2.2
        sun.data.color = (1.0, 1.0, 1.0)
        sun.rotation_euler = (math.radians(55), 0, math.radians(35))
    else:
        bg.inputs[0].default_value = (0.03, 0.04, 0.07, 1)
        bg.inputs[1].default_value = 1.0
        sun.data.energy = 0.06
        sun.data.color = (0.6, 0.7, 1.0)
        sun.rotation_euler = (math.radians(40), 0, math.radians(-60))


def set_mat(obj_name, mat_name):
    o = O[obj_name]
    for i, m in enumerate(o.data.materials):
        base = mat_name.replace('_Off', '')
        if m and m.name.replace('_Off', '') == base:
            o.data.materials[i] = M[mat_name]


def lit_spot(sock, root, energy, size_deg):
    s = C['sockets'][sock]
    p = Vector(s['pos']) + D[root]
    d = Vector(s['dir'])
    spot.hide_render = False
    spot.location = p
    spot.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    spot.data.color = tuple(s['color'])
    spot.data.spot_size = math.radians(size_deg)
    spot.data.spot_blend = 0.5
    spot.data.energy = energy
    spot.data.shadow_soft_size = 0.01


V = {   # name: roots, light, eye, target, lens, extra tags, exposure
    'cells': (['Item_Battery', 'Item_BatteryPack', 'Item_Battery6V'], 'desk', D['Item_BatteryPack'] + Vector((0.16, -0.36, 0.20)),
              D['Item_BatteryPack'] + Vector((0.02, 0.0, 0.035)), 40, (), 0.0),
    'walkie': (['Item_Walkie'], 'desk', D['Item_Walkie'] + Vector((0.13, -0.27, 0.20)), D['Item_Walkie'] + Vector((0.0, 0.0, 0.085)),
               36, (), 0.0),
    'lantern': (['Item_Lantern'], 'night', D['Item_Lantern'] + Vector((0.42, -0.30, 0.24)),
                D['Item_Lantern'] + Vector((-0.02, -0.20, 0.06)), 30, (), 0.6),
    'lantern_battery': (['Item_Lantern'], 'desk', D['Item_Lantern'] + Vector((-0.20, 0.33, 0.24)),
                        D['Item_Lantern'] + Vector((0.0, 0.02, 0.07)), 36, ('lantern_battery',), 0.0),
    'headlamp': (['Item_Headlamp'], 'desk', D['Item_Headlamp'] + Vector((0.28, -0.40, 0.26)),
                 D['Item_Headlamp'] + Vector((0.0, -0.03, 0.02)), 36, (), 0.0),
    'cart': (['Item_Cart'], 'out', D['Item_Cart'] + Vector((1.55, -2.05, 1.25)), D['Item_Cart'] + Vector((0.0, 0.05, 0.40)), 44,
             (), 0.0),
    'sled': (['Item_Sled'], 'out', D['Item_Sled'] + Vector((1.70, -2.30, 1.30)), D['Item_Sled'] + Vector((0.0, -0.50, 0.08)), 40,
             (), 0.0),
    'doll': (['Item_Doll'], 'floor', D['Item_Doll'] + Vector((0.18, -0.78, 0.36)), D['Item_Doll'] + Vector((0.03, -0.10, 0.13)),
             34, ('doll',), 0.0),
    'doll_turn': (['Item_Doll'], 'floor', D['Item_Doll'] + Vector((0.55, -0.42, 0.30)), D['Item_Doll'] + Vector((0.0, -0.02, 0.17)),
                  38, (), 0.0),
    'postcard': (['Item_Postcard'], 'desk', D['Item_Postcard'] + Vector((0.0, -0.20, 0.33)),
                 D['Item_Postcard'] + Vector((0.0, -0.065, 0.0)), 40, ('postcard',), 0.0),
    'small': (['Item_Bulb', 'Item_BulbBox', 'Item_WorkerTag', 'Item_Key_Stationsleiter'], 'desk',
              D['Item_BulbBox'] + Vector((0.025, -0.46, 0.20)), D['Item_BulbBox'] + Vector((0.025, -0.02, 0.04)), 40, (), 0.0),
    'iceaxe': ([], 'out', D['Item_IceAxe'] + Vector((0.42, -1.00, 0.60)), D['Item_IceAxe'] + Vector((0.07, 0.0, 0.34)), 36,
               ('iceaxe',), 0.0),
}
WT, KEY = O['Item_WorkerTag'], O['Item_Key_Stationsleiter']
wt_mw, key_mw = WT.matrix_world.copy(), KEY.matrix_world.copy()
for nm, (roots, lk, e, t, lens, tags, ev) in V.items():
    if want and nm not in want:
        continue
    show(roots, tags)
    light(lk, t)
    O['Doll_Head'].rotation_euler = (0, 0, math.radians(52.0) if nm == 'doll_turn' else 0.0)     # towards the camera
    O['Lantern_Door'].rotation_euler = (math.radians(-88.0) if nm == 'lantern_battery' else 0.0, 0, 0)
    O['Headlamp_Lamp'].rotation_euler = (math.radians(20.0) if nm == 'headlamp' else 0.0, 0, 0)
    set_mat('Lantern_Lens', 'M_Gear_LensAmber' if nm == 'lantern' else 'M_Gear_LensAmber_Off')
    set_mat('Headlamp_Lens', 'M_Gear_LensClear' if nm == 'headlamp' else 'M_Gear_LensClear_Off')
    if nm == 'small':                                    # the tag and the key lie on the desk (as found)
        WT.matrix_world = Matrix.Translation(D['Item_BulbBox'] + Vector((0.10, -0.06, 0.0018))) @ Matrix.Rotation(math.radians(-90), 4, 'X') \
            @ Matrix.Rotation(math.radians(20), 4, 'Y') @ Matrix.Translation(Vector((0, 0, 0.031)))
        KEY.matrix_world = Matrix.Translation(D['Item_BulbBox'] + Vector((0.165, 0.0, 0.0036))) @ Matrix.Rotation(math.radians(-90), 4, 'X') \
            @ Matrix.Rotation(math.radians(-35), 4, 'Y') @ Matrix.Translation(Vector((0, 0, 0.045)))
    else:
        WT.matrix_world, KEY.matrix_world = wt_mw, key_mw
    if nm == 'lantern':
        lit_spot('Light_Lantern', 'Item_Lantern', 6.0, 60.0)
    if nm == 'headlamp':
        bpy.context.view_layer.update()
        s = C['sockets']['Light_Headlamp']
        lm = O['Headlamp_Lamp']
        p = lm.matrix_world @ (Vector(s['pos']) - Vector(C['parts']['Headlamp_Lamp']['pivot']))
        d = lm.matrix_world.to_3x3() @ Vector(s['dir'])
        spot.hide_render = False
        spot.location = p
        spot.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        spot.data.color = tuple(s['color'])
        spot.data.spot_size = math.radians(40.0)
        spot.data.spot_blend = 0.4
        spot.data.energy = 3.0
        lamp.data.energy = 25.0
    sc.view_settings.exposure = ev
    look(e, t, lens)
    P.render(os.path.join(OUT, nm + '.png'))
    print('rendered', nm, flush=True)
