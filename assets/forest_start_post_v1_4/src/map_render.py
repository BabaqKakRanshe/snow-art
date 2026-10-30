"""The Forest map seen from above, from the scene's own data (the Unity editor can't be reached from the container):
the 9 TerrainData tiles (heights -> hill shade, the 8 terrain layers -> snow, ploughed roads, tracks, rock; 78 783 terrain trees
and rocks by prototype), the lake's and the creeks' ice meshes (World/Streams). Winter colours as the scene shows them under
flat light. -> <out.png> over X -600..1200, Z -1200..600 (+X right, +Z up), <px> square.
python3 -I map_render.py <out.png> [px]"""
import sys, json, re, math
import numpy as np
from PIL import Image, ImageDraw

T = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/terr'
STREAMS = '/mnt/user-data/uploads/snow/Snow/Assets/Levels/Forest/World/Streams'
X0, Z0, SIZE, TILE = -600.0, -1200.0, 1800.0, 600.0
out = sys.argv[1]
PX = int(sys.argv[2]) if len(sys.argv) > 2 else 1800
mpp = SIZE / PX
d = np.load(f'{T}/terrain.npz')
names = json.load(open(f'{T}/proto_names.json'))

# ---- ground: heights and layers resampled onto the map grid (row 0 = the top = Z max)
Hm = np.zeros((PX, PX), np.float32)
Wm = np.zeros((PX, PX, 8), np.float32)
cols = (np.arange(PX) + 0.5) * mpp + X0
rows = Z0 + SIZE - (np.arange(PX) + 0.5) * mpp
for i in range(3):
    for j in range(3):
        H = d[f'Forest_TerrainData_{i}_{j}_H'] * 136.0 - 84.0
        Wt = d[f'Forest_TerrainData_{i}_{j}_W'].astype(np.float32)[::-1]          # alphamap rows: Z min first
        tx0, tz0 = X0 + i * TILE, Z0 + j * TILE
        ci = np.nonzero((cols >= tx0) & (cols < tx0 + TILE))[0]
        ri = np.nonzero((rows >= tz0) & (rows < tz0 + TILE))[0]
        u = (cols[ci] - tx0) / TILE
        v = (rows[ri] - tz0) / TILE
        hx = np.clip((u * 1024).astype(int), 0, 1024)
        hz = np.clip((v * 1024).astype(int), 0, 1024)
        Hm[np.ix_(ri, ci)] = H[np.ix_(hz, hx)]
        ax = np.clip((u * 1024).astype(int), 0, 1023)
        az = np.clip((v * 1024).astype(int), 0, 1023)
        Wm[np.ix_(ri, ci)] = Wt[np.ix_(az, ax)]
# layers: ForestFloor, ForestFloorDark, RoadGravel, TrailSoil, Rock, RoadRuts, TrailTrack, Asphalt -> their winter look
LAYER = np.array([(228, 232, 238), (214, 219, 226), (150, 148, 142), (204, 200, 192), (118, 118, 118), (164, 158, 148),
                  (196, 194, 188), (122, 122, 124)], np.float32)
ws = Wm / np.maximum(Wm.sum(2, keepdims=True), 1e-4)
road = ws[..., 2] + ws[..., 5] + ws[..., 7] + 0.6 * (ws[..., 3] + ws[..., 6])            # gravel, ruts, asphalt; tracks
img = (ws[..., :, None] * LAYER[None, None]).sum(2)
gz, gx = np.gradient(Hm, mpp)
light = np.array([-1.0, 1.0, 1.4]); light /= np.linalg.norm(light)                  # from the north-west, cartographic
nrm = np.dstack([-gx, gz, np.ones_like(Hm)])                                         # gz: rows run to -Z
nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
shade = np.clip((nrm * light).sum(2), 0, 1)
img *= np.clip(1.0 + 0.16 * (shade - shade.mean()) / max(shade.std(), 1e-4), 0.72, 1.14)[..., None]

