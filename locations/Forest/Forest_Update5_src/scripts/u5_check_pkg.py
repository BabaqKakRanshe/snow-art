"""Independent check of Forest_Update5.unitypackage (reads only the package, Update 4's package and Update 3's files).

- tar.gz with <guid>/asset, <guid>/asset.meta (guid inside = folder name), <guid>/pathname; one entry per path
- the 25 models of the base and the far points, nothing else in Models/
- GUIDs of replaced files = Update 3's (or the project's for LogPile, FenceChain, OldFence a / b / c, Forest_Wires);
  Data and README = Update 3's GUIDs; new textures unique (also against Update 4's package)
- Data JSON parses, is Update 4's plus the block u5 only (every other key and value equal); interactables, lights and halos
  of the 25 models equal Update 3's; materials = Update 4's list (same order, same definitions) + new ones at the end
- every material of every FBX is defined in Forest_Materials.json; every texture a new definition names is in the package or
  in Update 3's / Update 4's / the project's texture names; every texture of the package is used
- every layout reference of the replaced models (interactables, drives, lighting.assign, light / halo fixtures) is a node
  of its FBX; flicker and power materials are defined; every model is placed (prefabs, rocks or worldModels)
- PNGs open, PSX names end with _px, cut-outs carry alpha with holes, sizes <= 2048
- README = Update 4's README + the section "Обновление 5"

python3 -I u5_check_pkg.py <package> <u4_package> <u3_dir> <u3raw_dir> <project_textures.txt>"""
import sys, os, json, tarfile, io, re
import numpy as np
from PIL import Image

pkg, u4pkg, u3_dir, u3raw, projtex = sys.argv[1:6]
ROOT = 'Assets/Locations/Forest'
MODELS = ['Hatch', 'Crates', 'LogPile', 'LightPole', 'PowerPole', 'FenceChain', 'OldFence', 'OldFence_b', 'OldFence_c',
          'Helipad', 'RadioMast', 'Forest_Wires', 'Dish_1', 'Dish_2', 'Dish_3', 'Dish_4', 'Dish_5', 'Radome', 'RelayMast',
          'MeteoStation', 'LookoutTower', 'PumpHouse', 'Chapel', 'Cabin', 'Campsite']
P = []


def read_pkg(path, label):
    t = tarfile.open(path, 'r:gz')
    files = {}
    for m in t.getmembers():
        if not m.isfile():
            P.append(f'{label}: non-file member {m.name}')
            continue
        g, part = m.name.split('/')
        files.setdefault(g, {})[part] = t.extractfile(m).read()
    paths = {}
    for g, d in files.items():
        if 'pathname' not in d or 'asset.meta' not in d:
            P.append(f'{label} {g}: incomplete entry {sorted(d)}')
            continue
        pn = d['pathname'].decode('utf-8')
        if pn in paths:
            P.append(f'{label}: duplicate path {pn}')
        paths[pn] = g
        meta = d['asset.meta'].decode('utf-8')
        if f'guid: {g}' not in meta:
            P.append(f'{label} {pn}: meta guid differs from entry {g}')
        if not re.fullmatch(r'[0-9a-f]{32}', g):
            P.append(f'{label} {pn}: bad guid {g}')
        if 'asset' not in d and 'folderAsset: yes' not in meta:
            P.append(f'{label} {pn}: no asset and not a folder')
    return files, paths


files, paths = read_pkg(pkg, 'U5')
files4, paths4 = read_pkg(u4pkg, 'U4')
for pn in paths:
    if not (pn == 'Assets/Locations' or pn == ROOT or pn.startswith(ROOT + '/')):
        P.append(f'{pn}: outside {ROOT}')
models = sorted(pn.split('/')[-1][:-4] for pn in paths if pn.startswith(f'{ROOT}/Models/') and pn.endswith('.fbx'))
if models != sorted(MODELS):
    P.append(f'models: missing {sorted(set(MODELS) - set(models))}, extra {sorted(set(models) - set(MODELS))}')
