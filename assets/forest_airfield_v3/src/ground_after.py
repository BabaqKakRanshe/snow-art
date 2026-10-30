"""The airfield's ground after the concept (numpy only; used by concept.py and for checks).

Grid: the crop of the World Sync ground in data/ground_crop.npy (rows = Unity z, cols = Unity x), ground_crop.json.
Runway frame (ForestAirfield.json, as built): centre (961.87; -412.55), yaw -6.923; u across (+u east), v along (+v north).
Cross-section (from the axis):
  0..9 m      the slabs (as now), 1 % crossfall
  9..38 m     flat strip under snow, 2 % down outwards (the shoulders 9..13 ploughed, windrows at 13..17)
  38..46 m    on the cut side a shallow swale (0.45 m)
  then 1:4 to the ground, top and toe rounded (r ~ 25 m); fill sides go down at 1:3 from 38 m.
Ends: the flat strip goes on 75 m past the south end (turning pad) and 30 m past the north end, then 1:4.
South pad: the flat goes out to 52 m on the west side at v -395..-322.
Hangar: apron flat at the floor (-15.80) from the gate to the runway (0.5 % fall to the runway), a rounded hill over the
hall (top -6.0, 1:2 near the facade, softer behind, joining the hillside); at the facade's back the earth stays just under
its top and rises to the crest from 4.5 m behind it.
Roads: no change under the road models of ForestRoads.json (D1 at the north-west corner), the change back over 3 m + 2.5 x
its size from them.
"""
import json
import math
import os

import numpy as np
from scipy import ndimage

D = os.path.dirname(os.path.abspath(__file__))
RW = dict(x=961.87, z=-412.55, yaw=-6.923)
_C, _S = math.cos(math.radians(RW['yaw'])), math.sin(math.radians(RW['yaw']))
PAVE_U, PAVE_V0, PAVE_V1 = 9.0, -350.0, 350.0
W_FLAT = 38.0
SWALE = (38.0, 46.0, 0.45)
SLOPE = 4.0          # cuts
SLOPE_FILL = 3.0     # fills (the west embankment of the south half would be 100 m wide at 1:4)
END_S, END_N = -425.0, 380.0
PAD = dict(v0=-395.0, v1=-322.0, w=52.0)
HANGAR = dict(x=982.44, z=-208.59, yaw=-96.92, floor=-15.80, gate_u=44.3, hall=(-21.0, -17.5, 21.0, 0.0),   # hall: U_h, V_h rect (V_h < 0 behind the gate plane)
              top=-6.0, front=1.6, back=3.2, cap=-7.65)    # cap: the earth at the facade's back, 4 cm under its top (-7.61)
REACH = 170.0
WALL = (17.0, 0.567, -7.85, 1.4)    # BunkerHangar's wing walls: |U_h| at the facade, splay per metre out, earth top at the facade, its fall per metre


def to_uv(x, z):
    dx, dz = np.asarray(x, dtype=np.float64) - RW['x'], np.asarray(z, dtype=np.float64) - RW['z']
    return dx * _C - dz * _S, dx * _S + dz * _C


def to_xz(u, v):
    u, v = np.asarray(u, dtype=np.float64), np.asarray(v, dtype=np.float64)
    return RW['x'] + u * _C + v * _S, RW['z'] - u * _S + v * _C


def hangar_frame(x, z):
    c, s = math.cos(math.radians(HANGAR['yaw'])), math.sin(math.radians(HANGAR['yaw']))
    dx, dz = np.asarray(x) - HANGAR['x'], np.asarray(z) - HANGAR['z']
    return dx * c - dz * s, dx * s + dz * c          # U_h (along the facade), V_h (forward, to the runway)


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def rect_dist(U, V, r):
    du = np.maximum(np.maximum(r[0] - U, U - r[2]), 0.0)
    dv = np.maximum(np.maximum(r[1] - V, V - r[3]), 0.0)
    return np.hypot(du, dv)


MAP = '/mnt/user-data/uploads/snow/source/world_sync/forest/map/'
BIG_BOX = (700.0, -1180.0, 1200.0, 300.0)     # the package's region: the grading reaches 170 m off the axis


