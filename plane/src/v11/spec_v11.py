"""Utility Plane v11 lighting: single source of truth.

Frames
  plane frame = Unity prefab space: +X right (starboard), +Y up, +Z forward (nose). The left wing tip is at x = -7.07.
  az = angle from +Z towards +X (right = positive), el = elevation (up = positive), degrees.
  light frame = Quaternion.LookRotation(fwd, up) of each light: +Z beam axis, +X = cross(up, Z), +Y = cross(Z, X).
  URP spot cookie: u = 0.5 + 0.5 * (x/z) / tan(outer/2), v = 0.5 + 0.5 * (y/z) / tan(outer/2) (v up; PNG row 0 = top).

Emission functions E(dir) in 0..1 describe the lamp + lens + housing. They drive the cookies (light shape on surfaces) and,
through the glow / beam parameters, the in-air effects. Intensities are Unity URP units (linear intensity, inverse
square falloff): E_surface = I * cookie * spot * window(range) / d^2.
"""
import numpy as np

D2R = np.pi / 180.0


def dirv(az, el):
    a, e = np.radians(az), np.radians(el)
    return np.array([np.sin(a) * np.cos(e), np.sin(e), np.cos(a) * np.cos(e)])


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def look_rotation(fwd, up=(0, 1, 0)):
    """Columns = light X, Y, Z axes in the parent (plane) frame, exactly as Unity's Quaternion.LookRotation."""
    z = unit(fwd)
    x = np.cross(np.asarray(up, float), z)
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)
    return np.stack([x, y, z], 1)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def window(x, lo, hi, soft):
    return smoothstep(lo - soft, lo + soft, x) * (1 - smoothstep(hi - soft, hi + soft, x))


def deg(x):
    return np.degrees(x)


# ---------------------------------------------------------------- emission functions
# d: (..., 3) directions in the PLANE frame;  l: same directions in the LIGHT frame
def _mount(el):
    """lamp base / mounting below the lens: nothing straight down"""
    return smoothstep(-89.0, -78.0, el)


def em_nav(d, l, side):                       # side -1 = left (red), +1 = right (green)
    az = deg(np.arctan2(side * d[..., 0], d[..., 2]))       # 0 = forward, 90 = outboard, 180 = aft
    el = deg(np.arcsin(np.clip(d[..., 1], -1, 1)))
    h = smoothstep(-3, 3, az) * (1 - smoothstep(107, 113, az))
    h = h * (0.6 + 0.4 * (1 - smoothstep(12, 30, az)))         # FAR 25.1391: 40 cd ahead, 5 cd from 20 deg on
    v = np.where(el < 0, np.cos(np.radians(el)) ** 1.4, np.cos(np.radians(el)) ** 2.5) * _mount(el)
    return h * v


def em_tail(d, l):
    az = deg(np.arctan2(d[..., 0], -d[..., 2]))                # 0 = straight aft
    el = deg(np.arcsin(np.clip(d[..., 1], -1, 1)))
    h = 1 - smoothstep(67, 73, np.abs(az))                      # 140 deg aft sector
    v = np.where(el < 0, np.cos(np.radians(el)) ** 1.4, np.cos(np.radians(el)) ** 2.5) * _mount(el)
    return h * v


def em_strobe(d, l, side):
    o = side * d[..., 0]                                        # outboard component
    el = deg(np.arcsin(np.clip(d[..., 1], -1, 1)))
    return smoothstep(-0.25, 0.15, o) * np.cos(np.radians(el)) ** 1.2 * _mount(el)


def em_beacon(d, l, base_az, el_lo, el_hi, top):
    # rotating beam: narrow in azimuth (relative to the beam's current heading), wide in elevation (plane frame)
    az = deg(np.arctan2(d[..., 0], d[..., 2])) - base_az
    az = (az + 180.0) % 360.0 - 180.0
    el = deg(np.arcsin(np.clip(d[..., 1], -1, 1)))
    fan = np.exp(-0.5 * (az / 7.0) ** 2)
    w = window(el, el_lo, el_hi, 3.0)
    if top:
        w = w * (0.5 + 0.5 * smoothstep(el_lo, -18.0, el))
    else:
        w = w * (0.55 + 0.45 * smoothstep(el_lo, -15.0, el))
    return fan * w


