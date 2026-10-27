"""forest_devices build (devices_kit): one object per part with its pivot as the origin, each root in its own collection and
standing at devices_kit.DISPLAY in the file (the contract gives everything in the root's own frame); the label / key-field /
plate faces (panel atlas) joined into their bodies as a second material; PSX atlases baked with psxbake + devices_paint:
Devices (the desk things, 512 px at 256 px/m) and Outdoor (the drop box, the weather screen; 512 px at 128 px/m); explicit
materials: the panel, the LEDs lit / off, the fax LCD lit / off, the laptop screen, the fax paper, the recorder's window glass;
the snow_kit monitor linked from ../snow_kit/snow_kit.blend as an instance on the computer; the interaction contract (parts,
sockets, colliders, kit_instances, placements in forest_far, meta).
python3 -I devices_build.py [--draft] -> out/devices.blend, out/devices.json, out/devices_contract.json, tex/devices/*
--draft: no bakes, flat zone colours -> out/devices_draft.blend"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import psxlib as P
import psxbake as PB
import devices_tex as DT
import gen_kit as K
import devices_kit as DK

DRAFT = '--draft' in sys.argv
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'devices')
OUT = os.path.join(HERE, 'out')
KIT_BLEND = os.path.join(HERE, 'snow_kit', 'snow_kit.blend')     # -> ../snow_kit/snow_kit.blend from the package's devices.blend
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
PB.POS_SCALE = 8.0                                    # bake range +-4 m: the roots stand from x -2.2 to 2.4
DESK_PPM, BOX_PPM = 256.0, 128.0


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
PB_BASE, PB_EMI, PAPER, TILES = DT.build(TEX)

# ------------------------------------------------------------------ 1. geometry
DK.build_devices()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts'] and n not in DK.MERGE]
assert not missing, f'objects without a contract entry: {missing}'
colls = {}
for root in DK.ROOTS:
    colls[root] = bpy.data.collections.new(root)
    colls[root].instance_offset = DK.DISPLAY[root]            # linked as a collection instance, the root lands on the empty
    bpy.context.scene.collection.children.link(colls[root])
objs = {}
for name, k in K.KBS.items():
    root = DK.ROOT_OF[name]
    off = DK.DISPLAY[root]
    K.transform_kb(k, Matrix.Translation(off))
    p = C['parts'][DK.MERGE.get(name, name)]
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
import devices_paint as DPT
lid, screen = objs['IX_LaptopLid'], objs['Laptop_Screen']
attach(screen, lid)
lid.rotation_euler = (math.radians(-100.0), 0.0, 0.0)      # baked with the lid open: no closed-lid AO on the palm rest / bezel
sdoor = objs['IX_ScreenDoor']
sdoor.rotation_euler = (0.0, 0.0, math.radians(-100.0))   # and the screen's door open: daylight in the box
bpy.context.view_layer.update()
if DRAFT:
    cache = {}

    def zmat(z):
        if z not in cache:
            m = bpy.data.materials.new(f'draft_{z}')
            m.use_nodes = True
            pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            c = PB.lin(*DPT.DRAFT_COL.get(z, (128, 128, 128)))
            pb.inputs['Base Color'].default_value = (float(c[0]), float(c[1]), float(c[2]), 1)
            pb.inputs['Roughness'].default_value = 0.75
            m.diffuse_color = (float(c[0]), float(c[1]), float(c[2]), 1)
            cache[z] = m
        return cache[z]

    for name, o in objs.items():
        if K.ATLAS[name] not in ('Devices', 'Outdoor'):
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
    PB.make_atlas('Devices', groups['Devices'], DPT.paint_devices, TEX, prefix='T_Dev_', mat_prefix='M_Dev_', size=512,
                  ao_min=0.45, ao_dist=0.05, rough=0.6, log=log, info=INFO['atlases'], ppm_cap=DESK_PPM,
                  prio_zones=(DK.Z_TAPE,))
    PB.make_atlas('Outdoor', groups['Outdoor'], DPT.paint_outdoor, TEX, prefix='T_Dev_', mat_prefix='M_Dev_', size=512,
                  ao_min=0.40, ao_dist=0.25, rough=0.7, log=log, info=INFO['atlases'], ppm_cap=BOX_PPM,
                  prio_zones=(DK.Z_SLOT, DK.Z_SCRBLACK))
lid.rotation_euler = (0.0, 0.0, 0.0)
sdoor.rotation_euler = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 3. explicit materials
m_panel = PB.tex_mat('M_Dev_Panel', PB_BASE, PB_EMI, 0.0, rough=0.6)
lens_mats = {}
for kind, mname in (('led_g', 'M_Dev_LEDG'), ('led_r', 'M_Dev_LEDR')):
    for sfx, e in (('', 2.0), ('_Off', 0.0)):
        m = PB.tex_mat(mname + sfx, PB_BASE, PB_EMI, e, rough=0.25)
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        pb.inputs['Emission Strength'].default_value = e        # an LED glows by day too
        m['lamp_kind'] = kind
        m.use_fake_user = bool(sfx)                              # the 'off' variants are on no mesh: keep them in the file
        lens_mats[kind + sfx] = m
m_lcd = PB.tex_mat('M_Dev_FaxLCD', TILES['FaxLCD_BaseColor'], TILES['FaxLCD_Emission'], 1.0, rough=0.3)
next(n for n in m_lcd.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Emission Strength'].default_value = 1.0
m_lcd_off = bpy.data.materials.new('M_Dev_FaxLCD_Off')
m_lcd_off.use_nodes = True
pb = next(n for n in m_lcd_off.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
pb.inputs['Base Color'].default_value = tuple(float(a) for a in PB.lin(70, 86, 64)) + (1.0,)
pb.inputs['Roughness'].default_value = 0.3
m_lcd_off.use_fake_user = True
m_screen = P.psx_material('M_Dev_ScreenOff', TILES['ScreenOff_BaseColor'], rough=0.15, spec=0.5)
m_paper = P.psx_material('M_Dev_FaxPaper', PAPER, rough=0.85)
m_glass = P.psx_glass('M_Dev_Glass', tint=(0.10, 0.10, 0.11), alpha=0.50)
for name, o in objs.items():
    a = K.ATLAS[name]
    if a in ('Devices', 'Outdoor'):
        continue
    o.data.materials.clear()
    if a == 'panel':
        o.data.materials.append(m_panel)
    elif a.startswith('lens:'):
        o.data.materials.append(lens_mats[a[5:]])
        o['lamp_kind'] = a[5:]
    elif a == 'lcd':
        o.data.materials.append(m_lcd)
    elif a == 'screen':
        o.data.materials.append(m_screen)
    elif a == 'paper':
        o.data.materials.append(m_paper)
    elif a == 'glass':
        o.data.materials.append(m_glass)
    else:
        raise ValueError(a)

# ------------------------------------------------------------------ 3b. the panel faces join their bodies (second material slot)
for name, dst in DK.MERGE.items():
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
log('merged', len(DK.MERGE), 'panel faces into their bodies')

# ------------------------------------------------------------------ 4. hierarchy (world transforms kept)
for name, p in C['parts'].items():
    if name in objs and p.get('parent') and p['parent'] in objs:
        attach(objs[name], objs[p['parent']])
    p['object'] = name if name in objs else None
    p['root'] = DK.ROOT_OF.get(name, name)


def root_of_part(name):
    while C['parts'][name].get('parent'):
        name = C['parts'][name]['parent']
    return name


for s in C['sockets'].values():
    s['root'] = root_of_part(s['parent']) if s.get('parent') in C['parts'] else s.get('parent')

# ------------------------------------------------------------------ 4b. the snow_kit monitor (a collection linked from the kit)
A_U = Matrix(((-1, 0, 0), (0, 0, 1), (0, -1, 0)))           # Blender -> Unity axes


def rot_unity(R3):
    q = (A_U @ R3 @ A_U.transposed()).to_quaternion()
    return [round(q.x, 6) + 0.0, round(q.y, 6) + 0.0, round(q.z, 6) + 0.0, round(q.w, 6) + 0.0]


items = sorted({ki['item'] for ki in DK.KIT_INST.values()})
with bpy.data.libraries.load(KIT_BLEND, link=True) as (src, dst):
    dst.collections = [c for c in src.collections if c in items]
kcoll = {c.name: c for c in dst.collections}
assert set(kcoll) == set(items), set(items) - set(kcoll)
inst_coll = bpy.data.collections.new('Kit_Instances')
bpy.context.scene.collection.children.link(inst_coll)
C['kit_instances'] = {}
for name, ki in DK.KIT_INST.items():
    root = DK.ROOT_OF[ki['parent']]
    e = bpy.data.objects.new(name, None)
    inst_coll.objects.link(e)
    e.instance_type = 'COLLECTION'
    e.instance_collection = kcoll[ki['item']]
    e.empty_display_type, e.empty_display_size = 'PLAIN_AXES', 0.04
    e.matrix_world = Matrix.Translation(ki['pos'] + DK.DISPLAY[root])
    e['kit_item'] = ki['item']
    e['note'] = ki['note']
    attach(e, objs[ki['parent']])
    piv = Vector(C['parts'][ki['parent']]['pivot'])
    lp = ki['pos'] - piv
    C['kit_instances'][name] = dict(item=ki['item'], parent=ki['parent'], root=root, note=ki['note'], ix_ids={},
                                    pos=r4(lp), rot_quat_wxyz=[1.0, 0.0, 0.0, 0.0], scale=[1.0, 1.0, 1.0],
                                    posUnity=to_unity(lp), rotUnity_xyzw=rot_unity(Matrix.Identity(3)),
                                    scaleUnity=[1.0, 1.0, 1.0], pos_root=r4(ki['pos']))
log('kit instances', list(C['kit_instances']))
C['placements'] = {}
for root, lst in DK.PLACEMENTS.items():
    out = []
    for pl in lst:
        R3 = Matrix.Rotation(math.radians(pl['yaw']), 3, 'Z')
        q = R3.to_quaternion()
        out.append(dict(parent=pl['parent'], package=pl['package'], note=pl['note'], pos=r4(pl['pos']), yaw=pl['yaw'],
                        rot_quat_wxyz=[round(q.w, 6) + 0.0, round(q.x, 6) + 0.0, round(q.y, 6) + 0.0, round(q.z, 6) + 0.0],
                        posUnity=to_unity(pl['pos']), rotUnity_xyzw=rot_unity(R3)))
    C['placements'][root] = out

# ------------------------------------------------------------------ 5. colliders (in each parent's own frame)
coll_c = bpy.data.collections.new('Colliders')
bpy.context.scene.collection.children.link(coll_c)
C['colliders'] = []
for name, par, (x0, x1, y0, y1, z0, z1), rot in DK.BOXES:
    root = DK.ROOT_OF[par]
    off = DK.DISPLAY[root]
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
    p['box'] = dict(center=r4((lo + hi) / 2), size=r4(np.maximum(hi - lo, 0.004)))

# ------------------------------------------------------------------ 7. Unity values, meta, stats, save
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
    if o.type != 'MESH' or o.name.startswith('COL_') or o.library is not None:
        continue
    t = sum(len(pl.vertices) - 2 for pl in o.data.polygons)
    tris += t
    tris_root[o.get('root', '?')] = tris_root.get(o.get('root', '?'), 0) + t
INFO['tris'] = tris
INFO['tris_by_root'] = tris_root
INFO['objects'] = {r: sorted(o.name for o in colls[r].objects) for r in DK.ROOTS}
INFO['display_offset'] = {r: r4(DK.DISPLAY[r]) for r in DK.ROOTS}
C['meta'] = dict(version='1.0', units='metres, degrees',
                 frame='each root (Fax, FaxPaper, Cassette, CassetteBox, DropBox, ObjectPC, Laptop, TapeDeck, MeteoScreen) in '
                       'its own frame: z up, the front -y; origin on the surface it stands on (z = 0) under its middle - the drop '
                       'box: the post on the ground; the cassette: its middle; the tape recorder: the middle of its back face. '
                       'Every pivot / pos here is in its root\'s frame. In devices.blend the roots stand apart (display_offset); '
                       'their FBX is exported with the root at the origin',
                 unity='position (x, y, z) -> Unity (-x, z, -y) in the prefab; axis likewise; angle -> -angle (Unity is left-handed); '
                       'box centre likewise, size (sx, sy, sz) -> (sx, sz, sy); the root\'s front (-y) is the prefab\'s +Z',
                 display_offset=INFO['display_offset'],
                 colliders='BoxCollider per entry on its parent: center / size in the parent\'s own frame (its pivot, no rotation), '
                           'centerUnity / sizeUnity the same in Unity axes; center_root: in the root\'s frame. The COL_ objects are '
                           'in the .blend for reference (collection Colliders), not in the FBX',
                 kit_instances='snow_kit models placed as instances (the computer\'s monitor): in devices.blend an empty showing '
                               'the collection linked from ../snow_kit/snow_kit.blend (props kit_item); in Unity put the kit\'s prefab '
                               '(Assets/Kit/Prefabs/<item>) under the parent with pos / rot (prefab frame) or posUnity / rotUnity_xyzw',
                 placements='where forest_far\'s prefabs take a model: under the parent (a forest_far root) at pos / yaw (the '
                            'parent\'s frame) or posUnity / rotUnity_xyzw - the tape recorder in each dish cabinet, the weather '
                            'screen on the weather station (forest_far 1.1)',
                 model='devices.blend', textures='tex',
                 materials='M_Dev_Devices (the desk things, the recorder) / M_Dev_Outdoor (the drop box, the screen): baked PSX '
                           'atlases (point filter); M_Dev_Panel: the labels, key fields, the fax panel, the recorder\'s faceplate, '
                           'the plate, the thermometer scales and the chart (second material on those bodies; the keys and buttons '
                           'are panel objects); M_Dev_LEDG / _Off, M_Dev_LEDR / _Off: lit / off; M_Dev_FaxLCD / _Off: the fax '
                           'display lit / off; M_Dev_ScreenOff: the laptop screen dark (the game puts its picture there); '
                           'M_Dev_FaxPaper: the received fax (the game prints on it); M_Dev_Glass: the recorder\'s window',
                 ix='IX_LaptopLid, IX_TapeDoor, IX_ScreenDoor - names without numbers: Unity numbers them when the prefab goes on '
                    'the map')
sfx = '_draft' if DRAFT else ''
for o in bpy.data.objects:
    if o.name.startswith('COL_') and o.library is None:
        o.hide_set(True)
json.dump(_nz(C), open(os.path.join(OUT, f'devices_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
kinds = {}
for p in C['parts'].values():
    kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
INFO['contract'] = dict(parts=len(C['parts']), sockets=len(C['sockets']), colliders=len(C['colliders']),
                        kit_instances=len(C['kit_instances']), placements={k: len(v) for k, v in C['placements'].items()},
                        kinds=kinds)
log('contract', INFO['contract'], 'tris', tris, tris_root)
for o in [o for o in bpy.data.objects if o.type == 'MESH' and o.library is None]:
    uvs = o.data.uv_layers
    if 'PSX' in uvs:
        for u in [u for u in uvs if u.name != 'PSX']:
            uvs.remove(u)
        uvs['PSX'].active = True
    if 'zone' in o.data.attributes and not DRAFT:
        o.data.attributes.remove(o.data.attributes['zone'])
for lib in bpy.data.libraries:                       # the kit is linked as ../snow_kit/snow_kit.blend (the package layout)
    lib.filepath = '//../snow_kit/snow_kit.blend'
json.dump(_nz(INFO), open(os.path.join(OUT, f'devices{sfx}.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'devices{sfx}.blend'), relative_remap=False)
log('saved', f'devices{sfx}.blend')
