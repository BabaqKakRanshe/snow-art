"""v11 lighting previews, step 2: URP forward lighting recomputed per pixel from the Cycles passes (albedo, normal,
emission) with the exact URP light model (inverse square x smooth range window, spot cone, cookie, Lambert + URP
specular), Embree shadow rays only for lights that cast shadows in Unity, exponential-squared fog, then (v11) the
UtilityPlane/Airlight glows and UtilityPlane/Beam beams (fx_numpy = the same maths as the shaders), URP-like bloom.
python3 urp_emulate.py <passes prefix> <variant v10|v11> <out.png> [json overrides]"""
import sys, json, os
import numpy as np
import OpenEXR
from PIL import Image
from scipy.ndimage import gaussian_filter
from embreex import rtcore_scene as rtcs
from embreex.mesh_construction import TriangleMesh
sys.path.insert(0, '/home/claude/plane/v11')
from spec_v11 import LIGHTS, BY_KEY, SOCKETS, parked_to_world, light_pos, look_rotation, cct_rgb, srgb_encode, PARKED_PITCH
import fx_numpy as fx

prefix, variant, out_png = sys.argv[1], sys.argv[2], sys.argv[3]
O = dict(levels=dict(nav=1, strobe=0, beacon=1, landing=1, cabin=1, cargo=1, flood=1, panel=1, avionics=1),
         beacon_top=150.0, beacon_bottom=-120.0, atmosphere=0.35, fog_density=0.02, fog_color=(0.008, 0.010, 0.013),
         ambient=0.004, moon=0.03, shadows='Medium', glow=1.0, beam=1.0, bloom=0.25, exposure=1.0, downsample=2,
         time=3.0, cookie_dir='/home/claude/plane/v11/cookies')
if len(sys.argv) > 4:
    over = json.loads(sys.argv[4])
    lv = over.pop('levels', {})
    O.update(over)
    O['levels'].update(lv)
LV = O['levels']

# ---------------------------------------------------------------- passes + scene
f = OpenEXR.File(prefix + '_passes.exr')
P = {}
for part in f.parts:
    for k, c in part.channels.items():
        P[k.replace('ViewLayer.', '')] = np.asarray(c.pixels, np.float64)
alb = P['Diffuse Color']
gloss = P['Glossy Color']
emit = P['Emission']
nrm_b = np.stack([P['Normal.X'], P['Normal.Y'], P['Normal.Z']], -1)
matidx = np.rint(P['Material Index.X']).astype(int)
H, W = alb.shape[:2]
S = np.load(prefix + '_scene.npz')
Mb = np.array([[-1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0]])            # Blender -> Unity
N = nrm_b @ Mb.T
N /= np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-9)
V, T = S['V'].astype(np.float64), S['T']
tri = V[T]
scene = rtcs.EmbreeScene(); TriangleMesh(scene, tri.astype(np.float32))
cast = S['cast']
shadow_scene = rtcs.EmbreeScene(); TriangleMesh(shadow_scene, tri[cast].astype(np.float32))

# camera rays (pixel centres, as rendered)
fov = float(S['fov']); tanh = np.tan(np.radians(fov) / 2)
ii, jj = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
cx = (ii / W * 2 - 1) * tanh * W / H
cy = (1 - jj / H * 2) * tanh
dcam = np.stack([cx, cy, -np.ones_like(cx)], -1)
dcam /= np.linalg.norm(dcam, axis=-1, keepdims=True)
rd = dcam @ (Mb @ S['cam_rot_b']).T                                   # Unity world
ro = np.asarray(S['cam_pos'], float)
cam_fwd = Mb @ S['cam_rot_b'] @ np.array([0, 0, -1.0])
r = scene.run(np.broadcast_to(ro, rd.shape).reshape(-1, 3).astype(np.float32), rd.reshape(-1, 3).astype(np.float32), output=1)
hit = (r['primID'] >= 0).reshape(H, W)
tfar = np.where(hit, r['tfar'].reshape(H, W), 1e6).astype(np.float64)
Pw = ro + rd * tfar[..., None]
# sanity: Embree hits vs the render's coverage
cov = (alb.sum(-1) + gloss.sum(-1) + emit.sum(-1)) > 0
print('hit/coverage agreement %.4f' % ((hit == cov).mean()), flush=True)

