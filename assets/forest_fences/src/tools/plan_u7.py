"""Plan of the U7 placements (game frame) over the terrain, trees, bones, water and road:
python3 plan_u7.py <u7_layout.json> <out.png> [xmin xmax zmin zmax] [--labels]"""
import json, sys, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
a = sys.argv[1:]
U = json.load(open(a[0]))
out = a[1]
ext = [float(v) for v in a[2:6]] if len(a) >= 6 and not a[2].startswith('--') else None
LBL = '--labels' in a
L = json.load(open('/home/claude/uaz/out/forest_update6/stage/Assets/Locations/Forest/Data/Forest_Layout.json'))
B = json.load(open('/home/claude/fence/map_big.json'))
G = np.load('/home/claude/fence/drive_grid.npz')
F = json.load(open('/home/claude/fence/map_forest.json'))
bones = np.array(json.load(open('/home/claude/fence/bones_cells.json')))
recs = U['records']
if ext is None:
    xs = [r['p'][0] for r in recs]; zs = [r['p'][2] for r in recs]
    ext = [min(xs) - 25, max(xs) + 25, min(zs) - 25, max(zs) + 25]
x0, x1, z0, z1 = ext
W = 14.0
H = W * (z1 - z0) / (x1 - x0)
fig, ax = plt.subplots(figsize=(W, H), dpi=110)
# terrain (hillshade) from the drive grid heights (1 m cells over [-600, 600])
Hh = G['H']
i0, i1 = int(x0 + 600), int(x1 + 600); j0, j1 = int(z0 + 600), int(z1 + 600)
sub = Hh[i0:i1, j0:j1]
gx, gz = np.gradient(sub)
shade = np.clip(0.55 + 0.35 * (gx * 0.7 - gz * 0.7) / 1.0, 0, 1)
slope = G['slope_deg'][i0:i1, j0:j1]
rgb = np.stack([0.80 * shade, 0.84 * shade, 0.76 * shade], -1)
rgb[slope > 28] = rgb[slope > 28] * 0.6 + np.array([0.35, 0.10, 0.10])
wat = G['water'][i0:i1, j0:j1]
rgb[wat] = [0.45, 0.62, 0.85]
ax.imshow(np.transpose(rgb, (1, 0, 2)), origin='lower', extent=(x0, x1, z0, z1), interpolation='nearest')
# road
R = np.array(F['road'])
m = (R[:, 0] > x0) & (R[:, 0] < x1) & (R[:, 2] > z0) & (R[:, 2] < z1)
ax.scatter(R[m, 0], R[m, 2], s=2.0, c='#b09a74', lw=0, alpha=0.6)
# bones: cells (2 m), dark = low enough to block a van, light = high above (an arch)
bx, bz = bones[:, 0] * 2 + 1, bones[:, 1] * 2 + 1
bm = (bx > x0) & (bx < x1) & (bz > z0) & (bz < z1)
if bm.any():
    hg = np.array([Hh[int(x + 600), int(z + 600)] for x, z in zip(bx[bm], bz[bm])])
    low = bones[bm, 2] < hg + 2.6
    ax.scatter(bx[bm][low], bz[bm][low], s=9, marker='s', c='#d8cfb0', edgecolors='#7a6f50', lw=0.3)
    ax.scatter(bx[bm][~low], bz[bm][~low], s=9, marker='s', c='none', edgecolors='#c8bfa0', lw=0.4)
# trees (trunks)
trunk = ('Spruce', 'Pine', 'Birch', 'Dead', 'Snag', 'Fir', 'Larch', 'SpruceHC')
T = np.array([[t['p'][0], t['p'][2]] for t in L['trees'] if t['m'].startswith(trunk)])
tm = (T[:, 0] > x0) & (T[:, 0] < x1) & (T[:, 1] > z0) & (T[:, 1] < z1)
ax.scatter(T[tm, 0], T[tm, 1], s=6, c='#2f5a2a', lw=0)
rem = U.get('removed_trees', [])
if rem:
    RT = np.array([[t['p'][0], t['p'][2]] for t in rem])
    ax.scatter(RT[:, 0], RT[:, 1], s=26, marker='x', c='#d03020', lw=1.0)