def em_landing(d, l):
    lz = np.maximum(l[..., 2], 1e-6)
    th = deg(np.arccos(np.clip(l[..., 2], -1, 1)))
    ax = deg(np.arctan2(l[..., 0], lz))
    ay = deg(np.arctan2(l[..., 1], lz))
    core = np.exp(-0.5 * (th / 4.5) ** 2) + 0.10 * np.exp(-0.5 * ((th - 7.5) / 1.3) ** 2)   # PAR lamp: hot core + ring
    skirt = 0.075 * window(ay, -35, -4, 7) * window(ax, -28, 28, 10) * (0.3 + 0.7 * smoothstep(-36, -6, ay))
    up = 0.012 * window(ay, 0, 22, 6) * window(ax, -22, 22, 6)
    return np.clip(core + skirt + up, 0, 1)


def em_dome(d, l):
    th = deg(np.arccos(np.clip(l[..., 2], -1, 1)))
    return (1 - smoothstep(40, 57, th)) * (1 - 0.3 * smoothstep(8, 42, th))


def em_cargo(d, l):
    lz = np.maximum(l[..., 2], 1e-6)
    th = np.arccos(np.clip(l[..., 2], -1, 1))
    ax = np.abs(deg(np.arctan2(l[..., 0], lz)))                  # across the tube (plane X: towards the walls)
    ay = np.abs(deg(np.arctan2(l[..., 1], lz)))                  # along the tube (plane Z)
    return (1 - smoothstep(64, 74, ax)) * (1 - smoothstep(56, 68, ay)) * (0.55 + 0.45 * np.cos(th))


def em_flood(d, l):
    lz = np.maximum(l[..., 2], 1e-6)
    ax = deg(np.arctan2(l[..., 0], lz))
    ay = deg(np.arctan2(l[..., 1], lz))                          # + = towards the panel face
    upper = 1 - smoothstep(58, 68, ay)
    lower = 0.14 + 0.24 * smoothstep(-48, -8, ay)                # spill on the pilots' hands and laps
    v = lower + (upper - lower) * smoothstep(-8, 8, ay)
    return window(ax, -63, 63, 7) * v


