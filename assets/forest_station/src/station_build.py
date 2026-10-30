"""forest_station build (adapted from forest_pager's pager_build / forest_devices' devices_build): one object per root with
its pivot as the origin, each root in its own collection and standing at station_kit.DISPLAY in the file (the contract gives
everything in the root's own frame); the sockets as empties (Slot_*) under their roots; one PSX atlas baked with psxbake +
station_paint: Props (class prop: 64 px/m, the posts at 2x for the punched holes, AO 0.40 / 0.16); the contract (parts,
sockets, colliders, meta).
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_station/station_build.py [--draft]
-> out/station.blend, out/station.json, out/station_contract.json, out/station_lights.json, tex/station/*; --draft: no
bakes, flat zone colours"""
import sys, os, math, json, time
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import psxlib as P
import psxbake as PB
import gen_kit as K
import station_kit as SK

DRAFT = '--draft' in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex', 'station')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
PB.POS_SCALE = 8.0                                    # bake range +-4 m
PROP_PPM = 64.0                                       # snow_style class 'prop' (= snow_kit's Kit atlas: the monitors)
POST_SCALE = 2.0                                      # the posts' faces (seen up close, the hole row) at 2x


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

# ------------------------------------------------------------------ 1. geometry
SK.build_all()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts']]
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
    p = C['parts'][name]
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


def zone_area(objs_, zones):
    a = 0.0
    for o in objs_:
        za = o.data.attributes['zone'].data
        for pl in o.data.polygons:
            if int(round(za[pl.index].value)) in zones:
                a += pl.area
    return a


groups = {}
for name, o in objs.items():
    groups.setdefault(K.ATLAS[name], []).append(o)

# ------------------------------------------------------------------ 2. the atlas (or flat zone colours for the draft)
INFO['atlases'] = {}
import station_paint as SPT
A_all = sum(pl.area for o in groups['Props'] for pl in o.data.polygons)
A_post = zone_area(groups['Props'], {SK.Z_POST})
# the cap counts the whole UV area: with the posts at 2x (4x area) the cap that keeps the rest at 64 px/m is higher
cap = PROP_PPM * math.sqrt((A_all + (POST_SCALE ** 2 - 1) * A_post) / A_all)
INFO['density_plan'] = dict(area_m2=round(A_all, 3), post_area_m2=round(A_post, 3), base_ppm=PROP_PPM,
                            post_ppm=PROP_PPM * POST_SCALE, cap_used=round(cap, 2))
log('density plan', INFO['density_plan'])
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
    PB.make_atlas('Props', groups['Props'], SPT.paint_props, TEX, prefix='T_Station_', mat_prefix='M_Station_', size=None,
                  ppm=cap, ao_min=0.40, ao_dist=0.16, rough=0.75, log=log, info=INFO['atlases'], ppm_cap=cap,
                  zone_scale={SK.Z_POST: POST_SCALE}, prio_zones=(SK.Z_FOOT, SK.Z_TFOOT))
    a = INFO['atlases']['Props']
    a['ppm_base'] = round(a['ppm'] * math.sqrt(A_all / (A_all + (POST_SCALE ** 2 - 1) * A_post)), 1)
    a['ppm_posts'] = round(a['ppm_base'] * POST_SCALE, 1)
    log('ATLAS Props real density: base', a['ppm_base'], 'posts', a['ppm_posts'])

# ------------------------------------------------------------------ 3. the sockets as empties under their roots
for name, s in C['sockets'].items():
    par = s['parent']
    root = SK.ROOT_OF[par]
    e = bpy.data.objects.new(name, None)
    colls[root].objects.link(e)
    e.empty_display_type, e.empty_display_size = 'ARROWS', 0.06
    # every socket here faces the root's front (-y) with z up = the root's own axes: the empty is not rotated
    assert tuple(s.get('dir') or (0, -1, 0)) == (0.0, -1.0, 0.0), name
    e.matrix_world = Matrix.Translation(Vector(s['pos']) + SK.DISPLAY[root])
    e['socket_kind'] = s['kind']
    if s.get('item'):
        e['item'] = s['item']
    e['note'] = s['note']
    e['root'] = root
    attach(e, objs[par])
    s['root'] = root
    s['object'] = name
