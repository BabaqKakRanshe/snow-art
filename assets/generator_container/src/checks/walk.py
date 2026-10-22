"""Walkability of the container with the contract colliders: capsule r 0.30, h 1.80, step 0.30 above the floor."""
import json, math, sys
import numpy as np
from collections import deque
from scipy.ndimage import distance_transform_edt

SUF = sys.argv[1] if len(sys.argv) > 1 else ''
C = json.load(open(f'/home/claude/uaz/out/cont_contract{SUF}.json'))
FLOOR, R, H, STEP = 0.31, 0.30, 1.80, 0.30
res = 0.01
xs = np.arange(-3.0, 3.0, res)
ys = np.arange(-2.4, 2.4, res)
X, Y = np.meshgrid(xs, ys, indexing='ij')
blocked = np.zeros(X.shape, bool)
for c in C['colliders']:
    cx, cy, cz = c['center_body']
    sx, sy, sz = c['size']
    z0, z1 = cz - sz / 2, cz + sz / 2
    if z1 <= FLOOR + STEP + 1e-6 or z0 >= FLOOR + H:
        continue
    blocked |= (np.abs(X - cx) <= sx / 2) & (np.abs(Y - cy) <= sy / 2)
dist = distance_transform_edt(~blocked) * res
free = dist > R
inside = (X > -2.97) & (X < 2.90) & (Y > -2.345) & (Y < 2.345)


def idx(x, y):
    return int(round((x - xs[0]) / res)), int(round((y - ys[0]) / res))


start = idx(-2.55, -1.20)
print('door point free:', free[start], 'dist', round(float(dist[start]), 3))
reach = np.zeros_like(free)
q = deque([start])
reach[start] = True
while q:
    i, j = q.popleft()
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a, b = i + di, j + dj
        if 0 <= a < free.shape[0] and 0 <= b < free.shape[1] and free[a, b] and not reach[a, b] and inside[a, b]:
            reach[a, b] = True
            q.append((a, b))
rows = []
for j in range(free.shape[1] - 1, -1, -6):
    y = ys[j]
    line = ''
    for i in range(0, free.shape[0], 6):
        line += '#' if blocked[i, j] else ('.' if reach[i, j] else (',' if free[i, j] and inside[i, j] else ' '))
    rows.append('%+.2f %s' % (y, line))
print('\n'.join(rows))
print('reachable area m2 (capsule centres):', round(float(reach.sum() * res * res), 2), 'of free', round(float((free & inside).sum() * res * res), 2))
hands = {k: s for k, s in C['sockets'].items() if s['kind'] in ('hand', 'pour', 'item_slot')}
EYE = FLOOR + 1.62
rx, ry = X[reach], Y[reach]
print('\ninside hand sockets: nearest reachable capsule centre, horizontal / eye distance (worst first)')
worst = []
for k, s in hands.items():
    x, y, z = s['pos']
    if not (-2.97 < x < 2.90 and -2.345 < y < 2.345):
        continue
    d2 = (rx - x) ** 2 + (ry - y) ** 2
    i = int(np.argmin(d2))
    dh = math.sqrt(d2[i])
    de = math.sqrt(d2[i] + (EYE - z) ** 2)
    worst.append((de, k, dh, z, (round(float(rx[i]), 2), round(float(ry[i]), 2))))
for de, k, dh, z, at in sorted(worst, reverse=True)[:25]:
    print(f'  {k:28s} horiz {dh:.2f} m  eye-dist {de:.2f} m  socket z {z:.2f}  from {at}')
print('\nfree spans (capsule centres) along y at x =')
for x in (-2.6, -2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5):
    i, _ = idx(x, 0)
    col = reach[i, :]
    spans, run = [], None
    for j, v in enumerate(col):
        if v and run is None:
            run = j
        if (not v) and run is not None:
            spans.append((round(float(ys[run]), 2), round(float(ys[j - 1]), 2)))
            run = None
    if run is not None:
        spans.append((round(float(ys[run]), 2), round(float(ys[-1]), 2)))
    print('  x %+.2f:' % x, spans)