# ---- ice: the lake and the creeks (meshes in world space)
def yaml_mesh(path):
    s = open(path).read()
    fmt = int(re.search(r'm_IndexFormat: (\d+)', s).group(1))
    ib = bytes.fromhex(re.search(r'm_IndexBuffer: ([0-9a-f]+)', s).group(1))
    idx = np.frombuffer(ib, np.uint16 if fmt == 0 else np.uint32).astype(np.int64)
    vc = int(re.search(r'm_VertexCount: (\d+)', s).group(1))
    ch = re.findall(r'- stream: (\d+)\s+offset: (\d+)\s+format: (\d+)\s+dimension: (\d+)', s)
    stride = sum(int(dm) * 4 for st, of, fm, dm in ch if int(st) == 0 and int(dm) > 0)
    vd = bytes.fromhex(re.search(r'_typelessdata: ([0-9a-f]+)', s).group(1))
    v = np.frombuffer(vd[:vc * stride], np.float32).reshape(vc, stride // 4)[:, :3]
    return v, idx.reshape(-1, 3)


ice = Image.new('L', (PX, PX), 0)
dr = ImageDraw.Draw(ice)
for f in ('LakeIce.asset', 'CreekIce_NW_gorge.asset', 'CreekIce_SE.asset'):
    v, tri = yaml_mesh(f'{STREAMS}/{f}')
    for a, b, c in tri:
        pts = [((v[k, 0] - X0) / mpp, (Z0 + SIZE - v[k, 2]) / mpp) for k in (a, b, c)]
        dr.polygon(pts, fill=255)
icem = np.asarray(ice, np.float32)[..., None] / 255.0
img = img * (1 - icem) + np.array((176, 192, 204), np.float32) * icem

# ---- trees and rocks (terrain trees): crowns as discs, darker in the middle
canopy = Image.new('RGB', (PX, PX), (0, 0, 0))
mask = Image.new('L', (PX, PX), 0)
dc, dm = ImageDraw.Draw(canopy), ImageDraw.Draw(mask)
def look(n):
    m = re.search(r'(\d+)', n)
    h = float(m.group(1)) if m else 6.0
    if n.startswith(('Spruce', 'Fir')):
        return 0.17 * h, (34, 46, 38), 235
    if n.startswith('Birch'):
        return 0.20 * h, (120, 112, 98), 150
    if n.startswith(('Dead', 'Snag')):
        return 0.07 * h + 0.5, (96, 92, 86), 200
    if n.startswith('Bush'):
        return 1.3, (62, 70, 56), 200
    if n.startswith('Rock'):
        return 1.6, (128, 128, 126), 230
    if n.startswith('?'):
        return 1.1, (44, 56, 46), 200
    return 0.0, None, 0
LOOK = [look(n) for n in names]
order = []
for i in range(3):
    for j in range(3):
        Tt = d[f'Forest_TerrainData_{i}_{j}_T']
        for px_, pz_, k, wsc in Tt:
            order.append((X0 + i * TILE + px_ * TILE, Z0 + j * TILE + pz_ * TILE, int(k), float(wsc)))
for (x, z, k, wsc) in order:
    r, col, a = LOOK[k]
    if col is None or r <= 0:
        continue
    rp = max(0.5, r * wsc / mpp)
    cx, cy = (x - X0) / mpp, (Z0 + SIZE - z) / mpp
    dc.ellipse([cx - rp, cy - rp, cx + rp, cy + rp], fill=col)
    dm.ellipse([cx - rp, cy - rp, cx + rp, cy + rp], fill=a)
cm = np.asarray(mask, np.float32)[..., None] / 255.0
img = img * (1 - cm) + np.asarray(canopy, np.float32) * cm
if '--plan' in sys.argv:                                                              # for the 99 px plan: masses and lines
    from scipy import ndimage
    k = max(1, int(round(9.0 / mpp)))
    dens = ndimage.gaussian_filter(cm[..., 0], 6.0 / mpp)
    forest = np.clip((dens - 0.18) / 0.30, 0, 1)[..., None]
    snow = img * (1 - cm) + np.array((226, 230, 236), np.float32) * cm * 0.0
    base = np.where(cm > 0, np.array((226, 230, 236), np.float32), img)
    base = ndimage.uniform_filter(base, size=(k, k, 1))
    img = base * (1 - forest) + np.array((42, 56, 46), np.float32) * forest
    rd = ndimage.maximum_filter(np.clip((road - 0.35) / 0.3, 0, 1), size=2 * k + 1)[..., None]
    img = img * (1 - rd) + np.array((104, 96, 86), np.float32) * rd
    wi = ndimage.maximum_filter(icem[..., 0], size=2 * k + 1)[..., None]
    img = img * (1 - wi) + np.array((168, 186, 200), np.float32) * wi
Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8), 'RGB').save(out)
print(out, PX, 'px', round(mpp, 2), 'm/px; trees', len(order))
