"""sky_systems build (sky_kit): one object per part with its pivot as the origin, each root in its own collection at its
DISPLAY offset in the file (the contract gives everything in the root's own frame); the panel faces joined into their
bodies as another material; PSX atlases baked with psxbake + sky_paint: SkyMachines (the chiller and the sprayer, 1024),
SkyStructures (the ballast release and the altitude board, 1024) and SkyWalk
(the walkway modules, 1024); explicit materials: the panel, the grating (cut-out, box-mapped 0.5 m), the lamps and the
amber / red / green lights off and lit; the interaction contract (parts, sockets, colliders, lights, meta).
python3 -I sky_build.py [--draft] [--reuse A,B] -> out/sky.blend, out/sky.json, out/sky_contract.json, out/sky_lights.json,
tex/sky/*"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import psxlib as P
import psxbake as PB
import sky_tex as ST
import gen_kit as K
import sky_kit as SK

DRAFT = '--draft' in sys.argv
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'sky')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
T0 = time.time()
INFO = {}
PB.POS_SCALE = 60.0                                   # bake range +-30 m (the display offsets)
PPM = 51.3
BAKED = ('SkyMachines', 'SkyStructures', 'SkyWalk')
EXPLICIT = ('panel', 'grating', 'lamp', 'amber', 'red', 'green')


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
TP = ST.build(TEX)

# ------------------------------------------------------------------ 1. geometry
SK.build_sky()
C = K.CONTRACT
ROOTS = SK.ROOTS
DISPLAY = SK.DISPLAY
missing = [n for n in K.KBS if n not in C['parts'] and n not in SK.MERGE]
assert not missing, f'objects without a contract entry: {missing}'


def box_uv(k, scale=1.0):
    """box-mapped UVs on every face (scale: tiles per metre)"""
    for f in k.bm.faces:
        n = f.normal if f.normal.length > 0 else Vector((0, 0, 1))
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            p = l.vert.co
            u_ = (p.x, p.y) if ax == 2 else (p.y, p.z) if ax == 0 else (p.x, p.z)
            l[k.uvl].uv = (u_[0] * scale, u_[1] * scale)


for name, k in K.KBS.items():                                 # n-gons -> triangles
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
    root = SK.ROOT_OF[name]
    off = DISPLAY[root]
    if K.ATLAS[name] == 'grating':
        k.bm.normal_update()
        box_uv(k, 2.0)                                        # UV 1 = 0.5 m (one 64 px tile)
    K.transform_kb(k, Matrix.Translation(off))
    p = C['parts'][SK.MERGE.get(name, name)]
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
for name, o in objs.items():                                   # the AO bakes see only what is solid
    if K.ATLAS[name] in EXPLICIT:
        o.hide_render = True

# ------------------------------------------------------------------ 2. atlases (or flat zone colours for the draft)
INFO['atlases'] = {}
import sky_paint as SP
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

    def make_atlas(name, objs, painter, tex, prefix='T_Sky_', mat_prefix='M_Sky_', size=1024, rough=0.8,
                   zone_scale=None, ppm_cap=None, **kw):
        """PB.make_atlas, or for an atlas in --reuse: the same UVs (deterministic) and the previous build's texture"""
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

    make_atlas('SkyMachines', groups['SkyMachines'], SP.paint_machines, TEX, size=1024, ao_min=0.40, ao_dist=0.5,
               rough=0.75, log=log, info=INFO['atlases'], ppm_cap=PPM,
               zone_scale={SK.Z_PAD: 0.6, SK.Z_DUST: 0.5, SK.Z_HOPIN: 0.6, SK.Z_LEVER: 1.5, SK.Z_VALVE: 1.5, SK.Z_BELT: 1.3})
    make_atlas('SkyStructures', groups['SkyStructures'], SP.paint_machines, TEX, size=1024, ao_min=0.40, ao_dist=0.5,
               rough=0.75, log=log, info=INFO['atlases'], ppm_cap=PPM,
               zone_scale={SK.Z_CONC: 0.6, SK.Z_PAD: 0.6, SK.Z_DECKUND: 0.5, SK.Z_BOARD: 0.7, SK.Z_LEVER: 1.5, SK.Z_BLOCK: 1.2,
                           SK.Z_BHID: 0.04, SK.Z_PIT: 0.3})
    make_atlas('SkyWalk', groups['SkyWalk'], SP.paint_walk, TEX, size=1024, ao_min=0.40, ao_dist=0.3, rough=0.75,
               log=log, info=INFO['atlases'], ppm_cap=PPM, zone_scale={SK.Z_WLAMP: 1.5, SK.Z_WPLATE: 1.5})

