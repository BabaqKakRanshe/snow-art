"""U7 records near the gate and the barrier in their local (Blender) frames: gate x along the wall (+ = west, the
leaf's parking side), y inside; barrier x along the boom (post -> rest), y toward the booth"""
import json, math
import numpy as np
U = json.load(open('/home/claude/uaz/out/forest_update7/u7_layout.json'))
FIRST = 5649
def yaw_of(q): return math.degrees(2 * math.atan2(q[1], q[3]))
def ux_of(y): t = math.radians(y); return np.array([math.cos(t), -math.sin(t)])
def uz_of(y): t = math.radians(y); return np.array([math.sin(t), math.cos(t)])
GP = np.array(U['gate']['game'])[[0, 2]]; GY = 8.0
GX_B = -ux_of(GY); GY_B = -uz_of(GY)          # Blender +x, +y of the gate in the world
B = U['barrier']; BP = np.array(B['post']); ARM = (np.array(B['rest']) - BP) / np.linalg.norm(np.array(B['rest']) - BP)
RIN = np.array(B['road_in'])
print('gate Blender +x', GX_B, '+y', GY_B, ' west_end local', (np.array(U['gate']['west_end']) - GP) @ GX_B,
      'east_end', (np.array(U['gate']['east_end']) - GP) @ GX_B)
print('barrier ARM', ARM, 'ROAD_IN', RIN, 'yaw', B['yaw'])
for name, O, X, Y in (('GATE', GP, GX_B, GY_B), ('BARRIER', BP, ARM, RIN)):
    rows = []
    for i, r in enumerate(U['records']):
        d = np.array([r['p'][0], r['p'][2]]) - O
        lx, ly = d @ X, d @ Y
        if abs(ly) < 8 and -40 < lx < 46:
            yaw = yaw_of(r['q'])
            bx = -ux_of(yaw)                            # the piece's Blender +x in the world
            rows.append((lx, ly, i + FIRST, r['m'], r['p'][1], r['group'], float(bx @ X)))
    rows.sort()
    print(name)
    for lx, ly, idx, m, y, g, bxx in rows:
        print('  %5d %-24s x=%7.3f y=%6.3f h=%7.3f %-9s bx.X=%+.2f' % (idx, m, lx, ly, y, g, bxx))
