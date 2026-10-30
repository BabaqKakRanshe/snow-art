"""forest_network build (adapted from the forest_airfield build): one object per part with its pivot as the origin, each root
in its own collection standing at net_kit.DISPLAY; one PSX atlas baked with psxbake + net_paint: NetProps (snow pole, culvert
end, compartment stones; the prop class, 64 px/m); the panel atlas (net_tex) with the stones' numbers; no lamps; the contract
(parts, sockets, colliders, meta).
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_network/net_build.py [--draft]
-> out/net.blend, out/net.json, out/net_contract.json, out/net_lights.json, tex/net/*"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import psxlib as P
import psxbake as PB
import net_tex as YT
import gen_kit as K
import net_kit as SK

DRAFT = '--draft' in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex', 'net')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
SHED_PPM = 51.3                                       # the generator shed's building atlas (px / m): the project's pixel
PB.POS_SCALE = 20.0                                   # bake range +-10 m: the props stand within 4 m of the origin


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


LIGHT_TYPES_UNUSED = {
    'edge': dict(unity='Point', I=0.5, rng=5.0, cct=2700, color=(1.0, 0.72, 0.30), group='runway', spot=None,
                 desc="runway edge light (amber dome); group runway: all edge and threshold lights switch together from the "
                      "airfield's power. Many of them: a real Light only on every second or third, the rest glow cards only"),
    'thr': dict(unity='Point', I=0.5, rng=5.0, cct=6500, color=(0.35, 1.0, 0.45), group='runway', spot=None,
                desc='threshold light (green dome) across the runway end; group runway'),
}

bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
PB_BASE, PB_EMI = YT.build(TEX)

# ------------------------------------------------------------------ 1. geometry
SK.build_network()
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
    if name == 'NET_CulvertHead' or (name.startswith(('NET_Stone', 'NET_Sign_')) and not name.endswith(('_Number', '_Board'))):
        bmesh.ops.remove_doubles(k.bm, verts=list(k.bm.verts), dist=1e-4)
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

# ------------------------------------------------------------------ 2. atlases (or flat zone colours for the draft)
INFO['atlases'] = {}
import net_paint as SPT
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
        if K.ATLAS[name] not in ('NetProps',):
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
    PB.make_atlas('NetProps', groups['NetProps'], SPT.paint_props, TEX, prefix='T_NET_', mat_prefix='M_NET_', size=None,
                  ppm=64.0, ao_min=0.40, ao_dist=0.15, rough=0.85, log=log, info=INFO['atlases'], ppm_cap=64.0,
                  prio_zones=(SK.Z_POLE, SK.Z_STONE))

# ------------------------------------------------------------------ 3. explicit materials
m_panel = PB.tex_mat('M_NET_Panel', PB_BASE, PB_EMI, 0.0, rough=0.7)
for name, o in objs.items():
    a = K.ATLAS[name]
    if a == 'NetProps':
        continue
    o.data.materials.clear()
    if a == 'panel':
        o.data.materials.append(m_panel)
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


def root_of_part(name):
    while C['parts'][name].get('parent'):
        name = C['parts'][name]['parent']
    return name


for s in C['sockets'].values():
    s['root'] = root_of_part(s['parent']) if s.get('parent') in C['parts'] else s.get('parent')

# ------------------------------------------------------------------ 5. lamps: none
json.dump(dict(note='forest network props: no lamps', lights=[]), open(os.path.join(OUT, 'net_lights.json'), 'w'), indent=1)
INFO['lamps'] = 0

# ------------------------------------------------------------------ 6. colliders (in each parent's own frame)
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

# ------------------------------------------------------------------ 7. part boxes (grab / hit box of moving parts)
for k, p in C['parts'].items():
    o = objs.get(k)
    if o is None or p['kind'] == 'static':
        continue
    co = np.array([tuple(v.co) for v in o.data.vertices])
    lo, hi = co.min(0), co.max(0)
    p['box'] = dict(center=r4((lo + hi) / 2), size=r4(np.maximum(hi - lo, 0.004)))

# ------------------------------------------------------------------ 8. Unity values of the parts and sockets, meta, stats, save
for k, p in C['parts'].items():
    p['pivotUnity'] = to_unity(p['pivot'])
    if p.get('axis'):
        p['axisUnity'] = to_unity(p['axis'])
for s in C['sockets'].values():
    s['posUnity'] = to_unity(s['pos'])
    if s.get('dir'):
        s['dirUnity'] = to_unity(s['dir'])
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
C['meta'] = dict(version='1.0', units='metres, degrees', built='locally with tools/snow_style (Blender 5.2.3), 27.10.2026',
                 frame="each root in its own frame: z up, the front -y; the pole and the stones: their middle at the ground (sunk "
                       "0.35 / 0.30 m); the culvert end: the invert at the face of the headwall, the pipe +y. In net.blend the roots "
                       "stand apart (display_offset); FBX with the root at the origin",
                 assembly="NET_SnowPole every 30 m along both runway edges (3 m off the paving) and every ~50 m along the forest "
                          "roads, alternating sides, reflector to the road; NET_CulvertHead at both ends of the culvert under D1 "
                          "(ForestNetwork.json culverts: x, z, invert, yaw, length), each facing away from the road, 0.3 m into the "
                          "bed; NET_Stone<NN> at fork NN (5-12) by the road edge, the number to the road",
                 unity='position (x, y, z) -> Unity (-x, z, -y) in the prefab; axis likewise; angle -> -angle (Unity is left-handed); '
                       'box centre likewise, size (sx, sy, sz) -> (sx, sz, sy); the root front (-y) is the prefab +Z',
                 display_offset=INFO['display_offset'],
                 colliders='BoxCollider per entry on its parent: center / size in the parent own frame. COL_ objects are reference '
                           'only, not in the FBX',
                 lamps='net_lights.json (none)', model='net.blend', textures='tex',
                 materials="M_NET_NetProps: the baked PSX atlas (point filter); M_NET_Panel: the numbers of the stones",
                 ix='none')
sfx = '_draft' if DRAFT else ''
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_set(True)
json.dump(_nz(C), open(os.path.join(OUT, f'net_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
kinds = {}
for p in C['parts'].values():
    kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
INFO['contract'] = dict(parts=len(C['parts']), sockets=len(C['sockets']), colliders=len(C['colliders']), kinds=kinds)
log('contract', INFO['contract'], 'tris', tris, tris_root)
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    uvs = o.data.uv_layers
    if 'PSX' in uvs:
        for u in [u for u in uvs if u.name != 'PSX']:
            uvs.remove(u)
        uvs['PSX'].active = True
    if 'zone' in o.data.attributes and not DRAFT:
        o.data.attributes.remove(o.data.attributes['zone'])
json.dump(_nz(INFO), open(os.path.join(OUT, f'net{sfx}.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'net{sfx}.blend'))
log('saved', f'net{sfx}.blend')
