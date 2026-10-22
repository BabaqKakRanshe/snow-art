"""Walkability with the contract colliders: capsule r 0.30, h 1.80, step 0.30 (boxes entirely below floor+step ignored)."""
import json, math
import numpy as np
from collections import deque

C = json.load(open('/home/claude/uaz/out/gen_contract.json'))
FLOOR, R, H, STEP = 0.10, 0.30, 1.80, 0.30
res = 0.01
xs = np.arange(-2.6, 2.6, res)
ys = np.arange(-1.9, 1.9, res)
X, Y = np.meshgrid(xs, ys, indexing='ij')
blocked = np.zeros(X.shape, bool)
names = {}
for c in C['colliders']:
    if c.get('rotation'):
        continue
    cx, cy, cz = c['center_body']
    sx, sy, sz = c['size']
    z0, z1 = cz - sz / 2, cz + sz / 2
    if z1 <= FLOOR + STEP + 1e-6 or z0 >= FLOOR + H:
        continue
    m = (np.abs(X - cx) <= sx / 2) & (np.abs(Y - cy) <= sy / 2)
    blocked |= m
    names[c['name']] = (cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, z0, z1)
# distance transform (brute force via scipy if available)
try:
    from scipy.ndimage import distance_transform_edt
    dist = distance_transform_edt(~blocked) * res
except Exception:
    raise
free = dist > R
inside = (X > -2.28) & (X < 2.28) & (Y > -1.58) & (Y < 1.58)


def idx(x, y):
    return int(round((x - xs[0]) / res)), int(round((y - ys[0]) / res))


start = idx(-1.9, 0.0)
print('door point free:', free[start], 'dist', dist[start])
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
# ascii map (5 cm): '#' blocked, '.' free+reachable, ',' free unreachable, ' ' too tight
rows = []
for j in range(free.shape[1] - 1, -1, -5):
    y = ys[j]
    if y < -1.62 or y > 1.62:
        continue
    line = ''
    for i in range(0, free.shape[0], 5):
        x = xs[i]
        if x < -2.32 or x > 2.32:
            continue
        line += '#' if blocked[i, j] else ('.' if reach[i, j] else (',' if free[i, j] else ' '))
    rows.append('%+.2f %s' % (y, line))
print('\n'.join(rows))
# narrowest passages: max inscribed radius along reachable cells
print('reachable area m2 (capsule centres):', reach.sum() * res * res)
# interaction points
hands = {k: s for k, s in C['sockets'].items() if s['kind'] in ('hand', 'pour', 'item_slot')}
EYE = FLOOR + 1.62
rx, ry = X[reach], Y[reach]
print('\nhand sockets: nearest reachable capsule centre, horizontal / eye distance')
worst = []
for k, s in hands.items():
    x, y, z = s['pos']
    if not (-2.28 < x < 2.28 and -1.58 < y < 1.58):
        continue
    d2 = (rx - x) ** 2 + (ry - y) ** 2
    i = int(np.argmin(d2))
    dh = math.sqrt(d2[i])
    de = math.sqrt(d2[i] + (EYE - z) ** 2)
    worst.append((de, k, dh, z, (round(float(rx[i]), 2), round(float(ry[i]), 2))))
for de, k, dh, z, at in sorted(worst, reverse=True)[:25]:
    print(f'  {k:28s} horiz {dh:.2f} m  eye-dist {de:.2f} m  socket z {z:.2f}  from {at}')
# aisle widths at some x: free span along y
print('\nfree spans (capsule centres) along y at x =')
for x in (-2.0, -1.5, -1.0, -0.5, 0.0, 0.4, 0.8, 1.2, 1.5, 1.8, 2.0, 2.2):
    i, _ = idx(x, 0)
    col = reach[i, :]
    spans, run = [], None
    for j, v in enumerate(col):
        if v and run is None:
            run = j
        if (not v) and run is not None:
            spans.append((round(ys[run], 2), round(ys[j - 1], 2)))
            run = None
    print('  x %+.2f:' % x, spans)
