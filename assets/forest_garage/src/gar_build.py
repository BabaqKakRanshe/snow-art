"""Garage build (gar_kit + gar_paint): Update 3's three objects -- Garage (the static mesh: envelope, roof, hall and
contents, the glass, the signs and the lamp lenses joined in) with its two IX parts IX_GarageDoor_92 / IX_GarageSideDoor_93
on Update 3's pivots; PSX atlases at the generator shed's pixel density: Bld (outside and inside in one, as the shed's),
Parts (the two leaves); gar_tex's panel atlas on the signs; the materials the game knows by name (M_GlassDirty, M_Lamp_FluorOff,
M_Lamp_BulbOff -- the power system swaps the lamps); the contract (parts, sockets, Update 3's lights / glows / power,
the map placement).
python3 -I gar_build.py [--draft] [--only Bld,Parts] -> out/garage.blend, out/garage.json, out/garage_contract.json
--draft: no bakes (flat zone colours) -> out/garage_draft.blend"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector
import psxlib as P
import psxbake as PB
import gen_kit as K
import bld_common as BC

DRAFT = '--draft' in sys.argv
ONLY = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else (set() if DRAFT else None)
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'garage')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
PB.POS_SCALE = 20.0                                  # bake range +-10 m: the garage and its apron fit with room


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
import gar_tex as GT
PANEL_B = GT.build(TEX)
import gar_spec as S
import gar_kit as GK
import gar_paint as GP
import main_open as MO
import main_furn as F
import main_fx as FX

U3 = json.load(open(os.path.join(HERE, 'gar_u3_data.json')))
MATDEF = {m['name']: m for m in json.load(open(os.path.join(HERE, 'gar_u3_materials.json')))}

# ------------------------------------------------------------------ 1. geometry
GK.build_garage()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts']]
assert not missing, f'objects without a contract entry: {missing}'
NO_WELD = {K.Z_GALV, GK.Z_TRIM, GK.Z_FRAME, GK.Z_WINFRAME, GK.Z_FASCIA, GK.Z_SOFFIT, MO.Z_TRACK}
BC.prepare_kbs(NO_WELD)
INFO['coplanar_separated'] = BC.separate_coplanar([n for n in K.KBS if not BC.is_joined(K.ATLAS[n])], info=INFO)
log('coplanar overlapping faces pushed apart', INFO['coplanar_separated'], INFO['coplanar_moved_mm'])
objs = BC.make_objects(log)
log('objects', len(objs))

# ------------------------------------------------------------------ 2. atlases
groups = {}
for name, o in objs.items():
    a = K.ATLAS[name]
    if not BC.is_joined(a):
        groups.setdefault('Bld' if a in ('GarExt', 'GarIn') else a[3:], []).append(o)    # one building atlas, as the shed
log('atlases', {a: len(v) for a, v in groups.items()})
GLASS_OVERLAY = [o for n, o in objs.items() if BC.is_joined(K.ATLAS[n])]
VIVID = (F.Z_EXTING, F.Z_DRUM_R, F.Z_DRUM_B, F.Z_QUAD, F.Z_TOOL, F.Z_BAR, GK.Z_SPILL, F.Z_PUMPG, F.Z_COPPER, F.Z_BRASS,
         MO.Z_LOCK, GK.Z_BEAM, F.Z_JERRY, F.Z_SIGN)
SPEC = {'Bld': dict(cap=BC.SHED_PPM, ao_min=0.35, ao_dist=0.40, rough=0.85,
                   zs={GK.Z_FELT: 0.75, GK.Z_SOFFIT: 0.8, GK.Z_DECK: 0.85}),
        'Parts': dict(cap=64.0, ao_min=0.40, ao_dist=0.20, rough=0.75, zs=None, max=1024)}


def colour_of(z):
    return GK.DRAFT_COL.get(z) or MO.DRAFT_COL.get(z) or F.DRAFT_COL.get(z) or FX.DRAFT_COL.get(z) or (150, 148, 140)


INFO['atlases'] = BC.bake_groups(groups, ['Bld', 'Parts'], SPEC, GP.paint_gar, TEX, 'T_Gar_', 'M_Gar_', prio=VIVID,
                                 only=ONLY, colour_of=colour_of, hide_always=GLASS_OVERLAY, log=log)

# ------------------------------------------------------------------ 3. the named materials, glass, panel; joins
m_panel = P.psx_material('M_Gar_Panel', PANEL_B, rough=0.6)
LENS = {'fluoroff': 'M_Lamp_FluorOff', 'bulboff': 'M_Lamp_BulbOff'}


def mat_for(name):
    a = K.ATLAS[name]
    if a == 'glass':
        return BC.u3_mat('M_GlassDirty', MATDEF)
    if a == 'panel':
        return m_panel
    return BC.u3_mat(LENS[a.split(':', 1)[1]], MATDEF)


def target_of(name):
    for suf in ('__in', '__fluor', '__bulb', '_Panel', '_Glass'):
        if name.endswith(suf):
            return name[:-len(suf)]
    return None


BC.join_all(objs, target_of, mat_for, log)

# ------------------------------------------------------------------ 4. sockets: knocks (rays from outside), hands, audio
dg = bpy.context.evaluated_depsgraph_get()
nk = 0


def knock(name, org, d, parent_hint, note):
    global nk
    hit, loc, nrm, idx, ob, mw = bpy.context.scene.ray_cast(dg, Vector(org), Vector(d), distance=3.0)
    if not hit:
        log('WARN knock ray missed', name)
        return
    par = ob.name if ob.name in objs else parent_hint
    if nrm.dot(Vector(d)) > 0:
        nrm = -nrm
    C['sockets'][name] = dict(pos=BC.r4(loc + nrm * 0.005), kind='knock', parent=par, root=C['parts'][par]['root'],
                              dir=BC.r4(nrm), note=note)
    nk += 1


g, sd = S.GATE, S.SIDE
gx = (g['u'][0] + g['u'][1]) / 2
knock('Knock_GarageGate', (gx, -6.0, 1.30), (0, 1, 0), g['name'], 'the gate rattles: hit from outside')
knock('Knock_GarageSideDoor', (7.2, (sd['u'][0] + sd['u'][1]) / 2, 1.25), (-1, 0, 0), sd['name'], 'fists on the side door')
for w in S.WINDOWS:
    um = (w['u'][0] + w['u'][1]) / 2
    zm = (w['z'][0] + w['z'][1]) / 2
    sg = -1 if w['wall'] == 'S' else 1
    knock('Knock_' + w['name'], (um - 0.25, sg * 5.8, zm), (0, -sg, 0), 'Garage', 'something knocks on the glass from outside')
INFO['knock_points'] = nk
hu = sd['leaf_hi'][1] - 0.07
for side, xx in (('A', sd['leaf_hi'][0] + 0.07), ('B', sd['leaf_lo'][0] - 0.07)):
    K.socket(f'Hand_GarageSideDoor_{side}', (xx, hu, 1.05), 'hand', parent=sd['name'], root='Garage',
             note='the lever handle (' + ('outside' if side == 'A' else 'inside') + ')')
K.socket('Hand_GarageGate_A', (gx, -4.56, 1.05), 'hand', parent=g['name'], root='Garage',
         note='the gate\'s T-handle outside (turn, lift here)')
K.socket('Hand_GarageGate_B', (gx, -4.30, 1.05), 'hand', parent=g['name'], root='Garage',
         note='the gate\'s grip inside')
for nm, p, note in (('Audio_GarageGate', (gx, -4.0, 2.6), 'the gate: the springs, the steel rattles, the lock rods'),
                    ('Audio_GarageFluor', (0.0, 0.0, 4.2), 'the fittings hum (with power)'),
                    ('Audio_GarageRoof', (0.0, 0.0, 4.5), 'rain and wind on the steel roof and walls')):
    K.socket(nm, p, 'audio', parent='Garage', root='Garage', note=note)

# ------------------------------------------------------------------ 5. part boxes, light masks, the Update 3 data
INFO['part_boxes'] = BC.part_boxes(objs)
U3IX = {i['child']: i for i in U3['interactables']}
for k_, p in C['parts'].items():
    p['lightMask'] = 2                                   # Update 3: the Garage prefab's nodes had no assign: exterior
    p['pivotUnity'] = BC.to_unity(p['pivot'])
    if k_ in U3IX:
        u = U3IX[k_]
        p['u3'] = dict(kind=u['kind'], axisUnity=u['axis'], min=u['min'], max=u['max'], locked=u.get('locked', False))
    o = objs.get(k_)
    if o is not None:
        p['materials'] = [m.name for m in o.data.materials if m]
ixs = [n for n in C['parts'] if n.startswith('IX_')]
INFO['ix'] = dict(count=len(ixs), u3=len(U3IX), missing=sorted(set(U3IX) - set(ixs)), extra=sorted(set(ixs) - set(U3IX)))
log('IX parts', INFO['ix'])
C['lighting'] = dict(rooms=[], assign='every part carries lightMask 2 (the exterior layer: Update 3 assigned nothing in '
                                      'the Garage prefab, its lights are tagged room Exterior)')
C['prefabLights'] = U3['prefabLights']
C['prefabGlows'] = U3['prefabGlows']
C['power'] = U3['power']
C['locks'] = {g['name']: S.LOCK_KEY, sd['name']: S.LOCK_KEY}

# ------------------------------------------------------------------ 6. meta, stats, save
C['meta'] = dict(
    units='metres, degrees',
    frames='the building frame: x east, y north, z up, origin = the hall\'s floor in the middle of the hall (floor 0.0, '
           'the ground round it -0.10, eaves 4.40, roof 4.64) - the frame of Update 3\'s Garage.fbx after import',
    unity='position (x, y, z) -> Unity prefab-local (-x, z, -y) (pivotUnity given); a hinge\'s Blender axis is Update 3\'s '
          'Unity axis as (X, Z, -Y) with angle -> -angle; u3.axisUnity / min / max are Update 3\'s values and stay valid '
          '(same names, pivots and ranges); part.box: the grab / hit box of a moving part in its own frame',
    map_placement=dict(Garage=S.PLACE),
    hierarchy='Garage (one static mesh, as Update 3) > IX_GarageDoor_92, IX_GarageSideDoor_93',
    colliders='as Update 3: a MeshCollider on every mesh object (the glass included); no separate boxes',
    light_layers='lightMask 2 on every object (exterior layer, as Update 3 had it); prefabLights / prefabGlows are Update '
                 '3\'s, unchanged: the fittings and the bulkhead stand where those lights are',
    materials='M_Gar_Bld (on Garage: outside and inside, one atlas as the shed\'s) / M_Gar_Parts (the two leaves): baked '
              'PSX atlases (point filter, no mips); '
              'M_Gar_Panel: signs, labels, papers; named materials kept from Update 3 (the game swaps or knows them): '
              'M_Lamp_FluorOff (the two fittings\' diffusers -> M_Lamp_Fluor with power), M_Lamp_BulbOff (the bulkhead '
              'over the gate -> M_Lamp_Bulb), M_GlassDirty (the windows) - their definitions stay those of '
              'Forest_Materials.json',
    sockets='knock: on the gate, the side door and each window from outside (scares); hand: the handles; audio',
    locks='both doors locked as Update 3 (Forest_Opening.json: key Garage, Item_Key_Garage in the checkpoint\'s key box)',
    model='garage.blend', textures='tex/garage')
BC.psx_uv_only()
sfx = '_draft' if DRAFT else ('_test' if ONLY else '')
json.dump(BC.nz(C), open(os.path.join(OUT, f'garage_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
kinds = {}
for p in C['parts'].values():
    kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
INFO['contract'] = dict(parts=len(C['parts']), sockets=len(C['sockets']), kinds=kinds)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
INFO['tris'] = sum(P.tri_count(o) for o in meshes)
INFO['tris_by_object'] = {o.name: P.tri_count(o) for o in meshes}
INFO['objects'] = len(meshes)
INFO['materials'] = sorted({m.name for o in meshes for m in o.data.materials if m})
log('contract', INFO['contract'], 'tris', INFO['tris'], INFO['tris_by_object'], 'materials', INFO['materials'])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'garage{sfx}.blend'))
json.dump(INFO, open(os.path.join(OUT, f'garage{sfx}.json'), 'w'), indent=1)
log('saved garage' + sfx)
