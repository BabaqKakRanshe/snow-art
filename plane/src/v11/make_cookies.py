"""Writes Textures/Cookies/T_Cookie_<key>.png (sRGB-encoded grey, alpha = grey) + a contact sheet."""
import numpy as np, os, sys
from PIL import Image, ImageDraw
from spec_v11 import *
out = sys.argv[1] if len(sys.argv) > 1 else 'cookies'
os.makedirs(out, exist_ok=True)
tiles = []
for L in LIGHTS:
    if L['type'] != 'spot':
        continue
    c = make_cookie(L)
    g = np.round(srgb_encode(c) * 255).astype(np.uint8)
    # URP clamps the spot cookie UV to the edge texel: keep a black 1 px border so nothing streaks outside the cone
    g[0, :] = g[-1, :] = g[:, 0] = g[:, -1] = 0
    Image.fromarray(np.stack([g, g, g, g], -1), 'RGBA').save(os.path.join(out, 'T_Cookie_%s.png' % L['key']), optimize=True)
    # preview tile: cookie x URP spot attenuation (what the light really projects)
    d, l = cookie_dirs(L, c.shape[0])
    t = c * spot_atten(L, l)
    t = Image.fromarray(np.round(srgb_encode(t) * 255).astype(np.uint8)).resize((192, 192), Image.NEAREST).convert('RGB')
    ImageDraw.Draw(t).text((3, 3), L['key'], fill=(255, 200, 0))
    tiles.append(t)
sheet = Image.new('RGB', (192 * 7, 192 * 2))
for i, t in enumerate(tiles): sheet.paste(t, ((i % 7) * 192, (i // 7) * 192))
sheet.save('/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/cookies_v11.png')
print('cookies:', len(tiles), sorted(os.listdir(out)))
