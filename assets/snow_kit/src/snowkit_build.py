"""Snow kit build (snowkit_kit): one object per part with its pivot as the origin, parented under its item's root; every item
a collection named as the item (instance offset = the item's origin, so a building links the collection and places it as
an instance); the Kit atlas baked with psxbake + snowkit_paint (64 px / m, the props' density); the panel atlas
(snowkit_tex) on labels, signs, the dial, the camera glass; lamp lenses lit / off; the CRT screen off / on (UV 0..1);
the beacon's halo; colliders; the lights json; the contract (parts, sockets, colliders per item, Unity values).
python3 -I snowkit_build.py [--draft]  -> out/snow_kit.blend, out/snow_kit.json, out/snow_kit_contract.json,
                                          out/snow_kit_lights.json, tex/snow_kit/*
--draft: no bakes, flat zone colours (layout check) -> out/snow_kit_draft.blend"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import psxlib as P
import psxbake as PB
import gen_lights as GL
import van_lights as VL
import gen_kit as K
import snowkit_spec as S
import snowkit_kit as KK

DRAFT = '--draft' in sys.argv
ASIZE = int(sys.argv[sys.argv.index('--size') + 1]) if '--size' in sys.argv else None
XSFX = sys.argv[sys.argv.index('--sfx') + 1] if '--sfx' in sys.argv else ''
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'snow_kit' + XSFX)
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
T0 = time.time()
INFO = {}
PB.POS_SCALE = 40.0
PPM = 64.0                                      # the props' pixel density (KppProps, the items)


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


def r4(v):
    return [round(float(a), 4) + 0.0 for a in v]


def to_unity(v):
    return [round(-float(v[0]), 4) + 0.0, round(float(v[2]), 4) + 0.0, round(-float(v[1]), 4) + 0.0]


def _nz(o):
    if isinstance(o, float):
        return o + 0.0
    if isinstance(o, dict):
        return {k: _nz(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_nz(v) for v in o]
    return o


# ------------------------------------------------------------------ the kit's light types (the beacon, the mast's floodlight
# and street lamp); lamp frame = Unity light frame: +Z the beam, +Y up


def _th(l):
    return np.degrees(np.arccos(np.clip(l[..., 2], -1, 1)))


def em_flood(l):
    """halogen floodlight: a wide flat beam, brighter in the middle, the reflector's edge cuts it at ~60 deg"""
    th = _th(l)
    return np.clip((1 - VL.smoothstep(46, 62, th)) * (0.50 + 0.50 * np.exp(-0.5 * (th / 24.0) ** 2)), 0, 1)


def em_street(l):
    """box street lamp (mercury): a broad batwing under it, a little dimmer straight down, nothing above ~80 deg"""
    th = _th(l)
    return np.clip((1 - VL.smoothstep(68, 82, th)) * (0.62 + 0.38 * np.sin(np.radians(np.minimum(th, 60.0)) * 1.5)), 0, 1)


GL.TYPES.clear()
GL.TYPES.update({
    'beacon': dict(em=lambda l: np.clip(1.0 - np.abs(l[..., 2]) * 1.6, 0, 1) * np.clip(l[..., 0], 0, 1) ** 2 + 0.02, I=1.2, cd=45,
                   cct=1900, filt=(1.0, 0.62, 0.18), unity='Spot', rng=14.0, group='power', shadows=False, res=64, lens_floor=0.3,
                   desc='orange rotating beacon: a narrow beam (spot 30, range 14) turned round the vertical at 80 rpm while the '
                        'barrier / the gate moves; the dome lit with it'),
    'flood': dict(em=em_flood, I=9.0, cd=700, cct=3000, filt=(1.0, 0.97, 0.90), unity='Spot', rng=24.0, group='power',
                  shadows=False, res=128, lens_floor=0.15,
                  desc='halogen floodlight 500 W on a mast: a wide beam (spot 110, range 24) tipped 30 down; lit with the power'),
    'street': dict(em=em_street, I=4.5, cd=320, cct=4200, filt=(0.86, 0.96, 1.0), unity='Spot', rng=18.0, group='power',
                   shadows=False, res=128, lens_floor=0.15,
                   desc='street lamp on a mast (mercury 125 W, bluish white): a broad cone down (spot 160, range 18); lit with '
                        'the power'),
})

bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
if not DRAFT:
    import snowkit_tex as ST
    TX = ST.build(TEX)
    INFO['ies'] = GL.write_ies_all(os.path.join(TEX, 'IES'))
else:
    TX = None

# ------------------------------------------------------------------ 1. geometry, objects, hierarchy
KK.build_kit()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts']]
assert not missing, f'objects without a contract entry: {missing}'
objs = {}
for name, k in K.KBS.items():
    bmesh.ops.remove_doubles(k.bm, verts=list(k.bm.verts), dist=1e-5)
    objs[name] = k.to_object(name, pivot=Vector(C['parts'][name]['pivot']))
bpy.context.view_layer.update()


def attach(child, parent):
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    child.matrix_world = mw


for name, p in C['parts'].items():
    if p.get('parent'):
        attach(objs[name], objs[p['parent']])
    p['object'] = name


def root_of(name):
    while C['parts'][name].get('parent'):
        name = C['parts'][name]['parent']
    return name


for name in C['parts']:
    assert KK.ITEM_OF.get(name) == root_of(name), (name, KK.ITEM_OF.get(name), root_of(name))

# ------------------------------------------------------------------ 2. layout for the bake and the file (roots only move)
LAYOUT = {
    'Kit_Console_2': (0.0, 0.0, 0.0), 'Kit_Console_4': (0.55, 0.0, 0.0), 'Kit_Console_Button': (1.05, 0.0, 0.0),
    'Kit_Console_Label_Schranke': (1.25, 0.0, 0.0), 'Kit_Console_Label_Tor': (1.40, 0.0, 0.0),
    'Kit_Console_Label_Licht': (1.55, 0.0, 0.0), 'Kit_Console_Label_Blank': (1.70, 0.0, 0.0),
    'Kit_Phone': (2.10, 0.0, 0.0), 'Kit_Monitor_CRT': (2.65, 0.0, 0.0), 'Kit_Beacon': (3.15, 0.0, 0.0),
    'Kit_DoorLock': (3.50, 0.0, 0.08), 'Kit_DoorLock_Strike': (3.70, 0.0, 0.075), 'Kit_Camera_Head': (4.10, 0.0, 0.0),
    'Kit_Camera_BracketWall': (4.60, 0.0, 1.0), 'Kit_Camera_BracketPole': (5.20, 0.0, 1.0),
    'Kit_JunctionBox': (5.80, 0.0, 0.08), 'Kit_Conduit_Straight': (6.20, 0.0, 0.016), 'Kit_Conduit_Elbow': (7.50, 0.0, 0.016),
    'Kit_Conduit_Clamp': (7.90, 0.0, 0.016), 'Kit_Conduit_Entry': (8.20, 0.0, 0.024),
    'Kit_Cabinet_Power': (0.0, 1.6, 0.40), 'Kit_RoofStand': (1.5, 1.6, 0.0),
    'Kit_Pole': (0.0, 4.5, 0.0), 'Kit_Pole_Trafo': (4.0, 4.5, 0.0), 'Kit_Mast': (2.0, 4.5, 0.0),
    'Kit_Mast_Flood': (0.0, 7.5, 1.0), 'Kit_Mast_Horn': (1.0, 7.5, 1.0), 'Kit_Mast_Yagi': (2.5, 7.5, 1.0),
    'Kit_Mast_Lamp': (4.0, 7.5, 1.0), 'Kit_Mast_Antenna': (6.0, 7.5, 1.0), 'Kit_Mast_Siren': (7.5, 7.5, 1.0),
    'Kit_Wire_Bare': (0.0, 10.0, 3.0), 'Kit_Wire_Drop': (0.0, 11.0, 3.0),
}
# (attachments and brackets that hang high up are laid out a metre up: the painter's mud at the foot (world z < 0.3) is for
# things that stand on the ground)
assert set(LAYOUT) == set(S.ITEM_NAMES), set(S.ITEM_NAMES) ^ set(LAYOUT)
for name, pos in LAYOUT.items():
    objs[name].location = Vector(pos)
