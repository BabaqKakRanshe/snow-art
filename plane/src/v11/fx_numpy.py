"""numpy port of the v11 shaders UtilityPlane/Airlight and UtilityPlane/Beam (same maths, same parameters) for the
preview composites and for calibration. All vectors in the Unity world frame (+X right, +Y up, +Z forward)."""
import numpy as np

HALF_PI = np.pi / 2


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def ign(px, py):
    return np.mod(52.9829189 * np.mod(px * 0.06711056 + py * 0.00583715, 1.0), 1.0)


def fog_vis(viewz, fog_density, own):
    if fog_density is None:
        return own
    return np.exp(-(fog_density * np.maximum(viewz, 0.0)) ** 2)


# ---------------------------------------------------------------- Airlight
def pattern(d, P):
    az = np.degrees(np.arctan2(d[..., 0], d[..., 2]))
    el = np.degrees(np.arcsin(np.clip(d[..., 1], -1, 1)))
    p = 1 - smoothstep(P['sector'] - P['soft'], P['sector'] + P['soft'], np.abs(az))
    if P['elev'] > 0:
        p = p * np.maximum(np.cos(np.radians(el)), 1e-4) ** P['elev']
    if P['beam'] > 0:
        th = np.degrees(np.arccos(np.clip(d[..., 2], -1, 1)))
        p = p * np.exp(-0.5 * th * th / P['beam'] ** 2)
    if P['fan'] > 0:
        p = p * np.exp(-0.5 * az * az / P['fan'] ** 2)
        p = p * smoothstep(P['el_lo'] - 3, P['el_lo'] + 3, el) * (1 - smoothstep(P['el_hi'] - 3, P['el_hi'] + 3, el))
    return np.maximum(p, P['floor'])


def hg_int(theta, g):
    a = 1 - g
    return (1 - g * g) / (4 * np.pi) * theta / (a * a * np.sqrt(a * a + g * theta * theta))


def airlight(ro, rd, T, cam_fwd, pix_ang, c, Rpat, P, I, color, sigma, fog_density=None, px=None, py=None, lamp_vis=1.0):
    """rd: (H,W,3) unit rays; T: (H,W) scene distance along the ray; Rpat: 3x3, columns = pattern frame axes (world)."""
    toL = c - ro
    dist = max(np.linalg.norm(toL), 1e-4)
    R = np.clip(dist * P['radius_scale'], P['radius_min'], P['radius_max'])
    tc = rd @ toL
    h2 = np.maximum(dist * dist - tc * tc, 0)
    h = np.sqrt(h2)
    hs = np.sqrt(h2 + P['core_size'] ** 2)
    to_obj = lambda v: v @ Rpat                       # world dir -> pattern frame (Rpat orthonormal)
    dcam = to_obj(-toL / dist)
    pcam = pattern(dcam[None, None, :], P)[0, 0]
    lens_ang = P['core_size'] / dist
    core_ang = max(lens_ang, P['min_px'] * pix_ang)
    ang = np.arctan2(h, np.maximum(tc, 1e-4))
    core = 1 - smoothstep(core_ang * 0.5, core_ang, ang)
    core = core * max(min(lens_ang ** 2 / core_ang ** 2, 1.0), 0.2)
    core = core * (T >= tc - 2 * P['core_size']) * (tc >= 0)
    core_rad = P['core_gain'] * pcam * core
    t1 = np.minimum(T, tc + 4 * R)
    th0 = np.arctan(-tc / hs) + HALF_PI
    th1 = np.maximum(np.arctan((t1 - tc) / hs) + HALF_PI, th0)
    fwd = (hg_int(th1, P['g']) - hg_int(th0, P['g'])) * lamp_vis
    iso = (th1 - th0) / (4 * np.pi)
    pside_dir = ro + rd * tc[..., None] - c
    n = np.linalg.norm(pside_dir, axis=-1, keepdims=True)
    pside_dir = np.where(n > 1e-3, pside_dir / np.maximum(n, 1e-6), -toL / dist)
    pside = pattern(to_obj(pside_dir), P)
    win = 1 - smoothstep(0.35 * R, R, h)
    halo = sigma / hs * (P['forward'] * fwd * pcam + (1 - P['forward']) * P['iso'] * iso * pside) * P['halo'] * win
    vis = fog_vis(toL @ cam_fwd, fog_density, np.exp(-sigma * dist))
    halo_rad = I * halo * vis
    halo_rad = halo_rad / (1 + P.get('halo_clip', 0.6) * halo_rad)
    out = (I * core_rad * vis + halo_rad)[..., None] * np.asarray(color)[None, None, :]
    if px is not None:
        out = out * (1 + (ign(px, py) - 0.5) * 0.06)[..., None]
    return out


GLOW_DEFAULTS = dict(core_size=0.035, core_gain=2.0, min_px=1.5, halo=1.0, iso=1.0, g=0.85, forward=0.6, sector=180, soft=3,
                     elev=0.0, beam=0.0, fan=0.0, el_lo=-90, el_hi=90, floor=0.05, radius_scale=0.5, radius_min=2.0,
                     radius_max=60.0)


# ---------------------------------------------------------------- Beam
def hash3(p):
    p = np.mod(p * 0.1031, 1.0)
    p = p + (p * (p[..., ::-1] + 31.32)).sum(-1, keepdims=True)    # dot(p, p.zyx + 31.32)
    return np.mod((p[..., 0] + p[..., 1]) * p[..., 2], 1.0)


