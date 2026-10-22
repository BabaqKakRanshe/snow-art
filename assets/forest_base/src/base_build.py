"""Base prefabs build (base_kit + base_paint): the shaft hatch, the helipad, the radio mast, the crates, the log pile, the
yard light, the power pole, the chain-link and old fences, the overhead line - each Update 3 prefab one object (its
static mesh, the sign faces / lenses / cut-outs joined in as Update 3's FBX; the hatch's lid IX_HatchLid_94 a child),
its root at its Update 3 place on the map (Blender frame of the map: Unity (x, y, z) -> (-x, -z, y)); PSX atlases at the
generator shed's pixel density, baked with each prefab in its own frame and the ground under it (Update 3's terrain,
base_ground.json) for the contact shading: Props (hatch, crates, logs), Helipad, Mast, Poles, Fence; base_tex's sign
panel (the faces glow faintly at night, as Update 3's M_ObsSigns), the chain-link / barbed / rusty-wire cut-outs,
Update 3's lamp materials on the lenses (M_Lamp_SodiumOff, M_Lamp_WarmOff, M_Light_Red), Forest_Wires in Update 3's
M_Cable (+ M_Galvanized, M_Enamel on the risers); the contract (prefabs, placements, sockets, materials).
python3 -I base_build.py [--draft] [--only Props,Helipad,...] -> out/base.blend, out/base.json, out/base_contract.json
--draft: no bakes (flat zone colours) -> out/base_draft.blend"""
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
TEX = os.path.join(HERE, 'tex', 'base')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
PB.POS_SCALE = 140.0                                 # bake range +-70 m: the mast is 64.6 m tall, its anchors 33 m out


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
import base_tex as BT
PANEL, CHAIN, BARB, RUSTY = BT.build(TEX)
import base_spec as S
import base_kit as BK
import base_paint as BP

U3 = S.U3
MATDEF = U3['materials']

# ------------------------------------------------------------------ 1. geometry
BK.build_base()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts']]
assert not missing, f'objects without a contract entry: {missing}'
NO_WELD = {BK.Z_HHINGE, BK.Z_HLOCK, BK.Z_CSTEEL, BK.Z_CSTRAW, BK.Z_CROPE, BK.Z_LBOLT, BK.Z_MTURN, BK.Z_MPLATE, BK.Z_PGALV,
           BK.Z_SFRAME, BK.Z_ROPE, BK.Z_SCLAMP,
           BK.Z_MLEG, BK.Z_MBAR, BK.Z_MGUY, BK.Z_MLADDER, BK.Z_MTRAY, BK.Z_MCOAX}   # the mast's members stay short islands
CUTOUT = ('chainlink', 'barbed', 'rust')


def joined_atlas(a):
    return a in ('glass', 'panel') or a.startswith('lens:') or a in CUTOUT


BC.is_joined = joined_atlas                           # the cut-outs are joined into their owners as the panel is
BC.face_out = lambda k: None                          # the lenses are built facing out (lathes, the flat lens down)
BC.prepare_kbs(NO_WELD)
INFO['coplanar_separated'], moved = 0, {}
for n_ in [n for n in K.KBS if not joined_atlas(K.ATLAS[n]) and K.ATLAS[n] != 'cable']:
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
import unwrap_fast as UF                              # the road build's fast unwrap (Blender's box packing)
P.unwrap_group = UF.unwrap_fast
GROUPS = ('Props', 'Helipad', 'Mast', 'Poles', 'Fence')
groups = {}
for name, o in objs.items():
    a = K.ATLAS[name]
    if a in GROUPS:
        groups.setdefault(a, []).append(o)
