"""forest_beer build (the smoke pack's smoke2_build, several roots): one object per part with its pivot as the origin, each
root in its own collection; the labels (explicit UVs) joined into their bodies as another material; the PSX atlas baked with
psxbake + beer_paint (Small: 512 px, capped at 512 px / m as the pager and the smoke pack); the label materials M_Beer_<Brand>;
the action 'Open' on each can's tab and flap (for the views; the game moves the parts in code); the contract.
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_beer/beer_build.py [--draft]
-> out/beer.blend, out/beer.json, out/beer_contract.json, tex/*; --draft: no bakes, flat zone colours"""
import sys, os, math, json, time
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
from PIL import Image
import psxbake as PB
import beer_tex as BT
import gen_kit as K
import beer_kit as SK

DRAFT = '--draft' in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
PB.POS_SCALE = 8.0                                    # bake range +-4 m (cans a few cm, laid out 0.45 x 0.13 m)
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
    """root frame -> Unity (prefab-local): (x, y, z) -> (-x, z, -y)"""
    return [round(-float(v[0]), 4) + 0.0, round(float(v[2]), 4) + 0.0, round(-float(v[1]), 4) + 0.0]


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
TP = BT.build(TEX)
black = os.path.join(TEX, 'T_Black.png')
Image.new('RGB', (4, 4), (0, 0, 0)).save(black)

# ------------------------------------------------------------------ 1. geometry
SK.build_all()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts'] and n not in SK.MERGE and n not in SK.ROOTS]
assert not missing, f'objects without a contract entry: {missing}'
colls = {}
for root in SK.ROOTS:
    colls[root] = bpy.data.collections.new(root)
    colls[root].instance_offset = SK.DISPLAY[root]
    bpy.context.scene.collection.children.link(colls[root])
objs = {}
for name, k in K.KBS.items():
    root = SK.ROOT_OF[name]
    off = SK.DISPLAY[root]
    K.transform_kb(k, Matrix.Translation(off))
    p = C['parts'].get(SK.MERGE.get(name, name), C['parts'].get(root))
    piv = Vector(p['pivot']) if SK.MERGE.get(name, name) in C['parts'] else Vector((0, 0, 0))
    o = k.to_object(name, coll=colls[root], pivot=piv + off)
    o['root'] = root
    objs[name] = o
# KB faces come with their own vertices: weld them, or every quad is its own island and the margins eat the atlas
for name, o in objs.items():
    if K.ATLAS[name] == 'Small':
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bm.to_mesh(o.data)
        bm.free()
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

# ------------------------------------------------------------------ 2. the Small atlas (or flat zone colours for the draft)
INFO['atlases'] = {}
import beer_paint as SP
if DRAFT:
    cache = {}

    def zmat(z):
        if z not in cache:
            m = bpy.data.materials.new(f'draft_{z}')
            m.use_nodes = True
            pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            c = PB.lin(*SP.DRAFT_COL.get(z, (128, 128, 128)))
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
    PB.make_atlas('Small', groups['Small'], SP.paint_small, TEX, prefix='T_Beer_', mat_prefix='M_Beer_', size=512,
                  ao_min=0.45, ao_dist=0.03, rough=0.55, log=log, info=INFO['atlases'], ppm_cap=SMALL_PPM)

# ------------------------------------------------------------------ 3. explicit materials
mats = {}
for b in BT.BRANDS:
    mats['label_' + b] = PB.tex_mat(f'M_Beer_{b}', TP[f'T_Beer_{b}'], black, 0.0, rough=0.45)
for name, o in objs.items():
    a = K.ATLAS[name]
    if a == 'Small':
        continue
    o.data.materials.clear()
    o.data.materials.append(mats[a])

# ------------------------------------------------------------------ 3b. the explicit-UV faces join their bodies
for name, dst in SK.MERGE.items():
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
log('merged', len(SK.MERGE), 'printed parts into their bodies')

# ------------------------------------------------------------------ 4. hierarchy (world transforms kept)
for name, p in C['parts'].items():
    if name in objs and p.get('parent') and p['parent'] in objs:
        attach(objs[name], objs[p['parent']])
    p['object'] = name if name in objs else None
    p['root'] = SK.ROOT_OF.get(name, name)
    if name in SK.MASS:
        p['mass_kg'] = SK.MASS[name]
for s in C['sockets'].values():
    s['root'] = s.get('parent')

