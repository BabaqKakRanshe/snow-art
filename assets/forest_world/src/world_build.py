"""forest_world build (world_kit + world_ice): one object per part with its pivot as the origin, each root in its own
collection standing at its DISPLAY offset in the file (the contract gives everything in the root's own frame - for the ice:
its host prefab's frame); the door markings and the newspaper (panel) joined into their bodies as another material;
PSX atlases baked with psxbake + world_paint: World (the fire barrel and both cars, 1024 px at 51.3 px/m) and Cave (the
rock shell and its dressing, 1024 px); explicit materials: the panel, the cars' glass, the wreck's cracked windscreen, the
fire's flipbook, the embers lit / off, the ice (tiling); the interaction contract (parts, sockets, colliders, the cave's
mesh collider, the ice's hosts and hit boxes, lights, meta).
python3 -I world_build.py [--draft] -> out/world.blend, out/world.json, out/world_contract.json, out/world_lights.json, tex/world/*"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
sys.path.insert(1, '/home/claude/far')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import psxlib as P
import psxbake as PB
import world_tex as WT
import gen_kit as K
import world_kit as WK
import world_ice as WI

DRAFT = '--draft' in sys.argv
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'world')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
T0 = time.time()
INFO = {}
PB.POS_SCALE = 40.0                                   # bake range +-20 m: the cave reaches y 18
WORLD_PPM = 51.3


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
    return [round(-float(v[0]), 4) + 0.0, round(float(v[2]), 4) + 0.0, round(-float(v[1]), 4) + 0.0]


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
TP = WT.build(TEX)

# ------------------------------------------------------------------ 1. geometry
WK.build_world()
WI.build_ice()
C = K.CONTRACT
ROOTS = WK.ROOTS + WI.ICE_ROOTS
DISPLAY = dict(WK.DISPLAY, **WI.ICE_DISPLAY)
missing = [n for n in K.KBS if n not in C['parts'] and n not in WK.MERGE]
assert not missing, f'objects without a contract entry: {missing}'


def box_uv(k, scale=1.0):
    """box-mapped UVs (1 m = one tile of the 64 px ice texture) on every face"""
    for f in k.bm.faces:
        n = f.normal if f.normal.length > 0 else Vector((0, 0, 1))
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            p = l.vert.co
            l[k.uvl].uv = ((p.x, p.y) if ax == 2 else (p.y, p.z) if ax == 0 else (p.x, p.z))
            l[k.uvl].uv = (l[k.uvl].uv[0] * scale, l[k.uvl].uv[1] * scale)


colls = {}
for root in ROOTS:
    colls[root] = bpy.data.collections.new(root)
    colls[root].instance_offset = DISPLAY[root]
    bpy.context.scene.collection.children.link(colls[root])
objs = {}
for name, k in K.KBS.items():
    root = WK.ROOT_OF[name]
    off = DISPLAY[root]
    if K.ATLAS[name] == 'ice':
        k.bm.normal_update()
        box_uv(k)
    K.transform_kb(k, Matrix.Translation(off))
    p = C['parts'][WK.MERGE.get(name, name)]
    o = k.to_object(name, coll=colls[root], pivot=Vector(p['pivot']) + off)
    o['root'] = root
    objs[name] = o
for name, o in objs.items():                        # the collision shell must not shade the cave's AO bake
    if K.ATLAS[name] == 'none':
        o.hide_render = True
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
import world_paint as WP
boot = objs['IX_WreckCarBoot']
if DRAFT:
    cache = {}

    def zmat(z):
        if z not in cache:
            m = bpy.data.materials.new(f'draft_{z}')
            m.use_nodes = True
            pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            c = PB.lin(*WP.DRAFT_COL.get(z, (128, 128, 128)))
            pb.inputs['Base Color'].default_value = (float(c[0]), float(c[1]), float(c[2]), 1)
            pb.inputs['Roughness'].default_value = 0.75
            m.diffuse_color = (float(c[0]), float(c[1]), float(c[2]), 1)
            cache[z] = m
        return cache[z]

    for name, o in objs.items():
        if K.ATLAS[name] not in ('World', 'Cave'):
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
    PB.make_atlas('World', groups['World'], WP.paint_world, TEX, prefix='T_World_', mat_prefix='M_World_', size=1024,
                  ao_min=0.42, ao_dist=0.25, rough=0.65, log=log, info=INFO['atlases'], ppm_cap=WORLD_PPM,
                  prio_zones=(WK.Z_AMBER, WK.Z_TAIL, WK.Z_SNOW))
    props = (WK.Z_CANDLE, WK.Z_WAX, WK.Z_SOLE, WK.Z_BOOT, WK.Z_TIN, WK.Z_SAWF, WK.Z_SAWB, WK.Z_NAIL, WK.Z_BOTTLE, WK.Z_WIRE,
             WK.Z_BUCKET, WK.Z_SAWDUST)
    zs = {WK.Z_ROCK: 0.70, WK.Z_ROCKD: 0.08}
    zs.update({z: 1.8 for z in props})
    PB.make_atlas('Cave', groups['Cave'], WP.paint_cave, TEX, prefix='T_World_', mat_prefix='M_World_', size=1024,
                  ao_min=0.35, ao_dist=0.45, rough=0.85, log=log, info=INFO['atlases'], zone_scale=zs)   # (no prio zones: the
    # vivid bits would take palette entries from the rock's greys and posterize it into blotches)

# ------------------------------------------------------------------ 3. explicit materials
m_panel = P.psx_material('M_World_Panel', TP['Panel_BaseColor'], rough=0.7)


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


def alpha_mat(name, img_path, emission=0.0, clip=False, rough=0.5):
    """point-filtered texture with its alpha (cut-out for the fire, blended for the cracked glass); emission = the texture"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    pb = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    ti = nt.nodes.new('ShaderNodeTexImage')
    ti.image = bpy.data.images.load(img_path, check_existing=True)
    ti.interpolation = 'Closest'
    uvn = nt.nodes.new('ShaderNodeUVMap')
    uvn.uv_map = 'PSX'
    nt.links.new(uvn.outputs[0], ti.inputs[0])
    nt.links.new(ti.outputs['Color'], pb.inputs['Base Color'])
    nt.links.new(ti.outputs['Alpha'], pb.inputs['Alpha'])
    pb.inputs['Roughness'].default_value = rough
    if emission:
        nt.links.new(ti.outputs['Color'], pb.inputs['Emission Color'])
        pb.inputs['Emission Strength'].default_value = emission
    try:
        m.surface_render_method = 'DITHERED' if clip else 'BLENDED'
    except Exception:
        pass
    return m


