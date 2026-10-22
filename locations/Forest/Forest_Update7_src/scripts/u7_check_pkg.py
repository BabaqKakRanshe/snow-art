"""Independent check of Forest_Update7.unitypackage (reads only the packages of Updates 4-7 and Update 3's raw entries).

- tar.gz with <guid>/asset, <guid>/asset.meta (guid inside = folder name), <guid>/pathname; one entry per path, all under
  Assets/Locations/Forest; folders with Update 3's GUIDs and metas
- Models/: the 22 kit models, new GUIDs (md5 of 'snow/Forest/Update7/' + path) clashing with nothing of Updates 3-6
- Textures/: 7 new T_Fence_* (new GUIDs); 9 replaced with the GUIDs Updates 4 / 5 gave them, the same size and mode as
  the files they replace, different pixels; PNGs open, _px names, <= 2048; cut-outs RGBA with holes
- Data, each in its own format (byte-exact round trip):
    Forest_Layout.json    = Update 6's except rocks (FenceChain out, the U7 records appended), trees (the u7.removed ones
                            out, nothing else), the block u7; every other key identical
    Forest_Materials.json = Update 6's list (same order and definitions) except doubleSided of the 9 cut-outs + the new
                            ones at the end
  no nested arrays (JsonUtility)
- every material of every FBX (read from the file) is defined; every texture a material of this update names is in the
  package; every texture of the package is used by a material
- the U7 records: models of the package (not the three unplaced ones), yaw-only unit quaternions, u7.records.first/count
  right; every placed model placed; u7.controls point at records with the same m / p / q
- README = Update 6's README + the section "Обновление 7", no {placeholder} left

python3 -I u7_check_pkg.py <u7.unitypackage> <u6.unitypackage> <u5.unitypackage> <u4.unitypackage> <u3raw_dir>"""
import sys, os, json, tarfile, io, re, hashlib, math
import numpy as np
from PIL import Image

pkg, u6pkg, u5pkg, u4pkg, u3raw = sys.argv[1:6]
ROOT = 'Assets/Locations/Forest'
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


F7, P7 = read_pkg(pkg, 'U7')
F6, P6 = read_pkg(u6pkg, 'U6')
F5, P5 = read_pkg(u5pkg, 'U5')
F4, P4 = read_pkg(u4pkg, 'U4')
a7 = lambda pn: F7[P7[pn]]['asset']
a6 = lambda pn: F6[P6[pn]]['asset']
u3guid = {}
for g in os.listdir(u3raw):
    p = os.path.join(u3raw, g, 'pathname')
    if os.path.exists(p):
        u3guid[open(p, encoding='utf-8').read().split('\n')[0]] = g
for pn in P7:
    if not (pn == 'Assets/Locations' or pn == ROOT or pn.startswith(ROOT + '/')):
        P.append(f'{pn}: outside {ROOT}')
for f in ('Assets/Locations', ROOT, f'{ROOT}/Models', f'{ROOT}/Textures', f'{ROOT}/Data'):
    if P7.get(f) != u3guid.get(f):
        P.append(f'folder {f}: guid {P7.get(f)} (Update 3: {u3guid.get(f)})')
older = {}
for lab, PP in (('U3', u3guid), ('U4', P4), ('U5', P5), ('U6', P6)):
    for pn, g in PP.items():
        older.setdefault(g, set()).add((lab, pn))

KIT = ['Abatis', 'Abatis_b', 'ChainFence', 'ChainFence_Torn', 'ConcreteFence', 'ConcreteFence_Broken', 'ConcreteFence_Plain',
       'ConcreteFence_Sign', 'ConcreteFence_Socket', 'ConcreteFence_Wicket', 'ConcreteFence_b', 'Hedgehog', 'RoadBlock_Cube',
       'RoadBlock_FBS', 'RoadBlock_Jersey', 'RoadBlock_Jersey_Striped', 'Sign_Halt', 'Sign_NoEntry', 'TankTooth', 'TankTooth_b',
       'WireBarricade', 'WireCoil']
models = sorted(pn.split('/')[-1][:-4] for pn in P7 if pn.startswith(f'{ROOT}/Models/'))
if models != sorted(KIT):
    P.append(f'models {models}')
for pn, g in P7.items():
    if pn.startswith(f'{ROOT}/Models/') or pn.startswith(f'{ROOT}/Textures/T_Fence_'):
        want = hashlib.md5(('snow/Forest/Update7/' + pn).encode()).hexdigest()
        if g != want:
            P.append(f'{pn}: guid {g} is not the Update 7 rule ({want})')
        if g in older:
            P.append(f'{pn}: guid {g} already used by {sorted(older[g])}')