Vdir = -rd
Rp = np.array([[1, 0, 0], [0, np.cos(np.radians(-PARKED_PITCH)), -np.sin(np.radians(-PARKED_PITCH))],
               [0, np.sin(np.radians(-PARKED_PITCH)), np.cos(np.radians(-PARKED_PITCH))]])


def Ry(a):
    a = np.radians(a)
    return np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])


def srgb_to_lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def load_cookie(key):
    im = np.asarray(Image.open(os.path.join(O['cookie_dir'], 'T_Cookie_%s.png' % key)).convert('L'), float) / 255.0
    return srgb_to_lin(im)


def sample_cookie(img, u, v):
    n = img.shape[0]
    x = np.clip(u, 0, 1) * n - 0.5
    y = (1 - np.clip(v, 0, 1)) * n - 0.5
    x0 = np.clip(np.floor(x).astype(int), 0, n - 1); y0 = np.clip(np.floor(y).astype(int), 0, n - 1)
    x1 = np.clip(x0 + 1, 0, n - 1); y1 = np.clip(y0 + 1, 0, n - 1)
    fx_, fy_ = np.clip(x - x0, 0, 1), np.clip(y - y0, 0, 1)
    return (img[y0, x0] * (1 - fx_) * (1 - fy_) + img[y0, x1] * fx_ * (1 - fy_) + img[y1, x0] * (1 - fx_) * fy_ +
            img[y1, x1] * fx_ * fy_)


def occluded(pos, ldir, dist, mask):
    """Embree shadow rays from surface points towards the light (casters only)."""
    occ = np.zeros(pos.shape[:2], bool)
    idx = np.nonzero(mask.reshape(-1))[0]
    if len(idx) == 0:
        return occ
    o = (pos.reshape(-1, 3)[idx] + N.reshape(-1, 3)[idx] * 0.004 + ldir.reshape(-1, 3)[idx] * 0.002).astype(np.float32)
    d = ldir.reshape(-1, 3)[idx].astype(np.float32)
    far = np.maximum(dist.reshape(-1)[idx] - 0.03, 1e-3).astype(np.float32)
    res = shadow_scene.run(o, d, dists=far, output=1)
    o2 = occ.reshape(-1)
    o2[idx] = res['primID'] >= 0
    return o2.reshape(occ.shape)


# specular colour: metals (dark albedo, bright gloss) keep the gloss colour, dielectrics F0 = 0.04
lum = lambda c: c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722
metal = (lum(alb) < 0.06) & (lum(gloss) > 0.2)
F0 = np.where(metal[..., None], gloss, 0.04)
ROUGH = 0.25                                                        # roughness for perceptual 0.5


