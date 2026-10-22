"""Forest Update 7 as it would stand in the game: the in-game forest scene (allblend/Forest_game.blend: Update 3's
location with the models of Updates 4-6), the base drawn in (ForestYardPlan x0.7071 about (340, -360)) and the checkpoint
moved (ForestRelocation) as the Unity side does it, Update 3's chain-link fence gone, the trees of the U7 data removed,
and the U7 kit placed from u7_layout.json. Cycles by day.
python3 -I u7_preview.py -- <Forest_game.blend> <fences.blend> <u7_layout.json> <out_dir> [spp] [views] [--save x.blend]"""
import bpy, sys, os, json, math
sys.path.insert(0, '/home/claude/uaz')
import numpy as np
import psxlib as P
from mathutils import Matrix, Vector, Quaternion
from mathutils.kdtree import KDTree
a = sys.argv[sys.argv.index('--') + 1:]
SAVE = a[a.index('--save') + 1] if '--save' in a else None
a = [x for i, x in enumerate(a) if x not in ('--save', '--from') and (i == 0 or a[i - 1] not in ('--save', '--from'))]
GAME, KIT, U7, OUT = a[0], a[1], a[2], a[3]
SPP = int(a[4]) if len(a) > 4 else 24
ONLY = set(a[5].split(',')) if len(a) > 5 and a[5] != 'all' else None
os.makedirs(OUT, exist_ok=True)
FROM = sys.argv[sys.argv.index('--from') + 1] if '--from' in sys.argv else None
bpy.ops.wm.open_mainfile(filepath=FROM or GAME)
sc = bpy.context.scene
PCTEX = '/home/claude/pcstage/locations/_blend/textures'           # the location's textures (the blend's paths point elsewhere)
fixed = 0
for im in bpy.data.images:
    if im.source == 'FILE' and im.packed_file is None and not os.path.exists(bpy.path.abspath(im.filepath)):
        alt = os.path.join(PCTEX, os.path.basename(bpy.path.abspath(im.filepath)))
        if os.path.exists(alt):
            im.filepath = alt
            im.reload()
            fixed += 1
print('textures re-pointed', fixed, flush=True)
U = json.load(open(U7))
C = Matrix(((-1, 0, 0), (0, 0, -1), (0, 1, 0)))          # Unity -> Blender of this map: (x, y, z) -> (-x, -z, y)
Ci = C.transposed()


def u2b(p, q):
    R = Quaternion((q[3], q[0], q[1], q[2])).to_matrix()
    M = (C @ R @ Ci).to_4x4()
    M.translation = C @ Vector(p)
    return M


def b2u(t):
    return Ci @ Vector(t)


def yaw_q(deg):
    h = math.radians(deg) / 2
    return [0.0, math.sin(h), 0.0, math.cos(h)]


def unity_yaw(M):
    """yaw (deg) of a yaw-only placement from its Blender matrix (Blender rotation z = -yaw)"""
    R = Ci @ M.to_3x3() @ C
    return math.degrees(math.atan2(R[0][2], R[2][2]))


