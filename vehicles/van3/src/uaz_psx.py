"""UAZ-452 «Uaz» by tiunov.se (Sketchfab, CC BY 4.0) -> PSX like the Utility Plane.
1. interior height: the ceiling lining sits 17 cm under the roof; lift it to 3 cm under the roof skin (1.30 m inside)
2. every face gets a zone (paint / black metal / rubber / lenses / lining / dash / seats ...) by material + an
   inside test (a ray along the normal hits the body) + island size (seat tubes vs cushions)
3. atlases Body / Trim / Wheel / Cabin / Seats with unique UVs; Cycles bakes world position, normal, zone, AO
4. a numpy painter makes the colour per texel (khaki paint, fade, rust, chips, road grime, salt; pine boards,
   tufted vinyl, rug, plaid; leatherette seats), then the plane's PSX step: AO in the colour, grooves as
   1-texel lines, 64-colour palette, Bayer 4x4, point filtering, no normal maps
python3 -I uaz_psx.py [livery=khaki]   -> out/uaz_psx.blend, tex/uaz/*.png"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import psxlib as P
from noise import ss, lerp, mixc, fbm

HERE = P.HERE
LIVERY = sys.argv[1] if len(sys.argv) > 1 else 'khaki'
TEX = os.path.join(HERE, 'tex', 'uaz' if LIVERY == 'khaki' else 'uaz_' + LIVERY)
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
ATLAS_OF = {Z_PAINT: 'Body', Z_BLACK: 'Trim', Z_RUBBER: 'Trim', Z_HEAD: 'Trim', Z_HEAD2: 'Trim', Z_AMBER: 'Trim',
            Z_RED: 'Trim', Z_MIRROR: 'Trim', Z_RIM: 'Wheel', Z_TYRE: 'Wheel', Z_LINING: 'Cabin', Z_DASH: 'Cabin',
            Z_CONTROL: 'Cabin', Z_CUSHION: 'Seats', Z_FRAME: 'Seats', Z_GLASS: 'Glass'}
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

# store the zone as a face attribute and split the objects by atlas
for o in meshes:
    a = o.data.attributes.get('zone') or o.data.attributes.new('zone', 'FLOAT', 'FACE')
    a.data.foreach_set('value', ZONES[o.name].astype(np.float32))
ATL_MATS = {k: bpy.data.materials.new('ATL_' + k) for k in ('Body', 'Trim', 'Wheel', 'Cabin', 'Seats', 'Glass')}
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
K = {   # livery colours (sRGB)
    'khaki': dict(paint=(80, 90, 56), fade=(126, 128, 96), repaint=(70, 84, 50), band=None),
    'red': dict(paint=(150, 34, 26), fade=(176, 92, 74), repaint=(132, 30, 24), band=(214, 210, 198)),
    'white': dict(paint=(196, 198, 190), fade=(214, 212, 196), repaint=(180, 184, 176), band=(170, 40, 30)),
}[LIVERY]
C = dict(rust_d=lin(74, 38, 20), rust_o=lin(146, 70, 30), primer=lin(146, 144, 134), dirt=lin(58, 50, 40),
         salt=lin(172, 170, 160), under=lin(28, 26, 23), black=lin(30, 30, 29), black_w=lin(68, 66, 62),
         metal=lin(112, 110, 104), rubber=lin(22, 22, 22), dust=lin(66, 61, 54), head=lin(196, 204, 210),
         amber=lin(214, 122, 30), red=lin(158, 26, 20), mirror=lin(150, 158, 166), tyre=lin(24, 24, 24),
         tyre_w=lin(48, 47, 45), snow=lin(196, 200, 206), pine=lin(172, 134, 92), pine_d=lin(128, 92, 58),
         knot=lin(84, 56, 34), vinyl=lin(96, 56, 38), vinyl_d=lin(64, 36, 24), ply=lin(134, 104, 70),
         rug_a=lin(128, 38, 30), rug_b=lin(70, 32, 26), rug_c=lin(176, 140, 92), mat=lin(30, 30, 30),
         seat=lin(112, 44, 32), seat_w=lin(150, 86, 66), frame=lin(92, 92, 88), ctrl=lin(28, 28, 28),
         plaid_a=lin(140, 40, 34), plaid_b=lin(46, 70, 52), plaid_c=lin(200, 186, 150), dash_dark=lin(40, 40, 38))
PAINT, FADE, REPAINT = lin(*K['paint']), lin(*K['fade']), lin(*K['repaint'])
BAND = lin(*K['band']) if K['band'] else None


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
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n_lo = fbm(Pp, 1.1, 3, seed=1)
    n_mid = fbm(Pp, 6.0, 3, seed=2)
    n_hi = fbm(Pp, 38.0, 2, seed=3)
    col = np.tile(PAINT, (len(x), 1))
    if BAND is not None:                                    # livery band (red / white variants)
        col = mixc(col, BAND, (ss(1.02, 1.03, z) * (1 - ss(1.17, 1.18, z))) * (np.abs(Nn[:, 2]) < 0.6))
    col = col * (0.86 + 0.22 * n_lo + 0.12 * (n_mid - 0.5) + 0.16 * (n_hi - 0.5))[:, None]
    up = np.clip(Nn[:, 2], 0, 1)
    fade = ss(0.25, 0.95, up) * (0.42 + 0.30 * n_lo) + 0.10 * ss(0.4, 0.8, n_lo)
    col = mixc(col, FADE, fade)
    patch = ss(0.66, 0.69, fbm(Pp, 2.4, 2, seed=5)) * (1 - up)
    col = mixc(col, REPAINT, patch * 0.8)
    # wear sources: low band, arch lips, cavities (seams), window corners
    low = 1 - ss(0.46, 0.82, z)
    arch = np.zeros_like(x)
    for xc in WHEEL_X:
        r = np.sqrt((x - xc) ** 2 + (z - WHEEL_Z) ** 2)
        arch = np.maximum(arch, (1 - ss(0.43, 0.56, r)) * (np.abs(Nn[:, 1]) > 0.3))
    cav = ss(0.62, 0.30, ao)
    win = ss(0.10, 0.0, np.abs(z - Z_WIN_BOT)) * (np.abs(Nn[:, 1]) > 0.5)
    src = np.clip(np.maximum.reduce([low * 0.85, arch, cav * 0.55, win * 0.6]), 0, 1)
    rn = fbm(Pp, 13.0, 3, seed=7)
    rb = fbm(Pp, 44.0, 2, seed=8)
    rv = rn * 0.72 + rb * 0.28
    rust = ss(0.66 - 0.36 * src, 0.73 - 0.36 * src, rv) * (src > 0.04)
    # rust runs down from the spots and from the window sills
    st = fbm(Pp * np.array([1, 1, 0.10], np.float32), 22.0, 2, seed=12)
    runs = ss(0.70, 0.78, st) * (1 - up) * np.clip(win * 2 + low * 0.6 + rust, 0, 1)
    col = mixc(col, C['rust_d'], np.clip(rust * 0.95 + runs * 0.45, 0, 1))
    col = mixc(col, C['rust_o'], rust * ss(0.45, 0.75, rb) * 0.6)
    # chips to primer (more where it rubs: low, arches)
    chip = ss(0.875 - 0.10 * src, 0.895 - 0.10 * src, fbm(Pp, 62.0, 2, seed=9))
    col = mixc(col, C['primer'], chip * (1 - rust) * 0.9)
    # dirt: road grime low and behind the wheels, rain streaks under the windows, dirt in seams
    grime = (1 - ss(0.40, 0.98, z)) * (0.50 + 0.50 * n_mid)
    spray = np.zeros_like(x)
    for xc in WHEEL_X:
        spray = np.maximum(spray, np.exp(-((x - (xc - 0.55)) / 0.45) ** 2) * (1 - ss(0.35, 1.15, z)))
    spray = np.maximum(spray, (x < -2.0) * (1 - ss(0.4, 1.3, z)))           # rear end catches the wheel spray
    rain = ss(0.62, 0.74, fbm(Pp * np.array([1, 1, 0.07], np.float32), 16.0, 2, seed=10)) * (z < Z_WIN_BOT) * (1 - up)
    col = mixc(col, C['dirt'], np.clip(grime * 0.62 + spray * 0.45 + rain * 0.38 + cav * 0.40, 0, 0.88))
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
    col = np.zeros((n, 3), np.float32)
    # black metal: bumpers, grille, handles, wipers, hinges
    b = np.tile(C['black'], (n, 1)) * (0.85 + 0.3 * n_mid + 0.25 * (n_hi - 0.5))[:, None]
    b = mixc(b, C['black_w'], up * 0.55 * (0.5 + n_mid))
    rust = ss(0.70, 0.76, fbm(Pp, 16.0, 3, seed=23) + 0.25 * (1 - ss(0.4, 0.9, z)))
    b = mixc(b, C['rust_d'], rust * 0.85)
    b = mixc(b, C['metal'], ss(0.88, 0.90, fbm(Pp, 60.0, 2, seed=24)) * 0.8)
    b = mixc(b, C['dirt'], (1 - ss(0.35, 0.9, z)) * 0.45 + ss(0.6, 0.3, ao) * 0.3)
    col = np.where((Z == Z_BLACK)[:, None], b, col)
    # rubber seals
    r = np.tile(C['rubber'], (n, 1)) * (0.9 + 0.2 * n_hi)[:, None]
    r = mixc(r, C['dust'], up * 0.5 + (1 - ss(0.4, 0.9, z)) * 0.4)
    col = np.where((Z == Z_RUBBER)[:, None], r, col)
    # head lamps: clear glass over a ribbed reflector, dark rim
    hc = np.where(y > 0, 0.5, -0.5)
    rr = np.sqrt((y - hc) ** 2 + (z - 1.01) ** 2)
    ring = 0.88 + 0.12 * np.cos(rr * 2 * np.pi / 0.016)
    h = np.tile(C['head'], (n, 1)) * ring[:, None] * (0.92 + 0.12 * n_hi)[:, None]
    h = mixc(h, C['dirt'], 0.15 + 0.2 * ss(0.5, 0.8, n_mid))
    col = np.where(np.isin(Z, [Z_HEAD, Z_HEAD2])[:, None], h, col)
    col = np.where((Z == Z_AMBER)[:, None], C['amber'] * (0.85 + 0.25 * n_hi)[:, None], col)
    col = np.where((Z == Z_RED)[:, None], C['red'] * (0.85 + 0.25 * n_hi)[:, None], col)
    col = np.where((Z == Z_MIRROR)[:, None], C['mirror'] * (0.85 + 0.3 * n_mid)[:, None], col)
    return col


def paint_wheel(Pp, Nn, Z, ao, aa, centre):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    r = np.sqrt((x - centre[0]) ** 2 + (z - centre[2]) ** 2)
    n_hi = fbm(Pp, 40.0, 2, seed=31)
    n_mid = fbm(Pp, 8.0, 2, seed=32)
    t = np.tile(C['tyre'], (n, 1)) * (0.9 + 0.2 * n_hi)[:, None]
    tread = ss(0.29, 0.31, r)
    t = mixc(t, C['tyre_w'], tread * ss(0.55, 0.85, ao))                 # worn tread tops
    t = mixc(t, C['dust'], (1 - tread) * np.abs(Nn[:, 1]) * 0.35 * (0.6 + 0.6 * n_mid))
    t = mixc(t, C['snow'], tread * ss(0.55, 0.30, ao) * 0.55)            # packed snow in the grooves
    rim = np.tile(PAINT, (n, 1)) * (0.8 + 0.3 * n_mid + 0.2 * (n_hi - 0.5))[:, None]
    rim = mixc(rim, C['rust_d'], ss(0.6, 0.7, fbm(Pp, 18.0, 2, seed=33) + 0.4 * ss(0.15, 0.2, r)) * 0.8)
    rim = mixc(rim, C['dirt'], 0.25 + 0.35 * ss(0.6, 0.3, ao))
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
    engine = cab & (np.abs(y) < 0.44) & (z > 0.80) & (z < 1.30) & (x > 0.95)
    wall = ~floor & ~down & ~engine
    # pine boards: ceiling along x, walls / partition horizontal
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
    # tufted vinyl below the window line, diamonds 10 cm with buttons
    s_al = np.where(np.abs(Nn[:, 0]) > 0.7, y, x)
    du = (s_al + z) / 0.10
    dv = (s_al - z) / 0.10
    fu, fv = du - np.round(du), dv - np.round(dv)
    crease = 1 - ss(0.04, 0.10, np.minimum(np.abs(fu), np.abs(fv)))
    btn = 1 - ss(0.05, 0.09, np.sqrt(fu ** 2 + fv ** 2))
    vin = C['vinyl'] * (0.9 + 0.2 * n_lo + 0.12 * (n_hi - 0.5))[:, None]
    vin = mixc(vin, C['vinyl_d'], np.clip(crease * 0.55 + btn * 0.8, 0, 1))
    lower = z < Z_WIN_BOT - 0.02
    # cab walls: painted metal in the body colour (cleaner than outside), door cards vinyl
    cabpaint = PAINT * (0.9 + 0.16 * n_lo + 0.1 * (n_hi - 0.5))[:, None]
    wallc = np.where((lower & ~cab)[:, None], vin, pine)
    wallc = np.where((cab & ~lower)[:, None], cabpaint, wallc)
    wallc = np.where((cab & lower)[:, None], vin, wallc)
    col = np.where(wall[:, None] | down[:, None], wallc, col)
    groove = np.where((wall & ~lower & ~cab) | down, seam, groove)
    # floor: plywood planks along x, a rug down the aisle, a ribbed rubber mat in the cab
    pf, seam_f = boards(y, 0.24, aa)
    ply = C['ply'] * ((0.84 + 0.22 * hash1(pf, 3)) * (0.88 + 0.2 * fbm(np.stack([x * 0.5, pf * 2.3, pf], 1).astype(np.float32), 7.0, 2, seed=45)))[:, None]
    rug = (np.abs(y) < 0.36) & (x > -2.05) & (x < X_PART - 0.06)
    stripe = np.floor(x / 0.075)
    rugc = np.where((np.mod(stripe, 4) == 0)[:, None], C['rug_c'], np.where((np.mod(stripe, 2) == 0)[:, None], C['rug_b'], C['rug_a']))
    edge = (np.abs(y) > 0.31)
    rugc = np.where(edge[:, None], C['rug_b'], rugc) * (0.85 + 0.25 * n_hi)[:, None]
    mat = C['mat'] * (1 - 0.35 * (np.abs(x / 0.03 - np.round(x / 0.03)) < 0.18))[:, None]
    fl = np.where(rug[:, None], rugc, ply)
    fl = np.where(cab[:, None], mat, fl)
    fl = mixc(fl, C['dirt'], (x < -1.85) * 0.35 + ss(0.5, 0.25, ao) * 0.3)
    col = np.where(floor[:, None], fl, col)
    groove = np.where(floor & ~rug & ~cab, seam_f, groove)
    # engine cover: brown vinyl with a plaid blanket on top
    pl_u, pl_v = np.mod(x / 0.06, 4), np.mod(y / 0.06, 4)
    plaid = np.where(((pl_u < 1) | (pl_v < 1))[:, None], C['plaid_a'], C['plaid_b'])
    plaid = np.where(((np.abs(pl_u - 2.5) < 0.12) | (np.abs(pl_v - 2.5) < 0.12))[:, None], C['plaid_c'], plaid)
    eng = np.where((Nn[:, 2] > 0.35)[:, None], plaid, C['vinyl'] * (0.9 + 0.2 * n_lo)[:, None])
    col = np.where(engine[:, None] & ~floor[:, None], eng, col)
    # dash (body colour, dark gauge faces facing the driver) and controls
    dash = PAINT * (0.95 + 0.12 * n_lo + 0.08 * (n_hi - 0.5))[:, None]
    dash = mixc(dash, C['dash_dark'], (Nn[:, 0] < -0.75) * 0.0)
    col = np.where((Z == Z_DASH)[:, None], dash, col)
    col = np.where((Z == Z_CONTROL)[:, None], C['ctrl'] * (0.9 + 0.4 * ss(0.5, 0.9, ao) * n_hi)[:, None], col)
    return col, groove


def paint_seats(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo = fbm(Pp, 3.0, 3, seed=51)
    n_hi = fbm(Pp, 40.0, 2, seed=52)
    s = C['seat'] * (0.86 + 0.22 * n_lo + 0.14 * (n_hi - 0.5))[:, None]
    up = Nn[:, 2] > 0.6
    s = mixc(s, C['seat_w'], up * ss(0.45, 0.8, n_lo) * 0.55)              # worn sitting areas
    # stitched panels: lines every 12 cm across the seat
    _, st = boards(np.where(up, x, z), 0.12, aa)
    # plaid blankets over the rearmost bench and the two facing seats
    pl_u, pl_v = np.mod((x + y) / 0.06, 4), np.mod((x - y) / 0.06, 4)
    plaid = np.where(((pl_u < 1) | (pl_v < 1))[:, None], C['plaid_a'], C['plaid_b'])
    plaid = np.where(((np.abs(pl_u - 2.5) < 0.12) | (np.abs(pl_v - 2.5) < 0.12))[:, None], C['plaid_c'], plaid)
    blanket = (x > -1.08) & (x < -0.28) & (y > 0.02) & (z > 0.9)            # the forward-facing bench
    s = np.where(blanket[:, None], plaid * (0.9 + 0.15 * n_hi)[:, None], s)
    f = C['frame'] * (0.8 + 0.3 * n_lo + 0.2 * (n_hi - 0.5))[:, None]
    f = mixc(f, C['black'], ss(0.82, 0.86, fbm(Pp, 50.0, 2, seed=53)) * 0.7)
    col = np.where((Z == Z_CUSHION)[:, None], s, f)
    groove = np.where((Z == Z_CUSHION) & ~blanket, st * 0.7, 0.0)
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
    p = os.path.join(TEX, f'T_UAZ_{name}_BaseColor.png')
    Image.fromarray(q, 'RGB').save(p)
    m = P.psx_material('M_UAZ_' + name, p, rough=rough)
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(m)
    ppm_real = size * math.sqrt(fill / A)
    INFO[name] = dict(size=size, ppm=round(ppm_real, 1), area_m2=round(A, 2), uv_fill=round(fill, 3),
                      colours=int(len(np.unique(q.reshape(-1, 3), axis=0))))
    log('ATLAS', name, INFO[name])
    return m


# saloon panes for the curtains
panes = {}
for o in parts['Glass']:
    for p in o.data.polygons:
        if p.area > 0.03 and abs(p.normal.y) > 0.8 and p.center.x < 0.85:
            xs = [o.data.vertices[i].co.x for i in p.vertices]
            zs = [o.data.vertices[i].co.z for i in p.vertices]
            side = 1 if p.center.y > 0 else -1
            panes.setdefault(side, []).append([min(xs), max(xs), min(zs), max(zs)])
windows = []
for side, iv in panes.items():
    iv.sort()
    cur = iv[0][:]
    for a_ in iv[1:]:
        if a_[0] <= cur[1] + 0.02:
            cur = [cur[0], max(cur[1], a_[1]), min(cur[2], a_[2]), max(cur[3], a_[3])]
        else:
            windows.append((cur[0], cur[1], side, cur[2], cur[3]))
            cur = a_[:]
    windows.append((cur[0], cur[1], side, cur[2], cur[3]))
windows = [w for w in windows if w[1] - w[0] > 0.25]
INFO['saloon_windows'] = [[round(v, 3) for v in w] for w in windows]
log('saloon windows', INFO['saloon_windows'])
loc_r = bvh_roof.ray_cast(Vector((-1.92, 0.63, 1.70)), Vector((0, 0, 1)), 1.0)[0]
bvh_all = build_bvh([o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('Wheel')])
loc_c = bvh_all.ray_cast(Vector((-1.92, 0.63, 1.40)), Vector((0, 0, 1)), 1.0)[0]
roof_z = loc_r.z if loc_r else 2.05
ceil_z = loc_c.z if loc_c else 1.97
props, lights = UP.build(windows, wall_y=0.90, ceil_z=ceil_z, roof_z=roof_z)
log('props', len(props), 'roof', round(roof_z, 3), 'ceiling', round(ceil_z, 3))
glow_objs = [o for o in props if o.name in ('StoveGlow', 'LampBulb')]
parts['Props'] = [o for o in props if o not in glow_objs]
for name, loc, kind, energy, colr in lights:
    e = bpy.data.objects.new('LIGHT_' + name, None)
    bpy.context.scene.collection.objects.link(e)
    e.location = loc
    e['kind'], e['energy'], e['color'] = kind, energy, list(colr)

make_atlas('Body', parts['Body'], paint_body, size=256, rough=0.62)
make_atlas('Trim', parts['Trim'], paint_trim, size=256, rough=0.7)
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
make_atlas('Seats', parts['Seats'], paint_seats, size=256, ao_min=0.40, ao_dist=0.25, rough=0.75)
make_atlas('Props', parts['Props'], paint_props, size=256, ao_min=0.45, ao_dist=0.20, rough=0.8)
for o, (mname, colr, strength) in zip(glow_objs, [('M_UAZ_StoveGlow', (1.0, 0.42, 0.10), 9.0),
                                                   ('M_UAZ_LampBulb', (1.0, 0.80, 0.52), 14.0)]):
    if o.name == 'LampBulb':
        mname, colr, strength = 'M_UAZ_LampBulb', (1.0, 0.80, 0.52), 14.0
    else:
        mname, colr, strength = 'M_UAZ_StoveGlow', (1.0, 0.42, 0.10), 9.0
    m = bpy.data.materials.new(mname)
    m.use_nodes = True
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Base Color'].default_value = (*colr, 1)
    pb.inputs['Emission Color'].default_value = (*colr, 1)
    pb.inputs['Emission Strength'].default_value = 0.6
    m['night_emit'] = strength
    m['day_emit'] = 0.6 if o.name == 'StoveGlow' else 0.0
    o.data.materials.clear()
    o.data.materials.append(m)

# glass: cab vs saloon (glows at night)
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
# rejoin the parts of each original object (doors stay separate objects)
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
# lamps get their own materials (same texture) so they can glow
trim_img = bpy.data.materials['M_UAZ_Trim']
lamp_mats = {}
for zone_ids, mname, colr, strength in (((Z_HEAD, Z_HEAD2), 'M_UAZ_Lamp_Head', (1.0, 0.92, 0.78), 6.0),
                                        ((Z_RED,), 'M_UAZ_Lamp_Tail', (1.0, 0.08, 0.04), 3.0)):
    m = trim_img.copy()
    m.name = mname
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    ti = next(n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE')
    m.node_tree.links.new(ti.outputs[0], pb.inputs['Emission Color'])
    pb.inputs['Emission Strength'].default_value = 0.0
    m['night_emit'] = strength
    lamp_mats[zone_ids] = m
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    za = np.empty(len(o.data.polygons), np.float32)
    o.data.attributes['zone'].data.foreach_get('value', za)
    for zone_ids, m in lamp_mats.items():
        sel = np.isin(np.round(za).astype(int), zone_ids)
        if sel.any():
            if m.name not in [s.material.name for s in o.material_slots if s.material]:
                o.data.materials.append(m)
            mi = [s.material.name for s in o.material_slots].index(m.name)
            idx = np.empty(len(o.data.polygons), np.int32)
            o.data.polygons.foreach_get('material_index', idx)
            idx[sel] = mi
            o.data.polygons.foreach_set('material_index', idx)
            o.data.update()
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
log('tris', tris, INFO['objects'])
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
tag = 'uaz_psx' if LIVERY == 'khaki' else f'uaz_psx_{LIVERY}'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', f'{tag}.blend'))
json.dump(INFO, open(os.path.join(HERE, 'out', f'{tag}.json'), 'w'), indent=1)
log('saved', tag)
