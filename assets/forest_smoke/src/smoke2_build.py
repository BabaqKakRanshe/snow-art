"""forest_smoke 2.0 build (the pager's pager_build, several roots): one object per part with its pivot as the origin, each
root in its own collection; the printed faces (panels) joined into their bodies as another material; the PSX atlas
baked with psxbake + smoke2_paint (Small: 256 px at 512 px / m, as the pager and forest_gear's hand things);
explicit materials: the three pack prints (2000 px / m), the lighter's label, the flame, the brand filter, the ember;
the interaction contract (parts, sockets, colliders, mass, meta).
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_smoke/smoke2_build.py [--draft]
-> out/smoke.blend, out/smoke.json, out/smoke_contract.json, tex2/*; --draft: no bakes, flat zone colours"""
import sys, os, math, json, time
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
from PIL import Image
import psxbake as PB
import smoke2_tex as ST
import gen_kit as K
import smoke2_kit as SK

DRAFT = '--draft' in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex2')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
PB.POS_SCALE = 8.0                                    # bake range +-4 m (the things are a few cm, laid out 0.33 m wide)
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
TP = ST.build(TEX)
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
import smoke2_paint as SP
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
    PB.make_atlas('Small', groups['Small'], SP.paint_small, TEX, prefix='T_Smoke_', mat_prefix='M_Smoke_', size=256,
                  ao_min=0.45, ao_dist=0.03, rough=0.55, log=log, info=INFO['atlases'], ppm_cap=SMALL_PPM)

# ------------------------------------------------------------------ 3. explicit materials
mats = {}
for b in ST.BRANDS:
    mats['panel_' + b] = PB.tex_mat(f'M_CigPack_{b}', TP[f'T_CigPack_{b}'], black, 0.0, rough=0.6)
mats['lpanel'] = PB.tex_mat('M_Lighter_Panel', TP['T_Lighter_Panel_BaseColor'], black, 0.0, rough=0.5)
mats['flame'] = PB.tex_mat('M_Lighter_Flame', TP['T_Lighter_Panel_BaseColor'], TP['T_Lighter_Panel_Emission'], 2.0, rough=0.5)
next(n for n in mats['flame'].node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Emission Strength'].default_value = 2.0
mats['filter'] = PB.tex_mat('M_Cig_Filter', TP['T_Cig_Filter_Harzgold'], black, 0.0, rough=0.7)
for b in ST.BRANDS[1:]:
    m = PB.tex_mat(f'M_Cig_Filter_{b}', TP[f'T_Cig_Filter_{b}'], black, 0.0, rough=0.7)
    m.use_fake_user = True                                                   # the game swaps the filter by brand
mats['ember'] = PB.tex_mat('M_Cig_Ember', TP['T_Cig_Ember'], TP['T_Cig_Ember'], 1.5, rough=0.8)
next(n for n in mats['ember'].node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Emission Strength'].default_value = 1.5
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
C['meta'] = dict(version='2.0', units='metres, degrees, kg',
                 frame='each root in its own frame: z up, the front -y; origin on the surface it stands on under its middle '
                       '(the cigarette: its mouth end, lying along -y); FBX per root at the origin',
                 unity='position (x, y, z) -> Unity (-x, z, -y); axis likewise; angle -> -angle; box size (sx, sy, sz) -> (sx, sz, sy)',
                 materials='M_Smoke_Small: the baked PSX atlas (point filter) of the bodies, edges, foil, the lighter, the paper, the '
                           'ash; M_CigPack_<Brand>: the printed pack faces (2000 px / m); M_Lighter_Panel: the BLITZ label; '
                           'M_Lighter_Flame: the flame (emissive, hidden until lit); M_Cig_Filter (Harzgold in the file) and '
                           'M_Cig_Filter_Brocken / _Nordlicht: the filter per brand; M_Cig_Ember: the glow (the game drives it)',
                 model='smoke.blend', textures='tex')
sfx = '_draft' if DRAFT else ''
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_set(True)
json.dump(_nz(C), open(os.path.join(OUT, f'smoke_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
log('contract', len(C['parts']), 'parts', len(C['sockets']), 'sockets', 'tris', tris, tris_root)
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    uvs = o.data.uv_layers
    if 'PSX' in uvs:
        for u in [u for u in uvs if u.name != 'PSX']:
            uvs.remove(u)
        uvs['PSX'].active = True
    if 'zone' in o.data.attributes and not DRAFT:
        o.data.attributes.remove(o.data.attributes['zone'])
json.dump(_nz(INFO), open(os.path.join(OUT, f'smoke{sfx}.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'smoke{sfx}.blend'), relative_remap=False)
log('saved', f'smoke{sfx}.blend')
