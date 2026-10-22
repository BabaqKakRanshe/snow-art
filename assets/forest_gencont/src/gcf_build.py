"""GenContainer for the Forest map (Update 6): the generator container (cont_kit + gcf_kit) built and baked in the
container frame exactly as the standalone package (cont_build: the shed's interior moved in, atlases Cont / Genset /
Props + the panel), then turned onto Update 3's GenContainer:

  frame     Update 3's FBX frame of GenContainer (x along the box, the cargo doors at +x; y across; z up; ground z = 0,
            Unity prefab-local = (-x, z, -y)): p_u3 = (-x, -y - 1.22, z) of the container frame - turned 180 deg, the
            south box (generator, board, cargo doors) on Update 3's footprint, the north box (day tank, drums, shelf;
            the side door and the fill box in its front end) beside it on the -y side (Unity +z)
  names     Update 3's interactable parts: Door_L -> IX_ContDoorL_83, Door_R -> IX_ContDoorR_84, the new side door
            IX_ContSideDoor_85, Gen_Key -> IX_GenStart_86, Board_MCB_1..3 -> IX_Breaker_87..89, Board_Changeover ->
            IX_MainSwitch_90, the fill box lid IX_GenFillCap_300
  objects   as Update 3's: the root GenContainer (everything static joined in, by material) + the nine IX parts (each
            with what moves with it joined in: bars, bolt, signs) + Window_Glass
  materials M_GCont_Cont / Genset / Props / Panel (atlases), M_GCont_Needle, M_GCont_Diesel; the lamp glass in Update 3's
            M_Lamp_BulbOff (the power grid swaps it to M_Lamp_Bulb), the RUN and GEN lamps in M_LEDOff (-> M_LEDOn),
            the window and the sight glass in M_GlassClear
  data      prefabLights / prefabGlows / interactables / the viewpoint for Forest_Layout.json, Gen_FillNeck for
            Forest_Opening.json - all in out/gcf.json (u6_build writes them)

python3 -I gcf_build.py [--draft] -> out/gcf.blend, out/gcf.json, out/gcf_contract.json, tex/gcf/*"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
import psxlib as P
import psxbake as PB
import cont_tex as CT
import gen_tex as GT
import gen_kit as K
import gen_set as GS
import gen_room as GR
import cont_kit as CK
import gcf_kit as FK
import gen_paint as GP
import bld_common as BC

DRAFT = '--draft' in sys.argv
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'gcf')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
T0 = time.time()
INFO = {}
SCR = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/'
U3M = {m['name']: m for m in json.load(open(SCR + 'u3/Assets/Locations/Forest/Data/Forest_Materials.json'))['materials']}
U3L = json.load(open(SCR + 'u3/Assets/Locations/Forest/Data/Forest_Layout.json'))
U3O = json.load(open(SCR + 'u3/Assets/Locations/Forest/Data/Forest_Opening.json'))
PLACE = next(p for p in U3L['prefabs'] if p['m'] == 'GenContainer')
DY = -1.22                                             # container frame -> Update 3's frame: (-x, -y + DY, z)


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


r4 = BC.r4


def to_u3(v):
    return Vector((-v[0], -v[1] + DY, v[2]))


def ax_u3(a):
    return Vector((-a[0], -a[1], a[2]))


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
PB_BASE, PB_EMI = CT.build(TEX)

# ------------------------------------------------------------------ 1. geometry: the shed's interior, then the container
GR.FUEL_ROUTES = CK.fuel_routes_shed()
K.kb('Shed', 'Cont')
GS.build_genset()
GR.switchboard()
GR.day_tank()
GR.drums()
GR.pump()
GR.shelf_and_props()
C = K.CONTRACT
for n in ('Funnel',):                                  # the prologue's funnel is the hut's (Item_Funnel)
    K.KBS.pop(n).bm.free()
    K.ATLAS.pop(n)
    C['parts'].pop(n)
    for s in [s for s, d in C['sockets'].items() if d.get('parent') == n or s.endswith('_' + n)]:
        C['sockets'].pop(s)
interior = [n for n in K.KBS if n != 'Shed']
shift = {n: CK.group_of(C, n) for n in interior}
sock_shift = {n: CK.group_of(C, n) for n in C['sockets']}
nail = K.KBS.pop('Shed')
K.ATLAS.pop('Shed')
for d in list(C['parts'].values()) + list(C['sockets'].values()):
    if d.get('parent') == 'Shed':
        d['parent'] = 'GenContainer'
dt = GR.DT                                             # the day tank's top (container frame): where the fill pipe goes in
FK.TANK_IN = Vector((dt['x0'] + 0.23 + CK.G_N.x, (dt['y0'] + dt['y1']) / 2 + CK.G_N.y, dt['z1'] + CK.G_N.z))
log('day tank top (fill pipe in)', tuple(round(a, 3) for a in FK.TANK_IN))
FK.build_container()
K.merge_kb(K.KBS['GenContainer_In'], nail, Matrix.Translation(CK.NAIL_GROUP))
missing = [n for n in K.KBS if n not in C['parts']]
assert not missing, f'objects without a contract entry: {missing}'
log('interior objects', len(interior), 'container objects', len(K.KBS) - len(interior))
objs = {}
WELD = ('GenContainer', 'GenContainer_In', 'Door_R', 'Door_L', 'IX_ContSideDoor_85')
for name, k in K.KBS.items():
    if name in WELD:
        bmesh.ops.remove_doubles(k.bm, verts=list(k.bm.verts), dist=1e-4)
    objs[name] = k.to_object(name, pivot=Vector(C['parts'][name]['pivot']))
log('objects', len(objs))
groups = {}
for name, o in objs.items():
    groups.setdefault(K.ATLAS[name], []).append(o)

# ------------------------------------------------------------------ 2. Genset / Props: positions in the shed frame
prep = {}
if not DRAFT:
    prep['Genset'] = PB.prepare_atlas(groups['Genset'], size=512)
    prep['Props'] = PB.prepare_atlas(groups['Props'], size=512)
    log('prepared Genset, Props in the shed frame')
for name in interior:
    objs[name].location += shift[name]
    C['parts'][name]['pivot'] = r4(Vector(C['parts'][name]['pivot']) + shift[name])
for n, off in sock_shift.items():
    if n in C['sockets']:
        C['sockets'][n]['pos'] = r4(Vector(C['sockets'][n]['pos']) + off)
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 3. atlases (the container's painter + the new cut-ins)
import cont_paint as CPT
import pxfont as F
from noise import ss, mixc, fbm
from gen_paint import _common, RUST_D



def paint_gcf_all(Pp, Nn, Z, ao, aa):
    """the container's painter, then fresh paint round the new cut-ins in the north box's front end (the side door's
    frame, the fill box) and rust at their cut edges, as round the window and the louvre"""
    col, gr = CPT.paint_cont_all(Pp, Nn, Z, ao, aa)
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 561)
    wob = fbm(Pp, 9.0, 2, seed=562)
    e_wall = (Z == CK.Z_CPAINT_N) & (Nn[:, 0] > 0.6) & (x > 2.95)
    sd, fb = FK.SD, FK.FB
    patch = np.maximum(CPT.rect_in(y, z, sd['y0'] - 0.13, sd['y1'] + 0.13, 0.20, sd['z1'] + 0.14, wob, 0.10),
                       CPT.rect_in(y, z, fb['y0'] - 0.09, fb['y1'] + 0.09, fb['z0'] - 0.09, fb['z1'] + 0.09, wob, 0.06))
    patch = patch * e_wall
    pc = CPT.PATCH[CK.Z_CPAINT_N] * (0.92 + 0.12 * (n_hi - 0.5))[:, None]
    col = mixc(col, pc, patch * 0.85)
    cut = np.maximum(ss(0.07, 0.0, CPT.rect_d(y, z, sd['y0'], sd['y1'], sd['z0'], sd['z1'])),
                     ss(0.05, 0.0, CPT.rect_d(y, z, fb['y0'], fb['y1'], fb['z0'], fb['z1'])))
    col = mixc(col, RUST_D, (cut * e_wall * (0.35 + 0.4 * n_mid)) * 0.6)
    return col, gr


DRAFT_COL = {CK.Z_CPAINT_S: (62, 92, 116), CK.Z_CPAINT_N: (70, 96, 108), CK.Z_CROOF: (88, 104, 112), CK.Z_CCAST: (50, 66, 80),
             CK.Z_CINPAINT: (150, 154, 150), K.Z_FLOOR: (116, 113, 106), K.Z_LINING: (178, 150, 108),
             K.Z_ROOFUNDER: (118, 120, 116), K.Z_TRIMW: (212, 208, 194), CK.Z_UNDER: (30, 28, 26), K.Z_SLAB: (132, 130, 124),
             K.Z_TIMBER: (150, 118, 78), K.Z_DOORIN: (146, 118, 82), K.Z_STEELBLK: (36, 36, 36), K.Z_GALV: (150, 154, 152),
             K.Z_CHEQUER: (124, 124, 120), K.Z_ENAMEL: (36, 70, 50), K.Z_ENAMEL_IN: (232, 230, 222)}
INFO['atlases'] = {}
if DRAFT:
    for a in ('Cont', 'Genset', 'Props'):
        BC.draft(groups[a], lambda z: DRAFT_COL.get(z, (128, 128, 128)))
else:
    PB.make_atlas('Cont', groups['Cont'], paint_gcf_all, TEX, prefix='T_GCont_', mat_prefix='M_GCont_', size=1024,
                  ao_min=0.35, ao_dist=0.40, rough=0.85, log=log, info=INFO['atlases'],
                  prio_zones=(K.Z_ENAMEL, K.Z_INSUL, K.Z_RUSTPIPE), zone_scale={CK.Z_UNDER: 0.3, CK.Z_CROOF: 0.65})
    PB.finish_atlas('Genset', groups['Genset'], prep['Genset'], GP.paint_genset, TEX, prefix='T_GCont_', mat_prefix='M_GCont_',
                    ao_min=0.35, ao_dist=0.14, rough=0.7, log=log, info=INFO['atlases'],
                    prio_zones=(K.Z_RED2, K.Z_YEL2, K.Z_FANB, K.Z_WIRER, K.Z_GLASSB, K.Z_COPPER, K.Z_CHROME2))
    PB.finish_atlas('Props', groups['Props'], prep['Props'], GP.paint_props, TEX, prefix='T_GCont_', mat_prefix='M_GCont_',
                    ao_min=0.40, ao_dist=0.14, rough=0.75, log=log, info=INFO['atlases'],
                    prio_zones=(K.Z_DRUMB, K.Z_REDH, K.Z_EXT, K.Z_OILCAN, K.Z_JUG, K.Z_PALLET, K.Z_CABLER, K.Z_COPPERP, K.Z_BRASSP))
del prep

# ------------------------------------------------------------------ 4. explicit materials (the map's names where the game swaps them)
m_panel = PB.tex_mat('M_GCont_Panel', PB_BASE, PB_EMI, 0.0, rough=0.5)
m_bulb = BC.u3_mat('M_Lamp_BulbOff', U3M)
m_led = BC.u3_mat('M_LEDOff', U3M)
m_glass = BC.u3_mat('M_GlassClear', U3M)


def flat_mat(name, rgb, rough=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Base Color'].default_value = (*rgb, 1)
    pb.inputs['Roughness'].default_value = rough
    m['flat'] = list(rgb)
    return m


m_needle = flat_mat('M_GCont_Needle', (0.95, 0.30, 0.06))
m_diesel = flat_mat('M_GCont_Diesel', (0.62, 0.40, 0.06), rough=0.2)
POWER_LED = ('GLamp_RUN', 'BLamp_GEN')                  # green: on while the set runs (M_LEDOff -> M_LEDOn)
for name, o in objs.items():
    a = K.ATLAS[name]
    if a in ('Cont', 'Genset', 'Props'):
        continue
    o.data.materials.clear()
    if a == 'panel':
        o.data.materials.append(m_panel)
    elif a in ('lens:bulk', 'lens:ext'):
        o.data.materials.append(m_bulb)
    elif a.startswith('lens:'):
        o.data.materials.append(m_led if name in POWER_LED else m_panel)
    elif a == 'glass':
        o.data.materials.append(m_glass)
    elif a == 'needle':
        o.data.materials.append(m_needle)
    elif a == 'diesel':
        o.data.materials.append(m_diesel)
    else:
        raise ValueError(a)

# ------------------------------------------------------------------ 5. knock points (rays onto the shell, container frame)
hide_for_rays = []
dg = bpy.context.evaluated_depsgraph_get()
nk = 0
for name, org, d in FK.knock_rays():
    hit, loc, nrm, idx, ob, mw = bpy.context.scene.ray_cast(dg, Vector(org), Vector(d), distance=5.0)
    if not hit:
        log('WARN knock ray missed', name)
        continue
    C['sockets'][name] = dict(pos=r4(loc + nrm * 0.005), kind='knock', parent=ob.name if ob.name in objs else 'GenContainer',
                              dir=r4(nrm), note='something knocks / scratches here from outside (sound, a print in the dew)')
    nk += 1
INFO['knock_points'] = nk

# ------------------------------------------------------------------ 6. onto Update 3's frame (rotate the meshes, move the pivots)
RZ = Matrix.Rotation(math.pi, 4, 'Z')
for name, o in objs.items():
    o.data.transform(RZ)
    o.location = to_u3(o.location)
for p in C['parts'].values():
    p['pivot'] = r4(to_u3(p['pivot']))
    if p.get('axis') is not None:
        p['axis'] = r4(ax_u3(p['axis']))
for s in C['sockets'].values():
    s['pos'] = r4(to_u3(s['pos']))
    for k_ in ('dir', 'eye', 'facing'):
        if s.get(k_) is not None:
            s[k_] = r4(ax_u3(s[k_]) if k_ != 'eye' else to_u3(s[k_]))
LAMPS_U3 = [(n, to_u3(p), ax_u3(d), t, ax_u3(u)) for n, p, d, t, u in K.LAMPS]
root = objs['GenContainer']                              # the root's origin at Update 3's origin
root.data.transform(Matrix.Translation(root.location))
root.location = (0.0, 0.0, 0.0)
C['parts']['GenContainer']['pivot'] = [0.0, 0.0, 0.0]
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 7. Update 3's names
RENAME = {'Door_L': 'IX_ContDoorL_83', 'Door_R': 'IX_ContDoorR_84', 'Gen_Key': 'IX_GenStart_86',
          'Board_MCB_1': 'IX_Breaker_87', 'Board_MCB_2': 'IX_Breaker_88', 'Board_MCB_3': 'IX_Breaker_89',
          'Board_Changeover': 'IX_MainSwitch_90'}
for old, new in RENAME.items():
    o = objs.pop(old)
    o.name = new
    o.data.name = new
    objs[new] = o
    C['parts'][new] = C['parts'].pop(old)
    C['parts'][new]['was'] = old
    K.ATLAS[new] = K.ATLAS.pop(old)
for d in list(C['parts'].values()) + list(C['sockets'].values()):
    if d.get('parent') in RENAME:
        d['parent'] = RENAME[d['parent']]
for s in list(C['sockets']):
    for old, new in RENAME.items():
        if s.endswith('_' + old) or s.startswith(old + '_'):
            C['sockets'][s.replace(old, new)] = C['sockets'].pop(s)
            break
# the board's door stands open (165 deg, folded back towards the cargo doors): on the map the changeover and the breakers behind it are worked by hand
BD_OPEN = 165.0
bd = C['parts']['Board_Door']
Mbd = (Matrix.Translation(Vector(bd['pivot'])) @ Matrix.Rotation(math.radians(BD_OPEN), 4, Vector(bd['axis']))
       @ Matrix.Translation(-Vector(bd['pivot'])))


def under(name, top):
    n, seen = name, 0
    while n is not None and seen < 30:
        if n == top:
            return True
        n = C['parts'].get(n, {}).get('parent')
        seen += 1
    return False


for name in [n for n in objs if under(n, 'Board_Door')]:
    objs[name].matrix_world = Mbd @ objs[name].matrix_world
bd['modelled_at'] = BD_OPEN
bpy.context.view_layer.update()
IX = ['IX_ContDoorL_83', 'IX_ContDoorR_84', 'IX_ContSideDoor_85', 'IX_GenStart_86', 'IX_Breaker_87', 'IX_Breaker_88',
      'IX_Breaker_89', 'IX_MainSwitch_90', 'IX_GenFillCap_300']
FOREST_RANGE = {'IX_GenStart_86': (0, 52), 'IX_MainSwitch_90': (0, 60)}   # key OFF -> ON; changeover OFF -> GEN
for n in IX:
    assert n in objs, n
    if n in FOREST_RANGE:
        C['parts'][n]['range_forest'] = list(FOREST_RANGE[n])

# ------------------------------------------------------------------ 8. Update 3's objects: the root + the IX parts + Window_Glass
CHILDREN = IX + ['Window_Glass']


def owner(name):
    n, seen = name, 0
    while n is not None and seen < 30:
        if n in CHILDREN:
            return n
        n = C['parts'].get(n, {}).get('parent')
        seen += 1
    return 'GenContainer'


members = {}
for name in objs:
    if name in CHILDREN or name == 'GenContainer':
        continue
    members.setdefault(owner(name), []).append(name)
joined_log = {}
for tgt, srcs in members.items():
    T_ = objs[tgt]
    P.select_only([objs[s] for s in srcs] + [T_], active=T_)
    bpy.ops.object.join()
    for s in srcs:
        del objs[s]
    joined_log[tgt] = sorted(srcs)
for o in objs.values():                                  # one slot per material
    me = o.data
    seen_, remap = {}, []
    for m in me.materials:
        remap.append(seen_.setdefault(m.name if m else None, len(seen_)))
    if len(seen_) < len(me.materials):
        for poly in me.polygons:
            poly.material_index = remap[poly.material_index]
        mats = list(me.materials)
        me.materials.clear()
        done = set()
        for m in mats:
            if (m.name if m else None) not in done:
                me.materials.append(m)
                done.add(m.name if m else None)
for n in CHILDREN:
    BC.attach(objs[n], root)
log('objects', sorted(objs), {k: len(v) for k, v in joined_log.items()})
INFO['joined'] = joined_log

# ------------------------------------------------------------------ 9. the map's data: lights, halos, interactables, viewpoint, filler
def unity(v):
    return BC.to_unity(v)


def unity_axis(a):
    """Blender axis with +angle = open  ->  Unity axis with +angle = open (Unity is left-handed: the axis flips)"""
    u = BC.to_unity(a)
    return [round(-c, 4) + 0.0 for c in u]


def qrot(q, v):
    x, y, z, w = q
    u = np.array([x, y, z])
    v = np.asarray(v, np.float64)
    return v + 2.0 * np.cross(u, np.cross(u, v) + w * v)


def world(v_u3):
    return [round(float(a), 4) for a in (qrot(PLACE['q'], unity(v_u3)) + np.array(PLACE['p']))]


lights, glows = [], []
for n, p, d, t, u in LAMPS_U3:
    lp = unity(p)
    if t == 'barnlight':
        lights.append(dict(t='spot', p=lp, d=unity(d), c=[1.0, 0.72, 0.42], i=1.0, r=10.0, a=140.0, sh=False, tag='power',
                           off=True, room='Exterior'))
        glows.append(dict(p=unity(p + Vector((0, 0, 0.0))), m='M_Glow_Bulb', s=0.6, tag='power', off=True))
    else:
        lights.append(dict(t='point', p=lp, d=[0.0, -1.0, 0.0], c=[1.0, 0.76, 0.5], i=0.35, r=5.5, a=0.0, sh=False,
                           tag='power', off=True, room='Exterior'))
        glows.append(dict(p=unity(p), m='M_Glow_Bulb', s=0.4, tag='power', off=True))
inter = []
U3I = {e['child']: e for e in U3L['interactables'] if e['model'] == 'GenContainer'}
for n in IX:
    p = C['parts'][n]
    rng = p.get('range_forest') or p['range']
    e = dict(model='GenContainer', child=n, kind='hinge', axis=unity_axis(p['axis']), min=float(rng[0]), max=float(rng[1]),
             locked=False)
    inter.append(dict(new=e, old=U3I.get(n)))
# viewpoint: in the cargo doorway, looking along the generator at its panel and the board
cam_u3, tgt_u3 = Vector((2.55, 0.55, 1.85)), Vector((-0.45, -0.25, 1.05))
vp = dict(name='GenContainer', p=world(cam_u3), target=world(tgt_u3), fov=62.0, preview='Forest_GenContainer.jpg')
neck_u3 = Vector(C['sockets']['Pour_Fill']['pos'])
stand_u3 = Vector((neck_u3.x - 0.75, neck_u3.y, 0.0))
fill = dict(neck=world(neck_u3), stand=world(stand_u3), label='Tagestank 100 l', capacityL=100)
old_fill = next(e for e in U3O['interactables'] if e['id'] == 'Gen_FillNeck')
INFO['data'] = dict(prefabLights=dict(model='GenContainer', lights=lights), prefabGlows=dict(model='GenContainer', glows=glows),
                    interactables=inter, viewpoint=vp, viewpoint_u3=next(v for v in U3L['viewpoints'] if v['name'] == 'GenContainer'),
                    fill=fill, fill_u3={k: old_fill[k] for k in ('neck', 'stand', 'label', 'capacityL')},
                    placement=PLACE)
log('lights', len(lights), 'interactables', [(i['new']['child'], i['new']['axis'], i['new']['max']) for i in inter])

# ------------------------------------------------------------------ 10. contract (Update 3's frame), stats, save
for k_, p in C['parts'].items():
    p['pivotUnity'] = unity(p['pivot'])
    if p.get('axis') is not None:
        p['axisUnity'] = unity_axis(p['axis'])
    p['object'] = k_ if k_ in objs else owner(k_)
for s in C['sockets'].values():
    s['posUnity'] = unity(s['pos'])
C['lamps'] = [dict(name=n, pos=r4(p), dir=r4(d), type=t, up=r4(u), posUnity=unity(p), dirUnity=unity(d)) for n, p, d, t, u in LAMPS_U3]
C['meta'] = dict(
    units='metres, degrees',
    frame='Update 3\'s GenContainer frame (its FBX after import): x along the boxes, the cargo doors at +x, y across (the '
          'north box with the day tank and the side door at -y), z up, ground z = 0, floor 0.31; Unity prefab-local '
          '(-x, z, -y); placement unchanged (Forest_Layout.json)',
    axes='axis + range: right hand, + opens; Unity: axisUnity with the same +range (the axis flips with the handedness)',
    objects='GenContainer (everything static joined in) + the nine IX parts (what moves with each joined in) + '
            'Window_Glass; part.object = the object a detail ended up in',
    origin='the generator container package (cont_kit, GENCONT_CONTRACT.md) with gcf_kit\'s map changes')
json.dump(BC.nz(C), open(os.path.join(OUT, 'gcf_contract.json'), 'w'), indent=1, ensure_ascii=False)
BC.psx_uv_only()
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
INFO['tris'] = sum(P.tri_count(o) for o in meshes)
INFO['tris_by_object'] = {o.name: P.tri_count(o) for o in meshes}
INFO['materials'] = {o.name: [m.name for m in o.data.materials] for o in meshes}
lo_, hi_ = P.world_bbox(meshes)
INFO['bbox'] = [lo_.round(3).tolist(), hi_.round(3).tolist()]
log('tris', INFO['tris'], INFO['tris_by_object'], 'bbox', INFO['bbox'])
sfx = '_draft' if DRAFT else ''
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'gcf{sfx}.blend'))
json.dump(BC.nz(INFO), open(os.path.join(OUT, f'gcf{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
log('saved gcf' + sfx)