for pn in paths:
    if pn.startswith(f'{ROOT}/Models/') and not pn.endswith('.fbx'):
        P.append(f'{pn}: not an FBX in Models/')

# ---- GUIDs
u3guid = {}
for g in os.listdir(u3raw):
    p = os.path.join(u3raw, g, 'pathname')
    if os.path.exists(p):
        u3guid[open(p, encoding='utf-8').read().split('\n')[0]] = g
project_guid = {f'{ROOT}/Models/LogPile.fbx': 'b411e328025cb9beb4936a7f23ebd90a',
                f'{ROOT}/Models/FenceChain.fbx': 'c52efb2f488b20e32e445ef687cda2e5',
                f'{ROOT}/Models/OldFence.fbx': 'cff14cd3e0248e29ff56ae8be6fdb848',
                f'{ROOT}/Models/OldFence_b.fbx': 'bd0b65a000303e2d3c2a881bfd563359',
                f'{ROOT}/Models/OldFence_c.fbx': '2a58e2b49ad5d9ef588498bcd9d5cce4',
                f'{ROOT}/Models/Forest_Wires.fbx': '62a9c3400b37253c3e9e21007ec48caf',
                f'{ROOT}/Models/EuroPost.fbx': '47ee0862def446e696f77605525628d5',
                f'{ROOT}/Models/FallenTree.fbx': 'ee4e1164bd4e27d5104894280c7bbfd7',
                f'{ROOT}/Models/LogCut.fbx': '1a0d28a5db802f234ea2f37cefe53e59'}
known = dict(u3guid, **project_guid)
for pn, g in paths4.items():                 # Update 4's new files (its textures)
    known.setdefault(pn, g)
for pn, g in paths.items():
    if pn in known and known[pn] != g:
        P.append(f'{pn}: GUID {g} differs from the existing {known[pn]}')
    if pn not in known and g in set(known.values()):
        P.append(f'{pn}: new file reuses an existing GUID {g}')
    if pn.startswith(f'{ROOT}/Models/') and pn not in known:
        P.append(f'{pn}: model without a known GUID')
    if pn.startswith(f'{ROOT}/Textures/') and pn in known:
        P.append(f'{pn}: texture replaces an existing file')

asset = lambda pn: files[paths[pn]]['asset']
asset4 = lambda pn: files4[paths4[pn]]['asset']
# ---- data
L = json.loads(asset(f'{ROOT}/Data/Forest_Layout.json'))
M = json.loads(asset(f'{ROOT}/Data/Forest_Materials.json'))
L4 = json.loads(asset4(f'{ROOT}/Data/Forest_Layout.json'))
M4 = json.loads(asset4(f'{ROOT}/Data/Forest_Materials.json'))
L3 = json.load(open(os.path.join(u3_dir, ROOT, 'Data/Forest_Layout.json')))
for k in set(L) | set(L4):
    if L.get(k) != L4.get(k) and k != 'u5':
        P.append(f'layout key {k} changed against Update 4')
if 'u5' not in L or sorted(L['u5'].get('replaced', [])) != sorted(MODELS) or L['u5'].get('changes'):
    P.append(f'layout u5 block: {L.get("u5")}')
same3 = 0
for k in ('prefabLights', 'prefabGlows', 'interactables'):
    a = [x for x in L[k] if x['model'] in MODELS]
    b = [x for x in L3[k] if x['model'] in MODELS]
    if a != b:
        P.append(f'{k} of the 25 models differ from Update 3')
    same3 += len(a)
mat4 = {m['name']: m for m in M4['materials']}
mat = {m['name']: m for m in M['materials']}
if M['materials'][:len(M4['materials'])] != M4['materials']:
    P.append('materials: Update 4 part changed (order or definitions)')
