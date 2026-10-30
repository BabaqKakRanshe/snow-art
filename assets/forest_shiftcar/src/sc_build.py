"""forest_shiftcar build (adapted from the forest_plates build): one object per part with its pivot as the origin; the ShiftCar
atlas (1024, the shed's 51.3 px/m cap) baked with psxbake + sc_paint; the panel atlas (sc_tex) on the door lettering; the start
car's dirty glass; the contract (parts, the battery socket, colliders, meta). No lamps.
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- <abs path>/work/forest_shiftcar/sc_build.py [--draft]
-> out/sc.blend, out/sc.json, out/sc_contract.json, tex/sc/*"""
import sys, os, math, json, time
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import psxbake as PB
import psxlib as P
import sc_tex as YT
import gen_kit as K
import start_kit as STK
import sc_kit as SK

DRAFT = '--draft' in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex', 'sc')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
PB.POS_SCALE = 16.0                                  # bake range +-8 m: the car spans y -2.2 .. 2.4
SHED_PPM = 51.3


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


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
PB_BASE, PB_EMI = YT.build(TEX)

# ------------------------------------------------------------------ 1. geometry
SK.build_car()
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

# ------------------------------------------------------------------ 2. the ShiftCar atlas (or flat zone colours for the draft)
INFO['atlases'] = {}
import sc_paint as SPT
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
        if K.ATLAS[name] != 'ShiftCar':
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
    away = [o for n, o in objs.items() if K.ATLAS[n] != 'ShiftCar']    # the letters and the glass must not shade the paint
    for o in away:
        o.location.z += 100.0
    bpy.context.view_layer.update()
    PB.make_atlas('ShiftCar', groups['ShiftCar'], SPT.paint_car, TEX, prefix='T_SC_', mat_prefix='M_SC_', size=1024, ao_min=0.35,
                  ao_dist=0.40, rough=0.85, log=log, info=INFO['atlases'], ppm_cap=SHED_PPM,
                  zone_scale={STK.Z_UNDER: 0.6, STK.Z_LINER: 0.8, STK.Z_CARPET: 0.8},
                  prio_zones=(STK.Z_TAIL, STK.Z_HEAD, STK.Z_CHROME, STK.Z_PLATE))
    for o in away:
        o.location.z -= 100.0
    bpy.context.view_layer.update()

# ------------------------------------------------------------------ 3. explicit materials: the lettering, the glass
m_panel = PB.tex_mat('M_SC_Panel', PB_BASE, PB_EMI, 0.0, rough=0.6)
_nt = m_panel.node_tree                                 # cut-out letters: the image's alpha clips the quad
_pb = next(n for n in _nt.nodes if n.type == 'BSDF_PRINCIPLED')
_im = next(n for n in _nt.nodes if n.type == 'TEX_IMAGE' and n.image and os.path.basename(n.image.filepath) == os.path.basename(PB_BASE))
_nt.links.new(_im.outputs['Alpha'], _pb.inputs['Alpha'])
try:
    m_panel.surface_render_method = 'DITHERED'
except AttributeError:
    pass
m_glass = P.psx_glass('M_SC_GlassDirty', tint=(0.05, 0.055, 0.055), alpha=0.82)
for name, o in objs.items():
    a = K.ATLAS[name]
    if a == 'ShiftCar':
        continue
    o.data.materials.clear()
    if a == 'panel':
        o.data.materials.append(m_panel)
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
    p['root'] = SK.ROOT_OF.get(name, name)

# ------------------------------------------------------------------ 5. colliders (in each parent's own frame)
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
    ob.display_type = 'WIRE'
    ob.hide_render = True
    ob['collider'] = 'box'
    attach(ob, objs[par])
    lc = c - piv
    C['colliders'].append(dict(name='COL_' + name, parent=par, root=root, type='box', center=r4(lc), size=r4(size),
                               center_root=r4(c), centerUnity=to_unity(lc), sizeUnity=r4((size.x, size.z, size.y))))
log('colliders', len(C['colliders']))

# ------------------------------------------------------------------ 6. Unity values, meta, stats, save
for k, p in C['parts'].items():
    p['pivotUnity'] = to_unity(p['pivot'])
for k, s in C['sockets'].items():
    s['posUnity'] = to_unity(s['pos'])
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
INFO['panel_metres'] = {k: list(YT.size_m(k)) for k in YT.REG}
C['meta'] = dict(version='2.3', units='metres, degrees', built='locally with tools/snow_style (Blender 5.2.3), 28.10.2026',
                 frame='z up, the front -y; origin on the ground between the axles. FBX with the root at the origin',
                 placement='on the forest road before the checkpoint (ForestWorld.json, the old ShiftCar entry), broken down, the '
                           'hood up',
                 unity='position (x, y, z) -> Unity (-x, z, -y) in the prefab; box centre likewise, size (sx, sy, sz) -> (sx, sz, sy); '
                       'the root front (-y) is the prefab +Z',
                 colliders='BoxCollider per entry on its parent: center / size in the parent own frame. COL_ objects are reference '
                           'only, not in the FBX',
                 sockets='Slot_ShiftCar_Battery: the battery (VanItem_Battery_Net) stands on its tray in the engine bay, stowed; '
                         'the players take it to the checkpoint booth\'s power cabinet',
                 model='sc.blend', textures='tex',
                 materials='M_SC_ShiftCar: baked PSX atlas (point filter); M_SC_Panel: the door lettering (256 x 64 RGBA, alpha cut-out); '
                           'M_SC_GlassDirty: all windows (dark; a black shell behind, no interior)',
                 ix='none: doors and the hood are static')
sfx = '_draft' if DRAFT else ''
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_set(True)
json.dump(_nz(C), open(os.path.join(OUT, f'sc_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
INFO['contract'] = dict(parts=len(C['parts']), sockets=len(C['sockets']), colliders=len(C['colliders']))
log('contract', INFO['contract'], 'tris', tris, tris_root)
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    uvs = o.data.uv_layers
    if 'PSX' in uvs:
        for u in [u for u in uvs if u.name != 'PSX']:
            uvs.remove(u)
        uvs['PSX'].active = True
    if 'zone' in o.data.attributes and not DRAFT:
        o.data.attributes.remove(o.data.attributes['zone'])
json.dump(_nz(INFO), open(os.path.join(OUT, f'sc{sfx}.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'sc{sfx}.blend'))
log('saved', f'sc{sfx}.blend')
