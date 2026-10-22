"""The Forest map's far points (the five satellite dishes, the radome, the relay mast, the weather station, the lookout
tower, the pump house, the chapel, the forest cabin, the abandoned campsite) - Update 3's data and the dimensions of the
rebuilt models.  Every prefab is built in its own frame, the frame of its Update 3 FBX after import: x / y / z (z up),
Unity prefab-local = (-x, z, -y).  The placements (Unity p, q xyzw: far_u3_data.json, from Forest_Layout.json) stay as
they are.  The ground under each placement: far_ground.json (flat under all of them: within +-7 cm)."""
import os, json, math
import numpy as np
import base_spec as BS

HERE = os.path.dirname(os.path.abspath(__file__))
U3 = json.load(open(os.path.join(HERE, 'far_u3_data.json')))
GROUND = json.load(open(os.path.join(HERE, 'far_ground.json')))
STAIRS = json.load(open(os.path.join(HERE, 'far_lookout_stairs.json')))      # Update 3's treads and landings (exact)

ROOTS = ['Dish_1', 'Dish_2', 'Dish_3', 'Dish_4', 'Dish_5', 'Radome', 'RelayMast', 'MeteoStation', 'LookoutTower',
         'PumpHouse', 'Chapel', 'Cabin', 'Campsite']


def placements(name):
    return U3['prefabs'].get(name) or U3['scatter'].get(name) or []


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


frame_matrix = BS.frame_matrix


def map_matrix(name, i=0):
    e = placements(name)[i]
    return frame_matrix(e['p'], e['q'])


def local_to_map(name, v, i=0):
    M = map_matrix(name, i)
    return (M @ np.array([v[0], v[1], v[2], 1.0]))[:3]


def u2b(p):
    """Unity prefab-local -> the prefab's own frame"""
    return (-p[0], -p[2], p[1])


# ---------------------------------------------------------------- the dishes (Update 3's: 16 m on 1, 2, 5; 12 m on 3, 4)
# the reflector turns on the elevation axle (along x through (0, 0, axle_z)); its vertex 0.20 behind the axle on its
# axis (0, cos el, sin el); a paraboloid of depth `depth` over radius R (f / D 0.40); the feed's horn at the focus,
# Update 3's beacon 0.73 beyond the focus on the axis (its light and halo stay there)
DISHES = {'Dish_1': dict(size='L', el=38.0, door='IX_CabinetDoor_2'), 'Dish_2': dict(size='L', el=42.0, door='IX_CabinetDoor_3'),
          'Dish_3': dict(size='S', el=45.0, door='IX_CabinetDoor_4'), 'Dish_4': dict(size='S', el=40.0, door='IX_CabinetDoor_5'),
          'Dish_5': dict(size='L', el=36.0, door='IX_CabinetDoor_6')}
DSIZE = {'L': dict(R=8.0, depth=2.5, axle_z=8.0, ped_top=6.4, head=(6.3, 7.1), arms=(6.5, 8.7), ref='Dish_1',
               shaft=(0.0, -0.95, 7.50)),
         'S': dict(R=6.0, depth=1.875, axle_z=6.5, ped_top=4.9, head=(4.8, 5.6), arms=(5.0, 7.2), ref='Dish_3',
               shaft=(0.0, -0.92, 6.00))}
# axle_z: Update 3's elevation axis (the reflector's vertex is 0.20 in front of it); shaft: the rebuilt dish's elevation
# shaft behind the reflector (the yoke's bearings), the same for every elevation of a size
DISH = dict(plinth=2.6, plinth_top=1.2, plinth_bottom=-0.5, ped_r=1.07, head=(1.3, 1.1), arm_x=(1.325, 1.575), arm_y=0.8,
            vertex_back=0.20, shell=0.12, beacon_beyond=0.73, ladder_y=-1.15, ladder_x=0.25,
            pad=(3.3, 5.1, -3.8, -2.6, 0.16), cab=(3.6, 4.8, -3.5, -2.9, 0.16, 1.96), roof=(3.55, 4.85, -3.55, -2.85, 1.96, 2.04),
            door=dict(hinge_x=3.65, x1=4.75, y=-2.885, z=(0.17, 1.87)),
            sign=dict(posts=(2.30, 2.90), y=-3.742, c=(2.60, 1.60), w=1.03, h=0.42),
            lamp=dict(pole=(6.0, -3.6), light=(5.0133, -3.9591, 5.85)))


