"""Walkability of the hut with the contract colliders (door open: its collider left out): capsule r 0.30, h 1.80, step
0.30; from the path outside the door into the room; the prologue's item spots within reach (1.0 m from a free point).
python3 walk.py [_draft] [R H]"""
import json, math, sys
import numpy as np
from collections import deque
from scipy.ndimage import distance_transform_edt

SUF = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith('_') else ''
C = json.load(open(f'/home/claude/hut11/out/hut_contract{SUF}.json'))
FLOOR, R, H, STEP = 0.33, 0.30, 1.80, 0.30
NUM = [float(a) for a in sys.argv[1:] if a.replace('.', '', 1).isdigit()]
if len(NUM) >= 2:                                      # walk.py [_draft] R H: another capsule (the game's: 0.36 1.82)
    R, H = NUM[0], NUM[1]
print(f'capsule r {R:.2f} h {H:.2f}')
res = 0.01
xs = np.arange(-3.0, 3.0, res)
ys = np.arange(-4.0, 3.0, res)
X, Y = np.meshgrid(xs, ys, indexing='ij')


def blocked_at(base):
    b = np.zeros(X.shape, bool)
    for c in C['colliders']:
        if c['parent'] != 'TowerHut' or c['name'] in ('COL_Door', 'COL_Floor', 'COL_Step'):
            continue
        cx, cy, cz = c['center_hut']
        sx, sy, sz = c['size']
        if 'rotation' in c:                                   # roof slopes: far above
            continue
        z0, z1 = cz - sz / 2, cz + sz / 2
        if z1 <= base + STEP + 1e-6 or z0 >= base + H:
            continue
        b |= (np.abs(X - cx) <= sx / 2) & (np.abs(Y - cy) <= sy / 2)
    return b


# inside the floor is at 0.33, outside the ground is 0: the band differs; a cell counts as free if it is free for its
# own level (room interior uses the floor band, the rest the ground band)
room = (X > -1.22) & (X < 1.22) & (Y > -1.08) & (Y < 1.08)
door = (X > -0.78) & (X < 0.02) & (Y >= -1.20) & (Y <= -1.08)
blk = np.where(room | door, blocked_at(FLOOR), blocked_at(0.0))
walls = np.zeros(X.shape, bool)                                   # the walls stay solid at both levels
for c in C['colliders']:
    if c['name'].startswith('COL_Wall') or c['name'] in ('COL_Window',):
        cx, cy, cz = c['center_hut']
        sx, sy, sz = c['size']
        if cz + sz / 2 <= STEP or cz - sz / 2 >= FLOOR + H:            # the lintel over the door is above the head
            continue
        walls |= (np.abs(X - cx) <= sx / 2) & (np.abs(Y - cy) <= sy / 2)
blk |= walls
dist = distance_transform_edt(~blk) * res
free = dist > R


def idx(x, y):
    return int(round((x - xs[0]) / res)), int(round((y - ys[0]) / res))


start = idx(-0.38, -2.10)
print('path point free:', free[start], 'dist', round(float(dist[start]), 3))
reach = np.zeros_like(free)
q = deque([start])
reach[start] = True
while q:
    i, j = q.popleft()
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a, b = i + di, j + dj
        if 0 <= a < free.shape[0] and 0 <= b < free.shape[1] and free[a, b] and not reach[a, b]:
            reach[a, b] = True
            q.append((a, b))
inroom = reach & room
print('room cells reached: %.2f m2 of %.2f m2 free' % (inroom.sum() * res * res, (free & room).sum() * res * res))
for k, s in C['sockets'].items():
    if not k.startswith('Spot_') and k not in ('Slot_Stove_Fire', 'Pour_Barrel', 'Hand_Window_Latch', 'Hand_Kettle', 'Hand_Axe',
                                               'Hand_Stove_Damper', 'Ladder_Roof_Bottom'):
        continue
    x, y, z = s['pos']
    d = np.hypot(X - x, Y - y)
    ok = reach & (d < 1.0)
    dm = float(d[reach].min()) if reach.any() else 9
    print(f'  {k:22s} reachable: {bool(ok.any())}  nearest free point {dm:.2f} m')
