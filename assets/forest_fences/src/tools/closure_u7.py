"""Closure of the U7 layout (game frame), flood fill on a 0.25 m grid with the pieces' footprints at the van body's
height (0.35 m: teeth 0.80 m wide, the abatis by its real ends and only the trunk's width), the trees that stay
(trunks) and the bones only where the probe found them on the lines (anything else ignored: buildings, slopes, water,
the rest of the giant - so a leak found may be a false alarm, a closure found holds).
A van is a disk of 0.97 m (1.94 m wide), a walker 0.35 m. Cases: barrier and gate closed / barrier open / both open.
python3 closure_u7.py <u7_layout.json> [out.png]"""
import json, os, sys, math
import numpy as np
from scipy import ndimage
sys.path.insert(0, '/home/claude/uaz')
U = json.load(open(sys.argv[1]))
L = json.load(open('/home/claude/uaz/out/forest_update6/stage/Assets/Locations/Forest/Data/Forest_Layout.json'))
CELL = 0.25
X0, X1, Z0, Z1 = 70.0, 480.0, -480.0, 10.0
nx, nz = int((X1 - X0) / CELL), int((Z1 - Z0) / CELL)
FOOT = {'ConcreteFence': (1.25, 0.12), 'ConcreteFence_b': (1.25, 0.12), 'ConcreteFence_Broken': (1.25, 0.12),
        'ConcreteFence_Sign': (1.25, 0.12), 'ConcreteFence_Plain': (1.25, 0.12), 'ConcreteFence_Wicket': (1.25, 0.12),
        'ConcreteFence_Socket': (0.48, 0.38), 'TankTooth': (0.398, 0.398), 'TankTooth_b': (0.398, 0.398),
        'RoadBlock_FBS': (1.19, 0.20), 'RoadBlock_Jersey': (1.0, 0.31), 'RoadBlock_Jersey_Striped': (1.0, 0.31),
        'RoadBlock_Cube': (0.5, 0.5), 'WireCoil': (2.5, 0.48), 'WireBarricade': (1.5, 0.75), 'Hedgehog': (0.8, 0.8),
        'Abatis': (3.76, 0.30), 'Abatis_b': (3.305, 0.30), 'Sign_Halt': (0.62, 0.10), 'Sign_NoEntry': (0.30, 0.08)}
FOOT_OFF = {}
# the abatis at the van body's height (0.35-0.5 m): its solid geometry spans model x -3.91..3.61 (Abatis), -3.32..3.29
# (Abatis_b); model x = Unity -x: the centre shifts by +0.15 / +0.015 along Unity x; only the trunk's width across
XOFF = {'Abatis': 0.15, 'Abatis_b': 0.015}
TRUNK = {'SpruceHC': 0.30, 'Spruce': 0.30, 'Fir': 0.30, 'Pine': 0.30, 'Larch': 0.28, 'Birch': 0.20, 'Dead': 0.20, 'Snag': 0.22}
xs = X0 + (np.arange(nx) + 0.5) * CELL
zs = Z0 + (np.arange(nz) + 0.5) * CELL
XX, ZZ = np.meshgrid(xs, zs, indexing='ij')


def box_mask(c, ux, uz, hx, hz):
    m = np.zeros((nx, nz), bool)
    r = math.hypot(hx, hz) + 0.3
    i0, i1 = max(0, int((c[0] - r - X0) / CELL)), min(nx, int((c[0] + r - X0) / CELL) + 1)
    j0, j1 = max(0, int((c[1] - r - Z0) / CELL)), min(nz, int((c[1] + r - Z0) / CELL) + 1)
    if i0 >= i1 or j0 >= j1:
        return None
    dx, dz = XX[i0:i1, j0:j1] - c[0], ZZ[i0:i1, j0:j1] - c[1]
    a = np.abs(dx * ux[0] + dz * ux[1]) <= hx
    b = np.abs(dx * uz[0] + dz * uz[1]) <= hz
    return (i0, i1, j0, j1, a & b)


