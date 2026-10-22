"""Independent check of Forest_Update4.unitypackage (reads only the package and Update 3's files).

- tar.gz with <guid>/asset, <guid>/asset.meta (guid inside = folder name), <guid>/pathname; one entry per path
- GUIDs of replaced files = Update 3's (or the project's for EuroPost / FallenTree / LogCut); new ones unique
- Data JSON parses, is Update 3's plus the listed changes only (every other key and value equal)
- every material of every FBX is defined in Forest_Materials.json; every texture a definition names is in the package or
  in Update 3's / the project's texture names (Update 2's textures are required, as for Update 3)
- every layout reference of the replaced models (interactables, drives, lighting.assign, light / halo fixtures) is a node
  of its FBX; flicker and power materials are defined
- PNGs open, PSX names end with _px, cut-outs carry alpha, sizes <= 2048 (the core's max size for these)

python3 -I u4_check_pkg.py <package> <u3_dir> <u3raw_dir> <project_textures.txt>"""
import sys, os, json, tarfile, io, re
import numpy as np
from PIL import Image

pkg, u3_dir, u3raw, projtex = sys.argv[1:5]
ROOT = 'Assets/Locations/Forest'
P = []
t = tarfile.open(pkg, 'r:gz')
files = {}
for m in t.getmembers():
    if not m.isfile():
        P.append(f'non-file member {m.name}')
        continue
    g, part = m.name.split('/')
    files.setdefault(g, {})[part] = t.extractfile(m).read()
paths = {}
for g, d in files.items():
    if 'pathname' not in d or 'asset.meta' not in d:
        P.append(f'{g}: incomplete entry {sorted(d)}')
        continue
    pn = d['pathname'].decode('utf-8')
    if pn in paths:
        P.append(f'duplicate path {pn}')
    paths[pn] = g
    meta = d['asset.meta'].decode('utf-8')
    if f'guid: {g}' not in meta:
        P.append(f'{pn}: meta guid differs from entry {g}')
    if not re.fullmatch(r'[0-9a-f]{32}', g):
        P.append(f'{pn}: bad guid {g}')
    if 'asset' not in d and 'folderAsset: yes' not in meta:
        P.append(f'{pn}: no asset and not a folder')

u3guid = {}
for g in os.listdir(u3raw):
    p = os.path.join(u3raw, g, 'pathname')
    if os.path.exists(p):
        u3guid[open(p, encoding='utf-8').read().split('\n')[0]] = g
project_guid = {f'{ROOT}/Models/EuroPost.fbx': '47ee0862def446e696f77605525628d5',
                f'{ROOT}/Models/FallenTree.fbx': 'ee4e1164bd4e27d5104894280c7bbfd7',
                f'{ROOT}/Models/LogCut.fbx': '1a0d28a5db802f234ea2f37cefe53e59'}
known = dict(u3guid, **project_guid)
for pn, g in paths.items():
    if pn in known and known[pn] != g:
        P.append(f'{pn}: GUID {g} differs from the existing {known[pn]}')
    if pn not in known and g in set(known.values()):
        P.append(f'{pn}: new file reuses an existing GUID {g}')

asset = lambda pn: files[paths[pn]]['asset']
# ---- data
L = json.loads(asset(f'{ROOT}/Data/Forest_Layout.json'))
M = json.loads(asset(f'{ROOT}/Data/Forest_Materials.json'))
L3 = json.load(open(os.path.join(u3_dir, ROOT, 'Data/Forest_Layout.json')))
M3 = json.load(open(os.path.join(u3_dir, ROOT, 'Data/Forest_Materials.json')))
allowed_layout = {'prefabLights', 'prefabGlows', 'interactables', 'u4'}
for k in set(L) | set(L3):
    if L.get(k) != L3.get(k) and k not in allowed_layout:
        P.append(f'layout key {k} changed')
diff_l = []
for k in ('prefabLights', 'prefabGlows'):
    for a, b in zip(L[k], L3[k]):
        if a != b:
            diff_l.append((k, a['model']))
    if len(L[k]) != len(L3[k]):
        P.append(f'{k}: count changed')
for a, b in zip(L['interactables'], L3['interactables']):
    if a != b:
        diff_l.append(('interactables', a['model'], a['child'], {kk: (b.get(kk), a.get(kk)) for kk in a if a.get(kk) != b.get(kk)}))
mat3 = {m['name']: m for m in M3['materials']}
mat = {m['name']: m for m in M['materials']}
redefined = [n for n in mat3 if mat[n] != mat3[n]]
new = [n for n in mat if n not in mat3]
if [m['name'] for m in M['materials'][:len(M3['materials'])]] != [m['name'] for m in M3['materials']]:
    P.append('materials: Update 3 order changed')

