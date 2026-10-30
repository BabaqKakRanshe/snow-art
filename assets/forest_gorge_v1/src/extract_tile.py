"""current tile 0_2: heights (full), trees, splat, prototype externals"""
import UnityPy, sys, json
import numpy as np
from PIL import Image
P, OUT = sys.argv[1], sys.argv[2]
X0, Z0, TILE, OY, SY = -600.0, 0.0, 600.0, -84.0, 136.0
env = UnityPy.load(P)
td = None; tex = {}
for obj in env.objects:
    if obj.type.name == 'TerrainData': td = obj
    elif obj.type.name == 'Texture2D': tex[obj.path_id] = obj
tt = td.read_typetree()
hm = tt['m_Heightmap']; R = hm['m_Resolution']
H = OY + SY * (np.array(hm['m_Heights'], dtype=np.int32).reshape(R, R).astype(np.float64) / 32766.0)
np.save(OUT + '/tile_h.npy', H.astype(np.float32))
trees = []
for t in tt['m_DetailDatabase']['m_TreeInstances']:
    p = t['position']
    trees.append([X0 + p['x'] * TILE, OY + p['y'] * SY, Z0 + p['z'] * TILE, t['widthScale'], t['heightScale'], t['rotation'], t['index']])
np.save(OUT + '/tile_trees.npy', np.array(trees, np.float64))
protos = [dict(fid=p['prefab']['m_FileID'], pid=p['prefab']['m_PathID']) for p in tt['m_DetailDatabase']['m_TreePrototypes']]
ext = []
for e in td.assets_file.externals:
    g = e.guid
    gh = g.hex() if hasattr(g, 'hex') else str(g)
    ext.append(gh)
layers = [dict(fid=l['m_FileID'], pid=l['m_PathID']) for l in tt['m_SplatDatabase']['m_TerrainLayers']]
ar = tt['m_SplatDatabase']['m_AlphamapResolution']
spl = []
for k, a in enumerate(tt['m_SplatDatabase']['m_AlphaTextures']):
    t = tex.get(a['m_PathID'])
    arr = np.asarray(t.read().image)[::-1]          # rows = z bottom-up
    spl.append(arr)
np.save(OUT + '/tile_splat.npy', np.concatenate(spl, -1))
json.dump(dict(res=R, alpha_res=ar, protos=protos, externals=ext, layers=layers, ntrees=len(trees)), open(OUT + '/tile_meta.json', 'w'))
print('res', R, 'alpha', ar, 'trees', len(trees), 'protos', len(protos), 'h', H.min(), H.max(), 'splat', [s.shape for s in spl])
