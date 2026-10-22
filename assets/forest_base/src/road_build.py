"""Road prefabs build (road_kit + road_paint): the twelve signs, the delineator post, the zone gate, the bridge, the overlook
deck and the windfall - each Update 3 prefab one object (its static mesh, the faces / chain-link / barbed wire / reflectors
joined in, as Update 3's FBX), its root at its Update 3 place on the map (Blender frame of the map: Unity (x, y, z) ->
(-x, -z, y)); PSX atlases at the generator shed's pixel density, baked with each prefab in its own frame (Signs: the
signs and the post side by side; Windfall: the tree and the log apart) and the ground under it (Update 3's terrain,
road_ground.json) for the contact shading: Signs, Gate, Bridge, Deck, Windfall; road_tex's sign panel (the faces glow
faintly at night, as Update 3's M_ObsSigns), the chain-link and barbed-wire cut-outs, Update 3's M_Reflector on the
reflectors; the contract (prefabs, placements, the EuroPost scatter, sockets, colliders, materials).
python3 -I road_build.py [--draft] [--only Signs,Gate,...] -> out/road.blend, out/road.json, out/road_contract.json
--draft: no bakes (flat zone colours) -> out/road_draft.blend"""
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
TEX = os.path.join(HERE, 'tex', 'road')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
PB.POS_SCALE = 80.0                                  # bake range +-40 m: the fallen spruce is 32 m long, the signs side by side


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
import road_tex as RT
PANEL, CHAIN, BARB = RT.build(TEX)
import road_spec as S
import road_kit as RK
import road_paint as RP

U3 = S.U3
MATDEF = U3['materials']

# ------------------------------------------------------------------ 1. geometry
RK.build_road()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts']]
assert not missing, f'objects without a contract entry: {missing}'
NO_WELD = {RK.Z_SCLAMP, RK.Z_STEEL, RK.Z_DSTEEL, RK.Z_GHINGE, RK.Z_CHAIN, RK.Z_TBRANCH, RK.Z_TBREAK, RK.Z_SAWDUST,
           RK.Z_DRAG, RK.Z_SOIL}


_IS_JOINED = BC.is_joined


def joined_atlas(a):
    return _IS_JOINED(a) or a in ('chainlink', 'barbed')


BC.is_joined = joined_atlas                           # the cut-outs are joined into their owners as the panel is
BC.prepare_kbs(NO_WELD)
INFO['coplanar_separated'], moved = 0, {}
for n_ in [n for n in K.KBS if not joined_atlas(K.ATLAS[n])]:        # per prefab: they all stand at the origin here
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

# ------------------------------------------------------------------ 2. atlases (each group baked in its own layout)
def _unwrap_fast(objs_, uv_name='PSX', margin=0.003, angle=60, zone_scale=None, custom=None):
    """psxlib.unwrap_group with Blender's box packing instead of the concave one: the bridge has thousands of small
    islands (planks, bolts) and the concave packer takes tens of minutes; bld_common.prep_atlas repacks the boxes in
    shelves (uvpack) right after and keeps the better of the two anyway"""
    for o in objs_:
        me = o.data
        old = me.uv_layers.active
        for u in me.uv_layers:
            u.active_render = (u == old) if old else False
        uvl = me.uv_layers.get(uv_name) or me.uv_layers.new(name=uv_name)
        me.uv_layers.active = uvl
        if old:
            old.active_render = True
    P.select_only(objs_)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.reveal()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0, correct_aspect=True,
                             scale_to_bounds=False)
    if zone_scale:
        bpy.ops.object.mode_set(mode='OBJECT')
        for o in objs_:
            za = o.data.attributes.get('zone')
            if za is None:
                continue
            uvd = o.data.uv_layers[uv_name].data
            for p_ in o.data.polygons:
                f_ = zone_scale.get(int(round(za.data[p_.index].value)))
                if f_:
                    for li in p_.loop_indices:
                        uvd[li].uv = uvd[li].uv * f_
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, rotate_method='AXIS_ALIGNED', scale=True, margin_method='FRACTION', margin=margin,
                            shape_method='AABB')
    bpy.ops.object.mode_set(mode='OBJECT')


