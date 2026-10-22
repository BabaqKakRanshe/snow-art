"""Forest Update 7 placements, in the frame of the game as it is now: after the Unity side's ForestYardPlan (the yard drawn
in x0.7071 towards the main building) and ForestRelocation (the checkpoint 274 m out along the road).
  1. the base perimeter: PO-2 panels along the drawn-in chain-link fence's lines (which they replace), up to the gate
     (as drawn in) on both sides; the 8 m hole beside the gate and the 9 m walk-through to the hatch are gone (a wicket
     in the south side instead of the walk-through);
  2. the checkpoint: wings of PO-2 from the barrier's post and its rest along the barrier's line, FBS blocks at the wing
     roots, two staggered pairs of concrete barriers on the approach (a chicane a van takes at walking pace), the HALT
     board and the no-entry sign, concertina, hedgehogs and a cheval de frise in front of the wings;
  3. the funnel: lines of dragon's teeth (an abatis here and there) from the wings' ends to the perimeter's corners, so a
     car reaches the gate only through the barrier; people walk between the teeth.
Checks here: trees in the way (removed from the data, listed), the giant's bones (Blender BVH probe, bone_probe.py),
the free gaps along each blocking line (none wider than MAX_GAP), the ground under every piece.
python3 fence_layout.py -> out/forest_update7/u7_layout.json"""
import json, math, os, sys, subprocess, hashlib
import numpy as np
from collections import Counter
HERE = '/home/claude/uaz'
FENCE = '/home/claude/fence'
LAYOUT = os.path.join(HERE, 'out/forest_update6/stage/Assets/Locations/Forest/Data/Forest_Layout.json')
OUT = os.path.join(HERE, 'out/forest_update7')
FOREST_BLEND = '/home/claude/pcstage/locations/_blend/Forest.blend'
L = json.load(open(LAYOUT))
rng = np.random.default_rng(2026)

# ---------------------------------------------------------------- the game's transforms (read from the project, 21.10)
YARD_C, YARD_S, YARD_R = np.array([340.0, -360.0]), 0.7071, 135.0            # ForestYardPlan
REL_OLD = np.array([310.945, 16.0509, -282.1992])                            # ForestRelocation: the barrier's pivot
REL_NEW = np.array([143.51488, 9.27351, -64.67514])
REL_YAW = -65.3345
GATE_GAME = np.array([313.23465, 16.018454, -309.11115])                    # the Gate as drawn in
HATCH_GAME = np.array([353.13382, 16.236992, -418.96973])                   # the shaft hatch as drawn in


def ymap(p):
    p = np.asarray(p, float)
    return p if np.hypot(*(p - YARD_C)) > YARD_R else YARD_C + (p - YARD_C) * YARD_S


def yaw_of(q):
    return math.degrees(2 * math.atan2(q[1], q[3]))


def q_of(yaw):
    h = math.radians(yaw) / 2
    return [0.0, round(math.sin(h), 6) + 0.0, 0.0, round(math.cos(h), 6) + 0.0]


def ux_of(yaw):                       # Unity local +x in the world (x, z)
    t = math.radians(yaw)
    return np.array([math.cos(t), -math.sin(t)])


def uz_of(yaw):                       # Unity local +z = Blender -y: the outer face of a kit piece
    t = math.radians(yaw)
    return np.array([math.sin(t), math.cos(t)])


def yaw_facing(n):
    """the yaw that turns a kit piece's outer face (Blender -y = Unity +z) to the direction n"""
    return math.degrees(math.atan2(n[0], n[1]))


def bx_of(yaw):                       # Blender +x of a kit piece in the world = -(Unity +x)
    return -ux_of(yaw)


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


# ---------------------------------------------------------------- the ground (Update 3's terrain = the Unity Terrain's source)
B = json.load(open(os.path.join(FENCE, 'map_big.json')))
TER = np.array(B['terrain'])
from scipy.interpolate import LinearNDInterpolator
_g = LinearNDInterpolator(TER[:, [0, 2]], TER[:, 1])


sys.path.insert(0, FENCE)
import game_ground as GG                              # the game's Terrain (after the integration's levelling), 22.10


def ground_u3(x, z):
    h = float(_g(x, z))
    return h if not math.isnan(h) else 0.0


def ground(x, z):
    """the ground of the game: Unity Terrain tile 1_1 as the project has it (the yard's and the checkpoint's pads
    levelled by the integration, hummocks, erosion); the pieces stand on it"""
    return GG.ground(x, z)


def ground_box(c, yaw, hx, hz):
    """the ground at the centre and the four corners of a footprint (half sizes along Unity x, z)"""
    ux, uz = ux_of(yaw), uz_of(yaw)
    pts = [c] + [c + ux * sx * hx + uz * sz * hz for sx in (-1, 1) for sz in (-1, 1)]
    return [ground(*p) for p in pts]


# ---------------------------------------------------------------- trees: trunks (obstacles) and the small stuff
TRUNK = {'SpruceHC': 0.30, 'Spruce': 0.30, 'Fir': 0.30, 'Pine': 0.30, 'Larch': 0.28, 'Birch': 0.20, 'Dead': 0.20, 'Snag': 0.22}
TREES = []                                  # (index, x, z, trunk radius or 0 for bush/fern/weeds)
for i, t in enumerate(L['trees']):
    pre = t['m'].split('_')[0]
    TREES.append((i, t['p'][0], t['p'][2], TRUNK.get(pre, 0.0) * t.get('s', 1.0)))