# ---------------------------------------------------------------- light table
# shadows: tier the light gets at the quality where it casts shadows; q = lowest rig shadowQuality that turns them on
LIGHTS = [
    dict(key='Nav_L', socket='Socket_Nav_L', fwd=dirv(-55, -35), up=(0, 1, 0), outer=160, inner=152, range=8.0,
         intensity=4.0, cct=6500, filter=(1.0, 0.02, 0.01), kind='incandescent', group='nav',
         em=lambda d, l: em_nav(d, l, -1), res=128,
         glow=dict(pattern_fwd=dirv(-55, 0), sector=55, soft=3, elev=2.5, floor=0.06, core=0.035, core_gain=2.2,
                   halo=0.7, iso=1.0)),
    dict(key='Nav_R', socket='Socket_Nav_R', fwd=dirv(55, -35), up=(0, 1, 0), outer=160, inner=152, range=8.0,
         intensity=4.0, cct=6500, filter=(0.02, 1.0, 0.45), kind='incandescent', group='nav',
         em=lambda d, l: em_nav(d, l, +1), res=128,
         glow=dict(pattern_fwd=dirv(55, 0), sector=55, soft=3, elev=2.5, floor=0.06, core=0.035, core_gain=2.2,
                   halo=0.7, iso=1.0)),
    dict(key='Nav_Tail', socket='Socket_Nav_Tail', fwd=dirv(180, -25), up=(0, 1, 0), outer=160, inner=152, range=7.0,
         intensity=1.5, cct=3000, filter=(1.0, 1.0, 1.0), kind='incandescent', group='nav',
         em=em_tail, res=128,
         glow=dict(pattern_fwd=dirv(180, 0), sector=70, soft=3, elev=2.5, floor=0.06, core=0.03, core_gain=2.2,
                   halo=0.7, iso=1.0)),
    dict(key='Strobe_L', socket='Socket_Strobe_L', fwd=dirv(-90, -15), up=(0, 1, 0), outer=170, inner=164, range=26.0,
         intensity=30.0, cct=6500, filter=(0.92, 0.96, 1.0), kind='xenon', group='strobe',
         em=lambda d, l: em_strobe(d, l, -1), res=128,
         glow=dict(pattern_fwd=dirv(-90, 0), sector=100, soft=20, elev=1.2, floor=0.04, core=0.03, core_gain=2.5,
                   halo=0.6, iso=1.0, radius_scale=0.9)),
    dict(key='Strobe_R', socket='Socket_Strobe_R', fwd=dirv(90, -15), up=(0, 1, 0), outer=170, inner=164, range=26.0,
         intensity=30.0, cct=6500, filter=(0.92, 0.96, 1.0), kind='xenon', group='strobe',
         em=lambda d, l: em_strobe(d, l, +1), res=128,
         glow=dict(pattern_fwd=dirv(90, 0), sector=100, soft=20, elev=1.2, floor=0.04, core=0.03, core_gain=2.5,
                   halo=0.6, iso=1.0, radius_scale=0.9)),
    dict(key='Beacon_Top', socket='Socket_Beacon_Top', fwd=dirv(180, -16), up=(0, 1, 0), outer=72, inner=68, range=30.0,
         intensity=25.0, cct=6500, filter=(1.0, 0.06, 0.012), kind='incandescent', group='beacon', rotates=True,
         em=lambda d, l: em_beacon(d, l, 180.0, -40.0, 8.0, True), res=128,
         glow=dict(pattern_fwd=dirv(180, 0), fan=7.0, el_lo=-40, el_hi=8, elev=0.0, floor=0.05, core=0.03, core_gain=1.6,
                   halo=1.0, iso=0.0),
         beam=dict(length=26.0, x=(-24, 24), y=(-30, 30), fan=7.0, el_lo=-40, el_hi=8, gain=1.0, g=0.6)),
    dict(key='Beacon_Bottom', socket='Socket_Beacon_Bottom', fwd=dirv(0, -36), up=(0, 1, 0), outer=80, inner=76, range=16.0,
         intensity=8.0, cct=6500, filter=(1.0, 0.06, 0.012), kind='incandescent', group='beacon', rotates=True,
         em=lambda d, l: em_beacon(d, l, 0.0, -62.0, -3.0, False), res=128,
         glow=dict(pattern_fwd=dirv(0, 0), fan=7.0, el_lo=-62, el_hi=-3, elev=0.0, floor=0.05, core=0.04, core_gain=1.6,
                   halo=1.0, iso=0.0),
         beam=dict(length=12.0, x=(-24, 24), y=(-30, 36), fan=7.0, el_lo=-62, el_hi=-3, gain=1.0, g=0.6)),
    dict(key='Landing', socket='Socket_Landing', fwd=dirv(1.5, -12), up=(0, 1, 0), outer=78, inner=74, range=160.0,
         intensity=900.0, cct=3400, filter=(1.0, 1.0, 1.0), kind='incandescent', group='landing', tau=(0.12, 0.25),
         em=em_landing, res=256, shadows='medium', q='Low', near=0.2,
         glow=dict(pattern_fwd=None, beam_width=4.5, elev=0.0, floor=0.015, core=0.05, core_gain=0.35,
                   halo=1.0, iso=0.0),
         beam=dict(length=70.0, x=(-32, 32), y=(-38, 26), core=4.5, skirt=0.012, gain=1.0, g=0.7)),
    dict(key='Dome_L', socket='Socket_Light_Dome_L', fwd=unit((-0.245, -0.97, 0.11)), up=(0, 0, 1), outer=118, inner=104,
         range=2.3, intensity=0.5, cct=3000, filter=(1.0, 1.0, 1.0), kind='incandescent', group='cabin',
         em=em_dome, res=128, shadows='low', q='Medium', near=0.08),
    dict(key='Dome_R', socket='Socket_Light_Dome_R', fwd=unit((0.245, -0.97, 0.11)), up=(0, 0, 1), outer=118, inner=104,
         range=2.3, intensity=0.5, cct=3000, filter=(1.0, 1.0, 1.0), kind='incandescent', group='cabin',
         em=em_dome, res=128, shadows='low', q='Medium', near=0.08),
    dict(key='Cargo', socket='Socket_Light_Cargo', fwd=(0, -1, 0), up=(0, 0, 1), outer=150, inner=142, range=2.7,
         intensity=0.7, cct=6500, filter=(0.88, 1.0, 0.86), kind='fluorescent', group='cargo',
         em=em_cargo, res=128, shadows='medium', q='Medium', near=0.08),
    dict(key='Cargo_2', socket='Socket_Light_Cargo_2', fwd=(0, -1, 0), up=(0, 0, 1), outer=150, inner=142, range=2.7,
         intensity=0.7, cct=6500, filter=(0.88, 1.0, 0.86), kind='fluorescent', group='cargo',
         em=em_cargo, res=128, shadows='medium', q='Medium', near=0.08),
    dict(key='Flood', socket='Socket_Light_Flood', offset=(-0.3, -0.005, -0.10), fwd=unit((0, -0.966, 0.259)), up=(0, 0, 1),
         outer=140, inner=132, range=1.5, intensity=0.3, cct=6500, filter=(1.0, 0.05, 0.02), kind='incandescent',
         group='flood', em=em_flood, res=128, shadows='low', q='Medium', near=0.05),
    dict(key='Flood_2', socket='Socket_Light_Flood', offset=(0.3, -0.005, -0.10), fwd=unit((0, -0.966, 0.259)), up=(0, 0, 1),
         outer=140, inner=132, range=1.5, intensity=0.3, cct=6500, filter=(1.0, 0.05, 0.02), kind='incandescent',
         group='flood', em=em_flood, res=128, shadows='low', q='Medium', near=0.05),
    # bounce fill: Unity has no bounce for real-time lights; a weak shadowless point per cabin area stands in for the
    # light thrown back by seats, floor and walls (ranges stay inside the cabin: no glow on the wings or the snow)
    dict(key='Fill_Cockpit', socket='Socket_Light_Dome_L', type='point', offset=(0.085, -0.42, 0.0), fwd=(0, 0, 1), up=(0, 1, 0),
         outer=179, inner=179, range=1.25, intensity=0.075, cct=3000, filter=(1.0, 1.0, 1.0), kind='incandescent',
         group='cabin', em=None, res=0),
    dict(key='Fill_Bay', socket='Socket_Light_Cargo', type='point', offset=(0.0, -0.54, -0.65), fwd=(0, 0, 1), up=(0, 1, 0),
         outer=179, inner=179, range=2.0, intensity=0.1, cct=6500, filter=(0.88, 1.0, 0.86), kind='fluorescent',
         group='cargo', em=None, res=0),
]
for L in LIGHTS:
    L.setdefault('type', 'spot')
    L.setdefault('offset', (0.0, 0.0, 0.0))
    L.setdefault('shadows', None)
    L.setdefault('q', None)
    L.setdefault('glow', None)
    L.setdefault('beam', None)
    L.setdefault('rotates', False)
    L.setdefault('near', 0.1)
    L.setdefault('tau', (0.06, 0.12))
    L['fwd'] = unit(L['fwd'])
    L['R'] = look_rotation(L['fwd'], L['up'])