bpy.context.view_layer.update()
groups = {}
for name, o in objs.items():
    groups.setdefault(K.ATLAS[name], []).append(o)
log('objects', len(objs), {a: len(v) for a, v in groups.items()})

# ------------------------------------------------------------------ 3. the Kit atlas (or flat zone colours)
INFO['atlases'] = {}
if DRAFT:
    cache = {}

    def zmat(z):
        if z not in cache:
            m = bpy.data.materials.new(f'draft_{z}')
            m.use_nodes = True
            pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            c = PB.lin(*S.ZONE_INFO.get(z, ('', (128, 128, 128), ''))[1])
            pb.inputs['Base Color'].default_value = (float(c[0]), float(c[1]), float(c[2]), 1)
            pb.inputs['Roughness'].default_value = 0.7
            m.diffuse_color = (float(c[0]), float(c[1]), float(c[2]), 1)
            cache[z] = m
        return cache[z]

    for o in groups['Kit']:
        me = o.data
        zl = [round(a.value) for a in me.attributes['zone'].data]
        me.materials.clear()
        idx = {}
        for z in sorted(set(zl)):
            idx[z] = len(me.materials)
            me.materials.append(zmat(z))
        for poly, z in zip(me.polygons, zl):
            poly.material_index = idx[z]
else:
    import snowkit_paint as KP
    PB.make_atlas('Kit', groups['Kit'], KP.painter, TEX, prefix='T_Kit_', mat_prefix='M_Kit_', size=ASIZE, ppm=PPM, ao_min=0.40,
                  ao_dist=0.14, rough=0.7, log=log, info=INFO['atlases'], ppm_cap=PPM,
                  zone_scale={S.Z_KBTN: 2.0, S.Z_KCOPPER: 1.6, S.Z_KREDC: 1.5, S.Z_KHANDLE: 1.5, S.Z_KPOLE: 0.7, S.Z_KTRAFO: 0.8},
                  prio_zones=(S.Z_KBTN, S.Z_KPHONE, S.Z_KREDC, S.Z_KCOPPER))

# ------------------------------------------------------------------ 4. explicit materials
if DRAFT:
    flat = bpy.data.materials.new('draft_flat')
    flat.diffuse_color = (0.6, 0.6, 0.6, 1)
    m_panel = flat
    lens_mats = {k: flat for k in S.LAMP_KINDS}
    m_screen_off = m_screen_on = m_glow = flat
else:
    m_panel = PB.tex_mat('M_Kit_Panel', TX['base'], TX['emi'], 0.0, rough=0.55)
    lens_mats = {}
    for kind in S.LAMP_KINDS:
        for sfx, ne in (('', 3.0 if kind != 'Beacon' else 4.0), ('_Off', 0.0)):
            m = PB.tex_mat('M_Kit_Lamp_' + kind + sfx, TX['base'], TX['emi'], ne, rough=0.2)
            m['lamp_kind'] = kind
            m.use_fake_user = bool(sfx)
            lens_mats[kind + sfx] = m
        lens_mats[kind] = lens_mats[kind]

    def img_mat(name, path, emit):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        pb = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        uvn = nt.nodes.new('ShaderNodeUVMap')
        uvn.uv_map = 'PSX'
        ti = nt.nodes.new('ShaderNodeTexImage')
        ti.image = bpy.data.images.load(path, check_existing=True)
        ti.interpolation = 'Closest'
        nt.links.new(uvn.outputs[0], ti.inputs[0])
        nt.links.new(ti.outputs[0], pb.inputs['Base Color'])
        if emit:
            nt.links.new(ti.outputs[0], pb.inputs['Emission Color'])
        pb.inputs['Emission Strength'].default_value = 0.0
        pb.inputs['Roughness'].default_value = 0.08
        m['night_emit'] = emit
        return m

    m_screen_off = img_mat('M_Kit_Screen_Off', TX['screen_off'], 0.0)
    m_screen_on = img_mat('M_Kit_Screen_On', TX['screen_on'], 1.8)
    m_screen_on.use_fake_user = True
    m_screen_on['unity'] = 'render texture of the placement\'s camera goes here (emission = the picture)'
    m_glow = bpy.data.materials.new('M_Kit_Glow')
    m_glow.use_nodes = True
    nt = m_glow.node_tree
    nt.nodes.clear()
    o_ = nt.nodes.new('ShaderNodeOutputMaterial')
    uvn = nt.nodes.new('ShaderNodeUVMap')
    uvn.uv_map = 'PSX'
    ti = nt.nodes.new('ShaderNodeTexImage')
    ti.image = bpy.data.images.load(TX['emi'], check_existing=True)
    ti.interpolation = 'Closest'
    nt.links.new(uvn.outputs[0], ti.inputs[0])
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = 0.0
    nt.links.new(ti.outputs[0], em.inputs['Color'])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(tr.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], o_.inputs['Surface'])
    m_glow['night_emit'] = 2.0
    m_glow['blend'] = 'additive'
    try:
        m_glow.surface_render_method = 'BLENDED'
    except AttributeError:
        pass
