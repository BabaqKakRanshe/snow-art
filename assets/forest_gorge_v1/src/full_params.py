"""NW river gorge along the whole river (593 m line of river_nw_line.json + run-out at both ends), Unity coordinates.

Ground: the map export (source/world_sync/forest/map/ground.r16, 2026-10-28 20:03) minus the local agent's NW gorge delta
= the original ground; the new ground is the stepped gorge profile of the Bridge30 concept, carried along the line with the
water level of the package's river (26.8 m at the spring down to 7.92 m from ~105 m on). Writes:
  data/H_new.npy (full map grid), data/params.npz, data/line.npz,
  unity/ground_delta.f32 + ground_delta.json (export_ground.py format, base = the map export's ground.r16),
  unity/gorge_mask.u8 + data/mask.json, data/creek.json (creek + cut lines for ForestStreams.json).
Profile per side (u = distance from the line): bed W-0.9 | tier-0 face f0 -> ledge z1 | tier-1 face f1 -> ledge z2 |
tier-2 face f2 -> rim zr | blend to the original ground. Ramps sit 0.5-1.0 m behind each face, inside the rock blocks.
"""
import json, os
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from scipy.ndimage import binary_dilation, gaussian_filter, map_coordinates, minimum_filter

D = os.path.dirname(os.path.abspath(__file__))
UP = '/mnt/user-data/uploads/snow'
X0, Z0, ST, N = -600.0, -1200.0, 0.5859375, 3073
OX, OZ = -331.33, 331.64                      # the concept's scene origin (bridge_under.npz is in that frame)
BRIDGE = np.array([-331.33, 331.64])
T_START, T_END = -8.0, 600.0                   # gorge from just above the line start to past the map edge
FADE_IN = (-8.0, 14.0)


def smoothstep(a, b, x):
    x = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1)
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- ground
G = np.load(os.path.join(D, '..', 'gorge', 'data', 'ground_map.npy')).astype(np.float64)       # current (map export)
O = np.load(os.path.join(D, 'data', 'ground_orig.npy')).astype(np.float64)                      # before the NW gorge


def sample(H, x, z):
    fx = (np.asarray(x, float) - X0) / ST; fz = (np.asarray(z, float) - Z0) / ST
    j = np.clip(np.floor(fx).astype(int), 0, N - 2); i = np.clip(np.floor(fz).astype(int), 0, N - 2)
    a = np.clip(fz - i, 0, 1); b = np.clip(fx - j, 0, 1)
    return H[i, j] * (1 - a) * (1 - b) + H[i + 1, j] * a * (1 - b) + H[i, j + 1] * (1 - a) * b + H[i + 1, j + 1] * a * b


def on_map(x, z):
    return (x >= X0) & (x <= X0 + (N - 1) * ST) & (z >= Z0) & (z <= Z0 + (N - 1) * ST)


# ---------------------------------------------------------------- the line, dense, extended at both ends
L = json.load(open(UP + '/tools/blender_context/workshop/river_nw_line.json', encoding='utf-8'))
P = np.array(L['points'], float).reshape(-1, 2)
seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
LEN = seg[-1]
d0 = (P[1] - P[0]) / np.linalg.norm(P[1] - P[0]); d1 = (P[-1] - P[-2]) / np.linalg.norm(P[-1] - P[-2])
TD = np.arange(T_START - 12, T_END + 12 + 1e-6, 0.25)
XYD = np.stack([np.interp(TD, seg, P[:, 0]), np.interp(TD, seg, P[:, 1])], -1)
lo, hi = TD < 0, TD > LEN
XYD[lo] = P[0] + d0 * TD[lo, None]
XYD[hi] = P[-1] + d1 * (TD[hi, None] - LEN)
TAN = np.gradient(XYD, axis=0)
k = np.ones(41) / 41.0                                                   # 10 m smoothing of the direction
TAN = np.stack([np.convolve(np.pad(TAN[:, c], 20, mode='edge'), k, mode='valid') for c in range(2)], -1)
TAN /= np.linalg.norm(TAN, axis=1, keepdims=True)
NOR = np.stack([-TAN[:, 1], TAN[:, 0]], -1)                              # left looking downstream (+t)
KD = cKDTree(XYD)


