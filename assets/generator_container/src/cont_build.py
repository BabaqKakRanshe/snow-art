"""Generator container build: the generator shed's interior (gen_set, gen_room: built in the shed frame, then moved
group by group) inside the twin container (cont_kit) -> one object per part with its pivot as the origin; PSX atlases:
Cont - the whole building, outside and in (the inside finished as the shed's), one atlas as the shed's, with the
shed's AO settings - baked with psxbake + cont_paint, Genset and Props prepared in the shed frame (the
shed painters keep their coordinates) and finished in the container (AO from the real surroundings), Snow; the panel
atlas (cont_tex) on the explicit-UV objects, glass, needles; the lamp json, the interaction contract (parts, sockets,
colliders, meta), the hierarchy, snow blend shapes.
python3 -I cont_build.py [--draft]  -> out/cont.blend, out/cont.json, out/cont_contract.json, out/cont_lights.json, tex/cont/*
--draft: no bakes, flat zone colours (layout preview) -> out/cont_draft.blend"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import psxlib as P
import psxbake as PB
import cont_tex as CT                    # patches gen_tex first: circuit 8 = CONTAINER, umlauts, the sign regions
import gen_tex as GT
import gen_lights as GL
import gen_kit as K
import gen_set as GS
import gen_room as GR
import cont_kit as CK
import gen_paint as GP

DRAFT = '--draft' in sys.argv
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'cont')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}


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


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
PB_BASE, PB_EMI = CT.build(TEX)
GL.TYPES['bulkhead'].update(group='room', desc='caged bulkhead, 60 W incandescent behind a frosted dome; CONTAINER circuit '
                            '(Board_MCB_8) and Light_Switch; the cage throws six soft spokes (cookie)')
GL.TYPES['barnlight'].update(desc='barn light over the doors, 100 W under a deep enamel shade; OUTDOOR LIGHTS circuit (Board_MCB_2)')
if not DRAFT:
    INFO['ies'] = GL.write_ies_all(os.path.join(TEX, 'IES'))
    INFO['cookies'] = GL.write_cookies(os.path.join(TEX, 'Cookies'), os.path.join(TEX, 'cookies_sheet.png'))

# ------------------------------------------------------------------ 1. geometry: the shed's interior, then the container
GR.FUEL_ROUTES = CK.fuel_routes_shed()
K.kb('Shed', 'Cont')                                   # gen_room hangs the logbook nail on the shed mesh: catch it
GS.build_genset()
GR.switchboard()
GR.day_tank()
GR.drums()
GR.pump()
GR.shelf_and_props()
C = K.CONTRACT
interior = [n for n in K.KBS if n != 'Shed']
shift = {n: CK.group_of(C, n) for n in interior}
sock_shift = {n: CK.group_of(C, n) for n in C['sockets']}
nail = K.KBS.pop('Shed')
K.ATLAS.pop('Shed')
for d in list(C['parts'].values()) + list(C['sockets'].values()):
    if d.get('parent') == 'Shed':
        d['parent'] = 'GenContainer'
CK.build_container()
K.merge_kb(K.KBS['GenContainer_In'], nail, Matrix.Translation(CK.NAIL_GROUP))
missing = [n for n in K.KBS if n not in C['parts']]
assert not missing, f'objects without a contract entry: {missing}'
log('interior objects', len(interior), 'container objects', len(K.KBS) - len(interior))
objs = {}
WELD = ('GenContainer', 'GenContainer_In', 'Door_R', 'Door_L')   # corrugated sheets: one island per wall, not per strip
for name, k in K.KBS.items():
    if name.startswith('Snow_') or name in WELD:       # continuous sheets: weld so they unwrap as big islands
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
# ------------------------------------------------------------------ 3. move the interior into the container
for name in interior:
    objs[name].location += shift[name]
    C['parts'][name]['pivot'] = r4(Vector(C['parts'][name]['pivot']) + shift[name])
for n, off in sock_shift.items():
    C['sockets'][n]['pos'] = r4(Vector(C['sockets'][n]['pos']) + off)
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 4. atlases (or flat zone colours for the draft)
DRAFT_COL = {   # sRGB, roughly the painters' base colours
    CK.Z_CPAINT_S: (62, 92, 116), CK.Z_CPAINT_N: (70, 96, 108), CK.Z_CROOF: (88, 104, 112), CK.Z_CCAST: (50, 66, 80),
    CK.Z_CINPAINT: (150, 154, 150), K.Z_FLOOR: (116, 113, 106), K.Z_LINING: (178, 150, 108), K.Z_ROOFUNDER: (118, 120, 116),
    K.Z_TRIMW: (212, 208, 194), CK.Z_UNDER: (30, 28, 26), CK.Z_SEAL: (20, 20, 20), K.Z_SLAB: (132, 130, 124),
    K.Z_TIMBER: (150, 118, 78), K.Z_DOORIN: (146, 118, 82), K.Z_STEELBLK: (36, 36, 36), K.Z_GALV: (150, 154, 152),
    K.Z_RUSTPIPE: (104, 58, 34), K.Z_CHEQUER: (124, 124, 120), K.Z_INSUL: (222, 220, 212), K.Z_WIRE: (22, 22, 22),
    K.Z_ENAMEL: (36, 70, 50), K.Z_ENAMEL_IN: (232, 230, 222), K.Z_SNOW: (236, 240, 248),
    K.Z_GPAINT: (70, 102, 66), K.Z_ALT: (70, 102, 66), K.Z_GIRON: (60, 60, 58), K.Z_SKID: (32, 32, 32), K.Z_EXH: (110, 64, 40),
    K.Z_ALU2: (106, 108, 102), K.Z_RAD: (30, 32, 32), K.Z_RADT: (34, 34, 32), K.Z_FANB: (222, 150, 30), K.Z_HOSE2: (28, 28, 28),
    K.Z_BELT: (24, 24, 24), K.Z_STEEL3: (168, 170, 168), K.Z_COPPER: (186, 110, 64), K.Z_BRASS2: (186, 148, 70),
    K.Z_GLASSB: (206, 150, 40), K.Z_BATTC: (42, 44, 46), K.Z_LEAD2: (112, 114, 116), K.Z_WIRER: (152, 30, 24),
    K.Z_WIRERB: (20, 20, 20), K.Z_YEL2: (222, 182, 40), K.Z_RED2: (184, 30, 24), K.Z_PANELBOX: (56, 60, 58),
    K.Z_RUBBERM: (36, 34, 32), K.Z_CANVAS2: (132, 120, 88), K.Z_FILTERC: (204, 200, 184), K.Z_AIRF: (30, 30, 30),
    K.Z_BLACK2: (24, 24, 24), K.Z_CHROME2: (196, 198, 200),
    K.Z_CAB: (194, 196, 190), K.Z_CABIN: (150, 152, 148), K.Z_BRK: (26, 26, 26), K.Z_MCB: (210, 208, 198), K.Z_TOGGLE: (18, 18, 18),
    K.Z_REDH: (190, 30, 24), K.Z_TANKP: (102, 114, 100), K.Z_DRUMB: (38, 70, 122), K.Z_DRUMR: (164, 36, 26),
    K.Z_DRUMTOP: (38, 70, 122), K.Z_PALLET: (222, 182, 32), K.Z_PUMP: (150, 34, 24), K.Z_HOSEP: (30, 30, 30),
    K.Z_STEELP: (160, 162, 158), K.Z_BRASSP: (190, 150, 70), K.Z_WOOD: (156, 124, 82), K.Z_OILCAN: (36, 76, 150),
    K.Z_JUG: (222, 222, 212), K.Z_BOXC: (172, 142, 98), K.Z_TOOLBOX: (176, 30, 24), K.Z_RAG: (120, 104, 84),
    K.Z_CABLEJ: (184, 112, 60), K.Z_EXT: (200, 30, 26), K.Z_MAT: (32, 32, 32), K.Z_HARDB: (112, 82, 56),
    K.Z_COPPERP: (182, 106, 62), K.Z_CABLER: (156, 30, 24), K.Z_CABLEB: (20, 20, 20)}
INFO['atlases'] = {}
if DRAFT:
    cache = {}

    def zmat(z):
        if z not in cache:
            m = bpy.data.materials.new(f'draft_{z}')
            m.use_nodes = True
            pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            c = PB.lin(*DRAFT_COL.get(z, (128, 128, 128)))
            pb.inputs['Base Color'].default_value = (float(c[0]), float(c[1]), float(c[2]), 1)
            pb.inputs['Roughness'].default_value = 0.75
            cache[z] = m
        return cache[z]

    for name, o in objs.items():
        if K.ATLAS[name] not in ('Cont', 'Genset', 'Props', 'Snow'):
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
    import cont_paint as CPT
    PB.make_atlas('Cont', groups['Cont'], CPT.paint_cont_all, TEX, prefix='T_GCont_', mat_prefix='M_GCont_', size=1024,
                  ao_min=0.35, ao_dist=0.40, rough=0.85, log=log, info=INFO['atlases'],
                  prio_zones=(K.Z_ENAMEL, K.Z_INSUL, K.Z_RUSTPIPE), zone_scale={CK.Z_UNDER: 0.3, CK.Z_CROOF: 0.65})
    PB.finish_atlas('Genset', groups['Genset'], prep['Genset'], GP.paint_genset, TEX, prefix='T_GCont_', mat_prefix='M_GCont_',
                    ao_min=0.35, ao_dist=0.14, rough=0.7, log=log, info=INFO['atlases'],
                    prio_zones=(K.Z_RED2, K.Z_YEL2, K.Z_FANB, K.Z_WIRER, K.Z_GLASSB, K.Z_COPPER, K.Z_CHROME2))
    PB.finish_atlas('Props', groups['Props'], prep['Props'], GP.paint_props, TEX, prefix='T_GCont_', mat_prefix='M_GCont_',
                    ao_min=0.40, ao_dist=0.14, rough=0.75, log=log, info=INFO['atlases'],
                    prio_zones=(K.Z_DRUMB, K.Z_REDH, K.Z_EXT, K.Z_OILCAN, K.Z_JUG, K.Z_PALLET, K.Z_CABLER, K.Z_COPPERP, K.Z_BRASSP))
    PB.make_atlas('Snow', groups['Snow'], GP.paint_snow, TEX, prefix='T_GCont_', mat_prefix='M_GCont_', size=256, ao_min=0.80,
                  ao_dist=0.12, rough=0.9, ncol=24, log=log, info=INFO['atlases'])

    def zone_ppm(objs_, size, zones):
        """texel density (px / m) of the faces in `zones` on an atlas"""
        a3 = a2 = 0.0
        for o in objs_:
            me, M = o.data, o.matrix_world
            uv, za = me.uv_layers['PSX'], me.attributes['zone']
            for p in me.polygons:
                if round(za.data[p.index].value) not in zones:
                    continue
                vs = [M @ me.vertices[i].co for i in p.vertices]
                us = [uv.data[li].uv for li in p.loop_indices]
                for i in range(1, len(vs) - 1):
                    a3 += (vs[i] - vs[0]).cross(vs[i + 1] - vs[0]).length / 2
                    e1, e2 = us[i] - us[0], us[i + 1] - us[0]
                    a2 += abs(e1.x * e2.y - e1.y * e2.x) / 2
        return round(size * math.sqrt(a2 / a3), 1) if a3 else None

    INFO['atlases']['Cont']['ppm_parts'] = {
        'walls outside': zone_ppm(groups['Cont'], 1024, (CK.Z_CPAINT_S, CK.Z_CPAINT_N)),
        'inside (ply, floor, timber, roof underside)': zone_ppm(groups['Cont'], 1024, (K.Z_LINING, K.Z_FLOOR, K.Z_TIMBER, K.Z_ROOFUNDER)),
        'roofs on top': zone_ppm(groups['Cont'], 1024, (CK.Z_CROOF,)), 'underside': zone_ppm(groups['Cont'], 1024, (CK.Z_UNDER,))}
    log('Cont texel density by part', INFO['atlases']['Cont']['ppm_parts'])

# ------------------------------------------------------------------ 5. explicit materials
m_panel = PB.tex_mat('M_GCont_Panel', PB_BASE, PB_EMI, 0.0, rough=0.5)
LENS = {'amber': 3.0, 'red': 3.0, 'green': 3.0, 'white': 3.0, 'bulk': 4.0, 'ext': 5.0}
lens_mats = {}
for kname, night in LENS.items():
    m = PB.tex_mat('M_GCont_Lamp_' + kname.capitalize(), PB_BASE, PB_EMI, night, rough=0.25)
    m['lamp_kind'] = kname
    lens_mats[kname] = m
m_glass = P.psx_glass('M_GCont_Glass')
m_needle = bpy.data.materials.new('M_GCont_Needle')
m_needle.use_nodes = True
_pb = next(n for n in m_needle.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
_pb.inputs['Base Color'].default_value = (0.95, 0.30, 0.06, 1)
_pb.inputs['Emission Color'].default_value = (1.0, 0.35, 0.08, 1)
_pb.inputs['Emission Strength'].default_value = 0.0
m_needle['night_emit'] = 0.0
m_diesel = bpy.data.materials.new('M_GCont_Diesel')
m_diesel.use_nodes = True
_pb = next(n for n in m_diesel.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
_pb.inputs['Base Color'].default_value = (0.62, 0.40, 0.06, 1)
_pb.inputs['Roughness'].default_value = 0.2
for name, o in objs.items():
    a = K.ATLAS[name]
    if a in ('Cont', 'Genset', 'Props', 'Snow'):
        continue
    o.data.materials.clear()
    if a == 'panel':
        o.data.materials.append(m_panel)
    elif a.startswith('lens:'):
        o.data.materials.append(lens_mats[a[5:]])
        o['lamp_kind'] = a[5:]
    elif a == 'glass':
        o.data.materials.append(m_glass)
    elif a == 'needle':
        o.data.materials.append(m_needle)
    elif a == 'diesel':
        o.data.materials.append(m_diesel)
    else:
        raise ValueError(a)

# ------------------------------------------------------------------ 6. hierarchy (world transforms kept)
bpy.context.view_layer.update()


def attach(child, parent):
    bpy.context.view_layer.update()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


for name, p in C['parts'].items():
    if name in objs and p.get('parent') and p['parent'] in objs:
        attach(objs[name], objs[p['parent']])
    p['object'] = name if name in objs else None

# ------------------------------------------------------------------ 7. lamps: LIGHT_ empties + lights json
LMETA = GL.meta()
lens_of = {n: 'Lens_' + n for n, *_ in K.LAMPS}
for name, pos, d, typ, up in K.LAMPS:
    e = bpy.data.objects.new('LIGHT_' + name, None)
    bpy.context.scene.collection.objects.link(e)
    e.empty_display_type, e.empty_display_size = 'SINGLE_ARROW', 0.12
    dv = Vector(d).normalized()
    uv_ = Vector(up)
    uv_ = (uv_ - dv * uv_.dot(dv)).normalized()
    xv_ = uv_.cross(dv)                                  # empty: +Z = beam, +Y = the json 'up' (Unity light frame)
    e.matrix_world = Matrix.Translation(Vector(pos)) @ Matrix((xv_, uv_, dv)).transposed().to_4x4()
    e['type'], e['group'], e['dir'], e['up'], e['color'] = typ, LMETA[typ]['group'], list(dv), list(up), LMETA[typ]['color']
    e['intensity_urp'] = GL.TYPES[typ]['I']
    e['lens'] = lens_of[name]
    attach(e, objs['GenContainer'])
INFO['lamps'] = GL.lights_json(os.path.join(OUT, 'cont_lights.json'), K.LAMPS, lens_of,
                               'generator container lamps. position / forward / up: container frame (x east, y north, z up, m); '
                               '*Unity: (-y, z, x). intensityURP at 100 %. group: room = CONTAINER circuit (Board_MCB_8) and '
                               'Light_Switch, outd = OUTDOOR LIGHTS (Board_MCB_2); both need the busbar live (the set running '
                               'with GEN selected, or LINE). lens: the glowing object to light up with the lamp.')

# ------------------------------------------------------------------ 8. colliders: the shell + the moved interior
coll = bpy.data.collections.new('Colliders')
bpy.context.scene.collection.children.link(coll)
C['colliders'] = []
INNER = ('Genset_', 'Switchboard', 'Board_Door', 'DayTank', 'Pallet', 'Shelf', 'Drum_')
boxes = CK.static_boxes_shell()
for name, par, b, rot in GR.static_boxes():
    if name.startswith(INNER):
        o_ = shift[par]
        boxes.append((name, par, (b[0] + o_.x, b[1] + o_.x, b[2] + o_.y, b[3] + o_.y, b[4] + o_.z, b[5] + o_.z), rot))
for name, par, (x0, x1, y0, y1, z0, z1), rot in boxes:
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
    lc = Pobj.matrix_world.inverted() @ c
    ent = dict(name='COL_' + name, parent=par, type='box', center=r4(lc), size=r4(size), center_body=r4(c),
               parent_origin=r4(Pobj.matrix_world.translation))
    if rot:
        ent['rotation'] = [float(a) for a in rot]
        ent['rotationUnity'] = [0.0, 0.0, -float(rot[0])]
    C['colliders'].append(ent)
log('colliders', len(C['colliders']))

# ------------------------------------------------------------------ 9. knock points (rays onto the shell)
hide_for_rays = [o for o in bpy.data.objects if o.name.startswith(('COL_', 'Snow_'))]
for o in hide_for_rays:
    o.hide_viewport = True
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
nk = 0
for name, org, d in CK.knock_rays():
    hit, loc, nrm, idx, ob, mw = bpy.context.scene.ray_cast(dg, Vector(org), Vector(d), distance=5.0)
    if not hit:
        log('WARN knock ray missed', name)
        continue
    par = ob.name if ob.name in objs else 'GenContainer'
    C['sockets'][name] = dict(pos=r4(loc + nrm * 0.005), kind='knock', parent=par, dir=r4(nrm),
                              note='something knocks / scratches here from outside (sound, frost-print decal)')
    nk += 1
for o in hide_for_rays:
    o.hide_viewport = False
INFO['knock_points'] = nk

# ------------------------------------------------------------------ 10. part boxes, removable flags, stretch rests
nb = 0
for k, p in C['parts'].items():
    o = objs.get(k)
    if o is None or p['kind'] == 'static' or k.startswith(('Needle_', 'Lens_', 'GLamp_', 'BLamp_')):
        continue
    co = np.array([tuple(v.co) for v in o.data.vertices])
    lo, hi = co.min(0), co.max(0)
    p['box'] = dict(center=r4((lo + hi) / 2), size=r4(np.maximum(hi - lo, 0.004)))
    nb += 1
for k, p in C['parts'].items():
    if p['kind'] == 'twist' and 'removable' not in p:
        p['removable'] = 'end' if k.endswith(('_Cap', 'Lid')) else False
    if p['kind'] == 'stretch':
        p['rest'] = 1.0
INFO['part_boxes'] = nb

# ------------------------------------------------------------------ 11. snow blend shapes (Clear = no snow), hidden by default
for name in ('Snow_Roof', 'Snow_DoorDrift'):
    o = objs[name]
    o.shape_key_add(name='Basis', from_mix=False)
    sk = o.shape_key_add(name='Clear', from_mix=False)
    sk.value = 0.0                                     # 0 = full snow as modelled; the game drives Clear 0..100
    M = o.matrix_world
    Mi = M.inverted()
    for i, v in enumerate(o.data.vertices):
        w = M @ v.co
        zc = (CK.ROOF_Z - 0.01) if name == 'Snow_Roof' else -0.01        # Clear 100: under the roof panels / the ground
        sk.data[i].co = Mi @ Vector((w.x, w.y, min(w.z, zc)))

# the drift: the lowest Clear at which the leaves' bottom edge (z 0.275) clears the snow everywhere in their swing
o = objs['Snow_DoorDrift']
zmax = 0.0
for v in o.data.vertices:
    w = o.matrix_world @ v.co
    for (px, py), L_ in (((-3.015, -2.455), 1.24), ((-3.015, -0.004), 1.23)):
        if w.x < -3.0 and math.hypot(w.x - px, w.y - py) < L_ + 0.02:
            zmax = max(zmax, w.z)
clear_min = int(math.ceil(100 * (zmax - CK.LEAF['z0']) / (zmax + 0.01))) if zmax > CK.LEAF['z0'] else 0
C['parts']['Snow_DoorDrift']['note'] = C['parts']['Snow_DoorDrift']['note'].replace('from Clear 61', f'from Clear {clear_min}')
INFO['drift'] = dict(max_height_in_swing=round(zmax, 3), clear_min=clear_min)
json.dump(INFO['drift'], open(os.path.join(OUT, 'cont_drift.json'), 'w'))
log('drift', INFO['drift'])

# ------------------------------------------------------------------ 12. meta, stats, save
C['meta'] = dict(units='metres, degrees', frame='container frame: x east (the radiator louvre end), y north, z up; ground z = 0 '
                 'under the pads, floor z = 0.31; origin = the middle of the twin footprint',
                 unity='position (x, y, z) -> Unity (-y, z, x); axis likewise; angle -> -angle (Unity is left-handed); box '
                       'centre likewise, box size (sx, sy, sz) -> (sy, sz, sx)',
                 colliders='colliders: BoxCollider per entry on its parent (centre / size in the parent frame); part.box: '
                           'the grab / hit box of a moving part in its own frame',
                 blendshapes='Snow_Roof, Snow_DoorDrift: Clear (100 = no snow)', lamps='cont_lights.json',
                 model='cont.blend', textures='tex', links='links.from / ratio: the part follows another part',
                 origin_of_interior='the genset, switchboard, day tank, drums, pump, shelf and the props are the generator '
                                    'shed\'s (gen_set / gen_room), moved in unchanged')
for k, p in C['parts'].items():
    if p.get('default') == 'hidden' and k in objs:
        objs[k].hide_render = True
        objs[k].hide_set(True)
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_set(True)
sfx = '_draft' if DRAFT else ''
json.dump(_nz(C), open(os.path.join(OUT, f'cont_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
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
lo_, hi_ = P.world_bbox([o for o in meshes if not o.name.startswith('Snow_')])
INFO['bbox'] = [lo_.round(3).tolist(), hi_.round(3).tolist()]
log('tris', INFO['tris'], INFO['tris_by_atlas'], 'bbox', INFO['bbox'])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'cont{sfx}.blend'))
json.dump(INFO, open(os.path.join(OUT, f'cont{sfx}.json'), 'w'), indent=1)
log('saved cont' + sfx)
