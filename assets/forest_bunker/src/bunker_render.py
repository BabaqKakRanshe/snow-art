"""Cycles previews of out/bunker.blend: the hangar from the lake with its gates shut; at dusk with the gates open, the lamps
lit and the plane under its tarp inside (forest UtilityPlane v13 with the WinterKit, appended from its own .blend and parked
on Slot_Plane); inside, toward the gate (the side door, the plane); the vestibule with the round door and the wet prints;
the door open (act 3); the entrance trench from above; the hatch under the ice; the hatch open over the shaft.
python3 -I bunker_render.py <views|all> [spp] -> rend/bunker/<view>.png"""
import sys, os, math, json
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector, Matrix
import psxlib as P
import bunker_kit as BK
import bunker_spec as S

HERE = P.HERE
OUT = os.path.join(HERE, 'rend', 'bunker')
PLANE = '/mnt/user-data/uploads/snow/source/plane/UtilityPlane_Unity_v13/Blender/UtilityPlane_v13.blend'
os.makedirs(OUT, exist_ok=True)
want = sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] != 'all' else None
spp = int(sys.argv[2]) if len(sys.argv) > 2 else 32
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'bunker.blend'))
C = json.load(open(os.path.join(HERE, 'out', 'bunker_contract.json')))
sc = bpy.context.scene
O, Mt = bpy.data.objects, bpy.data.materials
D = {r: Vector(v) for r, v in BK.DISPLAY.items()}
HG, VS, EN = D['BunkerHangar'], D['BlastDoor'], D['BunkerEntrance']


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


m_snow = mat('M_RSnow', (0.62, 0.64, 0.68), 0.9)
m_ice = mat('M_RLake', (0.36, 0.42, 0.50), 0.25)
# outside the hangar: the lake ice, snow on the shore round it, the bank over the hall
mesh('G_Lake', [(-80, -120, -0.22), (80, -120, -0.22), (80, -5.9, -0.22), (-80, -5.9, -0.22)], [(0, 1, 2, 3)], m_ice, 'out')
bank = [(-80, -5.9, -0.21), (-20.3, -5.9, -0.21), (-19.9, -5.2, 1.0), (-16.9, 0.0, 8.05), (16.9, 0.0, 8.05), (19.9, -5.2, 1.0),
        (20.3, -5.9, -0.21), (80, -5.9, -0.21), (80, 60, 12.0), (-80, 60, 12.0)]
mesh('G_Bank', bank, [(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)], m_snow, 'out')
# the ground round the entrance trench (a hole for it)
xo, y0, y1 = S.E['xi'] + S.E['t'], -0.30, S.E['land_y1'] + 0.30
e = EN
g = [(e.x - 40, e.y - 40, 0), (e.x + 40, e.y - 40, 0), (e.x + 40, e.y + 40, 0), (e.x - 40, e.y + 40, 0),
     (e.x - xo, e.y + y0, 0), (e.x + xo, e.y + y0, 0), (e.x + xo, e.y + y1, 0), (e.x - xo, e.y + y1, 0)]
mesh('G_Entr', g, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], m_snow, 'entr')
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.angle = math.radians(4.0)
sc.collection.objects.link(sun)
torch = bpy.data.objects.new('torch', bpy.data.lights.new('torch', 'SPOT'))
torch.data.energy = 80.0
torch.data.spot_size = math.radians(40)
torch.data.spot_blend = 0.6
torch.data.color = (1.0, 0.92, 0.80)
torch.data.shadow_soft_size = 0.02
sc.collection.objects.link(torch)
LAMPS = {}
for L in json.load(open(os.path.join(HERE, 'out', 'bunker_lights.json')))['lights']:
    kind = 'SPOT' if L['type'] == 'spot' else 'POINT'
    ob = bpy.data.objects.new(L['name'], bpy.data.lights.new(L['name'], kind))
    ob.data.color = tuple(L['color_linear'])
    ob.data.shadow_soft_size = 0.05
    if kind == 'SPOT':
        ob.data.spot_size = math.radians(115)
        ob.data.spot_blend = 0.5
    ob.location = D[L['root']] + Vector(L['pos'])
    sc.collection.objects.link(ob)
    LAMPS[L['name']] = (ob, L['root'], kind)
P.setup_cycles((1100, 750), spp)
sc.cycles.max_bounces = 6
w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes['Background']

# the plane, parked on Slot_Plane (its own .blend: the aircraft, the WinterKit installed, the cockpit)
KEEP = ['Aircraft', 'Winter kit 1.2 - installed (WinterKit)', 'Cockpit', 'Fittings_v9']
with bpy.data.libraries.load(PLANE, link=False) as (src, dst):
    dst.collections = [c for c in KEEP if c in src.collections]
PLANE_OBJS = []
for c in dst.collections:
    sc.collection.children.link(c)
    for o in c.all_objects:
        o['view'] = 'plane'
        PLANE_OBJS.append(o)
PARK = Matrix.Translation(HG) @ S.plane_park_matrix()
O['UtilityPlane'].matrix_world = PARK
O['WinterKit'].matrix_world = PARK
tarp = O['PlaneTarp']
tarp.matrix_world = PARK
for o in O:
    if o.name.startswith(('COL_', 'HIT_', 'COLM_')):
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
        o.hide_render = o.name.startswith(('COL_', 'HIT_', 'COLM_')) or o.name not in keep