# ---- textures
REPL = ['T_Base_ChainLink_A_px.png', 'T_Base_Barbed_A_px.png', 'T_Base_Rust_A_px.png', 'T_Kpp_ChainLink_A_px.png',
        'T_Kpp_Barbed_A_px.png', 'T_Yard_ChainLink_A_px.png', 'T_Yard_Barbed_A_px.png', 'T_Road_ChainLink_A_px.png',
        'T_Road_Barbed_A_px.png']
tex = sorted(pn.split('/')[-1] for pn in P7 if pn.startswith(f'{ROOT}/Textures/'))
new_tex = [t for t in tex if t.startswith('T_Fence_')]
if sorted(set(tex) - set(new_tex)) != sorted(REPL):
    P.append(f'replaced textures {sorted(set(tex) - set(new_tex))}')
if len(new_tex) != 7:
    P.append(f'new textures {new_tex}')
img = {}
for t in tex:
    pn = f'{ROOT}/Textures/{t}'
    if not re.fullmatch(r'T_[A-Za-z0-9]+_[A-Za-z0-9]+_[AE]_px\.png', t):
        P.append(f'{t}: name')
    im = Image.open(io.BytesIO(a7(pn)))
    im.load()
    img[t] = im
    if max(im.size) > 2048:
        P.append(f'{t}: {im.size}')
    if t in REPL:
        src = (F5, P5) if t.startswith('T_Base_') else (F4, P4)
        g_old = src[1].get(pn)
        if g_old is None:
            P.append(f'{t}: not in Update {5 if t.startswith("T_Base_") else 4}')
            continue
        if P7[pn] != g_old:
            P.append(f'{t}: guid {P7[pn]} != {g_old} (Update 4/5)')
        old = Image.open(io.BytesIO(src[0][g_old]['asset']))
        if old.size != im.size or old.mode != im.mode:
            P.append(f'{t}: {im.size} {im.mode} replaces {old.size} {old.mode}')
        if np.array_equal(np.asarray(old), np.asarray(im)):
            P.append(f'{t}: same pixels as before')
cut = [t for t in tex if any(k in t for k in ('ChainLink', 'Barbed', 'Rust', 'Razor'))]
for t in cut:
    a = np.asarray(img[t].convert('RGBA'))[..., 3]
    if img[t].mode != 'RGBA' or not (a.min() < 128 < a.max()):
        P.append(f'{t}: not a cut-out (mode {img[t].mode}, alpha {a.min()}..{a.max()})')

# ---- data


def data(name, dump):
    pn = f'{ROOT}/Data/{name}'
    raw7, raw6 = a7(pn).decode('utf-8'), a6(pn).decode('utf-8')
    o7, o6 = json.loads(raw7), json.loads(raw6)
    if dump(o7) != raw7:
        P.append(f'{name}: not in its own format')
    if P7[pn] != u3guid.get(pn):
        P.append(f'{name}: guid')
    return o7, o6


def nested(o, path='$'):
    if isinstance(o, list):
        for i, x in enumerate(o):
            if isinstance(x, list):
                P.append(f'nested array at {path}[{i}]')
                return
            nested(x, f'{path}[{i}]')
    elif isinstance(o, dict):
        for k, v in o.items():
            nested(v, f'{path}.{k}')


L7, L6 = data('Forest_Layout.json', lambda o: json.dumps(o, separators=(',', ':')))
M7, M6 = data('Forest_Materials.json', lambda o: json.dumps(o, indent=1))
nested(L7)
nested(M7)
for k in set(L6) | set(L7):
    if k in ('rocks', 'trees', 'u7'):
        continue
    if L6.get(k) != L7.get(k):
        P.append(f'Forest_Layout.json: {k} differs from Update 6')
u7 = L7.get('u7', {})
first, count = u7['records']['first'], u7['records']['count']
r6 = [r for r in L6['rocks'] if r['m'] != 'FenceChain']
if len(L6['rocks']) - len(r6) != 213:
    P.append(f'Update 6 had {len(L6["rocks"]) - len(r6)} FenceChain')
if L7['rocks'][:first] != r6 or first != len(r6):
    P.append('rocks before the U7 records differ from Update 6 without FenceChain')
if len(L7['rocks']) != first + count:
    P.append(f'rocks: {len(L7["rocks"])} != first + count')
if any(r['m'] == 'FenceChain' for r in L7['rocks']):
    P.append('FenceChain still in rocks')
