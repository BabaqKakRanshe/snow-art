"""Generator shed lighting (the plane v11 / van method): an emission diagram per lamp type gives the IES profile
(LM-63, type C, absolute candela), the Unity spot cookie and the lens glow; lamp frame = Unity light frame
(+Z beam axis, +Y up, +X right seen from behind the lamp).  Intensities in URP units (E = I / d^2), calibrated like
the van (snow / floor under a lamp 0.2 .. 0.6).
python3 gen_lights.py <out_dir>   (IES, cookies, contact sheet)"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import van_lights as VL
from ies_lm63 import write_ies

ss, window = VL.smoothstep, VL.window


def em_bulkhead(l):
    """caged bulkhead, frosted dome: a hemisphere out to ~80 deg, a little brighter on the axis; the three cage bars
    across the dome cast six soft dark spokes and a dark hub where they cross"""
    lx, ly, lz = l[..., 0], l[..., 1], l[..., 2]
    th = np.degrees(np.arccos(np.clip(lz, -1, 1)))
    az = np.arctan2(ly, lx)
    base = (1 - ss(70, 88, th)) * (0.72 + 0.28 * np.cos(np.radians(np.minimum(th, 90))))
    bars = ss(0.90, 0.985, np.cos(6 * az)) * window(th, 14, 84, 6)
    hub = 1 - ss(3, 9, th)
    return np.clip(base * (1 - 0.55 * bars) * (1 - 0.45 * hub), 0, 1)


def em_barn(l):
    """barn light: bulb under a deep enamel shade; the white inside throws a hot cone down, the rim cuts at ~72 deg"""
    th = np.degrees(np.arccos(np.clip(l[..., 2], -1, 1)))
    return np.clip((1 - ss(64, 76, th)) * (0.50 + 0.50 * np.exp(-0.5 * (th / 32.0) ** 2)), 0, 1)


TYPES = {
    'bulkhead': dict(em=em_bulkhead, I=1.1, cd=60, cct=2700, filt=(1.0, 1.0, 1.0), unity='Spot', outer=160, inner=140,
                     rng=8.0, group='shed', shadows=True, res=128, lens_floor=0.2,
                     desc='caged bulkhead, 60 W incandescent behind a frosted dome; SHED circuit (Board_MCB_8) and '
                          'Light_Switch; the cage throws six soft spokes (cookie)'),
    'barnlight': dict(em=em_barn, I=3.0, cd=180, cct=2700, filt=(1.0, 1.0, 1.0), unity='Spot', outer=150, inner=120,
                      rng=14.0, group='outd', shadows=True, res=128, lens_floor=0.1,
                      desc='barn light over the door, 100 W under a deep enamel shade; OUTDOOR LIGHTS circuit (Board_MCB_2)'),
}


def colour(t):
    T = TYPES[t]
    return (np.asarray(T['filt']) * VL.cct_rgb(T['cct'])).tolist()


def meta():
    return {k: dict(I=T['I'], cd=T['cd'], k_norm=1.0 / (VL.K_CYCLES * T['cd']), color=colour(k), group=T['group'],
                    lens_floor=T['lens_floor'], unity=T['unity']) for k, T in TYPES.items()}


def write_ies_all(out):
    os.makedirs(out, exist_ok=True)
    H = np.arange(0.0, 360.0, 2.5)
    Vg = np.arange(0.0, 180.001, 1.0)
    G, C = np.meshgrid(np.radians(Vg), np.radians(H))
    phi = np.radians(270.0) - C
    l = np.stack([np.sin(G) * np.cos(phi), np.sin(G) * np.sin(phi), np.cos(G)], -1)
    for key, T in TYPES.items():
        e = np.clip(T['em'](l), 0, None)
        e[e < 1e-4] = 0.0
        cd = T['cd'] * e / max(e.max(), 1e-9)
        kw = {'TEST': 'computed from the generator shed emission diagram (gen_lights.py), same shape as T_Cookie_%s.png' % key,
              'TESTLAB': 'Generator shed (Snow)', 'MANUFAC': 'Generator shed (Snow)', 'LUMCAT': key, 'LUMINAIRE': T['desc'],
              'LAMP': 'incandescent, %d K' % T['cct'],
              'OTHER': 'nadir (0 deg) = beam axis; C0 = light -Y, C90 = light -X, C180 = light +Y, C270 = light +X'}
        write_ies(os.path.join(out, key + '.ies'), Vg, H, cd, kw)
    return list(TYPES)


def write_cookies(out, sheet=None):
    os.makedirs(out, exist_ok=True)
    tiles = []
    for key, T in TYPES.items():
        if T['unity'] != 'Spot':
            continue
        c = VL.make_cookie(T, T['res'])
        g = np.round(VL.srgb_encode(c) * 255).astype(np.uint8)
        g[0, :] = g[-1, :] = g[:, 0] = g[:, -1] = 0
        Image.fromarray(np.stack([g, g, g, g], -1), 'RGBA').save(os.path.join(out, 'T_Cookie_%s.png' % key), optimize=True)
        t = Image.fromarray(np.round(VL.srgb_encode(c) * 255).astype(np.uint8)).resize((220, 220), Image.NEAREST).convert('RGB')
        ImageDraw.Draw(t).text((4, 4), '%s %d deg' % (key, T['outer']), fill=(255, 200, 0))
        tiles.append(t)
    if sheet:
        S = Image.new('RGB', (220 * len(tiles), 220))
        for i, t in enumerate(tiles):
            S.paste(t, (i * 220, 0))
        S.save(sheet)
    return [t for t in TYPES if TYPES[t]['unity'] == 'Spot']


def lights_json(path, lamps, lens_of, note):
    """lamps: [(name, pos, dir, type, up)] in the shed frame; Unity position (-y, z, x)"""
    items = []
    f = lambda v: [round(float(a), 4) + 0.0 for a in v]
    U = lambda v: [round(-float(v[1]), 4) + 0.0, round(float(v[2]), 4) + 0.0, round(float(v[0]), 4) + 0.0]
    for name, pos, d, t, up in lamps:
        T = TYPES[t]
        it = dict(socket='LIGHT_' + name, lens=lens_of.get(name, ''), type=t, unityLight=T['unity'], position=f(pos),
                  forward=f(d), up=f(up), positionUnity=U(pos), forwardUnity=U(d), upUnity=U(up), intensityURP=T['I'],
                  peakCandela=T['cd'], kelvin=T['cct'], filterLinear=list(T['filt']), range=T['rng'], group=T['group'],
                  shadows=bool(T['shadows']), ies='IES/%s.ies' % t, desc=T['desc'])
        if T['unity'] == 'Spot':
            it.update(spotOuter=T['outer'], spotInner=T['inner'], cookie='T_Cookie_%s' % t)
        items.append(it)
    json.dump(dict(note=note, lights=items), open(path, 'w'), indent=1)
    return len(items)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'gen')
    print(write_ies_all(os.path.join(out, 'IES')))
    print(write_cookies(os.path.join(out, 'Cookies'), os.path.join(out, 'cookies_sheet.png')))