def load(big=False):
    if big:
        m = json.load(open(MAP + 'map.json', encoding='utf-8'))['ground']
        raw = np.fromfile(MAP + m['file'], dtype='<u2').reshape(m['nz'], m['nx'])
        i0, i1 = int((BIG_BOX[0] - m['x0']) / m['step']), min(m['nx'] - 1, int((BIG_BOX[2] - m['x0']) / m['step']))
        j0, j1 = int((BIG_BOX[1] - m['z0']) / m['step']), min(m['nz'] - 1, int((BIG_BOX[3] - m['z0']) / m['step']))
        h = m['hmin'] + raw[j0:j1 + 1, i0:i1 + 1].astype(np.float64) / 65535.0 * (m['hmax'] - m['hmin'])
        g = {'i0': i0, 'j0': j0, 'x0': m['x0'], 'z0': m['z0'], 'step': m['step']}
        nz, nx = h.shape
        X = g['x0'] + (g['i0'] + np.arange(nx)) * g['step']
        Z = g['z0'] + (g['j0'] + np.arange(nz)) * g['step']
        XX, ZZ = np.meshgrid(X, Z)
        return h, g, XX, ZZ
    h = np.load(os.path.join(D, 'data', 'ground_crop.npy')).astype(np.float64)
    g = json.load(open(os.path.join(D, 'data', 'ground_crop.json')))
    nz, nx = h.shape
    X = g['x0'] + (g['i0'] + np.arange(nx)) * g['step']
    Z = g['z0'] + (g['j0'] + np.arange(nz)) * g['step']
    XX, ZZ = np.meshgrid(X, Z)
    return h, g, XX, ZZ


def sample(h, g, x, z):
    fx = (np.atleast_1d(x) - g['x0']) / g['step'] - g['i0']
    fz = (np.atleast_1d(z) - g['z0']) / g['step'] - g['j0']
    return ndimage.map_coordinates(h, [fz, fx], order=1, mode='nearest')


def profile(h, g):
    """runway axis heights y(v): the built profile over the slabs (smoothed), the end areas at the end grades"""
    vs = np.arange(-800.0, 800.5, 1.0)
    acc = np.zeros(len(vs))
    for o in np.linspace(-6, 6, 5):
        x, z = to_xz(np.full(len(vs), o), vs)
        acc += sample(h, g, x, z)
    y0 = acc / 5.0
    pv = (vs >= PAVE_V0) & (vs <= PAVE_V1)
    yp = ndimage.gaussian_filter1d(y0[pv], 4.0, mode='nearest')
    i0, i1 = int(np.argmax(pv)), int(len(pv) - np.argmax(pv[::-1]) - 1)
    k0 = (yp[25] - yp[0]) / 25.0
    k1 = (yp[-1] - yp[-26]) / 25.0
    y = np.empty(len(vs))
    y[pv] = yp
    y[:i0] = yp[0] + (vs[:i0] - vs[i0]) * k0
    y[i1 + 1:] = yp[-1] + (vs[i1 + 1:] - vs[i1]) * k1
    return vs, y, y0