TREE_XZ = np.array([[x, z] for _, x, z, _ in TREES])
TREE_R = np.array([r for *_, r in TREES])
REMOVED = {}                                # tree index -> why


def trees_near(c, rad):
    d = np.hypot(TREE_XZ[:, 0] - c[0], TREE_XZ[:, 1] - c[1])
    return [k for k in np.nonzero(d < rad + 0.35)[0] if k not in REMOVED]


def in_box(p, c, yaw, hx, hz, pad=0.0):
    r = np.asarray(p) - c
    return abs(r @ ux_of(yaw)) <= hx + pad and abs(r @ uz_of(yaw)) <= hz + pad


def clear_box(c, yaw, hx, hz, why, trunks=True):
    """remove the trees whose trunk (or, for the small stuff, whose root) is inside the footprint; returns the trunks
    that are (when trunks=False nothing is removed for those and they are reported instead)"""
    hit = []
    for k in trees_near(c, math.hypot(hx, hz) + 0.5):
        r = TREE_R[k]
        if in_box(TREE_XZ[k], c, yaw, hx, hz, pad=r + (0.10 if r > 0 else 0.0)):
            if r > 0 and not trunks:
                hit.append(k)
            else:
                REMOVED[k] = why
    return hit


# ---------------------------------------------------------------- the giant's bones along a line (Blender BVH, cached)
BONE_CACHE = os.path.join(FENCE, 'bone_cache.json')
_bc = json.load(open(BONE_CACHE)) if os.path.exists(BONE_CACHE) else {}


def bone_runs(A, Bp):
    key = '%.3f,%.3f,%.3f,%.3f' % (A[0], A[1], Bp[0], Bp[1])
    if key not in _bc:
        q = os.path.join(FENCE, 'bq_one.json')
        o = os.path.join(FENCE, 'bq_one_out.json')
        json.dump(dict(lines=[[list(map(float, A)), list(map(float, Bp))]], step=0.1, half=0.55, zlo=0.15, zhi=2.2,
                       ground=os.path.join(FENCE, 'map_big.json')), open(q, 'w'))
        subprocess.run(['python3', '-I', os.path.join(FENCE, 'bone_probe.py'), '--', FOREST_BLEND, q, o], check=True,
                       capture_output=True)
        _bc[key] = json.load(open(o))['lines'][0]['occupied']
        json.dump(_bc, open(BONE_CACHE, 'w'))
    return _bc[key]


# ---------------------------------------------------------------- the records
RECS = []                                   # (group, record)
SOCKETS = []


def put(m, c, yaw, group, y=None, note=None):
    c = np.asarray(c, float)
    yy = ground(*c) if y is None else y
    r = dict(m=m, p=[round(float(c[0]), 4) + 0.0, round(float(yy), 4) + 0.0, round(float(c[1]), 4) + 0.0], q=q_of(yaw))
    RECS.append((group, r, note))
    return r


# footprints (half sizes along Blender x / y = Unity -x / -z; symmetric enough) for the clearing and the gap checks
FOOT = {'ConcreteFence': (1.25, 0.12), 'ConcreteFence_b': (1.25, 0.12), 'ConcreteFence_Broken': (1.25, 0.12),
        'ConcreteFence_Sign': (1.25, 0.12), 'ConcreteFence_Plain': (1.25, 0.12), 'ConcreteFence_Wicket': (1.25, 0.12),
        'ConcreteFence_Socket': (0.48, 0.38), 'TankTooth': (0.5, 0.5), 'TankTooth_b': (0.5, 0.5),
        'RoadBlock_FBS': (1.19, 0.20), 'RoadBlock_Jersey': (1.0, 0.31), 'RoadBlock_Jersey_Striped': (1.0, 0.31),
        'RoadBlock_Cube': (0.5, 0.5), 'WireCoil': (2.5, 0.48), 'WireBarricade': (1.5, 0.75), 'Hedgehog': (0.8, 0.8),
        'Abatis': (4.3, 1.35), 'Abatis_b': (3.8, 1.3), 'Sign_Halt': (0.62, 0.10), 'Sign_NoEntry': (0.30, 0.08)}
FOOT_OFF = {'Abatis': -0.55, 'Abatis_b': -0.75}           # the footprint's centre on Blender y (the crowns go out, -y)


def foot_centre(m, c, yaw):
    return np.asarray(c) - uz_of(yaw) * FOOT_OFF.get(m, 0.0)    # Blender y -> Unity -z


def place(m, c, yaw, group, y=None, clear=True, note=None):
    hx, hz = FOOT[m]
    fc = foot_centre(m, c, yaw)
    if clear:
        clear_box(fc, yaw, hx + 0.15, hz + 0.15, '%s %s' % (group, m))
    return put(m, c, yaw, group, y=y, note=note)


# ================================================================ 1. the base perimeter
FC = [r for r in L['rocks'] if r['m'] == 'FenceChain']