if set(M) != set(M4) or any(M[k] != M4[k] for k in M if k != 'materials'):
    P.append('materials file: keys other than the list changed')
new = [m['name'] for m in M['materials'][len(M4['materials']):]]
for n in new:
    if not re.fullmatch(r'M_(Base|Far)_\w+', n):
        P.append(f'new material {n}: unexpected name')
if len(set(m['name'] for m in M['materials'])) != len(M['materials']):
    P.append('materials: duplicate names')

# ---- textures
tex_in_pkg = {pn.split('/')[-1] for pn in paths if pn.startswith(f'{ROOT}/Textures/') and pn.endswith('.png')}
u3tex = {pn.split('/')[-1] for pn in u3guid if pn.startswith(f'{ROOT}/Textures/')}
u4tex = {pn.split('/')[-1] for pn in paths4 if pn.startswith(f'{ROOT}/Textures/')}
proj = {l.strip() for l in open(projtex) if l.strip()}
for n in new:
    s = mat[n]
    for key in ('albedo', 'emissionMap', 'mask', 'normal'):
        f = s.get(key) or ''
        if f and f not in tex_in_pkg | u3tex | u4tex | proj:
            P.append(f'material {n}: {key} {f} not found')
used_tex = {m.get(key) for m in M['materials'] for key in ('albedo', 'emissionMap', 'mask', 'normal')}
for f in sorted(tex_in_pkg - used_tex):
    P.append(f'texture {f}: no material uses it')
tex_info = {}
for pn in paths:
    if pn.startswith(f'{ROOT}/Textures/') and pn.endswith('.png'):
        im = Image.open(io.BytesIO(asset(pn)))
        im.load()
        name = pn.split('/')[-1][:-4]
        tex_info[name] = (im.size, im.mode)
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
tmp = os.path.join(os.path.dirname(os.path.abspath(pkg)), '_check_fbx.fbx')
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
    if name not in nodes:
        P.append(f'{name}: no root node of its name')
    fbx_nodes[name], fbx_mats[name] = nodes, mats
    for m in mats:
        if m not in mat:
            P.append(f'{name}: material {m} is not in Forest_Materials.json')
os.remove(tmp)
used_mats = {m for s in fbx_mats.values() for m in s}
for n in new:
    if n not in used_mats:
        P.append(f'new material {n}: no FBX uses it')
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
placed = {p['m'] for p in L['prefabs']} | {p['m'] for p in L['rocks']} | set(L['worldModels'])
count = {}
for p in L['prefabs'] + L['rocks']:
    count[p['m']] = count.get(p['m'], 0) + 1
for name in fbx_nodes:
    if name not in placed:
        P.append(f'{name}: not placed in the layout')

# ---- README
r4 = asset4(f'{ROOT}/README.md').decode('utf-8').rstrip('\n')
r5 = asset(f'{ROOT}/README.md').decode('utf-8')
if not r5.startswith(r4) or '## Обновление 5' not in r5[len(r4):]:
    P.append('README: not Update 4\'s README + the section "Обновление 5"')
if '{' in r5[len(r4):] and re.search(r'\{[a-z_]+\}', r5[len(r4):]):
    P.append('README: unfilled placeholder')

print(f'entries {len(paths)}: {len(models)} FBX, {len(tex_in_pkg)} PNG, '
      f'{sum(1 for p in paths if p.endswith(".json"))} JSON, README {int(f"{ROOT}/README.md" in paths)}')
print('placements:', {m: count.get(m, 0) for m in MODELS if m != 'Forest_Wires'}, 'Forest_Wires in worldModels:',
      'Forest_Wires' in L['worldModels'])
print('Update 3 entries kept for the 25 models (lights, halos, interactables):', same3)
print('materials: new', len(new), new)
print('textures:', {k: v for k, v in sorted(tex_info.items())})
print('PROBLEMS', len(P))
for p in P:
    print('  ', p)