P.unwrap_group = _unwrap_fast
GROUP_OF = {'Signs': 'Signs', 'Gate': 'Gate', 'Bridge': 'Bridge', 'Deck': 'Deck', 'Windfall': 'Windfall'}
groups = {}
for name, o in objs.items():
    a = K.ATLAS[name]
    if not joined_atlas(a):
        groups.setdefault(GROUP_OF[a], []).append(o)
log('atlases', {a: [o.name for o in v] for a, v in groups.items()})
SPEC = {'Signs': dict(cap=BC.SHED_PPM, ao_min=0.40, ao_dist=0.12, rough=0.70, zs=None, max=1024),
        'Gate': dict(cap=BC.SHED_PPM, ao_min=0.38, ao_dist=0.25, rough=0.75, zs=None, max=1024),
        'Bridge': dict(cap=BC.SHED_PPM, ao_min=0.36, ao_dist=0.45, rough=0.90, zs={RK.Z_PILE: 0.85, RK.Z_BRACE: 0.85}),
        'Deck': dict(cap=BC.SHED_PPM, ao_min=0.36, ao_dist=0.35, rough=0.88, zs=None, max=1024),
        'Windfall': dict(cap=BC.SHED_PPM, ao_min=0.34, ao_dist=0.40, rough=0.92, zs={RK.Z_TBRANCH: 0.8}, max=1024)}
VIVID = (RK.Z_EPBODY, RK.Z_TCUT, RK.Z_SAWDUST, RK.Z_GPLATE, RK.Z_CHAIN)


def bake_layout(group):
    """where each root of a group stands while it is baked (its own frame, apart from the others)"""
    lay = {}
    if group == 'Signs':
        x = 0.0
        for n in S.SIGN_ORDER + ['EuroPost']:
            w = S.SIGNS[n]['face'][0] + 0.4 if n in S.SIGNS else 0.4
            lay[n] = (x + w / 2, 0.0, 0.0)
            x += w + 1.2
        off = x / 2
        lay = {n: (v[0] - off, v[1], v[2]) for n, v in lay.items()}
    elif group == 'Windfall':
        lay = {'FallenTree': (-15.0, 3.0, 0.0), 'LogCut': (0.0, -10.0, 0.0)}
    else:
        r = {'Gate': 'ZoneGate', 'Bridge': 'Bridge30', 'Deck': 'OverlookDeck'}[group]
        lay = {r: (0.0, 0.0, 0.0)}
    return lay


GROUNDS = {'ZoneGate': (-6.0, 6.0, -3.0, 3.0, 0.25), 'Bridge30': (-22.0, 22.0, -4.0, 4.0, 0.5),
           'OverlookDeck': (-4.0, 4.0, -3.0, 6.0, 0.25), 'FallenTree': (-6.0, 30.0, -6.0, 6.0, 0.5),
           'LogCut': (-6.0, 6.0, -4.0, 5.0, 0.25)}


def ground_objects(lay):
    """the ground under each root of the layout (AO only)"""
    made = []
    for n, off in lay.items():
        if n in GROUNDS:
            v, f = RK.ground_patch(n, *GROUNDS[n])
        elif n in S.SIGNS:
            v, f = RK.ground_patch(n, -1.6, 1.6, -0.6, 0.6, 0.1)
        else:
            v = [(-0.6, -0.6, 0.0), (0.6, -0.6, 0.0), (0.6, 0.6, 0.0), (-0.6, 0.6, 0.0)]
            f = [(0, 1, 2, 3)]
        me = bpy.data.meshes.new('AOG_' + n)
        me.from_pydata([(a + off[0], b + off[1], c + off[2]) for a, b, c in v], [], f)
        ob = bpy.data.objects.new('AOG_' + n, me)
        bpy.context.scene.collection.objects.link(ob)
        made.append(ob)
    return made


def colour_of(z):
    return RK.DRAFT_COL.get(z, (150, 148, 140))


