"""Walkability round the station yard with the contract colliders: capsule r 0.34, h 1.80, step 0.35 (the Snow player), per level (a 2D flood
fill on each floor height). FuelTanks: outside on the ground (0) from the yard to the pump's operator spot, the jerrycan,
the fill couplings, the stile's foot; inside the bund (floor 0.15) from the stile's inner foot round both tanks, the gap
between them (the hide spot), the ladder's foot; the stile's steps rise at most 0.35. Trafo: the pad (0.20); with the gate
shut the enclosure is closed, with the gate open (100) it is reached from the front, the hide spot behind the transformer,
the latch from outside.  python3 walk.py [_draft]"""
import json, math, sys
import numpy as np
from collections import deque
from scipy.ndimage import distance_transform_edt

SUF = sys.argv[1] if len(sys.argv) > 1 else ''
C = json.load(open(f'/home/claude/uaz/out/yard_contract{SUF}.json'))
R, H, STEP = 0.34, 1.80, 0.35                      # the Snow player's capsule (Player.prefab)
res = 0.02
S = C['sockets']


def grid(x0, x1, y0, y1):
    xs = np.arange(x0, x1, res)
    ys = np.arange(y0, y1, res)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    return xs, ys, X, Y


def blocked(X, Y, root, base, skip=(), extra=()):
    b = np.zeros(X.shape, bool)
    for c in C['colliders']:
        if c['root'] != root or c['name'] in skip:
            continue
        cx, cy, cz = c['center_root']
        sx, sy, sz = c['size']
        z0, z1 = cz - sz / 2, cz + sz / 2
        m = (np.abs(X - cx) <= sx / 2) & (np.abs(Y - cy) <= sy / 2)
        b |= m & (z1 > base + STEP) & (z0 < base + H)
    for poly in extra:
        b |= poly(X, Y)
    return b


def reach_from(xs, ys, free, start):
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


def near(X, Y, reach, p, rad=1.0):
    d = np.hypot(X - p[0], Y - p[1])
    ok = reach & (d < rad)
    return bool(ok.any()), float(d[reach].min()) if reach.any() else 9.0


# ---------------------------------------------------------------- FuelTanks
xs, ys, X, Y = grid(-9.0, 9.0, -9.0, 8.0)
bund = (np.abs(X) <= 4.30) & (np.abs(Y) <= 3.60)
blk_out = blocked(X, Y, 'FuelTanks', 0.0) | bund
free_out = distance_transform_edt(~blk_out) * res > R
reach_out, ok = reach_from(xs, ys, free_out, (-0.5, -8.0))
print('FuelTanks outside: start free', ok)
for k in ('Stand_PumpOperator', 'Spot_Jerrycan', 'Hand_PumpLever', 'Pump_Nozzle'):
    p = S[k]['pos']
    r_, dm = near(X, Y, reach_out, p)
    print(f'  {k:22s} reachable: {r_}  nearest free point {dm:.2f} m')
for name, p in (('fill coupling T1', (-3.25, -3.96)), ('fill coupling T2', (-3.50, -3.96)), ('stile foot', (3.46, -4.40)),
                ('signboard', (0.90, -3.95)), ('back of the bund', (0.0, 4.2))):
    r_, dm = near(X, Y, reach_out, p)
    print(f'  {name:22s} reachable: {r_}  nearest free point {dm:.2f} m')
inside = (np.abs(X) < 4.10) & (np.abs(Y) < 3.40)
blk_in = blocked(X, Y, 'FuelTanks', 0.15, skip=('COL_Bund_Slab',)) | ~inside
free_in = distance_transform_edt(~blk_in) * res > R
reach_in, ok = reach_from(xs, ys, free_in, (3.46, -2.62))
area = lambda m: m.sum() * res * res
print('inside the bund: start (the stile\'s inner foot) free', ok, ' reached %.1f of %.1f m2 free floor' %
      (area(reach_in & inside), area(free_in & inside)))
for name, p in (('Hide_TankGap', S['Hide_TankGap']['pos']), ('ladder foot', (3.35, -1.75)), ('left end', (-3.6, 0.0)),
                ('in front of tank 1', (0.0, -3.10)), ('behind tank 2', (0.0, 3.10)), ('the sump', (-3.65, -2.6))):
    r_, dm = near(X, Y, reach_in, p)
    print(f'  {name:22s} reachable: {r_}  nearest free point {dm:.2f} m')
top = lambda n: round(next(c['center_root'][2] + c['size'][2] / 2 for c in C['colliders'] if c['name'] == n), 3)
outs = [0.0] + [top(n) for n in ('COL_Stile_1', 'COL_Stile_2', 'COL_Stile_Top')]
ins = [0.15] + [top(n) for n in ('COL_Stile_4', 'COL_Stile_3', 'COL_Stile_Top')]
print('stile: outside', outs, 'rises', [round(b - a, 2) for a, b in zip(outs[:-1], outs[1:])],
      '| inside', ins, 'rises', [round(b - a, 2) for a, b in zip(ins[:-1], ins[1:])])
cl = {c['name']: c for c in C['colliders']}
rl, rr = cl['COL_Stile_Rail_L'], cl['COL_Stile_Rail_R']
gap = (rr['center_root'][0] - rr['size'][0] / 2) - (rl['center_root'][0] + rl['size'][0] / 2)
print(f'stile: clear width between the rail colliders {gap:.3f} m, the capsule {2 * R:.2f} m -> {"passes" if gap > 2 * R + 0.04 else "TOO TIGHT"}')
# ---------------------------------------------------------------- Trafo
xs, ys, X, Y = grid(-7.0, 7.0, -8.0, 6.0)
pad = (np.abs(X) <= 2.60) & (np.abs(Y) <= 2.10)
base_ok = lambda skip, extra: blocked(X, Y, 'Trafo', 0.20, skip=skip + ('COL_Trafo_Pad',), extra=extra)
piv = (-1.50, -2.00)
a = math.radians(-100.0)
d = (math.cos(a), math.sin(a))


def open_leaf(X, Y, L=1.56, w=0.05):
    u = (X - piv[0]) * d[0] + (Y - piv[1]) * d[1]
    v = -(X - piv[0]) * d[1] + (Y - piv[1]) * d[0]
    return (u >= 0) & (u <= L) & (np.abs(v) <= w / 2)


inside_t = (np.abs(X) < 2.47) & (Y > -1.97) & (Y < 1.75)
for label, skip, extra in (('gate shut', (), ()), ('gate open', ('COL_Gate_Leaf',), (open_leaf,))):
    free = distance_transform_edt(~base_ok(skip, extra)) * res > R
    reach, ok = reach_from(xs, ys, free, (-0.70, -4.50))
    print(f'Trafo, {label}: start free {ok}; inside reached {area(reach & inside_t):.1f} of {area(free & inside_t):.1f} m2 free')
    for k in ('Hand_TrafoGate', 'Hide_Trafo'):
        p = S[k]['pos']
        r_, dm = near(X, Y, reach, p)
        print(f'  {k:22s} reachable: {r_}  nearest free point {dm:.2f} m')