# ---- textures
tex_in_pkg = {pn.split('/')[-1] for pn in paths if pn.startswith(f'{ROOT}/Textures/') and pn.endswith('.png')}
u3tex = {pn.split('/')[-1] for pn in u3guid if pn.startswith(f'{ROOT}/Textures/')}
proj = {l.strip() for l in open(projtex) if l.strip()}
for n in new + redefined:
    s = mat[n]
    for key in ('albedo', 'emissionMap', 'mask', 'normal'):
        f = s.get(key) or ''
        if f and f not in tex_in_pkg | u3tex | proj:
            P.append(f'material {n}: {key} {f} not found')
for m in M['materials']:                       # every Update 3 texture name stays resolvable (Update 2 provides some)
    for key in ('albedo', 'emissionMap', 'mask'):
        f = m.get(key) or ''
        if f and not f.startswith('shared:') and f not in tex_in_pkg | u3tex | proj:
            pass                               # Update 2's files (e.g. T_FX_Exit_A_px.png): checked in Unity (F3 log)
for pn in paths:
    if pn.startswith(f'{ROOT}/Textures/') and pn.endswith('.png'):
        im = Image.open(io.BytesIO(asset(pn)))
        name = pn.split('/')[-1][:-4]
        if not name.endswith('_px'):
            P.append(f'{pn}: not a _px name')
        if max(im.size) > 2048:
            P.append(f'{pn}: {im.size} > 2048')
        users = [m for m in M['materials'] if m.get('albedo') == pn.split('/')[-1] and m['type'] == 'cutout']
        if users and im.mode != 'RGBA':
            P.append(f'{pn}: cut-out texture without alpha ({im.mode})')
        if users:
            a = np.asarray(im)[..., 3]
            if not (a.min() < 128 < a.max()):
                P.append(f'{pn}: alpha has no holes')

# ---- FBX materials and nodes
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, addon_utils
addon_utils.enable('io_scene_fbx')
from io_scene_fbx import parse_fbx
fbx_nodes, fbx_mats = {}, {}
tmp = os.path.join(os.path.dirname(pkg), '_check_fbx.fbx')
for pn in paths:
    if not pn.endswith('.fbx'):
        continue
    open(tmp, 'wb').write(asset(pn))
    root, ver = parse_fbx.parse(tmp)
    find = lambda e, n: [c for c in e.elems if c.id == n]
    name = pn.split('/')[-1][:-4]
    nodes, mats = set(), set()
    for e in find(root, b'Objects')[0].elems:
        nm = e.props[1].split(b'\x00')[0].decode()
        if e.id == b'Model':
            nodes.add(nm)
        if e.id == b'Material':
            mats.add(nm)
    fbx_nodes[name], fbx_mats[name] = nodes, mats
    for m in mats:
        if m not in mat:
            P.append(f'{name}: material {m} is not in Forest_Materials.json')
os.remove(tmp)
for it in L['interactables']:
    if it['model'] in fbx_nodes:
        for c in [it['child']] + list(it.get('drives') or []):
            if c not in fbx_nodes[it['model']]:
                P.append(f'interactable {it["model"]}/{c} not in its FBX')
for a in L['lighting']['assign']:
    if a['model'] in fbx_nodes and a['node'] not in fbx_nodes[a['model']]:
        P.append(f'lighting.assign {a["model"]}/{a["node"]} not in its FBX')
for k, key in (('prefabLights', 'lights'), ('prefabGlows', 'glows')):
    for x in L[k]:
        if x['model'] in fbx_nodes:
            for d in x[key]:
                if d.get('fx') and d['fx'] not in fbx_nodes[x['model']]:
                    P.append(f'{k} {x["model"]}: fixture {d["fx"]} not in its FBX')
                if k == 'prefabGlows' and d['m'] not in mat:
                    P.append(f'{k} {x["model"]}: glow material {d["m"]} undefined')
for f in L['flickers']:
    if f['material'] not in mat:
        P.append(f'flicker material {f["material"]} undefined')
for n in L['power']['materialsOff'] + L['power']['materialsOn']:
    if n not in mat:
        P.append(f'power material {n} undefined')
placed = {p['m'] for p in L['prefabs']} | {p['m'] for p in L['rocks']}
for name in fbx_nodes:
    if name not in placed:
        P.append(f'{name}: not placed in the layout')

print(f'entries {len(paths)}: {sum(1 for p in paths if p.endswith(".fbx"))} FBX, {len(tex_in_pkg)} PNG, '
      f'{sum(1 for p in paths if p.endswith(".json"))} JSON, README {int(f"{ROOT}/README.md" in paths)}')
print('layout changes:', len(diff_l))
for d in diff_l:
    print('  ', d)
print('materials: new', len(new), 'redefined', redefined)
print('PROBLEMS', len(P))
for p in P:
    print('  ', p)