def stamp(M, c, ux, uz, hx, hz):
    hx, hz = max(hx, 0.75 * CELL), max(hz, 0.75 * CELL)       # thin walls: no holes between the cell centres
    r = box_mask(c, ux, uz, hx, hz)
    if r:
        i0, i1, j0, j1, m = r
        M[i0:i1, j0:j1] |= m


def disk(M, c, rad):
    i0, i1 = max(0, int((c[0] - rad - X0) / CELL)), min(nx, int((c[0] + rad - X0) / CELL) + 1)
    j0, j1 = max(0, int((c[1] - rad - Z0) / CELL)), min(nz, int((c[1] + rad - Z0) / CELL) + 1)
    if i0 < i1 and j0 < j1:
        M[i0:i1, j0:j1] |= (XX[i0:i1, j0:j1] - c[0]) ** 2 + (ZZ[i0:i1, j0:j1] - c[1]) ** 2 <= rad * rad


OBST = np.zeros((nx, nz), bool)
WICKET = []
for r in U['records']:
    m = r['m']
    yaw = 2 * math.atan2(r['q'][1], r['q'][3])
    ux = np.array([math.cos(yaw), -math.sin(yaw)])
    uz = np.array([math.sin(yaw), math.cos(yaw)])
    c = np.array([r['p'][0], r['p'][2]]) - uz * FOOT_OFF.get(m, 0.0) + ux * XOFF.get(m, 0.0)
    hx, hz = FOOT[m]
    if m == 'ConcreteFence_Wicket':
        WICKET.append((c, ux, uz))
        stamp(OBST, c + ux * 0.62, ux, uz, 0.63, hz)          # the panel's part (Blender x -1.24..-0.06 = Unity +x side)
        continue
    if m.startswith('Sign_'):
        continue                                              # posts only: they block nothing
    stamp(OBST, c, ux, uz, hx, hz)
removed = {t['index'] for t in U['removed_trees']}
for i, t in enumerate(L['trees']):
    pre = t['m'].split('_')[0]
    if pre in TRUNK and i not in removed:
        disk(OBST, (t['p'][0], t['p'][2]), TRUNK[pre] * t.get('s', 1.0))
for nm, ln in U['lines'].items():
    A, Bp = np.array(ln['A']), np.array(ln['B'])
    D = (Bp - A) / np.linalg.norm(Bp - A)
    n = np.array([D[1], -D[0]])
    for b0, b1 in ([] if os.environ.get('NO_BONES') else ln['bone_runs']):   # NO_BONES=1: as if the bones had no collider
        stamp(OBST, A + D * (b0 + b1) / 2, D, n, (b1 - b0) / 2, 0.55)
# the barrier (closed: boom across), the gate (closed: leaf across), the wicket's door (closed)
Bk = U['barrier']
BP, REST = np.array(Bk['post']), np.array(Bk['rest'])
ARM = (REST - BP) / np.linalg.norm(REST - BP)
nrm = np.array([ARM[1], -ARM[0]])
BAR_FIXED = np.zeros_like(OBST)
stamp(BAR_FIXED, BP, ARM, nrm, 0.375, 0.375)                    # the foot
stamp(BAR_FIXED, REST, ARM, nrm, 0.12, 0.08)                    # the rest
BOOM = np.zeros_like(OBST)
stamp(BOOM, BP + ARM * 2.715, ARM, nrm, 3.285, 0.07)
G = U['gate']
GP = np.array(G['game'])[[0, 2]]
GW, GE = np.array(G['west_end']), np.array(G['east_end'])
GX = (GE - GW) / np.linalg.norm(GE - GW)                     # the gate's Unity +x
gn = np.array([GX[1], -GX[0]])
gin = gn if gn @ (np.array([340.0, -360.0]) - GP) > 0 else -gn  # to the inside
GATE_FIXED = np.zeros_like(OBST)
stamp(GATE_FIXED, GP + GX * -1.30, GX, gn, 1.13, 0.03)         # the fixed panel, Unity x -2.43..-0.17
stamp(GATE_FIXED, GP + GX * 7.175 + gin * 0.22, GX, gn, 0.225, 0.23)   # the receiver post
stamp(GATE_FIXED, GP + GX * -0.16 + gin * 0.22, GX, gn, 0.08, 0.21)    # the guides
LEAF = np.zeros_like(OBST)
stamp(LEAF, GP + GX * 3.5 + gin * 0.22, GX, gn, 3.5, 0.035)    # the leaf closed, Unity x 0..7, 0.22 m inside
DOOR = np.zeros_like(OBST)
for c, ux, uz in WICKET:
    stamp(DOOR, c - ux * 0.62, ux, uz, 0.6, 0.12)


