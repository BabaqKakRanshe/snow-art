"""Station yard build (yard_kit): the fuel tanks and the transformer, one object per part with its pivot as the origin, each
root its own prefab (FuelTanks at the scene origin, Trafo at its place beside it, turned -90 as on the map); PSX atlases baked
with psxbake + yard_paint at the generator shed's pixel density: Tanks (the bund, the tanks, the lines, the stile), Trafo
(the pad, the transformer, the pole, the cabinet, the fence's steel), YardProps (the pump, the valves, the extinguisher,
the small things); the panel atlas (yard_tex) on the signs, plates and dials; chain-link and barbed wire (alpha cut-out);
the interaction contract (parts, sockets, colliders, meta with the map placement of both roots), the hierarchy.
python3 -I yard_build.py [--draft]  -> out/yard.blend, out/yard.json, out/yard_contract.json, tex/yard/*
--draft: no bakes, flat zone colours (layout preview) -> out/yard_draft.blend"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import psxlib as P
import psxbake as PB
import yard_tex as YT
import gen_kit as K
import yard_kit as YK

DRAFT = '--draft' in sys.argv
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'yard')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
SHED_PPM = 51.3                                       # the generator shed's building atlas (px / m): the project's pixel
PB.POS_SCALE = 40.0                                   # bake range +-20 m: the pole's top stands 8.6 m up, the Trafo 13 m out
U3 = {'FuelTanks': dict(p=(403.0346, 16.3273, -342.6034), q=(0.0, -0.656059, 0.0, 0.75471)),       # Forest_Layout.json
      'Trafo': dict(p=(392.0185, 16.2829, -349.1338), q=(0.0, 0.069756, 0.0, 0.997564))}


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
    """root frame -> Unity (prefab-local): (x, y, z) -> (-x, z, -y)"""
    return [round(-float(v[0]), 4) + 0.0, round(float(v[2]), 4) + 0.0, round(-float(v[1]), 4) + 0.0]


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
PB_BASE, PB_EMI, PB_CHAIN, PB_BARB = YT.build(TEX)

# ------------------------------------------------------------------ 1. geometry, each root in its own frame
YK.build_yard()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts']]
assert not missing, f'objects without a contract entry: {missing}'
objs = {}
WELD = ('FuelTanks', 'Trafo', 'Pump', 'FuelTanks_Props', 'Trafo_Props', 'IX_PumpLever_301', 'IX_TrafoGate_91')
for name, k in K.KBS.items():
    if name in WELD:
        bmesh.ops.remove_doubles(k.bm, verts=list(k.bm.verts), dist=1e-4)
    p = C['parts'][name]
    objs[name] = k.to_object(name, pivot=Vector(p['pivot']))
log('objects', len(objs))
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

# ------------------------------------------------------------------ 2. colliders (root frames, before the Trafo moves)
coll = bpy.data.collections.new('Colliders')
bpy.context.scene.collection.children.link(coll)
C['colliders'] = []
for name, par, (x0, x1, y0, y1, z0, z1), rot, root in YK.static_boxes():
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
    C['colliders'].append(dict(name='COL_' + name, parent=par, root=root, type='box', center=r4(lc), size=r4(size),
                               center_root=r4(cw), centerUnity=to_unity(lc), sizeUnity=r4((size.x, size.z, size.y))))
log('colliders', len(C['colliders']))

# ------------------------------------------------------------------ 3. knock points (rays per root, the other one hidden)
meshes_of = {r: [o for o in objs.values() if C['parts'][o.name]['root'] == r] for r in YK.ROOTS}
nk = 0
for root in YK.ROOTS:
    hide = [o for o in bpy.data.objects if o.name.startswith(('COL_',)) or
            (o.name in objs and C['parts'][o.name]['root'] != root)]
    for o in hide:
        o.hide_viewport = True
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    for name, org, d, r_ in YK.knock_rays():
        if r_ != root:
            continue
        hit, loc, nrm, idx, ob, mw = bpy.context.scene.ray_cast(dg, Vector(org), Vector(d), distance=6.0)
        if not hit:
            log('WARN knock ray missed', name)
            continue
        par = ob.name if ob.name in objs else root
        C['sockets'][name] = dict(pos=r4(loc + nrm * 0.005), kind='knock', parent=par, root=root, dir=r4(nrm),
                                  note='something knocks / scratches here from outside (sound, frost-print decal)')
        nk += 1
    for o in hide:
        o.hide_viewport = False
INFO['knock_points'] = nk

# ------------------------------------------------------------------ 4. part boxes (grab / hit box of moving parts)
nb = 0
for k, p in C['parts'].items():
    o = objs.get(k)
    if o is None or p['kind'] == 'static':
        continue
    co = np.array([tuple(v.co) for v in o.data.vertices])
    lo, hi = co.min(0), co.max(0)
    p['box'] = dict(center=r4((lo + hi) / 2), size=r4(np.maximum(hi - lo, 0.004)))
    nb += 1
INFO['part_boxes'] = nb

# ------------------------------------------------------------------ 5. the Trafo to its place beside the tanks
tp, ty = YK.TRAFO_PLACE
objs['Trafo'].matrix_world = Matrix.Translation(tp) @ Matrix.Rotation(math.radians(ty), 4, 'Z')
bpy.context.view_layer.update()
groups = {}
for name, o in objs.items():
    groups.setdefault(K.ATLAS[name], []).append(o)

# ------------------------------------------------------------------ 6. atlases (or flat zone colours for the draft)
INFO['atlases'] = {}
import yard_paint as YP
if DRAFT:
    cache = {}

    def zmat(z):
        if z not in cache:
            m = bpy.data.materials.new(f'draft_{z}')
            m.use_nodes = True
            pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            c = PB.lin(*YP.DRAFT_COL.get(z, (128, 128, 128)))
            pb.inputs['Base Color'].default_value = (float(c[0]), float(c[1]), float(c[2]), 1)
            pb.inputs['Roughness'].default_value = 0.75
            cache[z] = m
        return cache[z]

    for name, o in objs.items():
        if K.ATLAS[name] not in ('Tanks', 'Trafo', 'YardProps'):
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
    prep = PB.prepare_atlas(groups['Tanks'], size=1024, angle=30, zone_scale={YK.Z_BUNDF: 0.6, YK.Z_PLINTH: 0.8}, ppm_cap=SHED_PPM,
                            margin_px=1.8, custom_uv=YK.tank_uvs)
    PB.finish_atlas('Tanks', groups['Tanks'], prep, YP.paint_tanks, TEX, prefix='T_Yard_', mat_prefix='M_Yard_', ao_min=0.35,
                    ao_dist=0.40, rough=0.85, log=log, info=INFO['atlases'], prio_zones=(YK.Z_SHELL, YK.Z_TANK))
    prep = PB.prepare_atlas(groups['Trafo'], size=1024, angle=40, ppm_cap=SHED_PPM, margin_px=1.8)
    PB.finish_atlas('Trafo', groups['Trafo'], prep, YP.paint_trafo, TEX, prefix='T_Yard_', mat_prefix='M_Yard_', ao_min=0.35,
                    ao_dist=0.40, rough=0.85, log=log, info=INFO['atlases'], prio_zones=(YK.Z_PORC, YK.Z_TRAFO))
    PB.make_atlas('YardProps', groups['YardProps'], YP.paint_props, TEX, prefix='T_Yard_', mat_prefix='M_Yard_', size=None, ppm=64.0,
                  ao_min=0.40, ao_dist=0.14, rough=0.75, log=log, info=INFO['atlases'], ppm_cap=64.0,
                  prio_zones=(YK.Z_PUMPB, YK.Z_EXT, YK.Z_WHEEL))

    def zone_ppm(objs_, size, zones):
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

    INFO['ppm_parts'] = {
        'tanks (shells, heads, saddles)': zone_ppm(groups['Tanks'], 1024, (YK.Z_SHELL, YK.Z_TANK, YK.Z_SADDLE)),
        'bund walls': zone_ppm(groups['Tanks'], 1024, (YK.Z_BUNDW,)),
        'bund floor': zone_ppm(groups['Tanks'], 1024, (YK.Z_BUNDF,)),
        'transformer': zone_ppm(groups['Trafo'], 1024, (YK.Z_TRAFO, YK.Z_FINS)),
        'pole': zone_ppm(groups['Trafo'], 1024, (YK.Z_POLE,)),
        'pad': zone_ppm(groups['Trafo'], 1024, (YK.Z_PAD,))}
    log('texel density by part', INFO['ppm_parts'])

# ------------------------------------------------------------------ 7. explicit materials
m_panel = PB.tex_mat('M_Yard_Panel', PB_BASE, PB_EMI, 0.0, rough=0.6)


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


m_chain = cutout_mat('M_Yard_ChainLink', PB_CHAIN, 0.5)
m_barb = cutout_mat('M_Yard_Barbed', PB_BARB, 0.5)
for name, o in objs.items():
    a = K.ATLAS[name]
    if a in ('Tanks', 'Trafo', 'YardProps'):
        continue
    o.data.materials.clear()
    if a == 'panel':
        o.data.materials.append(m_panel)
    elif a == 'chainlink':
        o.data.materials.append(m_chain)
    elif a == 'barbed':
        o.data.materials.append(m_barb)
    else:
        raise ValueError(a)

# ------------------------------------------------------------------ 8. meta, map placement, stats, save
placement = {}
for root in YK.ROOTS:
    u = U3[root]
    placement[root] = dict(p=list(u['p']), q=list(u['q']), yawUnity=round(2 * math.degrees(math.atan2(u['q'][1], u['q'][3])), 3))
INFO['placement'] = placement
C['meta'] = dict(units='metres, degrees',
                 frames='each root is its own prefab and has its own frame; a part / socket / collider gives its root. FuelTanks: '
                        'x along the tanks, y toward the back (-y = the yard side with the pump), z up, origin = the middle of '
                        'the bund on the ground (bund floor 0.15). Trafo: x along the gate side, y toward the back (the pole), z up, '
                        'origin = the middle of the pad on the ground (pad top 0.20)',
                 unity='position (x, y, z) -> Unity (-x, z, -y) in the root\'s prefab; axis likewise; angle -> -angle (Unity is '
                       'left-handed); box centre likewise, box size (sx, sy, sz) -> (sx, sz, sy)',
                 map_placement=placement,
                 blend='in yard.blend FuelTanks stands at the origin and Trafo at its place beside it (8, -10, -0.044 in the '
                       'FuelTanks frame, turned -90 deg), as on the map',
                 colliders='colliders: BoxCollider per entry on its parent: center / size in the parent\'s own frame (Blender), '
                           'centerUnity / sizeUnity the same in Unity axes; center_root: the box centre in its root\'s frame. '
                           'part.box: the grab / hit box of a moving part in its own frame',
                 model='yard.blend', textures='tex',
                 materials='M_Yard_Tanks (the bund, the tanks, the lines, the stile) / M_Yard_Trafo (pad, transformer, pole, cabinet, '
                           'fence steel) / M_Yard_YardProps (the pump, the valves, the extinguisher, small things): baked PSX '
                           'atlases (point filter); M_Yard_Panel: signs, plates, dials; M_Yard_ChainLink, M_Yard_Barbed: alpha '
                           'cut-out 0.5, tiled 0.5 m',
                 prologue='S7 (FOREST_OPENING.md): the day tank of the generator is empty; Jerrycan_Yard (Spot_Jerrycan) is filled at '
                          'the wing pump (IX_PumpLever_301, held: +0.5 L/s into a can within 0.45 m of Pump_Nozzle and at most 0.7 '
                          'm below it), carried to the generator container. The transformer gate IX_TrafoGate_91 is not locked')
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_set(True)
sfx = '_draft' if DRAFT else ''
json.dump(_nz(C), open(os.path.join(OUT, f'yard_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
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
INFO['tris_by_root'] = {}
for o in meshes:
    a = K.ATLAS.get(o.name, '?')
    INFO['tris_by_atlas'][a] = INFO['tris_by_atlas'].get(a, 0) + P.tri_count(o)
    r = C['parts'][o.name]['root']
    INFO['tris_by_root'][r] = INFO['tris_by_root'].get(r, 0) + P.tri_count(o)
INFO['objects'] = sorted(o.name for o in meshes)
log('tris', INFO['tris'], INFO['tris_by_atlas'], INFO['tris_by_root'])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'yard{sfx}.blend'))
json.dump(INFO, open(os.path.join(OUT, f'yard{sfx}.json'), 'w'), indent=1)
log('saved yard' + sfx)