m_glass = P.psx_glass('M_World_Glass', tint=(0.34, 0.38, 0.36), alpha=0.55)
m_crack = alpha_mat('M_World_GlassCracked', TP['GlassCracked_BaseColor'], rough=0.4)
m_fire = alpha_mat('M_World_Fire', TP['Fire_BaseColor'], emission=4.0, clip=True)
m_emb_off = flat_mat('M_World_Embers_Off', (30, 28, 26), rough=0.9)
m_emb = flat_mat('M_World_Embers', (200, 70, 20), (255, 110, 30), 4.0, 0.9, fake=True)
m_ice = P.psx_material('M_World_Ice', TP['Ice_BaseColor'], rough=0.25, spec=0.5)
for name, o in objs.items():
    a = K.ATLAS[name]
    if a in ('World', 'Cave'):
        continue
    o.data.materials.clear()
    if a == 'panel':
        o.data.materials.append(m_panel)
    elif a == 'glass':
        o.data.materials.append(m_glass)
    elif a == 'glasscrack':
        o.data.materials.append(m_crack)
    elif a == 'fire':
        o.data.materials.append(m_fire)
    elif a == 'embers':
        o.data.materials.append(m_emb_off)
    elif a == 'ice':
        o.data.materials.append(m_ice)
    elif a == 'none':
        o.display_type = 'WIRE'
        o.hide_render = True
    else:
        raise ValueError(a)

# ------------------------------------------------------------------ 3b. the explicit-UV faces join their bodies
for name, dst in WK.MERGE.items():
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
log('merged', len(WK.MERGE), 'faces into their bodies')

# ------------------------------------------------------------------ 4. hierarchy (world transforms kept)
for name, p in C['parts'].items():
    if name in objs and p.get('parent') and p['parent'] in objs:
        attach(objs[name], objs[p['parent']])
    p['object'] = name if name in objs else None
    p['root'] = WK.ROOT_OF.get(name, name)
    if name in WK.MASS:
        p['mass_kg'] = WK.MASS[name]


def root_of_part(name):
    while C['parts'][name].get('parent'):
        name = C['parts'][name]['parent']
    return name