if not FROM:                                                       # steps 1-5 (a saved scene has them done)
    # ---------------------------------------------------------------- 1. Update 3's chain-link out; the wires out (they hang
    # between the poles' old places)
    reb = bpy.data.collections['Rebuilt (Updates 4-6)']
    gone = 0
    for o in list(reb.objects):
        if o.name.startswith(('FenceChain_u46', 'Forest_Wires_u46')):
            bpy.data.objects.remove(o, do_unlink=True)
            gone += 1
    print('removed fence sections and wires', gone, flush=True)

    # ---------------------------------------------------------------- 2. the checkpoint moved (ForestRelocation)
    REL_OLD = Vector((310.945, 16.0509, -282.1992))
    REL_NEW = Vector((143.51488, 9.27351, -64.67514))
    REL_YAW = -65.3345


    def reloc(p):
        t = math.radians(REL_YAW)
        dx, dz = p[0] - REL_OLD[0], p[2] - REL_OLD[2]
        return Vector((REL_NEW[0] + dx * math.cos(t) + dz * math.sin(t), REL_NEW[1] + (p[1] - REL_OLD[1]),
                       REL_NEW[2] - dx * math.sin(t) + dz * math.cos(t)))


    for nm in ('Barrier_u46', 'Checkpoint_u46'):
        o = bpy.data.objects[nm]
        p = b2u(o.matrix_world.translation)
        o.matrix_world = u2b(reloc(p), yaw_q(unity_yaw(o.matrix_world) + REL_YAW))
        print('moved', nm, tuple(round(v, 3) for v in reloc(p)))

    # ---------------------------------------------------------------- 3. the base drawn in (ForestYardPlan), structures and items
    YC, YS, YR = (340.0, -360.0), 0.7071, 135.0
    STRUCT = ('BaseMain', 'BaseMain_Opening', 'LightPole', 'PowerPole', 'Crates', 'Garage', 'Trafo', 'GenContainer', 'FuelTanks',
              'Helipad', 'RadioMast', 'Hatch', 'LogPile', 'Gate')
    mapped = 0


    def ymap_obj(o):
        global mapped
        p = b2u(o.matrix_world.translation)
        d = math.hypot(p[0] - YC[0], p[2] - YC[1])
        if d > YR:
            return
        q = Vector((YC[0] + (p[0] - YC[0]) * YS, p[1], YC[1] + (p[2] - YC[1]) * YS))
        M = o.matrix_world.copy()
        M.translation = C @ q
        o.matrix_world = M
        mapped += 1


    for o in reb.objects:
        if o.name.split('_u46')[0] in STRUCT:
            ymap_obj(o)
    for cname in ('Items (opening + dressing)', 'Van (Car_Start)'):
        col = bpy.data.collections.get(cname)
        if col:
            for o in col.objects:
                if o.parent is None:
                    ymap_obj(o)
    print('drawn in', mapped)
    for cname in ('Lights', 'Lights_Power', 'Lights_BV', 'Viewpoints'):
        lc = sc.view_layers[0].layer_collection.children.get(cname)
        if lc:
            lc.exclude = True
    for o in bpy.data.collections['World'].objects:
        if o.name.startswith('Mist_'):
            o.hide_render = True

    # ---------------------------------------------------------------- 4. the trees the U7 data removes
    inst = [o for c in bpy.data.collections['Instances'].children for o in c.objects]
    kd = KDTree(len(inst))
    for i, o in enumerate(inst):
        kd.insert(o.matrix_world.translation, i)
    kd.balance()
    rem = 0
    for t in U['removed_trees']:
        co, i, d = kd.find(C @ Vector(t['p']))
        if d is not None and d < 0.02:
            bpy.data.objects.remove(inst[i], do_unlink=True)
            inst[i] = None
            rem += 1
    print('trees removed', rem, 'of', len(U['removed_trees']))

    # ---------------------------------------------------------------- 5. the kit, instanced at the U7 placements
    lib = bpy.data.collections.new('Library_U7')
    sc.collection.children.link(lib)
    with bpy.data.libraries.load(KIT, link=False) as (src, dst):
        dst.collections = [n for n in src.collections]
    kitcol = {}
    for c in dst.collections:
        if c is None or c.name not in bpy.data.objects:
            continue
        lib.children.link(c)
        c.instance_offset = bpy.data.objects[c.name].location.copy()   # (matrix_world is not set yet after an append)
        kitcol[c.name] = c
    for o in bpy.data.objects:
        if o.name.startswith(('AOG', 'COL_')) and o.users_collection and o.users_collection[0].name in kitcol:
            o.hide_render = True
    sc.view_layers[0].layer_collection.children['Library_U7'].exclude = True
    u7 = bpy.data.collections.new('Update 7 (fences, blocks)')
    sc.collection.children.link(u7)
    for k, r in enumerate(U['records']):
        e = bpy.data.objects.new('%s_u7_%03d' % (r['m'], k), None)
        e.instance_type = 'COLLECTION'
        e.instance_collection = kitcol[r['m']]
        e.empty_display_size = 0.5
        e.matrix_world = u2b(r['p'], r['q'])
        u7.objects.link(e)
    print('kit placements', len(U['records']))
    for m in bpy.data.materials:                                         # point filter
        if m.use_nodes and m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE':
                    n.interpolation = 'Closest'
    if SAVE:
        bpy.ops.wm.save_as_mainfile(filepath=SAVE, compress=True)
        print('saved', SAVE)

# the kit's instance offsets: each model stands in the showroom row at its own x (also for a scene saved before this fix)
for c in bpy.data.collections['Library_U7'].children:
    if c.name in bpy.data.objects:
        c.instance_offset = bpy.data.objects[c.name].location.copy()