def shade(light_pos_w, R_light, color, I, rng, kind, outer=None, inner=None, cookie=None, shadows=False):
    """URP additional light: returns the radiance added per pixel (diffuse + specular)."""
    Lv = light_pos_w - Pw
    d2 = np.maximum((Lv ** 2).sum(-1), 1e-6)
    dist = np.sqrt(d2)
    Ld = Lv / dist[..., None]
    win = np.clip(1 - (d2 / rng ** 2) ** 2, 0, 1) ** 2
    att = win / d2
    if kind == 'spot':
        l = (-Ld) @ R_light                                           # light -> point, light frame
        co, ci = np.cos(np.radians(outer / 2)), np.cos(np.radians(inner / 2))
        a = 1.0 / max(ci - co, 1e-4)
        att = att * np.clip(l[..., 2] * a - co * a, 0, 1) ** 2
        if cookie is not None:
            t = np.tan(np.radians(outer / 2))
            z = np.maximum(l[..., 2], 1e-6)
            u = 0.5 + 0.5 * (l[..., 0] / z) / t
            v = 0.5 + 0.5 * (l[..., 1] / z) / t
            att = att * sample_cookie(cookie, u, v) * (l[..., 2] > 0)
    ndl = np.clip((N * Ld).sum(-1), 0, 1)
    rad = I * att * ndl * hit
    if shadows:
        m = rad > 1e-5
        rad = rad * ~occluded(Pw, Ld, dist, m)
    Hh = Ld + Vdir
    Hh /= np.maximum(np.linalg.norm(Hh, axis=-1, keepdims=True), 1e-9)
    noh = np.clip((N * Hh).sum(-1), 0, 1); loh = np.clip((Ld * Hh).sum(-1), 0, 1)
    r2 = ROUGH * ROUGH
    dd = noh * noh * (r2 - 1) + 1.00001
    spec = r2 / (dd * dd * np.maximum(0.1, loh * loh) * (ROUGH * 4 + 2))
    return (alb + F0 * spec[..., None]) * (rad[..., None] * np.asarray(color)[None, None, :])


col = np.zeros((H, W, 3))
# ambient + moon (directional with shadows)
col += alb * O['ambient'] * np.array([0.55, 0.65, 1.0])
moon_dir = np.array([-0.45, 0.55, -0.70]); moon_dir /= np.linalg.norm(moon_dir)
ndl = np.clip(N @ moon_dir, 0, 1) * hit
if O['moon'] > 0:
    mm = ndl > 0
    occ = occluded(Pw, np.broadcast_to(moon_dir, Pw.shape), np.full((H, W), 500.0), mm)
    col += alb * (O['moon'] * ndl * ~occ)[..., None] * np.array([0.55, 0.65, 1.0])

SHQ = {'Off': 0, 'Low': 1, 'Medium': 2, 'High': 3}[O['shadows']]
fxlist = []
lens_emit = {}                                                      # material index -> linear colour x strength
LENS = ['Lens_Nav_L', 'Lens_Nav_R', 'Lens_Nav_Tail', 'Lens_Strobe_L', 'Lens_Strobe_R', 'Lens_Beacon_Top',
        'Lens_Beacon_Bottom', 'Lens_Landing', 'Lens_Dome', 'Lens_CargoLight', 'Lens_Flood_L', 'Lens_Flood_R']
GROUP_LEVEL = {'nav': LV['nav'], 'strobe': LV['strobe'], 'beacon': LV['beacon'], 'landing': LV['landing'],
               'cabin': LV['cabin'], 'cargo': LV['cargo'], 'flood': LV['flood']}

