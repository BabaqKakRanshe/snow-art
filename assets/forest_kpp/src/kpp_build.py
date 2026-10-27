"""Checkpoint v2 build (kpp_kit): one object per part with its pivot as the origin; the snow_kit instances (KIT_INST) as
empties that instance the kit's collections linked from ../snow_kit/snow_kit.blend (props: kit_item, ix_ids); PSX atlases baked with psxbake + kpp_paint:
Kpp (the booth) and KppYard (the barrier and the gate) at the generator shed's pixel density (positions baked with
POS_SCALE 40: the barrier 7 m out and the gate's parking end 18 m away bake where they stand), KppProps (the small things);
the panel atlas
(kpp_tex) on the signs, papers, labels, the clock, the radio; the lenses (the fluorescent tube, the bulkhead dome: lit
and off), the glow cards, glass, the barbed wire (alpha band, Update 7's T_Kpp_Barbed_A_px); the wire previews (the K9 rule);
the lamp json, the interaction contract (parts, sockets, colliders, kit_instances, wires, keep_clear, meta: the map and game
placement of the three roots), the hierarchy.
python3 -I kpp_build.py [--draft]  -> out/kpp.blend, out/kpp.json, out/kpp_contract.json, out/kpp_lights.json, tex/kpp/*
--draft: no bakes, flat zone colours (layout preview) -> out/kpp_draft.blend"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler, Quaternion
import psxlib as P
import psxbake as PB
import kpp_tex as KT
import gen_lights as GL
import van_lights as VL
import gen_kit as K
import kpp_kit as KK
import snowkit_spec as SKS
import snowkit_kit as SKK

DRAFT = '--draft' in sys.argv
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'kpp')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
SHED_PPM = 51.3                                       # the generator shed's building atlas (px / m): the project's pixel
PB.POS_SCALE = 40.0                                   # bake range +-20 m: the gate's parking end stands 18 m out
KPP_U = dict(p=(313.0406, 16.4376, -289.5625), q=(0.0, 0.069756, 0.0, 0.997564))   # Checkpoint in Forest (Unity p, q xyzw)
U3_ROOTS = {'Checkpoint': ((313.0406, 16.4376, -289.5625), 8.0)}                  # Forest_Layout.json (Update 3)


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
    """booth frame -> Unity (prefab-local): (x, y, z) -> (-x, z, -y)"""
    return [round(-float(v[0]), 4) + 0.0, round(float(v[2]), 4) + 0.0, round(-float(v[1]), 4) + 0.0]


# ------------------------------------------------------------------ lamp types: the fluorescent batten, the bulkhead
ss, window = VL.smoothstep, VL.window


def em_fluor(l):
    """fluorescent batten seen from the tube: the white housing over it cuts everything above ~100 deg off the vertical;
    along the tube (lamp X) the light falls off like a line source"""
    th = np.degrees(np.arccos(np.clip(l[..., 2], -1, 1)))
    along = np.clip(np.abs(l[..., 0]), 0, 1)
    return np.clip((1 - ss(92, 108, th)) * (0.50 + 0.50 * np.sqrt(1 - along ** 2)) + 0.03, 0, 1)


GL.TYPES.clear()
GL.TYPES.update({
    'fluor': dict(em=em_fluor, I=0.45, cd=40, cct=6000, filt=(0.92, 1.0, 1.0), unity='Point', rng=6.5, group='power',
                  shadows=False, res=128, lens_floor=0.10,
                  desc='fluorescent batten under the rafters (one 36 W tube): v2 - on with the booth\'s power only, flickering a '
                       'few seconds as it strikes (flicker min / max / speed as Update 3\'s Light_booth); Point 0.45, range 6.5'),
    'bulkhead_kpp': dict(em=GL.em_bulkhead, I=1.0, cd=60, cct=2700, filt=(1.0, 1.0, 1.0), unity='Point', rng=9.0, group='power',
                         shadows=False, res=128, lens_floor=0.2,
                         desc='caged bulkhead over the door (the shed\'s), 60 W incandescent: on with the booth\'s power (Update 3: '
                              'Point 1.0, range 9, off until power)'),
})
FLICKER = {'fluor': dict(min=0.08, max=1.0, speed=5.0)}

bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
PB_BASE, PB_EMI, PB_CHAIN, PB_BARB = KT.build(TEX)
PB_BARB = os.path.join(OUT, 'forest_fences', 'tex', 'replacements', 'T_Kpp_Barbed_A_px.png')   # Update 7's (in the project)
KIT_BLEND = os.path.join(HERE, 'snow_kit', 'snow_kit.blend')        # -> ../snow_kit/snow_kit.blend from the package's kpp.blend
if not DRAFT:
    INFO['ies'] = GL.write_ies_all(os.path.join(TEX, 'IES'))

# ------------------------------------------------------------------ 1. geometry
KK.build_kpp()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts']]
assert not missing, f'objects without a contract entry: {missing}'
objs = {}
WELD = ('Checkpoint', 'Barrier')                 # not the gate: its rail is cut in pieces for the atlas
for name, k in K.KBS.items():
    if name in WELD:
        bmesh.ops.remove_doubles(k.bm, verts=list(k.bm.verts), dist=1e-4)
    p = C['parts'][name]
    o = k.to_object(name, pivot=Vector(p['pivot']))
    assert not p.get('yaw'), 'the KPP roots share the booth axes'
    objs[name] = o
log('objects', len(objs))
bpy.context.view_layer.update()
groups = {}
for name, o in objs.items():
    groups.setdefault(K.ATLAS[name], []).append(o)

# ------------------------------------------------------------------ 2. atlases (or flat zone colours for the draft)
INFO['atlases'] = {}
import kpp_paint as KP
if DRAFT:
    cache = {}

    def zmat(z):
        if z not in cache:
            m = bpy.data.materials.new(f'draft_{z}')
            m.use_nodes = True
            pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            c = PB.lin(*KP.DRAFT_COL.get(z, (128, 128, 128)))
            pb.inputs['Base Color'].default_value = (float(c[0]), float(c[1]), float(c[2]), 1)
            pb.inputs['Roughness'].default_value = 0.75
            m.diffuse_color = (float(c[0]), float(c[1]), float(c[2]), 1)
            cache[z] = m
        return cache[z]

    for name, o in objs.items():
        if K.ATLAS[name] not in ('Kpp', 'KppYard', 'KppProps'):
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
    zs = {K.Z_ROOF: 0.70, K.Z_SLAB: 0.75}
    PB.make_atlas('Kpp', groups['Kpp'], KP.paint_kpp, TEX, prefix='T_Kpp_', mat_prefix='M_Kpp_', size=1024, ao_min=0.35,
                  ao_dist=0.40, rough=0.85, log=log, info=INFO['atlases'], ppm_cap=SHED_PPM, zone_scale=zs,
                  prio_zones=(K.Z_TRIMW, KK.Z_BOLLARD, KK.Z_KEYBOX))
    PB.make_atlas('KppYard', groups['KppYard'], KP.paint_kpp, TEX, prefix='T_Kpp_', mat_prefix='M_Kpp_', size=512, ao_min=0.35,
                  ao_dist=0.40, rough=0.85, log=log, info=INFO['atlases'], ppm_cap=SHED_PPM, zone_scale={KK.Z_CONC: 0.8},
                  prio_zones=(KK.Z_BOOM, KK.Z_BARPOST))
    PB.make_atlas('KppProps', groups['KppProps'], KP.paint_props, TEX, prefix='T_Kpp_', mat_prefix='M_Kpp_', size=None, ppm=64.0,
                  ao_min=0.40, ao_dist=0.14, rough=0.75, log=log, info=INFO['atlases'], ppm_cap=64.0,
                  prio_zones=(KK.Z_PHONE, KK.Z_VEST, KK.Z_EXTP, KK.Z_BELLP, KK.Z_BINDER))

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

    INFO['atlases']['Kpp']['ppm_parts'] = {
        'walls outside': zone_ppm(groups['Kpp'], 1024, (K.Z_CLAD,)),
        'inside (ply, floor, timber, roof underside)': zone_ppm(groups['Kpp'], 1024, (K.Z_LINING, K.Z_FLOOR, K.Z_TIMBER, K.Z_ROOFUNDER)),
        'roof on top': zone_ppm(groups['Kpp'], 1024, (K.Z_ROOF,)),
        'barrier (boom, posts)': zone_ppm(groups['KppYard'], 512, (KK.Z_BOOM, KK.Z_BARPOST)),
        'gate (galvanised)': zone_ppm(groups['KppYard'], 512, (K.Z_GALV,))}
    log('Kpp texel density by part', INFO['atlases']['Kpp']['ppm_parts'])

# ------------------------------------------------------------------ 3. explicit materials
m_panel = PB.tex_mat('M_Kpp_Panel', PB_BASE, PB_EMI, 0.0, rough=0.6)
lens_mats = {}
for kname, night in (('fluor', 3.0), ('bulk', 3.0)):
    for sfx, ne in (('', night), ('_Off', 0.0)):
        m = PB.tex_mat('M_Kpp_Lamp_' + kname.capitalize() + sfx, PB_BASE, PB_EMI, ne, rough=0.2)
        m['lamp_kind'] = kname
        m.use_fake_user = bool(sfx)                    # the 'off' variants are on no mesh: keep them in the file
        lens_mats[kname + sfx] = m
m_glow = bpy.data.materials.new('M_Kpp_Glow')                 # additive halo: emission from the panel's glow tiles
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
m_glass = P.psx_glass('M_Kpp_Glass')
def cutout_mat(name, path, tile):
    """tiled alpha cut-out material (alpha > 0.5), point filter"""
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
    pb_.inputs['Metallic'].default_value = 0.0
    m['alpha_clip'] = 0.5
    m['metres_per_tile'] = tile
    try:
        m.surface_render_method = 'DITHERED'
    except AttributeError:
        pass
    return m


m_barb = cutout_mat('M_Kpp_Barbed', PB_BARB, 0.5)
for name, o in objs.items():
    a = K.ATLAS[name]
    if a in ('Kpp', 'KppYard', 'KppProps'):
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
    elif a == 'barbed':
        o.data.materials.append(m_barb)
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

# ------------------------------------------------------------------ 4b. the snow_kit instances (collections linked from the kit)
import kpp2_frame as KF
KC = KK.KIT_CONTRACT
with bpy.data.libraries.load(KIT_BLEND, link=True) as (src, dst):
    dst.collections = [c for c in src.collections if c in KC['items']]
kcoll = {c.name: c for c in dst.collections}
assert set(kcoll) == set(KC['items']), set(KC['items']) - set(kcoll)
inst_coll = bpy.data.collections.new('Kit_Instances')
bpy.context.scene.collection.children.link(inst_coll)
inst = {}
for name, ki in KK.KIT_INST.items():
    e = bpy.data.objects.new(name, None)
    inst_coll.objects.link(e)
    e.instance_type = 'COLLECTION'
    e.instance_collection = kcoll[ki['item']]
    e.empty_display_type, e.empty_display_size = 'PLAIN_AXES', 0.04
    e.matrix_world = ki['M']
    e['kit_item'] = ki['item']
    if ki['ids']:
        e['ix_ids'] = json.dumps(ki['ids'])
    e['note'] = ki['note']
    inst[name] = e
for name, ki in KK.KIT_INST.items():
    attach(inst[name], inst.get(ki['parent']) or objs[ki['parent']])
bpy.context.view_layer.update()
A_U = Matrix(((-1, 0, 0), (0, 0, 1), (0, -1, 0)))           # Blender -> Unity axes


def rot_unity(R3):
    q = (A_U @ R3 @ A_U.transposed()).to_quaternion()
    return [round(q.x, 6) + 0.0, round(q.y, 6) + 0.0, round(q.z, 6) + 0.0, round(q.w, 6) + 0.0]


def root_part(name):
    while name in KK.KIT_INST:
        name = KK.KIT_INST[name]['parent']
    while C['parts'][name].get('parent'):
        name = C['parts'][name]['parent']
    return name


def to_game(p, root):
    if root in ('Checkpoint', 'Barrier'):
        return [round(float(a), 3) + 0.0 for a in KF.booth_to_game(p)]
    if root == 'Gate':
        return [round(float(a), 3) + 0.0 for a in KF.gate_to_game(Vector(p) - KK.GATE_PLACE[0])]
    return None


KI = {}
for name, ki in KK.KIT_INST.items():
    e = inst[name]
    Ml = e.parent.matrix_world.inverted() @ e.matrix_world
    loc, rq, sca = Ml.decompose()
    lw, _, _ = e.matrix_world.decompose()
    rt = root_part(name)
    KI[name] = dict(item=ki['item'], parent=ki['parent'], root=rt, note=ki['note'], ix_ids=ki['ids'],
                    pos=r4(loc), rot_quat_wxyz=[round(a, 6) + 0.0 for a in rq], scale=r4(sca),
                    posUnity=to_unity(loc), rotUnity_xyzw=rot_unity(rq.to_matrix()), scaleUnity=r4((sca.x, sca.z, sca.y)),
                    pos_kpp=r4(lw), pos_game=to_game(lw, rt))
    pw = KK.KIT_CONTRACT['items'][ki['item']].get('power_parts') or []
    if pw:                                     # its lenses / screen light up only with the booth's power (group power)
        KI[name]['power'] = dict(group='power', parts=pw)
C['kit_instances'] = KI
INFO['kit_instances'] = {}
for v in KI.values():
    INFO['kit_instances'][v['item']] = INFO['kit_instances'].get(v['item'], 0) + 1
log('kit instances', len(KI), INFO['kit_instances'])


def ksock_world(name, sock, key=None):
    s = KC['sockets'][sock]
    M = inst[name].matrix_world
    if key:
        return (M.to_3x3() @ Vector(s[key])).normalized()
    return M @ Vector(s['pos'])


# the two cameras (the monitors show them): their view points as sockets of their roots
for cam, mon, root in (('Cam_Barrier', 'Monitor_Barrier', 'Checkpoint'), ('Cam_Gate', 'Monitor_Gate', 'Gate')):
    pos = ksock_world(cam, 'CAM_View')
    d = ksock_world(cam, 'CAM_View', 'dir')
    sname = 'CAM_' + cam.split('_')[1]
    C['sockets'][sname] = dict(pos=r4(pos), kind='camera', parent=root, dir=r4(d), monitor=mon, fov=55.0,
                               pos_game=to_game(pos, root),
                               note=f'{cam}\'s view: Unity puts the camera for {mon} here (render texture into its '
                                    f'Kit_Monitor_Screen, material M_Kit_Screen_On) while the booth has power')

# overhead wires (v2.1: kit models, instances Wire_Drop_* / Wire_Line_* placed by kpp_kit.wire_span): their ends and spans
wires = []
for name, item, (ia, sa), (ib, sb) in KK.WIRE_SPANS:
    a, b = ksock_world(ia, sa), ksock_world(ib, sb)
    span = (b - a).length
    hspan = (Vector((b.x, b.y)) - Vector((a.x, a.y))).length
    rule_sag = max(SKS.WIRE['sag_min'], SKS.WIRE['sag_k'] * hspan * hspan)
    wires.append(dict(instance=name, item=item, group='drop' if item == 'Kit_Wire_Drop' else 'line',
                      a=dict(instance=ia, socket=sa, pos=r4(a), pos_game=to_game(a, 'Checkpoint')),
                      b=dict(instance=ib, socket=sb, pos=r4(b), pos_game=to_game(b, 'Checkpoint')),
                      span=round(span, 3), scale_x=round(span / KC['parts'][item]['span'], 4),
                      sag_model=KC['parts'][item]['sag'], sag_rule=round(rule_sag, 3)))
onward = []
for ia, socks in (('Pole_2', ['Wire_1', 'Wire_2', 'Wire_3']), ('Pole_Gate', ['Wire_1', 'Wire_2', 'Wire_3'])):
    for sname in socks:
        p_ = ksock_world(ia, sname)
        onward.append(dict(instance=ia, socket=sname, pos=r4(p_), pos_game=to_game(p_, root_part(ia)),
                           toward='the base' if ia == 'Pole_2' else 'the KPP'))
C['wires'] = dict(rule=SKS.WIRE, spans=wires, onward=onward,
                  note='v2.1: the wires are kit models - the drop Wire_Drop_1..4 (Kit_Wire_Drop, black service cable) and the '
                       'line Wire_Line_1..3 (Kit_Wire_Bare) - instances in kit_instances, each turned from its socket a to b '
                       'and scaled in x (scale_x); the line goes on from Pole_2 toward the base and ends at Pole_Gate: Unity '
                       'places Kit_Pole about every 40 m along the road and a Kit_Wire_Bare between each pair of Wire_1..3 '
                       '(onward: the ends here), or builds the spans by the rule')
# trees off the new poles and the line (game frame; the vegetation bake keeps these clear like u7.keepClear)
kc = []
pg = {n: to_game(inst[n].matrix_world.translation, root_part(n)) for n in ('Pole_1', 'Pole_2', 'Pole_Gate', 'CamPole_Barrier',
                                                                           'CamPole_Gate')}
for n, r in (('Pole_1', 1.5), ('Pole_2', 2.0), ('Pole_Gate', 1.5), ('CamPole_Barrier', 1.0), ('CamPole_Gate', 1.0)):
    kc.append(dict(kind='circle', c=[pg[n][0], pg[n][2]], r=r, why=n))
kc.append(dict(kind='strip', a=[pg['Pole_1'][0], pg['Pole_1'][2]], b=[pg['Pole_2'][0], pg['Pole_2'][2]], r=2.5,
               why='under the line Pole_1 - Pole_2'))
C['keep_clear'] = kc
INFO['wires'] = len(wires)

# ------------------------------------------------------------------ 5. lamps: LIGHT_ empties + lights json
LMETA = GL.meta()
lens_of = {'Fluor': 'Lens_Fluor', 'Bulk_Door': 'Lens_Bulk_Door'}
glow_of = {'Fluor': 'Glow_Fluor', 'Bulk_Door': 'Glow_Bulk_Door'}
lamp_parent = {'Fluor': 'Lamp_Fluor', 'Bulk_Door': 'Checkpoint'}
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
    it = dict(socket='LIGHT_' + name, lens=lens_of[name], glow=glow_of.get(name, ''), parent=lamp_parent[name], type=typ,
              unityLight=T['unity'], position=r4(pos), forward=r4(d), up=r4(up), positionUnity=to_unity(pos),
              forwardUnity=to_unity(d), upUnity=to_unity(up), intensityURP=T['I'], peakCandela=T['cd'], kelvin=T['cct'],
              filterLinear=list(T['filt']), colorLinear=r4(GL.colour(typ)), range=T['rng'], group=T['group'],
              shadows=bool(T['shadows']), ies='IES/%s.ies' % typ, desc=T['desc'], startsOn=False)
    if typ in FLICKER:
        it['flicker'] = FLICKER[typ]
    items.append(it)
json.dump(dict(note='checkpoint lamps (v2). position / forward / up: booth frame (Checkpoint prefab: x toward the road, y toward the '
                    'back, z up, m); *Unity: (-x, z, -y) in the prefab. intensityURP at 100 %. group power = only with the booth\'s '
                    'power (the battery in the cabinet, both clamps on, the switch at BATTERIE): the fluorescent batten (flickers '
                    'a few seconds as it strikes; lens M_Kpp_Lamp_Fluor, glow Glow_Fluor with it) and the bulkhead over the door '
                    '(Glow_Bulk_Door shown, Lens_Bulk_Door -> M_Kpp_Lamp_Bulk). With the power the kit instances light too: the '
                    'monitors\' screens (M_Kit_Screen_On), the lamps (M_Kit_Lamp_*), the door lock\'s lamp, the cabinet\'s lamp; '
                    'the barrier\'s beacon (Kit_Beacon: its own light, snow_kit_lights.json) turns while the boom moves. Point '
                    'lights: the IES files describe the shape.',
               lights=items), open(os.path.join(OUT, 'kpp_lights.json'), 'w'), indent=1)
INFO['lamps'] = len(items)

# ------------------------------------------------------------------ 6. colliders
coll = bpy.data.collections.new('Colliders')
bpy.context.scene.collection.children.link(coll)
C['colliders'] = []
for name, par, (x0, x1, y0, y1, z0, z1), rot, local in KK.static_boxes():
    Pobj = objs[par]
    c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    size = Vector((x1 - x0, y1 - y0, z1 - z0))
    kb_ = K.KB()
    kb_.box(-size.x / 2, size.x / 2, -size.y / 2, size.y / 2, -size.z / 2, size.z / 2, 0)
    ob = kb_.to_object('COL_' + name, coll=coll)
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
    ent = dict(name='COL_' + name, parent=par, type='box', center=r4(lc), size=r4(size), center_kpp=r4(cw),
               centerUnity=to_unity(lc), sizeUnity=r4((size.x, size.z, size.y)))
    if rot:
        nz = [i for i, a in enumerate(rot) if a]
        assert len(nz) == 1, rot
        ent['rotation'] = [float(a) for a in rot]
        ru = [0.0, 0.0, 0.0]
        i = nz[0]
        if i == 0:
            ru[0] = float(rot[0])                       # about Blender +x -> about Unity +x, same sign
        elif i == 1:
            ru[2] = float(rot[1])                       # about Blender +y -> about Unity +z, same sign
        else:
            ru[1] = -float(rot[2])                      # about Blender +z -> about Unity +y, opposite sign
        ent['rotationUnity'] = ru
    C['colliders'].append(ent)
log('colliders', len(C['colliders']))

# ------------------------------------------------------------------ 7. knock points (rays onto the shell)
hide_for_rays = [o for o in bpy.data.objects if o.name.startswith(('COL_', 'Glow_')) and o.library is None]
for o in hide_for_rays:
    o.hide_viewport = True
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
nk = 0
for name, org, d in KK.knock_rays():
    hit, loc, nrm, idx, ob, mw = bpy.context.scene.ray_cast(dg, Vector(org), Vector(d), distance=5.0)
    if not hit:
        log('WARN knock ray missed', name)
        continue
    par = ob.name if ob.name in objs else 'Checkpoint'
    C['sockets'][name] = dict(pos=r4(loc + nrm * 0.005), kind='knock', parent=par, dir=r4(nrm),
                              note='something knocks / scratches here from outside (sound, frost-print decal)')
    nk += 1
for o in hide_for_rays:
    o.hide_viewport = False
INFO['knock_points'] = nk

# ------------------------------------------------------------------ 8. part boxes (grab / hit box of moving parts)
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
yaw_h = 2 * math.degrees(math.atan2(KPP_U['q'][1], KPP_U['q'][3]))


def unity_world(pos, yaw_local=0.0):
    """booth-frame point / yaw -> Forest (Unity) world position and rotation (y-up, left-handed)"""
    v = to_unity(pos)
    a = math.radians(yaw_h)
    x = v[0] * math.cos(a) + v[2] * math.sin(a)
    z = -v[0] * math.sin(a) + v[2] * math.cos(a)
    p = [round(KPP_U['p'][0] + x, 4), round(KPP_U['p'][1] + v[1], 4), round(KPP_U['p'][2] + z, 4)]
    yu = yaw_h - yaw_local
    h = math.radians(yu) / 2
    return dict(p=p, q=[0.0, round(math.sin(h), 6), 0.0, round(math.cos(h), 6)], yawUnity=round(yu, 3))


placement = {'Checkpoint': dict(p=list(KPP_U['p']), q=list(KPP_U['q']), yawUnity=round(yaw_h, 3))}
for root in ('Barrier', 'Gate'):
    placement[root] = unity_world(C['parts'][root]['pivot'], 0.0)
INFO['placement'] = placement


def yq(yaw):
    h = math.radians(yaw) / 2
    return [0.0, round(math.sin(h), 6), 0.0, round(math.cos(h), 6)]


game = {'Checkpoint': dict(p=to_game((0, 0, 0), 'Checkpoint'), q=yq(KF.BOOTH_YAW_GAME), yawUnity=round(KF.BOOTH_YAW_GAME, 4)),
        'Barrier': dict(p=to_game(KK.BARRIER_PLACE[0], 'Barrier'), q=yq(KF.BOOTH_YAW_GAME), yawUnity=round(KF.BOOTH_YAW_GAME, 4)),
        'Gate': dict(p=list(KF.GATE_GAME['p']), q=yq(KF.GATE_GAME['yaw']), yawUnity=KF.GATE_GAME['yaw'])}
C['meta'] = dict(version='2.0', units='metres, degrees',
                 frame='booth frame (the Checkpoint prefab\'s): x toward the road, y toward the back (the door, the station side), z '
                       'up; origin = the middle of the pad on the ground; floor z = 0.15; the road at the barrier and the gate is '
                       '0.38 lower',
                 unity='position (x, y, z) -> Unity (-x, z, -y) in the Checkpoint prefab; axis likewise; angle -> -angle (Unity is '
                       'left-handed); box centre likewise, box size (sx, sy, sz) -> (sx, sz, sy); a rotation R -> A R A^T, '
                       'A = the axis map (rotUnity_xyzw); a scale (sx, sy, sz) -> (sx, sz, sy)',
                 roots='three roots on the map, each its own prefab, with the booth\'s axes in this file (yaw 0 between them): '
                       'Checkpoint (the booth), Barrier (7 m out on the road), Gate (beside the booth here); and Barrier_Manual '
                       '(the v1 hand barrier, a prefab not on the map, 7 m further out here). Barrier and Gate parts and sockets '
                       'are given in the booth frame; map_placement: the Update 3 places (Forest_Layout.json); game_placement: '
                       'where they stand in the game now (ForestRelocation moves the booth and the barrier together, '
                       'ForestYardPlan leaves the gate at the yard, ~300 m away)',
                 map_placement=placement, game_placement=game,
                 kit='snow_kit instances (kit_instances): an empty per instance with the kit item\'s collection linked from '
                     '../snow_kit/snow_kit.blend; props kit_item, ix_ids (the IX_ parts of that instance get these numbers: '
                     'IX_ConsoleButton -> IX_ConsoleButton_312 ...); Unity: the builder puts the item\'s prefab (Assets/Kit/) on '
                     'the empty with its transform (the conduits are scaled in x); pos / rot / scale are in the parent\'s frame, '
                     'pos_kpp in this file\'s world, pos_game in the game',
                 colliders='colliders: BoxCollider per entry on its parent: center / size in the parent\'s own frame (Blender), '
                           'centerUnity / sizeUnity the same in Unity axes; rotation = Blender XYZ euler of the box (the roof sheet), '
                           'rotationUnity = Unity euler; center_kpp: the box centre in the booth frame. part.box: the grab / hit box '
                           'of a moving part in its own frame. The kit instances bring their own colliders (SNOW_KIT_CONTRACT.md)',
                 lamps='kpp_lights.json (+ the beacon in snow_kit_lights.json)', model='kpp.blend', textures='tex',
                 materials='M_Kpp_Kpp (the booth) / M_Kpp_KppYard (the barrier, the gate) / M_Kpp_KppProps: baked PSX atlases (point '
                           'filter); M_Kpp_Panel: signs, papers, labels, the clock, the radio; M_Kpp_Lamp_Fluor / _Off, '
                           'M_Kpp_Lamp_Bulk / _Off: lit / off; M_Kpp_Glow: additive halo; M_Kpp_Glass; M_Kpp_Barbed: alpha cut-out '
                           '0.5, tiled 0.5 m (Update 7\'s texture, one-sided). The kit instances use the kit\'s M_Kit_* materials',
                 prologue='S6 / X05 v2 (QUESTIONS_KPP.md «Решено»): no power at first; the players bring the van\'s Battery to '
                          'PowerCabinet (Slot_Battery), put both clamps on, turn IX_CabinetSwitch to BATTERIE: the door lock '
                          'releases IX_BoothDoor_74, the lamps light, the monitors show CAM_Barrier and CAM_Gate; Btn_Schranke '
                          'raises / lowers IX_BarrierArm_82, Btn_Tor sends IX_Gate_81 along (one press, it runs to the end). The '
                          'keys hang on the Key_Hook_ sockets (no Schranke), Note_KPPLog on Spot_KPPLog. X05: Phone / '
                          'Phone_Receiver (zone Phone_KPP) and Phone_Bell ring')
for o in bpy.data.objects:
    if o.name.startswith('COL_') and o.library is None:
        o.hide_set(True)
sfx = '_draft' if DRAFT else ''
json.dump(_nz(C), open(os.path.join(OUT, f'kpp_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
kinds = {}
for p in C['parts'].values():
    kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
INFO['contract'] = dict(parts=len(C['parts']), sockets=len(C['sockets']), colliders=len(C['colliders']), kinds=kinds)
log('contract', INFO['contract'])
for o in [o for o in bpy.data.objects if o.type == 'MESH' and o.library is None]:
    uvs = o.data.uv_layers
    if 'PSX' in uvs:
        for u in [u for u in uvs if u.name != 'PSX']:
            uvs.remove(u)
        uvs['PSX'].active = True
        uvs['PSX'].active_render = True
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith(('COL_', 'Preview_')) and o.library is None]
INFO['tris'] = sum(P.tri_count(o) for o in meshes)
INFO['tris_by_atlas'] = {}
for o in meshes:
    a = K.ATLAS.get(o.name, '?')
    INFO['tris_by_atlas'][a] = INFO['tris_by_atlas'].get(a, 0) + P.tri_count(o)
INFO['objects'] = sorted(o.name for o in meshes)
INFO['empties'] = sorted(o.name for o in bpy.data.objects if o.type == 'EMPTY' and o.library is None)
RTS = ('Barrier', 'Gate', 'Barrier_Manual')
booth = [o for o in meshes if not (o.name.startswith('Preview_') or o.name in RTS or (o.parent and o.parent.name in RTS) or
                                   (o.parent and o.parent.parent and o.parent.parent.name in RTS))]
lo_, hi_ = P.world_bbox(booth)
INFO['bbox_booth'] = [lo_.round(3).tolist(), hi_.round(3).tolist()]
log('tris', INFO['tris'], INFO['tris_by_atlas'], 'bbox (the booth)', INFO['bbox_booth'])
for lib in bpy.data.libraries:                       # the kit is linked as ../snow_kit/snow_kit.blend (the package layout)
    lib.filepath = '//../snow_kit/snow_kit.blend'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'kpp{sfx}.blend'), relative_remap=False)
json.dump(INFO, open(os.path.join(OUT, f'kpp{sfx}.json'), 'w'), indent=1)
log('saved kpp' + sfx)
