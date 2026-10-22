"""Generator shed build: gen_kit / gen_set / gen_room geometry -> one object per part with its pivot as the origin,
PSX atlases (Shed, Genset, Props, Snow) baked with psxbake + gen_paint, the pixel-art panel atlas (gen_tex) on the
explicit-UV objects (panel faces, dials, signs, stencils, lamp lenses), glass, needles; the lamp json (gen_lights),
the interaction contract (parts, sockets, colliders, meta), the hierarchy, snow blend shapes.
python3 -I gen_build.py   -> out/gen.blend, out/gen.json, out/gen_contract.json, out/gen_lights.json, tex/gen/*"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import psxlib as P
import psxbake as PB
import gen_tex as GT
import gen_lights as GL
import gen_kit as K
import gen_set as GS
import gen_room as GR
import gen_paint as GP

HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'gen')
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
PB_BASE, PB_EMI = GT.build(TEX)
INFO['ies'] = GL.write_ies_all(os.path.join(TEX, 'IES'))
INFO['cookies'] = GL.write_cookies(os.path.join(TEX, 'Cookies'), os.path.join(TEX, 'cookies_sheet.png'))

# ------------------------------------------------------------------ 1. geometry
K.build_shed()
GS.build_genset()
GR.build_room()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts']]
assert not missing, f'objects without a contract entry: {missing}'
# belt sanity: every belt point outside every pulley
import van3_mech as VM
belt = VM._belt_path(GS.BELT_X, GS.BELT, n=6)
worst = min(math.hypot(p.y - y, p.z - z) - r for p in belt for (y, z, r) in GS.BELT)
INFO['belt_clearance_m'] = round(worst, 4)
log('belt: min distance outside the pulleys', round(worst, 4))
objs = {}
for name, k in K.KBS.items():
    if name.startswith('Snow_'):                       # one continuous sheet: weld the grid so it unwraps as big islands
        bmesh.ops.remove_doubles(k.bm, verts=list(k.bm.verts), dist=1e-4)
    piv = Vector(C['parts'][name]['pivot'])
    objs[name] = k.to_object(name, pivot=piv)
log('objects', len(objs))

# ------------------------------------------------------------------ 2. baked atlases
groups = {}
for name, o in objs.items():
    groups.setdefault(K.ATLAS[name], []).append(o)
INFO['atlases'] = {}
PB.make_atlas('Shed', groups['Shed'], GP.paint_shed, TEX, size=1024, ao_min=0.35, ao_dist=0.40, rough=0.85, log=log,
              info=INFO['atlases'], prio_zones=(K.Z_ENAMEL, K.Z_INSUL))
PB.make_atlas('Genset', groups['Genset'], GP.paint_genset, TEX, size=512, ao_min=0.35, ao_dist=0.14, rough=0.7, log=log,
              info=INFO['atlases'], prio_zones=(K.Z_RED2, K.Z_YEL2, K.Z_FANB, K.Z_WIRER, K.Z_GLASSB, K.Z_COPPER, K.Z_CHROME2))
PB.make_atlas('Props', groups['Props'], GP.paint_props, TEX, size=512, ao_min=0.40, ao_dist=0.14, rough=0.75, log=log,
              info=INFO['atlases'], prio_zones=(K.Z_DRUMB, K.Z_REDH, K.Z_EXT, K.Z_OILCAN, K.Z_JUG, K.Z_PALLET, K.Z_CABLER,
                                                K.Z_COPPERP, K.Z_BRASSP))
PB.make_atlas('Snow', groups['Snow'], GP.paint_snow, TEX, size=256, ao_min=0.80, ao_dist=0.12, rough=0.9, ncol=24, log=log,
              info=INFO['atlases'])

# ------------------------------------------------------------------ 3. explicit materials
m_panel = PB.tex_mat('M_Gen_Panel', PB_BASE, PB_EMI, 0.0, rough=0.5)
LENS = {'amber': 3.0, 'red': 3.0, 'green': 3.0, 'white': 3.0, 'bulk': 4.0, 'ext': 5.0}
lens_mats = {}
for kname, night in LENS.items():
    m = PB.tex_mat('M_Gen_Lamp_' + kname.capitalize(), PB_BASE, PB_EMI, night, rough=0.25)
    m['lamp_kind'] = kname
    lens_mats[kname] = m
m_glass = P.psx_glass('M_Gen_Glass')
m_needle = bpy.data.materials.new('M_Gen_Needle')
m_needle.use_nodes = True
_pb = next(n for n in m_needle.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
_pb.inputs['Base Color'].default_value = (0.95, 0.30, 0.06, 1)
_pb.inputs['Emission Color'].default_value = (1.0, 0.35, 0.08, 1)
_pb.inputs['Emission Strength'].default_value = 0.0
m_needle['night_emit'] = 0.0
m_diesel = bpy.data.materials.new('M_Gen_Diesel')
m_diesel.use_nodes = True
_pb = next(n for n in m_diesel.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
_pb.inputs['Base Color'].default_value = (0.62, 0.40, 0.06, 1)
_pb.inputs['Roughness'].default_value = 0.2
for name, o in objs.items():
    a = K.ATLAS[name]
    if a in ('Shed', 'Genset', 'Props', 'Snow'):
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

# ------------------------------------------------------------------ 4. hierarchy (world transforms kept)
bpy.context.view_layer.update()


def attach(child, parent):
    bpy.context.view_layer.update()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


for name, p in C['parts'].items():
    if name in objs and p.get('parent') and p['parent'] in objs:
        attach(objs[name], objs[p['parent']])
    p['object'] = name if name in objs else None

# ------------------------------------------------------------------ 5. lamps: LIGHT_ empties + lights json
LMETA = GL.meta()
lens_of = {'Bulk_Ceiling': 'Lens_Bulk_Ceiling', 'Bulk_Board': 'Lens_Bulk_Board', 'Ext_Door': 'Lens_Ext_Door'}
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
    attach(e, objs['Shed'])
INFO['lamps'] = GL.lights_json(os.path.join(OUT, 'gen_lights.json'), K.LAMPS, lens_of,
                               'generator shed lamps. position / forward / up: shed frame (x east, y north, z up, m); '
                               '*Unity: (-y, z, x). intensityURP at 100 %. group: shed = SHED circuit (Board_MCB_8) and '
                               'Light_Switch, outd = OUTDOOR LIGHTS (Board_MCB_2); both need the busbar live (the set '
                               'running with GEN selected, or LINE). lens: the glowing object to light up with the lamp.')

# ------------------------------------------------------------------ 6. colliders
coll = bpy.data.collections.new('Colliders')
bpy.context.scene.collection.children.link(coll)
C['colliders'] = []
for name, par, (x0, x1, y0, y1, z0, z1), rot in GR.static_boxes():
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

# ------------------------------------------------------------------ 7. knock points (rays onto the shell)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
hide_for_rays = [o for o in bpy.data.objects if o.name.startswith(('COL_', 'Snow_'))]
for o in hide_for_rays:
    o.hide_viewport = True
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
nk = 0
for name, org, d in GR.knock_rays():
    hit, loc, nrm, idx, ob, mw = bpy.context.scene.ray_cast(dg, Vector(org), Vector(d), distance=5.0)
    if not hit:
        log('WARN knock ray missed', name)
        continue
    par = ob.name if ob.name in objs else 'Shed'
    C['sockets'][name] = dict(pos=r4(loc + nrm * 0.005), kind='knock', parent=par, dir=r4(nrm),
                              note='something knocks / scratches here from outside (sound, frost-print decal)')
    nk += 1
for o in hide_for_rays:
    o.hide_viewport = False
INFO['knock_points'] = nk

# ------------------------------------------------------------------ 8. part boxes, removable flags, stretch rests
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

# ------------------------------------------------------------------ 9. snow blend shapes (Clear = no snow), hidden by default
for name in ('Snow_Roof', 'Snow_DoorDrift'):
    o = objs[name]
    o.shape_key_add(name='Basis', from_mix=False)
    sk = o.shape_key_add(name='Clear', from_mix=False)
    sk.value = 0.0                                     # 0 = full snow as modelled; the game drives Clear 0..100
    M = o.matrix_world
    Mi = M.inverted()
    for i, v in enumerate(o.data.vertices):
        w = M @ v.co
        zc = (K.z_st(w.y) - 0.015) if name == 'Snow_Roof' else -0.01      # Clear 100: sunk into the roof sheet / the ground
        sk.data[i].co = Mi @ Vector((w.x, w.y, min(w.z, zc)))

# ------------------------------------------------------------------ 10. meta, stats, save
C['meta'] = dict(units='metres, degrees', frame='shed frame: x east (the louvre end), y north, z up; ground z = 0 at the slab '
                 'edge, floor z = 0.10; origin = the middle of the slab',
                 unity='position (x, y, z) -> Unity (-y, z, x); axis likewise; angle -> -angle (Unity is left-handed); box '
                       'centre likewise, box size (sx, sy, sz) -> (sy, sz, sx)',
                 colliders='colliders: BoxCollider per entry on its parent (centre / size in the parent frame); rotation = '
                           'Blender XYZ euler of the box (only the two roof slopes), rotationUnity = Unity euler; part.box: '
                           'the grab / hit box of a moving part in its own frame',
                 blendshapes='Snow_Roof, Snow_DoorDrift: Clear (100 = no snow)', lamps='out/gen_lights.json',
                 model='out/gen.blend', textures='tex/gen', links='links.from / ratio: the part follows another part')
for k, p in C['parts'].items():
    if p.get('default') == 'hidden' and k in objs:
        objs[k].hide_render = True
        objs[k].hide_set(True)
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_set(True)
json.dump(_nz(C), open(os.path.join(OUT, 'gen_contract.json'), 'w'), indent=1, ensure_ascii=False)
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
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'gen.blend'))
json.dump(INFO, open(os.path.join(OUT, 'gen.json'), 'w'), indent=1)
log('saved gen')