def side_line(yaw):
    pts = np.array([[r['p'][0], r['p'][2]] for r in FC if round(yaw_of(r['q'])) == yaw])
    return pts.mean(0), ux_of(yaw)


def intersect(l1, l2):
    (p, d), (q, e) = l1, l2
    t = np.linalg.solve(np.array([d, -e]).T, q - p)
    return p + d * t[0]


SIDE = {'N': side_line(8), 'W': side_line(-82), 'S': side_line(188), 'E': side_line(98)}
CORNERS_U3 = {'NW': intersect(SIDE['N'], SIDE['W']), 'NE': intersect(SIDE['N'], SIDE['E']),
              'SE': intersect(SIDE['S'], SIDE['E']), 'SW': intersect(SIDE['S'], SIDE['W'])}
CORNERS = {k: ymap(v) for k, v in CORNERS_U3.items()}
g_yaw = yaw_of(next(p for p in L['prefabs'] if p['m'] == 'Gate')['q'])
GX = ux_of(g_yaw)                                    # the gate's Unity +x: the fixed panel at -2.37, the receiver at +7.18
# the runs end clear of the gate: its fixed panel ends at Unity x -2.43, the receiver post at +7.40; a run's end socket
# (0.95 m) stands just beyond them (gaps of 0.5 m above the sockets: nobody walks through)
GATE_W, GATE_E = GATE_GAME[[0, 2]] + GX * -2.925, GATE_GAME[[0, 2]] + GX * 7.90
GATE_Y = float(GATE_GAME[1])
LEAF_TRAVEL = (-6.6 - 0.5, 0.4)          # Unity x of the leaf opened (it runs 0.185..0.255 m inside, its foot 0.05 m up)
GAP_U3 = (np.array([364.9, -434.2]) + np.array([356.0, -432.9])) / 2   # Update 3's walk-through in the south side
WICKET_AT = ymap(GAP_U3)
PO2 = 2.5
RUNS = {}
LOWERED = []
START_SOCKETS = []
CORNER_LOWERED = []
S_GAP = 0.02                                      # PO-2: 2.50 m apart, 2.48 m long


def po2_run(name, A, Bp, out_dir, group, signs=(), wicket_at=None, broken=(), pick=None, start_socket=True):
    """PO-2 panels from A to B, the relief (outer face) to out_dir. Each panel stands in its socket at its +x end; the
    run's first socket (with its outrigger) at the -x end of the first panel"""
    A, Bp = np.asarray(A, float), np.asarray(Bp, float)
    D = unit(Bp - A)
    n = np.array([D[1], -D[0]])
    if n @ out_dir < 0:
        n = -n
    yaw = yaw_facing(n)
    bx = bx_of(yaw)
    Lr = float(np.linalg.norm(Bp - A))
    k = max(1, int(round(Lr / PO2)))
    s = Lr / k
    xs = [A + D * s * (i + 0.5) for i in range(k)]
    if bx @ D < 0:                                   # the panels' +x runs from B to A: walk from B
        xs = xs[::-1]
    start = xs[0] - bx * s / 2
    wi = None
    if wicket_at is not None:
        wi = int(np.argmin([np.linalg.norm(c - wicket_at) for c in xs]))
    sign_i = {int(round(f * (k - 1))) for f in signs}
    broken_i = {int(round(f * (k - 1))) for f in broken}
    def in_leaf(p):
        """a socket the gate's leaf passes over when it opens (it runs 0.185..0.255 m inside, its foot 0.05 m up)"""
        r = p - GATE_GAME[[0, 2]]
        return group == 'perimeter' and LEAF_TRAVEL[0] <= r @ GX <= LEAF_TRAVEL[1] and abs(r @ np.array([GX[1], -GX[0]])) < 1.0

    def near_leaf(p):
        r = p - GATE_GAME[[0, 2]]
        return group == 'perimeter' and LEAF_TRAVEL[0] - 2.6 <= r @ GX < LEAF_TRAVEL[0] and abs(r @ np.array([GX[1], -GX[0]])) < 1.0

    def at_receiver(p, lo, hi):
        """the run beside the receiver post (Unity x of the gate +7.40): at the gate's level, not the ground's (the
        gate stands 0.31 m under Update 3's ground here; around it the Terrain was most likely brought down to it)"""
        r = p - GATE_GAME[[0, 2]]
        return group == 'perimeter' and lo <= r @ GX <= hi and abs(r @ np.array([GX[1], -GX[0]])) < 1.0

    low_y = GATE_Y - 0.04                            # the sockets' tops (0.08) under the leaf's foot (gate base + 0.05)
    if start_socket:
        y0 = ground(*start)
        if in_leaf(start):
            y0 = min(y0, low_y)
            LOWERED.append('ConcreteFence_Socket')
        place('ConcreteFence_Socket', start, yaw, group, y=y0)
        START_SOCKETS.append((len(RECS) - 1, start))
    overlap = s < PO2 - S_GAP                         # panels 2.48 m: closer than that they overlap at the joints
    for i, c in enumerate(xs):
        if i == wi:
            m = 'ConcreteFence_Wicket'
        elif i in sign_i:
            m = 'ConcreteFence_Sign'
        elif i in broken_i:
            m = 'ConcreteFence_Broken'
        elif pick is not None:
            m = pick(i, k)
        else:
            m = 'ConcreteFence' if rng.random() < 0.6 else 'ConcreteFence_b'
        sock = c + bx * s / 2
        y = ground(*c)
        if in_leaf(sock):
            y = min(y, low_y)
            LOWERED.append(m)
        elif near_leaf(sock):                         # the next one halfway down: two steps of the fence's top, not one
            y = min(y, (y + low_y) / 2)
            LOWERED.append(m + ' (half)')
        elif at_receiver(sock, 7.5, 8.5):
            y = min(y, GATE_Y)
            LOWERED.append(m + ' (receiver)')
        elif at_receiver(sock, 8.5, 11.0):
            y = min(y, (y + GATE_Y) / 2)
            LOWERED.append(m + ' (receiver, half)')
        cc = c + (n * 0.012 if overlap and i % 2 else 0.0)   # every other panel 12 mm out: the overlapping ends do not fight
        place(m, cc, yaw, group, y=y)
        SOCKETS.append((sock, y))
    RUNS[name] = dict(A=A.tolist(), B=Bp.tolist(), panels=k, spacing=round(s, 4), yaw=round(yaw, 3), length=round(Lr, 2),
                      outer=n.tolist())
    return RUNS[name]