def dish_geom(name):
    d = DISHES[name]
    s = DSIZE[d['size']]
    el = math.radians(d['el'])
    ax = np.array([0.0, math.cos(el), math.sin(el)])
    axle = np.array([0.0, 0.0, s['axle_z']])
    vtx = axle - ax * DISH['vertex_back']
    f = (2 * s['R']) ** 2 / (16 * s['depth'])
    return dict(axis=ax, axle=axle, vertex=vtx, focal=f, focus=vtx + ax * f, beacon=vtx + ax * (f + DISH['beacon_beyond']),
                R=s['R'], depth=s['depth'], el=d['el'], size=d['size'])


# ---------------------------------------------------------------- the radome (Update 3's: a 16 m tower, the dome on top)
RADOME = dict(foot=3.0, top_c=2.6, bay=4.0, h=16.0, footing=1.3, deck=(16.0, 17.0), deck_half=3.744, dome_c=20.644,
              dome_r=5.2, dome_base=16.95, beacon_base=25.844, beacon_top=26.392, hut=(7.75, 10.25, -2.5, 2.5, 2.6),
              hut_roof=(7.65, 10.35, -2.6, 2.6, 2.6, 2.76), hut_door=(10.28, 0.9, 1.9, 0.1, 2.2), ac=(8.5, 9.5, -2.2, -1.2, 2.7, 3.5),
              ladder_x=-1.5)


def radome_c(z):
    r = RADOME
    return r['foot'] + (r['top_c'] - r['foot']) * max(0.0, min(1.0, z / r['h']))


# ---------------------------------------------------------------- the relay mast (Update 3's: 42 m, a fenced compound, a hut)
RELAY = dict(foot=2.23, h=42.0, bay=3.5, taper=0.0393, footings=2.3, footing=1.3, beacon_top=(42.02, 42.52),
             beacons_mid=21.0, beacon_mid_xy=1.725, drum=dict(z=31.5, x=1.06, r=0.69, depth=0.56),
             panels=dict(z=(39.1, 40.9), r=1.10, w=0.32, d=0.14), hut=(4.75, 7.25, -2.0, 2.0, 2.6),
             hut_roof=(4.65, 7.35, -2.1, 2.1, 2.6, 2.76), hut_door=(7.28, 0.4, 1.4, 0.1, 2.2), ac=(5.5, 6.5, -1.7, -0.7, 2.7, 3.5),
             fence=dict(x=(-6.0, 10.0), y=(-6.0, 6.0), h=2.2, post_top=2.3, gate_y=(-0.85, 0.85)),
             sign=dict(x=-6.072, y=0.0, z=1.5, w=0.80, h=0.22))


def relay_c(z):
    return RELAY['foot'] - RELAY['taper'] * z


# ---------------------------------------------------------------- the weather station (Update 3's enclosure 12 m)
METEO = dict(fence=6.0, fence_h=0.9, picket=0.08, pitch=0.16, gate=(-0.6, 0.6),
             screen=dict(legs=(0.30, 0.25), leg_top=1.2, box=(0.75, 0.60, 1.2, 1.9), roof=(0.85, 0.70, 1.905, 1.955)),
             mast=(3.0, 2.0, 8.0), vane=(2.4, 3.7, 8.0), cups_z=7.6, gauge=(-2.0, 2.5, 1.0, 1.45, 0.095))

# ---------------------------------------------------------------- the lookout tower (Update 3's: 22 m, the cab on top)
LOOKOUT = dict(foot=3.0, top_c=1.70, h=22.0, bays=7, footing=1.3, cab=2.0, wall=1.8, floor=(21.88, 22.0), wall_top=23.0,
               glass=(23.05, 24.05), eaves=24.1, roof=(2.2, 25.2), rod_top=27.0,
               # the stairwell in the cab floor (x0, x1, y0, y1): over the last flight's top treads (their headroom: the
               # floor is 0.88 over the top landing) and the top landing; the ship ladder climbs +y from the landing to
               # the floor at its +y edge (treads x 0.75 .. 1.55); rails round the rest of the well
               well=(-0.15, 1.75, -0.95, 0.30), ladder_x=(0.75, 1.55), ladder_y=(-0.32, -0.12, 0.08), ladder_d=0.24,
               finder=(-0.85, 0.85))


