"""KPP v2 as it would stand in the game: the Update 7 game scene (fence/game/u7_game.blend: Update 3's location with the
models of Updates 4-6, the base drawn in, the checkpoint moved, the U7 kit placed) with the v1 Checkpoint / Barrier / Gate
swapped for v2 (out/kpp.blend with its snow_kit instances and the wire previews), the Update 7 records at the gate and the
barrier from walls_v2 (u7_layout_v2.json) and the ground levelled along them (levelling.json). Cycles.
python3 -I kpp2_game.py -- <out_dir> [spp] [views|all] [--save x.blend]"""
import bpy, sys, os, json, math
sys.path.insert(0, '/home/claude/uaz')
import numpy as np
from mathutils import Matrix, Vector, Quaternion
import psxlib as P
import kpp2_frame as KF

a = sys.argv[sys.argv.index('--') + 1:]
SAVE = a[a.index('--save') + 1] if '--save' in a else None
a = [x for i, x in enumerate(a) if x != '--save' and (i == 0 or a[i - 1] != '--save')]
OUT = a[0]
SPP = int(a[1]) if len(a) > 1 else 24
ONLY = set(a[2].split(',')) if len(a) > 2 and a[2] != 'all' else None
os.makedirs(OUT, exist_ok=True)
HERE = '/home/claude/uaz'
bpy.ops.wm.open_mainfile(filepath='/home/claude/fence/game/u7_game.blend')
sc = bpy.context.scene
PCTEX = '/home/claude/pcstage/locations/_blend/textures'
for im in bpy.data.images:
    if im.source == 'FILE' and im.packed_file is None and not os.path.exists(bpy.path.abspath(im.filepath)):
        alt = os.path.join(PCTEX, os.path.basename(bpy.path.abspath(im.filepath)))
        if os.path.exists(alt):
            im.filepath = alt
            im.reload()
Cm = Matrix(((-1, 0, 0), (0, 0, -1), (0, 1, 0)))          # Unity -> this map's Blender: (x, y, z) -> (-x, -z, y)
Ci = Cm.transposed()
A_U = Matrix(((-1, 0, 0), (0, 0, 1), (0, -1, 0)))          # a package frame (Blender, z up) -> Unity prefab-local


def u2b(p, q):
    R = Quaternion((q[3], q[0], q[1], q[2])).to_matrix()
    M = (Cm @ R @ Ci).to_4x4()
    M.translation = Cm @ Vector(p)
    return M


def frame_to_map(pos_u, yaw_u):
    """4x4: a package root's frame (Blender z up, at its own origin) -> this map, for a root at Unity pos_u with yaw_u"""
    a_ = math.radians(yaw_u)
    Ry = Matrix(((math.cos(a_), 0, math.sin(a_)), (0, 1, 0), (-math.sin(a_), 0, math.cos(a_))))
    M = (Cm @ Ry @ A_U).to_4x4()
    M.translation = Cm @ Vector(pos_u)
    return M


# ---------------------------------------------------------------- 1. v1 out, v2 in
for nm in ('Checkpoint_u46', 'Barrier_u46', 'Gate_u46'):
    o = bpy.data.objects.get(nm)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)
# the v1 package's own data (Checkpoint, Gate, LIGHT_Fluor, M_Kpp_* ...) is still in this file behind the instances: renamed
# '<name>_v1' so that v2 comes in under its own names (an appended 'Gate' would turn into 'Gate.001')
KPP_BLEND = os.path.join(HERE, 'out', 'kpp.blend')
with bpy.data.libraries.load(KPP_BLEND, link=True) as (src, dst):
    v2names = {a: set(getattr(src, a)) for a in ('objects', 'meshes', 'materials', 'images', 'lights', 'collections',
                                                   'node_groups', 'cameras', 'curves')}
nren = 0
for a, ns in v2names.items():
    for idb in list(getattr(bpy.data, a)):
        if idb.library is None and idb.name in ns:
            idb.name = idb.name + '_v1'
            nren += 1