if variant == 'v11':
    LENSMAP = {'Nav_L': ('Lens_Nav_L', 3.0), 'Nav_R': ('Lens_Nav_R', 3.0), 'Nav_Tail': ('Lens_Nav_Tail', 2.5),
               'Strobe_L': ('Lens_Strobe_L', 25.0), 'Strobe_R': ('Lens_Strobe_R', 25.0),
               'Beacon_Top': ('Lens_Beacon_Top', 6.0), 'Beacon_Bottom': ('Lens_Beacon_Bottom', 6.0),
               'Landing': ('Lens_Landing', 8.0), 'Dome_L': ('Lens_Dome', 2.5), 'Cargo': ('Lens_CargoLight', 2.5),
               'Flood': ('Lens_Flood_L', 2.0), 'Flood_2': ('Lens_Flood_R', 2.0)}
    QMIN = {'Low': 1, 'Medium': 2, 'High': 3}
    for L in LIGHTS:
        lev = GROUP_LEVEL[L['group']]
        if lev <= 0:
            continue
        out = lev                                                  # steady state: filament output = level
        if L['kind'] == 'fluorescent':
            out = 0.9 + 0.1 * lev
        kel = L['cct'] * (lev ** 0.2 if L['kind'] == 'incandescent' else 1.0)
        lin = np.asarray(L['filter']) * cct_rgb(kel)
        pos = parked_to_world(light_pos(L))
        Rl = Rp @ L['R']
        ang = 0.0
        if L['rotates']:
            ang = O['beacon_top'] if L['key'] == 'Beacon_Top' else O['beacon_bottom']
            Rl = Rp @ Ry(ang) @ L['R']
        sh = L['shadows'] is not None and SHQ >= QMIN[L['q']] and SHQ > 0
        I = L['intensity'] * out
        beam_cut = 1.0
        if L['key'] == 'Beacon_Top':                    # rig: CutForward (fades over the cabin; no shadows below High)
            f3 = (Ry(ang) @ L['R'])[:, 2]
            hd = abs(np.degrees(np.arctan2(f3[0], f3[2])))
            t_ = np.clip((hd - 26.0) / 14.0, 0, 1); beam_cut = t_ * t_ * (3 - 2 * t_)
        I_lamp = I
        I = I * (beam_cut if SHQ < 3 else 1.0)
        if L['type'] == 'spot':
            col += shade(pos, Rl, lin, I, L['range'], 'spot', L['outer'], L['inner'], load_cookie(L['key']), sh)
        else:
            col += shade(pos, Rl, lin, I, L['range'], 'point', None, None, None, sh)
        if L['key'] in LENSMAP:
            ln, gain = LENSMAP[L['key']]
            lens_emit[1 + LENS.index(ln)] = lin * gain * out
        if L['glow']:
            g = dict(fx.GLOW_DEFAULTS)
            G = L['glow']
            g.update(core_size=G['core'], core_gain=G['core_gain'], floor=G['floor'], halo=G.get('halo', 1.0), iso=G.get('iso', 1.0),
                     sector=G.get('sector', 180), soft=G.get('soft', 3), elev=G.get('elev', 0.0), beam=G.get('beam_width', 0.0),
                     fan=G.get('fan', 0.0), el_lo=G.get('el_lo', -90), el_hi=G.get('el_hi', 90))
            g['radius_scale'] = G.get('radius_scale', 0.5)
            if G.get('pattern_fwd') is None:
                Rpat = Rl
            else:
                Rpat = Rp @ (Ry(ang) if L['rotates'] else np.eye(3)) @ look_rotation(G['pattern_fwd'], (0, 1, 0))
            fxlist.append(('glow', L, pos, Rpat, g, I_lamp, lin))
        if L['beam']:
            B = dict(L['beam'])
            B['x'], B['y'] = tuple(B['x']), tuple(B['y'])
            B['core'] = B.get('core', 0.0)
            if B['core'] == 0:
                B['fan'] = B.get('fan', 7.0)
                Rb0 = L['R']
                up_os = Rb0.T @ np.array([0, 1.0, 0])
                hz = np.asarray(L['fwd'], float) - np.dot(L['fwd'], [0, 1, 0]) * np.array([0, 1.0, 0])
                hz /= np.linalg.norm(hz)
                B['up_os'], B['hz_os'] = up_os, Rb0.T @ hz
            fxlist.append(('beam', L, pos, Rl, B, I_lamp * beam_cut, lin))
    pl = LV['panel']
    if pl > 0:
        f_ = pl ** 0.2
        lens_emit[20] = np.array([1, 0.9, 0.78]) * cct_rgb(3000 * f_) * 0.75 * pl