# ------------------------------------------------------------------ 3. explicit materials
m_panel = P.psx_material('M_Sky_Panel', TP['Panel_BaseColor'], rough=0.6)


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


def grating_mat(name, img_path):
    """the grating: point-filtered, alpha cut-out, both faces"""
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
    pb.inputs['Roughness'].default_value = 0.7
    try:
        m.surface_render_method = 'DITHERED'
    except Exception:
        pass
    m.use_backface_culling = False
    return m


MATS = {'panel': m_panel, 'grating': grating_mat('M_Sky_Grating', TP['Grating_BaseColor'])}
for key, nm, off_rgb, on_rgb, st in (('lamp', 'Lamp', (176, 170, 150), (255, 214, 150), 6.0),
                                     ('amber', 'Amber', (150, 92, 30), (255, 150, 40), 8.0),
                                     ('red', 'Red', (120, 30, 24), (255, 40, 24), 8.0),
                                     ('green', 'Green', (30, 90, 40), (60, 255, 90), 6.0)):
    MATS[key] = flat_mat(f'M_Sky_{nm}_Off', off_rgb, rough=0.3)
    flat_mat(f'M_Sky_{nm}', on_rgb, on_rgb, st, 0.3, fake=True)
for name, o in objs.items():
    a = K.ATLAS[name]
    if a in BAKED:
        continue
    o.data.materials.clear()
    o.data.materials.append(MATS[a] if not DRAFT or a in MATS else MATS['panel'])
    o.hide_render = False

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
log('merged', len(SK.MERGE), 'faces into their bodies')

# ------------------------------------------------------------------ 4. hierarchy (world transforms kept)
for name, p in C['parts'].items():
    if name in objs and p.get('parent') and p['parent'] in objs:
        attach(objs[name], objs[p['parent']])
    p['object'] = name if name in objs else None
    p['root'] = SK.ROOT_OF.get(name, name)
    if name in SK.MASS:
        p['mass_kg'] = SK.MASS[name]
    if p.get('target_pos'):
        p['target_posUnity'] = to_unity(p['target_pos'])


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


def add_box(name, par, lo_hi, rot=None):
    x0, x1, y0, y1, z0, z1 = lo_hi
    root = SK.ROOT_OF[par]
    off = DISPLAY[root]
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
    ent = dict(name=ob.name, parent=par, root=root, type='box', center=r4(lc), size=r4(size), center_root=r4(c),
               centerUnity=to_unity(lc), sizeUnity=r4((size.x, size.z, size.y)))
    if rot:
        ent['rotation'] = [float(a) for a in rot]
        ent['rotationUnity'] = [float(rot[0]), -float(rot[2]), float(rot[1])]
    C['colliders'].append(ent)


for name, par, lo_hi, rot in SK.BOXES:
    add_box(name, par, lo_hi, rot)
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
for name, par, pos, d, kind, colr, rng, beh in SK.LIGHTS:
    ent = dict(name=name, parent=par, root=SK.ROOT_OF[par], type=kind, pos=r4(pos), posUnity=to_unity(pos),
               color_linear=list(colr), range=rng, behaviour=beh, default='off')
    if d is not None:
        ent['dir'] = r4(d)
        ent['dirUnity'] = to_unity(d)
        ent['spot_angle'] = 100
    lights.append(ent)
json.dump(_nz(dict(lights=lights)), open(os.path.join(OUT, 'sky_lights.json'), 'w'), indent=1)
for k, p in C['parts'].items():
    p['pivotUnity'] = to_unity(p['pivot'])
    if p.get('axis'):
        p['axisUnity'] = to_unity(p['axis'])