def to_ts(x, z):
    p = np.stack([np.ravel(x), np.ravel(z)], -1)
    _, i = KD.query(p)
    r = p - XYD[i]
    t = TD[i] + np.einsum('ij,ij->i', r, TAN[i])
    s = np.einsum('ij,ij->i', r, NOR[i])
    return t.reshape(np.shape(x)), s.reshape(np.shape(x))


def at(t, s=0.0):
    t = np.asarray(t, float)
    x = np.interp(t, TD, XYD[:, 0]); z = np.interp(t, TD, XYD[:, 1])
    nx = np.interp(t, TD, NOR[:, 0]); nz = np.interp(t, TD, NOR[:, 1])
    return x + nx * s, z + nz * s


# ---------------------------------------------------------------- parameters along t
TP = np.arange(T_START - 10, T_END + 10.01, 0.5)


def wave(seed, lams=(61.0, 33.0, 17.0), amps=(0.55, 0.3, 0.15)):
    rng = np.random.default_rng(seed)
    return sum(a * np.sin(2 * np.pi * TP / l + rng.uniform(0, 2 * np.pi)) for l, a in zip(lams, amps))


def water_level():
    """the package's river level along the line (median of its faces within 2.5 m), monotone down the stream"""
    W = json.load(open(os.path.join(D, 'data', 'water_full.json')))[0]
    V = np.array(W['v']); F = W['f']
    C = np.array([V[f].mean(0) for f in F])
    m = (C[:, 0] > -620) & (C[:, 0] < -120) & (C[:, 2] > 100) & (C[:, 2] < 620)
    C = C[m]
    t, s = to_ts(C[:, 0], C[:, 2])
    ok = np.abs(s) < 2.5
    t, y = t[ok], C[ok, 1]
    lev = np.full(len(TP), np.nan)
    for k_, tt in enumerate(TP):
        mm = np.abs(t - tt) < 1.5
        if mm.any():
            lev[k_] = np.median(y[mm])
    good = np.isfinite(lev)
    lev = np.interp(TP, TP[good], lev[good])
    lev = np.minimum.accumulate(lev)                                       # never rises downstream
    kk = np.ones(9) / 9.0
    lev = np.convolve(np.pad(lev, 4, mode='edge'), kk, mode='valid')
    return np.maximum(lev, 7.92)


WL = water_level()


def rim_height(side):
    vals = []
    for u in (22.0, 23.5, 25.0, 26.5):
        x, z = at(TP, side * u)
        vals.append(np.where(on_map(x, z), sample(O, x, z), np.nan))
    h = np.nanmean(np.stack(vals), 0)
    ok = np.isfinite(h)
    h = np.interp(TP, TP[ok], h[ok])
    kk = np.ones(31) / 31.0
    return np.convolve(np.pad(h, 15, mode='edge'), kk, mode='valid')


TB = float(to_ts(np.array([BRIDGE[0]]), np.array([BRIDGE[1]]))[0][0])
SHORT = dict(lams=(47.0, 21.0, 9.0), amps=(0.45, 0.35, 0.2))