C0 = YARD_C
ring = [('N_west', CORNERS['NW'], GATE_W), ('N_east', GATE_E, CORNERS['NE']), ('E', CORNERS['NE'], CORNERS['SE']),
        ('S', CORNERS['SE'], CORNERS['SW']), ('W', CORNERS['SW'], CORNERS['NW'])]
opts = {'N_west': dict(signs=(0.85,)), 'N_east': dict(signs=(0.08, 0.55)), 'E': dict(signs=(0.5,), broken=(0.30,)),
        'S': dict(signs=(0.2, 0.8), wicket_at=WICKET_AT, broken=(0.62,)), 'W': dict(signs=(0.5,), broken=(0.72,))}
for nm, a_, b_ in ring:
    po2_run(nm, a_, b_, unit((a_ + b_) / 2 - C0), 'perimeter', **opts[nm])

# a run's first socket where another run's last panel has its socket (the corners): 15 mm under it
for ri, p in START_SOCKETS:
    near = [y for q, y in SOCKETS if np.linalg.norm(q - p) < 0.6]
    if near:
        g_, r_, note_ = RECS[ri]
        r_['p'][1] = round(min(r_['p'][1], min(near)) - 0.015, 4) + 0.0
        CORNER_LOWERED.append(r_['m'])


# ================================================================ 2. the checkpoint (as moved)
def T(p):
    """ForestRelocation: Update 3's place -> the moved checkpoint's (x, y, z)"""
    p = np.asarray(p, float)
    t = math.radians(REL_YAW)
    d = np.array([p[0] - REL_OLD[0], p[2] - REL_OLD[2]])
    d = np.array([d[0] * math.cos(t) + d[1] * math.sin(t), -d[0] * math.sin(t) + d[1] * math.cos(t)])
    return np.array([REL_NEW[0] + d[0], REL_NEW[1] + (p[1] - REL_OLD[1]), REL_NEW[2] + d[1]])


bar = next(p for p in L['prefabs'] if p['m'] == 'Barrier')
booth = next(p for p in L['prefabs'] if p['m'] == 'Checkpoint')
BAR_YAW = yaw_of(bar['q']) + REL_YAW
BP = T(bar['p'])[[0, 2]]
BOOTH = T(booth['p'])[[0, 2]]
ARM = bx_of(BAR_YAW)                               # Blender +x of the barrier: from the post to the rest (5.6 m)
REST = BP + ARM * 5.6
perp = np.array([ARM[1], -ARM[0]])
ROAD_IN = perp if perp @ (BOOTH - BP) > 0 else -perp   # along the road, to the base (the booth is on the inside)
OUT_K = -ROAD_IN                                    # the approach
LANE = (BP + REST) / 2
WING = 30.0
W_POST0, W_REST0 = BP - ARM * 0.90, BP + ARM * 6.25    # sockets clear of the barrier's foot (0.375) and its rest (5.72)
W_POST1, W_REST1 = W_POST0 - ARM * WING, W_REST0 + ARM * WING
po2_run('KPP_post', W_POST0, W_POST1, OUT_K, 'kpp', signs=(0.10,), pick=lambda i, k: 'ConcreteFence_b' if i % 3 == 1 else 'ConcreteFence')
po2_run('KPP_rest', W_REST0, W_REST1, OUT_K, 'kpp', signs=(0.10,), pick=lambda i, k: 'ConcreteFence_b' if i % 3 == 1 else 'ConcreteFence')


def kpp(a, c):
    """a point in the checkpoint's road frame: a metres along the road (to the base +), c metres from the post along the
    boom (+ to the rest)"""
    return BP + ROAD_IN * a + ARM * c


yaw_road = yaw_facing(OUT_K)                        # outer faces to the approach
# FBS blocks in front of the wing roots, two high; a cube beside each
for c_, sg in ((-0.90 - 1.4, -1), (6.25 + 1.4, 1)):
    p = kpp(-1.3, c_)
    place('RoadBlock_FBS', p, yaw_road, 'kpp')
    put('RoadBlock_FBS', p, yaw_road, 'kpp', y=ground(*p) + 0.58)
    place('RoadBlock_Cube', kpp(-1.4, c_ + sg * 2.1), yaw_road + sg * 9, 'kpp')
