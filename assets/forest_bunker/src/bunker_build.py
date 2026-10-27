"""forest_bunker build (bunker_kit): one object per part with its pivot as the origin, each root in its own collection at
its DISPLAY offset in the file (the contract gives everything in the root's own frame; PlaneTarp in the plane's frame); the
signs and the console face (panel) joined into their bodies as another material; PSX atlases baked with psxbake +
bunker_paint: Hangar (the shell, 2048 at 51.3 px/m), HangarParts (gates, steel, lamps, the side door, railings, 1024),
BlastDoor (1024), Entrance (1024), Tarp (512); explicit materials: the panel, the lamps lit / off, the wet prints (cut-out),
the clear ice (box-mapped, blended); the interaction contract (parts, sockets, colliders, hit boxes, lights, meta).
python3 -I bunker_build.py [--draft] -> out/bunker.blend, out/bunker.json, out/bunker_contract.json, out/bunker_lights.json,
tex/bunker/*"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import psxlib as P
import psxbake as PB
import bunker_tex as BT
import gen_kit as K
import bunker_kit as BK
import bunker_spec as S

DRAFT = '--draft' in sys.argv
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'bunker')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
T0 = time.time()
INFO = {}
PB.POS_SCALE = 80.0                                   # bake range +-40 m: the hangar's facade spans 40 m with the display offsets
PPM = 51.3
BAKED = ('Hangar', 'HangarParts', 'BlastDoor', 'Entrance', 'Tarp')


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
TP = BT.build(TEX)

# ------------------------------------------------------------------ 1. geometry
BK.build_bunker()
C = K.CONTRACT
ROOTS = BK.ROOTS
DISPLAY = BK.DISPLAY
missing = [n for n in K.KBS if n not in C['parts'] and n not in BK.MERGE]
assert not missing, f'objects without a contract entry: {missing}'


def box_uv(k, scale=1.0):
    """box-mapped UVs (1 m = one tile of the 64 px ice texture) on every face"""
    for f in k.bm.faces:
        n = f.normal if f.normal.length > 0 else Vector((0, 0, 1))
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            p = l.vert.co
            u_ = (p.x, p.y) if ax == 2 else (p.y, p.z) if ax == 0 else (p.x, p.z)
            l[k.uvl].uv = (u_[0] * scale, u_[1] * scale)


for name, k in K.KBS.items():                                 # n-gons (the octagonal door, the console's end) -> triangles
    big = [f for f in k.bm.faces if len(f.verts) > 4]
    if big:
        bmesh.ops.triangulate(k.bm, faces=big, quad_method='BEAUTY', ngon_method='BEAUTY')
colls = {}
for root in ROOTS:
    colls[root] = bpy.data.collections.new(root)
    colls[root].instance_offset = DISPLAY[root]
    bpy.context.scene.collection.children.link(colls[root])
objs = {}
for name, k in K.KBS.items():
    root = BK.ROOT_OF[name]
    off = DISPLAY[root]
    if K.ATLAS[name] == 'iceclear':
        k.bm.normal_update()
        box_uv(k)
    K.transform_kb(k, Matrix.Translation(off))
    p = C['parts'][BK.MERGE.get(name, name)]
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
# the AO bakes see only what is solid: glass, ice, decals out of the way
for name, o in objs.items():
    if K.ATLAS[name] in ('lamp', 'prints', 'iceclear', 'panel'):
        o.hide_render = True

# ------------------------------------------------------------------ 2. atlases (or flat zone colours for the draft)
INFO['atlases'] = {}
import bunker_paint as BP
if DRAFT:
    cache = {}

    def zmat(z):
        if z not in cache:
            m = bpy.data.materials.new(f'draft_{z}')
            m.use_nodes = True
            pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            c = PB.lin(*BP.DRAFT_COL.get(z, (128, 128, 128)))
            pb.inputs['Base Color'].default_value = (float(c[0]), float(c[1]), float(c[2]), 1)
            pb.inputs['Roughness'].default_value = 0.75
            m.diffuse_color = (float(c[0]), float(c[1]), float(c[2]), 1)
            cache[z] = m
        return cache[z]

    for name, o in objs.items():
        if K.ATLAS[name] not in BAKED:
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
    REUSE = set(sys.argv[sys.argv.index('--reuse') + 1].split(',')) if '--reuse' in sys.argv else set()

    def make_atlas(name, objs, painter, tex, prefix='T_Bunker_', mat_prefix='M_Bunker_', size=1024, rough=0.8,
                   zone_scale=None, ppm_cap=None, **kw):
        """PB.make_atlas, or for an atlas in --reuse: the same UVs as prepare_atlas makes (deterministic) and the
        texture of the previous build - no bake (rebuild only what changed)"""
        if name not in REUSE:
            return PB.make_atlas(name, objs, painter, tex, prefix=prefix, mat_prefix=mat_prefix, size=size, rough=rough,
                                 zone_scale=zone_scale, ppm_cap=ppm_cap, **kw)
        from PIL import Image
        margin = max(0.002, (2.2 if ppm_cap else 1.5) / size)
        P.unwrap_group(objs, margin=margin, angle=62, zone_scale=zone_scale)
        A = P.area3d(objs)
        fill = max(P.uv_fill(objs), 1e-6)
        if ppm_cap and size * math.sqrt(fill / A) > ppm_cap:
            kk = ppm_cap / (size * math.sqrt(fill / A))
            for o in objs:
                for l in o.data.uv_layers['PSX'].data:
                    l.uv = l.uv * kk
            fill = max(P.uv_fill(objs), 1e-6)
        path = os.path.join(tex, f'{prefix}{name}_BaseColor.png')
        m = P.psx_material(mat_prefix + name, path, rough=rough)
        for o in objs:
            o.data.materials.clear()
            o.data.materials.append(m)
        q = np.asarray(Image.open(path).convert('RGB'))
        INFO['atlases'][name] = dict(size=size, ppm=round(size * math.sqrt(fill / A), 1), area_m2=round(A, 2),
                                     uv_fill=round(fill, 3), colours=int(len(np.unique(q.reshape(-1, 3), axis=0))))
        log('ATLAS (reused)', name, INFO['atlases'][name])
        return m

    hid = 0.04
    make_atlas('Hangar', groups['Hangar'], BP.paint_hangar, TEX, prefix='T_Bunker_', mat_prefix='M_Bunker_', size=2048,
                  ao_min=0.40, ao_dist=0.9, rough=0.85, log=log, info=INFO['atlases'], ppm_cap=PPM,
                  zone_scale={BK.Z_HHIDE: hid, BK.Z_HCEIL: 0.55, BK.Z_HFLOOR: 0.85, BK.Z_HAPRON: 0.7, BK.Z_HSTUB: 0.3,
                              BK.Z_HICE: 1.4})
    make_atlas('HangarParts', groups['HangarParts'], BP.paint_parts, TEX, prefix='T_Bunker_', mat_prefix='M_Bunker_',
                  size=2048, ao_min=0.40, ao_dist=0.35, rough=0.7, log=log, info=INFO['atlases'], ppm_cap=PPM,
                  zone_scale={BK.Z_BEAM: 0.6, BK.Z_GLEAFIN: 0.6, BK.Z_HANDLE: 1.5, BK.Z_CAGE: 1.5, BK.Z_LAMPB: 1.5})
    make_atlas('BlastDoor', groups['BlastDoor'], BP.paint_blastdoor, TEX, prefix='T_Bunker_', mat_prefix='M_Bunker_',
                  size=1024, ao_min=0.38, ao_dist=0.6, rough=0.75, log=log, info=INFO['atlases'], ppm_cap=PPM,
                  zone_scale={BK.Z_VHIDE: hid, BK.Z_VCEIL: 0.6, BK.Z_TUN: 0.5, BK.Z_STEPD: 0.5, BK.Z_VOID: 0.1,
                              BK.Z_RING: 1.3, BK.Z_LEAF: 1.2, BK.Z_HUB: 1.3})
    make_atlas('Entrance', groups['Entrance'], BP.paint_entrance, TEX, prefix='T_Bunker_', mat_prefix='M_Bunker_',
                  size=1024, ao_min=0.38, ao_dist=0.5, rough=0.8, log=log, info=INFO['atlases'], ppm_cap=PPM,
                  zone_scale={BK.Z_EHIDE: hid, BK.Z_ELID: 2.0, BK.Z_EWHEEL: 2.0, BK.Z_EOUT: 0.5})
    make_atlas('Tarp', groups['Tarp'], BP.paint_tarp, TEX, prefix='T_Bunker_', mat_prefix='M_Bunker_', size=512,
                  ao_min=0.42, ao_dist=0.6, rough=0.9, log=log, info=INFO['atlases'], ppm_cap=PPM)

# ------------------------------------------------------------------ 3. explicit materials
m_panel = P.psx_material('M_Bunker_Panel', TP['Panel_BaseColor'], rough=0.6)


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


def alpha_mat(name, img_path, clip=False, rough=0.5, alpha_mul=1.0):
    """point-filtered texture with its alpha (cut-out or blended)"""
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
    if clip:
        nt.links.new(ti.outputs['Alpha'], pb.inputs['Alpha'])
    else:
        pb.inputs['Alpha'].default_value = alpha_mul
    pb.inputs['Roughness'].default_value = rough
    try:
        m.surface_render_method = 'DITHERED' if clip else 'BLENDED'
    except Exception:
        pass
    return m


m_lamp_off = flat_mat('M_Bunker_Lamp_Off', (176, 170, 150), rough=0.3)
m_lamp = flat_mat('M_Bunker_Lamp', (255, 226, 170), (255, 214, 150), 6.0, 0.3, fake=True)
m_prints = alpha_mat('M_Bunker_Prints', TP['Prints_BaseColor'], clip=True, rough=0.15)
m_ice = alpha_mat('M_Bunker_IceClear', TP['Ice_BaseColor'], clip=False, rough=0.15, alpha_mul=0.35)
for name, o in objs.items():
    a = K.ATLAS[name]
    if a in BAKED:
        if a == 'Tarp':
            o.data.materials[0].use_backface_culling = False
        continue
    o.data.materials.clear()
    if a == 'panel':
        o.data.materials.append(m_panel)
    elif a == 'lamp':
        o.data.materials.append(m_lamp_off)
    elif a == 'prints':
        o.data.materials.append(m_prints)
    elif a == 'iceclear':
        o.data.materials.append(m_ice)
    else:
        raise ValueError(a)
    o.hide_render = False

# ------------------------------------------------------------------ 3b. the explicit-UV faces join their bodies
for name, dst in BK.MERGE.items():
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
log('merged', len(BK.MERGE), 'faces into their bodies')

# ------------------------------------------------------------------ 4. hierarchy (world transforms kept)
for name, p in C['parts'].items():
    if name in objs and p.get('parent') and p['parent'] in objs:
        attach(objs[name], objs[p['parent']])
    p['object'] = name if name in objs else None
    p['root'] = BK.ROOT_OF.get(name, name)
    if name in BK.MASS:
        p['mass_kg'] = BK.MASS[name]


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
    root = BK.ROOT_OF[par]
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


for name, par, lo_hi, rot in BK.BOXES:
    add_box(name, par, lo_hi, rot)
for name, lo_hi in BK.HITS:
    add_box(name, name, lo_hi, kind='hit', note='trigger / hit box of a removable ice chunk (not a solid collider)')
log('colliders', len(C['colliders']))

# ------------------------------------------------------------------ 6. part boxes (grab / hit box of moving parts)
for k, p in C['parts'].items():
    o = objs.get(k)
    if o is None or p['kind'] == 'static':
        continue
    co = np.array([tuple(v.co) for v in o.data.vertices])
    lo, hi = co.min(0), co.max(0)
    p['box'] = dict(center=r4((lo + hi) / 2), size=r4(np.maximum(hi - lo, 0.002)))

# ------------------------------------------------------------------ 7. lights, Unity values, meta, stats, save
lights = []
for name, par, pos, d, kind, colr, rng, beh in BK.LIGHTS:
    ent = dict(name=name, parent=par, root=BK.ROOT_OF[par], type=kind, pos=r4(pos), posUnity=to_unity(pos),
               color_linear=list(colr), range=rng, behaviour=beh, default='off')
    if d is not None:
        ent['dir'] = r4(d)
        ent['dirUnity'] = to_unity(d)
        ent['spot_angle'] = 110
    lights.append(ent)
json.dump(_nz(dict(lights=lights)), open(os.path.join(OUT, 'bunker_lights.json'), 'w'), indent=1)
for k, p in C['parts'].items():
    p['pivotUnity'] = to_unity(p['pivot'])
    if p.get('axis'):
        p['axisUnity'] = to_unity(p['axis'])
for s in C['sockets'].values():
    s['posUnity'] = to_unity(s['pos'])
    for key in ('dir', 'up', 'forward'):
        if s.get(key):
            s[key + 'Unity'] = to_unity(s[key])
    if s.get('euler'):
        e = s['euler']
        s['eulerUnity'] = [round(float(e[0]), 4), round(-float(e[2]), 4), round(float(e[1]), 4)]
    if s.get('yaw') is not None:
        s['yawUnity'] = -float(s['yaw'])
C['removable'] = list(BK.REMOVABLE)
M = S.plane_park_matrix()
C['plane'] = dict(model='forest UtilityPlane v13 (source/plane/UtilityPlane_Unity_v13), the WinterKit 1.2 installed',
                  slot='Slot_Plane', pitch_deg=round(S.PLANE['pitch'], 3),
                  main_wheels_y=S.PLANE['y_main'], root=r4(M.translation), rootUnity=to_unity(M.translation),
                  tarp='PlaneTarp: child of the plane root at (0, 0, 0), no rotation',
                  note='the plane itself is not part of this package; the tarp was draped with the plane in this pose')
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
INFO['mass_kg'] = BK.MASS
C['meta'] = dict(version='1.0', units='metres, degrees, kg',
                 frame='each root in its own frame: z up, the front -y; BunkerHangar: origin on the floor in the middle of the '
                       'gate line; BlastDoor: the floor in the middle of its open end; BunkerEntrance: the ground at the top '
                       'step\'s edge; PlaneTarp: forest UtilityPlane\'s own frame. Every pivot / pos here is in its root\'s '
                       'frame. In bunker.blend the roots stand apart (display_offset; the vestibule at its link behind the '
                       'hangar); their FBX is exported with the root at the origin',
                 unity='position (x, y, z) -> Unity (-x, z, -y) in the prefab; axis likewise; angle -> -angle (Unity is '
                       'left-handed); box centre likewise, size (sx, sy, sz) -> (sx, sz, sy); Euler XYZ (x, y, z) -> Unity '
                       '(x, -z, y); the root\'s front (-y) is the prefab\'s +Z',
                 display_offset=INFO['display_offset'],
                 assembly='BlastDoor on BunkerHangar Link_BlastDoor (no rotation); the plane on Slot_Plane, PlaneTarp under the '
                          'plane root; BunkerEntrance by the hand on the lake, joined to the hangar\'s Link_SideDoor by the '
                          'underground part (not in this package) from its Link_Shaft',
                 colliders='BoxCollider per type box entry on its parent (center / size in the parent\'s own frame, optional '
                           'rotation); type hit: a trigger box of a removable ice chunk. The COL_ / HIT_ objects are in the '
                           '.blend for reference (collection Colliders), not in the FBX',
                 lights='bunker_lights.json: the hangar\'s six pendant lamps (spots), its door and back lamps, the vestibule\'s '
                        'two, the portal\'s one (all off in the file: the bunker has no power until the players bring it)',
                 model='bunker.blend', textures='tex',
                 materials='M_Bunker_Hangar / _HangarParts / _BlastDoor / _Entrance / _Tarp: baked PSX atlases (point filter; '
                           'M_Bunker_Tarp: Render Face Both); M_Bunker_Panel: signs and the door console; M_Bunker_Lamp_Off / '
                           'M_Bunker_Lamp: the lamps\' glasses off / lit (lit kept by a fake user); M_Bunker_Prints: wet boot '
                           'prints, alpha cut-out; M_Bunker_IceClear: the ice on the entrance landing, box-mapped (UV 1 = 1 m, '
                           'the tile repeats), opacity 0.35 (one layer: no underside)',
                 names='the doors IX_* without numbers - Unity numbers them when it places them')
sfx = '_draft' if DRAFT else ''
for o in bpy.data.objects:
    if o.name.startswith(('COL_', 'HIT_', 'COLM_')) and o.library is None:
        o.hide_set(True)
json.dump(_nz(C), open(os.path.join(OUT, f'bunker_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
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
json.dump(_nz(INFO), open(os.path.join(OUT, f'bunker{sfx}.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'bunker{sfx}.blend'), relative_remap=False)
log('saved', f'bunker{sfx}.blend')