# ---------------------------------------------------------------- 6. light, cameras
for o in list(sc.objects):
    if o.type == 'LIGHT' and o.data.type == 'SUN':
        o.hide_render = True
P.world((0.55, 0.62, 0.74), 1.0)
P.sun(4.2, (38, 0, 200))
P.setup_cycles((1280, 720), SPP)
sc.cycles.max_bounces = 3
sc.render.use_persistent_data = True
B = json.load(open('/home/claude/fence/map_big.json'))
from scipy.interpolate import LinearNDInterpolator
_T = np.array(B['terrain'])
_g = LinearNDInterpolator(_T[:, [0, 2]], _T[:, 1])


def gy(x, z):
    return float(_g(x, z))


def V2(v):
    return np.array(v, float)


Bk = U['barrier']
BP, REST, RIN = V2(Bk['post']), V2(Bk['rest']), V2(Bk['road_in'])
ARM = (REST - BP) / np.linalg.norm(REST - BP)
R = np.array(json.load(open('/home/claude/fence/map_forest.json'))['road'])
R = R[np.hypot(R[:, 0] - BP[0], R[:, 2] - BP[1]) < 70]


def road_mid(a_):
    rel = R[:, [0, 2]] - BP
    s = np.abs(rel @ RIN - a_) < 2.5
    c = rel[s] @ ARM
    return (c.min() + c.max()) / 2


def kpp(a_, c_, h):
    p = BP + RIN * a_ + ARM * c_
    return (p[0], gy(*p) + h, p[1])


def at(p2, h):
    return (p2[0], gy(*p2) + h, p2[1])


G = U['gate']
GP = V2(G['game'])[[0, 2]]
GX = (V2(G['east_end']) - V2(G['west_end'])) / np.linalg.norm(V2(G['east_end']) - V2(G['west_end']))
gn = np.array([GX[1], -GX[0]])
gout = gn if gn @ (GP - V2([340.0, -360.0])) > 0 else -gn
ln = U['lines']['teeth_post_NE']
LA, LB = V2(ln['A']), V2(ln['B'])
LD = (LB - LA) / np.linalg.norm(LB - LA)
Lout = V2(ln['outer'])
W = V2(U['wicket'])
HATCH = V2(U['context']['Hatch'])
VIEWS = {
    'kpp_driver': (kpp(-46.0, road_mid(-46.0), 1.9), kpp(0.0, 2.8, 1.0), 34.0),
    'kpp_air': (kpp(-34.0, road_mid(-34.0) - 4.0, 30.0), kpp(2.0, 3.0, 0.0), 30.0),
    'kpp_inside': (kpp(26.0, -7.0, 2.2), kpp(0.0, 3.5, 1.0), 30.0),
    'funnel_line': (at(LA + LD * 118.0 - Lout * 5.0, 1.7), at(LA + LD * 160.0, 0.4), 30.0),
    'funnel_out': (at(LA + LD * 155.0 + Lout * 9.0, 2.6), at(LA + LD * 165.0 + Lout * 0.8, 0.6), 28.0),
    'gate': (at(GP + GX * 3.5 + gout * 22.0, 2.4), at(GP + GX * 3.5, 1.2), 30.0),
    'corner_NW': (at(V2(U['corners']['NW']) + V2([-30.0, 26.0]), 16.0), at(V2(U['corners']['NW']) + V2([4.0, -6.0]), 0.0), 30.0),
    'wicket': (at(HATCH + (HATCH - W) / np.linalg.norm(HATCH - W) * 9.0 + V2([-4.0, 0.0]), 1.8), at(W, 1.1), 32.0),
    'overview': ((60.0, 190.0, -360.0), (285.0, 10.0, -195.0), 28.0),
}


def cam(name, eye, target, lens):
    cd = bpy.data.cameras.new(name)
    co = bpy.data.objects.new(name, cd)
    sc.collection.objects.link(co)
    e, t = C @ Vector(eye), C @ Vector(target)
    co.location = e
    co.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler()
    cd.lens = lens
    cd.clip_start = 0.1
    cd.clip_end = 2000
    sc.camera = co


for nm, (eye, tgt, lens) in VIEWS.items():
    if ONLY and nm not in ONLY:
        continue
    cam(nm, eye, tgt, lens)
    P.render(os.path.join(OUT, nm + '.png'))
    print('rendered', nm, flush=True)
print('done')