BY_KEY = {L['key']: L for L in LIGHTS}

# socket positions, plane frame (Unity prefab space), from Data/sockets.json v10
SOCKETS = {
    'Socket_Nav_L': (-7.07, 2.86835, 2.3), 'Socket_Nav_R': (7.07, 2.86835, 2.3),
    'Socket_Strobe_L': (-7.075, 2.86835, 2.08), 'Socket_Strobe_R': (7.075, 2.86835, 2.08),
    'Socket_Nav_Tail': (0.0, 2.26, -5.1), 'Socket_Beacon_Top': (0.0, 3.915, -4.4),
    'Socket_Beacon_Bottom': (0.0, 0.955, -1.65), 'Socket_Landing': (-2.3, 2.68978, 2.57),
    'Socket_Light_Dome_L': (-0.085, 2.4726, 2.29), 'Socket_Light_Dome_R': (0.085, 2.4726, 2.29),
    'Socket_Light_Cargo': (0.0, 2.54, 0.55), 'Socket_Light_Cargo_2': (0.0, 2.54, -0.75),
    'Socket_Light_Flood': (0.0, 2.015, 2.965),
}

PARKED_PITCH = 9.98          # deg nose up
PARKED_ROOT_Y = -0.372


def parked_to_world(p):
    """plane frame -> world for the parked pose (ParkedPose at the origin, yaw 0)."""
    p = np.asarray(p, float)
    ph = np.radians(-PARKED_PITCH)                        # Unity Euler(x): y' = y cos - z sin, z' = y sin + z cos
    y = p[..., 1] * np.cos(ph) - p[..., 2] * np.sin(ph)
    z = p[..., 1] * np.sin(ph) + p[..., 2] * np.cos(ph)
    return np.stack([p[..., 0], y + PARKED_ROOT_Y, z], -1)