log('socket empties', len(C['sockets']))

# ------------------------------------------------------------------ 4. parts
for name, p in C['parts'].items():
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
for s in C['sockets'].values():
    s['posUnity'] = to_unity(s['pos'])
    for key in ('dir', 'up'):
        if s.get(key):
            s[key + 'Unity'] = to_unity(s[key])
tris, tris_root, size_root = 0, {}, {}
for o in bpy.data.objects:
    if o.type != 'MESH' or o.name.startswith('COL_') or o.library is not None:
        continue
    t = sum(len(pl.vertices) - 2 for pl in o.data.polygons)
    tris += t
    r = o.get('root', '?')
    tris_root[r] = tris_root.get(r, 0) + t
    co = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices]) - np.array(SK.DISPLAY[r])
    lo, hi = co.min(0), co.max(0)
    size_root[r] = dict(lo=r4(lo), hi=r4(hi), size=r4(hi - lo), sizeUnity=r4((hi[0] - lo[0], hi[2] - lo[2], hi[1] - lo[1])))
INFO['tris'] = tris
INFO['tris_by_root'] = tris_root
INFO['bounds'] = size_root
INFO['objects'] = {r: sorted(o.name for o in colls[r].objects) for r in SK.ROOTS}
INFO['display_offset'] = {r: r4(SK.DISPLAY[r]) for r in SK.ROOTS}
C['meta'] = dict(version='1.0', units='metres, degrees',
                 frame='each root in its own frame: z up, the front -y; Station_MonitorRack_3x3: origin on the floor under the '
                       'middle of its BACK face (it stands against a wall); Station_SideTable: origin on the floor under its '
                       'middle. Every pivot / pos here is in its root\'s frame. In station.blend the roots stand apart '
                       '(display_offset); the FBX are exported with the root at the origin',
                 unity='position (x, y, z) -> Unity (-x, z, -y) in the prefab; box centre likewise, size (sx, sy, sz) -> (sx, sz, '
                       'sy); the root\'s front (-y) is the prefab\'s +Z',
                 display_offset=INFO['display_offset'],
                 sockets='Slot_* are empties under their root in station.blend and in the FBX (child transforms, no rotation); '
                         'posUnity = the same in the prefab',
                 colliders='BoxCollider per entry on its root: center / size in the root\'s frame, centerUnity / sizeUnity the '
                           'same in Unity axes. The COL_ objects are in the .blend for reference (collection Colliders), not '
                           'in the FBX',
                 kit_monitor='Kit_Monitor_CRT as built (snow_kit 1.1): 0.34 wide, 0.31 tall, 0.45 deep (y -0.202 front .. '
                             '+0.248 back about its pivot); the slots centre that depth 0.26 m in front of the rack\'s back',
                 model='station.blend', textures='tex',
                 materials='M_Station_Props: the baked PSX atlas T_Station_Props_BaseColor.png (point filter, BaseColor only, '
                           'no emission) on both models')
sfx = '_draft' if DRAFT else ''
for o in bpy.data.objects:
    if o.name.startswith('COL_') and o.library is None:
        o.hide_set(True)
json.dump(_nz(C), open(os.path.join(OUT, f'station_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
json.dump({'lights': [], 'note': 'forest_station has no lamps'}, open(os.path.join(OUT, f'station_lights{sfx}.json'), 'w'), indent=1)
INFO['contract'] = dict(parts=len(C['parts']), sockets=len(C['sockets']), colliders=len(C['colliders']))
log('contract', INFO['contract'], 'tris', tris, tris_root)
for o in [o for o in bpy.data.objects if o.type == 'MESH' and o.library is None]:
    uvs = o.data.uv_layers
    if 'PSX' in uvs:
        for u in [u for u in uvs if u.name != 'PSX']:
            uvs.remove(u)
        uvs['PSX'].active = True
    if 'zone' in o.data.attributes and not DRAFT:
        o.data.attributes.remove(o.data.attributes['zone'])
json.dump(_nz(INFO), open(os.path.join(OUT, f'station{sfx}.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'station{sfx}.blend'), relative_remap=False)
log('saved', f'station{sfx}.blend')