for s in C['sockets'].values():
    s['root'] = root_of_part(s['parent']) if s.get('parent') in C['parts'] else s.get('parent')

# ------------------------------------------------------------------ 5. colliders (in each parent's own frame) and hit boxes
coll_c = bpy.data.collections.new('Colliders')
bpy.context.scene.collection.children.link(coll_c)
C['colliders'] = []


def add_box(name, par, lo_hi, rot=None, kind='box', note=None):
    x0, x1, y0, y1, z0, z1 = lo_hi
    root = WK.ROOT_OF[par]
    off = DISPLAY[root]
    piv = Vector(C['parts'][par]['pivot'])
    c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    size = Vector((x1 - x0, y1 - y0, z1 - z0))
    kb_ = K.KB()
    kb_.box(-size.x / 2, size.x / 2, -size.y / 2, size.y / 2, -size.z / 2, size.z / 2, 0)
    ob = kb_.to_object(('COL_' if kind == 'box' else 'HIT_') + name, coll=coll_c)
    ob.location = c + off
    if rot:
        ob.rotation_euler = Euler([math.radians(a) for a in rot], 'XYZ')
    ob.display_type = 'WIRE'
    ob.hide_render = True
    ob['collider'] = kind
    attach(ob, objs[par])
    lc = c - piv
    ent = dict(name=ob.name, parent=par, root=root, type=kind, center=r4(lc), size=r4(size), center_root=r4(c),
               centerUnity=to_unity(lc), sizeUnity=r4((size.x, size.z, size.y)))
    if rot:
        ent['rotation'] = [float(a) for a in rot]
        ent['rotationUnity'] = [float(rot[0]), -float(rot[2]), float(rot[1])]
    if note:
        ent['note'] = note
    C['colliders'].append(ent)


for name, par, lo_hi, rot in WK.BOXES:
    add_box(name, par, lo_hi, rot)
for name, lo_hi in WI.BOXES:
    pad = 0.05
    x0, x1, y0, y1, z0, z1 = lo_hi
    add_box(name, name, (x0 - pad, x1 + pad, y0 - pad, y1 + pad, z0 - pad, z1 + pad), kind='hit',
            note='trigger / hit box of a removable ice part (not a solid collider)')
cm = objs['COLM_Cave']
cm.name = 'COLM_Cave'
C['colliders'].append(dict(name='COLM_Cave', parent='ForesterCave', root='ForesterCave', type='mesh',
                           tris=len(cm.data.polygons), note='MeshCollider (not convex) from the object COLM_Cave: the rock '
                                                            'shell simplified; the dressing gets no collider'))
log('colliders', len(C['colliders']))

# ------------------------------------------------------------------ 6. part boxes (grab / hit box of moving parts)
for k, p in C['parts'].items():
    o = objs.get(k)
    if o is None or p['kind'] == 'static':
        continue
    co = np.array([tuple(v.co) for v in o.data.vertices])
    lo, hi = co.min(0), co.max(0)
    p['box'] = dict(center=r4((lo + hi) / 2), size=r4(np.maximum(hi - lo, 0.002)))

# ------------------------------------------------------------------ 7. lights, ice, Unity values, meta, stats, save
lights = []
for name, par, pos, d, kind, colr, rng, beh in WK.LIGHTS:
    lights.append(dict(name=name, parent=par, root=WK.ROOT_OF[par], type=kind, pos=r4(pos), posUnity=to_unity(pos),
                       color_linear=list(colr), range=rng, behaviour=beh, default='off'))
json.dump(_nz(dict(lights=lights)), open(os.path.join(OUT, 'world_lights.json'), 'w'), indent=1)
C['ice'] = {}
for root in WI.ICE_ROOTS:
    host, pkg = WI.HOSTS[root]
    C['ice'][root] = dict(host=host, package=pkg, parts=sorted(n for n in C['parts'] if C['parts'][n].get('root') == root),
                          removable=[n for n, h in WI.REMOVABLE if C['parts'][n].get('root') == root],
                          note=f'parent {root} to {host} at its origin, no rotation (the ice is in {host}\'s own frame)')
C['anchors'] = dict(ShiftCar=dict(anchor='anchors/Car_Parked', layout='Forest_Layout.json',
                                  p=[323.2564, 16.3794, -335.4306], q=[0.0, -0.688355, 0.0, 0.725374],
                                  note='the previous shift\'s car: put ShiftCar on this anchor (Unity world, as the layout gives it)'))
