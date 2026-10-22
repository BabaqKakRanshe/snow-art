"""Main building build (main_shell / main_open / main_rooms / main_rooms2 / main_fx / main_signs): one object per part with
its pivot as the origin, Update 3's hierarchy kept (BaseMain with R_<Room> x15, the IX_* parts and the FX_* fixtures under
it; the second prefab BaseMain_Opening with its 8 parts); PSX atlases baked with psxbake + main_paint at the generator
shed's pixel density: MainExt (the envelope, the roofs, the outside), Rm_<Room> x15 (each room's shell, finishes and
furniture: the room's light layer), MainParts (doors, windows, shutters, drawers, switches ...), MainFx (the fixtures'
bodies), MainOpening (the heating controls, the door bar); main_tex's panel atlas on the signs, labels, papers and dials;
the materials the game switches by name (M_ScreenOff, M_LEDOff, M_HeatFault, the fixtures' M_FX_* / M_LEDOn) and the
glass joined into their objects; the interaction contract (parts with Update 3's pivots / axes / ranges, light-layer masks,
Update 3's lights and glows, sockets, map placement).
python3 -I main_build.py [--only Rm_Windfang,MainFx] -> out/main.blend, out/main.json, out/main_contract.json, tex/main/*
--only: bake just those atlases (the others get flat zone colours) -> out/main_test.blend"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
import psxlib as P
import psxbake as PB
import gen_kit as K
import uvpack

ONLY = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else None
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'main')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
SHED_PPM = 51.3                               # the generator shed's building atlas (px / m): the project's pixel
PB.POS_SCALE = 40.0                           # bake range +-20 m: the garage's west wall at x -18, the mast's top 18.5 up
U3 = json.load(open(os.path.join(HERE, 'main_u3_data.json')))
PLACE = dict(p=[340.0, 16.7443, -360.0], q=[0.0, 0.069756, 0.0, 0.997564])      # Forest_Layout.json: both prefabs
ROOTS = ('BaseMain', 'BaseMain_Opening')


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
    """building frame -> Unity prefab-local: (x, y, z) -> (-x, z, -y)"""
    return [round(-float(v[0]), 4) + 0.0, round(float(v[2]), 4) + 0.0, round(-float(v[1]), 4) + 0.0]


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
import main_tex as MT
PANEL_B, PANEL_E = MT.build(TEX)
import main_spec as S
import main_shell as MS
import main_open as MO
import main_rooms as MR
import main_furn as F
import main_fx as MFX
import main_signs as MSG
import main_paint as MP

# ------------------------------------------------------------------ 1. geometry
MS.build_shell()
MO.build_openings()
MR.build_rooms()
MFX.build_fx()
MSG.build_signs()
C = K.CONTRACT
part = K.part
part('BaseMain', 'static', (0, 0, 0), parent=None, note='the envelope, the roofs and the outside (exterior light layer)')
for rn, R in S.ROOMS.items():
    part('R_' + rn, 'static', (0, 0, 0), parent='BaseMain', room=rn, layer=R['layer'],
         note=f'room {rn}: its walls, floor, ceiling, finishes and furniture (light layer {R["layer"]})')
for rn in S.ROOMS:
    if 'R_' + rn + '_Glass' in K.KBS:
        part('R_' + rn + '_Glass', 'static', (0, 0, 0), parent='R_' + rn, note='the room\'s window glass')


def split_zones(src, zones, dst, atlas, note):
    """move the faces of `zones` out of KB src into a new KB dst (joined back with its own material after the bakes)"""
    k = K.KBS[src]
    fs = [f for f in k.bm.faces if int(round(f[k.zl])) in zones]
    if not fs:
        return 0
    d = K.kb(dst, atlas)
    for f in fs:
        d.poly([tuple(v.co) for v in f.verts], int(round(f[k.zl])), [tuple(l[k.uvl].uv) for l in f.loops])
    bmesh.ops.delete(k.bm, geom=fs, context='FACES')
    part(dst, 'static', C['parts'][src]['pivot'], parent=src, note=note)
    return len(fs)


nsplit = 0
for name in list(K.KBS):
    a = K.ATLAS[name]
    if a in ('glass', 'panel') or a.startswith('lens:'):
        continue
    nsplit += split_zones(name, {F.Z_SCREENP}, name + '__screen', 'lens:screenoff',
                          'the screens the station\'s power lights (M_ScreenOff -> M_ScreenOn); joined at export')
    nsplit += split_zones(name, {F.Z_LED}, name + '__led', 'lens:ledoff',
                          'the LEDs the station\'s power lights (M_LEDOff -> M_LEDOn); joined at export')
nsplit += split_zones('BaseMain', {MS.Z_ROOF, MS.Z_PARIN, MS.Z_UPSTAND}, 'BaseMain__roof', 'MainRoof',
                      'the roofs\' gravel, upstands and the parapets\' inner faces: their own atlas (M_Main_Roof) so the '
                      'facades keep the shed\'s pixel; joined into BaseMain at export')
log('split screen / LED / roof faces', nsplit)
missing = [n for n in K.KBS if n not in C['parts']]
assert not missing, f'objects without a contract entry: {missing}'

JOINED = lambda a: a in ('glass', 'panel') or a.startswith('lens:')
for name, k in K.KBS.items():
    a = K.ATLAS[name]
    if a.startswith('lens:'):                         # lit parts face out (Unity draws one side): a majority vote
        k.bm.normal_update()
        vs = [v.co for v in k.bm.verts]
        cc = sum(vs, Vector()) / max(len(vs), 1)
        vote = 0
        for f in k.bm.faces:
            d = f.calc_center_median() - cc
            if d.length > 1e-6:
                vote += 1 if f.normal.dot(d) > 0 else -1
        if vote < 0:
            bmesh.ops.reverse_faces(k.bm, faces=list(k.bm.faces))
    elif a == 'glass':                                # glass is seen from both sides: each pane twice, back to back
        for f in list(k.bm.faces):
            pts = [tuple(v.co) for v in f.verts]
            uvs = [tuple(l[k.uvl].uv) for l in f.loops]
            k.poly(list(reversed(pts)), f[k.zl], list(reversed(uvs)))
# welded: the walls, floors and boxes become whole islands; not welded: frames, copings and rails (welded they close into
# rings round their openings, and a ring's empty middle wastes its whole bounding box in the atlas)
NO_WELD = {K.Z_GALV, MO.Z_DOORFRAME, MO.Z_WINFRAME, MO.Z_ALUFRAME, MO.Z_SASH, MO.Z_SHUTRAIL, MO.Z_TRACK}
def _to2d(pts, n):
    u = (Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))).cross(n).normalized()
    v = n.cross(u)
    P2 = [(p.dot(u), p.dot(v)) for p in pts]
    a = sum(P2[i][0] * P2[(i + 1) % len(P2)][1] - P2[(i + 1) % len(P2)][0] * P2[i][1] for i in range(len(P2)))
    return P2 if a > 0 else list(reversed(P2))


def _clip(subject, clipper):
    out = subject
    for i in range(len(clipper)):
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]
        inp, out = out, []
        if not inp:
            break
        ins = lambda p: (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= -1e-9

        def inter(p, q):
            x1, y1, x2, y2, x3, y3, x4, y4 = p[0], p[1], q[0], q[1], a[0], a[1], b[0], b[1]
            den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if abs(den) < 1e-12:
                return q
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        for j in range(len(inp)):
            p, q = inp[j], inp[(j + 1) % len(inp)]
            if ins(q):
                if not ins(p):
                    out.append(inter(p, q))
                out.append(q)
            elif ins(p):
                out.append(inter(p, q))
    return out


def separate_coplanar(names, push=0.0008):
    """faces in one plane, facing the same way and overlapping, fight for the pixel in the game (two zones, or one zone
    with two texel grids: the dither differs): taken largest first, each face that overlaps faces already placed is lifted
    off its neighbours (its own vertices) and pushed out along its normal one step (`push`) past the highest of them, as
    a decal is. Runs on the welded KBs (building frame) before they become objects."""
    Fs, buckets = [], {}
    for name in names:
        k = K.KBS[name]
        k.bm.normal_update()
        k.bm.faces.ensure_lookup_table()
        for f in k.bm.faces:
            a = f.calc_area()
            if a < 1e-6:
                continue
            n = f.normal.copy()
            pts = [v.co.copy() for v in f.verts]
            d = n.dot(f.calc_center_median())
            Fs.append((name, f.index, n, d, pts, int(round(f[k.zl])), a))
            key = (round(n.x * 100), round(n.y * 100), round(n.z * 100), round(d * 1000))
            buckets.setdefault(key, []).append(len(Fs) - 1)
    adj = {}
    for key, ids in buckets.items():
        cand = list(ids)
        for dk in (-1, 1):
            cand += buckets.get((key[0], key[1], key[2], key[3] + dk), [])
        for i in ids:
            a = Fs[i]
            for j in cand:
                if j <= i:
                    continue
                b = Fs[j]
                if a[2].dot(b[2]) < 0.999 or abs(a[3] - b[3]) > 0.001:
                    continue
                inter = _clip(_to2d(a[4], a[2]), _to2d(b[4], a[2]))
                if len(inter) >= 3:
                    ar = abs(sum(inter[q][0] * inter[(q + 1) % len(inter)][1] - inter[(q + 1) % len(inter)][0] *
                                 inter[q][1] for q in range(len(inter)))) / 2
                    if ar > 1e-5:
                        adj.setdefault(i, set()).add(j)
                        adj.setdefault(j, set()).add(i)
    plane = {}                                                       # the face's plane after the move (along n)
    for i in sorted(adj, key=lambda i: -Fs[i][6]):
        top = max((plane[j] for j in adj[i] if j in plane), default=None)
        plane[i] = Fs[i][3] if top is None else max(Fs[i][3], top + push)
    by_kb = {}
    moved = []
    for i, dn in plane.items():
        if dn - Fs[i][3] > 1e-6:
            by_kb.setdefault(Fs[i][0], []).append((Fs[i][1], dn - Fs[i][3]))
            moved.append(dn - Fs[i][3])
    for name, fis in by_kb.items():
        k = K.KBS[name]
        k.bm.faces.ensure_lookup_table()
        old = [(k.bm.faces[fi], dd) for fi, dd in fis]
        for f, dd in old:
            n = f.normal.copy()
            k.poly([v.co + n * dd for v in f.verts], f[k.zl], [tuple(l[k.uvl].uv) for l in f.loops])
        bmesh.ops.delete(k.bm, geom=[f for f, dd in old], context='FACES')
    INFO['coplanar_moved_mm'] = dict(n=len(moved), max=round(max(moved, default=0) * 1000, 2))
    return len(moved)


for name, k in K.KBS.items():
    if not JOINED(K.ATLAS[name]):
        keep = {v for f in k.bm.faces if int(round(f[k.zl])) in NO_WELD for v in f.verts}
        bmesh.ops.remove_doubles(k.bm, verts=[v for v in k.bm.verts if v not in keep], dist=1e-4)
INFO['coplanar_separated'] = separate_coplanar([n for n in K.KBS if not JOINED(K.ATLAS[n])])
log('coplanar overlapping faces pushed apart', INFO['coplanar_separated'], INFO['coplanar_moved_mm'])
objs = {}
for name, k in K.KBS.items():
    if not k.bm.faces:
        log('WARN empty', name)
    objs[name] = k.to_object(name, pivot=Vector(C['parts'][name]['pivot']))
log('objects', len(objs))
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


def root_of(name):
    while C['parts'][name].get('parent'):
        name = C['parts'][name]['parent']
    return name


for name, p in C['parts'].items():
    p['root'] = root_of(name)


# ------------------------------------------------------------------ 2. atlases
groups = {}
for name, o in objs.items():
    a = K.ATLAS[name]
    if not JOINED(a):
        groups.setdefault('MainParts' if a == 'MainFx' else a, []).append(o)      # the fixtures share the parts' atlas
log('atlases', {a: len(v) for a, v in groups.items()})
GLASS = [o for n, o in objs.items() if K.ATLAS[n] == 'glass']
OVERLAY = [o for n, o in objs.items() if JOINED(K.ATLAS[n]) and K.ATLAS[n] != 'glass']
SHUTTERS = [objs[n] for n, p in C['parts'].items() if p['kind'] == 'scale' and n in objs]
VIVID = (F.Z_EXTING, F.Z_CALLPT, F.Z_BELL, F.Z_DRUM_R, F.Z_DRUM_B, F.Z_FIRSTAID, F.Z_SIGN, F.Z_JACKET, F.Z_TOWEL,
         F.Z_BINDER, F.Z_BOOKS, F.Z_QUAD, F.Z_TOOL, F.Z_BOILER, F.Z_PUMPG, F.Z_MAINSW, F.Z_BAR, MS.Z_STRIPE, F.Z_COPPER,
         F.Z_BRASS, F.Z_FABRIC_B, F.Z_FABRIC_G, F.Z_MAP, MO.Z_PANIC, MO.Z_LOCK, MFX.Z_FX_GREEN, MS.Z_BRICK)
CEIL = {MS.Z_CEIL: 0.75, MS.Z_CEILT: 0.75, MS.Z_CEILB: 0.75, MS.Z_SOFFIT: 0.8}
SPEC = {'MainExt': dict(cap=SHED_PPM, ao_min=0.35, ao_dist=0.40, rough=0.85, zs={MS.Z_PLINTH: 0.85}),
        'MainRoof': dict(cap=SHED_PPM, ao_min=0.35, ao_dist=0.40, rough=0.9, zs=None, max=1024),
        'MainParts': dict(cap=64.0, ao_min=0.40, ao_dist=0.20, rough=0.75, zs=None),
        'MainFx': dict(cap=64.0, ao_min=0.40, ao_dist=0.14, rough=0.6, zs=None),
        'MainOpening': dict(cap=96.0, ao_min=0.40, ao_dist=0.14, rough=0.6, zs=None)}
for a in groups:
    if a.startswith('Rm_'):
        SPEC[a] = dict(cap=SHED_PPM, ao_min=0.35, ao_dist=0.40, rough=0.85, zs=CEIL)


def prep_atlas(objs_, cap, zone_scale=None, angle=50, tol=0.90, max_size=2048, oversample=2, A=None):
    """psxbake.prepare_atlas with the size chosen from the texel density: the smallest power of two that holds the group
    at >= tol x cap (the islands are then shrunk to cap: the shed's pixel, never finer)"""
    A = A or P.area3d(objs_)
    size = 256
    while size < max_size and size * math.sqrt(0.70 / A) < tol * cap:
        size *= 2
    P.unwrap_group(objs_, margin=2.2 / size, angle=angle, zone_scale=zone_scale)
    fill = max(P.uv_fill(objs_), 1e-6)
    keep = [np.empty(2 * len(o.data.loops), np.float32) for o in objs_]     # Blender's packing or the shelves:
    for o, b in zip(objs_, keep):                                          # whichever covers more of the atlas
        o.data.uv_layers['PSX'].data.foreach_get('uv', b)
    f2 = uvpack.repack(objs_, size, 2.2)
    if f2 < fill:
        for o, b in zip(objs_, keep):
            o.data.uv_layers['PSX'].data.foreach_set('uv', b)
    else:
        fill = max(f2, 1e-6)
    if size < max_size and size * math.sqrt(fill / A) < tol * cap:          # the packing came out looser: one step up
        size *= 2
    if size * math.sqrt(fill / A) > cap:
        kk = cap / (size * math.sqrt(fill / A))
        for o in objs_:
            for l in o.data.uv_layers['PSX'].data:
                l.uv = l.uv * kk
        fill = max(P.uv_fill(objs_), 1e-6)
    hi = size * oversample
    pos, nor, zon = PB.bake_pass(objs_, 'pos', hi), PB.bake_pass(objs_, 'nor', hi), PB.bake_pass(objs_, 'zone', hi)
    cov = P.coverage_mask(objs_, hi)
    cov &= np.abs(np.linalg.norm(nor[..., :3] * 2 - 1, axis=-1) - 1) < 0.1
    return dict(size=size, hi=hi, oversample=oversample, A=A, fill=fill, pos=pos, nor=nor, zon=zon, cov=cov)


def hidden(obs, flag=True):
    for o in obs:
        o.hide_render = flag


def proxy(objs_):
    """one joined copy of a group for the bakes (Cycles syncs the scene once per baked object: 130 parts -> one)"""
    if len(objs_) == 1:
        return objs_[0], []
    cps = []
    for i, o in enumerate(objs_):
        c = o.copy()
        c.data = o.data.copy()
        sc_.collection.objects.link(c)
        mw = o.matrix_world.copy()
        c.parent = None
        c.matrix_world = mw
        n = len(c.data.loops)
        c.data.attributes.new('src_obj', 'INT', 'CORNER').data.foreach_set('value', np.full(n, i, np.int32))
        c.data.attributes.new('src_loop', 'INT', 'CORNER').data.foreach_set('value', np.arange(n, dtype=np.int32))
        cps.append(c)
    P.select_only(cps, active=cps[0])
    bpy.ops.object.join()
    px = cps[0]
    px.name = 'BAKE_PROXY'
    hidden(objs_)
    return px, objs_


def drop_proxy(px, orig):
    if orig:
        hidden(orig, False)
        me = px.data
        bpy.data.objects.remove(px)
        bpy.data.meshes.remove(me)


sc_ = bpy.context.scene


INFO['atlases'] = {}
cache = {}


def zmat(z):
    if z not in cache:
        m = bpy.data.materials.new(f'draft_{z}')
        m.use_nodes = True
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        col = MO.DRAFT_COL.get(z) or F.DRAFT_COL.get(z) or MFX.DRAFT_COL.get(z) or (150, 148, 140)
        c = PB.lin(*col)
        pb.inputs['Base Color'].default_value = (float(c[0]), float(c[1]), float(c[2]), 1)
        pb.inputs['Roughness'].default_value = 0.75
        cache[z] = m
    return cache[z]


def draft(objs_):
    for o in objs_:
        me = o.data
        zl = [round(a.value) for a in me.attributes['zone'].data]
        me.materials.clear()
        idx = {}
        for z in sorted(set(zl)):
            idx[z] = len(me.materials)
            me.materials.append(zmat(z))
        for poly, z in zip(me.polygons, zl):
            poly.material_index = idx[z]


ORDER = ['MainExt', 'MainRoof'] + sorted(a for a in groups if a.startswith('Rm_')) + ['MainParts', 'MainOpening']
hidden(GLASS + OVERLAY)                                   # glass, signs and lenses do not shade the bakes
for a in ORDER:
    if ONLY is not None and a not in ONLY:
        draft(groups[a])
        continue
    sp = SPEC[a]
    name = a.replace('Main', '', 1) if a.startswith('Main') else a          # Ext, Parts, Fx, Opening, Rm_<Room>
    t1 = time.time()
    px, orig = proxy(groups[a])
    prep = prep_atlas([px], sp['cap'], zone_scale=sp['zs'], A=P.area3d(groups[a]), max_size=sp.get('max', 2048))
    if a != 'MainParts':
        hidden([s for s in SHUTTERS if s not in groups[a]])           # the shutters are rolled up at the start
    PB.finish_atlas(name, [px], prep, MP.paint_main, TEX, prefix='T_Main_', mat_prefix='M_Main_', ao_min=sp['ao_min'],
                    ao_dist=sp['ao_dist'], rough=sp['rough'], log=log, info=INFO['atlases'], prio_zones=VIVID)
    hidden(SHUTTERS, False)
    if orig:                                              # the proxy's UVs and material back onto the parts
        m_ = px.data.materials[0]
        nl = len(px.data.loops)
        buf = np.empty(2 * nl, np.float32)
        px.data.uv_layers['PSX'].data.foreach_get('uv', buf)
        buf = buf.reshape(-1, 2)
        so, sl = np.empty(nl, np.int32), np.empty(nl, np.int32)
        px.data.attributes['src_obj'].data.foreach_get('value', so)
        px.data.attributes['src_loop'].data.foreach_get('value', sl)
        for i, o in enumerate(orig):
            me = o.data
            m = so == i
            uv = np.zeros((len(me.loops), 2), np.float32)
            uv[sl[m]] = buf[m]
            me.uv_layers['PSX'].data.foreach_set('uv', uv.reshape(-1))
            me.materials.clear()
            me.materials.append(m_)
        drop_proxy(px, orig)
    INFO['atlases'][name]['seconds'] = round(time.time() - t1, 1)
    del prep
hidden(GLASS + OVERLAY, False)

# ------------------------------------------------------------------ 3. the named materials, glass, panel; joins
MATDEF = {m['name']: m for m in json.load(open(os.path.join(HERE, 'main_u3_materials.json')))}


def u3_mat(name):
    """a material the game knows by name (Update 3's Forest_Materials.json values, for the renders here)"""
    m = bpy.data.materials.get(name)
    if m:
        return m
    d = MATDEF[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Base Color'].default_value = (*d['color'][:3], 1)
    pb.inputs['Roughness'].default_value = 1.0 - d.get('smoothness', 0.4)
    pb.inputs['Emission Color'].default_value = (*d['emission'][:3], 1)
    pb.inputs['Emission Strength'].default_value = float(d.get('emissionIntensity', 0.0))
    m['u3'] = json.dumps(d)
    return m


m_panel = PB.tex_mat('M_Main_Panel', PANEL_B, PANEL_E, 0.06, rough=0.6)
m_glass = P.psx_glass('M_GlassClear', tint=(0.10, 0.12, 0.13), alpha=0.30)
m_glass_d = P.psx_glass('M_GlassDark', tint=(0.02, 0.022, 0.025), alpha=0.85)
DARK_GLASS = ('IX_MainDoor_1_Glass',) + tuple(f'IX_RackDoor_{i}_Glass' for i in range(38, 45))
LENS = dict(MFX.LIT, screenoff='M_ScreenOff', ledoff='M_LEDOff', heatfault='M_HeatFault')


def mat_for(name):
    a = K.ATLAS[name]
    if a == 'glass':
        return m_glass_d if name in DARK_GLASS else m_glass
    if a == 'panel':
        return m_panel
    return u3_mat(LENS[a.split(':', 1)[1]])


def target_of(name):
    for suf in ('__lit2', '__lit', '__screen', '__led', '__fault', '__roof', '_Panel', '_Glass'):
        if name.endswith(suf):
            return name[:-len(suf)]
    raise ValueError(name)


joins = {}
for name in objs:
    if JOINED(K.ATLAS[name]) or name.endswith('__roof'):
        joins.setdefault(target_of(name), []).append(name)
for tgt, srcs in joins.items():
    T_ = objs[tgt]
    if not T_.data.materials:
        T_.data.materials.append(None)
    for s in srcs:
        o = objs[s]
        if JOINED(K.ATLAS[s]):                            # baked splits keep their atlas material
            o.data.materials.clear()
            o.data.materials.append(mat_for(s))
    P.select_only([objs[s] for s in srcs] + [T_], active=T_)
    bpy.ops.object.join()
    for s in srcs:
        del objs[s]
        C['parts'].pop(s, None)
    T_['joined'] = ','.join(srcs)
log('joined', sum(len(v) for v in joins.values()), 'objects into', len(joins))
for o in objs.values():                                   # the same material twice on one object -> one slot
    me = o.data
    seen = {}
    remap = []
    for i, m in enumerate(me.materials):
        remap.append(seen.setdefault(m.name if m else None, len(seen)))
    if len(seen) < len(me.materials):
        for poly in me.polygons:
            poly.material_index = remap[poly.material_index]
        mats = list(me.materials)
        me.materials.clear()
        done = set()
        for m in mats:
            if (m.name if m else None) not in done:
                me.materials.append(m)
                done.add(m.name if m else None)

# ------------------------------------------------------------------ 4. sockets: knocks (rays from outside), hands, audio
dg = bpy.context.evaluated_depsgraph_get()
nk = 0


def knock(name, org, d, parent_hint, note):
    global nk
    hit, loc, nrm, idx, ob, mw = bpy.context.scene.ray_cast(dg, Vector(org), Vector(d), distance=3.0)
    if not hit:
        log('WARN knock ray missed', name)
        return
    par = ob.name if ob.name in objs else parent_hint
    if nrm.dot(Vector(d)) > 0:
        nrm = -nrm
    C['sockets'][name] = dict(pos=r4(loc + nrm * 0.005), kind='knock', parent=par, root=C['parts'][par]['root'],
                              dir=r4(nrm), note=note)
    nk += 1


for w in S.WINDOWS:
    if w.get('internal'):
        continue
    ax, a0, a1 = w['wall']
    aout = a0 if abs(a0) > abs(a1) else a1
    sg = 1 if aout > 0 else -1
    zm = (w['z'][0] + w['z'][1]) / 2
    for sh in (w['shutters'] or [(None, w['u'][0], w['u'][1])]):
        nm, u0, u1 = sh
        um = (u0 + u1) / 2
        org = (aout + sg * 1.2, um, zm) if ax == 'x' else (um, aout + sg * 1.2, zm)
        d = (-sg, 0, 0) if ax == 'x' else (0, -sg, 0)
        knock('Knock_' + (nm[3:] if nm else w['name']), org, d, nm or 'BaseMain',
              'something knocks / scratches on the shutter (window) from outside' if nm else
              'something knocks on the glass from outside')
for name, d in S.DOORS.items():
    if d['out'] != 'Exterior':
        continue
    ax, a0, a1 = d['wall']
    aout = a0 if name == 'IX_RoofDoor_17' else (a0 if abs(a0) > abs(a1) else a1)    # the roof door: the roof is south
    sg = 1 if (aout > (a0 + a1) / 2) else -1
    um = (d['u'][0] + d['u'][1]) / 2
    z = d['z'][0] + 1.25
    org = (aout + sg * 1.2, um, z) if ax == 'x' else (um, aout + sg * 1.2, z)
    knock('Knock_' + name[3:], org, (-sg, 0, 0) if ax == 'x' else (0, -sg, 0), name, 'fists on the door from outside')
G = S.GARAGE_GATE
knock('Knock_GarageGate_18', ((G['u'][0] + G['u'][1]) / 2, -6.2, 1.3), (0, 1, 0), G['name'], 'the gate rattles: hit from outside')
INFO['knock_points'] = nk
for name, d in S.DOORS.items():                           # the handle on both faces: the free edge, 1.05 above the floor
    ax, a0, a1 = d['wall']
    u0, u1 = d['u']
    free = u1 if abs(d['hinge'] - u0) < abs(d['hinge'] - u1) else u0
    uh = free - 0.08 if free == u1 else free + 0.08
    pa = d.get('piv_x', d.get('piv_y'))
    zh = d['z'][0] + 1.05
    for side, a in (('A', min(a0, a1) - 0.07), ('B', max(a0, a1) + 0.07)):
        p = (a, uh, zh) if ax == 'x' else (uh, a, zh)
        K.socket(f'Hand_{name[3:]}_{side}', p, 'hand', parent=name, root='BaseMain', note='the handle (lever / pull)')
K.socket('Hand_GarageGate_18', ((G['u'][0] + G['u'][1]) / 2, -5.12, G['z'][0] + 0.95), 'hand', parent=G['name'],
         root='BaseMain', note='the gate\'s handle outside (up-and-over: lift here)')
for nm, p, note in (('Audio_Burner', (6.17, -2.32, S.UG_F + 0.78), 'the oil burner: ignition click, the roar, the fault hum'),
                    ('Audio_Boiler', (6.25, -1.65, S.UG_F + 1.0), 'the boiler ticks as it heats and cools'),
                    ('Audio_ServerRacks', (4.13, 5.0, 1.0), 'fans and relays in the racks (with power)'),
                    ('Audio_Fridge', (7.09, -1.785, S.OG_F + 0.9), 'the fridge hums and clicks (with power)'),
                    ('Audio_Chimney', (7.40, -1.40, 2.0), 'wind in the flue'),
                    ('Audio_GarageGate', ((G['u'][0] + G['u'][1]) / 2, -4.85, 2.0), 'the gate: springs, the steel rattles')):
    K.socket(nm, p, 'audio', parent='BaseMain', root='BaseMain', note=note)

# ------------------------------------------------------------------ 5. part boxes, light masks, the U3 data
nb = 0
for k_, p in C['parts'].items():
    o = objs.get(k_)
    p['object'] = k_ if o else None
    if o is None or p['kind'] == 'static':
        continue
    co = np.array([tuple(v.co) for v in o.data.vertices])
    lo, hi = co.min(0), co.max(0)
    p['box'] = dict(center=r4((lo + hi) / 2), size=r4(np.maximum(hi - lo, 0.004)))
    nb += 1
INFO['part_boxes'] = nb
MASK = {a['node']: a['mask'] for a in U3['assign']}
U3IX = {i['child']: i for i in U3['interactables']}
# Update 3 values that do not work with Update 3's own layout (kept as they are; the fix belongs to the game data)
U3_ISSUES = {n: 'Update 3 range 0..0.5 m: this pedestal faces the pedestal of IX_Drawer_35..37, 0.20 m in front of the '
                'drawer fronts - pulled out further the drawer runs into it. Recommended max 0.20 (kept 0.5 here, as '
                'Update 3)' for n in ('IX_Drawer_31', 'IX_Drawer_32', 'IX_Drawer_33', 'IX_Drawer_34')}
nomask = []
for k_, p in C['parts'].items():
    anc = p.get('parent')
    while anc and anc not in MASK:
        anc = C['parts'][anc].get('parent')
    if k_ in MASK:
        p['lightMask'] = MASK[k_]
    elif anc and anc != 'BaseMain':                       # Update 3: a node's children share its mask
        p['lightMask'] = MASK[anc]
        nomask.append(k_)
    else:
        q = Vector(p['pivot'])
        rm = next((rn for rn, R in S.ROOMS.items() if R['x0'] <= q.x <= R['x1'] and R['y0'] <= q.y <= R['y1'] and
                   R['f'] - 0.05 <= q.z <= R['c'] + 0.05), None)
        p['lightMask'] = (1 << S.ROOMS[rm]['layer']) if rm else 2
        nomask.append(k_)
    p['pivotUnity'] = to_unity(p['pivot'])
    if k_ in U3IX:
        u = U3IX[k_]
        p['u3'] = dict(kind=u['kind'], axisUnity=u['axis'], min=u['min'], max=u['max'], locked=u.get('locked', False))
    if k_ in U3_ISSUES:
        p['u3Issue'] = U3_ISSUES[k_]
    o = objs.get(k_)
    if o is not None:
        p['materials'] = [m.name for m in o.data.materials if m]
INFO['mask_derived'] = nomask
log('light masks: Update 3', len(C['parts']) - len(nomask), 'derived', len(nomask), nomask[:12])
ixs = [n for n in C['parts'] if n.startswith('IX_')]
miss_ix = sorted(set(U3IX) - set(ixs))
extra_ix = sorted(set(ixs) - set(U3IX))
INFO['ix'] = dict(count=len(ixs), u3=len(U3IX), missing=miss_ix, extra=extra_ix)
log('IX parts', len(ixs), 'of Update 3', len(U3IX), 'missing', miss_ix, 'extra', extra_ix)
fx_names = {n for n in C['parts'] if n.startswith('FX_')}
fx_lights = [L for pl in U3['prefabLights'] for L in pl['lights']]
INFO['lights'] = dict(u3=len(fx_lights), fixture_missing=sorted({L.get('fx') for L in fx_lights if L.get('fx') and
                                                                L['fx'] not in fx_names}))
C['lighting'] = dict(U3['lighting'], assign='every part carries lightMask (Update 3 assign where the node existed)')
C['prefabLights'] = U3['prefabLights']
C['prefabGlows'] = U3['prefabGlows']
C['power'] = U3['power']

# ------------------------------------------------------------------ 6. meta, stats, save
C['meta'] = dict(
    units='metres, degrees',
    frames='the building frame (both prefabs): x east, y north, z up, origin = the ground floor\'s finished level at the '
           'middle of the main block (ground floor 0.0, upper floor 3.40, basement -3.00, roof 6.60, garage floor -0.15, '
           'the yard at the entrance -0.45) - the frame of Update 3\'s BaseMain.fbx after import',
    unity='position (x, y, z) -> Unity prefab-local (-x, z, -y) (pivotUnity given); a hinge\'s Blender axis is Update 3\'s '
          'Unity axis as (X, Z, -Y) with angle -> -angle, a slide\'s (-X, -Z, Y); u3.axisUnity / min / max are Update 3\'s '
          'values and stay valid (same names, pivots and ranges); part.box: the grab / hit box of a moving part in its '
          'own frame',
    map_placement=dict(BaseMain=PLACE, BaseMain_Opening=PLACE),
    hierarchy='BaseMain (exterior) > R_<Room> x15, IX_* (131), FX_* (64); BaseMain_Opening (its own prefab, same place) > '
              'its 8 IX parts. Glass, signs, lenses, screens and LEDs are joined into their objects as extra materials',
    colliders='as Update 3: a MeshCollider on every mesh object (static ones and the IX parts, glass included); no '
              'separate boxes',
    light_layers='lightMask per part = 1 << layer of its room (Exterior 1 -> 2); BaseMain_Opening 160 (Heizung + Flur_UG), '
                 'IX_MainDoorBar_311 128 (Windfang), as Update 3; prefabLights / prefabGlows are Update 3\'s, unchanged '
                 '(the fixtures stand where they stood)',
    materials='M_Main_Ext / M_Main_Roof (on BaseMain) / M_Main_Rm_<Room> / M_Main_Parts (+ the fixtures) / M_Main_Opening: baked PSX atlases (point filter, '
              'no mips); M_Main_Panel: signs, labels, papers, dials (+ emission map: the exit pictogram, the lenses); '
              'named materials kept from Update 3 (the game swaps or knows them): M_ScreenOff (screens, -> M_ScreenOn '
              'with power), M_LEDOff (-> M_LEDOn), M_HeatFault (the STOERUNG lamp and the reset button, -> M_HeatFaultOn), '
              'the fixtures\' M_FX_Tube / Globe / Diffuser / Bulb / Exit / EmergencyLens / Halogen / Red and M_LEDOn, '
              'M_GlassClear, M_GlassDark - their definitions stay those of Forest_Materials.json',
    sockets='knock: a point on the outside of each shutter / window / exterior door (scares X06 / X07); hand: door '
            'handles on both faces; audio: plant noises',
    model='main.blend', textures='tex/main')
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    uvs = o.data.uv_layers
    if 'PSX' in uvs:
        for u in [u for u in uvs if u.name != 'PSX']:
            uvs.remove(u)
        uvs['PSX'].active = True
        uvs['PSX'].active_render = True
sfx = '_test' if ONLY is not None else ''
json.dump(_nz(C), open(os.path.join(OUT, f'main_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
kinds = {}
for p in C['parts'].values():
    kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
INFO['contract'] = dict(parts=len(C['parts']), sockets=len(C['sockets']), kinds=kinds)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
INFO['tris'] = sum(P.tri_count(o) for o in meshes)
INFO['tris_by_root'] = {}
INFO['tris_big'] = sorted(((P.tri_count(o), o.name) for o in meshes), reverse=True)[:20]
for o in meshes:
    r = C['parts'][o.name]['root']
    INFO['tris_by_root'][r] = INFO['tris_by_root'].get(r, 0) + P.tri_count(o)
INFO['objects'] = len(meshes)
INFO['materials'] = sorted({m.name for o in meshes for m in o.data.materials if m})
log('contract', INFO['contract'], 'tris', INFO['tris'], INFO['tris_by_root'], 'objects', len(meshes))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'main{sfx}.blend'))
json.dump(INFO, open(os.path.join(OUT, f'main{sfx}.json'), 'w'), indent=1)
log('saved main' + sfx)