rem = [x for x in u7['removed'] if x['list'] == 'trees']
key = lambda t: (t['m'], tuple(t['p']))
t6 = [key(t) for t in L6['trees']]
t7 = [key(t) for t in L7['trees']]
gone = set(t6) - set(t7)
if gone != {key(t) for t in rem} or len(t6) - len(t7) != len(rem) or [t for t in t6 if t not in gone] != t7:
    P.append(f'trees: {len(t6) - len(t7)} gone, u7.removed lists {len(rem)}')
rf = [x for x in u7['removed'] if x['list'] == 'rocks']
if len(rf) != 213 or any(x['m'] != 'FenceChain' for x in rf):
    P.append('u7.removed rocks')
recs = L7['rocks'][first:]
placed = set()
for i, r in enumerate(recs):
    if set(r) != {'m', 'p', 'q'}:
        P.append(f'U7 record {i}: keys {sorted(r)}')
    if r['m'] not in KIT or r['m'] in u7['unplaced']:
        P.append(f'U7 record {i}: model {r["m"]}')
    q = r['q']
    if abs(q[0]) > 1e-9 or abs(q[2]) > 1e-9 or abs(math.hypot(q[1], q[3]) - 1) > 2e-6:
        P.append(f'U7 record {i}: q {q}')
    placed.add(r['m'])
if sorted(placed | set(u7['unplaced'])) != sorted(KIT):
    P.append(f'placed {sorted(placed)} + unplaced {u7["unplaced"]} != the kit')
for c in u7['controls']:
    r = L7['rocks'][c['index']]
    if r['m'] != c['m'] or r['p'] != c['p'] or r['q'] != c['q']:
        P.append(f'control {c["what"]}: record differs')
if sorted(u7['added']) != sorted(KIT):
    P.append('u7.added')
# materials
n6 = [m['name'] for m in M6['materials']]
n7 = [m['name'] for m in M7['materials']]
if n7[:len(n6)] != n6:
    P.append('materials: Update 6 order changed')
ONE = {'M_Base_ChainLink', 'M_Base_Barbed', 'M_Base_Rust', 'M_Kpp_ChainLink', 'M_Kpp_Barbed', 'M_Yard_ChainLink', 'M_Yard_Barbed',
       'M_Road_ChainLink', 'M_Road_Barbed'}
for m6, m7 in zip(M6['materials'], M7['materials']):
    if m6['name'] in ONE:
        d = {k for k in set(m6) | set(m7) if m6.get(k) != m7.get(k)}
        if d != {'doubleSided'} or m7['doubleSided'] is not False:
            P.append(f'{m6["name"]}: changed {sorted(d)}')
    elif m6 != m7:
        P.append(f'{m6["name"]}: changed')
newm = M7['materials'][len(n6):]
defined = {m['name']: m for m in M7['materials']}
for m in newm:
    for f in ('albedo', 'emissionMap'):
        t = m.get(f)
        if t and t not in tex:
            P.append(f'{m["name"]}: {f} {t} not in the package')
used_tex = {m.get(f) for m in newm for f in ('albedo', 'emissionMap')} | {defined[n]['albedo'] for n in ONE}
for t in tex:
    if t not in used_tex:
        P.append(f'{t}: no material uses it')
for m in newm:
    if m['type'] == 'cutout' and m['doubleSided']:
        P.append(f'{m["name"]}: a two-sided cut-out')
# ---- FBX materials (from the files)
for nm in KIT:
    raw = a7(f'{ROOT}/Models/{nm}.fbx')
    mats = sorted(set(x.decode() for x in re.findall(rb'(M_[A-Za-z0-9_]+)\x00\x01Material', raw)))
    if not mats:
        P.append(f'{nm}.fbx: no materials found')
    for m in mats:
        if m not in defined:
            P.append(f'{nm}.fbx: material {m} not defined')
# ---- README
r7, r6 = a7(f'{ROOT}/README.md').decode('utf-8'), a6(f'{ROOT}/README.md').decode('utf-8')
if not r7.startswith(r6.rstrip('\n')) or '## Обновление 7' not in r7[len(r6.rstrip()):]:
    P.append('README: not Update 6\'s + the section')
if re.search(r'\{[a-z_0-9]+\}', r7[len(r6.rstrip()):]):
    P.append('README: a placeholder is left')
print('entries', len(P7), 'models', len(models), 'textures', len(tex), 'U7 records', count, 'trees out', len(rem))
print('PROBLEMS', len(P))
for p in P:
    print('  ', p)
