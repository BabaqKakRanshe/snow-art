"""Walkability round the checkpoint with the contract colliders and the map's fence (FenceChain at y 0, x <= -4.47 and
x >= 13.5): capsule r 0.30, h 1.80, step 0.35; the gate shut and the boom down (the prologue's start): from the road in
front of the barrier past the booth (the walkway) to the door and into the room; the prologue points within reach (1.0 m).
Then the boom up and the gate open: the car's way through (clear width at the barrier and the gate).
python3 walk.py [_draft]"""
import json, math, sys
import numpy as np
from collections import deque
from scipy.ndimage import distance_transform_edt

SUF = sys.argv[1] if len(sys.argv) > 1 else ''
C = json.load(open(f'/home/claude/uaz/out/kpp_contract{SUF}.json'))
FLOOR, R, H, STEP = 0.15, 0.30, 1.80, 0.35
res = 0.02
xs = np.arange(-9.0, 20.0, res)
ys = np.arange(-14.0, 7.0, res)
X, Y = np.meshgrid(xs, ys, indexing='ij')
pad = (np.abs(X) <= 3.05) & (np.abs(Y) <= 2.55)
base = np.where(pad, FLOOR, -0.15)


def blocked(skip=(), extra=()):
    b = np.zeros(X.shape, bool)
    for c in C['colliders']:
        if c['name'] in skip or 'rotation' in c:
            continue
        cx, cy, cz = c['center_kpp']
        sx, sy, sz = c['size']
        z0, z1 = cz - sz / 2, cz + sz / 2
        m = (np.abs(X - cx) <= sx / 2) & (np.abs(Y - cy) <= sy / 2)
        b |= m & (z1 > base + STEP) & (z0 < base + H)
    for (x0, x1, y0, y1) in extra:
        b |= (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1)
    return b


FENCE = [(-60.0, -4.47, -0.05, 0.05), (13.5, 60.0, -0.05, 0.05)]


def reach_from(free, start):
    i0 = (int(round((start[0] - xs[0]) / res)), int(round((start[1] - ys[0]) / res)))
    r = np.zeros_like(free)
    if not free[i0]:
        return r, False
    q = deque([i0])
    r[i0] = True
    while q:
        i, j = q.popleft()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b_ = i + di, j + dj
            if 0 <= a < free.shape[0] and 0 <= b_ < free.shape[1] and free[a, b_] and not r[a, b_]:
                r[a, b_] = True
                q.append((a, b_))
    return r, True


# 1. the start: gate shut, boom down; the door open (its collider out), the chair where it stands
blk = blocked(skip=('COL_Door', 'COL_Pad'), extra=FENCE)
free = distance_transform_edt(~blk) * res > R
reach, ok = reach_from(free, (7.0, -12.0))
room = (X > -1.98) & (X < 1.98) & (Y > -1.48) & (Y < 1.48)
inside_station = (Y > 0.6) & (np.abs(X) > 3.2)
print('start on the road free:', ok)
print('the room reached: %.2f m2 of %.2f m2 free' % ((reach & room).sum() * res * res, (free & room).sum() * res * res))
print('inside the station reached on foot (gate shut):', bool((reach & inside_station).any()))
walk_l = reach & (X < -3.05) & (X > -4.47) & (np.abs(Y) < 0.3)
walk_r = reach & (X > 2.10) & (X < 3.6) & (np.abs(Y) < 0.3)
print('walkway left of the booth: %s, right of the booth (road side): %s' % (bool(walk_l.any()), bool(walk_r.any())))
for k in ('Key_Hook_Schranke', 'Key_Hook_Generator', 'Hand_KeyBoxDoor', 'Spot_KPPLog', 'Hand_Phone_Receiver', 'Hand_BoothWindow',
          'Hand_Drawer_75', 'Hand_Drawer_78', 'Spot_Padlock', 'Hand_BarrierArm', 'Hand_Gate', 'Hand_Gate_2', 'Hand_BoothDoor_Out',
          'Seat_Chair', 'Hide_UnderDesk'):
    s = C['sockets'][k]
    x, y, z = s['pos']
    d = np.hypot(X - x, Y - y)
    okk = reach & (d < 1.0)
    dm = float(d[reach].min()) if reach.any() else 9
    print(f'  {k:22s} reachable: {bool(okk.any())}  nearest free point {dm:.2f} m')
# 2. boom up, gate open: the car's way (a 2.0 m wide car + 0.25 each side = clear 2.5 m)
blk2 = blocked(skip=('COL_Door', 'COL_Pad', 'COL_Boom', 'COL_Gate_Leaf'), extra=FENCE)
lx = C['parts']['IX_Gate_81']['pivot'][0]
blk2 |= (X >= lx + 6.6) & (X <= lx + 6.6 + 7.0) & (np.abs(Y - 0.22) <= 0.035)       # the leaf, open
for name, (ya, yb) in (('barrier band y -7.35..-6.55', (-7.35, -6.55)), ('gate band y -0.15..0.45', (-0.15, 0.45))):
    ia, ib = int(round((ya - ys[0]) / res)), int(round((yb - ys[0]) / res))
    row = blk2[:, ia:ib + 1].any(axis=1)                    # a car crossing the line: everything in the band is in its way
    runs, cur = [], None
    for i, bb in enumerate(row):
        if not bb and cur is None:
            cur = i
        if bb and cur is not None:
            runs.append((xs[cur], xs[i - 1]))
            cur = None
    if cur is not None:
        runs.append((xs[cur], xs[-1]))
    wide = [(round(a, 2), round(b, 2), round(b - a, 2)) for a, b in runs if 2.0 < a < 14.5 or 2.0 < b < 14.5]
    print(f'  {name}: clear spans {wide}')