def side_params(side):
    sd = 10 if side > 0 else 20
    P_ = {}
    steep = smoothstep(95.0, 70.0, TP)                                    # 1 in the cascade stretch above ~80 m
    P_['f0'] = (4.3 + 0.9 * wave(sd + 1)) * (1 - steep) + (3.0 + 0.4 * wave(sd + 11)) * steep
    P_['d0'] = 2.6 + 0.3 * wave(sd + 3)
    P_['d1'] = 2.6 + 0.3 * wave(sd + 5)
    P_['d2'] = 2.7 + 0.3 * wave(sd + 7)
    P_['zr'] = rim_height(side)
    P_['W'] = WL.copy()
    Hw = np.maximum(P_['zr'] - WL, 1.5)
    f1 = 0.33 + 0.10 * wave(sd + 2, **SHORT)
    f2 = 0.67 + 0.08 * wave(sd + 8, **SHORT)
    P_['z1'] = WL + Hw * f1
    P_['z2'] = WL + Hw * f2
    scale = np.clip(Hw / 9.0, 0.25, 1.0)                                  # low walls: narrow ledges
    P_['lw1'] = np.maximum((1.7 + 1.7 * wave(sd + 4, **SHORT)) * scale, 0.15)
    P_['lw2'] = np.maximum((1.4 + 1.6 * wave(sd + 6, **SHORT)) * scale, 0.15)
    # Bridge30: the bent in the river (posts 7.8-7.9) stands on a shelf, the other bent (posts 12.07-12.25) on ledge 1
    wb = 1.0 - smoothstep(6.0, 14.0, np.abs(TP - TB))
    fix = dict(f0=4.9, z1=12.25, d0=1.3, lw1=3.5) if side > 0 else dict(f0=4.6, z1=12.0, d0=2.4, lw1=1.0)
    for kk_, v in fix.items():
        P_[kk_] = P_[kk_] * (1 - wb) + v * wb
    P_['z2'] = np.maximum(P_['z2'], P_['z1'] + 1.2)
    P_['f1'] = P_['f0'] + P_['d0'] + P_['lw1']
    P_['f2'] = P_['f1'] + P_['d1'] + P_['lw2']
    P_['top'] = P_['f2'] + P_['d2']
    return P_


PL, PR = side_params(+1), side_params(-1)


def param(P_, key, t):
    return np.interp(t, TP, P_[key])


# ---------------------------------------------------------------- profile
def profile(t, s, hold):
    z = np.empty_like(s)
    for side, P_ in ((1, PL), (-1, PR)):
        m = (s >= 0) if side > 0 else (s < 0)
        if not m.any():
            continue
        tt, u, ho = t[m], np.abs(s[m]), hold[m]
        g = {k_: param(P_, k_, tt) for k_ in ('f0', 'z1', 'f1', 'z2', 'f2', 'zr', 'top', 'W')}
        bed = g['W'] - 0.9
        zz = np.full_like(u, 0.0) + bed
        zz = np.where(u >= g['f0'] + 0.5, bed + (g['z1'] - bed) * smoothstep(g['f0'] + 0.5, g['f0'] + 1.0, u), zz)
        zz = np.where(u >= g['f1'] + 0.5, g['z1'] + (g['z2'] - g['z1']) * smoothstep(g['f1'] + 0.5, g['f1'] + 1.0, u), zz)
        zz = np.where(u >= g['f2'] + 0.5, g['z2'] + (g['zr'] - g['z2']) * smoothstep(g['f2'] + 0.5, g['f2'] + 1.0, u), zz)
        ub = np.maximum(g['top'] + 1.5, 19.5)
        w = smoothstep(ub, ub + 6.0, u)
        zz = zz * (1 - w) + ho * w
        # the gorge starts below the spring: faded in over FADE_IN, and stops at T_END
        gs = smoothstep(FADE_IN[0], FADE_IN[1], tt) * smoothstep(T_END + 8, T_END, tt)
        zz = ho + (zz - ho) * gs
        z[m] = zz
    return z


def bridge_clamp(x, z, h, hold):
    B = np.load(os.path.join(D, '..', 'gorge', 'data', 'bridge_under.npz'))
    under, bx0, by0, c = B['under'], float(B['x0']) + OX, float(B['y0']) + OZ, float(B['cell'])
    ud = minimum_filter(under, size=5, mode='constant', cval=np.inf)
    j = np.floor((x - bx0) / c).astype(int); i = np.floor((z - by0) / c).astype(int)
    ok = (i >= 0) & (i < ud.shape[0]) & (j >= 0) & (j < ud.shape[1])
    lim = np.full_like(h, np.inf)
    lim[ok] = ud[i[ok], j[ok]] - 0.25
    lim = np.maximum(lim, hold)
    return np.minimum(h, lim)


# ---------------------------------------------------------------- the old road layers (tile 0_2 splat, current)
SPL = np.load(os.path.join(D, 'data', 'tile_splat.npy')).astype(np.float64) / 255.0        # rows = z (bottom-up)
ROAD = SPL[..., [2, 3, 5, 6, 7]].sum(-1)