# the chicane: two staggered pairs of barriers across the road, each from a road edge in, a 2.9 m lane left beside them
_R = np.array(json.load(open(os.path.join(FENCE, 'map_forest.json')))['road'])
_R = _R[np.hypot(_R[:, 0] - BP[0], _R[:, 2] - BP[1]) < 60]
_Ra = (_R[:, [0, 2]] - BP) @ ROAD_IN
_Rc = (_R[:, [0, 2]] - BP) @ ARM


def road_edges(a):
    sel = np.abs(_Ra - a) < 2.5
    return float(_Rc[sel].min()), float(_Rc[sel].max())


CHICANE = []
for a_, side in ((-12.0, 'post'), (-24.0, 'rest')):
    e0, e1 = road_edges(a_)
    if side == 'post':                                   # from the post's edge (c min) in
        cs = (e0 - 0.45 + 1.0, e0 - 0.45 + 3.05)
        lane = (e0 - 0.45 + 4.05, e1)
    else:                                                # from the rest's edge (c max) in
        cs = (e1 + 0.45 - 1.0, e1 + 0.45 - 3.05)
        lane = (e0, e1 + 0.45 - 4.05)
    for k_, c_ in enumerate(cs):
        m = 'RoadBlock_Jersey_Striped' if k_ == 0 else 'RoadBlock_Jersey'
        place(m, kpp(a_, c_), yaw_road, 'kpp')
    CHICANE.append(dict(a=a_, side=side, road=(round(e0, 2), round(e1, 2)), blocks=[round(c, 2) for c in cs],
                        lane=(round(lane[0], 2), round(lane[1], 2)), lane_width=round(lane[1] - lane[0], 2)))
place('Sign_Halt', kpp(-32.0, road_edges(-32.0)[1] + 1.3), yaw_road, 'kpp')   # right of the approach, facing the driver
place('Sign_NoEntry', kpp(-3.0, road_edges(-3.0)[1] + 1.0), yaw_road, 'kpp')
# concertina, hedgehogs and a cheval de frise in front of the wings
for c0, sg in ((-0.90, -1), (6.25, 1)):
    for k_ in range(4):
        cc = c0 + sg * (7.0 + 5.3 * k_)
        p = kpp(-1.9, cc)
        hit = clear_box(p, yaw_road, 2.6, 0.6, 'kpp coil', trunks=False)
        if hit:
            continue
        put('WireCoil', p, yaw_road, 'kpp')
    for k_, cc in enumerate((5.0, 13.0, 21.0)):
        p = kpp(-5.5 - (k_ % 2) * 1.5, c0 + sg * cc)
        if not clear_box(p, 0.0, 0.85, 0.85, 'kpp hedgehog', trunks=False):
            put('Hedgehog', p, float(rng.uniform(0, 360)), 'kpp')
for end, sg in ((W_POST1, -1), (W_REST1, 1)):
    p = end + OUT_K * 1.5 + ARM * sg * 0.5
    if not clear_box(p, yaw_road, 1.6, 0.8, 'kpp barricade', trunks=False):
        put('WireBarricade', p, yaw_road, 'kpp')
for side in (-1, 1):                                            # hedgehogs off the road's edges on the approach
    for a_ in (-30.0, -36.0):
        e0, e1 = road_edges(a_)
        cc = e0 - 1.6 if side < 0 else e1 + 1.6
        p = kpp(a_, cc)
        if not clear_box(p, 0.0, 0.85, 0.85, 'kpp hedgehog', trunks=False):
            put('Hedgehog', p, float(rng.uniform(0, 360)), 'kpp')

# ---------------------------------------------------------------- pieces overlapping one another (footprints, SAT)
def obb(r):
    yaw = yaw_of(r['q'])
    ux, uz = ux_of(yaw), uz_of(yaw)
    c = foot_centre(r['m'], [r['p'][0], r['p'][2]], yaw)
    hx, hz = FOOT[r['m']]
    return c, ux, uz, hx, hz


def overlap(a, b):
    ca, ua, va, ha, ka = a
    cb, ub, vb, hb, kb_ = b
    d = cb - ca
    for ax in (ua, va, ub, vb):
        ra = ha * abs(ua @ ax) + ka * abs(va @ ax)
        rb = hb * abs(ub @ ax) + kb_ * abs(vb @ ax)
        if abs(d @ ax) > ra + rb - 0.02:
            return False
    return True




def hits_built(m, c, yaw, groups=('perimeter', 'kpp'), margin=0.08):
    """would a piece at c overlap a fence panel, socket or block already placed (the corners, the wings' ends)?"""
    r = dict(m=m, p=[float(c[0]), 0.0, float(c[1])], q=q_of(yaw))
    o = obb(r)
    o = (o[0], o[1], o[2], o[3] + margin, o[4] + margin)
    for g, rr, _ in RECS:
        if g in groups and abs(rr['p'][0] - c[0]) < 4.0 and abs(rr['p'][2] - c[1]) < 4.0 and overlap(o, obb(rr)):
            return True
    return False