def noise3(x):
    i = np.floor(x)
    f = x - i
    f = f * f * (3 - 2 * f)
    def H(o):
        return hash3(i + np.array(o, float))
    n000, n100, n010, n110 = H((0, 0, 0)), H((1, 0, 0)), H((0, 1, 0)), H((1, 1, 0))
    n001, n101, n011, n111 = H((0, 0, 1)), H((1, 0, 1)), H((0, 1, 1)), H((1, 1, 1))
    lx = lambda a, b: a + (b - a) * f[..., 0]
    ly = lambda a, b: a + (b - a) * f[..., 1]
    return ly(lx(n000, n100), lx(n010, n110)) + (ly(lx(n001, n101), lx(n011, n111)) - ly(lx(n000, n100), lx(n010, n110))) * f[..., 2]


def win(x, lo, hi, soft):
    return smoothstep(lo - soft, lo + soft, x) * (1 - smoothstep(hi - soft, hi + soft, x))


def profile(d, B):
    z = np.maximum(d[..., 2], 1e-4)
    ax = np.degrees(np.arctan2(d[..., 0], z))
    ay = np.degrees(np.arctan2(d[..., 1], z))
    edge = (smoothstep(B['x'][0], B['x'][0] + 8, ax) * (1 - smoothstep(B['x'][1] - 8, B['x'][1], ax)) *
            smoothstep(B['y'][0], B['y'][0] + 8, ay) * (1 - smoothstep(B['y'][1] - 8, B['y'][1], ay)))
    if B.get('core', 0) > 0:
        th = np.degrees(np.arccos(np.clip(d[..., 2], -1, 1)))
        return (np.exp(-0.5 * th * th / B['core'] ** 2) + B.get('skirt', 0.0)) * edge
    up, hz = B['up_os'], B['hz_os']
    hx = np.cross(up, hz)
    el = np.degrees(np.arcsin(np.clip(d @ up, -1, 1)))
    az = np.degrees(np.arctan2(d @ hx, d @ hz))
    return np.exp(-0.5 * az * az / B['fan'] ** 2) * win(el, B['el_lo'], B['el_hi'], 3.0) * edge


def beam(ro, rd, T, cam_fwd, apex, Rl, B, I, color, sigma, fog_density=None, px=None, py=None, time=0.0, steps=12):
    """Rl: 3x3 light rotation (columns = light axes in world)."""
    o = (ro - apex) @ Rl                     # camera in light space
    d = rd @ Rl
    t0 = np.zeros(T.shape)
    t1 = T.copy()
    def clip(n, c):
        nonlocal t0, t1
        n = np.asarray(n, float)
        nd = d @ n
        f0 = o @ n + c
        par = np.abs(nd) < 1e-6
        t = -f0 / np.where(par, 1.0, nd)
        t0 = np.where(~par & (nd > 0), np.maximum(t0, t), t0)
        t1 = np.where(~par & (nd < 0), np.minimum(t1, t), t1)
        t1 = np.where(par & (f0 < 0), -1.0, t1)
    tn = lambda a: np.tan(np.radians(a))
    clip((1, 0, -tn(B['x'][0])), 0.0)
    clip((-1, 0, tn(B['x'][1])), 0.0)
    clip((0, 1, -tn(B['y'][0])), 0.0)
    clip((0, -1, tn(B['y'][1])), 0.0)
    clip((0, 0, -1), B['length'])
    valid = t1 > t0
    tc = -(d @ o)
    hh = np.linalg.norm(o + d * tc[..., None], axis=-1)
    hs = np.maximum(hh, B.get('hmin', 0.25))
    phi0 = np.arctan((t0 - tc) / hs)
    phi1 = np.arctan((t1 - tc) / hs)
    jit = ign(px, py) if px is not None else 0.5
    g = B.get('g', 0.55)
    hgn = (1 - g * g) / (4 * np.pi)
    wind = np.asarray(B.get('wind', (0.6, -0.9, 0.3)))
    drift = wind * time
    inv = 1.0 / max(B.get('noise_scale', 2.5), 0.1)
    cosf = np.maximum(rd @ cam_fwd, 1e-4)
    acc = np.zeros(T.shape)
    for k in range(steps):
        phi = phi0 + (phi1 - phi0) * (k + jit) / steps
        t = tc + hs * np.tan(phi)
        p = o + d * t[..., None]
        r = np.maximum(np.linalg.norm(p, axis=-1), 1e-3)
        prof = profile(p / r[..., None], B) * (1 - smoothstep(0.7 * B['length'], B['length'], r))
        cth = -np.sin(phi)
        hg = hgn * np.maximum(1 + g * g - 2 * g * cth, 1e-4) ** -1.5
        pw = ro + rd * t[..., None]
        nn = noise3((pw - drift) * inv) * 0.65 + noise3((pw - drift * 1.7) * (inv * 2.7)) * 0.35
        dens = np.maximum(1 + B.get('noise', 0.6) * (nn - 0.5) * 2, 0)
        vis = fog_vis(t * cosf, fog_density, np.exp(-sigma * (t + r)))
        acc += prof * hg * dens * vis
    L = sigma * I / hs * (phi1 - phi0) * acc / steps * B.get('gain', 1.0)
    L = np.where(valid, L, 0.0)
    out = L[..., None] * np.asarray(color)[None, None, :]
    if px is not None:
        out = out * (1 + (jit - 0.5) * 0.06)[..., None]
    return out