def compute(big=False, protect_roads=True, facade_cap=True):
    h, g, XX, ZZ = load(big)
    G = h.copy()
    U, V = to_uv(XX, ZZ)
    au = np.abs(U)
    vs, yprof, y0 = profile(h, g)
    Vc = np.clip(V, END_S, END_N)
    yv = np.interp(Vc, vs, yprof)
    # flat half-width: 38 m, the south pad 52 m on the west side
    pad = smoothstep(PAD['v0'] - 15, PAD['v0'], V) * (1 - smoothstep(PAD['v1'], PAD['v1'] + 15, V)) * (U < 0)
    W = W_FLAT + (PAD['w'] - W_FLAT) * pad
    flat = yv - 0.01 * np.minimum(au, PAVE_U) - 0.02 * np.clip(au - PAVE_U, 0.0, None)
    y_edge = yv - 0.01 * PAVE_U - 0.02 * (W - PAVE_U)
    dv = np.maximum(np.maximum(END_S - V, V - END_N), 0.0)
    du_f = np.maximum(au - W, 0.0)
    du_c = np.maximum(au - (W + SWALE[1] - SWALE[0]), 0.0)
    C = y_edge + np.hypot(du_c, dv) / SLOPE
    F = y_edge - np.hypot(du_f, dv) / SLOPE_FILL
    # by the hangar the hillside is kept: a 1:2 cut from the facade line (u 39.5) instead of the 1:4 corridor slope
    hb = (1 - smoothstep(22.0, 45.0, np.abs(V - 200.0))) * (U > 0)
    C = (1 - hb) * C + hb * (y_edge + np.maximum(au - 39.5, 0.0) / 2.0)
    inside = (au <= W) & (dv <= 0)
    N = np.where(inside, flat, np.clip(G, F, C))
    # the swale at the foot of cuts
    cut = (G > y_edge + 0.3) & (dv <= 0) & ~inside & (hb < 0.3)
    sw = np.clip((au - SWALE[0]) / (SWALE[1] - SWALE[0]), 0, 1)
    N = np.where(cut & (au > SWALE[0]) & (au < SWALE[1]), N - SWALE[2] * np.sin(sw * math.pi) ** 2, N)
    zone = (au < REACH) & (dv < REACH * 0.7)
    N = np.where(zone, N, G)
    # round the breaks: blur the change outside the flat strip
    step = g['step']
    delta = N - G
    b1 = ndimage.gaussian_filter(delta, 4.0 / step)
    b2 = ndimage.gaussian_filter(delta, 9.0 / step)
    w = smoothstep(W - 1.0, W + 6.0, au) * (1 - smoothstep(0.0, 0.5, -dv))      # 0 inside the strip
    w = np.maximum(w, smoothstep(0.0, 8.0, dv))
    wide = smoothstep(W + 10.0, W + 30.0, au) + smoothstep(10.0, 30.0, dv)
    wide = np.clip(wide, 0, 1)
    delta = (1 - w) * delta + w * ((1 - wide) * b1 + wide * b2)
    N = G + delta

    # the hangar: apron at the floor from the gate to the runway, hill over the hall
    Uh, Vh = hangar_frame(XX, ZZ)
    gate_vh = 0.0                                  # the gate plane (u 44.3) is V_h ~ +0.7; facade front at V_h ~ 5.4 (u 39)
    ap_len = HANGAR['gate_u'] - PAVE_U             # out to the slabs' edge
    in_ap = (np.abs(Uh) <= 21.0) & (Vh >= -1.0) & (Vh <= ap_len + 2)
    ap_y = HANGAR['floor'] - 0.005 * np.clip(Vh, 0, None)
    ap_w = (1 - smoothstep(21.0, 30.0, np.abs(Uh))) * (1 - smoothstep(ap_len + 2, ap_len + 6, Vh)) * smoothstep(-6.0, -1.0, Vh)
    N = np.where(ap_w > 0, (1 - ap_w) * N + ap_w * np.where(in_ap, ap_y, N), N)
    # hill: top over the hall, rounded crest, 1:1.6 at the front corners, 1:3.2 behind; merges with the hillside (max)
    hall = HANGAR['hall']
    dh = rect_dist(Uh, Vh, hall)
    crest = HANGAR['top'] - 0.9 * (np.clip(np.abs(Uh) / 21.0, 0, 1) ** 2)
    slope = np.where(Vh > -8.0, HANGAR['front'], HANGAR['back'])
    hill = crest - dh / slope - 0.02 * dh ** 2
    # the earth meets the facade's back just under its top and rises to the crest from 4.5 m behind it (1:3.3): the
    # Terrain holes at the gate (ForestAirfield.json, to V_h -1.8) then cut no pit that shows over the parapet
    if facade_cap:
        cap = HANGAR['cap'] + 0.3 * np.maximum(-Vh - 4.5, 0.0) + 0.3 * np.maximum(np.abs(Uh) - 22.0, 0.0)
        hill = np.minimum(hill, cap)
    # in front of the facade: BunkerHangar's own wing walls (facade +-17 m, splayed to +-20.4 m at 6 m out, tops falling
    # from -7.6 to the floor) hold the earth; the bank sits behind them, never over their tops; the apron between them
    wallM = np.where(Vh <= 6.0, WALL[0] + WALL[1] * np.clip(Vh, 0, None), 20.4 + (Vh - 6.0) * 8.0)
    wall_top = WALL[2] - WALL[3] * np.clip(Vh, 0, 6.0) - np.maximum(Vh - 6.0, 0) * 3.0
    # the step from the hill down to the apron is made behind the facade plane (V_h < -0.9, the wall is 0.1..0.7), so the
    # steep ground faces stay hidden behind the concrete
    FACE = -0.9
    front = (Vh > FACE) & (np.abs(Uh) > wallM + 0.9)                  # the step behind the wing wall, under its top
    bank_e = np.minimum(hill, wall_top - 0.25 + np.maximum(np.abs(Uh) - wallM - 0.9, 0) * 0.8)
    hill = np.where(Vh > FACE, np.where(front, bank_e, -1e9), hill)
    N = np.maximum(N, np.where(dh < 60, hill, -1e9))
    # keep the apron clear of the hill
    N = np.where(in_ap & (np.abs(Uh) < np.minimum(wallM + 0.9, 21.0)) & (Vh > FACE), np.minimum(N, ap_y), N)
    # far out the earthwork fades out (in the forest the slopes get steeper rather than end in a step), and to nothing at the
    # map's east edge (x 1200)
    dv_out = np.maximum(np.maximum(END_S - V, V - END_N), 0.0)
    fade = (1 - smoothstep(110.0, 165.0, au)) * (1 - smoothstep(70.0, 115.0, dv_out)) * (1 - smoothstep(1165.0, 1195.0, XX))
    N = G + (N - G) * fade
    delta = N - G
    if protect_roads:
        delta = road_protect(delta, XX, ZZ, g)
        N = G + delta
    return dict(G=G, N=N, delta=delta, U=U, V=V, XX=XX, ZZ=ZZ, g=g, W=W, vs=vs, y=yprof, y0=y0, Uh=Uh, Vh=Vh)


