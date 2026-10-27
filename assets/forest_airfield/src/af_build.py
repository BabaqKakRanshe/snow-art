"""forest_airfield build (adapted from the hut yard build): one object per part with its pivot as the origin, each root in its
own collection standing at af_kit.DISPLAY; PSX atlases baked with psxbake + af_paint: Runway (five 18 x 10 m modules, 2048 at
the shed pixel 51.3 px/m), AFProps (lights, marker, pointer; 64 px/m), AFPlug (the hangar's bricked-up back opening; 51.3);
the panel atlas (af_tex) on the arrow board, the door plate and the light domes; lens lit / off, glow cards; af_lights.json;
the contract (parts, sockets, colliders, meta).
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_airfield/af_build.py [--draft]
-> out/af.blend, out/af.json, out/af_contract.json, out/af_lights.json, tex/af/*"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import psxlib as P
import psxbake as PB
import af_tex as YT
import gen_kit as K
import af_kit as SK

DRAFT = '--draft' in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex', 'af')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
SHED_PPM = 51.3                                       # the generator shed's building atlas (px / m): the project's pixel
PB.POS_SCALE = 130.0                                  # bake range +-65 m: the runway modules stand from x -53 to 53


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


def r4(v):
    return [round(float(a), 4) + 0.0 for a in v]


def _nz(o):
    if isinstance(o, float):
        return o + 0.0
    if isinstance(o, dict):
        return {k: _nz(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_nz(v) for v in o]
    return o


def to_unity(v):
    """prefab frame -> Unity (prefab-local): (x, y, z) -> (-x, z, -y)"""
    return [round(-float(v[0]), 4) + 0.0, round(float(v[2]), 4) + 0.0, round(-float(v[1]), 4) + 0.0]


LIGHT_TYPES = {
    'edge': dict(unity='Point', I=0.5, rng=5.0, cct=2700, color=(1.0, 0.72, 0.30), group='runway', spot=None,
                 desc="runway edge light (amber dome); group runway: all edge and threshold lights switch together from the "
                      "airfield's power. Many of them: a real Light only on every second or third, the rest glow cards only"),
    'thr': dict(unity='Point', I=0.5, rng=5.0, cct=6500, color=(0.35, 1.0, 0.45), group='runway', spot=None,
                desc='threshold light (green dome) across the runway end; group runway'),
}

bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
PB_BASE, PB_EMI = YT.build(TEX)

# ------------------------------------------------------------------ 1. geometry
SK.build_airfield()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts']]
assert not missing, f'objects without a contract entry: {missing}'
colls = {}
for root in SK.ROOTS:
    colls[root] = bpy.data.collections.new(root)
    bpy.context.scene.collection.children.link(colls[root])
objs = {}
for name, k in K.KBS.items():
    root = SK.ROOT_OF[name]
    off = SK.DISPLAY[root]
    if name in SK.RWY or name == 'AF_HangarPlug':
        bmesh.ops.remove_doubles(k.bm, verts=list(k.bm.verts), dist=1e-4)
    K.transform_kb(k, Matrix.Translation(off))
    p = C['parts'][name]
    o = k.to_object(name, coll=colls[root], pivot=Vector(p['pivot']) + off)
    o['root'] = root
    objs[name] = o
log('objects', len(objs))
bpy.context.view_layer.update()
groups = {}
for name, o in objs.items():
    groups.setdefault(K.ATLAS[name], []).append(o)

# ------------------------------------------------------------------ 2. atlases (or flat zone colours for the draft)
INFO['atlases'] = {}
import af_paint as SPT
if DRAFT:
    cache = {}

    def zmat(z):
        if z not in cache:
            m = bpy.data.materials.new(f'draft_{z}')
            m.use_nodes = True
            pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            c = PB.lin(*SPT.DRAFT_COL.get(z, (128, 128, 128)))
            pb.inputs['Base Color'].default_value = (float(c[0]), float(c[1]), float(c[2]), 1)
            pb.inputs['Roughness'].default_value = 0.75
            m.diffuse_color = (float(c[0]), float(c[1]), float(c[2]), 1)
            cache[z] = m
        return cache[z]

    for name, o in objs.items():
        if K.ATLAS[name] not in ('Runway', 'AFProps', 'AFPlug'):
            continue
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
    PB.make_atlas('Runway', groups['Runway'], SPT.paint_runway, TEX, prefix='T_AF_', mat_prefix='M_AF_', size=2048, ppm=SHED_PPM,
                  ao_min=0.45, ao_dist=0.40, rough=0.9, log=log, info=INFO['atlases'], ppm_cap=SHED_PPM,
                  zone_scale={SK.Z_RSKIRT: 0.5})
    PB.make_atlas('AFProps', groups['AFProps'], SPT.paint_props, TEX, prefix='T_AF_', mat_prefix='M_AF_', size=None,
                  ppm=64.0, ao_min=0.40, ao_dist=0.15, rough=0.8, log=log, info=INFO['atlases'], ppm_cap=64.0,
                  prio_zones=(SK.Z_MARK,))
    PB.make_atlas('AFPlug', groups['AFPlug'], SPT.paint_plug, TEX, prefix='T_AF_', mat_prefix='M_AF_', size=512,
                  ppm=SHED_PPM, ao_min=0.35, ao_dist=0.40, rough=0.85, log=log, info=INFO['atlases'], ppm_cap=SHED_PPM)

# ------------------------------------------------------------------ 3. explicit materials
m_panel = PB.tex_mat('M_AF_Panel', PB_BASE, PB_EMI, 0.0, rough=0.6)
lens_mats = {}
for kname, night in (('edge', 3.0), ('thr', 3.0)):
    for sfx, ne in (('', night), ('_Off', 0.0)):
        m = PB.tex_mat('M_AF_Lamp_' + kname.capitalize() + sfx, PB_BASE, PB_EMI, ne, rough=0.2)
        m['lamp_kind'] = kname
        m.use_fake_user = bool(sfx)                    # the 'off' variants are on no mesh: keep them in the file
        lens_mats[kname + sfx] = m
m_glow = bpy.data.materials.new('M_AF_Glow')               # additive halo: emission from the panel's glow tiles
m_glow.use_nodes = True
nt = m_glow.node_tree
nt.nodes.clear()
o_ = nt.nodes.new('ShaderNodeOutputMaterial')
uvn = nt.nodes.new('ShaderNodeUVMap')
uvn.uv_map = 'PSX'
ti = nt.nodes.new('ShaderNodeTexImage')
ti.image = bpy.data.images.load(PB_EMI, check_existing=True)
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
for name, o in objs.items():
    a = K.ATLAS[name]
    if a in ('Runway', 'AFProps', 'AFPlug'):
        continue
    o.data.materials.clear()
    if a == 'panel':
        o.data.materials.append(m_panel)
    elif a.startswith('lens:'):
        o.data.materials.append(lens_mats[a[5:]])
        o['lamp_kind'] = a[5:]
    elif a == 'glow':
        o.data.materials.append(m_glow)
        o.visible_shadow = False
    else:
        raise ValueError(a)

# ------------------------------------------------------------------ 4. hierarchy (world transforms kept)
bpy.context.view_layer.update()


def attach(child, parent):
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    child.matrix_world = mw


for name, p in C['parts'].items():
    if name in objs and p.get('parent') and p['parent'] in objs:
        attach(objs[name], objs[p['parent']])
    p['object'] = name if name in objs else None
    p['root'] = SK.ROOT_OF.get(name, name)


def root_of_part(name):
    while C['parts'][name].get('parent'):
        name = C['parts'][name]['parent']
    return name


for s in C['sockets'].values():
    s['root'] = root_of_part(s['parent']) if s.get('parent') in C['parts'] else s.get('parent')

# ------------------------------------------------------------------ 5. lamps: LIGHT_ empties + lights json
lens_of = {'Edge': 'Lens_Edge', 'Thr': 'Lens_Thr'}
glow_of = {'Edge': 'Glow_Edge', 'Thr': 'Glow_Thr'}
lamp_parent = {'Edge': 'Lamp_Edge', 'Thr': 'Lamp_Thr'}
items = []
for name, pos, d, typ, up in K.LAMPS:
    root = SK.ROOT_OF[lamp_parent[name]]
    off = SK.DISPLAY[root]
    e = bpy.data.objects.new('LIGHT_' + name, None)
    colls[root].objects.link(e)
    e.empty_display_type, e.empty_display_size = 'SINGLE_ARROW', 0.12
    dv = Vector(d).normalized()
    uv_ = Vector(up)
    uv_ = (uv_ - dv * uv_.dot(dv)).normalized()
    xv_ = uv_.cross(dv)                                  # empty: +Z = beam, +Y = the json 'up' (Unity light frame)
    e.matrix_world = Matrix.Translation(Vector(pos) + off) @ Matrix((xv_, uv_, dv)).transposed().to_4x4()
    T = LIGHT_TYPES[typ]
    e['type'], e['group'], e['dir'], e['up'], e['color'] = typ, T['group'], list(dv), list(up), list(T['color'])
    e['intensity_urp'] = T['I']
    e['lens'] = lens_of[name]
    attach(e, objs[lamp_parent[name]])
    it = dict(socket='LIGHT_' + name, root=root, lens=lens_of[name], glow=glow_of[name], parent=lamp_parent[name], type=typ,
              unityLight=T['unity'], position=r4(pos), forward=r4(dv), up=r4(uv_), positionUnity=to_unity(pos),
              forwardUnity=to_unity(dv), upUnity=to_unity(uv_), intensityURP=T['I'], kelvin=T['cct'], colorLinear=list(T['color']),
              range=T['rng'], group=T['group'], shadows=False, desc=T['desc'], startsOn=False)
    if T['spot']:
        it['spotAngle'] = T['spot']
    items.append(it)
    C['sockets']['LIGHT_' + name] = dict(pos=r4(pos), kind='light', parent=lamp_parent[name], root=root, dir=r4(dv),
                                         note=f'{T["unity"]} light ({typ}): af_lights.json')
json.dump(dict(note='airfield lights. position / forward / up: the root own frame (Blender: z up, the front -y, m); *Unity: (-x, z, '
                    '-y) in the prefab. intensityURP at 100 %. The lens (Lens_*) switches M_AF_Lamp_<Kind> (lit) / _Off, the halo card '
                    '(Glow_*) is shown with it. group runway: every edge and threshold light; all start off in the file.',
               lights=items), open(os.path.join(OUT, 'af_lights.json'), 'w'), indent=1)
INFO['lamps'] = len(items)

# ------------------------------------------------------------------ 6. colliders (in each parent's own frame)
coll_c = bpy.data.collections.new('Colliders')
bpy.context.scene.collection.children.link(coll_c)
C['colliders'] = []
for name, par, (x0, x1, y0, y1, z0, z1), rot in SK.BOXES:
    root = SK.ROOT_OF[par]
    off = SK.DISPLAY[root]
    piv = Vector(C['parts'][par]['pivot'])
    c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    size = Vector((x1 - x0, y1 - y0, z1 - z0))
    kb_ = K.KB()
    kb_.box(-size.x / 2, size.x / 2, -size.y / 2, size.y / 2, -size.z / 2, size.z / 2, 0)
    ob = kb_.to_object('COL_' + name, coll=coll_c)
    ob.location = c + off
    if rot:
        ob.rotation_euler = Euler([math.radians(a) for a in rot], 'XYZ')
    ob.display_type = 'WIRE'
    ob.hide_render = True
    ob['collider'] = 'box'
    attach(ob, objs[par])
    lc = c - piv
    ent = dict(name='COL_' + name, parent=par, root=root, type='box', center=r4(lc), size=r4(size), center_root=r4(c),
               centerUnity=to_unity(lc), sizeUnity=r4((size.x, size.z, size.y)))
    if rot:
        ent['rotation'] = [float(a) for a in rot]
        ent['rotationUnity'] = [float(rot[0]), -float(rot[2]), float(rot[1])]
    C['colliders'].append(ent)
log('colliders', len(C['colliders']))

# ------------------------------------------------------------------ 7. part boxes (grab / hit box of moving parts)
for k, p in C['parts'].items():
    o = objs.get(k)
    if o is None or p['kind'] == 'static':
        continue
    co = np.array([tuple(v.co) for v in o.data.vertices])
    lo, hi = co.min(0), co.max(0)
    p['box'] = dict(center=r4((lo + hi) / 2), size=r4(np.maximum(hi - lo, 0.004)))

# ------------------------------------------------------------------ 8. Unity values of the parts and sockets, meta, stats, save
for k, p in C['parts'].items():
    p['pivotUnity'] = to_unity(p['pivot'])
    if p.get('axis'):
        p['axisUnity'] = to_unity(p['axis'])
for s in C['sockets'].values():
    s['posUnity'] = to_unity(s['pos'])
    if s.get('dir'):
        s['dirUnity'] = to_unity(s['dir'])
tris, tris_root = 0, {}
for o in bpy.data.objects:
    if o.type != 'MESH' or o.name.startswith('COL_'):
        continue
    t = sum(len(pl.vertices) - 2 for pl in o.data.polygons)
    tris += t
    tris_root[o.get('root', '?')] = tris_root.get(o.get('root', '?'), 0) + t
INFO['tris'] = tris
INFO['tris_by_root'] = tris_root
INFO['objects'] = {r: sorted(o.name for o in colls[r].objects) for r in SK.ROOTS}
INFO['display_offset'] = {r: r4(SK.DISPLAY[r]) for r in SK.ROOTS}
C['meta'] = dict(version='1.0', units='metres, degrees', built='locally with tools/snow_style (Blender 5.2.3), 27.10.2026',
                 frame="each root in its own frame: z up, the front -y; runway modules: the middle of the top (z = 0), +y along the "
                       "runway; lights, marker: the middle of the pad on the ground; the pointer: the post foot; the plug: BunkerHangar's "
                       "Link_BlastDoor. In af.blend the roots stand apart (display_offset); FBX with the root at the origin",
                 assembly='runway: RWY_Threshold at each end (-y edge = the end of the paving; turned 180 deg at the far end), then '
                          'RWY_Num17 / RWY_Num35, then RWY_Slab / RWY_SlabWorn mixed, each module snapped at Snap_*_N, some turned 180 '
                          'deg against repeats; AF_EdgeLight every 60 m 1.5 m outside both edges, AF_ThresholdLight in a row across '
                          'the end; AF_HangarPlug into BunkerHangar Link_BlastDoor instead of BlastDoor (the airfield hangar has no way '
                          'down); AF_Sign at the turn-off from the east road',
                 unity='position (x, y, z) -> Unity (-x, z, -y) in the prefab; axis likewise; angle -> -angle (Unity is left-handed); '
                       'box centre likewise, size (sx, sy, sz) -> (sx, sz, sy); the root front (-y) is the prefab +Z',
                 display_offset=INFO['display_offset'],
                 colliders='BoxCollider per entry on its parent: center / size in the parent own frame. COL_ objects are reference '
                           'only, not in the FBX',
                 lamps='af_lights.json', model='af.blend', textures='tex',
                 materials='M_AF_Runway (the five modules, one 2048 atlas) / M_AF_AFProps (lights, marker, pointer) / M_AF_AFPlug: '
                           'baked PSX atlases (point filter); M_AF_Panel: the arrow board, the door plate, the dome tiles; '
                           'M_AF_Lamp_Edge / _Off, M_AF_Lamp_Thr / _Off; M_AF_Glow: additive halo',
                 ix='none: nothing opens (the plug door is static)')
sfx = '_draft' if DRAFT else ''
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_set(True)
json.dump(_nz(C), open(os.path.join(OUT, f'af_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
kinds = {}
for p in C['parts'].values():
    kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
INFO['contract'] = dict(parts=len(C['parts']), sockets=len(C['sockets']), colliders=len(C['colliders']), kinds=kinds)
log('contract', INFO['contract'], 'tris', tris, tris_root)
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    uvs = o.data.uv_layers
    if 'PSX' in uvs:
        for u in [u for u in uvs if u.name != 'PSX']:
            uvs.remove(u)
        uvs['PSX'].active = True
    if 'zone' in o.data.attributes and not DRAFT:
        o.data.attributes.remove(o.data.attributes['zone'])
json.dump(_nz(INFO), open(os.path.join(OUT, f'af{sfx}.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'af{sfx}.blend'))
log('saved', f'af{sfx}.blend')