def reach(block, rad, seeds_free_edge=True):
    k = int(math.ceil(rad / CELL))
    st = np.hypot(*np.mgrid[-k:k + 1, -k:k + 1]) * CELL <= rad
    occ = ndimage.binary_dilation(block, structure=st)
    lab, n = ndimage.label(~occ)
    edge = set(np.unique(np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]]))) - {0}
    return lab, edge, occ


def ix(p):
    return int((p[0] - X0) / CELL), int((p[1] - Z0) / CELL)


gate_front = GP + GX * 3.5 - gin * 8.0
base_in = np.array([340.0, -360.0])
road_in = BP + (np.array(Bk['road_in'])) * 15.0 + ARM * 2.8
road_out = BP - np.array(Bk['road_in']) * 40.0 + ARM * 4.0
probes = {'outside, on the road 40 m before the barrier': road_out, 'the road 15 m behind the barrier (in the funnel)': road_in,
          'in front of the base gate (in the funnel)': gate_front, 'inside the base': base_in}
cases = [('van, barrier closed, gate closed (the wicket open, as built)', 0.97, [BAR_FIXED, BOOM, GATE_FIXED, LEAF]),
         ('van, barrier open, gate closed', 0.97, [BAR_FIXED, GATE_FIXED, LEAF]),
         ('van, barrier open, gate open', 0.97, [BAR_FIXED, GATE_FIXED]),
         ('walker, barrier closed, gate closed (wicket open)', 0.35, [BAR_FIXED, BOOM, GATE_FIXED, LEAF]),
         ('walker, the wicket shut too', 0.35, [BAR_FIXED, BOOM, GATE_FIXED, LEAF, DOOR])]
res = {}
for nm, rad, extra in cases:
    blk = OBST.copy()
    for e in extra:
        blk |= e
    lab, edge, occ = reach(blk, rad)
    row = {}
    for pn, p in probes.items():
        i, j = ix(p)
        l = lab[i, j]
        row[pn] = 'blocked cell' if l == 0 else ('reachable from outside' if l in edge else 'closed off')
    res[nm] = row
    print(nm)
    for pn, v in row.items():
        print('   %-48s %s' % (pn, v))
json.dump(res, open(sys.argv[1].replace('.json', '_closure.json'), 'w'), indent=1)
if len(sys.argv) > 2:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    blk = OBST | BAR_FIXED | BOOM | GATE_FIXED | LEAF
    lab, edge, occ = reach(blk, 0.97)
    outside = np.isin(lab, list(edge))
    img = np.ones((nx, nz, 3)) * 0.92
    img[outside] = [0.80, 0.88, 0.80]
    img[(lab > 0) & ~outside] = [0.95, 0.85, 0.70]
    img[occ & ~blk] = [0.75, 0.75, 0.75]
    img[blk] = [0.1, 0.1, 0.1]
    f, ax = plt.subplots(figsize=(12, 14), dpi=110)
    ax.imshow(np.transpose(img, (1, 0, 2)), origin='lower', extent=(X0, X1, Z0, Z1), interpolation='nearest')
    for pn, p in probes.items():
        ax.plot(p[0], p[1], 'r*', ms=10)
    ax.set_title('van (1.94 m): green = reachable from outside, orange = closed off; barrier and gate closed')
    plt.tight_layout()
    plt.savefig(sys.argv[2])