def lookout_c(z):
    L = LOOKOUT
    return L['foot'] + (L['top_c'] - L['foot']) * max(0.0, min(1.0, z / L['h']))


# ---------------------------------------------------------------- the pump house (Update 3's: brick, 4 x 3 m, flat roof)
PUMP = dict(base=(2.15, 1.65, 0.2), wall=(2.0, 1.5, 0.25), top=2.6, roof=(2.15, 1.65, 2.6, 2.76), door=(-0.475, 0.425, 2.2),
            leaf=dict(hinge_x=-0.59, x1=0.29, y=-1.52, z=(0.21, 2.19)), pump=(0.3, 0.9, 0.0, 0.6, 0.25, 0.9),
            pipe=(0.6, 0.3, 4.5, 0.6), box=(-1.55, -1.05, 1.1, 1.3, 1.05, 1.75), sign=(0.9, -1.64, 2.2, 1.04, 0.244))

# ---------------------------------------------------------------- the chapel (Update 3's: plastered nave 5 x 7.5 m)
CHAPEL = dict(out=(2.5, 3.75), inner=(2.0, 3.25), wall_top=3.6, eaves=(3.0, 2.84), ridge=6.8, roof_y=4.25,
              plinth=(2.54, 3.79, -0.6, 0.6), door=(-0.6, 0.6, 2.3), leaf=dict(hinge_x=-0.56, x1=0.59, y=-3.705, z=(0.01, 2.29)),
              windows=[(-1.5, -0.9), (1.3, 1.9)], win_z=(1.5, 2.6), turret=(0.45, -2.85, 6.5, 8.1), spire=(8.1, 9.3),
              cross=(9.3, 10.0), altar=(-0.8, 0.8, 2.4, 3.1, 1.0), cloth=(-0.85, 0.85, 2.35, 3.15, 1.04),
              candles=[(-0.55, 1.22, 1.25), (-0.35, 1.28, 1.31), (0.35, 1.22, 1.25), (0.55, 1.28, 1.31)], candle_y=2.7,
              icon=(-0.5, 0.5, 1.45, 2.75, 3.23), pews_x=((-1.65, -0.35), (0.35, 1.65)), pews_y=(-1.6, -0.6, 0.4, 1.4),
              graves=[(-6.29, -0.82), (-4.30, -0.86), (-2.57, -1.00), (-5.99, 1.60), (-4.21, 1.60), (-2.32, 1.62)],
              sign=(4.1, -4.75, 1.5, 1.63, 0.284))

# ---------------------------------------------------------------- the forest cabin (Update 3's: logs 5 x 4 m)
CABIN = dict(x=2.5, y=2.0, log_r=0.124, course=0.239, courses=15, eaves=(2.45, 3.42), ridge=5.14, roof_x=2.95,
             door=(-1.47, -0.62, 2.05), leaf=dict(hinge_x=-1.47, x1=-0.62, y=-2.0, z=(0.2, 2.05)), floor=(0.18, 0.22),
             window=(-0.675, 0.275, 0.925, 1.575), stove=(1.5, 1.2), chimney_top=5.538, bunk=(-2.4, -0.8, 0.8, 1.6, 0.5),
             table=(0.0, 0.0, 0.75), porch=(-1.2, 1.2, -3.7, -2.1, 0.18), porch_posts=(-1.1, 1.1, -3.6))

# ---------------------------------------------------------------- the abandoned campsite (Update 3's things)
CAMP = dict(tent=(-1.2, 1.2, -0.9, 0.9), fire=(3.0, 1.0, 0.40), pot=(3.3, 1.5), chair=(2.0, -1.0), pack=(1.23, 1.18),
            bottle=(2.5, 1.925), torch=(0.495, -1.655), torch_light=(0.6582, -1.7519, 0.0652))