# ------------------------------------------------------------------ 4b. the opening as an action per can (24 fps)
KEYS = [(1, 0.0, 0.0), (5, 22.0, 0.0), (10, SK.OPEN['tab_max'], SK.OPEN['flap']), (16, SK.OPEN['tab_rest'], SK.OPEN['flap'])]
bpy.context.scene.render.fps = 24
bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 16
for b in BT.BRANDS:
    for nm, col in (('Can_Tab_' + b, 1), ('Can_Flap_' + b, 2)):
        o = objs[nm]
        o.rotation_mode = 'XYZ'
        base = o.rotation_euler.copy()
        for f, tab, flap in KEYS:
            o.rotation_euler = (base.x + math.radians(tab if col == 1 else flap), base.y, base.z)
            o.keyframe_insert('rotation_euler', index=0, frame=f)
        o.rotation_euler = base
        o.animation_data.action.name = 'Open_' + nm
bpy.context.scene.frame_set(1)
INFO['open_keys'] = dict(fps=24, frames=[k[0] for k in KEYS], tab_deg=[k[1] for k in KEYS], flap_deg=[k[2] for k in KEYS])

# ------------------------------------------------------------------ 5. colliders (in each root's frame)
coll_c = bpy.data.collections.new('Colliders')
bpy.context.scene.collection.children.link(coll_c)
C['colliders'] = []
for name, root, (x0, x1, y0, y1, z0, z1), rot in SK.BOXES:
    off = SK.DISPLAY[root]
    c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    size = Vector((x1 - x0, y1 - y0, z1 - z0))
    kb_ = K.KB()
    kb_.box(-size.x / 2, size.x / 2, -size.y / 2, size.y / 2, -size.z / 2, size.z / 2, 0)
    ob = kb_.to_object('COL_' + name, coll=coll_c)
    ob.location = c + off
    ob.display_type = 'WIRE'
    ob.hide_render = True
    attach(ob, objs[root])
    C['colliders'].append(dict(name='COL_' + name, parent=root, root=root, type='box', center=r4(c), size=r4(size),
                               centerUnity=to_unity(c), sizeUnity=r4((size.x, size.z, size.y))))

# ------------------------------------------------------------------ 6. part boxes, Unity values, meta, stats, save
for k, p in C['parts'].items():
    o = objs.get(k)
    if o is None or p['kind'] == 'static':
        continue
    co = np.array([tuple(v.co) for v in o.data.vertices])
    lo, hi = co.min(0), co.max(0)
    p['box'] = dict(center=r4((lo + hi) / 2), size=r4(np.maximum(hi - lo, 0.004)))
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
    if o.type != 'MESH' or o.name.startswith('COL_'):
        continue
    t = sum(len(pl.vertices) - 2 for pl in o.data.polygons)
    tris += t
    tris_root[o.get('root', '?')] = tris_root.get(o.get('root', '?'), 0) + t
INFO['tris'] = tris
INFO['tris_by_root'] = tris_root
INFO['objects'] = {r: sorted(o.name for o in colls[r].objects) for r in SK.ROOTS}
INFO['display_offset'] = {r: r4(SK.DISPLAY[r]) for r in SK.ROOTS}
INFO['mass_kg'] = SK.MASS
C['meta'] = dict(version='1.1', units='metres, degrees, kg',
                 frame='each root in its own frame: z up, the label front -y; origin on the bottom under the middle; FBX per '
                       'root at the origin',
                 unity='position (x, y, z) -> Unity (-x, z, -y); axis likewise; angle -> -angle; box size (sx, sy, sz) -> (sx, sz, sy)',
                 materials='M_Beer_Small: the baked PSX atlas (point filter) of the steel, rims, lids, tabs, the inside; '
                           'M_Beer_<Brand>: the printed label (512 wide once round, unwrapped from concept_v1/cans_1.png, '
                           'Kalo from concept_v2/kalo_front_1.png)',
                 opening='tab 0 -> 70 deg while the flap goes 0 -> 82 (frames 1-10 at 24 fps), the tab back to 12 (frame 16); '
                         'the action Open_<part> in the file is for the views, the game drives the hinges itself',
                 brands={b: dict(name=BT.NAME[b], litres=BT.LITRES[b], abv=BT.ABV[b]) for b in BT.BRANDS},
                 model='beer.blend', textures='tex')
sfx = '_draft' if DRAFT else ''
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_set(True)
json.dump(_nz(C), open(os.path.join(OUT, f'beer_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
log('contract', len(C['parts']), 'parts', len(C['sockets']), 'sockets', 'tris', tris, tris_root)
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    uvs = o.data.uv_layers
    if 'PSX' in uvs:
        for u in [u for u in uvs if u.name != 'PSX']:
            uvs.remove(u)
        uvs['PSX'].active = True
    if 'zone' in o.data.attributes and not DRAFT:
        o.data.attributes.remove(o.data.attributes['zone'])
json.dump(_nz(INFO), open(os.path.join(OUT, f'beer{sfx}.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'beer{sfx}.blend'), relative_remap=False)
log('saved', f'beer{sfx}.blend')
