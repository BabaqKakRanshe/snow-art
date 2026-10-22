"""Van v2 on the reassembled tiunov.se body (Sketchfab "Uaz", CC BY 4.0): an original expedition van, not a stock
UAZ-452 any more.  New front module, split windscreen, winch bumper + bull bar, roof rack + light bar, roof markers,
flares, rails, steps, ladder, bigger wheels + lift, red / white fleet livery (the plane's colours); dashboard in the
plane's panel language (pixel-font gauges, warning strip, switch plate, CB radio, heater), folding troop seats like
the plane's, light fixtures outside and inside (lens atlas + emission), cozy saloon kit.
Textures: the plane's PSX recipe (unique UVs, AO in the colour, 1-texel grooves, 64 colours, Bayer 4x4, point filter).
python3 -I van2_build.py   -> out/van2.blend, out/van2.json, tex/van2/*.png"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import psxlib as P
from noise import ss, lerp, mixc, fbm

HERE = P.HERE
LIVERY = 'fleet'
TEX = os.path.join(HERE, 'tex', 'van2')
os.makedirs(TEX, exist_ok=True)
T0 = time.time()
INFO = {}


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


def lin(*rgb):
    c = np.array(rgb, np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'work', 'uaz_fixed.blend'))
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
wheels = sorted([o for o in meshes if o.name.startswith('Wheel')], key=lambda o: o.name)
body_objs = [o for o in meshes if o not in wheels]


def mat_names(o):
    return [s.material.name if s.material else '' for s in o.material_slots]


def build_bvh(objs):
    V, F = [], []
    for o in objs:
        w = P.world_verts(o)
        base = len(V)
        V += [tuple(x) for x in w]
        F += [[base + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(V, F)


# ------------------------------------------------------------------ 1. lift the ceiling lining
# the lining is a thin panel (both faces 'rezina') under a crowned roof skin: lift each vertex by up to 14 cm,
# keeping its top 3.5 cm under the skin above it (the skin is found among the outward 'kuzov' faces only)
kz = bpy.data.objects['Kuzov']
names = mat_names(kz)
wv = P.world_verts(kz)
roofF = [list(p.vertices) for p in kz.data.polygons if names[p.material_index] == 'kuzov' and p.normal.z > 0.2]
bvh_roof = BVHTree.FromPolygons([tuple(x) for x in wv], roofF)
ceil_v = set()
for p in kz.data.polygons:
    if names[p.material_index] == 'rezina' and p.center.z > 1.755 and abs(p.center.y) < 0.95 and -2.12 < p.center.x < 2.0:
        ceil_v.update(p.vertices)
moved, lifts = 0, []
for vi in ceil_v:
    v = kz.data.vertices[vi]
    loc, nor, idx, dist = bvh_roof.ray_cast(Vector((v.co.x, v.co.y, 1.70)), Vector((0, 0, 1)), 1.0)
    if loc is None:
        continue
    top = v.co.z + (0.025 if v.normal.z < 0 else 0.0)
    lift = min(0.14, loc.z - 0.035 - top)
    if lift > 1e-4:
        v.co.z += lift
        moved += 1
        lifts.append(lift)
kz.data.update()
INFO['ceiling_lift_m'] = [round(float(np.min(lifts)), 3), round(float(np.median(lifts)), 3), round(float(np.max(lifts)), 3)] if lifts else []
log('ceiling vertices lifted', moved, 'of', len(ceil_v), 'lift min/med/max', INFO['ceiling_lift_m'])

# ------------------------------------------------------------------ 2. zones
Z_PAINT, Z_BLACK, Z_RUBBER, Z_HEAD, Z_HEAD2, Z_AMBER, Z_RED, Z_MIRROR, Z_RIM, Z_TYRE = range(1, 11)
Z_LINING, Z_DASH, Z_CUSHION, Z_FRAME, Z_CONTROL, Z_GLASS = range(11, 17)
import van2_kit as VK
import van2_tex as VT
import van2_props as VP
ATLAS_OF = {Z_PAINT: 'Body', Z_BLACK: 'Trim', Z_RUBBER: 'Trim', Z_HEAD: 'Trim', Z_HEAD2: 'Trim', Z_AMBER: 'Trim',
            Z_RED: 'Trim', Z_MIRROR: 'Trim', Z_RIM: 'Wheel', Z_TYRE: 'Wheel', Z_LINING: 'Cabin', Z_DASH: 'Cabin',
            Z_CONTROL: 'Cabin', Z_CUSHION: 'Seats', Z_FRAME: 'Seats', Z_GLASS: 'Glass',
            VK.Z_CHROME: 'Trim', VK.Z_PANEL: 'Trim', VK.Z_REDPAINT: 'Trim', VK.Z_SPARE: 'Trim',
            VK.Z_ORANGE: 'Trim', VK.Z_SPARERIM: 'Trim',
            VK.Z_DASHP: 'Cabin', VK.Z_DASHPAD: 'Cabin', VK.Z_DOMEBASE: 'Cabin',
            VK.Z_CANVAS: 'Seats', VK.Z_TUBE: 'Seats', VK.Z_BRACKET: 'Seats', VK.Z_WEB: 'Seats', VK.Z_BUCKLE: 'Seats',
            VK.Z_FEET: 'Seats'}
for _z in range(20, 33):
    ATLAS_OF[_z] = 'Props'
ATLAS_OF[VK.Z_GLOW] = 'Glow'
ATLAS_OF[VK.Z_BULB] = 'Glow'
bvh = build_bvh(body_objs)


def islands(o, faces):
    """connected face islands among the given face indices"""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table()
    todo = set(faces)
    out = []
    while todo:
        f0 = todo.pop()
        stack, isl = [f0], [f0]
        while stack:
            f = bm.faces[stack.pop()]
            for e in f.edges:
                for g in e.link_faces:
                    if g.index in todo:
                        todo.remove(g.index)
                        stack.append(g.index)
                        isl.append(g.index)
        out.append(isl)
    bm.free()
    return out


def classify(o):
    me = o.data
    names = mat_names(o)
    n = len(me.polygons)
    cen = np.empty(n * 3, np.float32)
    me.polygons.foreach_get('center', cen)
    cen = cen.reshape(-1, 3)
    nor = np.empty(n * 3, np.float32)
    me.polygons.foreach_get('normal', nor)
    nor = nor.reshape(-1, 3)
    mi = np.empty(n, np.int32)
    me.polygons.foreach_get('material_index', mi)
    hit = np.zeros(n, bool)
    for i in range(n):
        d = Vector(nor[i])
        loc, nn, idx, dist = bvh.ray_cast(Vector(cen[i]) + d * 0.004, d, 3.5)
        hit[i] = loc is not None
    inbox = (cen[:, 0] > -2.15) & (cen[:, 0] < 2.08) & (np.abs(cen[:, 1]) < 0.955) & (cen[:, 2] > 0.5) & (cen[:, 2] < 2.06)
    inside = hit & inbox
    zone = np.zeros(n, np.int32)
    mname = np.array([names[i] for i in mi])
    zone[mname == 'Steklo'] = Z_GLASS
    zone[mname == 'zerkalo'] = Z_MIRROR
    zone[mname == 'stf'] = Z_HEAD
    zone[mname == 'f1'] = Z_HEAD2
    zone[mname == 'pov'] = Z_AMBER
    zone[mname == 'st'] = Z_RED
    zone[(mname == 'kuzov') & ~inside] = Z_PAINT
    zone[(mname == 'kuzov') & inside] = Z_DASH
    zone[(mname == 'metalChern') & ~inside] = Z_BLACK
    zone[(mname == 'rezina') & ~inside] = Z_RUBBER
    zone[(mname == 'rezina') & inside] = Z_LINING
    zone[(mname == 'disk')] = Z_RIM
    # seats: thick islands are cushions, thin ones tubes
    seat_faces = np.where((mname == 'metalChern') & inside)[0]
    zone[seat_faces] = Z_FRAME
    for isl in islands(o, list(seat_faces)):
        c = cen[isl]
        dims = c.max(0) - c.min(0)
        a = sum(me.polygons[i].area for i in isl)
        if dims.min() > 0.045 and a > 0.05:
            zone[isl] = Z_CUSHION
    # small loose lining islands in the cab are controls (wheel, levers, pedals)
    lin_faces = np.where(zone == Z_LINING)[0]
    for isl in islands(o, list(lin_faces)):
        a = sum(me.polygons[i].area for i in isl)
        dims = cen[isl].max(0) - cen[isl].min(0)
        if a < 0.12 and dims.max() < 0.6 and cen[isl, 0].mean() > 0.85:
            zone[isl] = Z_CONTROL
    zone[zone == 0] = Z_BLACK
    return zone


ZONES = {}
for o in body_objs:
    ZONES[o.name] = classify(o)
for w in wheels:
    names = mat_names(w)
    mi = np.array([p.material_index for p in w.data.polygons])
    ZONES[w.name] = np.where(np.array([names[i] for i in mi]) == 'disk', Z_RIM, Z_TYRE)
cnt = {}
for z in ZONES.values():
    for k, v in zip(*np.unique(z, return_counts=True)):
        cnt[int(k)] = cnt.get(int(k), 0) + int(v)
log('zones', cnt)

# store the zone as a face attribute
for o in meshes:
    a = o.data.attributes.get('zone') or o.data.attributes.new('zone', 'FLOAT', 'FACE')
    a.data.foreach_set('value', ZONES[o.name].astype(np.float32))

# ------------------------------------------------------------------ v2.1 surface probes (on the stock body, before removals)
bvh_p = build_bvh([o for o in body_objs if o.name != 'bumpP'])
_cache = {}


def _ray(o, d, mx=4.0):
    return bvh_p.ray_cast(Vector(o), Vector(d), mx)[0]


def nose(y, z):
    k = ('n', round(y, 4), round(z, 4))
    if k not in _cache:
        loc = _ray((3.0, y, z), (-1, 0, 0))
        _cache[k] = loc.x if loc else 2.0
    return _cache[k]


def roof(x, y):
    loc = _ray((x, y, 3.0), (0, 0, -1))
    return loc.z if loc else 2.05


def rear(y, z):
    loc = _ray((-3.0, y, z), (1, 0, 0))
    return loc.x if loc else -2.18


def ceil(x, y):
    loc = _ray((x, y, 1.5), (0, 0, 1), 1.0)
    return loc.z if loc else 1.95


S = dict(nose=nose, roof=roof, rear=rear, ceil=ceil)
# warm the nose cache on the panel grid before anything is removed
for _y in np.linspace(-0.82, 0.82, 35):
    for _z in np.linspace(0.68, 1.22, 13):
        nose(float(_y), float(_z))
# smooth nose for the new front panel: a robust fit, even in y, to the probe grid (the stock lamp rims stick out of
# the sheet and the stock grille sits in it; both are rejected as outliers, then removed or flattened behind the panel)
_gy, _gz = np.linspace(-0.82, 0.82, 35), np.linspace(0.68, 1.22, 13)
_YY, _ZZ = np.meshgrid(_gy, _gz)
_XX = np.array([[nose(float(a), float(b)) for a in _gy] for b in _gz])


def _nbasis(y, z):
    y2 = np.asarray(y, np.float64) ** 2 / 0.67
    t = (np.asarray(z, np.float64) - 0.95) / 0.27
    return np.stack([y2 ** i * t ** j for i in range(5) for j in range(4)], -1)


_A, _b = _nbasis(_YY.ravel(), _ZZ.ravel()), _XX.ravel()
_keep = np.ones(len(_b), bool)
for _it in range(10):
    _coef = np.linalg.lstsq(_A[_keep], _b[_keep], rcond=None)[0]
    _res = _b - _A @ _coef
    _keep = np.abs(_res) < (0.03 if _it < 2 else (0.012 if _it < 5 else 0.006))
log('nose fit: kept %d / %d, rms %.4f, max+ %.4f (all samples), max+ kept %.4f' % (
    _keep.sum(), len(_b), float(np.sqrt(np.mean(_res[_keep] ** 2))), float(_res.max()), float(_res[_keep].max())))


def nose_s(y, z):
    return float(_nbasis(y, z) @ _coef)


S['nose_s'] = nose_s

# saloon panes (for the curtains), from the stock glass
panes = {}
_kz = bpy.data.objects['Kuzov']
_za = np.empty(len(_kz.data.polygons), np.float32)
_kz.data.attributes['zone'].data.foreach_get('value', _za)
for p, zz in zip(_kz.data.polygons, _za):
    if int(round(zz)) == Z_GLASS and p.area > 0.03 and abs(p.normal.y) > 0.8 and p.center.x < 0.85:
        xs = [_kz.data.vertices[i].co.x for i in p.vertices]
        zs = [_kz.data.vertices[i].co.z for i in p.vertices]
        panes.setdefault(1 if p.center.y > 0 else -1, []).append([min(xs), max(xs), min(zs), max(zs)])
windows = []
for side_, iv in panes.items():
    iv.sort()
    cur = iv[0][:]
    for a_ in iv[1:]:
        if a_[0] <= cur[1] + 0.02:
            cur = [cur[0], max(cur[1], a_[1]), min(cur[2], a_[2]), max(cur[3], a_[3])]
        else:
            windows.append((cur[0], cur[1], side_, cur[2], cur[3]))
            cur = a_[:]
    windows.append((cur[0], cur[1], side_, cur[2], cur[3]))
windows = [w for w in windows if w[1] - w[0] > 0.25]
INFO['saloon_windows'] = [[round(v, 3) for v in w] for w in windows]


# ------------------------------------------------------------------ v2.2 removals: stock face, lamps, dash, saloon seats, bumper
def kill_faces(o, pred):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    zl = bm.faces.layers.float.get('zone')
    kill = [f for f in bm.faces if pred(int(round(f[zl])), f.calc_center_median())]
    if kill:
        bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    return len(kill)


def kz_pred(z, c):
    if z in (Z_HEAD, Z_HEAD2, Z_AMBER, Z_RED):
        return True
    if z in (Z_BLACK, Z_RUBBER, Z_GLASS) and c.x > 2.0 and abs(c.y) < 0.84 and 0.66 < c.z < 1.24:
        return True                                     # stock grille, lamp rims and lamp glass behind the new panel
    if z == Z_GLASS and c.x < -2.10 and abs(c.y) > 0.70 and 0.84 < c.z < 1.11:
        return True                                     # stock tail-lamp glass under the new clusters
    if z == Z_DASH and c.x > 1.5 and 0.95 < c.z < 1.45:
        return True
    if z in (Z_CUSHION, Z_FRAME) and c.x < 0.86:
        return True
    return False


INFO['removed_faces'] = {'Kuzov': kill_faces(bpy.data.objects['Kuzov'], kz_pred)}
for _dn in ('doorL', 'doorP', 'doorZL', 'dooZP'):
    INFO['removed_faces'][_dn] = kill_faces(bpy.data.objects[_dn], lambda z, c: z in (Z_HEAD, Z_HEAD2, Z_AMBER, Z_RED))
bpy.data.objects.remove(bpy.data.objects['bumpP'], do_unlink=True)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
body_objs = [o for o in meshes if not o.name.startswith('Wheel')]
log('removed', INFO['removed_faces'])
# flatten whatever stock sheet still stands proud of the smoothed nose inside the panel outline
_kz = bpy.data.objects['Kuzov']
_Mw = _kz.matrix_world.copy()
_Mi = _Mw.inverted()
_n_clamp, _worst = 0, 0.0
for _v in _kz.data.vertices:
    _w = _Mw @ _v.co
    if _w.x > 1.9 and abs(_w.y) < 0.815 and 0.685 < _w.z < 1.215:
        _lim = nose_s(_w.y, _w.z) + 0.004
        if _w.x > _lim:
            _worst = max(_worst, _w.x - _lim)
            _w.x = _lim
            _v.co = _Mi @ _w
            _n_clamp += 1
_kz.data.update()
log('nose clamp: %d vertices, worst %.3f m' % (_n_clamp, _worst))

# ------------------------------------------------------------------ v2.3 kit
VT.gauges(TEX)
VT.lenses(TEX)
LUV = {k: VT.uv(r, VT.LN) for k, r in VT.LENS.items()}
GUV = {k: VT.uv(r, VT.GN) for k, r in VT.REG.items()}
LENS_GROUPS = ('head', 'spot', 'amber', 'marker', 'tail', 'reverse', 'work', 'plate', 'dome', 'night')
lens = VK.LensKit()                                   # one lens object per lamp (switch / blink each on its own)
sockets = []
kb = VK.KB()
sockets += VK.front_module(kb, lens, S, LUV)
sockets += VK.bumper(kb, lens, LUV)
sockets += VK.visor(kb, lens, S, LUV)
kit_front = kb.to_object('Kit_Front')
kb, kb_load = VK.KB(), VK.KB()
sockets += VK.roof_rack(kb, kb_load, lens, S, LUV)
kit_roof = kb.to_object('Kit_RoofRack')
kit_load = kb_load.to_object('Kit_RoofLoad')
kb = VK.KB()
door_kb = {1: VK.KB(), -1: VK.KB()}
sockets += VK.side_kit(kb, lens, S, LUV, door_kb)
kit_side = kb.to_object('Kit_Side')
kb, kb_ladder, kb_spare = VK.KB(), VK.KB(), VK.KB()
sockets += VK.rear_kit(kb, lens, S, LUV, kb_ladder, kb_spare)
kit_rear = kb.to_object('Kit_Rear')
kb = VK.KB()
sockets += VK.dome_lamps(kb, lens, S, LUV, {'Dome_Saloon_F': (0.10, 0.0), 'Dome_Saloon_R': (-1.75, -0.25),
                                            'Dome_Cab': (1.30, 0.0)})
sockets += VK.night_lamp(kb, lens, LUV)
kit_int = kb.to_object('Kit_Interior')
kb, kb_g = VK.KB(), VK.KB()
needle_specs = VK.dashboard(kb, kb_g, GUV)
sockets.append(('Dash_Flood', VK.on_face(VK.COLUMN_Y, 1.325, 0.05), Vector(-VK.DASH_N), 'flood', Vector((0, 0, 1))))
dash = kb.to_object('Dash')
gauges_obj = kb_g.to_object('Dash_Gauges')
lens_objs = {sk: kb_.to_object('Lens_' + sk) for sk, kb_ in lens.kbs.items()}
LENS_GROUP_OF = dict(lens.groups)
for name_, door_name in ((1, 'doorL'), (-1, 'doorP')):                      # flares and rails ride on the cab doors
    extra = door_kb[name_].to_object('tmp_door_kit')
    P.select_only([bpy.data.objects[door_name], extra], active=bpy.data.objects[door_name])
    bpy.ops.object.join()
extra = kb_ladder.to_object('tmp_ladder')
P.select_only([bpy.data.objects['doorZL'], extra], active=bpy.data.objects['doorZL'])
bpy.ops.object.join()
extra = kb_spare.to_object('tmp_spare')                       # the spare wheel carrier swings with the right rear door
P.select_only([bpy.data.objects['dooZP'], extra], active=bpy.data.objects['dooZP'])
bpy.ops.object.join()
# folding troop seats: one master (left wall, x = -0.57) baked with the atlas, instanced afterwards
X_MASTER = -0.57
kb = VK.KB()
VK.seat_fixed(kb, X_MASTER)
seat_fixed = kb.to_object('Seat_L2_Fixed')
kb = VK.KB()
VK.seat_pan(kb, X_MASTER)
seat_pan = kb.to_object('Seat_L2', pivot=(X_MASTER, VK.YH, VK.ZH))
kb = VK.KB()
VK.seat_leg(kb, X_MASTER)
seat_leg = kb.to_object('Seat_L2_Leg', pivot=(X_MASTER, VK.YF, VK.ZH))
# cozy kit (stove with flue, wood box, boots, cargo, table, lamp, curtains, safety)
roof_at_flue = roof(-1.92, 0.63)
ceil_at_flue = ceil(-1.92, 0.63)
VP.PROPS.clear()
VP.LIGHTS.clear()
props, plights = VP.build(windows, wall_y=0.90, ceil_z=ceil_at_flue, roof_z=roof_at_flue)
kit_objs = [kit_front, kit_roof, kit_load, kit_side, kit_rear, kit_int, dash, seat_fixed, seat_pan, seat_leg] + list(props)
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o not in lens_objs.values() and o is not gauges_obj]
ZONES = {}
for o in meshes:                                   # the attribute is the truth now (removals, joins, kit)
    za = np.empty(len(o.data.polygons), np.float32)
    o.data.attributes['zone'].data.foreach_get('value', za)
    ZONES[o.name] = np.round(za).astype(np.int32)
log('kit', len(kit_objs), 'objects,', len(sockets), 'lamp sockets, props', len(props))
ATL_MATS = {k: bpy.data.materials.new('ATL_' + k) for k in ('Body', 'Trim', 'Wheel', 'Cabin', 'Seats', 'Props', 'Glow', 'Glass')}

parts = {k: [] for k in ATL_MATS}
for o in meshes:
    o['orig'] = o.name
    z = ZONES[o.name]
    used = sorted({ATLAS_OF[int(v)] for v in np.unique(z)})
    o.data.materials.clear()
    for k in used:
        o.data.materials.append(ATL_MATS[k])
    idx = np.array([used.index(ATLAS_OF[int(v)]) for v in z], np.int32)
    o.data.polygons.foreach_set('material_index', idx)
    o.data.update()
split = P.split_by_material(meshes)
for o in split:
    m = P.main_material(o)
    parts[m.name[4:]].append(o)
log('parts', {k: len(v) for k, v in parts.items()})

# geometry facts for the painter
glass_c = []
for o in parts['Glass']:
    for p in o.data.polygons:
        if p.area > 0.03:                                   # window panes, not lamp glass
            glass_c.append((*p.center, *p.normal))
glass_c = np.array(glass_c)
side = glass_c[(np.abs(glass_c[:, 4]) > 0.8) & (glass_c[:, 0] < 0.85)]
Z_WIN_BOT, Z_WIN_TOP = 9.0, -9.0
for o in parts['Glass']:                                    # pane extents from the vertices of big side panes
    for p in o.data.polygons:
        if p.area > 0.03 and abs(p.normal.y) > 0.8 and p.center.x < 0.85:
            zz = [o.data.vertices[i].co.z for i in p.vertices]
            Z_WIN_BOT = min(Z_WIN_BOT, min(zz))
            Z_WIN_TOP = max(Z_WIN_TOP, max(zz))
if Z_WIN_BOT > Z_WIN_TOP:
    Z_WIN_BOT, Z_WIN_TOP = 1.25, 1.70
X_PART = 0.88                                       # cab / saloon partition
WHEEL_X = (1.207, -1.203)
WHEEL_Z, WHEEL_R = 0.323, 0.323
INFO['window_band'] = [round(Z_WIN_BOT, 3), round(Z_WIN_TOP, 3)]
log('window band', INFO['window_band'])


# ------------------------------------------------------------------ 3. data bakes
def data_material(kind, img):
    m = bpy.data.materials.new('bake_' + kind)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    if kind in ('pos', 'nor'):
        geo = nt.nodes.new('ShaderNodeNewGeometry')
        mp = nt.nodes.new('ShaderNodeVectorMath')
        mp.operation = 'MULTIPLY_ADD'
        s = 1 / 6 if kind == 'pos' else 0.5
        mp.inputs[1].default_value = (s, s, s)
        mp.inputs[2].default_value = (0.5, 0.5, 0.5)
        nt.links.new(geo.outputs['Position' if kind == 'pos' else 'Normal'], mp.inputs[0])
        nt.links.new(mp.outputs[0], em.inputs['Color'])
    else:
        at = nt.nodes.new('ShaderNodeAttribute')
        at.attribute_type = 'GEOMETRY'
        at.attribute_name = 'zone'
        dv = nt.nodes.new('ShaderNodeMath')
        dv.operation = 'DIVIDE'
        dv.inputs[1].default_value = 32.0
        nt.links.new(at.outputs['Fac'], dv.inputs[0])
        nt.links.new(dv.outputs[0], em.inputs['Color'])
    ti = nt.nodes.new('ShaderNodeTexImage')
    ti.image = img
    nt.nodes.active = ti
    ti.select = True
    return m


def bake_pass(objs, kind, size, samples=1, ao_dist=0.35):
    img = bpy.data.images.new(f'{kind}_{size}', size, size, alpha=True, float_buffer=True)
    img.generated_color = (0, 0, 0, 0)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.render.bake.margin = 0
    sc.render.bake.use_clear = True
    for o in objs:                                          # props come without slots
        if not o.material_slots:
            o.data.materials.append(None)
    keep = {o.name: [s.material for s in o.material_slots] for o in objs}
    m = data_material(kind if kind != 'ao' else 'zone', img)
    for o in objs:
        for s in o.material_slots:
            s.material = m
    P.select_only(objs)
    if kind == 'ao':
        w = sc.world or bpy.data.worlds.new('W')
        sc.world = w
        w.light_settings.distance = ao_dist
        bpy.ops.object.bake(type='AO')
    else:
        bpy.ops.object.bake(type='EMIT')
    for o in objs:
        for s, mm in zip(o.material_slots, keep[o.name]):
            s.material = mm
    a = np.array(img.pixels[:], np.float32).reshape(size, size, 4)[::-1].copy()
    bpy.data.images.remove(img)
    bpy.data.materials.remove(m)
    return a


# ------------------------------------------------------------------ 4. painter
C = dict(rust_d=lin(74, 38, 20), rust_o=lin(146, 70, 30), primer=lin(146, 144, 134), dirt=lin(58, 50, 40),
         salt=lin(172, 170, 160), under=lin(28, 26, 23), black=lin(30, 30, 29), black_w=lin(68, 66, 62),
         metal=lin(112, 110, 104), rubber=lin(22, 22, 22), dust=lin(66, 61, 54), head=lin(196, 204, 210),
         amber=lin(214, 122, 30), red=lin(158, 26, 20), mirror=lin(150, 158, 166), tyre=lin(24, 24, 24),
         tyre_w=lin(48, 47, 45), snow=lin(196, 200, 206), pine=lin(172, 134, 92), pine_d=lin(128, 92, 58),
         knot=lin(84, 56, 34), vinyl=lin(96, 56, 38), vinyl_d=lin(64, 36, 24), ply=lin(134, 104, 70),
         rug_a=lin(128, 38, 30), rug_b=lin(70, 32, 26), rug_c=lin(176, 140, 92), mat=lin(30, 30, 30),
         seat=lin(78, 60, 52), seat_w=lin(118, 96, 84), frame=lin(92, 92, 88), ctrl=lin(28, 28, 28),
         plaid_a=lin(140, 40, 34), plaid_b=lin(46, 70, 52), plaid_c=lin(200, 186, 150), dash_dark=lin(40, 40, 38),
         white=lin(199, 196, 189), white_f=lin(196, 191, 177), guard=lin(56, 56, 58), chrome=lin(182, 184, 186),
         chrome_d=lin(90, 92, 94), panel=lin(24, 24, 24), redpaint=lin(170, 32, 24), dashc=lin(80, 82, 87),
         dashc_w=lin(122, 124, 128), pad=lin(26, 26, 28), domeb=lin(204, 200, 188), canvas=lin(112, 118, 85),
         orange=lin(212, 104, 26),
         canvas_d=lin(84, 90, 62), alu=lin(176, 178, 180), steel=lin(120, 122, 124), web=lin(112, 114, 114),
         buckle=lin(206, 206, 202))
PAINT, FADE, REPAINT = lin(143, 43, 38), lin(161, 79, 72), lin(128, 38, 33)     # the plane's red


def boards(s, pitch, aa):
    """board index and a seam mask for coordinate s"""
    w = s / pitch
    i = np.floor(w)
    d = np.abs(w - np.round(w)) * pitch
    seam = 1.0 - ss(0.006 - aa, 0.006 + aa, d)
    return i, seam


def hash1(i, seed=0):
    x = np.sin(i * 12.9898 + seed * 78.233) * 43758.5453
    return x - np.floor(x)


def paint_body(Pp, Nn, ao, aa):
    """fleet livery like the plane: red, a white belt band and a white roof, a dark stone guard; then the wear"""
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n_lo = fbm(Pp, 1.1, 3, seed=1)
    n_mid = fbm(Pp, 6.0, 3, seed=2)
    n_hi = fbm(Pp, 38.0, 2, seed=3)
    up = np.clip(Nn[:, 2], 0, 1)
    col = np.tile(PAINT, (len(x), 1))
    side = (np.abs(Nn[:, 2]) < 0.65).astype(np.float32)
    band = ss(1.193, 1.203, z) * (1 - ss(1.302, 1.312, z)) * side
    roofw = np.clip(ss(1.885, 1.915, z) * ss(0.30, 0.55, Nn[:, 2]) + ss(1.975, 1.99, z), 0, 1)
    guard = (1 - ss(0.585, 0.598, z)) * (Nn[:, 2] < 0.5)
    col = mixc(col, C['white'], band)
    col = mixc(col, C['white'], roofw)
    col = mixc(col, C['guard'], guard)
    col = col * (0.87 + 0.20 * n_lo + 0.10 * (n_mid - 0.5) + 0.15 * (n_hi - 0.5))[:, None]
    fade = ss(0.25, 0.95, up) * (0.40 + 0.30 * n_lo)
    white_mask = np.clip(band + roofw, 0, 1)
    red_mask = np.clip(1 - white_mask - guard, 0, 1)
    col = mixc(col, FADE, fade * red_mask * 0.8)
    col = mixc(col, C['white_f'], fade * white_mask * 0.6)
    patch = ss(0.67, 0.70, fbm(Pp, 2.4, 2, seed=5)) * (1 - up) * red_mask
    col = mixc(col, REPAINT, patch * 0.7)
    low = 1 - ss(0.46, 0.82, z)
    arch = np.zeros_like(x)
    for xc in WHEEL_X:
        r = np.sqrt((x - xc) ** 2 + (z - WHEEL_Z) ** 2)
        arch = np.maximum(arch, (1 - ss(0.43, 0.56, r)) * (np.abs(Nn[:, 1]) > 0.3))
    cav = ss(0.62, 0.30, ao)
    win = ss(0.10, 0.0, np.abs(z - Z_WIN_BOT)) * (np.abs(Nn[:, 1]) > 0.5)
    src = np.clip(np.maximum.reduce([low * 0.75, arch * 0.85, cav * 0.5, win * 0.5]), 0, 1)
    rn = fbm(Pp, 13.0, 3, seed=7)
    rb = fbm(Pp, 44.0, 2, seed=8)
    rv = rn * 0.72 + rb * 0.28
    rust = ss(0.69 - 0.34 * src, 0.76 - 0.34 * src, rv) * (src > 0.04)
    st = fbm(Pp * np.array([1, 1, 0.10], np.float32), 22.0, 2, seed=12)
    runs = ss(0.72, 0.80, st) * (1 - up) * np.clip(win * 2 + low * 0.6 + rust, 0, 1)
    col = mixc(col, C['rust_d'], np.clip(rust * 0.9 + runs * 0.40, 0, 1))
    col = mixc(col, C['rust_o'], rust * ss(0.45, 0.75, rb) * 0.6)
    chip = ss(0.915 - 0.14 * src, 0.935 - 0.14 * src, fbm(Pp, 62.0, 2, seed=9)) * (0.35 + 0.65 * ss(0.0, 0.3, src))
    col = mixc(col, C['primer'], chip * (1 - rust) * 0.85)
    grime = (1 - ss(0.40, 0.98, z)) * (0.50 + 0.50 * n_mid)
    spray = np.zeros_like(x)
    for xc in WHEEL_X:
        spray = np.maximum(spray, np.exp(-((x - (xc - 0.55)) / 0.45) ** 2) * (1 - ss(0.35, 1.15, z)))
    spray = np.maximum(spray, (x < -2.0) * (1 - ss(0.4, 1.3, z)))
    rain = ss(0.62, 0.74, fbm(Pp * np.array([1, 1, 0.07], np.float32), 16.0, 2, seed=10)) * (z < Z_WIN_BOT) * (1 - up)
    col = mixc(col, C['dirt'], np.clip(grime * 0.55 + spray * 0.42 + rain * 0.32 + cav * 0.38, 0, 0.85))
    salt = (1 - ss(0.42, 0.80, z)) * ss(0.48, 0.74, fbm(Pp, 7.5, 3, seed=11))
    col = mixc(col, C['salt'], salt * 0.42)
    col = mixc(col, C['under'], ss(-0.25, -0.7, Nn[:, 2]))
    return col


def paint_trim(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_mid = fbm(Pp, 6.0, 3, seed=21)
    n_hi = fbm(Pp, 40.0, 2, seed=22)
    up = np.clip(Nn[:, 2], 0, 1)
    col = np.tile(C['black'], (n, 1))
    b = np.tile(C['black'], (n, 1)) * (0.85 + 0.3 * n_mid + 0.25 * (n_hi - 0.5))[:, None]
    b = mixc(b, C['black_w'], up * 0.55 * (0.5 + n_mid))
    rust = ss(0.72, 0.78, fbm(Pp, 16.0, 3, seed=23) + 0.25 * (1 - ss(0.4, 0.9, z)))
    b = mixc(b, C['rust_d'], rust * 0.8)
    b = mixc(b, C['metal'], ss(0.88, 0.90, fbm(Pp, 60.0, 2, seed=24)) * 0.8)
    b = mixc(b, C['dirt'], (1 - ss(0.35, 0.9, z)) * 0.45 + ss(0.6, 0.3, ao) * 0.3)
    b = mixc(b, C['snow'], (z > 2.1) * up * ss(0.55, 0.8, n_mid) * 0.5)               # frost on the rack
    col = np.where(np.isin(Z, [Z_BLACK])[:, None], b, col)
    r = np.tile(C['rubber'], (n, 1)) * (0.9 + 0.2 * n_hi)[:, None]
    r = mixc(r, C['dust'], up * 0.5 + (1 - ss(0.4, 0.9, z)) * 0.4)
    col = np.where((Z == Z_RUBBER)[:, None], r, col)
    col = np.where((Z == Z_MIRROR)[:, None], C['mirror'] * (0.85 + 0.3 * n_mid)[:, None], col)
    ch = C['chrome'] * (0.82 + 0.3 * n_hi)[:, None]
    ch = mixc(ch, C['chrome_d'], ss(0.55, 0.8, n_mid) * 0.35 + ss(0.6, 0.3, ao) * 0.3)
    col = np.where((Z == VK.Z_CHROME)[:, None], ch, col)
    pn = C['panel'] * (0.85 + 0.3 * n_hi)[:, None]
    pn = mixc(pn, C['dirt'], (1 - ss(0.62, 1.0, z)) * 0.35)
    col = np.where((Z == VK.Z_PANEL)[:, None], pn, col)
    col = np.where((Z == VK.Z_REDPAINT)[:, None], C['redpaint'] * (0.85 + 0.3 * n_hi)[:, None], col)
    sp = C['tyre'] * (0.9 + 0.2 * n_hi)[:, None]
    sp = mixc(sp, C['snow'], up * ss(0.5, 0.75, n_mid) * 0.55)
    col = np.where((Z == VK.Z_SPARE)[:, None], sp, col)
    # sand ladders: moulded orange boards with a stud grid, scuffed and snowy
    gx, gy = np.mod(x / 0.05, 1.0), np.mod(y / 0.05, 1.0)
    stud = (np.abs(gx - 0.5) < 0.22) & (np.abs(gy - 0.5) < 0.22)
    og = C['orange'] * (0.86 + 0.25 * n_mid + 0.12 * (n_hi - 0.5))[:, None]
    og = np.where((stud & (Nn[:, 2] > 0.6))[:, None], og * 0.72, og)
    og = mixc(og, C['dirt'], ss(0.6, 0.85, fbm(Pp, 9.0, 2, seed=25)) * 0.35)
    og = mixc(og, C['snow'], up * ss(0.55, 0.8, n_mid) * 0.5)
    col = np.where((Z == VK.Z_ORANGE)[:, None], og, col)
    sr = C['white'] * (0.80 + 0.25 * n_mid + 0.15 * (n_hi - 0.5))[:, None]
    sr = mixc(sr, C['rust_d'], ss(0.64, 0.74, fbm(Pp, 18.0, 2, seed=26)) * 0.6)
    sr = mixc(sr, C['dirt'], 0.25 + 0.3 * ss(0.6, 0.3, ao))
    col = np.where((Z == VK.Z_SPARERIM)[:, None], sr, col)
    return col


def paint_wheel(Pp, Nn, Z, ao, aa, centre):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    r = np.sqrt((x - centre[0]) ** 2 + (z - centre[2]) ** 2)
    n_hi = fbm(Pp, 40.0, 2, seed=31)
    n_mid = fbm(Pp, 8.0, 2, seed=32)
    t = np.tile(C['tyre'], (n, 1)) * (0.9 + 0.2 * n_hi)[:, None]
    tread = ss(0.29, 0.31, r)
    t = mixc(t, C['tyre_w'], tread * ss(0.55, 0.85, ao))
    t = mixc(t, C['dust'], (1 - tread) * np.abs(Nn[:, 1]) * 0.35 * (0.6 + 0.6 * n_mid))
    t = mixc(t, C['snow'], tread * ss(0.55, 0.30, ao) * 0.55)
    rim = C['white'] * (0.78 + 0.3 * n_mid + 0.2 * (n_hi - 0.5))[:, None]
    rim = mixc(rim, C['rust_d'], ss(0.62, 0.72, fbm(Pp, 18.0, 2, seed=33) + 0.4 * ss(0.15, 0.2, r)) * 0.7)
    rim = mixc(rim, C['dirt'], 0.30 + 0.35 * ss(0.6, 0.3, ao))
    return np.where((Z == Z_RIM)[:, None], rim, t)


def paint_cabin(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo = fbm(Pp, 2.0, 3, seed=41)
    n_hi = fbm(Pp, 40.0, 2, seed=42)
    col = np.zeros((n, 3), np.float32)
    groove = np.zeros(n, np.float32)
    up, down = Nn[:, 2] > 0.65, Nn[:, 2] < -0.6
    floor = up & (z < 1.0)
    cab = x > X_PART + 0.02
    engine = cab & (np.abs(y) < 0.44) & (z > 0.80) & (z < 1.30) & (x > 0.95) & (x < 1.70)
    wall = ~floor & ~down & ~engine
    pi_c, seam_c = boards(y, 0.098, aa)
    pi_w, seam_w = boards(z, 0.098, aa)
    bi = np.where(down, pi_c, pi_w)
    seam = np.where(down, seam_c, seam_w)
    along = np.where(down, x, np.where(np.abs(Nn[:, 0]) > 0.7, y, x))
    grain = fbm(np.stack([along * 0.6, bi * 3.1, bi * 1.7], 1).astype(np.float32), 9.0, 3, seed=43)
    tone = 0.80 + 0.30 * hash1(bi, 1)
    pine = C['pine'] * (tone * (0.86 + 0.24 * grain))[:, None]
    pine = mixc(pine, C['pine_d'], ss(0.62, 0.80, grain) * 0.5)
    kn = fbm(Pp, 30.0, 2, seed=44)
    pine = mixc(pine, C['knot'], ss(0.86, 0.90, kn))
    s_al = np.where(np.abs(Nn[:, 0]) > 0.7, y, x)
    du = (s_al + z) / 0.10
    dv = (s_al - z) / 0.10
    fu, fv = du - np.round(du), dv - np.round(dv)
    crease = 1 - ss(0.04, 0.10, np.minimum(np.abs(fu), np.abs(fv)))
    btn = 1 - ss(0.05, 0.09, np.sqrt(fu ** 2 + fv ** 2))
    vin = C['vinyl'] * (0.9 + 0.2 * n_lo + 0.12 * (n_hi - 0.5))[:, None]
    vin = mixc(vin, C['vinyl_d'], np.clip(crease * 0.55 + btn * 0.8, 0, 1))
    lower = z < Z_WIN_BOT - 0.02
    # cab walls: the plane's cockpit grey-blue (painted metal), door cards vinyl
    cabpaint = C['dashc'] * (0.88 + 0.18 * n_lo + 0.1 * (n_hi - 0.5))[:, None]
    wallc = np.where((lower & ~cab)[:, None], vin, pine)
    wallc = np.where((cab & ~lower)[:, None], cabpaint, wallc)
    wallc = np.where((cab & lower)[:, None], vin, wallc)
    col = np.where(wall[:, None] | down[:, None], wallc, col)
    col = np.where((cab & down)[:, None], cabpaint, col)
    groove = np.where((wall & ~lower & ~cab) | (down & ~cab), seam, groove)
    pf, seam_f = boards(y, 0.24, aa)
    ply = C['ply'] * ((0.84 + 0.22 * hash1(pf, 3)) * (0.88 + 0.2 * fbm(np.stack([x * 0.5, pf * 2.3, pf], 1).astype(np.float32), 7.0, 2, seed=45)))[:, None]
    rug = (np.abs(y) < 0.30) & (x > -2.05) & (x < X_PART - 0.06)
    stripe = np.floor(x / 0.075)
    rugc = np.where((np.mod(stripe, 4) == 0)[:, None], C['rug_c'], np.where((np.mod(stripe, 2) == 0)[:, None], C['rug_b'], C['rug_a']))
    edge = (np.abs(y) > 0.25)
    rugc = np.where(edge[:, None], C['rug_b'], rugc) * (0.85 + 0.25 * n_hi)[:, None]
    mat = C['mat'] * (1 - 0.35 * (np.abs(x / 0.03 - np.round(x / 0.03)) < 0.18))[:, None]
    fl = np.where(rug[:, None], rugc, ply)
    fl = np.where(cab[:, None], mat, fl)
    fl = mixc(fl, C['dirt'], (x < -1.85) * 0.35 + ss(0.5, 0.25, ao) * 0.3)
    col = np.where(floor[:, None], fl, col)
    groove = np.where(floor & ~rug & ~cab, seam_f, groove)
    pl_u, pl_v = np.mod(x / 0.06, 4), np.mod(y / 0.06, 4)
    plaid = np.where(((pl_u < 1) | (pl_v < 1))[:, None], C['plaid_a'], C['plaid_b'])
    plaid = np.where(((np.abs(pl_u - 2.5) < 0.12) | (np.abs(pl_v - 2.5) < 0.12))[:, None], C['plaid_c'], plaid)
    eng = np.where((Nn[:, 2] > 0.35)[:, None], plaid, C['vinyl'] * (0.9 + 0.2 * n_lo)[:, None])
    col = np.where(engine[:, None] & ~floor[:, None], eng, col)
    col = np.where((Z == Z_CONTROL)[:, None], C['ctrl'] * (0.9 + 0.4 * ss(0.5, 0.9, ao) * n_hi)[:, None], col)
    # the new dashboard: grey-blue painted panel with worn edges, black vinyl pad, white dome bases
    dp = C['dashc'] * (0.86 + 0.2 * n_lo + 0.14 * (n_hi - 0.5))[:, None]
    dp = mixc(dp, C['dashc_w'], ss(0.85, 0.95, ao) * ss(0.82, 0.88, fbm(Pp, 55.0, 2, seed=46)))
    col = np.where((Z == VK.Z_DASHP)[:, None], dp, col)
    pad = C['pad'] * (0.85 + 0.3 * n_hi)[:, None]
    pad = mixc(pad, C['dust'], up * 0.25 * ss(0.4, 0.8, n_lo))
    col = np.where((Z == VK.Z_DASHPAD)[:, None], pad, col)
    col = np.where((Z == VK.Z_DOMEBASE)[:, None], C['domeb'] * (0.9 + 0.15 * n_hi)[:, None], col)
    groove = np.where(np.isin(Z, [VK.Z_DASHP, VK.Z_DASHPAD, VK.Z_DOMEBASE, Z_CONTROL]), 0.0, groove)
    return col, groove


def paint_seats(Pp, Nn, Z, ao, aa):
    """cab seats: dark vinyl; troop seats like the plane's: olive canvas, aluminium tubes, steel, grey webbing"""
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo = fbm(Pp, 3.0, 3, seed=51)
    n_hi = fbm(Pp, 40.0, 2, seed=52)
    up = Nn[:, 2] > 0.6
    cs = C['seat'] * (0.86 + 0.22 * n_lo + 0.14 * (n_hi - 0.5))[:, None]
    cs = mixc(cs, C['seat_w'], up * ss(0.45, 0.8, n_lo) * 0.5)
    _, st = boards(np.where(up, x, z), 0.12, aa)
    fr = C['frame'] * (0.8 + 0.3 * n_lo + 0.2 * (n_hi - 0.5))[:, None]
    col = np.where((Z == Z_CUSHION)[:, None], cs, fr)
    weave = 0.5 + 0.5 * np.sin(Pp[:, 0] * 2 * np.pi / 0.02) * np.sin(Pp[:, 1] * 2 * np.pi / 0.02)
    cv = C['canvas'] * (0.84 + 0.22 * n_lo + 0.10 * weave)[:, None]
    cv = mixc(cv, C['canvas_d'], ss(0.55, 0.3, ao) * 0.6 + up * ss(0.5, 0.8, n_lo) * 0.25)
    col = np.where((Z == VK.Z_CANVAS)[:, None], cv, col)
    al = C['alu'] * (0.8 + 0.25 * fbm(Pp * np.array([0.2, 1, 1], np.float32), 30.0, 2, seed=53))[:, None]
    col = np.where((Z == VK.Z_TUBE)[:, None], al, col)
    col = np.where((Z == VK.Z_BRACKET)[:, None], C['steel'] * (0.85 + 0.3 * n_hi)[:, None], col)
    rib = 0.85 + 0.15 * np.sin((Pp[:, 0] + Pp[:, 1]) * 2 * np.pi / 0.006)
    col = np.where((Z == VK.Z_WEB)[:, None], C['web'] * rib[:, None], col)
    col = np.where((Z == VK.Z_BUCKLE)[:, None], C['buckle'] * (0.85 + 0.2 * n_hi)[:, None], col)
    col = np.where((Z == VK.Z_FEET)[:, None], C['rubber'], col)
    groove = np.where(Z == Z_CUSHION, st * 0.7, 0.0)
    return col, groove


