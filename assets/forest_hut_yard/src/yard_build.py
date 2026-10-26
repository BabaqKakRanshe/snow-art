"""forest_hut_yard build (adapted from the forest_start build): one object per part with its pivot as the origin, each root in its
own collection standing at yard_kit.DISPLAY; PSX atlases baked with psxbake + yard_paint: YardWood (outhouse, feeder, polter,
porch; the shed pixel 51.3 px/m) and YardProps (the pointer, the lantern; 64 px/m); the panel atlas (yard_tex) on the arrow board,
the map and the lantern glass; lens lit / off, glow cards; yard_lights.json; the contract (parts, sockets, colliders, meta).
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_hut_yard/yard_build.py [--draft]
-> out/yard.blend, out/yard.json, out/yard_contract.json, out/yard_lights.json, tex/yard/*"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import psxlib as P
import psxbake as PB
import yard_tex as YT
import gen_kit as K
import yard_kit as SK

DRAFT = '--draft' in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex', 'yard')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
SHED_PPM = 51.3                                       # the generator shed's building atlas (px / m): the project's pixel
PB.POS_SCALE = 40.0                                   # bake range +-20 m: the roots stand from x -8.3 to 9.8


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
    'lantern': dict(unity='Point', I=0.9, rng=7.0, cct=2400, color=(1.0, 0.70, 0.30), group='trail', spot=None,
                    desc='the battery lantern with yellow glass on the trail-head pointer (forest_gear decision: battery, yellow); group '
                         'trail: lit at the start, goes out at X01 with the hut lantern'),
}

bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
PB_BASE, PB_EMI = YT.build(TEX)

# ------------------------------------------------------------------ 1. geometry
SK.build_yard()
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
    if name in ('HutOuthouse', 'HutPorch', 'HutFeeder'):
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
import yard_paint as SPT
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
        if K.ATLAS[name] not in ('YardWood', 'YardProps'):
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
    PB.make_atlas('YardWood', groups['YardWood'], SPT.paint_wood, TEX, prefix='T_Yard_', mat_prefix='M_Yard_', size=None, ppm=SHED_PPM,
                  ao_min=0.35, ao_dist=0.40, rough=0.85, log=log, info=INFO['atlases'], ppm_cap=SHED_PPM,
                  zone_scale={K.Z_ROOF: 0.75, K.Z_ROOFUNDER: 0.6, SK.Z_STONE: 0.6, SK.Z_ILIN: 0.8},
                  prio_zones=(K.Z_TRIMW, SK.Z_END, SK.Z_HAY))
    PB.make_atlas('YardProps', groups['YardProps'], SPT.paint_props, TEX, prefix='T_Yard_', mat_prefix='M_Yard_', size=None,
                  ppm=64.0, ao_min=0.40, ao_dist=0.20, rough=0.8, log=log, info=INFO['atlases'], ppm_cap=64.0,
                  prio_zones=(SK.Z_LMETAL,))

# ------------------------------------------------------------------ 3. explicit materials
m_panel = PB.tex_mat('M_Yard_Panel', PB_BASE, PB_EMI, 0.0, rough=0.6)
lens_mats = {}
for kname, night in (('lant', 3.0),):
    for sfx, ne in (('', night), ('_Off', 0.0)):
        m = PB.tex_mat('M_Yard_Lamp_' + kname.capitalize() + sfx, PB_BASE, PB_EMI, ne, rough=0.2)
        m['lamp_kind'] = kname
        m.use_fake_user = bool(sfx)                    # the 'off' variants are on no mesh: keep them in the file
        lens_mats[kname + sfx] = m
m_glow = bpy.data.materials.new('M_Yard_Glow')               # additive halo: emission from the panel's glow tiles
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
    if a in ('YardWood', 'YardProps'):
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
lens_of = {'Lant': 'Lens_Lant'}
glow_of = {'Lant': 'Glow_Lant'}
lamp_parent = {'Lant': 'Lamp_Lant'}
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
                                         note=f'{T["unity"]} light ({typ}): yard_lights.json')
json.dump(dict(note='hut yard lamps. position / forward / up: the root own frame (Blender: z up, the front -y, m); *Unity: (-x, z, '
                    '-y) in the prefab. intensityURP at 100 %. The lens (Lens_*) switches M_Yard_Lamp_<Kind> (lit) / _Off, the halo card '
                    '(Glow_*) is shown with it. group trail: the pointer lantern; all start off in the file.',
               lights=items), open(os.path.join(OUT, 'yard_lights.json'), 'w'), indent=1)
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
C['meta'] = dict(version='1.0', units='metres, degrees', built='locally with tools/snow_style (Blender 5.2.3), 26.10.2026',
                 frame='each root (HutOuthouse, HutFeeder, HutPolter, HutSign, HutPorch, HutMap) in its own frame: z up, the front -y; '
                       'origin on the ground (z = 0) - outhouse, feeder, polter: the middle of the footprint; the sign: the post foot; the '
                       'porch: the middle of the hut front (its back +y against the facade, the step at the door); the map: its middle on the table top. In '
                       'yard.blend the roots stand apart (display_offset); FBX with the root at the origin',
                 unity='position (x, y, z) -> Unity (-x, z, -y) in the prefab; axis likewise; angle -> -angle (Unity is left-handed); '
                       'box centre likewise, size (sx, sy, sz) -> (sx, sz, sy); the root front (-y) is the prefab +Z',
                 display_offset=INFO['display_offset'],
                 colliders='BoxCollider per entry on its parent: center / size in the parent own frame; rotation = Blender XYZ euler '
                           '(the outhouse roof), rotationUnity the Unity euler. COL_ objects are reference only, not in the FBX',
                 lamps='yard_lights.json', model='yard.blend', textures='tex',
                 materials='M_Yard_YardWood (outhouse, feeder, polter, porch) / M_Yard_YardProps (the pointer, the lantern): baked PSX '
                           'atlases (point filter); M_Yard_Panel: the arrow board, the map, the lens tile; M_Yard_Lamp_Lant / _Off; '
                           'M_Yard_Glow: additive halo',
                 ix='IX_Door (the outhouse door) - name without a number: Unity gives it its IX number on placement')
sfx = '_draft' if DRAFT else ''
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_set(True)
json.dump(_nz(C), open(os.path.join(OUT, f'yard_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
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
json.dump(_nz(INFO), open(os.path.join(OUT, f'yard{sfx}.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'yard{sfx}.blend'))
log('saved', f'yard{sfx}.blend')
