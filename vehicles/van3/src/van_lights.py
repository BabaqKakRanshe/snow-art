"""Van v2 lighting, single source of truth (the Utility Plane v11 method):
each lamp type has an emission diagram E(direction) in its own frame; the same diagram gives
  - the IES profile (IESNA LM-63-2002, type C, absolute candela) used by the Blender light rig,
  - the Unity spot cookie (T_Cookie_<type>.png),
  - the lens glow towards the viewer (the lens is bright only when you look into the beam).
Lamp frame = Unity light frame: +Z beam axis, +Y up, +X right (as seen from behind the lamp).
Blender: a point light with local X = +X, local Y = +Y, local -Z = beam axis reads the IES as written.
Intensities are Unity URP units (linear, E = I / d^2), calibrated like the plane (snow under a lamp 0.2..1).
python3 van_lights.py <out_dir>   (IES, cookies, contact sheet)"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ies_lm63 import write_ies

K_CYCLES = 0.070527            # Cycles IES node: Fac per candela (plane v11 calibration)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def window(x, lo, hi, soft):
    return smoothstep(lo - soft, lo + soft, x) * (1 - smoothstep(hi - soft, hi + soft, x))


def angles(l):
    lz = np.maximum(l[..., 2], 1e-6)
    ax = np.degrees(np.arctan2(l[..., 0], lz))                      # + = right
    ay = np.degrees(np.arctan2(l[..., 1], lz))                      # + = up
    th = np.degrees(np.arccos(np.clip(l[..., 2], -1, 1)))
    return ax, ay, th, l[..., 2] > 1e-4


# ---------------------------------------------------------------- emission diagrams (0..1)
def em_head(l):
    """halogen low beam, right-hand traffic: flat cut-off 0.57 deg below the axis on the left, a 15 deg kink up on
    the right; hot zone a little right and down, a wide spread, the foreground, faint glare above the cut-off"""
    ax, ay, th, front = angles(l)
    cut = -0.57 + np.clip(ax, 0, 7.5) * np.tan(np.radians(15))
    below = 1 - smoothstep(cut - 0.4, cut + 0.4, ay)
    hot = np.exp(-0.5 * (((ax - 2.5) / 7.0) ** 2 + ((ay + 1.7) / 1.9) ** 2))
    wide = 0.40 * np.exp(-0.5 * ((ax / 20.0) ** 2 + ((ay + 3.5) / 4.5) ** 2))
    fore = 0.06 * window(ay, -30, -5, 5) * window(ax, -44, 44, 10)
    glare = 0.010 * window(ay, -1, 14, 4) * window(ax, -35, 35, 10)
    return np.where(front, np.clip((hot + wide + fore) * below + glare, 0, 1), 0.0)


def em_spot(l):
    """round driving lamp: pencil beam with a soft ring and a short skirt"""
    ax, ay, th, front = angles(l)
    e = np.exp(-0.5 * (th / 3.2) ** 2) + 0.14 * np.exp(-0.5 * (th / 9.0) ** 2) + 0.03 * (1 - smoothstep(16, 27, th))
    return np.where(front, np.clip(e, 0, 1), 0.0)


def em_work(l):
    """work flood: wide rectangle with a hot centre a little below the axis"""
    ax, ay, th, front = angles(l)
    e = window(ax, -40, 40, 9) * window(ay, -36, 18, 7) * (0.5 + 0.5 * np.exp(-0.5 * ((ax / 16) ** 2 + ((ay + 6) / 12) ** 2)))
    return np.where(front, e, 0.0)


def em_tail(l):
    """tail / stop and turn lamps: wide horizontally, a little down, brighter on the axis"""
    ax, ay, th, front = angles(l)
    e = window(ax, -80, 80, 12) * window(ay, -50, 40, 12) * (0.55 + 0.45 * np.exp(-0.5 * (th / 25) ** 2))
    return np.where(front, e, 0.0)


def em_reverse(l):
    """reversing lamp: wide, mostly onto the ground behind"""
    ax, ay, th, front = angles(l)
    e = window(ax, -60, 60, 12) * window(ay, -58, 15, 8) * (0.5 + 0.5 * np.exp(-0.5 * ((ay + 15) / 14) ** 2))
    return np.where(front, e, 0.0)


def em_marker(l):
    """clearance / side marker: almost a hemisphere, nothing straight down"""
    ax, ay, th, front = angles(l)
    return np.where(front, window(ax, -88, 88, 10) * window(ay, -40, 75, 12), 0.0)


def em_plate(l):
    ax, ay, th, front = angles(l)
    return np.where(front, 1 - smoothstep(40, 58, th), 0.0)


def em_dome(l):
    """ceiling lamp: housing edge at ~62 deg, a little brighter straight down"""
    ax, ay, th, front = angles(l)
    return np.where(front, (1 - smoothstep(55, 70, th)) * (1 - 0.3 * smoothstep(10, 50, th)), 0.0)


def em_night(l):
    ax, ay, th, front = angles(l)
    return np.where(front, 1 - smoothstep(70, 86, th), 0.0)


def em_fog(l):
    """fog lamp: very wide and flat, a hard top cut-off a degree under the axis, the light stays under the fog"""
    ax, ay, th, front = angles(l)
    top = 1 - smoothstep(-2.0, -0.6, ay)
    e = window(ax, -40, 40, 9) * window(ay, -30, 0, 4) * top * (0.35 + 0.65 * np.exp(-0.5 * ((ay + 4.0) / 4.0) ** 2))
    return np.where(front, e, 0.0)


def em_hand(l):
    """inspection lamp: a bare bulb in a six-bar wire cage, the handle shadows the back; bars cut thin dark wedges"""
    lx, ly, lz = l[..., 0], l[..., 1], l[..., 2]
    th = np.degrees(np.arccos(np.clip(lz, -1, 1)))                   # 0 = towards the hook, 180 = into the handle
    az = np.arctan2(ly, lx)
    bars = smoothstep(0.90, 0.98, np.cos(6 * az)) * window(th, 25, 150, 8)
    return (1 - smoothstep(128, 160, th)) * (1 - 0.55 * bars)


def em_torch(l):
    """hand torch with a cheap reflector: hot spot 6 deg, a dark ring, the wide dim spill out to 28 deg"""
    ax, ay, th, front = angles(l)
    e = np.exp(-0.5 * (th / 6.0) ** 2) * (1 - 0.35 * window(th, 9, 13, 2)) + 0.16 * (1 - smoothstep(20, 30, th))
    return np.where(front, np.clip(e, 0, 1), 0.0)


def em_flare(l):
    """road flare held by its handle: a red ball of light, the burning end hides little, the hand side is dark"""
    th = np.degrees(np.arccos(np.clip(l[..., 2], -1, 1)))           # 0 = out of the burning end
    return 1 - 0.75 * smoothstep(110, 175, th)


def em_stove(l):
    """fire in the saloon stove: the light leaves through the open door (+axis) in a wide fan, the hot iron glows a little
    all round"""
    th = np.degrees(np.arccos(np.clip(l[..., 2], -1, 1)))           # 0 = straight out of the door
    return 0.12 + 0.88 * (1 - smoothstep(55, 95, th))


def em_pendant(l):
    """pendant lamp over the table: bare bulb under a conical shade - full light down and sideways, the shade cuts it
    just above the horizontal; a faint glow goes up through the cord hole"""
    th = np.degrees(np.arccos(np.clip(l[..., 2], -1, 1)))           # 0 = straight down
    return 0.04 + 0.96 * (1 - smoothstep(92, 104, th))


def em_flood(l):
    """instrument flood under the cluster hood: wide across the panel, cut by the hood above"""
    ax, ay, th, front = angles(l)
    return np.where(front, window(ax, -63, 63, 8) * window(ay, -55, 60, 8), 0.0)


# ---------------------------------------------------------------- lamp types
# I = URP intensity (100 %), cd = peak candela for IES / HDRP, cct + filter = colour (filter is linear),
# unity = light type, outer / inner = spot angles, rng = range (m), group = switch circuit
TYPES = {
    'head':    dict(em=em_head, I=320.0, cd=20000, cct=3300, filt=(1.0, 1.0, 1.0), unity='Spot', outer=70, inner=62,
                    rng=70.0, group='drive', shadows=True, res=256, lens_floor=0.012,
                    desc='halogen low beam, right-hand traffic: flat cut-off left, 15 deg kink right'),
    'spot':    dict(em=em_spot, I=550.0, cd=60000, cct=3400, filt=(1.0, 1.0, 1.0), unity='Spot', outer=40, inner=34,
                    rng=110.0, group='spot', shadows=True, res=128, lens_floor=0.010,
                    desc='round driving lamp: pencil beam sigma 3.2 deg, ring, skirt to 27 deg'),
    'work':    dict(em=em_work, I=70.0, cd=3500, cct=3400, filt=(1.0, 1.0, 1.0), unity='Spot', outer=110, inner=100,
                    rng=28.0, group='work', shadows=True, res=128, lens_floor=0.02,
                    desc='work flood 80 x 54 deg, hot centre 6 deg below the axis'),
    'tail':    dict(em=em_tail, I=2.5, cd=12, cct=2900, filt=(1.0, 0.035, 0.018), unity='Point', rng=4.0,
                    group='drive', shadows=False, lens_floor=0.06, desc='red tail lamp, wide'),
    'amber':   dict(em=em_tail, I=6.0, cd=90, cct=2900, filt=(1.0, 0.42, 0.04), unity='Point', rng=5.0,
                    group='turn', shadows=False, lens_floor=0.06, desc='amber turn signal, wide (blinks, 90 / min)'),
    'reverse': dict(em=em_reverse, I=22.0, cd=320, cct=2900, filt=(1.0, 1.0, 1.0), unity='Spot', outer=130, inner=118,
                    rng=10.0, group='reverse', shadows=False, res=128, lens_floor=0.04,
                    desc='reversing lamp, wide onto the ground behind'),
    'marker':  dict(em=em_marker, I=1.2, cd=6, cct=2900, filt=(1.0, 0.45, 0.05), unity='Point', rng=3.0,
                    group='drive', shadows=False, lens_floor=0.08, desc='amber clearance / side marker'),
    'plate':   dict(em=em_plate, I=0.8, cd=4, cct=2900, filt=(1.0, 1.0, 1.0), unity='Spot', outer=120, inner=104,
                    rng=1.5, group='drive', shadows=False, res=64, lens_floor=0.05, desc='number plate lamp, down'),
    'dome':    dict(em=em_dome, I=0.55, cd=30, cct=2800, filt=(1.0, 1.0, 1.0), unity='Spot', outer=140, inner=126,
                    rng=4.0, group='int', shadows=True, res=64, lens_floor=0.25, desc='ceiling dome lamp'),
    'night':   dict(em=em_night, I=0.12, cd=1, cct=2700, filt=(1.0, 0.06, 0.03), unity='Point', rng=2.5,
                    group='int', shadows=False, lens_floor=0.25, desc='red night lamp on the partition'),
    'flood':   dict(em=em_flood, I=0.08, cd=2, cct=2700, filt=(1.0, 0.40, 0.22), unity='Spot', outer=140, inner=126,
                    rng=1.2, group='int', shadows=False, res=64, lens_floor=0.0, desc='instrument flood under the hood'),
    'fog':     dict(em=em_fog, I=140.0, cd=4000, cct=3000, filt=(1.0, 0.80, 0.26), unity='Spot', outer=96, inner=86,
                    rng=30.0, group='fog', shadows=True, res=128, lens_floor=0.03,
                    desc='selective-yellow fog lamp in the bumper: 80 deg wide, hard top cut-off under the axis'),
    'hand':    dict(em=em_hand, I=1.6, cd=30, cct=2700, filt=(1.0, 1.0, 1.0), unity='Point', rng=6.0,
                    group='hand', shadows=True, lens_floor=0.3,
                    desc='inspection lamp on a cord: bare 21 W bulb in a wire cage (moves with the WorkLamp item)'),
    'torch':   dict(em=em_torch, I=18.0, cd=900, cct=3000, filt=(1.0, 0.95, 0.86), unity='Spot', outer=60, inner=14,
                    rng=22.0, group='torch', shadows=True, res=64, lens_floor=0.05,
                    desc='hand torch from the glovebox: hot spot 6 deg, dark ring, dim spill to 28 deg (rides on Flashlight)'),
    'flare':   dict(em=em_flare, I=9.0, cd=120, cct=1900, filt=(1.0, 0.10, 0.05), unity='Point', rng=12.0,
                    group='flare', shadows=True, lens_floor=0.2,
                    desc='red road flare from the glovebox, about a minute of burning; flicker it (rides on Flare_N)'),
    'stove':   dict(em=em_stove, I=0.35, cd=20, cct=2850, filt=(1.0, 1.0, 1.0), unity='Point', rng=4.5,
                    group='fire', shadows=True, lens_floor=0.0,
                    desc='fire in the saloon stove, 10 cm in front of the door: on while it burns, flicker it; '
                         'x 0.3 with StoveDoor shut, brighter with StoveDoor_Vent open (StoveGlow is the visible fire)'),
    'pendant': dict(em=em_pendant, I=0.56, cd=30, cct=4100, filt=(1.0, 1.0, 1.0), unity='Point', rng=4.0,
                    group='int', shadows=True, lens_floor=0.0,
                    desc='pendant lamp over the saloon table: bulb under a conical shade, on the Cabin circuit (Fuse_6)'),
}
SOCKET_SCALE = {'Dome_Cab': 0.6}            # per-lamp intensity factors


def cct_rgb(T):
    """Planckian locus -> linear sRGB, max 1 (the shape Unity uses for Light.colorTemperature)"""
    T = float(np.clip(T, 1000.0, 25000.0))
    if T <= 4000:
        x = -0.2661239e9 / T ** 3 - 0.2343589e6 / T ** 2 + 0.8776956e3 / T + 0.179910
    else:
        x = -3.0258469e9 / T ** 3 + 2.1070379e6 / T ** 2 + 0.2226347e3 / T + 0.240390
    if T <= 2222:
        y = -1.1063814 * x ** 3 - 1.34811020 * x ** 2 + 2.18555832 * x - 0.20219683
    elif T <= 4000:
        y = -0.9549476 * x ** 3 - 1.37418593 * x ** 2 + 2.09137015 * x - 0.16748867
    else:
        y = 3.0817580 * x ** 3 - 5.87338670 * x ** 2 + 3.75112997 * x - 0.37001483
    X, Y, Z = x / y, 1.0, (1 - x - y) / y
    c = np.maximum(np.array([3.2406 * X - 1.5372 * Y - 0.4986 * Z, -0.9689 * X + 1.8758 * Y + 0.0415 * Z,
                             0.0557 * X - 0.2040 * Y + 1.0570 * Z]), 0.0)
    return c / c.max()


def colour(t):
    T = TYPES[t]
    return (np.asarray(T['filt']) * cct_rgb(T['cct'])).tolist()


def srgb_encode(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def write_ies_all(out):
    os.makedirs(out, exist_ok=True)
    H = np.arange(0.0, 360.0, 2.5)
    for key, T in TYPES.items():
        if key == 'head':
            Vg = np.unique(np.r_[np.arange(0, 20, 0.25), np.arange(20, 60, 0.5), np.arange(60, 180.001, 1.0)])
        else:
            Vg = np.arange(0.0, 180.001, 1.0)
        G, C = np.meshgrid(np.radians(Vg), np.radians(H))
        phi = np.radians(270.0) - C
        l = np.stack([np.sin(G) * np.cos(phi), np.sin(G) * np.sin(phi), np.cos(G)], -1)
        e = np.clip(T['em'](l), 0, None)
        e[e < 1e-4] = 0.0
        cd = T['cd'] * e / max(e.max(), 1e-9)
        kw = {'TEST': 'computed from the van v2 emission diagram (van_lights.py), same shape as T_Cookie_%s.png' % key,
              'TESTLAB': 'Van v2 (Snow)', 'MANUFAC': 'Van v2 (Snow)', 'LUMCAT': key, 'LUMINAIRE': T['desc'],
              'LAMP': 'incandescent / halogen, %d K' % T['cct'],
              'OTHER': 'nadir (0 deg) = beam axis; C0 = light -Y, C90 = light -X, C180 = light +Y, C270 = light +X'}
        write_ies(os.path.join(out, key + '.ies'), Vg, H, cd, kw)


def make_cookie(T, n):
    ss = 3
    m = n * ss
    t = np.tan(np.radians(T['outer'] / 2.0))
    u = (np.arange(m) + 0.5) / m
    v = 1.0 - (np.arange(m) + 0.5) / m
    U, V = np.meshgrid(u, v)
    l = np.stack([(2 * U - 1) * t, (2 * V - 1) * t, np.ones_like(U)], -1)
    l /= np.linalg.norm(l, axis=-1, keepdims=True)
    e = T['em'](l).reshape(n, ss, n, ss).mean((1, 3))
    return np.clip(e / max(e.max(), 1e-9), 0, 1)


def write_cookies(out, sheet=None):
    os.makedirs(out, exist_ok=True)
    tiles = []
    for key, T in TYPES.items():
        if T['unity'] != 'Spot':
            continue
        c = make_cookie(T, T['res'])
        g = np.round(srgb_encode(c) * 255).astype(np.uint8)
        g[0, :] = g[-1, :] = g[:, 0] = g[:, -1] = 0                  # URP clamps to the edge texel
        Image.fromarray(np.stack([g, g, g, g], -1), 'RGBA').save(os.path.join(out, 'T_Cookie_%s.png' % key), optimize=True)
        t = Image.fromarray(np.round(srgb_encode(c) * 255).astype(np.uint8)).resize((200, 200), Image.NEAREST).convert('RGB')
        ImageDraw.Draw(t).text((4, 4), '%s %d deg' % (key, T['outer']), fill=(255, 200, 0))
        tiles.append(t)
    if sheet:
        S = Image.new('RGB', (200 * len(tiles), 200))
        for i, t in enumerate(tiles):
            S.paste(t, (i * 200, 0))
        S.save(sheet)
    return [t for t in TYPES if TYPES[t]['unity'] == 'Spot']


def meta():
    """per type: Cycles normalisation and colour for the Blender rig"""
    return {k: dict(I=T['I'], cd=T['cd'], k_norm=1.0 / (K_CYCLES * T['cd']), color=colour(k), group=T['group'],
                    lens_floor=T['lens_floor'], unity=T['unity']) for k, T in TYPES.items()}


def lights_json(path, sockets, lens_of=None, note=None, desc=False):
    """sockets: [(name, pos, dir, type, up)] in the van frame (x forward, y left, z up, metres, after the lift).
    Unity (FBX, Y up, Z forward): position (-y, z, x).  lens_of: {name: glowing object} where it is not Lens_<name>;
    desc: write the type description into every entry."""
    items = []
    lens_of = lens_of or {}
    for name, pos, d, t, up in sockets:
        T = TYPES[t]
        I = T['I'] * SOCKET_SCALE.get(name, 1.0)
        it = dict(socket='LIGHT_' + name, lens=lens_of.get(name, 'Lens_' + name), type=t, unityLight=T['unity'],
                  position=[round(float(v), 4) + 0.0 for v in pos], forward=[round(float(v), 4) + 0.0 for v in d],
                  up=[round(float(v), 4) + 0.0 for v in up],
                  positionUnity=[round(-float(pos[1]), 4) + 0.0, round(float(pos[2]), 4) + 0.0, round(float(pos[0]), 4) + 0.0],
                  forwardUnity=[round(-float(d[1]), 4) + 0.0, round(float(d[2]), 4) + 0.0, round(float(d[0]), 4) + 0.0],
                  upUnity=[round(-float(up[1]), 4) + 0.0, round(float(up[2]), 4) + 0.0, round(float(up[0]), 4) + 0.0],
                  intensityURP=round(I, 3), peakCandela=T['cd'] * SOCKET_SCALE.get(name, 1.0), kelvin=T['cct'],
                  filterLinear=list(T['filt']), range=T['rng'], group=T['group'], shadows=bool(T['shadows']),
                  ies='IES/%s.ies' % t)
        if T['unity'] == 'Spot':
            it.update(spotOuter=T['outer'], spotInner=T['inner'], cookie='T_Cookie_%s' % t)
        if desc:
            it['desc'] = T['desc']
        items.append(it)
    json.dump(dict(note=note or 'van v2 lamps. position / forward / up: van frame (x forward, y left, z up, m); *Unity: (-y, z, x). '
                                'intensityURP at 100 %; groups are switch circuits (drive, spot, work, turn, reverse, int).',
                   lights=items), open(path, 'w'), indent=1)
    return len(items)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'van2')
    write_ies_all(os.path.join(out, 'IES'))
    print('cookies', write_cookies(os.path.join(out, 'Cookies'), os.path.join(out, 'cookies_sheet.png')))
