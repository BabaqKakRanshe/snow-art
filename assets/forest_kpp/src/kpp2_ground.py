"""Ground height for KPP v2 placements: the game terrain (tile 1_1, levelled along the v2 walls: walls_v2/terrain_levelled_1_1.npy)
under a point given in the booth frame (Checkpoint root) or the gate frame (Gate root), returned as z in that frame.
python3 kpp2_ground.py booth x y [x y ...] | gate x y [...]   (also importable: ground_z(frame, x, y))"""
import os, sys, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
H1 = np.load(os.path.join(HERE, 'walls_v2', 'terrain_levelled_1_1.npy'))
STEP = 600.0 / (H1.shape[0] - 1)
GP = json.load(open(os.path.join(HERE, 'out', 'kpp_contract.json')))['meta']['game_placement']
A_U = np.array(((-1, 0, 0), (0, 0, 1), (0, -1, 0)), float)        # package frame (Blender, z up) -> Unity prefab-local


def sample(x, z):
    u, v = x / STEP, (z + 600.0) / STEP
    i0, j0 = int(np.floor(u)), int(np.floor(v))
    fu, fv = u - i0, v - j0
    H = H1
    return float((H[j0, i0] * (1 - fu) + H[j0, i0 + 1] * fu) * (1 - fv) + (H[j0 + 1, i0] * (1 - fu) + H[j0 + 1, i0 + 1] * fu) * fv)


def frame(name):
    g = GP['Checkpoint' if name == 'booth' else 'Gate']
    a = math.radians(g['yawUnity'])
    Ry = np.array(((math.cos(a), 0, math.sin(a)), (0, 1, 0), (-math.sin(a), 0, math.cos(a))))
    return np.array(g['p'], float), Ry @ A_U


def ground_z(name, x, y):
    """z of the ground under (x, y) in the frame 'booth' or 'gate' (the Gate root's own frame)"""
    p0, R = frame(name)
    u = p0 + R @ np.array((x, y, 0.0))
    h = sample(u[0], u[2])
    # the ground point in Unity, back to the frame: the frame's z is Unity up (R maps z to Unity y)
    q = R.T @ (np.array((u[0], h, u[2])) - p0)
    return float(q[2]), (float(u[0]), h, float(u[2]))


if __name__ == '__main__':
    name = sys.argv[1]
    v = [float(a) for a in sys.argv[2:]]
    for x, y in zip(v[0::2], v[1::2]):
        z, u = ground_z(name, x, y)
        print(f'{name} ({x:.2f}, {y:.2f}) -> z {z:+.3f}  (Unity {u[0]:.2f}, {u[1]:.3f}, {u[2]:.2f})')