for nm_, col_ in (('M_Kit_Wire', (0.012, 0.012, 0.012)), ('M_Kit_WireBare', (0.32, 0.33, 0.34))):
    m = bpy.data.materials.new(nm_)
    m.use_nodes = True
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Base Color'].default_value = (*col_, 1)
    pb.inputs['Roughness'].default_value = 0.6 if nm_ == 'M_Kit_Wire' else 0.45
    pb.inputs['Metallic'].default_value = 0.0 if nm_ == 'M_Kit_Wire' else 0.6
    m.diffuse_color = (*col_, 1)
    m.use_fake_user = True
    m['wire'] = S.WIRE['note']

for name, o in objs.items():
    a = K.ATLAS[name]
    if a == 'Kit':
        continue
    o.data.materials.clear()
    if a == 'panel':
        o.data.materials.append(m_panel)
    elif a.startswith('lens:'):
        o.data.materials.append(lens_mats[a[5:]])
        o['lamp_kind'] = a[5:]
    elif a == 'screen':
        o.data.materials.append(m_screen_off)
        o['screen'] = 'M_Kit_Screen_Off / M_Kit_Screen_On, UV 0..1'
    elif a == 'glow':
        o.data.materials.append(m_glow)
        o.visible_shadow = False
    elif a.startswith('wire:'):
        o.data.materials.append(bpy.data.materials['M_Kit_WireBare' if a == 'wire:bare' else 'M_Kit_Wire'])
    else:
        raise ValueError(a)

# ------------------------------------------------------------------ 5. collections per item (instance offset = the origin)
top = bpy.data.collections.new('Snow_Kit')
bpy.context.scene.collection.children.link(top)
icoll = {}
for _, name, _, _ in S.ITEMS:
    c = bpy.data.collections.new(name)
    top.children.link(c)
    c.instance_offset = Vector(LAYOUT[name])
    icoll[name] = c
for name, o in objs.items():
    for c in list(o.users_collection):
        c.objects.unlink(o)
    icoll[root_of(name)].objects.link(o)

# ------------------------------------------------------------------ 6. colliders (wire boxes in the item's collection)
C['colliders'] = []
for name, par, (x0, x1, y0, y1, z0, z1), rot in KK.COLLIDERS:
    root = root_of(par)
    c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    size = Vector((x1 - x0, y1 - y0, z1 - z0))
    kb_ = K.KB()
    kb_.box(-size.x / 2, size.x / 2, -size.y / 2, size.y / 2, -size.z / 2, size.z / 2, 0)
    ob = kb_.to_object('COL_' + name, coll=icoll[root])
    # the box is given in the item frame: place it from the root (its layout offset), then parent it to its part
    ob.location = objs[root].matrix_world @ c
    ob.display_type = 'WIRE'
    ob.hide_render = True
    ob['collider'] = 'box'
    attach(ob, objs[par])
    bpy.context.view_layer.update()
    lc = objs[par].matrix_world.inverted() @ ob.matrix_world.translation
    C['colliders'].append(dict(name='COL_' + name, item=root, parent=par, type='box', center=r4(lc), size=r4(size),
                               center_item=r4(c), centerUnity=to_unity(lc), sizeUnity=r4((size.x, size.z, size.y))))
