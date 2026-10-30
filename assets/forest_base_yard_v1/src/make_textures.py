"""textures of forest_base_v1 (64 x 64 pixel tiles like the project's): copies of the project textures the concept used,
the container ribs (8 ribs a tile: 0.3 m at the 2.4 m tile), the yellow / black and red / white bands.
python3 -I make_textures.py <out folder>"""
import os, sys
import numpy as np
from PIL import Image

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
MAPT = '/mnt/user-data/uploads/snow/source/world_sync/forest/map/textures/'
GR = '/mnt/user-data/uploads/snow/Snow/Assets/Locations/Forest/Terrain/Ground/'
COPIES = {'T_BaseConcrete_px': MAPT + 'T_Concrete_A_px.png', 'T_BaseSteel_px': MAPT + 'T_Steel_A_px.png',
          'T_BaseOlive_px': MAPT + 'T_PaintOlive_A_px.png', 'T_BaseRust_px': MAPT + 'T_Base_Rust_A_px.png',
          'T_BaseCorr_px': MAPT + 'T_Corrugated_A.png', 'T_BaseWood_px': MAPT + 'T_WoodSiding_A.jpg',
          'T_BaseSnow_A': GR + 'T_GR_Floor_A.png', 'T_BaseSnowDark_A': GR + 'T_GR_FloorDark_A.png', 'T_BaseSnowChunk_A': GR + 'T_GR_Gravel_A.png'}
for n, src in COPIES.items():
    im = Image.open(src).convert('RGB')
    im.save(os.path.join(OUT, n + '.png'))
    print(n, im.size)
rng = np.random.default_rng(2810)
N = 64
# container ribs: per 8 px rib: lit edge, face, shadowed edge; rust drips from the top rail
x = np.arange(N) % 8
prof = np.array([228, 214, 200, 196, 192, 188, 168, 150], float)[x]
img = np.tile(prof, (N, 1)) + rng.normal(0, 4, (N, N))
rust = np.zeros((N, N))
for _ in range(7):
    c = rng.integers(0, N); L = rng.integers(10, 40); w = rng.integers(1, 3)
    for y in range(L):
        rust[y, (c + np.arange(w)) % N] = max(0.0, 1 - y / L) * 0.8
rgb = np.stack([img, img, img], -1)
rc = np.array([110, 62, 36], float)
rgb = rgb * (1 - rust[..., None]) + rc * rust[..., None]
Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB').save(os.path.join(OUT, 'T_BaseContRibs_px.png'))
for name, top, bot in (('T_BaseStripeYB_px', (230, 160, 12), (22, 22, 22)), ('T_BaseBandRW_px', (160, 14, 10), (214, 214, 214))):
    a = np.zeros((N, N, 3), np.uint8); a[:N // 2] = top; a[N // 2:] = bot
    Image.fromarray(a, 'RGB').save(os.path.join(OUT, name + '.png'))
print('ribs, stripes')