else:
    # v10 as shipped: point lights (landing / flood spots), no cookies, no shadows, gamma colours, no glow
    g2l = srgb_to_lin
    V10 = [('Nav_L', 'point', (1, 0.1, 0.05), 3, 2, None, None, 'nav'), ('Nav_R', 'point', (0.1, 1, 0.2), 3, 2, None, None, 'nav'),
           ('Nav_Tail', 'point', (1, 1, 1), 3, 2, None, None, 'nav'),
           ('Strobe_L', 'point', (1, 1, 1), 10, 8, None, None, 'strobe'), ('Strobe_R', 'point', (1, 1, 1), 10, 8, None, None, 'strobe'),
           ('Beacon_Top', 'point', (1, 0.1, 0.02), 8, 4, None, None, 'beacon'),
           ('Beacon_Bottom', 'point', (1, 0.1, 0.02), 8, 4, None, None, 'beacon'),
           ('Landing', 'spot', (1, 0.97, 0.9), 150, 12, 28, (4, 0, 0), 'landing'),
           ('Dome_L', 'point', (1, 0.85, 0.62), 1.8, 0.8, None, None, 'cabin'), ('Dome_R', 'point', (1, 0.85, 0.62), 1.8, 0.8, None, None, 'cabin'),
           ('Cargo', 'point', (1, 0.85, 0.62), 2.5, 0.8, None, None, 'cargo'), ('Cargo_2', 'point', (1, 0.85, 0.62), 2.5, 0.8, None, None, 'cargo'),
           ('Flood', 'spot', (1, 0.6, 0.35), 1.5, 0.6, 100, (60, 0, 0), 'flood')]
    for key, kind, c, rng, I, ang, eul, grp in V10:
        lev = GROUP_LEVEL[grp]
        if lev <= 0:
            continue
        pos = parked_to_world(np.asarray(SOCKETS[BY_KEY[key]['socket']], float))
        Rl = Rp
        if eul is not None:
            a = np.radians(eul[0])                                 # Unity Euler X: forward -> down
            Rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
            Rl = Rp @ Rx
        col += shade(pos, Rl, g2l(c), I * lev, rng, kind, ang, 21.80208 if ang else None, None, False)
    E10 = {'Lens_Nav_L': ((1, 0.02, 0.01), 6, 'nav'), 'Lens_Nav_R': ((0.02, 1, 0.15), 6, 'nav'), 'Lens_Nav_Tail': ((1, 1, 1), 5, 'nav'),
           'Lens_Strobe_L': ((1, 1, 1), 30, 'strobe'), 'Lens_Strobe_R': ((1, 1, 1), 30, 'strobe'),
           'Lens_Beacon_Top': ((1, 0.08, 0.01), 12, 'beacon'), 'Lens_Beacon_Bottom': ((1, 0.08, 0.01), 12, 'beacon'),
           'Lens_Landing': ((1, 0.97, 0.9), 8, 'landing'), 'Lens_Dome': ((1, 0.85, 0.62), 3, 'cabin'),
           'Lens_CargoLight': ((1, 0.85, 0.62), 3, 'cargo')}
    for ln, (c, k, grp) in E10.items():
        lens_emit[1 + LENS.index(ln)] = g2l(c) * k * GROUP_LEVEL[grp]
    if LV['panel'] > 0:
        lens_emit[20] = g2l((1, 0.55, 0.25)) * 0.6 * LV['panel']

# displays (both variants): radio legends white x 1.2, screens idle glow
lens_emit[21] = np.array([1.0, 1.0, 1.0]) * 1.2 * LV['avionics'] * ((0.25 + 0.75 * LV['panel']) if variant == 'v11' else 1.0)
lens_emit[23] = srgb_to_lin((0.05, 0.12, 0.10)) * 0.6 * LV['avionics']
lens_emit[22] = np.zeros(3)
E = np.zeros((H, W, 3))
for idx, c in lens_emit.items():
    m = matidx == idx
    E[m] = emit[m] * np.asarray(c)[None, :]
col += E

# fog (URP exp2 on the surface colour), sky for no-hit pixels
viewz = tfar * (rd @ cam_fwd)
vis = np.exp(-(O['fog_density'] * viewz) ** 2)
fogc = np.asarray(O['fog_color'])
col = col * vis[..., None] + fogc * (1 - vis[..., None])
sky = np.array([0.0012, 0.0016, 0.0024]) + np.clip(rd[..., 1:2], 0, 1) * np.array([0.0, 0.0002, 0.0006])
col = np.where(hit[..., None], col, sky + fogc * 0.6)