log('atlases', {a: [o.name for o in v] for a, v in groups.items()})
SPEC = {'Props': dict(cap=BC.SHED_PPM, ao_min=0.38, ao_dist=0.30, rough=0.80, zs=None, max=1024),
        'Helipad': dict(cap=BC.SHED_PPM, ao_min=0.38, ao_dist=0.40, rough=0.85, zs={BK.Z_PAD: 0.5, BK.Z_PADSIDE: 0.6},
                        max=1024),
        'Mast': dict(cap=BC.SHED_PPM, ao_min=0.40, ao_dist=0.30, rough=0.75,
                     zs={BK.Z_MGUY: 0.3, BK.Z_MBAR: 0.6, BK.Z_MLEG: 0.7, BK.Z_MLADDER: 0.7, BK.Z_MCOAX: 0.5, BK.Z_MTRAY: 0.6,
                         BK.Z_MFOOT: 0.7, BK.Z_MANCH: 0.7}, max=1024),
        'Poles': dict(cap=BC.SHED_PPM, ao_min=0.40, ao_dist=0.25, rough=0.75, zs=None, max=512),
        'Fence': dict(cap=BC.SHED_PPM, ao_min=0.40, ao_dist=0.25, rough=0.80, zs=None, max=512)}
VIVID = (BK.Z_SOCKR, BK.Z_EXTBOX, BK.Z_MLEG, BK.Z_MBAR, BK.Z_PAD, BK.Z_PPLATE, BK.Z_HLOCK, BK.Z_LEND)
LAYOUTS = {'Props': {'Hatch': (0.0, 0.0, 0.0), 'Crates': (7.0, 0.0, 0.0), 'LogPile': (14.0, 0.0, 0.0)},
           'Helipad': {'Helipad': (0.0, 0.0, 0.0)},
           'Mast': {'RadioMast': (0.0, 0.0, 0.0)},
           'Poles': {'LightPole': (0.0, 0.0, 0.0), 'PowerPole': (4.0, 0.0, 0.0)},
           'Fence': {'FenceChain': (0.0, 0.0, 0.0), 'OldFence': (6.0, 0.0, 0.0), 'OldFence_b': (12.0, 0.0, 0.0),
                     'OldFence_c': (18.0, 0.0, 0.0)}}
GROUNDS = {'Hatch': (-2.5, 3.0, -2.6, 2.5, 0.25), 'Crates': (-2.0, 2.0, -1.6, 1.4, 0.25), 'LogPile': (-3.5, 3.5, -1.6, 1.6, 0.25),
           'Helipad': (-14.5, 17.0, -13.0, 12.0, 0.5), 'RadioMast': (-34.0, 34.0, -35.0, 26.0, 1.0),
           'LightPole': (-1.0, 2.0, -1.0, 1.0, 0.25), 'PowerPole': (-1.6, 1.6, -1.0, 1.0, 0.25)}


def ground_patch(name, x0, x1, y0, y1, step):
    xs = np.arange(x0, x1 + 1e-6, step)
    ys = np.arange(y0, y1 + 1e-6, step)
    verts = [(float(x), float(y), S.ground(name, float(x), float(y))) for y in ys for x in xs]
    nx = len(xs)
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(len(ys) - 1)
             for i in range(nx - 1)]
    return verts, faces


def ground_objects(lay):
    """the ground under each root of the layout (AO only); the fences stand on a flat plane"""
    made = []
    for n, off in lay.items():
        if n in GROUNDS:
            v, f = ground_patch(n, *GROUNDS[n])
        else:
            v = [(-2.6, -1.0, 0.0), (2.6, -1.0, 0.0), (2.6, 1.0, 0.0), (-2.6, 1.0, 0.0)]
            f = [(0, 1, 2, 3)]
        me = bpy.data.meshes.new('AOG_' + n)
        me.from_pydata([(a + off[0], b + off[1], c + off[2]) for a, b, c in v], [], f)
        ob = bpy.data.objects.new('AOG_' + n, me)
        bpy.context.scene.collection.objects.link(ob)
        made.append(ob)
    return made


def colour_of(z):
    return BK.DRAFT_COL.get(z, (150, 148, 140))