# ================================================================ 3. the funnel
TOOTH_SP = 2.05
MAX_GAP = 1.60            # m: no free gap along a blocking line wider than this at the van body's height
BODY_H = 0.35             # m: the van's body starts here (1.98 m wide above it; the wheels below are ray casts)
TOOTH_HALF = 0.5 - 0.32 * BODY_H / 1.1                 # a tooth's half width at that height (1.0 m at the ground, 0.36 at the top)
AB_EXT = {'Abatis': (-3.91, 3.61), 'Abatis_b': (-3.32, 3.29)}   # along the model's x at 0.35-0.5 m (its solid geometry)
AB_GAP = 0.85             # m: free gap between a tooth and an abatis' end at the van body's height
STRIP_TRUNK, STRIP_SMALL = 1.3, 1.0   # m: the strip cleared along a funnel line (trunk centre + radius / bush, fern)
LINES = {}


def teeth_line(name, A, Bp, out_dir, abatis_every=0):
    """teeth from A to B; trees in the way: a tooth is shifted along the line (up to 0.6 m) or left out where a trunk
    stands, the small stuff is removed; the bones (from the BVH probe) take the place of the teeth they cover"""
    A, Bp = np.asarray(A, float), np.asarray(Bp, float)
    D = unit(Bp - A)
    n = np.array([D[1], -D[0]])
    if n @ out_dir < 0:
        n = -n
    yaw_line = yaw_facing(n)                           # outer faces (the abatis' crowns) out of the funnel
    Lr = float(np.linalg.norm(Bp - A))
    bones = bone_runs(A, Bp)
    occ = []                                           # occupied intervals along the line [s0, s1, what]
    for b0, b1 in bones:
        occ.append([b0, b1, 'bone'])
    strip = 0
    for k in trees_near((A + Bp) / 2, Lr / 2 + 2.5):
        rel = TREE_XZ[k] - A
        s_, d_ = rel @ D, rel @ n
        if -1.0 < s_ < Lr + 1.0 and abs(d_) < (STRIP_TRUNK + TREE_R[k] if TREE_R[k] > 0 else STRIP_SMALL):
            REMOVED[k] = 'funnel strip ' + name
            strip += 1
    pos, placed, left, n_ab, k_ab = 0.5, 0, [], 0, 0
    last_s = -0.9 - TOOTH_HALF - 0.2                   # the wing's end stands in for the last tooth
    while pos <= Lr - 0.4:
        # an abatis now and then where its whole footprint is free of trunks and bones; its real ends (at the van
        # body's height) AB_GAP from the teeth on both sides
        if abatis_every and placed and placed % abatis_every == 0 and pos + 10.0 < Lr - 3.0:
            m = 'Abatis' if k_ab % 2 == 0 else 'Abatis_b'
            yw = yaw_line + float(rng.uniform(-4, 4))
            e0, e1 = AB_EXT[m]
            if bx_of(yw) @ D > 0:
                near, far = -e0, e1
            else:
                near, far = e1, -e0
            s_c = last_s + TOOTH_HALF + AB_GAP + near
            c = A + D * s_c
            hx, hz = FOOT[m]
            fc = foot_centre(m, c, yw)
            free = not clear_box(fc, yw, hx + 0.1, hz + 0.1, 'funnel abatis', trunks=False) and \
                not any(b0 < s_c + far + 0.5 and b1 > s_c - near - 0.5 for b0, b1 in bones)
            if free:
                place(m, c, yw, 'funnel')
                occ.append([s_c - near, s_c + far, m])
                last_s = s_c + far + AB_GAP + TOOTH_HALF - TOOTH_SP     # the next tooth: AB_GAP after the far end
                pos = last_s + TOOTH_SP
                k_ab += 1
                placed += 1
                continue
        done = False
        for sh in (0.0, -0.3, 0.3, -0.6, 0.6):
            s_ = pos + sh
            if s_ > Lr - 0.3:
                continue
            c = A + D * s_
            if any(b0 - 0.55 < s_ < b1 + 0.55 for b0, b1 in bones):
                continue
            m = 'TankTooth_b' if rng.random() < 0.16 else 'TankTooth'
            yw = yaw_line + float(rng.uniform(-22, 22) if m == 'TankTooth_b' else rng.uniform(-10, 10))
            if hits_built(m, c, yw):
                continue
            gs = ground_box(c, yw, 0.5, 0.5)
            y = min(gs[0], min(gs[1:]) + 0.22)          # the base (buried 0.25 m) never shows its underside
            place(m, c, yw, 'funnel', y=y)
            occ.append([s_ - TOOTH_HALF, s_ + TOOTH_HALF, 'tooth'])
            last_s = s_
            pos = s_ + TOOTH_SP
            placed += 1
            done = True
            break
        if not done:
            left.append(round(pos, 2))
            pos += TOOTH_SP
    # where a bone of the giant takes the teeth's place, the line must not rely on the bone having a collider: two teeth
    # beside the line (in the thirds of the gap, 1.2 m off it, on a side the bones leave free) close the gap by themselves
    # (links <= 1.2 m at the van body's height)
    backups = []
    rng_b = np.random.default_rng(7)
    for b0, b1 in bones:
        t_s = sorted(o[0] + TOOTH_HALF for o in occ if o[2] == 'tooth')
        before = max((t for t in t_s if t < b0), default=None)
        after = min((t for t in t_s if t > b1), default=None)
        if before is None or after is None:
            continue
        done_b = False
        for d_off in (1.2, -1.2, 1.0, -1.0, 1.35, -1.35):
            a2, b2 = A + D * (before - 1.0) + n * d_off, A + D * (after + 1.0) + n * d_off
            occ2 = bone_runs(a2, b2)
            pts = [before + (after - before) * k / 3 for k in (1, 2)]
            ok = all(not any(o0 - 0.55 < (p_ - (before - 1.0)) < o1 + 0.55 for o0, o1 in occ2) for p_ in pts)
            cand = []
            for p_ in pts:
                c = A + D * p_ + n * d_off
                yw = yaw_line + float(rng_b.uniform(-10, 10))
                trunk = any(TREE_R[k] > 0 and in_box(TREE_XZ[k], c, yw, 0.55, 0.55, pad=TREE_R[k] + 0.10)
                            for k in trees_near(c, 1.3))
                if hits_built('TankTooth', c, yw) or trunk:
                    ok = False
                cand.append((c, yw))
            if ok:
                for c, yw in cand:
                    gs = ground_box(c, yw, 0.5, 0.5)
                    place('TankTooth', c, yw, 'funnel', y=min(gs[0], min(gs[1:]) + 0.22))
                    placed += 1
                    backups.append([round(float(c[0]), 3), round(float(c[1]), 3)])
                done_b = True
                break
        if not done_b:
            print('WARNING: no free spot beside the bone at', b0, b1)
    last = max([o[1] for o in occ if o[2] != 'bone'], default=0.0)
    G = Lr + 0.9 - last                                 # to the corner's panels
    s_end = last + 0.75                                 # one more tooth close after the last (1.15 m centre to centre):
    if G > MAX_GAP and not any(b0 - 0.55 < s_end < b1 + 0.55 for b0, b1 in bones) and \
            not hits_built('TankTooth', A + D * s_end, yaw_line):
        c = A + D * s_end                               # no gap over 1.6 m, clear of the corner's sockets
        yw = yaw_line + float(rng.uniform(-10, 10))
        gs = ground_box(c, yw, 0.5, 0.5)
        place('TankTooth', c, yw, 'funnel', y=min(gs[0], min(gs[1:]) + 0.22))
        occ.append([s_end - TOOTH_HALF, s_end + TOOTH_HALF, 'tooth'])
        placed += 1
    # the ends: the gap between the first / last tooth and the nearest fence panel, in the plane (the runs meet the
    # line at an angle); measured at the van body's height (tooth half width TOOTH_HALF, panel half thickness 0.09)
    teeth_s = sorted(o[0] + TOOTH_HALF for o in occ if o[2] == 'tooth')

    def seg_dist(p, a_, b_):
        a_, b_ = np.asarray(a_), np.asarray(b_)
        t = np.clip((p - a_) @ (b_ - a_) / ((b_ - a_) @ (b_ - a_)), 0, 1)
        return float(np.linalg.norm(p - (a_ + (b_ - a_) * t)))

    segs = [(r_['A'], r_['B']) for r_ in RUNS.values()]
    end_gaps = []
    for s_t in (teeth_s[0], teeth_s[-1]):
        p_ = A + D * s_t
        end_gaps.append(round(min(seg_dist(p_, a_, b_) for a_, b_ in segs) - TOOTH_HALF - 0.09, 2))
    occ.append([-5.0, teeth_s[0] - TOOTH_HALF - end_gaps[0], 'wing'])
    occ.append([teeth_s[-1] + TOOTH_HALF + end_gaps[1], Lr + 5.0, 'corner'])
    # trunks standing on the line (they block where they stand)
    for k in trees_near((A + Bp) / 2, Lr / 2 + 1.0):
        r = TREE_R[k]
        if r <= 0:
            continue
        rel = TREE_XZ[k] - A
        s_, d_ = rel @ D, rel @ n
        if -1 < s_ < Lr + 1 and abs(d_) < r:
            h = math.sqrt(r * r - d_ * d_)
            occ.append([s_ - h, s_ + h, 'trunk'])
    occ.sort()
    gaps, cur = [], -5.0
    for s0, s1, w in occ:
        if s0 > cur:
            gaps.append((round(cur, 2), round(s0, 2)))
        cur = max(cur, s1)
    wide = [(g0, g1) for g0, g1 in gaps if g1 - g0 > MAX_GAP]
    LINES[name] = dict(A=A.tolist(), B=Bp.tolist(), length=round(Lr, 2), pieces=placed, abatis=k_ab, left_out=left,
                       trees_cleared=strip, end_gaps=end_gaps,
                       bone_runs=bones, bone_backups=backups,
                       max_gap=round(max(g1 - g0 for g0, g1 in gaps), 2) if gaps else 0.0,
                       wide_gaps=wide, outer=n.tolist())
    return LINES[name]


