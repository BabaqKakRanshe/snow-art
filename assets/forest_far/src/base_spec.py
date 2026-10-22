"""The Forest base's remaining prefabs (the shaft hatch, the helipad, the radio mast, the crates, the log pile, the yard
light poles, the power poles and their wires, the chain-link fence and the old boundary fence) - Update 3's data and the
dimensions of the rebuilt models.  Every prefab is built in its own frame, the frame of its Update 3 FBX after import:
x / y / z (z up), Unity prefab-local = (-x, z, -y).  The placements (Unity p, q xyzw: base_u3_data.json, from
Forest_Layout.json) stay as they are; Forest_Wires is a world model (the map frame).
The ground under each placement: base_ground.json (Update 3's terrain, scratchpad/u5/u5_ground.py)."""
import os, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
U3 = json.load(open(os.path.join(HERE, 'base_u3_data.json')))
GROUND = json.load(open(os.path.join(HERE, 'base_ground.json')))

ROOTS = ['Hatch', 'Helipad', 'RadioMast', 'Crates', 'LogPile', 'LightPole', 'PowerPole', 'FenceChain', 'OldFence',
         'OldFence_b', 'OldFence_c']                    # + the world model Forest_Wires


def placements(name):
    return U3['prefabs'].get(name) or U3['scatter'].get(name) or []


# ---------------------------------------------------------------- ground (bilinear on the sampled grid, prefab frame)
_G = {}


def _grid(name, i=0):
    key = (name, i)
    if key not in _G:
        g = GROUND['prefabs'][name][i]['grid']
        z = np.array([[np.nan if v is None else v for v in r] for r in g['z']], np.float64)
        _G[key] = (g['x0'], g['y0'], g['step'], np.nan_to_num(z, nan=float(np.nanmin(z))))
    return _G[key]


def ground(name, x, y, i=0):
    if name not in GROUND['prefabs']:
        return 0.0
    x0, y0, st, z = _grid(name, i)
    fi = min(max((x - x0) / st, 0.0), z.shape[1] - 1.0001)
    fj = min(max((y - y0) / st, 0.0), z.shape[0] - 1.0001)
    i_, j_ = int(fi), int(fj)
    a, b = fi - i_, fj - j_
    q = z[j_:j_ + 2, i_:i_ + 2]
    return float((q[0, 0] * (1 - a) + q[0, 1] * a) * (1 - b) + (q[1, 0] * (1 - a) + q[1, 1] * a) * b)


def ground_v(name, X, Y, i=0):
    if name not in GROUND['prefabs']:
        return np.zeros(len(X), np.float32)
    x0, y0, st, z = _grid(name, i)
    fi = np.clip((np.asarray(X, np.float64) - x0) / st, 0, z.shape[1] - 1.0001)
    fj = np.clip((np.asarray(Y, np.float64) - y0) / st, 0, z.shape[0] - 1.0001)
    i_, j_ = np.floor(fi).astype(int), np.floor(fj).astype(int)
    a, b = fi - i_, fj - j_
    return ((z[j_, i_] * (1 - a) + z[j_, i_ + 1] * a) * (1 - b) + (z[j_ + 1, i_] * (1 - a) + z[j_ + 1, i_ + 1] * a) * b).astype(np.float32)


# ---------------------------------------------------------------- the shaft hatch (Update 3's Hatch, IX_HatchLid_94)
HATCH = dict(collar=1.50, top=0.50, bottom=-0.25, chamfer=0.035, frame_in=0.91, frame_out=0.975,
             lid=0.90, lid_top=0.595, lid_skirt=0.51, lid_gap=0.03, pivot=(-0.90, 0.0, 0.51), hinge_y=(-0.58, 0.58),
             vent=(-1.18, 1.18), vent_top=1.22, sign_posts=(1.70, 2.30), sign_y=-1.93, sign=(2.0, 1.35, 0.93, 0.28),
             shaft_floor=0.06, staple_x=1.035, staple_top=0.66, handle_x=0.52)

# ---------------------------------------------------------------- the helipad (Update 3's sizes)
HELI = dict(r=10.40, top=0.15, bottom=-0.30, chamfer=0.03, h_bar=(1.25, 1.95, 2.50), h_cross=0.35,
            ring=(7.10, 7.80), ring_dashes=40, lights_r=9.60, light_top=0.43, sock=(13.0, 6.0), sock_top=6.40,
            sign=(13.0, -11.53, 1.60, 1.20, 0.42), sign_posts=(12.60, 13.40), pallet=(-12.5, 4.0),
            extinguisher=(11.55, -10.95))

# ---------------------------------------------------------------- the radio mast (60 m, guyed; Update 3's places)
MAST = dict(h=60.0, c0=1.02, c1=0.52, bay=1.5, leg_r=(0.055, 0.042), bar_r=0.024, diag_r=0.021,
            footings=1.10, footing=1.30, beacons=(20.0, 40.0), beacon_top=60.16, rod_top=64.6, bracket=0.30,
            guy_z=(21.0, 42.0, 57.0), anchors=((31.53, 9.76), (-24.22, 22.43), (-7.33, -32.19)), anchor_block=1.20,
            anchor_top=0.40, bands=7, ladder_y=-1.0)


def mast_c(z):
    """half the face width (corner offset) at height z"""
    m = MAST
    return m['c0'] + (m['c1'] - m['c0']) * max(0.0, min(1.0, z / m['h']))


