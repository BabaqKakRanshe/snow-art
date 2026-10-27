"""heights along the two wall lines before (U7) and after (v2): local x, id, model, y U7, y v2, steps"""
import json, math, sys
import numpy as np
U = json.load(open('/home/claude/uaz/out/forest_update7/u7_layout.json'))
V = json.load(open('u7_layout_v2.json'))
D = json.load(open('walls_v2_data.json'))
FIRST = 5649
def frame(k):
    f = D[k]; P, X, Y = np.array(f['P']), np.array(f['X']), np.array(f['Y'])
    return lambda p: np.array([(np.array(p) - P) @ X, (np.array(p) - P) @ Y])
out = {}
for k, lo, hi in (('gate', -42, 40), ('barrier', -34, 38)):
    L = frame(k)
    def rows(R):
        o = []
        for i, r in enumerate(R):
            if not r['m'].startswith('ConcreteFence'):
                continue
            x, y = L([r['p'][0], r['p'][2]])
            if abs(y) < 0.05 and lo <= x <= hi:
                o.append((round(float(x), 3), FIRST + i, r['m'], r['p'][1]))
        return sorted(o)
    a, b = rows(U['records']), rows(V['records'])
    print('==', k, 'U7:', len(a), 'v2:', len(b))
    print('   U7: x id m y | v2: x id m y')
    n = max(len(a), len(b))
    ia = {r[1]: r for r in a}
    prev_a = prev_b = None
    tab = []
    for r in b:
        o = ia.get(r[1])
        st_b = (r[3] - prev_b) if prev_b is not None and r[2] != 'ConcreteFence_Socket' else None
        tab.append(dict(x=r[0], id=r[1], m=r[2], y=r[3], x_u7=o[0] if o else None, y_u7=o[3] if o else None))
        if r[2] != 'ConcreteFence_Socket':
            prev_b = r[3]
        print('  %7.2f %5d %-22s %8.4f   (U7 %s)%s' % (r[0], r[1], r[2], r[3],
              ('x %7.2f y %8.4f' % (o[0], o[3])) if o else 'new', '' if st_b is None else '  step %+.3f' % st_b))
    out[k] = tab
json.dump(out, open('tables_v2.json', 'w'), indent=1)