def look(e, t, lens):
    cam.location = Vector(e)
    cam.rotation_euler = (Vector(t) - Vector(e)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.02
    cam.data.clip_end = 600.0


def light(kind):
    sun.hide_render = kind == 'night'
    if kind == 'overcast':
        bg.inputs[0].default_value = (0.58, 0.62, 0.70, 1)
        bg.inputs[1].default_value = 1.2
        sun.data.energy = 0.9
        sun.rotation_euler = (math.radians(55), 0, math.radians(-30))
    elif kind == 'dusk':
        bg.inputs[0].default_value = (0.16, 0.20, 0.30, 1)
        bg.inputs[1].default_value = 0.6
        sun.data.energy = 0.15
        sun.rotation_euler = (math.radians(80), 0, math.radians(20))
    else:
        bg.inputs[0].default_value = (0.03, 0.04, 0.07, 1)
        bg.inputs[1].default_value = 0.3


def lamps(on_roots, energy=1.0):
    for nm, (ob, root, kind) in LAMPS.items():
        ob.hide_render = root not in on_roots
        ob.data.energy = (260.0 if kind == 'SPOT' else 45.0) * energy
    for gname, root in (('BunkerHangar_Glow', 'BunkerHangar'), ('BlastDoor_Glow', 'BlastDoor'), ('BunkerEntrance_Glow', 'BunkerEntrance')):
        O[gname].data.materials[0] = Mt['M_Bunker_Lamp' if root in on_roots else 'M_Bunker_Lamp_Off']


REST = {}
MOVERS = ['IX_HangarGate_L', 'IX_HangarGate_R', 'IX_HangarSideDoor', 'IX_BlastDoor', 'IX_BunkerHatch'] + \
         [f'IX_BlastDoor_Bolt_{i + 1}' for i in range(6)]
for mv in MOVERS:
    REST[mv] = (O[mv].location.copy(), O[mv].rotation_euler.copy())


def pose(nm):
    for mv in MOVERS:
        O[mv].location, O[mv].rotation_euler = REST[mv][0].copy(), REST[mv][1].copy()
    for i in range(3):
        O[f'Ice_Hatch_{i + 1}'].hide_render = False
    if nm in ('hangar_open', 'hangar_in'):
        O['IX_HangarGate_L'].location.x -= S.H['leaf_w']
        O['IX_HangarGate_R'].location.x += S.H['leaf_w']
    if nm == 'door_open':
        for i in range(6):
            b = O[f'IX_BlastDoor_Bolt_{i + 1}']
            ax = Vector(C['parts'][b.name]['axis'])
            b.location = b.location + ax * 0.16
        O['IX_BlastDoor'].rotation_euler.z = -math.radians(88)
    if nm == 'entr_open':
        for i in range(3):
            O[f'Ice_Hatch_{i + 1}'].hide_render = True
        O['IX_BunkerHatch'].rotation_euler.x = -math.radians(105)


V = {   # name: roots, tags, light, lamps on, eye, target, lens, exposure, torch
    'hangar': (['BunkerHangar'], ('out',), 'overcast', [], HG + Vector((13.0, -31.0, 3.6)), HG + Vector((0.0, 0.0, 3.6)), 28, 0.0, False),
    'hangar_open': (['BunkerHangar', 'BlastDoor', 'PlaneTarp'], ('out', 'plane'), 'dusk', ['BunkerHangar', 'BlastDoor'],
                    HG + Vector((-7.0, -27.0, 2.0)), HG + Vector((0.0, 8.0, 2.6)), 30, 0.6, False),
    'hangar_in': (['BunkerHangar', 'BlastDoor', 'PlaneTarp'], ('out', 'plane'), 'dusk', ['BunkerHangar'],
                  HG + Vector((6.6, 14.6, 2.3)), HG + Vector((-2.6, 2.0, 1.7)), 18, 0.8, False),
    'vest': (['BlastDoor', 'BunkerHangar'], (), 'night', ['BlastDoor'], VS + Vector((0.45, 0.5, 1.7)), VS + Vector((0.0, 8.0, 1.9)),
             19, 1.0, False),
    'door_open': (['BlastDoor', 'BunkerHangar'], (), 'night', ['BlastDoor'], VS + Vector((1.6, 3.2, 1.75)),
                  VS + Vector((-0.4, 9.2, 1.3)), 20, 1.0, True),
    'entr': (['BunkerEntrance'], ('entr',), 'overcast', [], EN + Vector((0.45, -2.3, 1.75)), EN + Vector((0.0, 5.4, -2.1)), 17, -0.3, False),
    'entr_hatch': (['BunkerEntrance'], ('entr',), 'overcast', [], EN + Vector((0.45, 4.3, -1.55)), EN + Vector((0.0, 6.7, -3.0)), 22,
                   0.3, True),
    'entr_open': (['BunkerEntrance'], ('entr',), 'overcast', [], EN + Vector((0.05, 5.15, -1.45)), EN + Vector((0.0, 6.45, -6.2)), 20,
                  0.5, True),
}
for nm, (roots, tags, lk, lon, e, t, lens, ev, tor) in V.items():
    if want and nm not in want:
        continue
    show(roots, tags)
    pose(nm)
    light(lk)
    lamps(lon)
    torch.hide_render = not tor
    if tor:
        torch.location = Vector(e) + Vector((0.0, 0.0, -0.15))
        torch.rotation_euler = (Vector(t) - torch.location).to_track_quat('-Z', 'Y').to_euler()
    sc.view_settings.exposure = ev
    look(e, t, lens)
    P.render(os.path.join(OUT, nm + '.png'))
    print('rendered', nm, flush=True)