for k, p in C['parts'].items():
    p['pivotUnity'] = to_unity(p['pivot'])
    if p.get('axis'):
        p['axisUnity'] = to_unity(p['axis'])
for s in C['sockets'].values():
    s['posUnity'] = to_unity(s['pos'])
    for key in ('dir', 'up', 'forward'):
        if s.get(key):
            s[key + 'Unity'] = to_unity(s[key])
    if s.get('size'):
        s['sizeUnity'] = r4((s['size'][0], s['size'][2], s['size'][1]))
tris, tris_root = 0, {}
for o in bpy.data.objects:
    if o.type != 'MESH' or o.name.startswith(('COL_', 'HIT_', 'COLM_')) or o.library is not None:
        continue
    t = sum(len(pl.vertices) - 2 for pl in o.data.polygons)
    tris += t
    tris_root[o.get('root', '?')] = tris_root.get(o.get('root', '?'), 0) + t
INFO['tris'] = tris
INFO['tris_by_root'] = tris_root
INFO['objects'] = {r: sorted(o.name for o in colls[r].objects) for r in ROOTS}
INFO['display_offset'] = {r: r4(DISPLAY[r]) for r in ROOTS}
INFO['mass_kg'] = WK.MASS
INFO['paper_date'] = WT.PAPER_DATE
C['meta'] = dict(version='1.0', units='metres, degrees, kg',
                 frame='each root in its own frame: z up, the front -y, origin on the ground under its middle (the cave: the floor '
                       'in its mouth); the ice roots in their host prefab\'s frame. Every pivot / pos here is in its root\'s frame. In '
                       'world.blend the roots stand apart (display_offset); their FBX is exported with the root at the origin',
                 unity='position (x, y, z) -> Unity (-x, z, -y) in the prefab; axis likewise; angle -> -angle (Unity is left-handed); '
                       'box centre likewise, size (sx, sy, sz) -> (sx, sz, sy); the root\'s front (-y) is the prefab\'s +Z',
                 display_offset=INFO['display_offset'],
                 colliders='BoxCollider per type box entry on its parent (center / size in the parent\'s own frame); type hit: a '
                           'trigger box of a removable ice part; type mesh: the cave\'s MeshCollider (object COLM_Cave). The COL_ / '
                           'HIT_ objects are in the .blend for reference (collection Colliders), not in the FBX',
                 warm_radius=dict(FireBarrel=3.5, note='burning: no wind-chill and R1 (creatures keep off) within 3.5 m; embers: '
                                                        '1.5 m'),
                 lights='world_lights.json: the barrel\'s fire and the four candles in the cave (all off in the file)',
                 ice='each ice root goes under its host (forest_far RelayMast / Dish_n, forest_main BaseMain) at the origin; the root '
                     'is scenery (show after a blizzard, hide when it thaws); the removable parts are what the players knock off '
                     'to get the aerial working again (QUESTIONS_HORROR 41, BASE_THREATS B04); M_World_Ice is box-mapped (UV 1 = 1 m, '
                     'the texture repeats)',
                 model='world.blend', textures='tex',
                 materials='M_World_World / M_World_Cave: baked PSX atlases (point filter); M_World_Panel: the station marking on '
                           'the shift car\'s doors and the 1991 newspaper; M_World_Glass: the cars\' windows; M_World_GlassCracked: '
                           'the wreck\'s windscreen (alpha); M_World_Fire: the flames, 8-frame flipbook, alpha cut-out, emissive; '
                           'M_World_Embers_Off / M_World_Embers: the barrel\'s ember bed and air holes cold / glowing (off in the file); '
                           'M_World_Ice: the ice overlays',
                 names='FireBarrel, ShiftCar, WreckCar and ForesterCave are fixtures (not carried); the doors IX_* without numbers - '
                       'Unity numbers them when it places them')
sfx = '_draft' if DRAFT else ''
for o in bpy.data.objects:
    if o.name.startswith(('COL_', 'HIT_', 'COLM_')) and o.library is None:
        o.hide_set(True)
json.dump(_nz(C), open(os.path.join(OUT, f'world_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
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
json.dump(_nz(INFO), open(os.path.join(OUT, f'world{sfx}.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'world{sfx}.blend'), relative_remap=False)
log('saved', f'world{sfx}.blend')