log('colliders', len(C['colliders']))

# ------------------------------------------------------------------ 7. lights (the beacon)
LMETA = GL.meta()
lights = []
for name, pos, d, typ, up in K.LAMPS:
    lm = KK.LAMP_META[name]
    it = lm['item']
    e = bpy.data.objects.new('LIGHT_' + name, None)
    icoll[it].objects.link(e)
    e.empty_display_type, e.empty_display_size = 'SINGLE_ARROW', 0.12
    dv = Vector(d).normalized()
    uv_ = Vector(up)
    uv_ = (uv_ - dv * uv_.dot(dv)).normalized()
    xv_ = uv_.cross(dv)
    e.matrix_world = objs[it].matrix_world @ (Matrix.Translation(Vector(pos)) @ Matrix((xv_, uv_, dv)).transposed().to_4x4())
    T = GL.TYPES[typ]
    e['type'], e['group'] = typ, T['group']
    attach(e, objs[it])
    lights.append(dict(socket='LIGHT_' + name, item=it, lens=lm['lens'], glow=lm['glow'], type=typ,
                       unityLight=T['unity'], spotAngle=lm['spot'], position=r4(pos), forward=r4(d), up=r4(up),
                       positionUnity=to_unity(pos), forwardUnity=to_unity(d), upUnity=to_unity(up), intensityURP=T['I'],
                       peakCandela=T['cd'], kelvin=T['cct'], filterLinear=list(T['filt']), colorLinear=r4(GL.colour(typ)),
                       range=T['rng'], group=T['group'], shadows=False, rotateRPM=lm['rpm'], ies=f'IES/{typ}.ies', desc=T['desc'],
                       startsOn=False))
json.dump(dict(note='kit lamps that are real lights (the others are lit / off materials only). position / forward / up in the '
                    'item frame; *Unity in the prefab. group power = only with the power.', lights=lights),
          open(os.path.join(OUT, 'snow_kit_lights.json'), 'w'), indent=1)

# ------------------------------------------------------------------ 8. part boxes, Unity values, the items block
POWER_WHEN = {
    'Kit_Monitor_Screen': 'M_Kit_Screen_On (Unity puts the camera picture on it) while the building has power',
    'Lens_ConsoleButton': 'lit with the power while its barrier / gate is open (the building decides)',
    'Lens_CabinetPower': 'lit while the cabinet gives power (battery in, both clamps on, the switch at BATTERIE)',
    'Lens_DoorLock': 'lit (green: released) while the lock has power',
    'Lens_Beacon': 'lit and turning (with LIGHT_Beacon) while its barrier moves, with the power',
    'Lens_Flood': 'lit (with LIGHT_Flood and its halo) while the building has power',
    'Lens_Street': 'lit (with LIGHT_Street and its halo) while the building has power (or at night: the building decides)',
}
for k, p in C['parts'].items():
    o = objs[k]
    p['pivotUnity'] = to_unity(p['pivot'])
    if p.get('axis'):
        p['axisUnity'] = to_unity(p['axis'])
    p['item'] = root_of(k)
    p['material'] = [m.name for m in o.data.materials]
    lit = next((m for m in p['material'] if m.startswith('M_Kit_Lamp_') or m.startswith('M_Kit_Screen_')), None)
    if lit:                                                    # what lights up with the power (group power)
        on = 'M_Kit_Screen_On' if lit.startswith('M_Kit_Screen_') else lit.replace('_Off', '')
        p['power'] = dict(group='power', on=on, off=on.replace('_On', '_Off') if on.endswith('_On') else on + '_Off',
                          when=POWER_WHEN.get(k, 'lit while the building has power'))
    if p['kind'] != 'static' and not k.startswith(('Lens_', 'Glow_')):
        co = np.array([tuple(v.co) for v in o.data.vertices])
        lo, hi = co.min(0), co.max(0)
        p['box'] = dict(center=r4((lo + hi) / 2), size=r4(np.maximum(hi - lo, 0.004)))