GLASSLIKE = [o for n, o in objs.items() if joined_atlas(K.ATLAS[n])]
INFO['atlases'] = {}
for a in ['Signs', 'Gate', 'Bridge', 'Deck', 'Windfall']:
    if a not in groups:
        continue
    lay = bake_layout(a)
    keep = {n: objs[n].location.copy() for n in lay}
    for n, off in lay.items():
        objs[n].location = Vector(off)
    others = [o for o in objs.values() if o.name not in [g.name for g in groups[a]] and o.parent is None and o.name not in lay]
    BC.hidden(others)
    grounds = [] if (ONLY is not None and a not in ONLY) else ground_objects(lay)
    bpy.context.view_layer.update()
    RP.LAYOUT = lay
    BC.bake_groups({a: groups[a]}, [a], SPEC, RP.paint_road, TEX, 'T_Road_', 'M_Road_', prio=VIVID, only=ONLY,
                   colour_of=colour_of, hide_always=GLASSLIKE, log=log, info=INFO['atlases'])
    for g_ in grounds:
        me = g_.data
        bpy.data.objects.remove(g_)
        bpy.data.meshes.remove(me)
    BC.hidden(others, False)
    for n in lay:
        objs[n].location = keep[n]
    bpy.context.view_layer.update()

# ------------------------------------------------------------------ 3. materials: the sign panel, the cut-outs, the reflector
m_signs = PB.tex_mat('M_Road_Panel', PANEL, PANEL, 0.06, rough=0.55)
m_signs['u3_like'] = 'M_ObsSigns: lit, emissionMap = the albedo, emission 1, intensity 0.06 (retroreflective glow at night)'


def cutout_mat(name, path, tile):
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


m_chain = cutout_mat('M_Road_ChainLink', CHAIN, 0.5)
m_barb = cutout_mat('M_Road_Barbed', BARB, 0.5)


def mat_for(name):
    a = K.ATLAS[name]
    if a == 'panel':
        return m_signs
    if a == 'chainlink':
        return m_chain
    if a == 'barbed':
        return m_barb
    return BC.u3_mat('M_Reflector', MATDEF)


def target_of(name):
    for suf in ('_Face', '_Mesh', '_Barbed', '_Refl'):
        if name.endswith(suf):
            return name[:-len(suf)]
    return None


BC.join_all(objs, target_of, mat_for, log)

# ------------------------------------------------------------------ 4. the map: each root at its Update 3 place, in a collection
for n in ROOTS:
    o = objs[n]
    o.matrix_world = Matrix([list(r) for r in S.map_matrix(n)])
    col = bpy.data.collections.new(n)
    bpy.context.scene.collection.children.link(col)
    for c_ in list(o.users_collection):
        c_.objects.unlink(o)
    col.objects.link(o)
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 5. sockets, the contract
br = S.BRIDGE
for nm, p, note in (('Audio_BridgePlanks', (0.0, 0.0, 0.10), 'the deck: loose planks knock under feet and wheels'),
                    ('Audio_BridgeCreek', (2.5, 0.0, -11.3), 'the stream in the ravine under the bridge'),
                    ('Audio_BridgeTimber', (5.0, 0.0, -1.0), 'the timber creaks in the cold')):
    K.socket(nm, p, 'audio', parent='Bridge30', root='Bridge30', note=note)
K.socket('Audio_GateChain', (0.0, 0.06, S.GATE['lock_z']), 'audio', parent='ZoneGate', root='ZoneGate',
         note='the chain and the padlock knock against the tubes in the wind')
K.socket('Audio_GateWire', (0.0, 0.0, 2.65), 'audio', parent='ZoneGate', root='ZoneGate',
         note='the barbed wire hums in the wind')
K.socket('Audio_OverlookWind', (0.0, 3.0, 1.6), 'audio', parent='OverlookDeck', root='OverlookDeck',
         note='wind over the lake, the binoculars\' cap rattles')
K.socket('Look_OverlookScope', (1.4, 3.08, S.DECK['scope']['z']), 'look', parent='OverlookDeck', root='OverlookDeck',
         dir=(0, 1, 0), note='the binoculars\' eyepieces (they point over the lake to the hand)')
