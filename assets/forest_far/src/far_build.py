"""Far points build (far_kit + far_paint): the five dishes, the radome, the relay mast, the weather station, the lookout
tower, the pump house, the chapel, the cabin, the campsite - each Update 3 prefab one object (the sign faces, lenses, glass,
flames and cut-outs joined in as extra materials, as Update 3's FBX; the doors IX_* its children), its root at its Update 3
place on the map (Blender frame of the map: Unity (x, y, z) -> (-x, -z, y)); PSX atlases at the generator shed's pixel
density, baked with each prefab in its own frame and the ground under it for the contact shading: Dish16 (Dish_1 baked,
its UVs copied loop by loop onto Dish_2 and Dish_5: they are built by the same calls at their own elevations), Dish12
(Dish_3 -> Dish_4), Towers (radome, relay mast), Meteo, Lookout, Chapel, Small (pump house, cabin, campsite); far_tex's
sign panel, the base's chain-link and barbed wire, Update 3's materials on the lenses, glass and flames; the contract.
1.1: the forest_devices models at their mounts - MeteoScreen on the weather station (Mount_MeteoScreen; the station lost
its own screen), TapeDeck in every dish cabinet (Mount_TapeDeck_n) - empties showing their collections linked from
../forest_devices/devices.blend (contract: devices_instances).
python3 -I far_build.py [--draft] [--only Dish16,Towers,...] -> out/far.blend, out/far.json, out/far_contract.json
--draft: no bakes (flat zone colours) -> out/far_draft.blend"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
import psxlib as P
import psxbake as PB
import gen_kit as K
import bld_common as BC

DRAFT = '--draft' in sys.argv
ONLY = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else (set() if DRAFT else None)
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'far')
BASE_TEX = os.path.join(HERE, 'tex', 'base')
OUT = os.path.join(HERE, 'out')
DEV_BLEND = os.path.join(HERE, 'forest_devices', 'devices.blend')     # -> ../forest_devices/devices.blend from the package's far.blend
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
PB.POS_SCALE = 140.0                                 # bake range +-70 m: the relay mast is 42.5 m tall, laid out 30 m over


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
import far_tex as FT
PANEL = FT.build(TEX)
import base_tex as BT
_, CHAIN, BARB, _ = BT.build(BASE_TEX)                # the base's cut-outs (the same files the base's materials use)
import far_spec as S
import far_kit as FK
import far_paint as FP

U3 = S.U3
MATDEF = U3['materials']

# ------------------------------------------------------------------ 1. geometry
FK.build_far()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts']]
assert not missing, f'objects without a contract entry: {missing}'
COPIES = {'Dish_2': 'Dish_1', 'Dish_5': 'Dish_1', 'Dish_4': 'Dish_3'}
for cp, ref in list(COPIES.items()):
    COPIES[S.DISHES[cp]['door']] = S.DISHES[ref]['door']
NO_WELD = set(FK.DISH_ZONES) | {FK.Z_TLEG, FK.Z_TBRACE, FK.Z_TRLEG, FK.Z_TRBRACE, FK.Z_TLADDER, FK.Z_TBRIDGE, FK.Z_TCABLE,
                                 FK.Z_LLEG, FK.Z_LBRACE, FK.Z_LSTRING, FK.Z_LRAIL, FK.Z_MGUY, FK.Z_MMAST, FK.Z_TSTEEL,
                                 FK.Z_XPOLE, FK.Z_CIRON, FK.Z_PPIPE}
CUTOUT = ('chainlink', 'barbed')


def joined_atlas(a):
    return a in ('glass', 'panel') or a.startswith('lens:') or a in CUTOUT


BC.is_joined = joined_atlas
BC.face_out = lambda k: None                          # the lenses are built facing out
BC.prepare_kbs(NO_WELD)
DISHES = set(S.DISHES) | {S.DISHES[d]['door'] for d in S.DISHES}
INFO['coplanar_separated'], moved = 0, {}
for n_ in [n for n in K.KBS if not joined_atlas(K.ATLAS[n]) and n not in DISHES]:   # the dishes keep their face order
    inf = {}
    INFO['coplanar_separated'] += BC.separate_coplanar([n_], info=inf)
    if inf['coplanar_moved_mm']['n']:
        moved[n_] = inf['coplanar_moved_mm']
INFO['coplanar_moved_mm'] = moved
log('coplanar overlapping faces pushed apart', INFO['coplanar_separated'], moved)
objs = BC.make_objects(log)
log('objects', len(objs))
ROOTS = [n for n, p in C['parts'].items() if not p.get('parent')]
log('roots', ROOTS)

# ------------------------------------------------------------------ 2. atlases
import unwrap_fast as UF
P.unwrap_group = UF.unwrap_fast
GROUPS = ('Dish16', 'Dish12', 'Towers', 'Meteo', 'Lookout', 'Chapel', 'Small')
groups = {}
for name, o in objs.items():
    a = K.ATLAS[name]
    if a in GROUPS and name not in COPIES:
        groups.setdefault(a, []).append(o)
log('atlases', {a: [o.name for o in v] for a, v in groups.items()})
SPEC = {'Dish16': dict(cap=BC.SHED_PPM, ao_min=0.40, ao_dist=0.40, rough=0.70,
                       zs={FK.Z_DREFL: 0.45, FK.Z_DBACK: 0.30, FK.Z_DTRUSS: 0.5, FK.Z_DPLINTH: 0.7}, max=1024),
        'Dish12': dict(cap=BC.SHED_PPM, ao_min=0.40, ao_dist=0.40, rough=0.70,
                       zs={FK.Z_DREFL: 0.55, FK.Z_DBACK: 0.35, FK.Z_DTRUSS: 0.5, FK.Z_DPLINTH: 0.7}, max=1024),
        'Towers': dict(cap=BC.SHED_PPM, ao_min=0.40, ao_dist=0.35, rough=0.75,
                       zs={FK.Z_TLEG: 0.6, FK.Z_TBRACE: 0.5, FK.Z_TRLEG: 0.6, FK.Z_TRBRACE: 0.5, FK.Z_TDOME: 0.6,
                           FK.Z_TCABLE: 0.4, FK.Z_TFOOT: 0.7}, max=2048),
        'Meteo': dict(cap=BC.SHED_PPM, ao_min=0.40, ao_dist=0.25, rough=0.80, zs={FK.Z_MPICKET: 0.7, FK.Z_MGUY: 0.3}, max=1024),
        'Lookout': dict(cap=BC.SHED_PPM, ao_min=0.38, ao_dist=0.35, rough=0.78, zs={FK.Z_LLEG: 0.6, FK.Z_LBRACE: 0.5}, max=1024),
        'Chapel': dict(cap=BC.SHED_PPM, ao_min=0.36, ao_dist=0.40, rough=0.85, zs={FK.Z_CROOF: 0.7}, max=2048),
        'Small': dict(cap=BC.SHED_PPM, ao_min=0.36, ao_dist=0.35, rough=0.85, zs=None, max=2048)}
VIVID = (FK.Z_DREFL, FK.Z_TDOME, FK.Z_MVANE, FK.Z_MSTAKE, FK.Z_CCLOTH, FK.Z_XTENT, FK.Z_XPACK, FK.Z_PPUMP, FK.Z_XCHAIR,
         FK.Z_PBRICK)
LAYOUTS = {'Dish16': {'Dish_1': (0.0, 0.0, 0.0)}, 'Dish12': {'Dish_3': (0.0, 0.0, 0.0)},
           'Towers': {'Radome': (0.0, 0.0, 0.0), 'RelayMast': (30.0, 0.0, 0.0)}, 'Meteo': {'MeteoStation': (0.0, 0.0, 0.0)},
           'Lookout': {'LookoutTower': (0.0, 0.0, 0.0)}, 'Chapel': {'Chapel': (0.0, 0.0, 0.0)},
           'Small': {'PumpHouse': (0.0, 0.0, 0.0), 'Cabin': (10.0, 0.0, 0.0), 'Campsite': (20.0, 0.0, 0.0)}}
GROUNDS = {'Dish_1': (-9.0, 9.0, -5.0, 8.0, 0.5), 'Dish_3': (-9.0, 9.0, -5.0, 8.0, 0.5), 'Radome': (-6.0, 11.0, -6.0, 6.0, 0.5),
           'RelayMast': (-7.0, 11.0, -7.0, 7.0, 0.5), 'MeteoStation': (-7.0, 7.0, -7.0, 7.0, 0.5),
           'LookoutTower': (-4.5, 4.5, -4.5, 4.5, 0.25), 'Chapel': (-7.5, 5.5, -5.5, 5.5, 0.25),
           'PumpHouse': (-3.0, 3.0, -2.5, 5.0, 0.25), 'Cabin': (-5.0, 3.5, -4.5, 4.0, 0.25), 'Campsite': (-2.0, 4.0, -2.5, 2.5, 0.25)}


def ground_objects(lay):
    made = []
    for n, off in lay.items():
        x0, x1, y0, y1, st = GROUNDS.get(n, (-3, 3, -3, 3, 0.5))
        xs, ys = np.arange(x0, x1 + 1e-6, st), np.arange(y0, y1 + 1e-6, st)
        v = [(float(x), float(y), S.ground(n, float(x), float(y))) for y in ys for x in xs]
        nx = len(xs)
        f = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(len(ys) - 1) for i in range(nx - 1)]
        me = bpy.data.meshes.new('AOG_' + n)
        me.from_pydata([(a + off[0], b + off[1], c + off[2]) for a, b, c in v], [], f)
        ob = bpy.data.objects.new('AOG_' + n, me)
        bpy.context.scene.collection.objects.link(ob)
        made.append(ob)
    return made


def colour_of(z):
    return FK.DRAFT_COL.get(z, (150, 148, 140))


GLASSLIKE = [o for n, o in objs.items() if joined_atlas(K.ATLAS[n])]
INFO['atlases'] = {}


def paint_chunked(Pp, Nn, Z, ao, aa, step=1 << 20):
    """FP.paint_far over slices of texels: every painter works texel by texel (noise of the position, zone rules, hashes of
    board / panel indices), so the result equals one call; a 2048 atlas baked at 4096 (8 M texels) stays in memory"""
    n = len(Pp)
    if n <= step:
        return FP.paint_far(Pp, Nn, Z, ao, aa)
    cols, grs = [], []
    for i in range(0, n, step):
        c, g = FP.paint_far(Pp[i:i + step], Nn[i:i + step], Z[i:i + step], ao[i:i + step], aa)
        cols.append(np.asarray(c, np.float32))
        grs.append(np.zeros(len(c), np.float32) if g is None else np.asarray(g, np.float32))
    return np.concatenate(cols), np.concatenate(grs)


for a in GROUPS:
    if a not in groups:
        continue
    lay = LAYOUTS[a]
    keep = {n: objs[n].location.copy() for n in lay}
    for n, off in lay.items():
        objs[n].location = Vector(off)
    names = [g.name for g in groups[a]]
    others = [o for o in objs.values() if o.name not in names and o.parent is None and o.name not in lay]
    BC.hidden(others)
    grounds = [] if (ONLY is not None and a not in ONLY) else ground_objects(lay)
    bpy.context.view_layer.update()
    FP.LAYOUT = lay
    BC.bake_groups({a: groups[a]}, [a], SPEC, paint_chunked, TEX, 'T_Far_', 'M_Far_', prio=VIVID, only=ONLY,
                   colour_of=colour_of, hide_always=GLASSLIKE, log=log, info=INFO['atlases'])
    for g_ in grounds:
        me = g_.data
        bpy.data.objects.remove(g_)
        bpy.data.meshes.remove(me)
    BC.hidden(others, False)
    for n in lay:
        objs[n].location = keep[n]
    bpy.context.view_layer.update()

# the copies: the reference dish's UVs and material, loop by loop (the same calls built them in the same order)
for cp, ref in COPIES.items():
    a_, b_ = objs[ref].data, objs[cp].data
    assert len(a_.loops) == len(b_.loops) and len(a_.polygons) == len(b_.polygons), f'{cp}: topology differs from {ref}'
    buf = np.empty(2 * len(a_.loops), np.float32)
    a_.uv_layers['PSX'].data.foreach_get('uv', buf)
    uvl = b_.uv_layers.get('PSX') or b_.uv_layers.new(name='PSX')
    uvl.data.foreach_set('uv', buf)
    mi = np.empty(len(a_.polygons), np.int32)
    a_.polygons.foreach_get('material_index', mi)
    b_.materials.clear()
    for m in a_.materials:
        b_.materials.append(m)
    b_.polygons.foreach_set('material_index', mi)
    log('uv copy', ref, '->', cp, len(a_.loops), 'loops')
INFO['uv_copies'] = COPIES

# ------------------------------------------------------------------ 3. materials: the panel, the cut-outs, lenses, glass, flames
m_panel = PB.tex_mat('M_Far_Panel', PANEL, PANEL, 0.06, rough=0.55)
m_panel['u3_like'] = 'M_ObsSigns: lit, emissionMap = the albedo, emission 1, intensity 0.06 (retroreflective glow at night)'


def cutout_mat(name, path, tile):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt_ = m.node_tree
    pb_ = next(n for n in nt_.nodes if n.type == 'BSDF_PRINCIPLED')
    uvn_ = nt_.nodes.new('ShaderNodeUVMap')
    uvn_.uv_map = 'PSX'
    ti_ = nt_.nodes.new('ShaderNodeTexImage')
    ti_.image = bpy.data.images.load(path, check_existing=True)
    ti_.interpolation = 'Closest'
    ti_.extension = 'REPEAT'
    nt_.links.new(uvn_.outputs[0], ti_.inputs[0])
    nt_.links.new(ti_.outputs['Color'], pb_.inputs['Base Color'])
    gt_ = nt_.nodes.new('ShaderNodeMath')
    gt_.operation = 'GREATER_THAN'
    gt_.inputs[1].default_value = 0.5
    nt_.links.new(ti_.outputs['Alpha'], gt_.inputs[0])
    nt_.links.new(gt_.outputs[0], pb_.inputs['Alpha'])
    pb_.inputs['Roughness'].default_value = 0.6
    m['alpha_clip'] = 0.5
    m['metres_per_tile'] = tile
    try:
        m.surface_render_method = 'DITHERED'
    except AttributeError:
        pass
    return m


m_chain = cutout_mat('M_Base_ChainLink', CHAIN, 0.5)
m_barb = cutout_mat('M_Base_Barbed', BARB, 0.5)
LENS = {'lens:sodium': 'M_Lamp_SodiumOff', 'lens:red': 'M_Light_Red', 'lens:led': 'M_LEDOff', 'lens:candle': 'M_Candle',
        'lens:headlight': 'M_Headlight', 'glass': 'M_GlassDirty'}


def mat_for(name):
    a = K.ATLAS[name]
    if a == 'panel':
        return m_panel
    if a == 'chainlink':
        return m_chain
    if a == 'barbed':
        return m_barb
    return BC.u3_mat(LENS[a], MATDEF)


def target_of(name):
    for suf in ('_Sign', '_Beacon', '_Lamp', '_LED', '_Glass', '_Flame', '_Lens', '_Mesh', '_Barbed'):
        if name.endswith(suf):
            return name[:-len(suf)]
    return None


BC.join_all(objs, target_of, mat_for, log)

# ------------------------------------------------------------------ 4. the map: each root at its Update 3 place
for n in ROOTS:
    o = objs[n]
    o.matrix_world = Matrix([list(r) for r in S.map_matrix(n)])
    col = bpy.data.collections.new(n)
    bpy.context.scene.collection.children.link(col)
    for c_ in list(o.users_collection):
        c_.objects.unlink(o)
    col.objects.link(o)
    for ch in o.children:
        for c_ in list(ch.users_collection):
            c_.objects.unlink(ch)
        col.objects.link(ch)
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 5. sockets, part boxes, the contract
for d in S.DISHES:
    K.socket('Audio_' + d + '_Drive', (0.0, -1.3, S.DSIZE[S.DISHES[d]['size']]['head'][0] + 0.2), 'audio', parent=d, root=d,
             note='the azimuth drives: a hum, now and then a clunk (the dish never turns)')
K.socket('Audio_RadomeHum', (8.0, 0.0, 3.2), 'audio', parent='Radome', root='Radome', note='the shelter\'s air conditioner')
K.socket('Audio_RelayWind', (0.0, 0.0, 30.0), 'audio', parent='RelayMast', root='RelayMast', note='wind in the lattice, '
                                                                                                  'the feeders knock')
K.socket('Audio_MeteoCups', (3.0, 2.0, 7.9), 'audio', parent='MeteoStation', root='MeteoStation',
         note='the anemometer\'s cups whirr, the vane creaks')
K.socket('Mount_MeteoScreen', (0.0, 0.0, 0.0), 'mount', parent='MeteoStation', root='MeteoStation', dir=(0.0, 1.0, 0.0),
         note='forest_devices MeteoScreen (the Stevenson screen): its origin here, turned 180 deg about z - its door (its -y) '
              'to the north (+y); the logger\'s cable ends at its leg')
_cx0, _cx1, _cy0, _cy1, _cz0, _cz1 = S.DISH['cab']
for d in S.DISHES:
    K.socket('Mount_TapeDeck_' + d[-1], ((_cx0 + _cx1) / 2, _cy1 - 0.04, 1.30), 'mount', parent=d, root=d, dir=(0.0, 1.0, 0.0),
             note='forest_devices TapeDeck (the telemetry recorder): its origin (the middle of its back) on the front of the '
                  'cabinet\'s third module, turned 180 deg about z - it faces the cabinet door (' + S.DISHES[d]['door'] + ')')
K.socket('Audio_LookoutCab', (0.0, 0.0, 23.0), 'audio', parent='LookoutTower', root='LookoutTower',
         note='the cab\'s windows rattle, the tower creaks in the wind')
K.socket('Audio_PumpHum', (0.9, 0.3, 0.7), 'audio', parent='PumpHouse', root='PumpHouse', note='the pump (silent unless '
                                                                                               'the power grid is on)')
K.socket('Audio_ChapelBell', (0.0, -2.85, 7.3), 'audio', parent='Chapel', root='Chapel', note='the bell knocks in the wind')
K.socket('Audio_CabinStove', (1.5, 1.2, 1.0), 'audio', parent='Cabin', root='Cabin', note='the cold stove ticks')
K.socket('Audio_CampTent', (0.0, 0.0, 0.3), 'audio', parent='Campsite', root='Campsite', note='the tent\'s fabric flaps')
INFO['part_boxes'] = BC.part_boxes(objs)
for k_, p in C['parts'].items():
    p['lightMask'] = 2
    p['pivotUnity'] = BC.to_unity(p['pivot'])
    o = objs.get(k_)
    if o is not None:
        p['materials'] = [m.name for m in o.data.materials if m]
        p['object'] = k_
# ------------------------------------------------------------------ 5b. the forest_devices instances (collections linked from the package)
DEV = [('MeteoScreen', 'MeteoScreen', 'MeteoStation', 'Mount_MeteoScreen')] + \
      [('TapeDeck_' + d[-1], 'TapeDeck', d, 'Mount_TapeDeck_' + d[-1]) for d in S.DISHES]
with bpy.data.libraries.load(DEV_BLEND, link=True) as (src_, dst_):
    dst_.collections = sorted({it for _, it, _, _ in DEV})
dcoll = {c_.name: c_ for c_ in dst_.collections}
assert set(dcoll) == {it for _, it, _, _ in DEV}, dcoll
inst_coll = bpy.data.collections.new('Devices_Instances')
bpy.context.scene.collection.children.link(inst_coll)
C['devices_instances'] = {}
R180 = Matrix.Rotation(math.pi, 4, 'Z')
for name_, item, par, sock in DEV:
    sp_ = Vector(C['sockets'][sock]['pos'])
    e = bpy.data.objects.new(name_, None)
    inst_coll.objects.link(e)
    e.instance_type = 'COLLECTION'
    e.instance_collection = dcoll[item]
    e.empty_display_type, e.empty_display_size = 'PLAIN_AXES', 0.1
    bpy.context.view_layer.update()
    e.matrix_world = objs[par].matrix_world @ Matrix.Translation(sp_) @ R180
    e.parent = objs[par]
    e.matrix_parent_inverse = objs[par].matrix_world.inverted()
    e['devices_item'] = item
    e['package'] = 'forest_devices'
    C['devices_instances'][name_] = dict(item=item, package='forest_devices', parent=par, root=par, socket=sock,
                                         pos=[round(float(v), 4) + 0.0 for v in sp_], rot_quat_wxyz=[0.0, 0.0, 0.0, 1.0],
                                         scale=[1.0, 1.0, 1.0], posUnity=BC.to_unity(sp_), rotUnity_xyzw=[0.0, -1.0, 0.0, 0.0],
                                         scaleUnity=[1.0, 1.0, 1.0],
                                         note=C['sockets'][sock]['note'])
INFO['devices_instances'] = sorted(C['devices_instances'])
log('devices instances', INFO['devices_instances'])
pl = {}
for n in ROOTS:
    es = U3['prefabs'][n]
    pl[n] = dict(list='prefabs', count=len(es), placements=[dict(p=e['p'], q=e['q']) for e in es])
C['meta'] = dict(
    version='1.1',
    units='metres, degrees',
    frames='each prefab its own frame - the frame of its Update 3 FBX after import: x / y / z, z up, origin = the prefab\'s '
           'pivot (Update 3\'s)',
    unity='position (x, y, z) -> Unity prefab-local (-x, z, -y) (pivotUnity given); the placements are Update 3\'s '
          '(Forest_Layout.json) and stay as they are',
    axes='hinge axes and angles in Blender terms (right-handed, +angle opens); in Unity the axis converts as a position '
         'and the angle changes sign - the same axes and signs as Update 3\'s interactables (IX_CabinetDoor_n: (0, 0, 1) -> Unity (0, -1, 0); IX_PumpDoor_7 / IX_ChapelDoor_8 / IX_CabinDoor_9: (0, 0, -1) -> Unity (0, 1, 0); +angle opens every door out)',
    blend='each root stands at its Update 3 place on the map, in its own collection; for an FBX of one prefab put its root '
          'at (0, 0, 0) with no rotation',
    map_placement=pl,
    hierarchy='every prefab is one mesh object, as Update 3 (sign faces, lenses, glass, flames and the chain-link joined in '
              'as extra materials); the doors IX_CabinetDoor_2..6, IX_PumpDoor_7, IX_ChapelDoor_8, IX_CabinDoor_9 are '
              'children (Update 3\'s interactables: names, pivots, axes and ranges unchanged); 1.1: the forest_devices '
              'instances (devices_instances) are empties under their parent showing the collections linked from '
              '../forest_devices/devices.blend (props devices_item, package)',
    dishes='the reflector, the feed and the beacon stand where Update 3 has them (each dish at its own elevation: 38 / 42 / '
           '45 / 40 / 36 deg); Dish_2 and Dish_5 share Dish_1\'s atlas (T_Far_Dish16), Dish_4 Dish_3\'s (T_Far_Dish12)',
    lookout='Update 3\'s treads and landings unchanged (decorative, as in Update 3: steep flights, 47..66 deg, stacked one '
            'over another - a CharacterController does not climb them); new: a stairwell in the cab floor over the '
            'last flight and the top landing (the floor is 0.88 m over that landing: Update 3\'s cab had no opening and '
            'the last flight hit it), a ship ladder of three treads from the landing up to the floor, rails round the well',
    lights='unchanged: Update 3\'s lights and halos sit in the new lenses (dish beacons and yard lights, the radome\'s and '
           'the relay mast\'s beacons, the chapel\'s candles, the campsite\'s torch)',
    materials='M_Far_Dish16 / Dish12 / Towers / Meteo / Lookout / Chapel / Small: baked PSX atlases (point filter, no '
              'mips); M_Far_Panel: the signs, lit, emission = albedo at 0.06; M_Base_ChainLink / M_Base_Barbed: the base\'s '
              'cut-outs (the relay compound); Update 3\'s M_Light_Red, M_Lamp_SodiumOff, M_LEDOff, M_GlassDirty, M_Candle, '
              'M_Headlight',
    sockets='audio: the dishes\' drives, the radome\'s air conditioner, the relay mast\'s wind, the anemometer, the lookout\'s '
            'cab, the pump, the chapel\'s bell, the cabin\'s stove, the tent; mount (1.1): Mount_MeteoScreen (the weather '
            'station), Mount_TapeDeck_1..5 (the dish cabinets) - where the forest_devices models go',
    devices_instances='forest_devices models placed on the mounts (1.1): MeteoScreen on MeteoStation, TapeDeck_1..5 in the '
                      'dish cabinets; in Unity put forest_devices\' prefab (MeteoScreen / TapeDeck) under the parent at pos / '
                      'rot (the parent\'s frame) or posUnity / rotUnity_xyzw; DEVICES_CONTRACT.md has their parts and sockets',
    model='far.blend', textures='tex/far')
BC.psx_uv_only()
sfx = '_draft' if DRAFT else ('_test' if ONLY else '')
json.dump(BC.nz(C), open(os.path.join(OUT, f'far_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.library is None]     # not the linked forest_devices
INFO['tris'] = sum(P.tri_count(o) for o in meshes)
INFO['tris_by_object'] = {o.name: P.tri_count(o) for o in meshes}
INFO['objects'] = len(meshes)
INFO['materials'] = sorted({m.name for o in meshes for m in o.data.materials if m})
INFO['u3_tris'] = {n: v['tris'] for n, v in U3['u3_models'].items()}
log('tris', INFO['tris'], INFO['tris_by_object'], 'materials', [m for m in INFO['materials'] if not m.startswith('draft')])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'far{sfx}.blend'))
json.dump(INFO, open(os.path.join(OUT, f'far{sfx}.json'), 'w'), indent=1)
log('saved far' + sfx)
