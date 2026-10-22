"""Fence and road-block kit build (fence_kit + fence_paint): each prefab one object (its static mesh, the sign faces
and cut-outs joined in), PSX atlases at the generator shed's pixel density baked with each prefab on a flat ground
(contact shading): Concrete (PO-2 panels, sockets, outriggers, the wicket, the blocks, the teeth) and Props
(chain-link posts, the coil's stakes, the hedgehog, the cheval de frise, the abatis, the signs); fence_tex's sign panel
(faint glow at night like the other signs) and the cut-outs (netting, barbed, razor) as one-sided materials.
In the blend the prefabs stand in a row (their own collections), each at its own place along x.
python3 -I fence_build.py [--draft] [--only Concrete,Props] -> out/fences.blend, out/fences.json, out/fences_contract.json"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy
import numpy as np
from mathutils import Vector, Matrix
import psxlib as P
import psxbake as PB
import gen_kit as K
import bld_common as BC

DRAFT = '--draft' in sys.argv
ONLY = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else (set() if DRAFT else None)
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'fence')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
T0 = time.time()
INFO = {}
PB.POS_SCALE = 140.0


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
import fence_tex as FT
PANEL, NET, BARB, CBARB, RAZOR = FT.build(TEX)
REPL = FT.replacements(os.path.join(TEX, 'replacements'))
import fence_spec as S
import fence_kit as FK
import fence_paint as FP

# ------------------------------------------------------------------ 1. geometry
FK.build_all()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts']]
assert not missing, f'objects without a contract entry: {missing}'
CUTOUT = ('chainlink', 'barbed', 'chainbarbed', 'razor')


def joined_atlas(a):
    return a in ('glass', 'panel') or a.startswith('lens:') or a in CUTOUT


BC.is_joined = joined_atlas
BC.face_out = lambda k: None
BC.prepare_kbs((FK.Z_REBAR, FK.Z_LOOP))
INFO['coplanar_separated'] = 0
for n_ in [n for n in K.KBS if not joined_atlas(K.ATLAS[n])]:
    INFO['coplanar_separated'] += BC.separate_coplanar([n_])
objs = BC.make_objects(log)
ROOTS = [n for n, p in C['parts'].items() if not p.get('parent')]
assert sorted(ROOTS) == sorted(FK.MODELS), (sorted(ROOTS), sorted(FK.MODELS))
log('objects', len(objs), 'roots', len(ROOTS))

# ------------------------------------------------------------------ 2. atlases
import unwrap_fast as UF
P.unwrap_group = UF.unwrap_fast
GROUPS = ('Concrete', 'Props')
groups = {}
for name, o in objs.items():
    a = K.ATLAS[name]
    if a in GROUPS:
        groups.setdefault(a, []).append(o)
SPEC = {'Concrete': dict(cap=BC.SHED_PPM, ao_min=0.40, ao_dist=0.30, rough=0.85, zs=None, max=1024),
        'Props': dict(cap=BC.SHED_PPM, ao_min=0.40, ao_dist=0.25, rough=0.80, zs=None, max=512)}
VIVID = (FK.Z_JSTRIPE, FK.Z_WFRAME, FK.Z_WDOOR, FK.Z_REBAR)
LAYOUTS = {'Concrete': {'ConcreteFence': (0.0, 0, 0), 'ConcreteFence_b': (5.0, 0, 0), 'ConcreteFence_Broken': (10.0, 0, 0),
                        'ConcreteFence_Sign': (15.0, 0, 0), 'ConcreteFence_Plain': (20.0, 0, 0),
                        'ConcreteFence_Socket': (25.0, 0, 0), 'ConcreteFence_Wicket': (30.0, 0, 0),
                        'RoadBlock_FBS': (36.0, 0, 0), 'RoadBlock_Jersey': (40.0, 0, 0),
                        'RoadBlock_Jersey_Striped': (44.0, 0, 0), 'RoadBlock_Cube': (48.0, 0, 0), 'TankTooth': (51.5, 0, 0),
                        'TankTooth_b': (55.0, 0, 0)},
           'Props': {'ChainFence': (0.0, 0, 0), 'ChainFence_Torn': (5.0, 0, 0), 'WireCoil': (11.0, 0, 0),
                     'Hedgehog': (17.0, 0, 0), 'WireBarricade': (21.0, 0, 0), 'Abatis': (28.5, 0, 0),
                     'Abatis_b': (38.0, 0, 0), 'Sign_Halt': (45.0, 0, 0), 'Sign_NoEntry': (48.0, 0, 0)}}


def ground_objects(lay):
    made = []
    for n, off in lay.items():
        o = objs[n]
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        x0 = min(v.x for v in bb) - 0.8
        x1 = max(v.x for v in bb) + 0.8
        y0 = min(v.y for v in bb) - 0.8
        y1 = max(v.y for v in bb) + 0.8
        me = bpy.data.meshes.new('AOG_' + n)
        me.from_pydata([(x0, y0, 0.0), (x1, y0, 0.0), (x1, y1, 0.0), (x0, y1, 0.0)], [], [(0, 1, 2, 3)])
        ob = bpy.data.objects.new('AOG_' + n, me)
        bpy.context.scene.collection.objects.link(ob)
        made.append(ob)
    return made


def colour_of(z):
    return FK.DRAFT_COL.get(z, (150, 148, 140))


GLASSLIKE = [o for n, o in objs.items() if joined_atlas(K.ATLAS[n])]
INFO['atlases'] = {}
for a in GROUPS:
    if a not in groups:
        continue
    lay = LAYOUTS[a]
    for n, off in lay.items():
        objs[n].location = Vector(off)
    names = [g.name for g in groups[a]]
    others = [o for o in objs.values() if o.name not in names and o.parent is None and o.name not in lay]
    BC.hidden(others)
    bpy.context.view_layer.update()
    grounds = [] if (ONLY is not None and a not in ONLY) else ground_objects(lay)
    bpy.context.view_layer.update()
    FP.LAYOUT = lay
    BC.bake_groups({a: groups[a]}, [a], SPEC, FP.paint_fence, TEX, 'T_Fence_', 'M_Fence_', prio=VIVID, only=ONLY,
                   colour_of=colour_of, hide_always=GLASSLIKE, log=log, info=INFO['atlases'])
    for g_ in grounds:
        me = g_.data
        bpy.data.objects.remove(g_)
        bpy.data.meshes.remove(me)
    BC.hidden(others, False)
    bpy.context.view_layer.update()

# ------------------------------------------------------------------ 3. materials: the panel, the cut-outs
m_panel = PB.tex_mat('M_Fence_Panel', PANEL, PANEL, 0.06, rough=0.55)


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
    m['one_sided'] = True                       # each cut-out quad is two faces 2.4 mm apart: no backface drawing
    m.use_backface_culling = True
    try:
        m.surface_render_method = 'DITHERED'
    except AttributeError:
        pass
    return m


MATS = {'chainlink': cutout_mat('M_Fence_ChainLink', NET, 0.5), 'barbed': cutout_mat('M_Fence_Barbed', BARB, 0.5),
        'chainbarbed': cutout_mat('M_Fence_ChainBarbed', CBARB, 0.5), 'razor': cutout_mat('M_Fence_Razor', RAZOR, 0.5),
        'panel': m_panel}


def mat_for(name):
    return MATS[K.ATLAS[name]]


def target_of(name):
    if name in FK.MODELS:
        return None
    for suf in ('_Sign', '_Mesh', '_Barbed', '_Razor'):
        if name.endswith(suf):
            return name[:-len(suf)]
    return None


BC.join_all(objs, target_of, mat_for, log)

# ------------------------------------------------------------------ 4. the showroom: each prefab in its own collection
ROW = {}
x = 0.0
for n in FK.MODELS:
    o = objs[n]
    o.location = Vector((0, 0, 0))
    bpy.context.view_layer.update()
    bb = [Vector(c) for c in o.bound_box]
    x0, x1 = min(v.x for v in bb), max(v.x for v in bb)
    x += -x0 + 0.6
    o.location = Vector((x, 0.0, 0.0))
    ROW[n] = round(x, 3)
    x += x1 + 0.6
    col = bpy.data.collections.new(n)
    bpy.context.scene.collection.children.link(col)
    for c_ in list(o.users_collection):
        c_.objects.unlink(o)
    col.objects.link(o)
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 5. the contract
INFO['part_boxes'] = BC.part_boxes(objs)
for k_, p in C['parts'].items():
    p['lightMask'] = 2
    p['pivotUnity'] = BC.to_unity(p['pivot'])
    o = objs.get(k_)
    if o is not None:
        p['materials'] = [m.name for m in o.data.materials if m]
        p['object'] = k_
C['meta'] = dict(
    units='metres, degrees',
    frames='each prefab its own frame: x along the fence / block, y across (-y = the outside: the relief, the signs, the '
           'barbed outriggers\' outer arm, the abatis\' spikes), z up, origin = the pivot on the ground in the middle',
    unity='position (x, y, z) -> Unity prefab-local (-x, z, -y) (pivotUnity given)',
    blend='the prefabs stand in a row along x (showroom), each in its own collection; for an FBX of one prefab put its '
          'root at (0, 0, 0) with no rotation',
    row=ROW,
    hierarchy='every prefab is one mesh object (the sign faces and the cut-outs joined in as extra materials)',
    materials='M_Fence_Concrete / Props: baked PSX atlases (point filter); M_Fence_Panel: the sign faces, lit, emission = '
              'albedo at 0.06; M_Fence_ChainLink / Barbed / ChainBarbed / Razor: alpha cut-out 0.5, tiled 0.5 m, ONE-SIDED '
              '(every cut-out quad is two faces 2.4 mm apart, each facing out) - mip maps with Preserve Coverage',
    replacements='T_Base / Kpp / Yard / Road _ChainLink and _Barbed, T_Base_Rust: the same files, sizes, tilings and '
                 'strand heights as Updates 4-5, drawn anew (2 px wires, 16 px diamonds, RGB under the holes = the wire '
                 'colour); their materials become one-sided',
    model='fences.blend', textures='tex/fence')
BC.psx_uv_only()
sfx = '_draft' if DRAFT else ('_test' if ONLY else '')
json.dump(BC.nz(C), open(os.path.join(OUT, f'fences_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
INFO['tris'] = sum(P.tri_count(o) for o in meshes)
INFO['tris_by_object'] = {o.name: P.tri_count(o) for o in meshes}
INFO['objects'] = len(meshes)
INFO['materials'] = sorted({m.name for o in meshes for m in o.data.materials if m})
INFO['replacements'] = REPL
log('tris', INFO['tris'], INFO['tris_by_object'], 'materials', INFO['materials'])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'fences{sfx}.blend'))
json.dump(INFO, open(os.path.join(OUT, f'fences{sfx}.json'), 'w'), indent=1)
log('saved fences' + sfx)
