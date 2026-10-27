"""The Leitstand's gate station (main 1.2) against what already stands on that desk: Update 3's dressing props
(Forest_Dressing.json colliders) and the desk lamp FX_DeskLamp_7 - plan gaps between footprints (negative = overlap).
python3 main_leit_check.py -> out/main_leit_check.json"""
import os, sys, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
C = json.load(open(os.path.join(HERE, 'out', 'main_contract.json')))
KC = json.load(open(os.path.join(HERE, 'out', 'snow_kit_contract.json')))
DR = json.load(open(os.path.join(HERE, 'out', 'forest_update6', 'stage', 'Assets', 'Locations', 'Forest', 'Data',
                                 'Forest_Dressing.json')))
PLACE = dict(p=[340.0, 16.7443, -360.0], yaw=8.0)              # main_build.PLACE (both prefabs)
A_U = np.array(((-1, 0, 0), (0, 0, 1), (0, -1, 0)), float)     # building frame -> Unity prefab-local
DESK = (2.20, 3.80, -1.95, -1.15)                              # the right workstation's desk top (z 0.75)


def Ry(deg):
    a = math.radians(deg)
    return np.array(((math.cos(a), 0, math.sin(a)), (0, 1, 0), (-math.sin(a), 0, math.cos(a))))


R_B = Ry(PLACE['yaw']) @ A_U                                   # building frame -> Unity world (rotation)


def to_building(pu):
    return R_B.T @ (np.asarray(pu, float) - np.array(PLACE['p']))


def quat_R(q):
    x, y, z, w = q
    return np.array(((1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
                     (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
                     (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y))))


def prop_poly(p):
    """the footprint (x, y in the building frame) of a dressing prop's box collider"""
    c, s = np.array(p['collider']['center']), np.array(p['collider']['size'])
    Rw = quat_R(p['q'])
    pts = []
    for sx in (-0.5, 0.5):
        for sz in (-0.5, 0.5):
            lu = c + np.array((sx * s[0], 0.0, sz * s[2]))
            pts.append(to_building(np.array(p['p']) + Rw @ lu)[:2])
    return hull(np.array(pts))


def kit_poly(name):
    ki = C['kit_instances'][name]
    lo, hi = KC['items'][ki['item']]['bbox']
    w, x, y, z = ki['rot_quat_wxyz']
    R = quat_R((x, y, z, w))
    t = np.array(ki['pos_building'])
    pts = [(t + R @ np.array((a, b, 0.0)))[:2] for a in (lo[0], hi[0]) for b in (lo[1], hi[1])]
    return hull(np.array(pts))


def hull(P):
    P = sorted(map(tuple, P))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return np.array(lo[:-1] + up[:-1])


def overlap(A, B):
    for poly in (A, B):
        for i in range(len(poly)):
            e = poly[(i + 1) % len(poly)] - poly[i]
            n = np.array((-e[1], e[0]))
            a, b = A @ n, B @ n
            if a.max() < b.min() or b.max() < a.min():
                return False
    return True


def seg_dist(p, a, b):
    ab = b - a
    t = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-12), 0, 1)
    return np.linalg.norm(p - (a + t * ab))


def gap(A, B):
    if overlap(A, B):
        return -1.0
    d = min(seg_dist(p, Q[i], Q[(i + 1) % len(Q)]) for P_, Q in ((A, B), (B, A)) for p in P_ for i in range(len(Q)))
    return float(d)


def rect(x0, x1, y0, y1):
    return np.array(((x0, y0), (x1, y0), (x1, y1), (x0, y1)))


import bpy                                                     # noqa: F401 - main_rooms needs mathutils
import main_rooms as MR
cx, cy, _ = MR.LEIT_CCTV
station = {'стойка мониторов': rect(cx - 0.212, cx + 0.212, cy - 0.225, cy + 0.255)}
for n in ('Leit_Monitor_Barrier', 'Leit_Console'):
    station[n] = kit_poly(n)
others = {'FX_DeskLamp_7 (настольная лампа)': rect(3.478, 3.622, -1.741, -1.325)}
for p in DR['props']:
    if p.get('room') != 'Leitstand' or 'collider' not in p:
        continue
    b = to_building(p['p'])
    if DESK[0] - 0.2 < b[0] < DESK[1] + 0.2 and DESK[2] - 0.2 < b[1] < DESK[3] + 0.2 and 0.6 < b[2] < 0.9:
        others[p['id']] = prop_poly(p)
rows = []
for sn, sp in station.items():
    for on, op in others.items():
        rows.append(dict(station=sn, other=on, gap=round(gap(sp, op), 3)))
desk_ok = all(DESK[0] - 1e-3 <= x <= DESK[1] + 1e-3 and DESK[2] - 1e-3 <= y <= DESK[3] + 1e-3
              for sp in station.values() for x, y in sp)
out = dict(note='plan gaps (m) between the gate station (the monitor stand, the lower monitor, the console) and what stands on '
                'the right desk; negative = overlap', on_desk=desk_ok, rows=rows,
           min_gap=min(r['gap'] for r in rows), others=sorted(others))
json.dump(out, open(os.path.join(HERE, 'out', 'main_leit_check.json'), 'w'), indent=1, ensure_ascii=False)
for r in sorted(rows, key=lambda r: r['gap'])[:8]:
    print(r)
print('on the desk:', desk_ok, 'min gap', out['min_gap'], 'others', out['others'])
