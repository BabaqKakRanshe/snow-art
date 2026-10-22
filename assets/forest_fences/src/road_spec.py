"""The Forest map's road prefabs (the prologue road from the SPERRGEBIET gate to the observatory) - Update 3's data and the
dimensions of the rebuilt models.  Every prefab is built in its own frame, the frame of its Update 3 FBX after import:
x / y / z (z up), Unity prefab-local = (-x, z, -y); a sign's face looks to -y (Unity +z).  The map placement (Unity p,
q xyzw) is Update 3's (road_u3_data.json, from Forest_Layout.json) and stays as it is.

The ground under each prefab comes from Update 3's terrain (Forest_Terrain.fbx: the tiles and Forest_Road), sampled
along the prefab's local z in its own frame (road_ground.json, made by scratchpad/trail2/road_ground.py): posts,
pillars, piles and legs go down into it, the fallen spruce lies on it, the cuts sit at the road's edges."""
import os, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
U3 = json.load(open(os.path.join(HERE, 'road_u3_data.json')))
GROUND = json.load(open(os.path.join(HERE, 'road_ground.json')))


def place(name):
    e = U3['prefabs'][name][0]
    return dict(p=e['p'], q=e['q'])


# ---------------------------------------------------------------- ground (bilinear on the sampled grid, in the prefab frame)
_G = {}


def _grid(name):
    if name not in _G:
        g = GROUND['prefabs'][name]['grid']
        z = np.array([[np.nan if v is None else v for v in r] for r in g['z']], np.float64)
        _G[name] = (g['x0'], g['y0'], g['step'], z, g['surf'])
    return _G[name]


def ground(name, x, y):
    """ground height (local z) under (x, y) in the prefab's frame"""
    x0, y0, st, z, _ = _grid(name)
    fi, fj = (x - x0) / st, (y - y0) / st
    i, j = int(math.floor(fi)), int(math.floor(fj))
    i = min(max(i, 0), z.shape[1] - 2)
    j = min(max(j, 0), z.shape[0] - 2)
    a, b = min(max(fi - i, 0.0), 1.0), min(max(fj - j, 0.0), 1.0)
    q = z[j:j + 2, i:i + 2]
    return float((q[0, 0] * (1 - a) + q[0, 1] * a) * (1 - b) + (q[1, 0] * (1 - a) + q[1, 1] * a) * b)


def ground_v(name, X, Y):
    """vectorised ground() for arrays (the painters)"""
    x0, y0, st, z, _ = _grid(name)
    fi = np.clip((np.asarray(X, np.float64) - x0) / st, 0, z.shape[1] - 1.0001)
    fj = np.clip((np.asarray(Y, np.float64) - y0) / st, 0, z.shape[0] - 1.0001)
    i, j = np.floor(fi).astype(int), np.floor(fj).astype(int)
    a, b = fi - i, fj - j
    zz = np.nan_to_num(z, nan=float(np.nanmin(z)))
    return ((zz[j, i] * (1 - a) + zz[j, i + 1] * a) * (1 - b) + (zz[j + 1, i] * (1 - a) + zz[j + 1, i + 1] * a) * b).astype(np.float32)


def surface(name, x, y):
    x0, y0, st, z, s = _grid(name)
    i = min(max(int(round((x - x0) / st)), 0), z.shape[1] - 1)
    j = min(max(int(round((y - y0) / st)), 0), z.shape[0] - 1)
    return s[j][i]


def ground_min(name, pts):
    return min(ground(name, x, y) for x, y in pts)


