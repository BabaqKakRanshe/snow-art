"""forest_pager build (adapted from forest_gear's gear_build): one object per part with its pivot as the origin, the root in its
own collection; the printed faces (panel atlas) joined into the body as another material; the PSX atlas baked with psxbake +
pager_paint: Small (128 px at 512 px/m, as forest_gear's hand things); explicit materials: the panel, the LED red / off, the
LCD lit / off; the interaction contract (parts, sockets, colliders, mass, meta).
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_pager/pager_build.py [--draft]
-> out/pager.blend, out/pager.json, out/pager_contract.json, tex/pager/*; --draft: no bakes, flat zone colours"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import psxlib as P
import psxbake as PB
import pager_tex as GT
import gen_kit as K
import pager_kit as GK

DRAFT = '--draft' in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex', 'pager')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
PB.POS_SCALE = 8.0                                    # bake range +-4 m (the pager is 8 cm)
SMALL_PPM = 512.0


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
TP = GT.build(TEX)

# ------------------------------------------------------------------ 1. geometry
GK.build_all()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts'] and n not in GK.MERGE]
assert not missing, f'objects without a contract entry: {missing}'
colls = {}
for root in GK.ROOTS:
    colls[root] = bpy.data.collections.new(root)
    colls[root].instance_offset = GK.DISPLAY[root]            # linked as a collection instance, the root lands on the empty
    bpy.context.scene.collection.children.link(colls[root])
objs = {}
for name, k in K.KBS.items():
    root = GK.ROOT_OF[name]
    off = GK.DISPLAY[root]
    K.transform_kb(k, Matrix.Translation(off))
    p = C['parts'][GK.MERGE.get(name, name)]
    o = k.to_object(name, coll=colls[root], pivot=Vector(p['pivot']) + off)
    o['root'] = root
    objs[name] = o
log('objects', len(objs))
bpy.context.view_layer.update()


def attach(child, parent):
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    child.matrix_world = mw


groups = {}
for name, o in objs.items():
    groups.setdefault(K.ATLAS[name], []).append(o)

# ------------------------------------------------------------------ 2. atlases (or flat zone colours for the draft)
INFO['atlases'] = {}
import pager_paint as GPT
if DRAFT:
    cache = {}

    def zmat(z):
        if z not in cache:
            m = bpy.data.materials.new(f'draft_{z}')
            m.use_nodes = True
            pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            c = PB.lin(*GPT.DRAFT_COL.get(z, (128, 128, 128)))
            pb.inputs['Base Color'].default_value = (float(c[0]), float(c[1]), float(c[2]), 1)
            pb.inputs['Roughness'].default_value = 0.75
            m.diffuse_color = (float(c[0]), float(c[1]), float(c[2]), 1)
            cache[z] = m
        return cache[z]

    for name, o in objs.items():
        if K.ATLAS[name] != 'Small':
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
    PB.make_atlas('Small', groups['Small'], GPT.paint_small, TEX, prefix='T_Pager_', mat_prefix='M_Pager_', size=128,
                  ao_min=0.45, ao_dist=0.03, rough=0.55, log=log, info=INFO['atlases'], ppm_cap=SMALL_PPM,
                  prio_zones=(GK.Z_PG_RUB,))

# ------------------------------------------------------------------ 3. explicit materials
m_panel = PB.tex_mat('M_Pager_Panel', TP['Panel_BaseColor'], TP['Panel_Emission'], 0.0, rough=0.6)


def flat_mat(name, rgb, emi=None, strength=0.0, rough=0.3, fake=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    c = PB.lin(*rgb)
    pb.inputs['Base Color'].default_value = (float(c[0]), float(c[1]), float(c[2]), 1.0)
    pb.inputs['Roughness'].default_value = rough
    if emi is not None:
        e = PB.lin(*emi)
        pb.inputs['Emission Color'].default_value = (float(e[0]), float(e[1]), float(e[2]), 1.0)
        pb.inputs['Emission Strength'].default_value = strength
    m.diffuse_color = (float(c[0]), float(c[1]), float(c[2]), 1.0)
    m.use_fake_user = fake
    return m


m_led_off = flat_mat('M_Pager_LED_Off', (40, 30, 28), rough=0.25)
flat_mat('M_Pager_LEDR', (120, 30, 24), (255, 60, 40), 2.0, 0.25, fake=True)
m_lcd = PB.tex_mat('M_Pager_LCD', TP['LCD_BaseColor'], TP['LCD_Emission'], 1.0, rough=0.3)
next(n for n in m_lcd.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Emission Strength'].default_value = 1.0
m_lcd_off = PB.tex_mat('M_Pager_LCD_Off', TP['LCD_BaseColor'], TP['LCD_Emission'], 0.0, rough=0.3)
next(n for n in m_lcd_off.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Emission Strength'].default_value = 0.0
m_lcd_off.use_fake_user = True
for name, o in objs.items():
    a = K.ATLAS[name]
    if a == 'Small':
        continue
    o.data.materials.clear()
    if a == 'panel':
        o.data.materials.append(m_panel)
    elif a == 'led':
        o.data.materials.append(m_led_off)
    elif a == 'lcd':
        o.data.materials.append(m_lcd)
    else:
        raise ValueError(a)

# ------------------------------------------------------------------ 3b. the explicit-UV faces join their bodies
for name, dst in GK.MERGE.items():
    src, tgt = objs.pop(name), objs[dst]
    me = src.data.copy()
    me.transform(tgt.matrix_world.inverted() @ src.matrix_world)
    mat = src.data.materials[0]
    names = [mm.name for mm in tgt.data.materials]
    if mat.name not in names:
        tgt.data.materials.append(mat)
        names.append(mat.name)
    for pl in me.polygons:
        pl.material_index = names.index(mat.name)
    bm = bmesh.new()
    bm.from_mesh(tgt.data)
    bm.from_mesh(me)
    bm.to_mesh(tgt.data)
    bm.free()
    old = src.data
    bpy.data.objects.remove(src)
    bpy.data.meshes.remove(old)
    bpy.data.meshes.remove(me)
log('merged', len(GK.MERGE), 'faces into their bodies')

# ------------------------------------------------------------------ 4. hierarchy (world transforms kept)
for name, p in C['parts'].items():
    if name in objs and p.get('parent') and p['parent'] in objs:
        attach(objs[name], objs[p['parent']])
    p['object'] = name if name in objs else None
    p['root'] = GK.ROOT_OF.get(name, name)
    if name in GK.MASS:
        p['mass_kg'] = GK.MASS[name]


def root_of_part(name):
    while C['parts'][name].get('parent'):
        name = C['parts'][name]['parent']
    return name


for s in C['sockets'].values():
    s['root'] = root_of_part(s['parent']) if s.get('parent') in C['parts'] else s.get('parent')

# ------------------------------------------------------------------ 5. colliders (in each parent's own frame)
coll_c = bpy.data.collections.new('Colliders')
bpy.context.scene.collection.children.link(coll_c)
C['colliders'] = []
for name, par, (x0, x1, y0, y1, z0, z1), rot in GK.BOXES:
    root = GK.ROOT_OF[par]
    off = GK.DISPLAY[root]
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

# ------------------------------------------------------------------ 6. part boxes (grab / hit box of moving parts and items)
for k, p in C['parts'].items():
    o = objs.get(k)
    if o is None or p['kind'] == 'static':
        continue
    co = np.array([tuple(v.co) for v in o.data.vertices])
    lo, hi = co.min(0), co.max(0)
    p['box'] = dict(center=r4((lo + hi) / 2), size=r4(np.maximum(hi - lo, 0.002)))

# ------------------------------------------------------------------ 7. Unity values, meta, stats, save
for k, p in C['parts'].items():
    p['pivotUnity'] = to_unity(p['pivot'])
    if p.get('axis'):
        p['axisUnity'] = to_unity(p['axis'])
for s in C['sockets'].values():
    s['posUnity'] = to_unity(s['pos'])
    for key in ('dir', 'up', 'forward'):
        if s.get(key):
            s[key + 'Unity'] = to_unity(s[key])
tris, tris_root = 0, {}
for o in bpy.data.objects:
    if o.type != 'MESH' or o.name.startswith('COL_') or o.library is not None:
        continue
    t = sum(len(pl.vertices) - 2 for pl in o.data.polygons)
    tris += t
    tris_root[o.get('root', '?')] = tris_root.get(o.get('root', '?'), 0) + t
INFO['tris'] = tris
INFO['tris_by_root'] = tris_root
INFO['objects'] = {r: sorted(o.name for o in colls[r].objects) for r in GK.ROOTS}
INFO['display_offset'] = {r: r4(GK.DISPLAY[r]) for r in GK.ROOTS}
INFO['mass_kg'] = GK.MASS
INFO['asset_tag'] = GT.ASSET_TAG
INFO['lcd'] = dict(cols=GT.LCD_COLS, rows=GT.LCD_ROWS, px=list(GT.LCD_PX))
C['meta'] = dict(version='1.0', units='metres, degrees, kg',
                 frame='the root in its own frame: z up, the front (LCD, keys) -y; origin on the surface it stands on (z = 0) '
                       'under its middle. Every pivot / pos here is in the root\'s frame; FBX with the root at the origin',
                 unity='position (x, y, z) -> Unity (-x, z, -y) in the prefab; axis likewise; angle -> -angle (Unity is left-handed); '
                       'box centre likewise, size (sx, sy, sz) -> (sx, sz, sy); the root\'s front (-y) is the prefab\'s +Z',
                 colliders='BoxCollider per entry on its parent: center / size in the parent\'s own frame, centerUnity / sizeUnity '
                           'the same in Unity axes. The COL_ objects are in the .blend for reference (collection Colliders), not in '
                           'the FBX',
                 mass='mass_kg on the root: a suggestion for the rigidbody',
                 model='pager.blend', textures='tex',
                 materials='M_Pager_Small: the baked PSX atlas (point filter) of the body, keys, switch, clip; M_Pager_Panel: the '
                           'printed faces (the front with the bezel, key signs and maker line, the side\'s inventory sticker, the '
                           'top\'s BEEP / VIB) - another material on the body; M_Pager_LCD / M_Pager_LCD_Off: the screen lit (green '
                           'backlight, a sample list) / off - lit in the file; own texture, UV 0..1, the game replaces it with its '
                           'list; M_Pager_LEDR / M_Pager_LED_Off: the message LED (off in the file)',
                 names='the root is Item_Pager as forest_items\' / forest_gear\'s items; parts and sockets start with Pager_')
sfx = '_draft' if DRAFT else ''
for o in bpy.data.objects:
    if o.name.startswith('COL_') and o.library is None:
        o.hide_set(True)
json.dump(_nz(C), open(os.path.join(OUT, f'pager_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
kinds = {}
for p in C['parts'].values():
    kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
INFO['contract'] = dict(parts=len(C['parts']), sockets=len(C['sockets']), colliders=len(C['colliders']), kinds=kinds)
log('contract', INFO['contract'], 'tris', tris, tris_root)
for o in [o for o in bpy.data.objects if o.type == 'MESH' and o.library is None]:
    uvs = o.data.uv_layers
    if 'PSX' in uvs:
        for u in [u for u in uvs if u.name != 'PSX']:
            uvs.remove(u)
        uvs['PSX'].active = True
    if 'zone' in o.data.attributes and not DRAFT:
        o.data.attributes.remove(o.data.attributes['zone'])
json.dump(_nz(INFO), open(os.path.join(OUT, f'pager{sfx}.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'pager{sfx}.blend'), relative_remap=False)
log('saved', f'pager{sfx}.blend')
