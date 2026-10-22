"""Top-down snow illuminance (Unity units, URP falloff) for the parked plane, per exterior light and combined."""
import numpy as np, sys
from PIL import Image, ImageDraw
from spec_v11 import *
PH = np.radians(-PARKED_PITCH)
Rp = np.array([[1, 0, 0], [0, np.cos(PH), -np.sin(PH)], [0, np.sin(PH), np.cos(PH)]])   # plane -> world (rotation part)
N = 400; X0, X1, Z0, Z1 = -20, 20, -20, 60       # world x (right), z (forward)
xs = np.linspace(X0, X1, N); zs = np.linspace(Z1, Z0, int(N * (Z1 - Z0) / (X1 - X0)))
XX, ZZ = np.meshgrid(xs, zs)
P = np.stack([XX, np.zeros_like(XX), ZZ], -1)
def illum(L, level=1.0):
    lp = parked_to_world(light_pos(L))
    v = P - lp; d2 = (v ** 2).sum(-1); dd = np.sqrt(d2); w = v / dd[..., None]       # world dir light -> point
    dpl = w @ Rp                                    # world -> plane frame (Rp orthonormal: inverse = transpose)
    l = dpl @ L['R']                                # plane -> light frame
    e = L['em'](dpl, l) * spot_atten(L, l)
    win = np.clip(1 - (d2 / L['range'] ** 2) ** 2, 0, 1) ** 2
    ndl = np.clip(-w[..., 1], 0, 1)
    return L['intensity'] * level * e * win * ndl / d2
def tone(E, albedo=0.8):
    return (srgb_encode(np.clip(E * albedo, 0, 1)) * 255).astype(np.uint8)
keys = sys.argv[1:] or ['Landing', 'Nav_L', 'Nav_R', 'Nav_Tail', 'Strobe_L', 'Beacon_Top', 'Beacon_Bottom']
tiles = []
for k in keys:
    E = illum(BY_KEY[k])
    col = np.array(BY_KEY[k]['filter'])
    img = np.stack([tone(E * c) for c in col], -1)
    im = Image.fromarray(img); dr = ImageDraw.Draw(im)
    # plane footprint: sockets (projected) as dots
    for s, p in SOCKETS.items():
        w = parked_to_world(p); px = (w[0] - X0) / (X1 - X0) * N; pz = (Z1 - w[2]) / (Z1 - Z0) * img.shape[0]
        dr.ellipse([px - 2, pz - 2, px + 2, pz + 2], outline=(80, 80, 255))
    dr.text((4, 4), '%s max %.2f  E@5m %.3f' % (k, E.max(), 0), fill=(255, 255, 0))
    # grid every 10 m
    for gz in range(Z0, Z1 + 1, 10):
        y = (Z1 - gz) / (Z1 - Z0) * img.shape[0]; dr.line([0, y, 6, y], fill=(90, 90, 90)); dr.text((8, y - 6), str(gz), fill=(90, 90, 90))
    tiles.append(im)
    # centreline profile for the landing light
    if k == 'Landing':
        lp = parked_to_world(light_pos(BY_KEY[k]))
        ix = np.argmin(np.abs(xs - lp[0]))
        prof = [(z, E[np.argmin(np.abs(zs - z)), ix]) for z in (3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60)]
        print('landing on the snow along its line (x=%.1f): ' % lp[0] + ', '.join('%gm %.3f' % p for p in prof))
W = sum(t.width for t in tiles); H = max(t.height for t in tiles)
out = Image.new('RGB', (W, H)); x = 0
for t in tiles: out.paste(t, (x, 0)); x += t.width
out.save('/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/ground_v11.png')
for k in keys:
    L = BY_KEY[k]; print(k, 'world pos', np.round(parked_to_world(light_pos(L)), 3))