for s in C['sockets'].values():
    s['posUnity'] = to_unity(s['pos'])
    for key in ('dir', 'up', 'forward'):
        if s.get(key):
            s[key + 'Unity'] = to_unity(s[key])
    if s.get('rot_deg') is not None:
        s['yawUnity'] = -float(s['rot_deg'])
tris, tris_root = 0, {}
for o in bpy.data.objects:
    if o.type != 'MESH' or o.name.startswith('COL_'):
        continue
    t = sum(len(pl.vertices) - 2 for pl in o.data.polygons)
    tris += t
    tris_root[o.get('root', '?')] = tris_root.get(o.get('root', '?'), 0) + t
INFO['tris'] = tris
INFO['tris_by_root'] = tris_root
INFO['objects'] = {r: sorted(o.name for o in colls[r].objects) for r in ROOTS}
INFO['display_offset'] = {r: r4(DISPLAY[r]) for r in ROOTS}
INFO['mass_kg'] = SK.MASS
C['meta'] = dict(version='1.0', units='metres, degrees, kg',
                 frame='each root in its own frame: z up, the front -y; the machines: origin on the ground under the pad\'s '
                       'middle (SkyBallast: in the middle of the edge line, the drop at -y); the walkway modules: origin on the '
                       'deck at the module\'s start (SkyWalk_Ladder: at its top, SkyWalk_Cable: its lower end, SkyWalk_Anchor: '
                       'the plate\'s back). Every pivot / pos here is in its root\'s frame. In sky.blend the roots stand apart '
                       '(display_offset); their FBX is exported with the root at the origin',
                 unity='position (x, y, z) -> Unity (-x, z, -y) in the prefab; axis likewise; angle -> -angle (Unity is '
                       'left-handed); box centre likewise, size (sx, sy, sz) -> (sx, sz, sy); Euler XYZ (x, y, z) -> Unity '
                       '(x, -z, y); a socket\'s rot_deg about z -> yawUnity about Y; the root\'s front (-y) is the prefab\'s +Z',
                 display_offset=INFO['display_offset'],
                 assembly='the walkway: each module\'s origin on the previous one\'s *_End (SkyWalk_Turn: turned by its '
                          'yawUnity); SkyWalk_Cable from every Hang_* socket up to a SkyWalk_Anchor on the rock (scale its z to '
                          'the length); SkyWalk_Lamp on a railing post every ~12 m',
                 colliders='BoxCollider per entry on its parent (center / size in the parent\'s own frame, optional rotation). '
                           'The COL_ objects are in the .blend for reference (collection Colliders), not in the FBX',
                 lights='sky_lights.json: the chiller\'s and the ballast\'s amber beacons, the board\'s two floodlights and its '
                        'red obstruction light, the walkway lamp (all off in the file)',
                 model='sky.blend', textures='tex',
                 materials='M_Sky_SkyMachines / M_Sky_SkyStructures / M_Sky_SkyWalk: baked PSX atlases (point filter); '
                           'M_Sky_Panel: the control '
                           'panels, signs and the altitude board\'s face; M_Sky_Grating: the walkways\' and the sprayer '
                           'platform\'s grating, alpha cut-out, Render Face Both, box-mapped (UV 1 = 0.5 m, the 64 px tile '
                           'repeats); M_Sky_Lamp / _Amber / _Red / _Green with their _Off: the glasses lit / off (lit kept by a '
                           'fake user; the file has all off)',
                 names='the interactive parts IX_*; Unity numbers the copies when it places them')
sfx = '_draft' if DRAFT else ''
for o in bpy.data.objects:
    if o.name.startswith('COL_'):
        o.hide_set(True)
json.dump(_nz(C), open(os.path.join(OUT, f'sky_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
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
json.dump(_nz(INFO), open(os.path.join(OUT, f'sky{sfx}.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'sky{sfx}.blend'), relative_remap=False)
log('saved', f'sky{sfx}.blend')
