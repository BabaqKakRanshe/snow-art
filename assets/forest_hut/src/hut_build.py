"""Forester's hut build (hut_kit): one object per part with its pivot as the origin; PSX atlases baked with psxbake +
hut_paint: Hut (the hut, the sign and the hunting stand, at the generator shed's pixel density; the stand stands 11 m away:
its positions are baked in its own frame), HutProps (the small things); the panel atlas (hut_tex) on the map, the calendar and
the sign face, the lantern / oil lamp lenses (burning and out), the glow cards, glass; the lamp json, the interaction
contract (parts, sockets, colliders, meta, the map placement of the three roots), the hierarchy.
python3 -I hut_build.py [--draft]  -> out/hut.blend, out/hut.json, out/hut_contract.json, out/hut_lights.json, tex/hut/*
--draft: no bakes, flat zone colours (layout preview) -> out/hut_draft.blend"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler, Quaternion
import psxlib as P
import psxbake as PB
import hut_tex as HT
import gen_lights as GL
import van_lights as VL
import gen_kit as K
import hut_kit as HK

DRAFT = '--draft' in sys.argv
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'hut')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
SHED_PPM = 51.3                                       # the generator shed's building atlas (px / m): the project's pixel
HUT_U = dict(p=(-474.0, 28.3963, 404.0), q=(0.0, 0.481952, 0.0, 0.876197))   # TowerHut in Forest (Unity p, q xyzw)


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
    """hut frame -> Unity (prefab-local): (x, y, z) -> (-x, z, -y)"""
    return [round(-float(v[0]), 4) + 0.0, round(float(v[2]), 4) + 0.0, round(-float(v[1]), 4) + 0.0]


# ------------------------------------------------------------------ lamp types: the storm lantern and the oil lamp
ss, window = VL.smoothstep, VL.window


def em_storm(l):
    """storm lantern seen from the flame: the fuel tank shades the ground under it (to ~35 deg off the vertical), the
    cap over the globe shades upwards (from ~140 deg); the four guard wires throw faint spokes; the hot flame a little
    brighter level with it"""
    th = np.degrees(np.arccos(np.clip(l[..., 2], -1, 1)))
    az = np.arctan2(l[..., 1], l[..., 0])
    body = ss(20, 42, th) * (1 - ss(128, 152, th))
    level = 0.80 + 0.20 * np.exp(-0.5 * ((th - 90) / 30.0) ** 2)
    wires = 1 - 0.20 * ss(0.86, 0.98, np.cos(4 * (az - np.pi / 4)))
    return np.clip(body * level * wires + 0.04, 0, 1)


def em_oil(l):
    """hanging oil lamp: the enamel shade over the chimney throws the light down and out, cut at its rim (~105 deg
    off the vertical); the font under the flame shades the floor straight under it a little"""
    th = np.degrees(np.arccos(np.clip(l[..., 2], -1, 1)))
    return np.clip((1 - ss(96, 112, th)) * (0.55 + 0.45 * ss(8, 30, th)) * (0.85 + 0.15 * np.cos(np.radians(th))) + 0.03, 0, 1)


GL.TYPES.clear()
GL.TYPES.update({
    'stormlantern': dict(em=em_storm, I=0.9, cd=10, cct=1900, filt=(1.0, 0.96, 0.90), unity='Point', rng=11.0, group='lantern',
                         shadows=True, res=128, lens_floor=0.15,
                         desc='storm lantern (kerosene, flat wick) on its hook right of the door; burns at the start, goes out '
                              'for good at X01; flickers (the U3 lantern\'s settings: Point, 0.9, range 11)'),
    'oillamp': dict(em=em_oil, I=0.7, cd=12, cct=2000, filt=(1.0, 0.97, 0.92), unity='Point', rng=7.0, group='hut', shadows=True,
                    res=128, lens_floor=0.10,
                    desc='kerosene lamp with an enamel shade, hanging under the ridge; off at the start (light it: OPEN)'),
})

bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
PB_BASE, PB_EMI = HT.build(TEX)
if not DRAFT:
    INFO['ies'] = GL.write_ies_all(os.path.join(TEX, 'IES'))

# ------------------------------------------------------------------ 1. geometry
HK.build_hut()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts']]
assert not missing, f'objects without a contract entry: {missing}'
objs = {}
WELD = ('TowerHut', 'Hochsitz')
for name, k in K.KBS.items():
    if name in WELD:
        bmesh.ops.remove_doubles(k.bm, verts=list(k.bm.verts), dist=1e-4)
    p = C['parts'][name]
    o = k.to_object(name, pivot=Vector(p['pivot']))
    if p.get('yaw'):                                  # placed roots (and their children): the mesh in their own axes
        o.data.transform(Matrix.Rotation(math.radians(-p['yaw']), 4, 'Z'))
        o.rotation_euler = (0.0, 0.0, math.radians(p['yaw']))
    objs[name] = o
log('objects', len(objs))
bpy.context.view_layer.update()
groups = {}
for name, o in objs.items():
    groups.setdefault(K.ATLAS[name], []).append(o)

# ------------------------------------------------------------------ 2. atlases (or flat zone colours for the draft)
INFO['atlases'] = {}
if DRAFT:
    import hut_paint as HP
    cache = {}

    def zmat(z):
        if z not in cache:
            m = bpy.data.materials.new(f'draft_{z}')
            m.use_nodes = True
            pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            c = PB.lin(*HP.DRAFT_COL.get(z, (128, 128, 128)))
            pb.inputs['Base Color'].default_value = (float(c[0]), float(c[1]), float(c[2]), 1)
            pb.inputs['Roughness'].default_value = 0.75
            cache[z] = m
        return cache[z]

    for name, o in objs.items():
        if K.ATLAS[name] not in ('Hut', 'HutStand', 'HutProps'):
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
    import hut_paint as HP
    # one building atlas for the hut, the sign and the stand (as the shed's); the stand's positions / normals / zones are
    # baked in its own frame, 2.6 m down (inside the +-4 m bake range), its AO where it stands
    st = objs['Hochsitz']
    keep = (st.location.copy(), st.rotation_euler.copy())
    st.location, st.rotation_euler = Vector((0.0, 0.0, HK.HS_BAKE_DZ)), Euler((0.0, 0.0, 0.0))
    bpy.context.view_layer.update()
    zs = {z: 0.75 for z in HK.STAND_ZONES}                       # the stand is seen from 10 m and more, the roof from below
    zs.update({K.Z_ROOF: 0.70, HK.Z_STONE: 0.80})
    prep = PB.prepare_atlas(groups['Hut'], size=1024, ppm_cap=SHED_PPM, zone_scale=zs)
    st.location, st.rotation_euler = keep
    bpy.context.view_layer.update()
    PB.finish_atlas('Hut', groups['Hut'], prep, HP.paint_hut_all, TEX, prefix='T_Hut_', mat_prefix='M_Hut_', ao_min=0.35,
                    ao_dist=0.40, rough=0.85, log=log, info=INFO['atlases'],
                    prio_zones=(K.Z_TRIMW, HK.Z_BLANKET, HK.Z_MATTRESS, K.Z_RUSTPIPE))
    PB.make_atlas('HutProps', groups['HutProps'], HP.paint_props, TEX, prefix='T_Hut_', mat_prefix='M_Hut_', size=None, ppm=64.0,
                  ao_min=0.40, ao_dist=0.14, rough=0.75, log=log, info=INFO['atlases'], ppm_cap=64.0,
                  prio_zones=(HK.Z_JACKET, HK.Z_LANTERN, HK.Z_TIN, HK.Z_ENAMELW, HK.Z_BRASS))

    def zone_ppm(objs_, size, zones):
        """texel density (px / m) of the faces in `zones` on an atlas"""
        a3 = a2 = 0.0
        for o in objs_:
            me, M = o.data, o.matrix_world
            uvl, za = me.uv_layers['PSX'], me.attributes['zone']
            for p in me.polygons:
                if round(za.data[p.index].value) not in zones:
                    continue
                vs = [M @ me.vertices[i].co for i in p.vertices]
                us = [uvl.data[li].uv for li in p.loop_indices]
                for i in range(1, len(vs) - 1):
                    a3 += (vs[i] - vs[0]).cross(vs[i + 1] - vs[0]).length / 2
                    e1, e2 = us[i] - us[0], us[i + 1] - us[0]
                    a2 += abs(e1.x * e2.y - e1.y * e2.x) / 2
        return round(size * math.sqrt(a2 / a3), 1) if a3 else None

    INFO['atlases']['Hut']['ppm_parts'] = {
        'walls outside': zone_ppm(groups['Hut'], 1024, (K.Z_CLAD,)),
        'inside (ply, floor, timber, roof underside)': zone_ppm(groups['Hut'], 1024, (K.Z_LINING, HK.Z_FLOORB, K.Z_TIMBER, K.Z_ROOFUNDER)),
        'roof on top': zone_ppm(groups['Hut'], 1024, (K.Z_ROOF,)),
        'stand': zone_ppm(groups['Hut'], 1024, tuple(HK.STAND_ZONES))}
    log('Hut texel density by part', INFO['atlases']['Hut']['ppm_parts'])

# ------------------------------------------------------------------ 3. explicit materials
m_panel = PB.tex_mat('M_Hut_Panel', PB_BASE, PB_EMI, 0.0, rough=0.6)
lens_mats = {}
for kname, night in (('lantern', 3.0), ('oillamp', 3.0)):
    for sfx, ne in (('', night), ('_Off', 0.0)):
        m = PB.tex_mat('M_Hut_Lamp_' + kname.capitalize() + sfx, PB_BASE, PB_EMI, ne, rough=0.2)
        m['lamp_kind'] = kname
        m.use_fake_user = bool(sfx)                    # the 'out' variants are on no mesh: keep them in the file
        lens_mats[kname + sfx] = m
m_glow = bpy.data.materials.new('M_Hut_Glow')                 # additive halo: emission from the panel's glow tile
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
m_glass = P.psx_glass('M_Hut_Glass')
for name, o in objs.items():
    a = K.ATLAS[name]
    if a in ('Hut', 'HutStand', 'HutProps'):
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
    elif a == 'glass':
        o.data.materials.append(m_glass)
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

# ------------------------------------------------------------------ 5. lamps: LIGHT_ empties + lights json
LMETA = GL.meta()
lens_of = {'Lantern': 'Lens_Lantern', 'OilLamp': 'Lens_OilLamp'}
glow_of = {'Lantern': 'Glow_Lantern'}
lamp_parent = {'Lantern': 'Lantern', 'OilLamp': 'Lamp_Oil'}
items = []
for name, pos, d, typ, up in K.LAMPS:
    e = bpy.data.objects.new('LIGHT_' + name, None)
    bpy.context.scene.collection.objects.link(e)
    e.empty_display_type, e.empty_display_size = 'SINGLE_ARROW', 0.12
    dv = Vector(d).normalized()
    uv_ = Vector(up)
    uv_ = (uv_ - dv * uv_.dot(dv)).normalized()
    xv_ = uv_.cross(dv)                                  # empty: +Z = beam, +Y = the json 'up' (Unity light frame)
    e.matrix_world = Matrix.Translation(Vector(pos)) @ Matrix((xv_, uv_, dv)).transposed().to_4x4()
    T = GL.TYPES[typ]
    e['type'], e['group'], e['dir'], e['up'], e['color'] = typ, LMETA[typ]['group'], list(dv), list(up), LMETA[typ]['color']
    e['intensity_urp'] = T['I']
    e['lens'] = lens_of[name]
    attach(e, objs[lamp_parent[name]])
    items.append(dict(socket='LIGHT_' + name, lens=lens_of[name], glow=glow_of.get(name, ''), parent=lamp_parent[name], type=typ,
                      unityLight=T['unity'], position=r4(pos), forward=r4(d), up=r4(up), positionUnity=to_unity(pos),
                      forwardUnity=to_unity(d), upUnity=to_unity(up), intensityURP=T['I'], peakCandela=T['cd'], kelvin=T['cct'],
                      filterLinear=list(T['filt']), colorLinear=r4(GL.colour(typ)), range=T['rng'], group=T['group'],
                      shadows=bool(T['shadows']), ies='IES/%s.ies' % typ, desc=T['desc'],
                      startsOn=(name == 'Lantern')))
json.dump(dict(note='forester\'s hut lamps. position / forward / up: hut frame (TowerHut prefab: x right seen from the door side, '
                    'y into the hut, z up, m); *Unity: (-x, z, -y) in the prefab. intensityURP at 100 %. group lantern = the storm '
                    'lantern outside (burns at the start; X01 puts it out for good: light off, glow hidden, lens material -> '
                    'M_Hut_Lamp_Lantern_Off); group hut = the oil lamp inside (off at the start). lens: the glowing object, '
                    'glow: the halo cards. Point lights: the IES files describe the shape (URP Point lights do not use them).',
               lights=items), open(os.path.join(OUT, 'hut_lights.json'), 'w'), indent=1)
INFO['lamps'] = len(items)

# ------------------------------------------------------------------ 6. colliders
coll = bpy.data.collections.new('Colliders')
bpy.context.scene.collection.children.link(coll)
C['colliders'] = []
for name, par, (x0, x1, y0, y1, z0, z1), rot, local in HK.static_boxes():
    Pobj = objs[par]
    c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    size = Vector((x1 - x0, y1 - y0, z1 - z0))
    kb_ = K.KB()
    kb_.box(-size.x / 2, size.x / 2, -size.y / 2, size.y / 2, -size.z / 2, size.z / 2, 0)
    ob = kb_.to_object('COL_' + name, coll=coll)
    if local:                                         # box axes = the parent's own axes
        ob.matrix_world = Pobj.matrix_world @ Matrix.Translation(c)
    else:
        ob.location = c
        if rot:
            ob.rotation_euler = Euler([math.radians(a) for a in rot], 'XYZ')
    ob.display_type = 'WIRE'
    ob.hide_render = True
    ob['collider'] = 'box'
    attach(ob, Pobj)
    bpy.context.view_layer.update()
    cw = ob.matrix_world.translation.copy()
    lc = Pobj.matrix_world.inverted() @ cw
    ent = dict(name='COL_' + name, parent=par, type='box', center=r4(lc), size=r4(size), center_hut=r4(cw),
               centerUnity=to_unity(lc), sizeUnity=r4((size.x, size.z, size.y)))
    if rot and not local:
        assert rot[0] == 0 and rot[2] == 0
        ent['rotation'] = [float(a) for a in rot]
        ent['rotationUnity'] = [0.0, 0.0, float(rot[1])]             # about Blender +y -> about Unity +z, same sign
    C['colliders'].append(ent)
log('colliders', len(C['colliders']))

# ------------------------------------------------------------------ 7. knock points (rays onto the shell)
hide_for_rays = [o for o in bpy.data.objects if o.name.startswith(('COL_', 'Glow_'))]
for o in hide_for_rays:
    o.hide_viewport = True
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
nk = 0
for name, org, d in HK.knock_rays():
    hit, loc, nrm, idx, ob, mw = bpy.context.scene.ray_cast(dg, Vector(org), Vector(d), distance=5.0)
    if not hit:
        log('WARN knock ray missed', name)
        continue
    par = ob.name if ob.name in objs else 'TowerHut'
    C['sockets'][name] = dict(pos=r4(loc + nrm * 0.005), kind='knock', parent=par, dir=r4(nrm),
                              note='something knocks / scratches here from outside (sound, frost-print decal)')
    nk += 1
for o in hide_for_rays:
    o.hide_viewport = False
INFO['knock_points'] = nk

# ------------------------------------------------------------------ 8. part boxes (grab / hit box of moving parts and items)
nb = 0
for k, p in C['parts'].items():
    o = objs.get(k)
    if o is None or p['kind'] == 'static' or k.startswith(('Lens_', 'Glow_')):
        continue
    co = np.array([tuple(v.co) for v in o.data.vertices])
    lo, hi = co.min(0), co.max(0)
    p['box'] = dict(center=r4((lo + hi) / 2), size=r4(np.maximum(hi - lo, 0.004)))
    nb += 1
INFO['part_boxes'] = nb

# ------------------------------------------------------------------ 9. meta, map placement, stats, save
qh = Quaternion((HUT_U['q'][3], HUT_U['q'][0], HUT_U['q'][1], HUT_U['q'][2]))
yaw_h = 2 * math.degrees(math.atan2(HUT_U['q'][1], HUT_U['q'][3]))


def unity_world(pos, yaw_local=0.0):
    """hut-frame point / yaw -> Forest (Unity) world position and rotation (y-up, left-handed): yaw about Blender +z = a
    rotation about Unity +y by -yaw"""
    v = to_unity(pos)
    a = math.radians(yaw_h)
    x = v[0] * math.cos(a) + v[2] * math.sin(a)
    z = -v[0] * math.sin(a) + v[2] * math.cos(a)
    p = [round(HUT_U['p'][0] + x, 4), round(HUT_U['p'][1] + v[1], 4), round(HUT_U['p'][2] + z, 4)]
    yu = yaw_h - yaw_local
    h = math.radians(yu) / 2
    return dict(p=p, q=[0.0, round(math.sin(h), 6), 0.0, round(math.cos(h), 6)], yawUnity=round(yu, 3))


placement = {'TowerHut': dict(p=list(HUT_U['p']), q=list(HUT_U['q']), yawUnity=round(yaw_h, 3))}
for root in ('Hochsitz', 'Sign_Forsthuette'):
    placement[root] = unity_world(C['parts'][root]['pivot'], C['parts'][root].get('yaw', 0.0))
INFO['placement'] = placement
C['meta'] = dict(units='metres, degrees',
                 frame='hut frame (the TowerHut prefab\'s): x to the right seen from the door side, y into the hut (door -> back '
                       'wall), z up; origin = the middle of the footprint on the ground; floor z = 0.33',
                 unity='position (x, y, z) -> Unity (-x, z, -y) in the TowerHut prefab; axis likewise; angle -> -angle (Unity is '
                       'left-handed); box centre likewise, box size (sx, sy, sz) -> (sx, sz, sy)',
                 roots='three roots, each its own prefab at its Update 3 place: TowerHut (the hut), Hochsitz (the hunting stand), '
                       'Sign_Forsthuette (the sign at the path). part.yaw: the root\'s turn about z in the hut frame (the object '
                       'carries it as its rotation, its mesh is in its own axes); map_placement: Forest (Unity world) p / q of '
                       'each root',
                 map_placement=placement,
                 colliders='colliders: BoxCollider per entry on its parent: center / size in the parent\'s own frame (Blender), '
                           'centerUnity / sizeUnity the same in Unity axes; rotation = Blender XYZ euler of the box (the two roof '
                           'slopes), rotationUnity = Unity euler; center_hut: the box centre in the hut frame. part.box: the grab / '
                           'hit box of a moving part or item in its own frame',
                 lamps='hut_lights.json', model='hut.blend', textures='tex',
                 materials='M_Hut_Hut (the hut, the sign, the stand) / M_Hut_HutProps: baked PSX atlases (point filter); M_Hut_Panel: map, '
                           'calendar, sign face; M_Hut_Lamp_Lantern / _Off, M_Hut_Lamp_Oillamp / _Off: lenses burning / out '
                           '(base + emission textures, night_emit = emission strength); M_Hut_Glow: additive halo (emission '
                           'texture only); M_Hut_Glass',
                 prologue='S2 / X01 (FOREST_OPENING.md): the door IX_HutDoor_1 starts open, the lantern burns; Jerrycan_Hut, '
                          'Funnel_Hut, the flashlight and note_forester spawn at the Spot_ sockets (same places as Update 3); X01 = '
                          'LIGHT_Lantern off + Glow_Lantern hidden + Lens_Lantern -> M_Hut_Lamp_Lantern_Off')
for k, p in C['parts'].items():
    if p.get('default') == 'hidden' and k in objs:
        objs[k].hide_render = True
        objs[k].hide_set(True)
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_set(True)
sfx = '_draft' if DRAFT else ''
json.dump(_nz(C), open(os.path.join(OUT, f'hut_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
kinds = {}
for p in C['parts'].values():
    kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
INFO['contract'] = dict(parts=len(C['parts']), sockets=len(C['sockets']), colliders=len(C['colliders']), kinds=kinds)
log('contract', INFO['contract'])
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    uvs = o.data.uv_layers
    if 'PSX' in uvs:
        for u in [u for u in uvs if u.name != 'PSX']:
            uvs.remove(u)
        uvs['PSX'].active = True
        uvs['PSX'].active_render = True
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('COL_')]
INFO['tris'] = sum(P.tri_count(o) for o in meshes)
INFO['tris_by_atlas'] = {}
for o in meshes:
    a = K.ATLAS.get(o.name, '?')
    INFO['tris_by_atlas'][a] = INFO['tris_by_atlas'].get(a, 0) + P.tri_count(o)
INFO['objects'] = sorted(o.name for o in meshes)
INFO['empties'] = sorted(o.name for o in bpy.data.objects if o.type == 'EMPTY')
lo_, hi_ = P.world_bbox([o for o in meshes if o.name not in ('Hochsitz',) and not o.name.startswith('Sign_')])
INFO['bbox_hut'] = [lo_.round(3).tolist(), hi_.round(3).tolist()]
log('tris', INFO['tris'], INFO['tris_by_atlas'], 'bbox (the hut)', INFO['bbox_hut'])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'hut{sfx}.blend'))
json.dump(INFO, open(os.path.join(OUT, f'hut{sfx}.json'), 'w'), indent=1)
log('saved hut' + sfx)