def road_at(x, z):
    j = np.clip(((np.asarray(x) + 600.0) / (600.0 / 1024)).astype(int), 0, 1023)
    i = np.clip(((np.asarray(z) - 0.0) / (600.0 / 1024)).astype(int), 0, 1023)
    return ROAD[i, j]


def main():
    os.makedirs(os.path.join(D, 'unity'), exist_ok=True)
    # corridor box (the line +- 60 m), on the map grid
    xs, zs = XYD[:, 0], XYD[:, 1]
    bx0, bx1 = xs.min() - 60, xs.max() + 60
    bz0, bz1 = zs.min() - 60, zs.max() + 60
    i0, i1 = int(np.clip((bx0 - X0) / ST, 0, N - 1)), int(np.clip((bx1 - X0) / ST, 0, N - 1))
    j0, j1 = int(np.clip((bz0 - Z0) / ST, 0, N - 1)), int(np.clip((bz1 - Z0) / ST, 0, N - 1))
    gx = X0 + np.arange(i0, i1 + 1) * ST; gz = Z0 + np.arange(j0, j1 + 1) * ST
    GX, GZ = np.meshgrid(gx, gz)
    t, s = to_ts(GX, GZ)
    HO = O[j0:j1 + 1, i0:i1 + 1]
    inside_t = (t > T_START - 12) & (t < T_END + 12)
    Hn = np.where(inside_t, profile(t, s, HO), HO)
    Hn = bridge_clamp(GX, GZ, Hn, HO)
    # the road approaches at Bridge30 keep their ground
    rk = (road_at(GX, GZ) > 0.08) & (np.abs(s) > 12.0)
    wroad = np.clip(gaussian_filter(binary_dilation(rk, iterations=3).astype(np.float64), 1.5) * 1.6, 0, 1)
    Hn = Hn * (1 - wroad) + HO * wroad
    H_new = O.copy()                                                       # outside the corridor: the original ground
    H_new[j0:j1 + 1, i0:i1 + 1] = Hn
    np.save(os.path.join(D, 'data', 'H_new.npy'), H_new.astype(np.float32))
    np.savez(os.path.join(D, 'data', 'line.npz'), TD=TD, XYD=XYD, TAN=TAN, NOR=NOR, TB=TB)
    np.savez(os.path.join(D, 'data', 'params.npz'), TP=TP, **{f'L_{k_}': v for k_, v in PL.items()}, **{f'R_{k_}': v for k_, v in PR.items()})

    # ------------------------------------------------ ground delta against the map export (export_ground.py format)
    delta = (H_new - G).astype(np.float32)
    delta[np.abs(delta) < 0.005] = 0
    delta.tofile(os.path.join(D, 'unity', 'ground_delta.f32'))
    zz_, xx_ = np.nonzero(delta)
    info = {'nx': N, 'nz': N, 'x0': X0, 'z0': Z0, 'step': ST, 'file': 'ground_delta.f32',
            'blend': 'cloud: forest_gorge_v1 full_params.py (no .blend)', 'changed': int(len(zz_)),
            'base': 'F:/ClaudeGames/snow/source/world_sync/forest/map/ground.r16',
            'hmin': -58.71427536010742, 'hmax': 50.406150817871094,
            'raised_max': float(delta.max()), 'lowered_max': float(-delta.min()),
            'box': [float(X0 + xx_.min() * ST), float(Z0 + zz_.min() * ST), float(X0 + xx_.max() * ST), float(Z0 + zz_.max() * ST)]}
    json.dump(info, open(os.path.join(D, 'unity', 'ground_delta.json'), 'w', encoding='utf-8'), indent=1)

    # ------------------------------------------------ mask: 3 = river floor, 1 = walls and ledges, 2 = rim band
    u = np.abs(s)
    top = np.where(s >= 0, param(PL, 'top', t), param(PR, 'top', t))
    f0 = np.where(s >= 0, param(PL, 'f0', t), param(PR, 'f0', t))
    on = (t > FADE_IN[0] + 4) & (t < T_END) & on_map(GX, GZ)
    mask = np.zeros(t.shape, np.uint8)
    mask[on & (u < top + 9.0)] = 2
    mask[on & (u < top + 0.8)] = 1
    mask[on & (u < f0 + 0.3)] = 3
    mask[wroad > 0.5] = np.where(mask[wroad > 0.5] == 2, 2, 0)            # never on the roads
    mask.tofile(os.path.join(D, 'unity', 'gorge_mask.u8'))
    json.dump({'file': 'gorge_mask.u8', 'i0': i0, 'j0': j0, 'nx': int(i1 - i0 + 1), 'nz': int(j1 - j0 + 1),
               'x0': X0, 'z0': Z0, 'step': ST}, open(os.path.join(D, 'data', 'mask.json'), 'w'), indent=1)

    # ------------------------------------------------ creek (ForestStreams.json): middle of the floor, its width, kinds
    ts_ = np.arange(-4.0, min(T_END, LEN + 6.0) + 1e-6, 2.0)
    pts, widths, beds, kinds = [], [], [], []
    rng = np.random.default_rng(28)
    riffles = set()
    tt = 120.0
    while tt < LEN:
        tt += rng.uniform(55, 95)
        L_ = rng.uniform(5, 9)
        riffles.update(np.round(np.arange(tt, tt + L_, 2.0)).astype(int).tolist())
    for t_ in ts_:
        fl, fr = param(PL, 'f0', t_), param(PR, 'f0', t_)
        c = (fl - fr) / 2.0
        x, z = at(t_, c)
        if not on_map(x, z):
            continue
        y = float(np.interp(t_, TP, WL))
        slope = float((np.interp(t_ - 2, TP, WL) - np.interp(t_ + 2, TP, WL)) / 4.0)
        w_ = fl + fr + 0.5
        pts += [round(float(x), 3), round(float(z), 3), round(y, 3)]
        widths.append(round(float(w_), 2))
        beds.append(round(y - 0.9, 3))
        if slope > 0.12:
            kinds.append('step' if int(t_) % 8 == 0 else 'steppool')
        elif slope > 0.035:
            kinds.append('riffle')
        else:
            kinds.append('riffle' if int(round(t_)) in riffles else 'pool')
    creek = {'name': 'NW_gorge', 'width': 9.0, 'points': pts, 'widths': widths, 'beds': beds, 'kinds': kinds}
    cut_t = np.arange(-6.0, LEN + 0.01, 3.0)
    cut = []
    for t_ in cut_t:
        x, z = at(t_)
        cut += [round(float(x), 2), round(float(z), 2)]
    json.dump({'creek': creek, 'cut': {'name': 'NW_gorge', 'width': 16.0, 'points': cut}}, open(os.path.join(D, 'data', 'creek.json'), 'w'), indent=1)

    # ------------------------------------------------ report
    print('bridge t %.2f, line %.1f m, water %.2f..%.2f' % (TB, LEN, WL.min(), WL.max()))
    print('delta: changed %d, raise %.2f, cut %.2f, box %s' % (info['changed'], info['raised_max'], info['lowered_max'], [round(v) for v in info['box']]))
    print('mask', mask.shape, 'floor', int((mask == 3).sum()), 'walls', int((mask == 1).sum()), 'rim', int((mask == 2).sum()))
    print('creek points', len(pts) // 3, 'kinds', {k_: kinds.count(k_) for k_ in set(kinds)})
    for nm, P_ in (('L', PL), ('R', PR)):
        print(nm, {k_: (round(float(P_[k_].min()), 2), round(float(P_[k_].max()), 2)) for k_ in ('f0', 'z1', 'f1', 'z2', 'f2', 'zr', 'top')})
    for t_ in (-5, 10, 40, 80, 150, 280, 400, 560, 590):
        row = []
        for ss in (-18, -14, -10, -6, -3, 0, 3, 6, 10, 14, 18):
            x, z = at(t_, ss)
            row.append(float(sample(H_new, x, z)))
        print('t %5d W %5.2f | ' % (t_, np.interp(t_, TP, WL)) + ' '.join('%5.1f' % v for v in row))


if __name__ == '__main__':
    main()