# ---------------------------------------------------------------- crates, log pile (Update 3's places)
LOGS = [(-2.756, 2.244, -0.660, 0.200, 0.192), (-2.740, 2.260, -0.220, 0.200, 0.183),   # (x0, x1, y, z, r) bottom row
        (-2.811, 2.189, 0.220, 0.200, 0.230), (-2.621, 2.379, 0.660, 0.200, 0.190),
        (-2.329, 2.671, -0.440, 0.560, 0.219), (-2.761, 2.239, 0.000, 0.560, 0.204),     # middle row
        (-2.351, 2.649, 0.440, 0.560, 0.201),
        (-2.102, 2.898, -0.220, 0.920, 0.192), (-2.558, 2.442, 0.220, 0.920, 0.188)]     # top row

# ---------------------------------------------------------------- yard light pole (Update 3's lamp: light 5.85, halo 5.95)
LPOLE = dict(r0=0.082, r1=0.058, top=6.0, arm_x=0.92, head=(0.80, 1.30, -0.11, 0.11, 5.99, 6.11),
             lens=(0.84, 1.26, -0.08, 0.08, 5.985), foot=0.25, foot_top=0.05, foot_bottom=-0.40)

# ---------------------------------------------------------------- power pole (the yard's trafo pole, 0.32 m higher)
PPOLE = dict(top=9.0, r0=0.135, r1=0.108, bottom=-1.0, xarm=(8.47, 8.57), insul_x=(-1.05, 0.45, 1.05), insul_top=8.72)

# ---------------------------------------------------------------- chain-link fence section (Update 3's FenceChain: 3 m)
FENCE = dict(x0=-1.5, x1=1.5, post_x=1.5, post_r=0.035, post_top=2.30, post_bottom=-0.40, rail_z=2.20, rail_r=0.021,
             mesh_z=(0.03, 2.20), arm=((0.0, 2.30), (-0.36, 2.66)), barb_z=(2.40, 2.52, 2.64), barb_y=(-0.10, -0.22, -0.34))

# ---------------------------------------------------------------- the old boundary fence (Update 3's OldFence a / b / c: 4 m)
# post at x 2 (top displaced as Update 3's lean); four rusty barbed strands from x -2 (the previous section's post) to
# the post: (height at the ends, sag at the middle) - Update 3's slack wires
OLD = {'OldFence': dict(top=(1.991, -0.159, 1.893), strands=((0.407, 0.232), (0.827, 0.263), (1.247, 0.286), (1.667, 0.217)),
                        broken=None),
       'OldFence_b': dict(top=(1.968, -0.076, 1.899), strands=((0.407, 0.270), (0.827, 0.200), (1.247, 0.067), (1.667, 0.232)),
                          broken=None),
       'OldFence_c': dict(top=(2.012, 0.195, 1.890), strands=((0.407, 0.110), (0.827, 0.165), (1.247, 0.068), (1.667, 0.304)),
                          broken=1)}
OLD_POST_R = 0.062

# ---------------------------------------------------------------- map frame (Blender world: Unity (x, y, z) -> (-x, -z, y))
def _qrot(q, v):
    x, y, z, w = q
    u = np.array([x, y, z], np.float64)
    v = np.asarray(v, np.float64)
    return 2.0 * u.dot(v) * u + (w * w - u.dot(u)) * v + 2.0 * w * np.cross(u, v)


def frame_matrix(p, q):
    """4x4: a prefab's own frame -> the Blender map frame, for the placement p, q"""
    bw = lambda u: np.array([-u[0], -u[2], u[1]])
    ex, ey, ez = bw(_qrot(q, (-1, 0, 0))), bw(_qrot(q, (0, 0, -1))), bw(_qrot(q, (0, 1, 0)))
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2] = ex, ey, ez
    M[:3, 3] = [-p[0], -p[2], p[1]]
    return M


def map_matrix(name, i=0):
    e = placements(name)[i]
    return frame_matrix(e['p'], e['q'])


def local_to_map(name, v, i=0):
    M = map_matrix(name, i)
    return (M @ np.array([v[0], v[1], v[2], 1.0]))[:3]


# ---------------------------------------------------------------- the overhead line (Forest_Wires): Update 3's spans
# the yard's trafo pole (yard_kit POLE (0, 2), insulators at x -1.05 / 0.45 / 1.05, top 8.40) -> PowerPole 1 -> 2,
# trafo -> PowerPole 3 -> 4 (the poles in Forest_Layout order); three conductors each, insulator to the same insulator
TRAFO_P = dict(p=[392.0185, 16.2829, -349.1338], q=[0.0, 0.069756, 0.0, 0.997564])
TRAFO_INS = [(x, 2.0, 8.405) for x in PPOLE['insul_x']]
SPANS = [('T', 1), (1, 2), ('T', 3), (3, 4)]
LINE_ENDS = (2, 4)                                         # the line comes down a cable riser at these poles
WIRE_SAG = 0.0024                                          # sag = WIRE_SAG x span^2 (Update 3's slack line: ~0.8 m in 18 m)


def insulators(who):
    """the three insulator tops of the trafo ('T') or PowerPole n (1..4) in the Blender map frame"""
    if who == 'T':
        M = frame_matrix(TRAFO_P['p'], TRAFO_P['q'])
        return [(M @ np.array([*v, 1.0]))[:3] for v in TRAFO_INS]
    return [local_to_map('PowerPole', (x, 0.0, PPOLE['insul_top'] + 0.005), who - 1) for x in PPOLE['insul_x']]
