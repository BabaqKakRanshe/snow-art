"""Van drivability grid of the Forest (U3 data, Unity frame) and reachability with a blocking line.
Cells 1 m over [-600, 600]^2. Blocked: slope > MAXSLOPE, water, tree trunks (+clearance), giant bones lower than
the van, base fence (current FenceChain) except the gate, map edge."""
import json, math, sys
import numpy as np
from scipy.interpolate import LinearNDInterpolator
from scipy import ndimage
N0, N1, CELL = -600, 600, 1.0
n = int((N1 - N0) / CELL)
MAXSLOPE = 28.0          # deg, the van
CLEAR = 1.3              # m, half the van's width + a margin
L = json.load(open('/home/claude/uaz/out/forest_update6/stage/Assets/Locations/Forest/Data/Forest_Layout.json'))
B = json.load(open('map_big.json'))
def idx(x, z):
    return int((x - N0) / CELL), int((z - N0) / CELL)
xs = N0 + (np.arange(n) + 0.5) * CELL
X, Z = np.meshgrid(xs, xs, indexing='ij')
T = np.array(B['terrain'])
H = LinearNDInterpolator(T[:, [0, 2]], T[:, 1])(X, Z)
H = np.where(np.isnan(H), np.nanmean(H), H)
gx, gz = np.gradient(H, CELL)
slope = np.degrees(np.arctan(np.hypot(gx, gz)))
blocked = slope > MAXSLOPE
# water
W = np.array(B['water'])
wm = np.zeros_like(blocked)
for x, y, z in W:
    i, j = idx(x, z)
    if 0 <= i < n and 0 <= j < n: wm[i, j] = True
wm = ndimage.binary_dilation(wm, iterations=3)
wm = ndimage.binary_fill_holes(wm)
# trunks
trunk = ('Spruce', 'Pine', 'Birch', 'Dead', 'Snag', 'Fir', 'Larch', 'Oak', 'Beech', 'SpruceHC')
tm = np.zeros_like(blocked)
for t in L['trees']:
    if t['m'].startswith(trunk):
        i, j = idx(t['p'][0], t['p'][2])
        if 0 <= i < n and 0 <= j < n: tm[i, j] = True
r = int(math.ceil((CLEAR + 0.35) / CELL))
disk = np.hypot(*np.mgrid[-r:r + 1, -r:r + 1]) <= (CLEAR + 0.35) / CELL
tm = ndimage.binary_dilation(tm, structure=disk)
# bones (lower than 2.6 m above the ground)
bm = np.zeros_like(blocked)
for ci, cj, h in json.load(open('bones_cells.json')):
    x0, z0 = ci * 2.0, cj * 2.0
    for dx in (0.5, 1.5):
        for dz in (0.5, 1.5):
            i, j = idx(x0 + dx, z0 + dz)
            if 0 <= i < n and 0 <= j < n and h < H[i, j] + 2.6: bm[i, j] = True
bm = ndimage.binary_dilation(bm, iterations=int(CLEAR))
# base fence (FenceChain) except the gate (Gate prefab ~6 m opening)
fm = np.zeros_like(blocked)
def yaw(q): return math.degrees(2 * math.atan2(q[1], q[3]))
def draw_seg(mask, p, q, half):
    a = math.radians(yaw(q)); dx, dz = math.cos(a), -math.sin(a)
    for s in np.linspace(-half, half, int(half * 4) + 1):
        i, j = idx(p[0] + dx * s, p[2] + dz * s)
        if 0 <= i < n and 0 <= j < n: mask[i, j] = True
for rr in L['rocks']:
    if rr['m'] == 'FenceChain': draw_seg(fm, rr['p'], rr['q'], 1.55)
fm = ndimage.binary_dilation(fm, iterations=int(CLEAR))
edge = np.zeros_like(blocked); edge[:2, :] = edge[-2:, :] = edge[:, :2] = edge[:, -2:] = True
base = {'slope': blocked, 'water': wm, 'trees': tm, 'bones': bm, 'fence': fm, 'edge': edge}
np.savez_compressed('drive_grid.npz', H=H, slope_deg=slope, **base)
print('blocked shares: ' + ', '.join('%s %.1f%%' % (k, 100 * v.mean()) for k, v in base.items()))