# v11 effects
sigma = 0.12 * O['atmosphere']
Tsc = np.where(hit, tfar, 1e6)
pix_ang = 2 * tanh / H
px, py = ii, jj
Rcam = Mb @ S['cam_rot_b']


def lamp_visibility(c, tol):
    """as the shader: 5 depth taps (+-1.5 px) at the lamp's screen position; off screen or behind the camera -> at the
    nearest screen point in its direction, 3 px inside the edge; compared as distances along each tap's ray"""
    v = c - ro
    lc = v @ Rcam
    d = np.array([lc[0] / (tanh * W / H), lc[1] / tanh])
    w = -lc[2]
    ndc = d / w if w > 1e-4 else d * 1e4
    a = np.maximum(np.abs(ndc), 1e-6)
    ndc = ndc * min(1.0, (1 - 6.0 / W) / a[0], (1 - 6.0 / H) / a[1])
    pxl, pyl = (ndc[0] + 1) / 2 * W, (1 - ndc[1]) / 2 * H
    dist = float(np.linalg.norm(v))
    vis = 0.0
    for dx, dy in ((0, 0), (1.5, 0), (-1.5, 0), (0, 1.5), (0, -1.5)):
        i = int(np.clip(pxl + dx, 0, W - 1)); j = int(np.clip(pyl + dy, 0, H - 1))
        vis += float(Tsc[j, i] >= dist - tol / float(rd[j, i] @ cam_fwd))
    return vis / 5


for kind, L, pos, Rm, prm, I, lin in fxlist:
    if kind == 'glow' and O['glow'] > 0:
        lv = lamp_visibility(pos, 2 * prm['core_size'] + 0.05)
        if os.environ.get('DBG_LV'):
            _v = pos - ro; _lc = _v @ Rcam
            print('LV', L['key'], 'ndc', np.round([_lc[0] / -_lc[2] / tanh / (W / H), _lc[1] / -_lc[2] / tanh], 3) if _lc[2] < 0 else 'behind', 'dist', round(float(np.linalg.norm(_v)), 2), 'lv', lv, flush=True)
        col += fx.airlight(ro, rd, Tsc, cam_fwd, pix_ang, pos, Rm, prm, I * O['glow'], lin, sigma, O['fog_density'], px, py, lv)
    if kind == 'beam' and O['beam'] > 0:
        col += fx.beam(ro, rd, Tsc, cam_fwd, pos, Rm, prm, I * O['beam'], lin, sigma, O['fog_density'], px, py, O['time'])

col *= O['exposure']
# URP-like bloom: threshold 1, soft knee 0.5, intensity O['bloom'], scatter 0.7 over a mip pyramid
if O['bloom'] > 0:
    br = np.maximum(col.max(-1), 1e-6)
    knee = 0.5
    soft = np.clip(br - 1 + knee, 0, 2 * knee) ** 2 / (4 * knee + 1e-5)
    contrib = np.maximum(soft, br - 1) / br
    pre = col * contrib[..., None]
    acc = np.zeros_like(col)
    wsum = 0
    for k in range(1, 8):
        s = 2.0 ** k * (H / 1080.0)
        w = 0.7 ** (k - 1)
        acc += np.stack([gaussian_filter(pre[..., c], s, mode='nearest') for c in range(3)], -1) * w
        wsum += w
    col = col + O['bloom'] * acc / wsum
img = np.clip(col, 0, 1)
ds = O['downsample']
if ds > 1:
    img = img[:H - H % ds, :W - W % ds].reshape(H // ds, ds, W // ds, ds, 3).mean((1, 3))
img8 = np.round(srgb_encode(img) * 255).astype(np.uint8)
Image.fromarray(img8).save(out_png)
print('saved', out_png, img8.shape, 'max lin %.2f' % col.max(), flush=True)