print('v1 data renamed', nren, flush=True)
with bpy.data.libraries.load(KPP_BLEND, link=False) as (src, dst):
    onames = [str(n) for n in src.objects]
    dst.objects = list(onames)          # (Blender swaps this list's names for the objects in place)
v2 = bpy.data.collections.new('KPP v2')
sc.collection.children.link(v2)
objs = {n: o for n, o in zip(onames, dst.objects) if o is not None}
bad = [(n, o.name) for n, o in objs.items() if o.name != n]
print('v2 objects renamed on append:', bad[:10], flush=True)
for o in objs.values():
    v2.objects.link(o)
C = json.load(open(os.path.join(HERE, 'out', 'kpp_contract.json')))
gp = C['meta']['game_placement']
M_kpp = frame_to_map(gp['Checkpoint']['p'], gp['Checkpoint']['yawUnity'])
M_gate = frame_to_map(gp['Gate']['p'], gp['Gate']['yawUnity']) @ Matrix.Translation(-Vector((11.0, 0.0, -0.3772)))
ek, eg = bpy.data.objects.new('KPP_v2_frame', None), bpy.data.objects.new('Gate_v2_frame', None)
for e, M in ((ek, M_kpp), (eg, M_gate)):
    v2.objects.link(e)
    e.matrix_world = M


def root_of(o):
    while o.parent is not None:
        o = o.parent
    return o


for r, o in list(objs.items()):
    if o.parent is not None:
        continue
    if r == 'Barrier_Manual' or r.startswith('COL_'):
        for d in [o] + list(o.children_recursive):
            d.hide_render = True
            d.hide_viewport = True
        continue
    if o.name.startswith('qcam'):
        continue
    par = eg if r == 'Gate' else ek
    o.parent = par
    o.matrix_parent_inverse = Matrix.Identity(4)
for o in objs.values():
    if o.name.startswith('COL_'):
        o.hide_render = True
for coll_ in (bpy.data.collections, bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.node_groups):
    for idb in list(coll_):
        if idb.library is not None:
            try:
                idb.make_local()
            except Exception as ex:
                print('make_local', idb.name, ex)
import kit_preview as KP                                  # 2.1: the gate monitor shows the gate camera's stand-in (CAM 2)
if 'Monitor_Gate' in objs and objs['Monitor_Gate'].instance_collection is not None:
    KP.screen_variant(objs['Monitor_Gate'], os.path.join(HERE, 'tex', 'snow_kit', 'T_Kit_Screen_On_Gate.png'), 'Gate')
print('KPP v2 in:', len(objs), 'objects; libraries left:', [l.filepath for l in bpy.data.libraries], flush=True)
bpy.context.view_layer.update()

# ---------------------------------------------------------------- 2. the walls from walls_v2, the new record
U = json.load(open(os.path.join(HERE, 'walls_v2', 'u7_layout_v2.json')))
u7c = bpy.data.collections['Update 7 (fences, blocks)']
ents = {}
for o in u7c.objects:
    k = int(o.name.rsplit('_', 1)[1])
    ents[k] = o
lib = {c.name: c for c in bpy.data.collections['Library_U7'].children}
nnew = nmodel = 0
for k, r in enumerate(U['records']):
    e = ents.get(k)
    if e is None:
        e = bpy.data.objects.new('%s_u7_%03d' % (r['m'], k), None)
        e.instance_type = 'COLLECTION'
        u7c.objects.link(e)
        nnew += 1
    if e.instance_collection is not lib[r['m']]:      # the game scene was built from an earlier U7 list (teeth / abatis swaps)
        e.instance_collection = lib[r['m']]
        nmodel += 1
    e.matrix_world = u2b(r['p'], r['q'])
print('U7 records', len(U['records']), 'new', nnew, 'model fixed', nmodel, flush=True)