# prefabs (game frame where known)
for nm, p in U.get('context', {}).items():
    if not (x0 < p[0] < x1 and z0 < p[1] < z1):
        continue
    ax.plot(p[0], p[1], 'o', ms=5, c='#202020')
    ax.text(p[0] + 1.5, p[1] + 1.5, nm, fontsize=7, clip_on=True)
COL = {'ConcreteFence': '#6d6d6d', 'ConcreteFence_b': '#6d6d6d', 'ConcreteFence_Broken': '#b04020', 'ConcreteFence_Sign': '#c02020',
       'ConcreteFence_Socket': '#303030', 'ConcreteFence_Wicket': '#2070c0', 'TankTooth': '#505050', 'TankTooth_b': '#505050',
       'Abatis': '#6a4a20', 'Abatis_b': '#6a4a20', 'WireCoil': '#a0a0a0', 'WireBarricade': '#8a5a20',
       'RoadBlock_FBS': '#404040', 'RoadBlock_Jersey': '#606060', 'RoadBlock_Jersey_Striped': '#d02020', 'RoadBlock_Cube': '#404040',
       'Sign_Halt': '#e02020', 'Sign_NoEntry': '#e02020', 'Hedgehog': '#7a3a10'}
FOOT = {'ConcreteFence': (2.48, 0.16), 'ConcreteFence_b': (2.48, 0.16), 'ConcreteFence_Broken': (2.48, 0.16),
        'ConcreteFence_Sign': (2.48, 0.16), 'ConcreteFence_Plain': (2.48, 0.16), 'ConcreteFence_Wicket': (2.48, 0.16),
        'ConcreteFence_Socket': (0.95, 0.75), 'TankTooth': (1.0, 1.0), 'TankTooth_b': (1.0, 1.0), 'RoadBlock_FBS': (2.38, 0.40),
        'RoadBlock_Jersey': (2.0, 0.61), 'RoadBlock_Jersey_Striped': (2.0, 0.61), 'RoadBlock_Cube': (1.0, 1.0),
        'WireCoil': (5.0, 0.9), 'WireBarricade': (3.0, 1.6), 'Abatis': (7.67, 2.50), 'Abatis_b': (7.08, 2.37),
        'Sign_Halt': (1.2, 0.1), 'Sign_NoEntry': (0.6, 0.1), 'Hedgehog': (1.5, 1.5)}
# the abatis' boxes off their origins (from the export's bounds: Unity x, z = -Blender x, -Blender y)
OFFX = {'Abatis': 0.077, 'Abatis_b': -0.22}
OFFZ = {'Abatis': 0.70, 'Abatis_b': 0.547}
for r in recs:
    yaw = 2 * math.atan2(r['q'][1], r['q'][3])
    ux = np.array([math.cos(yaw), -math.sin(yaw)])           # Unity local +x
    uz = np.array([math.sin(yaw), math.cos(yaw)])            # Unity local +z (= Blender -y, the outside)
    c = np.array([r['p'][0], r['p'][2]])
    fx, fy = FOOT.get(r['m'], (1, 1))
    c = c + ux * OFFX.get(r['m'], 0.0) + uz * OFFZ.get(r['m'], 0.0)
    pts = [c + ux * sx * fx / 2 + uz * sy * fy / 2 for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    ax.add_patch(MPoly(pts, closed=True, fc=COL.get(r['m'], '#000'), ec='none', alpha=0.95))
    if r['m'].startswith(('ConcreteFence', 'Sign_')):
        ax.plot([c[0], c[0] + uz[0] * 1.2], [c[1], c[1] + uz[1] * 1.2], c='#c03030', lw=0.5)
for nm, run in U.get('runs', {}).items():
    if LBL and 'A' in run:
        A = np.array(run['A']); Bp = np.array(run['B'])
        mid = (A + Bp) / 2
        if x0 < mid[0] < x1 and z0 < mid[1] < z1:
            ax.text(mid[0], mid[1], nm, fontsize=7, color='#102060', clip_on=True)
ax.set_xlim(x0, x1); ax.set_ylim(z0, z1)
ax.set_aspect('equal')
ax.set_xlabel('x (Unity, m)'); ax.set_ylabel('z (Unity, m)')
ax.grid(True, lw=0.3, alpha=0.4)
plt.tight_layout()
plt.savefig(out, bbox_inches='tight', pad_inches=0.1)
print('saved', out)