# ---------------------------------------------------------------- the signs (Update 3's faces, posts and heights)
# face: the sign's face (w, z0, z1) as Update 3 had it; the plate is the face + 15 mm all round (Update 3's grey plate);
# posts at 0.64 of the half width (Update 3's); colours and texts read off Update 3's T_ObsSigns
BLUE, GREEN, BROWN, WHITE_F = 'blue', 'green', 'brown', 'white'
SIGNS = {
    'Sign_Observatory': dict(face=(2.40, 1.838, 2.162), post=0.768, scheme=BLUE, de='RADIOOBSERVATORIUM HOHENMOOS',
                             en='RADIO OBSERVATORY', note='at the SPERRGEBIET gate, the station\'s name'),
    'Sign_Viewpoint': dict(face=(1.20, 1.442, 1.758), post=0.384, scheme=BROWN, de='AUSSICHTSPUNKT', en='VIEWPOINT',
                           note='the overlook\'s sign at the road (tourist brown)'),
    'Sign_Lookout': dict(face=(1.30, 1.432, 1.768), post=0.416, scheme=GREEN, de='FEUERWACHTURM', en='FIRE LOOKOUT',
                         note='the fire lookout (forestry green)'),
    'Sign_Pump': dict(face=(1.10, 1.392, 1.808), post=0.352, scheme=BLUE, de='PUMPWERK', en='PUMP STATION',
                      note='the pump house by the river'),
    'Sign_Radar': dict(face=(0.90, 1.393, 1.807), post=0.288, scheme=BLUE, de='RADAR', en=None, note='the radome'),
    'Sign_Relay': dict(face=(1.30, 1.404, 1.796), post=0.416, scheme=BLUE, de='RELAISSTATION', en='RELAY STATION',
                       note='the relay mast'),
    'Sign_Weather': dict(face=(1.30, 1.417, 1.783), post=0.416, scheme=BLUE, de='WETTERSTATION', en='WEATHER STATION',
                         note='the weather station'),
}
DIST = {'Dist_11': '1,1', 'Dist_09': '0,9', 'Dist_07': '0,7', 'Dist_23': '2,3', 'Dist_03': '0,3'}
for _n, _km in DIST.items():
    SIGNS[_n] = dict(face=(1.50, 1.484, 1.716), post=0.480, scheme=WHITE_F, de=f'OBSERVATORIUM {_km} km', en=None,
                     note='distance sign along the road (1,1 -> 0,9 -> 0,7 -> 2,3 -> 0,3: the fourth lies, it should read '
                          '0,5 - as Update 3)' if _n == 'Dist_23' else 'distance sign along the road')
SIGN_ORDER = ['Sign_Observatory', 'Dist_11', 'Dist_09', 'Dist_07', 'Sign_Viewpoint', 'Dist_23', 'Dist_03', 'Sign_Weather',
              'Sign_Lookout', 'Sign_Pump', 'Sign_Radar', 'Sign_Relay']
BORDER = 0.015            # plate = face + 15 mm all round
FACE_Y = -0.024           # the face plane (Update 3's)
PLATE_BACK = -0.010       # the plate's fold reaches back to here; the rails behind it touch the posts (front y 0)
POST_R, POST_Y = 0.030, 0.030       # galvanised tube 60.3 behind the plate (Update 3: 0.052 x 0.06 at y 0..0.06)
POST_BOT = -0.40          # Update 3's: the posts go 0.40 below the pivot (deeper where the ground is higher)
CORNER_R = 0.022          # rounded plate corners

# ---------------------------------------------------------------- the EuroPost delineators (Update 3's scatter: 48)
POST = dict(h=1.00, below=0.35, w=0.120, d=0.100, band=0.25, refl=(0.040, 0.180))   # reflector w x h on both faces (+-y)

# ---------------------------------------------------------------- the SPERRGEBIET gate (Update 3's layout)
GATE = dict(pillar_x=4.25, pillar=0.40, pillar_top=2.80, cap=(0.48, 0.06), leaf_x=(0.045, 3.985), tube_r=0.0302,
            rail_z=(0.150, 2.300), mesh_z=(0.180, 2.270), mid_r=0.0212, brace_r=0.0212, plate=(1.63, 0.564),
            plate_cz=1.350, plate_x=2.0, plate_y=0.054, bars_z=(1.232, 1.468), bars_x=(1.08, 2.92),
            barb_foot=2.44, barb_h=0.42, barb_top=2.86, hinge_z=(0.42, 2.05), lock_z=1.20)