GLASSLIKE = [o for n, o in objs.items() if joined_atlas(K.ATLAS[n]) or K.ATLAS[n] == 'cable']
INFO['atlases'] = {}
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
    BP.LAYOUT = lay
    BC.bake_groups({a: groups[a]}, [a], SPEC, BP.paint_base, TEX, 'T_Base_', 'M_Base_', prio=VIVID, only=ONLY,
                   colour_of=colour_of, hide_always=GLASSLIKE, log=log, info=INFO['atlases'])
    for g_ in grounds:
        me = g_.data
        bpy.data.objects.remove(g_)
        bpy.data.meshes.remove(me)
    BC.hidden(others, False)
    for n in lay:
        objs[n].location = keep[n]
    bpy.context.view_layer.update()

# ------------------------------------------------------------------ 3. materials: the panel, the cut-outs, the lenses, the wires
m_panel = PB.tex_mat('M_Base_Panel', PANEL, PANEL, 0.06, rough=0.55)
m_panel['u3_like'] = 'M_ObsSigns: lit, emissionMap = the albedo, emission 1, intensity 0.06 (retroreflective glow at night)'


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


m_chain = cutout_mat('M_Base_ChainLink', CHAIN, 0.5)
m_barb = cutout_mat('M_Base_Barbed', BARB, 0.5)
m_rust = cutout_mat('M_Base_Rust', RUSTY, 0.5)
LENS = {'lens:sodium': 'M_Lamp_SodiumOff', 'lens:warm': 'M_Lamp_WarmOff', 'lens:red': 'M_Light_Red'}


def mat_for(name):
    a = K.ATLAS[name]
    if a == 'panel':
        return m_panel
    if a == 'chainlink':
        return m_chain
    if a == 'barbed':
        return m_barb
    if a == 'rust':
        return m_rust
    return BC.u3_mat(LENS[a], MATDEF)


def target_of(name):
    if name == 'Forest_Wires':
        return None
    for suf in ('_Sign', '_Lens', '_Mesh', '_Barbed', '_Wire'):
        if name.endswith(suf):
            return name[:-len(suf)]
    return None


BC.join_all(objs, target_of, mat_for, log)
w = objs['Forest_Wires']                               # the line: Update 3's materials by zone
me = w.data
me.materials.clear()
for mn in ('M_Cable', 'M_Galvanized', 'M_Enamel'):
    me.materials.append(BC.u3_mat(mn, MATDEF))
zl = [int(round(a.value)) for a in me.attributes['zone'].data]
for poly, zz in zip(me.polygons, zl):
    poly.material_index = zz
if 'PSX' not in me.uv_layers:                          # an empty UV channel (the materials are flat)
    me.uv_layers.new(name='PSX')

# ------------------------------------------------------------------ 4. the map: each root at its Update 3 place, in a collection
for n in ROOTS:
    o = objs[n]
    if n != 'Forest_Wires':
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
h = S.HATCH
K.socket('Audio_ShaftVent', (h['vent'][0], h['vent'][1], h['vent_top']), 'audio', parent='Hatch', root='Hatch',
         note='the shaft breathes through the vent: a low draught, now and then a knock from below')
K.socket('Audio_HatchLock', (h['staple_x'], 0.0, h['staple_top']), 'audio', parent='Hatch', root='Hatch',
         note='the padlock knocks against the staple in the wind')
K.socket('Audio_Windsock', (S.HELI['sock'][0] + 1.5, S.HELI['sock'][1], S.HELI['sock_top'] - 0.4), 'audio', parent='Helipad',
         root='Helipad', note='the windsock flaps, the swivel squeaks')
K.socket('Audio_MastGuys', (0.0, 0.0, 30.0), 'audio', parent='RadioMast', root='RadioMast',
         note='the guys hum in the wind, ice drops from the lattice')
K.socket('Audio_LineHum', (0.0, 0.0, S.PPOLE['insul_top']), 'audio', parent='PowerPole', root='PowerPole',
         note='the line hums when the generator runs (the power grid on), the insulators crackle in rain')
