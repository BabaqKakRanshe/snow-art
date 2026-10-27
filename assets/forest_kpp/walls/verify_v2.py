"""checks of u7_layout_v2.json: records and keepClear complete, the flat parts at one height, nothing overlapping that did not
before (U7's own footprint test), the diff consistent, trees and rocks on the ground that moves"""
import json, math
import numpy as np
U = json.load(open('/home/claude/uaz/out/forest_update7/u7_layout.json'))
V = json.load(open('u7_layout_v2.json'))
Df = json.load(open('diff.json'))
L = json.load(open('levelling.json'))
FIRST = 5649
n0, n1 = len(U['records']), len(V['records'])
assert n1 == n0 + len(Df['added']) and len(V['keep_clear']) == n1
for r in V['records']:
    assert set(r) == {'m', 'p', 'q', 'group'} and all(isinstance(v, float) for v in r['p']) and len(r['q']) == 4, r
ch = {c['id'] for c in Df['changed']}
for i, (a, b) in enumerate(zip(U['records'], V['records'])):
    if (a['p'] != b['p'] or a['q'] != b['q'] or a['m'] != b['m']) != ((FIRST + i) in ch):
        raise SystemExit('diff mismatch at %d' % (FIRST + i))
    assert a['m'] == b['m'] and a['group'] == b['group'] and a['q'] == b['q']
print('records', n0, '->', n1, 'changed', len(Df['changed']), 'added', len(Df['added']), 'removed', len(Df['removed']))
# moves and height changes
mv = [c for c in Df['changed'] if math.hypot(c['new']['p'][0] - c['old']['p'][0], c['new']['p'][2] - c['old']['p'][2]) > 1e-4]
dh = [c['new']['p'][1] - c['old']['p'][1] for c in Df['changed']]
print('moved in plan', len(mv), 'max move %.3f' % max(math.hypot(c['new']['p'][0] - c['old']['p'][0], c['new']['p'][2] - c['old']['p'][2]) for c in mv))
print('height changes: %d, min %+.3f max %+.3f' % (len(dh), min(dh), max(dh)))
by = {}
for c in Df['changed']:
    by.setdefault(c['m'], 0)
    by[c['m']] += 1
print('changed by model', by)
# U7's overlap test (outside the runs)
FOOT = {'ConcreteFence': (1.25, 0.12), 'ConcreteFence_b': (1.25, 0.12), 'ConcreteFence_Broken': (1.25, 0.12),
        'ConcreteFence_Sign': (1.25, 0.12), 'ConcreteFence_Plain': (1.25, 0.12), 'ConcreteFence_Wicket': (1.25, 0.12),
        'ConcreteFence_Socket': (0.48, 0.38), 'TankTooth': (0.5, 0.5), 'TankTooth_b': (0.5, 0.5),
        'RoadBlock_FBS': (1.19, 0.20), 'RoadBlock_Jersey': (1.0, 0.31), 'RoadBlock_Jersey_Striped': (1.0, 0.31),
        'RoadBlock_Cube': (0.5, 0.5), 'WireCoil': (2.5, 0.48), 'WireBarricade': (1.5, 0.75), 'Hedgehog': (0.8, 0.8),
        'Abatis': (4.3, 1.35), 'Abatis_b': (3.8, 1.3), 'Sign_Halt': (0.62, 0.10), 'Sign_NoEntry': (0.30, 0.08)}
FOOT_OFF = {'Abatis': -0.55, 'Abatis_b': -0.75}
def yaw_of(q): return math.degrees(2 * math.atan2(q[1], q[3]))
def ux_of(y): t = math.radians(y); return np.array([math.cos(t), -math.sin(t)])
def uz_of(y): t = math.radians(y); return np.array([math.sin(t), math.cos(t)])
def obb(r):
    yaw = yaw_of(r['q']); ux, uz = ux_of(yaw), uz_of(yaw)
    c = np.array([r['p'][0], r['p'][2]]) - uz * FOOT_OFF.get(r['m'], 0.0)
    hx, hz = FOOT[r['m']]
    return c, ux, uz, hx, hz
def overlap(a, b):
    ca, ua, va, ha, ka = a; cb, ub, vb, hb, kb_ = b
    d = cb - ca
    for ax in (ua, va, ub, vb):
        if abs(d @ ax) > ha * abs(ua @ ax) + ka * abs(va @ ax) + hb * abs(ub @ ax) + kb_ * abs(vb @ ax) - 0.02:
            return False
    return True
def bad_pairs(R):
    boxes = [obb(r) for r in R]; cent = np.array([b[0] for b in boxes]); out = set()
    for i in range(len(R)):
        for j in np.nonzero(np.hypot(*(cent - cent[i]).T) < 10.0)[0]:
            if j <= i: continue
            mi, mj = R[i]['m'], R[j]['m']
            if {mi, mj} <= {'RoadBlock_FBS'} and abs(R[i]['p'][1] - R[j]['p'][1]) > 0.3: continue
            if mi.startswith('ConcreteFence') and mj.startswith('ConcreteFence'): continue
            if overlap(boxes[i], boxes[j]): out.add((i, j))
    return out
b0, b1 = bad_pairs(U['records']), bad_pairs(V['records'])
print('overlaps outside the runs: U7', len(b0), 'v2', len(b1), 'new', sorted((FIRST + i, FIRST + j) for i, j in b1 - b0))
# PO-2 pieces next to each other in a run: the moved ones against their neighbours (sockets apart, panels overlapping <= 4 cm)
print('levelling', [(s['name'], s['height'], s['ramp_start'], s['ramp_end'], round(math.dist(s['line'][0], s['line'][1]), 2)) for s in L['strips']])
print('objects on the ground that moves', json.dumps(L['objects']['in_strips']))