# ---------------------------------------------------------------- the trestle bridge (Update 3's Bridge30)
BRIDGE = dict(
    deck_x=(-15.0, 15.0), plank_pitch=0.30, plank_w=0.26, plank_t=0.10, plank_top=-0.010, half_w=2.30,
    strips_y=(-0.95, 0.95), strip_w=0.70, strip_top=0.060, strip_boards=3,
    stringers_y=(-1.95, -1.17, -0.39, 0.39, 1.17, 1.95), stringer_r=0.18, stringer_x=(-15.55, 15.55), joints_x=(-5.0, 5.0),
    piers_x=(-5.0, 5.0), cap=(0.40, 0.40, 5.20), piles_y=(-2.30, -0.77, 0.77, 2.30), pile_r=0.155,
    posts_x=[-15.0 + 2.0 * i for i in range(16)], post=0.14, post_y=2.38, rail_top=1.060, hand=(0.14, 0.12),
    mid=(0.10, 0.08), mid_z=0.55, curb=(0.15, 0.13), curb_y=2.18,
    crib_x=(13.75, 15.75), crib_r=0.16, sill=(0.30, 0.30))

# ---------------------------------------------------------------- the overlook deck (Update 3's OverlookDeck)
DECK = dict(x=(-2.5, 2.5), y=(0.0, 3.6), top=0.74, board=(0.145, 0.040), legs_x=(-2.3, 0.0, 2.3), legs_y=(0.2, 3.4),
            leg_r=0.085, rail_back_x=(-2.5, -1.5, -0.5, 0.5, 1.5, 2.5), rail_side_y=(0.1, 1.2667, 2.4333, 3.6),
            rail_post=0.09, hand_z=1.75, hand_r=0.040, mid_z=1.30, mid_r=0.030, steps_x=(-0.60, 0.60),
            bench=dict(c=(-1.2, 0.9), len=1.8, depth=0.40, seat=1.18), scope=dict(c=(1.4, 3.2), z=1.95))

# ---------------------------------------------------------------- the windfall (FallenTree, LogCut): a dead spruce that fell
# downhill across the road; Update 3's FBX of these two are not in the copy here - rebuilt from the README (S4: "a spruce
# fallen across the road, sawn straight at both edges: fresh pale cuts, sawdust, the cut piece dragged to the verge") and
# the Windfall preview, on Update 3's pivots: FallenTree's x axis runs across the road (root at the pivot, uphill), the
# road crosses it at x 13.0 .. 19.0; LogCut lies on the far verge along the road (its x along the road).
TREE = dict(root_x=0.30, cut0=12.80, cut1=19.20, tip=31.0, r_base=0.27, r_cut0=0.215, r_cut1=0.185, kerf=0.008)


# ---------------------------------------------------------------- the map frame (Blender world: Unity (x, y, z) -> (-x, -z, y))
def _qrot(q, v):
    """rotate v by the Unity quaternion q (x, y, z, w)"""
    x, y, z, w = q
    u = np.array([x, y, z], np.float64)
    v = np.asarray(v, np.float64)
    return 2.0 * u.dot(v) * u + (w * w - u.dot(u)) * v + 2.0 * w * np.cross(u, v)


def frame_matrix(p, q):
    """4x4: a prefab's own frame (its FBX after import) -> the Blender map frame, for Update 3's placement p, q"""
    bw = lambda u: np.array([-u[0], -u[2], u[1]])
    ex = bw(_qrot(q, (-1, 0, 0)))
    ey = bw(_qrot(q, (0, 0, -1)))
    ez = bw(_qrot(q, (0, 1, 0)))
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2] = ex, ey, ez
    M[:3, 3] = [-p[0], -p[2], p[1]]
    return M


def map_matrix(name):
    if name == 'EuroPost':
        e = U3['europosts'][0]
        return frame_matrix(e['p'], e['q'])
    e = U3['prefabs'][name][0]
    return frame_matrix(e['p'], e['q'])