ends = {'post': W_POST1, 'rest': W_REST1}
dA = np.linalg.norm(W_POST1 - CORNERS['NE']) + np.linalg.norm(W_REST1 - CORNERS['NW'])
dB = np.linalg.norm(W_POST1 - CORNERS['NW']) + np.linalg.norm(W_REST1 - CORNERS['NE'])
pair = (('post', 'NE'), ('rest', 'NW')) if dA < dB else (('post', 'NW'), ('rest', 'NE'))
funnel_mid = (W_POST1 + W_REST1 + CORNERS['NW'] + CORNERS['NE']) / 4
for w, cn in pair:
    e, k_ = ends[w], CORNERS[cn]
    D = unit(k_ - e)
    a_, b_ = e + D * 0.9, k_ - D * 0.9
    mid = (a_ + b_) / 2
    teeth_line('teeth_%s_%s' % (w, cn), a_, b_, unit(mid - funnel_mid), abatis_every=24)

# ================================================================ the result
# what the Terrain bake must keep its own planting off (old yard's regrowth, saplings, boulders, clutter, ground cover): per
# piece, its footprint's long axis as a segment a-b (plan x, z) and a distance r (half depth + 1 m)
KEEP_MARGIN = 1.0
keep_clear = []
for g_, r_, _ in RECS:
    yw = yaw_of(r_['q'])
    hx, hz = FOOT[r_['m']]
    fc = foot_centre(r_['m'], np.array([r_['p'][0], r_['p'][2]]), yw)
    ax = ux_of(yw)
    a_, b_ = fc - ax * max(hx - hz, 0.0), fc + ax * max(hx - hz, 0.0)
    keep_clear.append(dict(a=[round(float(a_[0]), 2), round(float(a_[1]), 2)], b=[round(float(b_[0]), 2), round(float(b_[1]), 2)],
                           r=round(float(min(hx, hz) + KEEP_MARGIN), 2)))