def light_pos(L):
    return np.asarray(SOCKETS[L['socket']], float) + np.asarray(L['offset'], float)


# ---------------------------------------------------------------- cookies
def cookie_dirs(L, n):
    t = np.tan(np.radians(L['outer'] / 2.0))
    u = (np.arange(n) + 0.5) / n
    v = 1.0 - (np.arange(n) + 0.5) / n                    # row 0 = top of the image = v 1 = light +Y
    U, V = np.meshgrid(u, v)
    lx, ly = (2 * U - 1) * t, (2 * V - 1) * t
    l = np.stack([lx, ly, np.ones_like(lx)], -1)
    l = l / np.linalg.norm(l, axis=-1, keepdims=True)
    d = l @ L['R'].T                                       # light frame -> plane frame
    return d, l


def spot_atten(L, l):
    """URP GetAngleAttenuation: saturate(cos * a + b)^2"""
    co, ci = np.cos(np.radians(L['outer'] / 2)), np.cos(np.radians(L['inner'] / 2))
    a = 1.0 / max(ci - co, 1e-4)
    return np.clip(l[..., 2] * a - co * a, 0, 1) ** 2


def make_cookie(L, n=None):
    n = n or L['res']
    # supersample 3x3 so thin sector edges stay smooth
    ss = 3
    d, l = cookie_dirs(L, n * ss)
    e = L['em'](d, l)
    e = e.reshape(n, ss, n, ss).mean((1, 3))
    return np.clip(e, 0, 1)


def srgb_encode(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


# ---------------------------------------------------------------- colour temperature (Planckian locus -> linear sRGB, max 1)
def cct_rgb(T):
    """Kim et al. (2002) cubic spline of the Planckian locus, CIE XYZ -> linear sRGB, normalised to max = 1
    (the shape of Unity's Mathf.CorrelatedColorTemperatureToRGB, used by URP for Light.colorTemperature)."""
    T = float(np.clip(T, 1000.0, 25000.0))
    if T <= 4000:
        x = -0.2661239e9 / T**3 - 0.2343589e6 / T**2 + 0.8776956e3 / T + 0.179910
    else:
        x = -3.0258469e9 / T**3 + 2.1070379e6 / T**2 + 0.2226347e3 / T + 0.240390
    if T <= 2222:
        y = -1.1063814 * x**3 - 1.34811020 * x**2 + 2.18555832 * x - 0.20219683
    elif T <= 4000:
        y = -0.9549476 * x**3 - 1.37418593 * x**2 + 2.09137015 * x - 0.16748867
    else:
        y = 3.0817580 * x**3 - 5.87338670 * x**2 + 3.75112997 * x - 0.37001483
    X, Y, Z = x / y, 1.0, (1 - x - y) / y
    r = 3.2406 * X - 1.5372 * Y - 0.4986 * Z
    g = -0.9689 * X + 1.8758 * Y + 0.0415 * Z
    b = 0.0557 * X - 0.2040 * Y + 1.0570 * Z
    c = np.maximum(np.array([r, g, b]), 0.0)
    return c / c.max()