ROAD_KEEP = 1.0          # m beyond a road's footprint (lane, shoulder, plough berm) where the ground stays as it is


def road_footprint(XX, ZZ, g):
    """cells under the road models of ForestRoads.json (the road builder fitted the ground to them and the road meshes are
    fixed: the airfield's earthwork must not move the ground there): lane half width + shoulder + the wider berm + ROAD_KEEP"""
    roads = json.load(open(os.path.join(D, 'data', 'ForestRoads.json'), encoding='utf-8'))['roads']
    step = g['step']
    x0g, z0g = float(XX[0, 0]), float(ZZ[0, 0])
    nz, nx = XX.shape
    mask = np.zeros((nz, nx), bool)
    for rd in roads:
        P = np.asarray(rd['points'], float).reshape(-1, 3)
        if len(P) < 2:
            continue
        inb = (P[:, 0] > XX.min() - 30) & (P[:, 0] < XX.max() + 30) & (P[:, 1] > ZZ.min() - 30) & (P[:, 1] < ZZ.max() + 30)
        if not inb.any():
            continue
        berm = np.maximum(np.asarray(rd['bermLeft'], float).reshape(-1, 2)[:, 1], np.asarray(rd['bermRight'], float).reshape(-1, 2)[:, 1])
        half = np.asarray(rd['halfs'], float) + float(rd.get('shoulder', 0.6)) + berm + ROAD_KEEP
        for i in range(len(P) - 1):
            if not (inb[i] or inb[i + 1]):
                continue
            a, b = P[i, :2], P[i + 1, :2]
            n = max(1, int(np.ceil(np.linalg.norm(b - a) / 0.4)))
            for t in np.linspace(0.0, 1.0, n + 1):
                q = a + (b - a) * t
                r = half[i] + (half[i + 1] - half[i]) * t
                i0, i1 = max(0, int((q[0] - r - x0g) / step)), min(nx, int((q[0] + r - x0g) / step) + 2)
                j0, j1 = max(0, int((q[1] - r - z0g) / step)), min(nz, int((q[1] + r - z0g) / step) + 2)
                if i0 >= i1 or j0 >= j1:
                    continue
                sx = XX[j0:j1, i0:i1] - q[0]; sz = ZZ[j0:j1, i0:i1] - q[1]
                mask[j0:j1, i0:i1] |= sx * sx + sz * sz <= r * r
    return mask


def road_protect(delta, XX, ZZ, g):
    """no change under the roads; the change comes back over 3 m + 2.5 x its own size from the footprint (about 1:2 at
    most on the side of a deep cut)"""
    mask = road_footprint(XX, ZZ, g)
    if not mask.any():
        return delta
    dist = ndimage.distance_transform_edt(~mask) * g['step']
    L = 3.0 + 2.5 * np.abs(delta)
    w = smoothstep(0.0, 1.0, dist / L)
    return delta * w


if __name__ == '__main__':
    import sys
    r = compute()
    d = r['delta']
    print('delta', d.min(), d.max(), 'changed cells', (np.abs(d) > 0.05).sum())
    vs, y, y0 = r['vs'], r['y'], r['y0']
    for v in (-600, -500, -450, -425, -400, -350, -300, -200, 0, 200, 300, 350, 380, 400, 450, 500):
        i = int(v + 800)
        print(f'v {v:5d} y {y[i]:7.2f}  axis before {y0[i]:7.2f}')
    # cross sections
    from PIL import Image
    h, g = r['G'], r['g']
    us = np.arange(-120, 121, 10.0)
    for v in (-380, -300, -150, 0, 150, 200, 260, 330):
        x, z = to_xz(us, np.full(len(us), float(v)))
        b = sample(r['G'], g, x, z); a = sample(r['N'], g, x, z)
        print(f'v{v:5d} before', ' '.join(f'{q:6.1f}' for q in b))
        print(f'       after ', ' '.join(f'{q:6.1f}' for q in a))
    # hillshade preview
    def shade(H):
        gy, gx = np.gradient(H, g['step'])
        nrm = np.dstack([-gx, -gy, np.ones_like(H)])
        nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
        L = np.array([-0.5, 0.5, 0.7]); L /= np.linalg.norm(L)
        return np.clip(nrm @ L, 0, 1)
    sa, sb = shade(r['N']), shade(r['G'])
    img = np.concatenate([sb, np.ones((sb.shape[0], 8)), sa], 1)
    im = Image.fromarray((img[::-1] * 255).astype(np.uint8))
    im.save(os.path.join(D, 'rend', 'ground_shade.png'))
    np.save(os.path.join(D, 'data', 'ground_after.npy'), r['N'].astype(np.float32))