context = {'Gate': GATE_GAME[[0, 2]].tolist(), 'Barrier': BP.tolist(), 'Checkpoint': BOOTH.tolist(),
           'Hatch': HATCH_GAME[[0, 2]].tolist()}
removed = [dict(list='trees', m=L['trees'][k]['m'], p=L['trees'][k]['p'], index=int(k), why=w) for k, w in sorted(REMOVED.items())]
out = dict(frame='game: after ForestYardPlan (x0.7071 about (340, -360) within 135 m) and ForestRelocation (barrier '
                 '(310.945, 16.0509, -282.1992) -> (143.51488, 9.27351, -64.67514), yaw -65.3345)',
           corners_u3={k: v.tolist() for k, v in CORNERS_U3.items()}, corners={k: v.tolist() for k, v in CORNERS.items()},
           gate=dict(game=GATE_GAME.tolist(), west_end=GATE_W.tolist(), east_end=GATE_E.tolist()), wicket=WICKET_AT.tolist(),
           barrier=dict(post=BP.tolist(), rest=REST.tolist(), yaw=BAR_YAW, booth=BOOTH.tolist(), road_in=ROAD_IN.tolist()),
           runs=RUNS, lines=LINES, chicane=CHICANE, context=context, removed_trees=removed, keep_clear=keep_clear,
           records=[dict(group=g, **r) for g, r, _ in RECS])
os.makedirs(OUT, exist_ok=True)
json.dump(out, open(os.path.join(OUT, 'u7_layout.json'), 'w'), indent=1)
print('records', len(RECS), dict(Counter(r['m'] for g, r, _ in RECS)))
print('by group', dict(Counter(g for g, r, _ in RECS)))
for k, v in RUNS.items():
    print('%-9s %3d panels at %.3f m, yaw %.2f, %.1f m' % (k, v['panels'], v['spacing'], v['yaw'], v['length']))
for k, v in LINES.items():
    print('%-16s %.1f m: %d pieces (%d abatis), left out %s, bones %s, max gap %.2f, wide %s' % (
        k, v['length'], v['pieces'], v['abatis'], v['left_out'], v['bone_runs'], v['max_gap'], v['wide_gaps']))
print('chicane', CHICANE)
print('lowered at the gate (the leaf passes over their sockets):', LOWERED)
print('corner sockets lowered:', len(CORNER_LOWERED))
print('trees removed', len(removed), dict(Counter(r['m'].split('_')[0] for r in removed)))
print('removed by', dict(Counter(r['why'].split(' ')[0] for r in removed)))

allr = [r for g, r, _ in RECS]
boxes = [obb(r) for r in allr]
cent = np.array([b[0] for b in boxes])
bad = []
for i in range(len(allr)):
    near = np.nonzero(np.hypot(*(cent - cent[i]).T) < 10.0)[0]
    for j in near:
        if j <= i:
            continue
        mi, mj = allr[i]['m'], allr[j]['m']
        if {mi, mj} <= {'RoadBlock_FBS'} and abs(allr[i]['p'][1] - allr[j]['p'][1]) > 0.3:
            continue                                         # stacked
        if mi.startswith('ConcreteFence') and mj.startswith('ConcreteFence'):
            continue                                         # a run's panels and sockets meet by design
        if overlap(boxes[i], boxes[j]):
            bad.append((mi, mj, [round(v, 1) for v in allr[i]['p']]))
print('pieces overlapping (outside the runs):', len(bad), bad[:12])