# ---------------------------------------------------------------- 3. the ground levelled along the walls (levelling.json)
LV = json.load(open(os.path.join(HERE, 'walls_v2', 'levelling.json')))


def ss(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


nv = 0
for o in [o for o in bpy.data.objects if o.name.startswith('Terrain_') and o.type == 'MESH']:
    me = o.data
    M = o.matrix_world
    Mi = M.inverted()
    co = np.array([tuple(M @ v.co) for v in me.vertices])
    xu, zu, yu = -co[:, 0], -co[:, 1], co[:, 2]
    changed = np.zeros(len(co), bool)
    for s in LV['strips']:
        (ax, az), (bx, bz) = s['line']
        d = np.array([bx - ax, bz - az])
        L = np.linalg.norm(d)
        d /= L
        rel = np.stack([xu - ax, zu - az], 1)
        sa = rel @ d
        t = np.abs(rel @ np.array([-d[1], d[0]]))
        w_ac = np.where(t <= s['half_width'], 1.0, ss((s['half_width'] + s['falloff'] - t) / s['falloff']))
        w_al = np.where(sa < 0, np.clip(1 + sa / s['ramp_start'], 0, 1), np.where(sa > L, np.clip(1 - (sa - L) / s['ramp_end'], 0, 1), 1.0))
        w = w_ac * w_al
        m = w > 1e-4
        yu = np.where(m, yu + w * (s['height'] - yu), yu)
        changed |= m
    if changed.any():
        for i in np.nonzero(changed)[0]:
            p = Vector((co[i, 0], co[i, 1], yu[i]))
            me.vertices[i].co = Mi @ p
        me.update()
        nv += int(changed.sum())
print('terrain vertices levelled', nv, flush=True)

# ---------------------------------------------------------------- 4. light, render, the lamps for the night view
for o in list(sc.objects):
    if o.type == 'LIGHT' and o.data.type == 'SUN':
        o.hide_render = True
P.setup_cycles((1280, 720), SPP)
sc.cycles.max_bounces = 3
sc.render.use_persistent_data = True
for m in bpy.data.materials:
    if m.node_tree and m.library is None:
        for n_ in m.node_tree.nodes:
            if n_.type == 'TEX_IMAGE':
                n_.interpolation = 'Closest'
if SAVE:
    bpy.ops.wm.save_as_mainfile(filepath=SAVE, compress=True)


def W(p_booth):
    """a booth-frame point -> this map"""
    return M_kpp @ Vector(p_booth)


def WG(p_gate):
    return M_gate @ (Vector(p_gate) + Vector((11.0, 0.0, -0.3772)))


def sock(name):
    s = C['sockets'][name]
    root = s['parent']
    M = M_gate if root == 'Gate' else M_kpp
    return M @ Vector(s['pos']), (M.to_3x3() @ Vector(s['dir'])).normalized()


cb, cbd = sock('CAM_Barrier')
cg, cgd = sock('CAM_Gate')
VIEWS = {   # name: (eye, target, lens, night)
    'approach': (W((7.0, -40.0, 1.9)), W((4.0, -4.0, 1.0)), 34.0, False),
    'kpp_side': (W((9.5, -11.0, 2.2)), W((1.8, -4.5, 0.9)), 26.0, False),
    'kpp_back': (W((-6.5, 7.5, 3.0)), W((-0.8, 2.0, 2.0)), 26.0, False),
    'kpp_air': (W((22.0, -26.0, 24.0)), W((0.0, 8.0, 0.0)), 28.0, False),
    'inside': (W((0.15, 0.95, 1.70)), W((1.35, -1.05, 0.95)), 20.0, False),
    'inside_power': (W((0.15, 0.95, 1.70)), W((1.35, -1.05, 0.95)), 20.0, 'day_power'),
    'gate_out': (WG((-3.5, -16.0, 2.0)), WG((-3.0, 0.0, 1.2)), 30.0, False),
    'gate_in': (WG((5.5, 7.5, 3.0)), WG((-1.5, 0.6, 1.0)), 26.0, False),
    'cam_barrier': (cb, cb + cbd, 26.0, False),
    'cam_gate': (cg, cg + cgd, 26.0, False),
    'cam_barrier_night': (cb, cb + cbd, 26.0, True),
    'mast_barrier': (W((4.6, -2.6, 1.75)), W((1.5, -5.5, 1.75)), 18.0, False),
    'night_power': (W((8.0, -9.5, 2.0)), W((0.8, -1.0, 1.4)), 26.0, True),
}
# the Update 7 preview's cameras (fence/u7_preview.py): the same views as the U7 game renders, for v1 -> v2
B = json.load(open('/home/claude/fence/map_big.json'))
from scipy.interpolate import LinearNDInterpolator
_T = np.array(B['terrain'])
_g = LinearNDInterpolator(_T[:, [0, 2]], _T[:, 1])
Bk = U['barrier']
BP, REST, RIN = np.array(Bk['post']), np.array(Bk['rest']), np.array(Bk['road_in'])
ARM = (REST - BP) / np.linalg.norm(REST - BP)
RD = np.array(json.load(open('/home/claude/fence/map_forest.json'))['road'])
RD = RD[np.hypot(RD[:, 0] - BP[0], RD[:, 2] - BP[1]) < 70]


def road_mid(a_):
    rel = RD[:, [0, 2]] - BP
    s_ = np.abs(rel @ RIN - a_) < 2.5
    c = rel[s_] @ ARM
    return (c.min() + c.max()) / 2


def kppu(a_, c_, h):
    p = BP + RIN * a_ + ARM * c_
    return Cm @ Vector((p[0], float(_g(*p)) + h, p[1]))


def atu(p2, h):
    return Cm @ Vector((p2[0], float(_g(*p2)) + h, p2[1]))


Gk = U['gate']
GP = np.array(Gk['game'])[[0, 2]]
GX = (np.array(Gk['east_end']) - np.array(Gk['west_end'])) / np.linalg.norm(np.array(Gk['east_end']) - np.array(Gk['west_end']))
gn = np.array([GX[1], -GX[0]])
gout = gn if gn @ (GP - np.array([340.0, -360.0])) > 0 else -gn
VIEWS.update({
    'u7_kpp_driver': (kppu(-46.0, road_mid(-46.0), 1.9), kppu(0.0, 2.8, 1.0), 34.0, False),
    'u7_kpp_air': (kppu(-34.0, road_mid(-34.0) - 4.0, 30.0), kppu(2.0, 3.0, 0.0), 30.0, False),
    'u7_gate': (atu(GP + GX * 3.5 + gout * 22.0, 2.4), atu(GP + GX * 3.5, 1.2), 30.0, False),
})
cam = bpy.data.objects.new('cam_v2', bpy.data.cameras.new('cam_v2'))
sc.collection.objects.link(cam)
sc.camera = cam
night_objs = []
sun_obj = None
swapped = []                      # (mesh data, slot, the material before) - the power state is put back for the day views


def power(on):
    """the lit lens / screen materials on (with the booth's power) or back to what they were"""
    global swapped
    if on and not swapped:
        for o in bpy.data.objects:                         # the off lenses -> the lit materials
            if o.type == 'MESH' and o.data.materials:
                for i, ms in enumerate(o.data.materials):
                    if ms and ms.name.endswith('_Off'):
                        lit = bpy.data.materials.get(ms.name[:-4])
                        if lit:
                            swapped.append((o.data, i, ms))
                            o.data.materials[i] = lit
        scr_on = bpy.data.materials.get('M_Kit_Screen_On')
        if scr_on:
            for o in bpy.data.objects:
                want = bpy.data.materials.get(o.get('screen_on', 'M_Kit_Screen_On')) or scr_on
                if o.type == 'MESH' and o.name.startswith('Kit_Monitor_Screen') and o.data.materials[0] is not want:
                    swapped.append((o.data, 0, o.data.materials[0]))
                    o.data.materials[0] = want
            pb = next((n_ for n_ in scr_on.node_tree.nodes if n_.type == 'BSDF_PRINCIPLED'), None)
            if pb is not None:
                pb.inputs['Emission Strength'].default_value = 1.8
        for m in bpy.data.materials:                      # lit lenses: their emission on
            if m.node_tree is None:
                continue
            pb = next((n_ for n_ in m.node_tree.nodes if n_.type == 'BSDF_PRINCIPLED'), None)
            if pb is not None and m.get('night_emit') and not m.name.endswith('_Off'):
                pb.inputs['Emission Strength'].default_value = float(m['night_emit'])
    elif not on and swapped:
        for data, i, ms in reversed(swapped):
            data.materials[i] = ms
        swapped = []


def night(mode):
    """False: day, no power; True: night with the booth's power (dark sky, its lamps as point lights, lit lenses and
    screens); 'day_power': day with the power. Day: one sun (psxlib.sun makes a new one on every call - the previous one
    goes first, or the suns pile up view after view)"""
    global night_objs, sun_obj
    for o in night_objs:
        bpy.data.objects.remove(o, do_unlink=True)
    night_objs = []
    if sun_obj is not None:
        bpy.data.objects.remove(sun_obj, do_unlink=True)
        sun_obj = None
    if mode is True:
        P.world((0.010, 0.012, 0.022), 0.25)
    else:
        P.world((0.55, 0.62, 0.74), 1.0)
        sun_obj = P.sun(4.2, (38, 0, 200))
    if mode is True:                     # v2.1: the masts' floodlights (kit instances; their light in snow_kit_lights.json)
        KL = {lt['item']: lt for lt in json.load(open(os.path.join(HERE, 'out', 'snow_kit_lights.json')))['lights']}
        for nm_, ki in C['kit_instances'].items():
            lt = KL.get(ki['item'])
            if lt is None or lt['type'] != 'flood' or nm_ not in objs:
                continue
            Mi = objs[nm_].matrix_world
            ld = bpy.data.lights.new('N_' + nm_, 'SPOT')
            ld.energy = 650.0
            ld.spot_size = math.radians(lt['spotAngle'])
            ld.spot_blend = 0.55
            ld.color = tuple(min(1.0, c) for c in lt['colorLinear'])
            ld.shadow_soft_size = 0.05
            lo = bpy.data.objects.new('N_' + nm_, ld)
            sc.collection.objects.link(lo)
            lo.location = Mi @ Vector(lt['position'])
            lo.rotation_euler = (Mi.to_3x3() @ Vector(lt['forward'])).normalized().to_track_quat('-Z', 'Y').to_euler()
            night_objs.append(lo)
    if mode:
        LJ = json.load(open(os.path.join(HERE, 'out', 'kpp_lights.json')))['lights']
        for lt in LJ:
            ld = bpy.data.lights.new('N_' + lt['socket'], 'POINT')
            ld.energy = 60.0 if lt['type'] == 'fluor' else 40.0
            ld.color = tuple(min(1.0, c) for c in lt['colorLinear'])
            ld.shadow_soft_size = 0.05
            lo = bpy.data.objects.new('N_' + lt['socket'], ld)
            sc.collection.objects.link(lo)
            lo.location = W(lt['position'])
            night_objs.append(lo)
    power(bool(mode))


for nm, (eye, tgt, lens, nt) in VIEWS.items():
    if ONLY and nm not in ONLY:
        continue
    night(nt)
    cam.location = eye
    cam.rotation_euler = (tgt - eye).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.03 if nm in ('inside', 'inside_power', 'cam_barrier', 'cam_gate', 'cam_barrier_night') else 0.1
    cam.data.clip_end = 900
    sc.render.filepath = os.path.join(OUT, nm + '.png')
    bpy.ops.render.render(write_still=True)
    print('rendered', nm, flush=True)