K.socket('Audio_Windfall', (16.0, 0.0, 0.3), 'audio', parent='FallenTree', root='FallenTree',
         note='the gap in the windfall (the road between the cuts)')
for k_, p in C['parts'].items():
    p['lightMask'] = 2                                 # exterior, as every road prefab in Update 3
    p['pivotUnity'] = BC.to_unity(p['pivot'])
    o = objs.get(k_)
    if o is not None:
        p['materials'] = [m.name for m in o.data.materials if m]
        p['object'] = k_
pl = {}
for n in ROOTS:
    if n == 'EuroPost':
        pl[n] = dict(list='rocks (scatter)', count=len(U3['europosts']), placements=U3['europosts'])
    else:
        e = U3['prefabs'][n][0]
        pl[n] = dict(p=e['p'], q=e['q'], list='prefabs')
C['meta'] = dict(
    units='metres, degrees',
    frames='each prefab its own frame - the frame of its Update 3 FBX after import: x / y / z, z up, origin = the prefab\'s '
           'pivot (the signs: the middle between the posts at the foot, the face to -y; the gate: the middle of the opening '
           'on the road; the bridge: the deck\'s middle at the planks\' top; the deck: the front edge\'s middle; the tree: '
           'the root plate\'s pit; the log: its middle)',
    unity='position (x, y, z) -> Unity prefab-local (-x, z, -y) (pivotUnity given); the placements are Update 3\'s '
          '(Forest_Layout.json) and stay as they are',
    blend='each root stands at its Update 3 place on the map (Blender map frame: Unity (x, y, z) -> (-x, -z, y)), in its own '
          'collection; the mesh is in the prefab\'s own frame: for an FBX of one prefab put its root at (0, 0, 0) with no '
          'rotation (EuroPost stands at the first of its 48 places)',
    map_placement=pl,
    hierarchy='every prefab is one mesh object, as Update 3 (the faces, chain-link, barbed wire and reflectors are joined in '
              'as extra materials)',
    colliders='as Update 3: a MeshCollider on every prefab (the chain-link and the barbed wire included); the bridge\'s deck '
              'keeps Update 3\'s levels: the planks\' top -0.01, the running strips +0.06 with ramps at the ends (the car crosses, '
              'S5); the windfall leaves the road clear between x 12.8 and 19.2 (FallenTree\'s frame)',
    light_layers='lightMask 2 on every object (exterior); no lights or glows (Update 3 had none on these prefabs)',
    materials='M_Road_Signs / Gate / Bridge / Deck / Windfall: baked PSX atlases (point filter, no mips); M_Road_Panel: the '
              'sign faces, lit, its emission = its albedo at 0.06 (the faint retroreflective glow of Update 3\'s M_ObsSigns); '
              'M_Road_ChainLink, M_Road_Barbed: alpha cut-out 0.5, tiled 0.5 m, two-sided quads; M_Reflector: Update 3\'s '
              '(emissive amber) on the EuroPost\'s reflectors',
    sockets='audio: the bridge (planks, creek, timber), the gate (chain, wire), the overlook (wind), the windfall; look: the '
            'binoculars',
    model='road.blend', textures='tex/road')
BC.psx_uv_only()
sfx = '_draft' if DRAFT else ('_test' if ONLY else '')
json.dump(BC.nz(C), open(os.path.join(OUT, f'road_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
INFO['tris'] = sum(P.tri_count(o) for o in meshes)
INFO['tris_by_object'] = {o.name: P.tri_count(o) for o in meshes}
INFO['objects'] = len(meshes)
INFO['materials'] = sorted({m.name for o in meshes for m in o.data.materials if m})
INFO['u3_tris'] = {n: v['tris'] for n, v in U3['u3_models'].items()}
log('tris', INFO['tris'], INFO['tris_by_object'], 'materials', INFO['materials'])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'road{sfx}.blend'))
json.dump(INFO, open(os.path.join(OUT, f'road{sfx}.json'), 'w'), indent=1)
log('saved road' + sfx)
