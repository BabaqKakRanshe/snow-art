import bpy, math
import numpy as np
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
o = bpy.data.objects['Snow_DoorDrift']
kb = o.data.shape_keys.key_blocks
print('shape keys', [k.name for k in kb], 'Clear value', kb['Clear'].value, 'hidden', o.hide_render)
B = np.array([tuple(o.matrix_world @ k.co) for k in kb['Basis'].data])
Cl = np.array([tuple(o.matrix_world @ k.co) for k in kb['Clear'].data])
me = o.data; me.calc_loop_triangles()
tris = [tuple(t.vertices) for t in me.loop_triangles]
# dense samples on the top surface
rng = np.random.default_rng(0)
S = []
for a, b, c in tris:
    for _ in range(40):
        r1, r2 = rng.random(), rng.random()
        if r1 + r2 > 1: r1, r2 = 1 - r1, 1 - r2
        S.append((a, b, c, r1, r2))
S = np.array(S)
idx = S[:, :3].astype(int); r1 = S[:, 3:4]; r2 = S[:, 4:5]
def pts(V):
    return V[idx[:, 0]] + (V[idx[:, 1]] - V[idx[:, 0]]) * r1 + (V[idx[:, 2]] - V[idx[:, 0]]) * r2
PB, PC = pts(B), pts(Cl)
hinges = [(-2.47, 0.815), (-2.47, -0.815)]
for clear in (0.0, 0.5, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0):
    P = PB * (1 - clear) + PC * clear
    worst = 0
    for hx, hy in hinges:
        d = np.hypot(P[:, 0] - hx, P[:, 1] - hy)
        m = (d < 0.82) & (P[:, 0] < -2.47)
        if m.any():
            worst = max(worst, P[m, 2].max())
    print(f'Clear {clear*100:5.1f}: max snow height inside the leaves\' swing {worst:.3f} m  (door bottom z 0.11) -> {"BLOCKS" if worst > 0.11 else "clear"}')
# angle reachable at full snow for Door_R: the leaf bottom edge sweeps; find first angle where any leaf point (z=0.11) is below snow
for clear in (0.0, 0.7):
    P = PB * (1 - clear) + PC * clear
    for name, (hx, hy), sgn in (('Door_R', hinges[1], 1), ('Door_L', hinges[0], -1)):
        for ang in range(1, 171):
            a = math.radians(ang)
            # leaf line from the hinge: initially toward y=0 (sgn) -> rotates outward
            ok = True
            for s in np.linspace(0.02, 0.81, 30):
                x = hx - s * math.sin(a)
                y = hy + sgn * s * math.cos(a)
                near = np.hypot(P[:, 0] - x, P[:, 1] - y) < 0.03
                if near.any() and P[near, 2].max() > 0.11:
                    ok = False; break
            if not ok:
                print(f'  Clear {clear*100:.0f}: {name} leaf bottom meets the drift at {ang} deg'); break
        else:
            print(f'  Clear {clear*100:.0f}: {name} swings 170 deg freely')