for k, s in C['sockets'].items():
    s['item'] = KK.ITEM_OF[k]
    s['posUnity'] = to_unity(s['pos'])
    for key in ('dir', 'up', 'forward'):
        if s.get(key) is not None:
            s[key + 'Unity'] = to_unity(s[key])
items = {}
for kid, name, mount, ru in S.ITEMS:
    parts = [k for k in C['parts'] if C['parts'][k]['item'] == name]
    meshes = [objs[k] for k in parts]
    root = objs[name]
    inv = root.matrix_world.inverted()
    vs = np.array([tuple(inv @ (o.matrix_world @ v.co)) for o in meshes for v in o.data.vertices])
    lo, hi = vs.min(0), vs.max(0)
    items[name] = dict(id=kid, mount=mount, ru=ru, parts=parts, sockets=[k for k, s in C['sockets'].items() if s['item'] == name],
                       colliders=[c['name'] for c in C['colliders'] if c['item'] == name], bbox=[r4(lo), r4(hi)],
                       size=r4(hi - lo), tris=int(sum(P.tri_count(o) for o in meshes)),
                       materials=sorted({m.name for o in meshes for m in o.data.materials}),
                       unity_fbx=f'{S.UNITY_ROOT}/Models/{name}.fbx', wires=KK.WIRE_PTS.get(name, []),
                       power_parts=[k for k in parts if C['parts'][k].get('power')])
C['items'] = items
C['meta'] = dict(version=S.KIT_VERSION, units='metres, degrees',
                 frame='each item in its own frame: z up, the front -y; origins as each item says (wall things: the middle of the '
                       'back on the wall; desk / ground things: the middle of the underside; panel things: on the panel face, +z '
                       'out; pipe pieces: on the axis)',
                 unity='(x, y, z) -> (-x, z, -y); angle -> -angle; box size (sx, sy, sz) -> (sx, sz, sy); the item\'s front (-y) is '
                       'the prefab\'s +Z',
                 unity_root=S.UNITY_ROOT, materials=dict(
                     atlas='M_Kit_Kit (T_Kit_Kit_A_px: the baked PSX atlas of every model, point filter)',
                     panel='M_Kit_Panel (T_Kit_Panel_A_px + _E_px: labels, signs, the dial, the camera glass)',
                     lamps='M_Kit_Lamp_<Red|Green|Amber|Beacon> lit / _Off (same textures, emission on / off)',
                     screen='M_Kit_Screen_Off (T_Kit_Screen_Off) / M_Kit_Screen_On (the camera picture; T_Kit_Screen_On stands in)',
                     glow='M_Kit_Glow additive halo (the beacon)', wire='M_Kit_Wire (black service cable), M_Kit_WireBare (line)'),
                 wire=S.WIRE, battery=dict(KK.BATT, note='the van\'s Battery (Van/Data/parts.json): size (x, up, z) in its Unity '
                                                         'frame, posts at (+-x, up, z) = (0.04, 0.217, -+0.105)'),
                 lights='snow_kit_lights.json', model='snow_kit.blend', textures='tex',
                 instances='a building links the item\'s collection from snow_kit.blend and places an instance empty KIT_... at the '
                           'item\'s origin; in Unity the builder puts the item\'s prefab on that empty (the FBX has no references)')
sfx = ('_draft' if DRAFT else '') + XSFX
json.dump(_nz(C), open(os.path.join(OUT, f'snow_kit_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    uvs = o.data.uv_layers
    if 'PSX' in uvs:
        for u in [u for u in uvs if u.name != 'PSX']:
            uvs.remove(u)
        uvs['PSX'].active = True
        uvs['PSX'].active_render = True
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_set(True)
INFO['items'] = {n: dict(tris=v['tris'], size=v['size']) for n, v in items.items()}
INFO['tris'] = sum(v['tris'] for v in items.values())
INFO['contract'] = dict(parts=len(C['parts']), sockets=len(C['sockets']), colliders=len(C['colliders']))
log('tris', INFO['tris'], INFO['contract'])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'snow_kit{sfx}.blend'))
json.dump(INFO, open(os.path.join(OUT, f'snow_kit{sfx}.json'), 'w'), indent=1)
log('saved snow_kit' + sfx)
