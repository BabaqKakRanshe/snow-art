"""Cycles previews of out/sky.blend: the refrigeration unit down (FAULT and the beacon lit), its belt guard open; the dust
sprayer; the ballast release at the edge over the fog; the altitude board at dusk (floodlights, the lamps lit up to the
marker at 1200 m); a walkway run under the island (straight, landing, stair, straight; hangers up to the rock, a lamp);
the walkway close.
python3 -I sky_render.py <views|all> [spp] -> rend/sky/<view>.png"""
import sys, os, math, json
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector, Matrix, Euler
import psxlib as P
import sky_kit as SK

HERE = P.HERE
OUT = os.path.join(HERE, 'rend', 'sky')
os.makedirs(OUT, exist_ok=True)
want = sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] != 'all' else None
spp = int(sys.argv[2]) if len(sys.argv) > 2 else 32
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'sky.blend'))
C = json.load(open(os.path.join(HERE, 'out', 'sky_contract.json')))
sc = bpy.context.scene
O, Mt = bpy.data.objects, bpy.data.materials
D = {r: Vector(v) for r, v in SK.DISPLAY.items()}


def mat(name, rgb, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Base Color'].default_value = (*rgb, 1)
    pb.inputs['Roughness'].default_value = rough
    return m


def mesh(name, verts, faces, m, tag):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new(name, me)
    me.materials.append(m)
    sc.collection.objects.link(ob)
    ob['view'] = tag
    return ob


m_ground = mat('M_RGround', (0.50, 0.49, 0.44), 0.95)               # frozen ground under the island's pale dust
m_rock = mat('M_RRock', (0.10, 0.10, 0.10), 0.9)
mesh('G_Ground', [(-60, -60, -0.01), (60, -60, -0.01), (60, 60, -0.01), (-60, 60, -0.01)], [(0, 1, 2, 3)], m_ground, 'ground')
mesh('G_Edge', [(-60, -2.0, -0.01), (60, -2.0, -0.01), (60, 60, -0.01), (-60, 60, -0.01)], [(0, 1, 2, 3)], m_ground, 'edge')
# the walkway run (copies of the modules, sharing their meshes) under a slab of rock
WALK0 = Vector((40.0, 0.0, -20.0))


def copy_root(root, M):
    """copy a root's hierarchy (objects share meshes) and put the root at M"""
    src = [o for o in bpy.data.collections[root].all_objects]
    m = {}
    for o in src:
        c = o.copy()
        c['view'] = 'walk'
        sc.collection.objects.link(c)
        m[o.name] = c
    for o in src:
        if o.parent and o.parent.name in m:
            m[o.name].parent = m[o.parent.name]
            m[o.name].matrix_parent_inverse = o.matrix_parent_inverse.copy()      # setting .parent resets it
    r = m[root]
    r.matrix_world = M @ Matrix.Translation(-D[root]) @ O[root].matrix_world
    return m


S_ = C['sockets']
run = []
M0 = Matrix.Translation(WALK0)
for nm in ('SkyWalk_Straight', 'SkyWalk_Landing', 'SkyWalk_Stair', 'SkyWalk_Straight'):
    run.append((nm, M0.copy()))
    M0 = M0 @ Matrix.Translation(Vector(S_[nm + '_End']['pos']))
ROCK_Z = WALK0.z + 5.0
copies = []
for nm, M in run:
    copies.append(copy_root(nm, M))
    for sn, s in S_.items():
        if s['root'] != nm or s['kind'] != 'hang':
            continue
        p = M @ Vector(s['pos'])
        L = ROCK_Z - 0.12 - p.z
        cb = copy_root('SkyWalk_Cable', Matrix.Translation(p))
        cb['SkyWalk_Cable'].scale.z = L
        copy_root('SkyWalk_Anchor', Matrix.Translation(Vector((p.x, p.y, ROCK_Z))))
lamp_m = Matrix.Translation(WALK0 + Vector((0.57, 2.0, 1.1))) @ Matrix.Rotation(math.radians(90), 4, 'Z')
copy_root('SkyWalk_Lamp', lamp_m)
lamp_glow = [o for o in bpy.data.objects if o.get('view') == 'walk' and o.name.startswith('SkyWalk_Lamp_Glow')]
rk = WALK0 + Vector((0, 0, 5.0))
mesh('G_Rock', [(rk.x - 30, rk.y - 30, ROCK_Z), (rk.x + 30, rk.y - 30, ROCK_Z), (rk.x + 30, rk.y + 40, ROCK_Z),
                (rk.x - 30, rk.y + 40, ROCK_Z)], [(3, 2, 1, 0)], m_rock, 'walk')

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.angle = math.radians(4.0)
sc.collection.objects.link(sun)
LAMPS = {}
for L in json.load(open(os.path.join(HERE, 'out', 'sky_lights.json')))['lights']:
    kind = 'SPOT' if L['type'] == 'spot' else 'POINT'
    ob = bpy.data.objects.new(L['name'], bpy.data.lights.new(L['name'], kind))
    ob.data.color = tuple(L['color_linear'])
    ob.data.shadow_soft_size = 0.05
    if kind == 'SPOT':
        ob.data.spot_size = math.radians(100)
        ob.data.spot_blend = 0.5
        ob.rotation_euler = (-Vector(L['dir'])).to_track_quat('Z', 'Y').to_euler()
    ob.location = D[L['root']] + Vector(L['pos'])
    sc.collection.objects.link(ob)
    LAMPS[L['name']] = (ob, L['root'], kind)
wl = bpy.data.objects.new('walk_lamp', bpy.data.lights.new('walk_lamp', 'SPOT'))
wl.data.color = (1.0, 0.72, 0.42)
wl.data.spot_size = math.radians(110)
wl.location = lamp_m @ Vector((0, 0.27, 0.62))
wl.rotation_euler = (0, 0, 0)
sc.collection.objects.link(wl)
P.setup_cycles((1100, 750), spp)
sc.cycles.max_bounces = 6
w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes['Background']
for o in O:
    if o.name.startswith('COL_'):
        o.hide_render = True


def show(roots, tags=()):
    keep = set()
    for r in roots:
        for o in bpy.data.collections[r].all_objects:
            keep.add(o.name)
    for o in O:
        if o.type not in ('MESH', 'EMPTY'):
            continue
        if o.get('view'):
            o.hide_render = o['view'] not in tags
            continue
        o.hide_render = o.name.startswith('COL_') or o.name not in keep


def look(e, t, lens):
    cam.location = Vector(e)
    cam.rotation_euler = (Vector(t) - Vector(e)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.02
    cam.data.clip_end = 600.0


def light(kind):
    sun.hide_render = kind == 'night'
    if kind == 'overcast':
        bg.inputs[0].default_value = (0.66, 0.68, 0.72, 1)
        bg.inputs[1].default_value = 1.3
        sun.data.energy = 1.2
        sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    elif kind == 'dusk':
        bg.inputs[0].default_value = (0.20, 0.22, 0.30, 1)
        bg.inputs[1].default_value = 0.55
        sun.data.energy = 0.12
        sun.rotation_euler = (math.radians(82), 0, math.radians(25))
    else:
        bg.inputs[0].default_value = (0.05, 0.06, 0.09, 1)
        bg.inputs[1].default_value = 0.35


def glow(obj, key, on):
    nm = {'amber': 'Amber', 'red': 'Red', 'green': 'Green', 'lamp': 'Lamp'}[key]
    O[obj].data.materials[0] = Mt[f'M_Sky_{nm}' if on else f'M_Sky_{nm}_Off']


def state(view):
    for nm, (ob, root, kind) in LAMPS.items():
        ob.hide_render = True
        ob.data.energy = 240.0 if kind == 'SPOT' else 40.0
    wl.hide_render = True
    wl.data.energy = 120.0
    for g, key in (('SkyChiller_LampRun', 'green'), ('SkyChiller_LampFault', 'red'), ('SkyChiller_Beacon', 'amber'),
                   ('SkyBallast_Beacon', 'amber'), ('SkyAltimeter_Lamps', 'amber'), ('SkyAltimeter_Glow', 'lamp'),
                   ('SkyAltimeter_Obstruction', 'red')):
        glow(g, key, False)
    for o in lamp_glow:
        o.data.materials[0] = Mt['M_Sky_Lamp_Off']
    O['IX_SkyChillerGuard'].rotation_euler = (0, 0, 0)
    mk = O['SkyAltimeter_Marker']
    mk.location = REST_MK.copy()
    if view.startswith('chiller'):
        glow('SkyChiller_LampFault', 'red', True)
        glow('SkyChiller_Beacon', 'amber', True)
        LAMPS['Light_SkyChiller_Beacon'][0].hide_render = False
        LAMPS['Light_SkyChiller_Beacon'][0].data.energy = 15.0
    if view == 'chiller_open':
        O['IX_SkyChillerGuard'].rotation_euler = Euler((math.radians(-100), 0, 0))
    if view == 'altimeter':
        for g, key in (('SkyAltimeter_Lamps', 'amber'), ('SkyAltimeter_Glow', 'lamp'), ('SkyAltimeter_Obstruction', 'red')):
            glow(g, key, True)
        for nm in ('Light_SkyAltimeter_1', 'Light_SkyAltimeter_2', 'Light_SkyAltimeter_Obstruction'):
            LAMPS[nm][0].hide_render = False
        rng = C['parts']['SkyAltimeter_Marker']['range'][1]
        mk.location = REST_MK + Vector((0, 0, rng * 1200.0 / 2000.0))
    if view.startswith('walk'):
        for o in lamp_glow:
            o.data.materials[0] = Mt['M_Sky_Lamp']
        wl.hide_render = False


REST_MK = O['SkyAltimeter_Marker'].location.copy()
CH, SP, BA, AL = D['SkyChiller'], D['SkySprayer'], D['SkyBallast'], D['SkyAltimeter']
V = {   # name: roots, tags, light, eye, target, lens, exposure
    'chiller': (['SkyChiller'], ('ground',), 'overcast', CH + Vector((5.6, -8.4, 3.0)), CH + Vector((-0.2, 0.0, 0.9)), 28, 0.0),
    'chiller_open': (['SkyChiller'], ('ground',), 'overcast', CH + Vector((-0.6, -3.6, 1.7)), CH + Vector((-0.5, -0.4, 0.75)), 24, 0.2),
    'sprayer': (['SkySprayer'], ('ground',), 'overcast', SP + Vector((7.6, -10.2, 3.6)), SP + Vector((0.0, 0.0, 3.4)), 24, 0.0),
    'ballast': (['SkyBallast'], ('edge',), 'overcast', BA + Vector((-7.0, 9.5, 4.2)), BA + Vector((0.3, 1.2, 0.0)), 24, 0.0),
    'altimeter': (['SkyAltimeter'], ('ground',), 'dusk', AL + Vector((3.6, -13.0, 3.0)), AL + Vector((0.0, 0.0, 6.4)), 28, 0.9),
    'walk': ([], ('walk',), 'dusk', WALK0 + Vector((7.5, -3.5, -2.6)), WALK0 + Vector((0.0, 6.5, -1.4)), 22, 1.2),
    'walk_close': ([], ('walk',), 'dusk', WALK0 + Vector((0.25, 0.4, 1.55)), WALK0 + Vector((0.0, 6.0, -0.8)), 18, 1.4),
}
for nm, (roots, tags, lk, e, t, lens, ev) in V.items():
    if want and nm not in want:
        continue
    show(roots, tags)
    state(nm)
    light(lk)
    sc.view_settings.exposure = ev
    look(e, t, lens)
    P.render(os.path.join(OUT, nm + '.png'))
    print('rendered', nm, flush=True)