INFO['part_boxes'] = BC.part_boxes(objs)
for k_, p in C['parts'].items():
    p['lightMask'] = 2                                 # exterior, as every Forest prefab in Update 3
    p['pivotUnity'] = BC.to_unity(p['pivot'])
    o = objs.get(k_)
    if o is not None:
        p['materials'] = [m.name for m in o.data.materials if m]
        p['object'] = k_
pl = {}
for n in ROOTS:
    if n == 'Forest_Wires':
        pl[n] = dict(list='world model (the map frame, at the origin)')
    elif n in U3['scatter']:
        pl[n] = dict(list='rocks (scatter)', count=len(U3['scatter'][n]), first=U3['scatter'][n][0])
    else:
        es = U3['prefabs'][n]
        pl[n] = dict(list='prefabs', count=len(es), placements=[dict(p=e['p'], q=e['q']) for e in es])
C['meta'] = dict(
    units='metres, degrees',
    frames='each prefab its own frame - the frame of its Update 3 FBX after import: x / y / z, z up, origin = the prefab\'s '
           'pivot (Update 3\'s); Forest_Wires is in the map frame',
    unity='position (x, y, z) -> Unity prefab-local (-x, z, -y) (pivotUnity given); the placements are Update 3\'s '
          '(Forest_Layout.json) and stay as they are',
    axes='hinge axes and angles in Blender terms (right-handed, +angle opens); in Unity the axis converts as a position '
         'and the angle changes sign - the same axes and signs as Update 3\'s interactables (IX_HatchLid_94: (0, -1, 0) -> Unity (0, 0, -1), +100 deg lifts the lid)',
    blend='each root stands at its Update 3 place on the map (the scatter prefabs at their first place), in its own '
          'collection; for an FBX of one prefab put its root at (0, 0, 0) with no rotation',
    map_placement=pl,
    hierarchy='every prefab is one mesh object, as Update 3 (the sign faces, lenses, chain-link and wires are joined in as '
              'extra materials); the hatch\'s lid IX_HatchLid_94 is its child (hinge, locked: Update 3\'s interactable)',
    lights='unchanged: Update 3\'s lights and halos (RadioMast beacons at 20 / 40 / 60 m, the LightPole\'s spot and halo) '
           'sit in the new lenses',
    materials='M_Base_Props / Helipad / Mast / Poles / Fence: baked PSX atlases (point filter, no mips); M_Base_Panel: the '
              'sign faces, lit, emission = albedo at 0.06 (as M_ObsSigns); M_Base_ChainLink / Barbed / Rust: alpha cut-out 0.5, '
              'tiled 0.5 m, two-sided quads; Update 3\'s M_Lamp_SodiumOff, M_Lamp_WarmOff (the power grid swaps them), '
              'M_Light_Red (always lit), M_Cable, M_Galvanized, M_Enamel',
    sockets='audio: the shaft vent, the hatch\'s padlock, the windsock, the mast\'s guys, the line',
    model='base.blend', textures='tex/base')
BC.psx_uv_only()
sfx = '_draft' if DRAFT else ('_test' if ONLY else '')
json.dump(BC.nz(C), open(os.path.join(OUT, f'base_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
INFO['tris'] = sum(P.tri_count(o) for o in meshes)
INFO['tris_by_object'] = {o.name: P.tri_count(o) for o in meshes}
INFO['objects'] = len(meshes)
INFO['materials'] = sorted({m.name for o in meshes for m in o.data.materials if m})
INFO['u3_tris'] = {n: v['tris'] for n, v in U3['u3_models'].items()}
log('tris', INFO['tris'], INFO['tris_by_object'], 'materials', INFO['materials'])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'base{sfx}.blend'))
json.dump(INFO, open(os.path.join(OUT, f'base{sfx}.json'), 'w'), indent=1)
log('saved base' + sfx)