import uaz_props as UP


def paint_props(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo = fbm(Pp, 4.0, 3, seed=61)
    n_hi = fbm(Pp, 45.0, 2, seed=62)
    col = np.tile(lin(120, 120, 120), (n, 1))
    up = Nn[:, 2] > 0.6
    # iron: blued black, heat rust, worn edges, soot
    iron = lin(36, 34, 32) * (0.85 + 0.3 * n_lo + 0.25 * (n_hi - 0.5))[:, None]
    iron = mixc(iron, lin(92, 50, 30), ss(0.62, 0.72, fbm(Pp, 12.0, 3, seed=63)) * 0.7)
    iron = mixc(iron, lin(80, 78, 74), ss(0.86, 0.9, fbm(Pp, 55.0, 2, seed=64)) * 0.6)
    col = np.where((Z == UP.Z_IRON)[:, None], iron, col)
    # wood: planks of the box / table, crates
    pk, seam = boards(np.where(np.abs(Nn[:, 0]) > 0.6, z, x), 0.07, aa)
    wood = lin(150, 110, 68) * ((0.82 + 0.3 * hash1(pk, 7)) * (0.86 + 0.24 * fbm(np.stack([x * 0.4, pk * 2.0, y], 1).astype(np.float32), 10.0, 2, seed=65)))[:, None]
    wood = wood * (1 - 0.45 * seam)[:, None]
    tabletop = (z > 1.3) & up & (x > -0.3) & (x < 0.3)
    wood = np.where(tabletop[:, None], lin(118, 78, 46) * (0.9 + 0.2 * n_lo)[:, None], wood)
    col = np.where((Z == UP.Z_WOOD)[:, None], wood, col)
    crate = lin(132, 100, 62) * ((0.8 + 0.3 * hash1(pk, 9)) * (0.88 + 0.2 * n_hi))[:, None] * (1 - 0.5 * seam)[:, None]
    col = np.where((Z == UP.Z_CRATE)[:, None], crate, col)
    # birch logs: white bark with black streaks, cut ends
    bark = lin(206, 200, 186) * (0.85 + 0.2 * n_hi)[:, None]
    bark = mixc(bark, lin(40, 38, 34), ss(0.66, 0.72, fbm(Pp * np.array([3, 1, 1], np.float32), 14.0, 2, seed=66)))
    endc = lin(178, 136, 86) * (0.85 + 0.25 * n_lo)[:, None]
    col = np.where((Z == UP.Z_LOG)[:, None], np.where((np.abs(Nn[:, 0]) > 0.8)[:, None], endc, bark), col)
    # curtains: dark red cloth with a woven stripe
    stripe = (np.mod(z / 0.05, 1.0) < 0.18).astype(np.float32)
    cloth = lin(122, 46, 36) * (0.85 + 0.25 * n_lo)[:, None]
    cloth = mixc(cloth, lin(196, 160, 110), stripe * 0.45)
    col = np.where((Z == UP.Z_CLOTH)[:, None], cloth, col)
    # red enamel (lamp shade, a mug), chipped to white
    en = lin(168, 38, 28) * (0.9 + 0.2 * n_hi)[:, None]
    en = mixc(en, lin(222, 220, 210), ss(0.88, 0.9, fbm(Pp, 70.0, 2, seed=67)))
    col = np.where((Z == UP.Z_LAMP)[:, None], en, col)
    col = np.where((Z == UP.Z_CAN)[:, None], lin(148, 30, 24) * (0.85 + 0.3 * n_lo)[:, None], col)
    col = np.where((Z == UP.Z_BAG)[:, None], lin(98, 96, 62) * (0.85 + 0.3 * n_lo)[:, None], col)
    col = np.where((Z == UP.Z_FELT)[:, None], lin(104, 102, 98) * (0.85 + 0.3 * n_hi)[:, None], col)
    steel = lin(150, 152, 150) * (0.8 + 0.3 * n_lo + 0.2 * (n_hi - 0.5))[:, None]
    col = np.where((Z == UP.Z_STEEL)[:, None], steel, col)
    # first-aid kit (white with a red cross on the face) and the book (brown cover)
    kit = lin(206, 204, 196) * (0.9 + 0.15 * n_hi)[:, None]
    cross = ((np.abs(y + 0.67) < 0.02) & (np.abs(z - 1.50) < 0.055)) | ((np.abs(y + 0.67) < 0.055) & (np.abs(z - 1.50) < 0.02))
    kit = np.where((cross & (Nn[:, 0] < -0.6))[:, None], lin(176, 30, 26), kit)
    book = lin(92, 52, 40) * (0.9 + 0.2 * n_hi)[:, None]
    col = np.where((Z == UP.Z_KIT)[:, None], np.where((x < 0.5)[:, None], book, kit), col)
    return col, np.zeros(n, np.float32)


# ------------------------------------------------------------------ 5. PSX step (coverage-aware)
def psx_step(col_hi, ao_hi, cov_hi, groove_hi, f, ncol=64, ao_min=0.25, dither=1.0):
    from scipy import ndimage
    w = cov_hi.astype(np.float32)
    shaded = col_hi * (ao_min + (1 - ao_min) * ao_hi)[..., None] * (1 - 0.55 * groove_hi)[..., None]
    num = P.blocks(shaded * w[..., None], f).sum(2)
    den = P.blocks(w, f).sum(2)
    col = num / np.maximum(den, 1e-6)[..., None]
    aob = P.blocks(np.where(cov_hi, ao_hi, 1.0), f)
    line = np.clip((aob.mean(2) - aob.min(2)) * 2.4, 0, 0.5)
    col = col * (1 - line)[..., None]
    cov = den > 0.25 * f * f
    s = P.l2s(col).reshape(-1, 3)
    samp = s[cov.reshape(-1)]
    samp = samp[np.random.default_rng(1).choice(len(samp), min(len(samp), 60000), replace=False)]
    pal = P.kmeans(samp, ncol)
    n = col.shape[0]
    bay = np.tile(P.BAYER4, (n // 4 + 1, n // 4 + 1))[:n, :n].reshape(-1, 1)
    sd = np.clip(s + (bay - 0.5) * (1 / 24) * dither, 0, 1)
    idx = np.empty(len(sd), np.int32)
    for i in range(0, len(sd), 65536):
        idx[i:i + 65536] = ((sd[i:i + 65536, None, :] - pal[None]) ** 2).sum(-1).argmin(1)
    q = pal[idx].reshape(col.shape)
    if not cov.all():
        ii = ndimage.distance_transform_edt(~cov, return_distances=False, return_indices=True)
        q = q[ii[0], ii[1]]
    return (q * 255 + 0.5).astype(np.uint8), cov


def make_atlas(name, objs, painter, size=None, ppm=50.0, oversample=2, ao_min=0.25, ao_dist=0.35, rough=0.8,
               wheel_centre=None):
    from PIL import Image
    P.unwrap_group(objs, margin=0.004, angle=62)
    A = P.area3d(objs)
    fill = max(P.uv_fill(objs), 1e-6)
    if size is None:
        want = math.sqrt(A / fill) * ppm
        size = int(2 ** math.ceil(math.log2(max(want * 0.8, 1))))   # the power of two at or above 80 % of the aim
        size = max(256, min(1024, size))
    hi = size * oversample
    pos = bake_pass(objs, 'pos', hi)
    nor = bake_pass(objs, 'nor', hi)
    zon = bake_pass(objs, 'zone', hi)
    ao = bake_pass(objs, 'ao', hi, samples=40, ao_dist=ao_dist)[..., 0]
    cov = P.coverage_mask(objs, hi)
    Pp = (pos[..., :3] - 0.5) * 6.0
    Nn = nor[..., :3] * 2 - 1
    Nn /= np.maximum(np.linalg.norm(Nn, axis=-1, keepdims=True), 1e-6)
    Zz = np.round(zon[..., 0] * 32).astype(np.int32)
    ci = cov.reshape(-1)
    aa = 1.0 / (size * math.sqrt(fill / A)) / oversample            # texel size (m) at the working size
    args = (Pp.reshape(-1, 3)[ci].astype(np.float32), Nn.reshape(-1, 3)[ci].astype(np.float32))
    zz = Zz.reshape(-1)[ci]
    aov = ao.reshape(-1)[ci]
    if painter is paint_body:
        out, gr = painter(*args, aov, aa), None
    elif painter is paint_wheel:
        out, gr = painter(*args, zz, aov, aa, wheel_centre), None
    elif painter is paint_trim:
        out, gr = painter(*args, zz, aov, aa), None
    else:
        out, gr = painter(*args, zz, aov, aa)
    col = np.zeros((hi * hi, 3), np.float32)
    col[ci] = out
    groove = np.zeros(hi * hi, np.float32)
    if gr is not None:
        groove[ci] = gr
    q, cov_lo = psx_step(col.reshape(hi, hi, 3), np.clip(ao, 0, 1), cov, groove.reshape(hi, hi), oversample, ao_min=ao_min)
    p = os.path.join(TEX, f'T_Van_{name}_BaseColor.png')
    Image.fromarray(q, 'RGB').save(p)
    m = P.psx_material('M_Van_' + name, p, rough=rough)
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(m)
    ppm_real = size * math.sqrt(fill / A)
    INFO[name] = dict(size=size, ppm=round(ppm_real, 1), area_m2=round(A, 2), uv_fill=round(fill, 3),
                      colours=int(len(np.unique(q.reshape(-1, 3), axis=0))))
    log('ATLAS', name, INFO[name])
    return m


# ------------------------------------------------------------------ 6. atlases
for name, loc, kind, energy, colr in plights:                      # stove and pendant lamp
    e = bpy.data.objects.new('LIGHT_' + name, None)
    bpy.context.scene.collection.objects.link(e)
    e.location = loc
    e['kind'], e['energy'], e['color'], e['group'] = kind, energy, list(colr), 'int'
make_atlas('Body', parts['Body'], paint_body, size=256, rough=0.62)
make_atlas('Trim', parts['Trim'], paint_trim, size=512, rough=0.7)
w0 = [o for o in parts['Wheel'] if o['orig'] == 'Wheel'][0]
wc = (P.world_bbox([w0])[0] + P.world_bbox([w0])[1]) / 2
make_atlas('Wheel', [w0], paint_wheel, size=128, wheel_centre=wc, rough=0.85)
for o in parts['Wheel']:                                       # the other three wheels share the texture
    if o is w0:
        continue
    if len(o.data.loops) != len(w0.data.loops):
        log('WARN wheel topology differs', o.name)
        continue
    uv = o.data.uv_layers.get('PSX') or o.data.uv_layers.new(name='PSX')
    src = np.empty(len(w0.data.loops) * 2, np.float32)
    w0.data.uv_layers['PSX'].data.foreach_get('uv', src)
    uv.data.foreach_set('uv', src)
    o.data.materials.clear()
    o.data.materials.append(w0.data.materials[0])
make_atlas('Cabin', parts['Cabin'], paint_cabin, size=512, ao_min=0.42, ao_dist=0.30, rough=0.85)
make_atlas('Seats', parts['Seats'], paint_seats, size=256, ao_min=0.45, ao_dist=0.22, rough=0.75)
make_atlas('Props', parts['Props'], paint_props, size=256, ao_min=0.45, ao_dist=0.20, rough=0.8)
for o in parts['Glow']:
    if o['orig'] == 'LampBulb':
        mname, colr, strength, day = 'M_Van_LampBulb', (1.0, 0.80, 0.52), 14.0, 0.0
    else:
        mname, colr, strength, day = 'M_Van_StoveGlow', (1.0, 0.42, 0.10), 9.0, 0.6
    m = bpy.data.materials.get(mname) or bpy.data.materials.new(mname)
    m.use_nodes = True
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Base Color'].default_value = (*colr, 1)
    pb.inputs['Emission Color'].default_value = (*colr, 1)
    pb.inputs['Emission Strength'].default_value = day
    m['night_emit'] = strength
    m['day_emit'] = day
    o.data.materials.clear()
    o.data.materials.append(m)

# glass: cab vs saloon (the saloon glows at night)
g_cab = P.psx_glass('M_PSX_Glass_Cab')
g_room = P.psx_glass('M_PSX_Glass_Room')
g_room['glow'] = 0.32
g_cab['glow'] = 0.04
for o in parts['Glass']:
    o.data.materials.clear()
    o.data.materials.append(g_cab)
    o.data.materials.append(g_room)
    cen = np.empty(len(o.data.polygons) * 3, np.float32)
    o.data.polygons.foreach_get('center', cen)
    o.data.polygons.foreach_set('material_index', (cen.reshape(-1, 3)[:, 0] < X_PART).astype(np.int32))
    o.data.update()
# rejoin the parts of each original object (doors, kit pieces stay separate objects)
by_orig = {}
for k, objs in parts.items():
    for o in objs:
        by_orig.setdefault(o['orig'], []).append(o)
for orig, objs in by_orig.items():
    main = objs[0]
    if len(objs) > 1:
        P.select_only(objs, active=main)
        bpy.ops.object.join()
    main.name = orig
    main.data.name = orig


# ------------------------------------------------------------------ 7. lenses, gauges, needles (explicit-UV atlases)
def tex_mat(name, base, emi, night, rough=0.35):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    pb = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    uvn = nt.nodes.new('ShaderNodeUVMap')
    uvn.uv_map = 'PSX'
    for img, sock in ((base, 'Base Color'), (emi, 'Emission Color')):
        ti = nt.nodes.new('ShaderNodeTexImage')
        ti.image = bpy.data.images.load(img, check_existing=True)
        ti.interpolation = 'Closest'
        nt.links.new(uvn.outputs[0], ti.inputs[0])
        nt.links.new(ti.outputs[0], pb.inputs[sock])
    pb.inputs['Roughness'].default_value = rough
    pb.inputs['Emission Strength'].default_value = 0.0
    if 'Specular IOR Level' in pb.inputs:
        pb.inputs['Specular IOR Level'].default_value = 0.35
    m['night_emit'] = night
    return m


LENS_NIGHT = {'head': 5.0, 'spot': 5.0, 'amber': 0.0, 'marker': 3.0, 'tail': 2.5, 'reverse': 0.0, 'work': 4.0,
              'plate': 1.5, 'dome': 3.0, 'night': 2.5}
LB, LE = os.path.join(TEX, 'T_Van_Lens_BaseColor.png'), os.path.join(TEX, 'T_Van_Lens_Emission.png')
lens_mats = {}
for sk, o in lens_objs.items():                       # one material per lamp kind, shared by its lens objects
    g_ = LENS_GROUP_OF[sk]
    if g_ not in lens_mats:
        lens_mats[g_] = tex_mat('M_Van_Lens_' + g_.capitalize(), LB, LE, LENS_NIGHT[g_], rough=0.25)
        lens_mats[g_]['group'] = g_
    o.data.materials.clear()
    o.data.materials.append(lens_mats[g_])
    o['lamp_kind'] = g_
mg = tex_mat('M_Van_Gauges', os.path.join(TEX, 'T_Van_Gauges_BaseColor.png'), os.path.join(TEX, 'T_Van_Gauges_Emission.png'),
             1.4, rough=0.5)
gauges_obj.data.materials.clear()
gauges_obj.data.materials.append(mg)
mn = bpy.data.materials.new('M_Van_Needle')
mn.use_nodes = True
pbn = next(n for n in mn.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
pbn.inputs['Base Color'].default_value = (0.95, 0.30, 0.06, 1)
pbn.inputs['Emission Color'].default_value = (1.0, 0.35, 0.08, 1)
pbn.inputs['Emission Strength'].default_value = 0.0
mn['night_emit'] = 1.5
needles = []
for name_, centre_, length_ in needle_specs:
    o = VK.needle_object(name_, centre_, length_, VK.NEEDLE_REST[name_])
    o.data.materials.append(mn)
    needles.append(o)
INFO['needles'] = {o.name: dict(pivot=[round(v, 4) for v in o.location], rest_deg=VK.NEEDLE_REST[o.name[7:]],
                               axis=[round(v, 4) for v in VK.DASH_N]) for o in needles}

# ------------------------------------------------------------------ 8. folding seats: instances of the baked master
SEATS = {'L1': (1, -1.05), 'L2': (1, -0.57), 'L3': (1, -0.09), 'L4': (1, 0.39), 'R1': (-1, -1.00), 'R2': (-1, 0.62)}
mf, mp, ml = bpy.data.objects['Seat_L2_Fixed'], bpy.data.objects['Seat_L2'], bpy.data.objects['Seat_L2_Leg']
bpy.context.view_layer.update()


def mirror_y(me):
    me.transform(Matrix.Scale(-1, 4, Vector((0, 1, 0))))
    me.flip_normals()


def attach(child, parent):
    bpy.context.view_layer.update()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


attach(ml, mp)
INFO['seats'] = {}
for tag, (sgn, xc) in SEATS.items():
    if tag == 'L2':
        op, ol = mp, ml
    else:
        dx = xc - X_MASTER
        me = mf.data.copy()
        me.transform(Matrix.Translation((dx, 0, 0)))
        if sgn < 0:
            mirror_y(me)
        of = bpy.data.objects.new(f'Seat_{tag}_Fixed', me)
        bpy.context.scene.collection.objects.link(of)
        me = mp.data.copy()
        if sgn < 0:
            mirror_y(me)
        op = bpy.data.objects.new(f'Seat_{tag}', me)
        bpy.context.scene.collection.objects.link(op)
        op.location = (xc, sgn * VK.YH, VK.ZH)
        me = ml.data.copy()
        if sgn < 0:
            mirror_y(me)
        ol = bpy.data.objects.new(f'Seat_{tag}_Leg', me)
        bpy.context.scene.collection.objects.link(ol)
        ol.location = (xc, sgn * VK.YF, VK.ZH)
        attach(ol, op)
    op['sgn'] = sgn
    INFO['seats'][tag] = dict(side='left' if sgn > 0 else 'right', pan_pivot=[round(xc, 3), round(sgn * VK.YH, 3), round(VK.ZH, 3)],
                              leg_pivot=[round(xc, 3), round(sgn * VK.YF, 3), round(VK.ZH, 3)],
                              fold='pan about +X by %+d deg * fold, leg about +X by %+d deg * fold' % (-sgn * 90, sgn * 90))

# ------------------------------------------------------------------ 9. lamp sockets -> light markers
import van_lights as VL                               # emission diagrams -> IES, cookies, lights.json (plane v11 method)
LMETA = VL.meta()
INFO['lamps'] = {}
for s_ in sockets:
    name_, pos_, nrm_, typ = s_[:4]
    up_ = Vector(s_[4]) if len(s_) > 4 else Vector((0, 0, 1))
    nrm_ = Vector(nrm_).normalized()
    if typ == 'head':                                 # low beam: level and straight ahead, whatever the glass curvature
        nrm_ = Vector((1, 0, 0))
    up_ = (up_ - nrm_ * up_.dot(nrm_)).normalized()
    m_ = LMETA[typ]
    e = bpy.data.objects.new('LIGHT_' + name_, None)
    bpy.context.scene.collection.objects.link(e)
    e.empty_display_type, e.empty_display_size = 'SINGLE_ARROW', 0.12
    e.location = Vector(pos_) + nrm_ * 0.01
    e.rotation_euler = nrm_.to_track_quat('Z', 'Y').to_euler()          # empty +Z = beam axis (Unity light frame)
    e['type'], e['group'], e['dir'], e['up'], e['color'] = typ, m_['group'], list(nrm_), list(up_), m_['color']
    e['intensity_urp'] = VL.TYPES[typ]['I'] * VL.SOCKET_SCALE.get(name_, 1.0)
    e['lens'] = 'Lens_' + name_ if ('Lens_' + name_) in bpy.data.objects else ''
    INFO['lamps'][name_] = dict(type=typ, group=m_['group'], pos=[round(v, 4) for v in e.location],
                                dir=[round(v, 4) for v in nrm_], up=[round(v, 4) for v in up_])

# ------------------------------------------------------------------ 10. lift the body, bigger wheels
LIFT, WS = 0.09, 1.12
bpy.context.view_layer.update()
for o in list(bpy.data.objects):
    if o.parent is None and o.type in ('MESH', 'EMPTY') and not o.name.startswith('Wheel'):
        o.location.z += LIFT
for w in [o for o in bpy.data.objects if o.name.startswith('Wheel')]:
    lo_, hi_ = P.world_bbox([w])
    c_ = (lo_ + hi_) / 2
    w.data.transform(Matrix.Translation((c_[0], c_[1], WHEEL_R * WS)) @ Matrix.Scale(WS, 4) @ Matrix.Translation(-Vector(c_)))
INFO['lift_m'], INFO['wheel_scale'] = LIFT, WS
for k in INFO['lamps']:
    INFO['lamps'][k]['pos'][2] = round(INFO['lamps'][k]['pos'][2] + LIFT, 3)
VL.write_ies_all(os.path.join(TEX, 'IES'))
VL.write_cookies(os.path.join(TEX, 'Cookies'), os.path.join(TEX, 'cookies_sheet.png'))
log('lights.json', VL.lights_json(os.path.join(HERE, 'out', 'van2_lights.json'),
                                  [(k, v['pos'], v['dir'], v['type'], v['up']) for k, v in INFO['lamps'].items()]), 'lamps')
for k in INFO['seats']:
    INFO['seats'][k]['pan_pivot'][2] = round(INFO['seats'][k]['pan_pivot'][2] + LIFT, 3)
    INFO['seats'][k]['leg_pivot'][2] = round(INFO['seats'][k]['leg_pivot'][2] + LIFT, 3)
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    uvs = o.data.uv_layers
    if 'PSX' in uvs:
        for u in [u for u in uvs if u.name != 'PSX']:
            uvs.remove(u)
        uvs['PSX'].active = True
        uvs['PSX'].active_render = True
tris = sum(P.tri_count(o) for o in bpy.data.objects if o.type == 'MESH')
INFO['tris'] = tris
INFO['objects'] = sorted(o.name for o in bpy.data.objects if o.type == 'MESH')
lo_, hi_ = P.world_bbox([o for o in bpy.data.objects if o.type == 'MESH'])
INFO['bbox'] = [lo_.round(3).tolist(), hi_.round(3).tolist()]
log('tris', tris, 'bbox', INFO['bbox'])
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'van2.blend'))
json.dump(INFO, open(os.path.join(HERE, 'out', 'van2.json'), 'w'), indent=1)
log('saved van2')
