"""Independent check of Forest_Update6.unitypackage (reads only the package, Update 5's package and Update 3's files).

- tar.gz with <guid>/asset, <guid>/asset.meta (guid inside = folder name), <guid>/pathname; one entry per path, all
  under Assets/Locations/Forest
- Models/: GenContainer + the 83 items of Update 3 with Update 3's GUIDs, Item_RadioSet and Apparition with new GUIDs;
  nothing else; Data and README with Update 3's GUIDs; new textures do not replace any file of Updates 3 - 5
- Data, each in its file's own format (byte-exact round trip):
    Forest_Layout.json   = Update 5's except the GenContainer's prefabLights / prefabGlows entries, its interactables'
                           axis / min / max, the viewpoint GenContainer (p, target, fov), noColliderPrefixes + Apparition,
                           the block u6
    Forest_Materials.json = Update 5's list (same order, same definitions) + the new ones at the end
    Forest_Opening.json  = Update 3's except Gen_FillNeck (neck, stand, label, capacityL), the new keys of the scares
                           X02_Crossing.figure, X03_BackSeat.figure, X08_Radio.radio, and Note_GenProcedure's p / q (on
                           the new genset panel top, recomputed here from the container's place)
    Forest_Items.json    = Update 3's except the tris fields + Item_RadioSet at the end
    Forest_Dressing.json = Update 3's + one prop (Leitstand_RadioSet_1) appended at the end
    Forest_Notes.json    = Update 3's except the de / ru texts of gen_procedure (DIESEL, the start key, 100 l / 28 h)
  every list is a list of objects or of numbers / strings (JsonUtility: no nested arrays)
- every material of every FBX is defined; every texture a new material names is in the package or Update 3 / 5;
  every texture of the package is used; PNGs open, _px names, <= 2048
- the GenContainer's interactables are nodes of its FBX; its lights / halos carry the power tag; every catalog model has
  an FBX (package or Update 3); the radio prop's model is in the catalog; Apparition is skinned (LimbNodes, 4 takes)
- README = Update 5's README + the section "Обновление 6"

python3 -I u6_check_pkg.py <package> <u5_package> <u3_dir> <u3raw_dir>"""
import math, sys, os, json, tarfile, io, re
import numpy as np
from PIL import Image

pkg, u5pkg, u3_dir, u3raw = sys.argv[1:5]
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


files, paths = read_pkg(pkg, 'U6')
files5, paths5 = read_pkg(u5pkg, 'U5')
asset = lambda pn: files[paths[pn]]['asset']
asset5 = lambda pn: files5[paths5[pn]]['asset']
for pn in paths:
    if not (pn == 'Assets/Locations' or pn == ROOT or pn.startswith(ROOT + '/')):
        P.append(f'{pn}: outside {ROOT}')

u3guid = {}
for g in os.listdir(u3raw):
    p = os.path.join(u3raw, g, 'pathname')
    if os.path.exists(p):
        u3guid[open(p, encoding='utf-8').read().split('\n')[0]] = g
I3 = json.load(open(os.path.join(u3_dir, ROOT, 'Data/Forest_Items.json'), encoding='utf-8'))
ITEMS3 = sorted(e['model'] for e in I3['items'])
WANT = sorted(['GenContainer', 'Item_RadioSet', 'Apparition'] + ITEMS3)
models = sorted(pn.split('/')[-1][:-4] for pn in paths if pn.startswith(f'{ROOT}/Models/'))
if models != WANT:
    P.append(f'models: missing {sorted(set(WANT) - set(models))}, extra {sorted(set(models) - set(WANT))}')
for pn in paths:
    if pn.startswith(f'{ROOT}/Models/') and not pn.endswith('.fbx'):
        P.append(f'{pn}: not an FBX')

# ---- GUIDs
known = dict(u3guid)
for pn, g in paths5.items():
    known.setdefault(pn, g)
for pn, g in paths.items():
    if pn in known and known[pn] != g:
        P.append(f'{pn}: GUID {g} differs from the existing {known[pn]}')
    if pn not in known and g in set(known.values()):
        P.append(f'{pn}: new file reuses an existing GUID {g}')
    name = pn.split('/')[-1][:-4]
    if pn.startswith(f'{ROOT}/Models/'):
        if name in ('Item_RadioSet', 'Apparition'):
            if pn in known:
                P.append(f'{pn}: a new model replaces an existing file')
        elif pn not in u3guid:
            P.append(f'{pn}: replaced model without Update 3\'s GUID')
    if pn.startswith(f'{ROOT}/Textures/') and pn in known:
        P.append(f'{pn}: texture replaces an existing file')
    if pn.startswith(f'{ROOT}/Data/') or pn == f'{ROOT}/README.md':
        if pn not in u3guid:
            P.append(f'{pn}: data file without Update 3\'s GUID')


# ---- data: formats
def fmt(pn, dump):
    raw = asset(pn).decode('utf-8')
    obj = json.loads(raw)
    if dump(obj) != raw:
        P.append(f'{pn}: not in its file\'s format')
    return obj


D_COMPACT = lambda o: json.dumps(o, separators=(',', ':'))
D_IND1 = lambda o: json.dumps(o, indent=1)
D_IND1U = lambda o: json.dumps(o, indent=1, ensure_ascii=False)
L = fmt(f'{ROOT}/Data/Forest_Layout.json', D_COMPACT)
M = fmt(f'{ROOT}/Data/Forest_Materials.json', D_IND1)
O = fmt(f'{ROOT}/Data/Forest_Opening.json', D_IND1U)
I = fmt(f'{ROOT}/Data/Forest_Items.json', D_IND1U)
Dr = fmt(f'{ROOT}/Data/Forest_Dressing.json', D_IND1U)
Nt = fmt(f'{ROOT}/Data/Forest_Notes.json', D_IND1U)
N3 = json.load(open(os.path.join(u3_dir, ROOT, 'Data/Forest_Notes.json'), encoding='utf-8'))
L5 = json.loads(asset5(f'{ROOT}/Data/Forest_Layout.json'))
M5 = json.loads(asset5(f'{ROOT}/Data/Forest_Materials.json'))
O3 = json.load(open(os.path.join(u3_dir, ROOT, 'Data/Forest_Opening.json'), encoding='utf-8'))
D3 = json.load(open(os.path.join(u3_dir, ROOT, 'Data/Forest_Dressing.json'), encoding='utf-8'))


def nested(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            nested(v, f'{path}.{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, list):
                P.append(f'nested array at {path}[{i}]')
            nested(v, f'{path}[{i}]')


for nm, o in (('Opening', O), ('Items', I), ('Dressing', Dr)):
    nested(o, nm)

# layout
for k in set(L) | set(L5):
    if k in ('u6', 'prefabLights', 'prefabGlows', 'interactables', 'viewpoints', 'noColliderPrefixes'):
        continue
    if L.get(k) != L5.get(k):
        P.append(f'layout key {k} changed against Update 5')
for k in ('prefabLights', 'prefabGlows'):
    a = [x for x in L[k] if x['model'] != 'GenContainer']
    b = [x for x in L5[k] if x['model'] != 'GenContainer']
    if a != b:
        P.append(f'{k}: entries of other models changed')
    if [x['model'] for x in L[k]] != [x['model'] for x in L5[k]]:
        P.append(f'{k}: order or set of models changed')
gl = next(x for x in L['prefabLights'] if x['model'] == 'GenContainer')['lights']
gg = next(x for x in L['prefabGlows'] if x['model'] == 'GenContainer')['glows']
if not all(l.get('tag') == 'power' and l.get('off') for l in gl) or not all(g.get('tag') == 'power' and g.get('off') for g in gg):
    P.append('GenContainer lights / halos: not all power-tagged and off')
ia = [x for x in L['interactables'] if x['model'] != 'GenContainer']
ib = [x for x in L5['interactables'] if x['model'] != 'GenContainer']
if ia != ib:
    P.append('interactables of other models changed')
gi = [x for x in L['interactables'] if x['model'] == 'GenContainer']
gi5 = [x for x in L5['interactables'] if x['model'] == 'GenContainer']
if [x['child'] for x in gi] != [x['child'] for x in gi5]:
    P.append('GenContainer interactables: children or order changed')
for a, b in zip(gi, gi5):
    d = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    if set(d) - {'axis', 'min', 'max'}:
        P.append(f'GenContainer/{a["child"]}: keys {d} changed')
    if abs(sum(c * c for c in a['axis']) - 1) > 1e-6:
        P.append(f'GenContainer/{a["child"]}: axis not a unit vector')
va = {v['name']: v for v in L['viewpoints']}
vb = {v['name']: v for v in L5['viewpoints']}
for n in vb:
    d = sorted(k for k in set(va[n]) | set(vb[n]) if va[n].get(k) != vb[n].get(k))
    if n != 'GenContainer' and d:
        P.append(f'viewpoint {n} changed: {d}')
    if n == 'GenContainer' and set(d) - {'p', 'target', 'fov'}:
        P.append(f'viewpoint GenContainer: {d} changed')
if L['noColliderPrefixes'] != L5['noColliderPrefixes'] + ['Apparition']:
    P.append(f'noColliderPrefixes: {L["noColliderPrefixes"]}')
u6 = L.get('u6') or {}
if u6.get('update') != 6 or sorted(u6.get('replaced', [])) != sorted(['GenContainer'] + ITEMS3) or \
        sorted(u6.get('added', [])) != ['Apparition', 'Item_RadioSet'] or not u6.get('changes'):
    P.append(f'layout u6 block: {str(u6)[:300]}')

# materials
if M['materials'][:len(M5['materials'])] != M5['materials']:
    P.append('materials: Update 5 part changed (order or definitions)')
if set(M) != set(M5) or any(M[k] != M5[k] for k in M if k != 'materials'):
    P.append('materials file: keys other than the list changed')
new = [m['name'] for m in M['materials'][len(M5['materials']):]]
mat = {m['name']: m for m in M['materials']}
for n in new:
    if not re.fullmatch(r'M_(GCont_\w+|Item_\w+|RadioDisplay|RadioDisplayOn|Apparition)', n):
        P.append(f'new material {n}: unexpected name')
if len(mat) != len(M['materials']):
    P.append('materials: duplicate names')

# opening
for k in set(O) | set(O3):
    if k in ('interactables', 'scares', 'items'):
        continue
    if O.get(k) != O3.get(k):
        P.append(f'opening key {k} changed')
# items: only Note_GenProcedure moves (p, q) - onto the new genset panel top, recomputed here from the container's place
if [e['id'] for e in O['items']] != [e['id'] for e in O3['items']]:
    P.append('opening items: ids / order changed')
for a, b in zip(O['items'], O3['items']):
    d = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    if a['id'] == 'Note_GenProcedure':
        if d != ['p', 'q']:
            P.append(f'Note_GenProcedure: {d} changed (want p, q)')
        gc = next(e for e in L['prefabs'] if e['m'] == 'GenContainer')
        y0 = math.atan2(gc['q'][1], gc['q'][3]) * 2.0
        lx, ly, lz, yaw = 0.055, 1.752, 0.15, math.radians(4.0)       # panel top y 1.750 (x -0.03..0.14, z -0.06..0.50)
        want = [gc['p'][0] + lx * math.cos(y0) + lz * math.sin(y0), gc['p'][1] + ly, gc['p'][2] - lx * math.sin(y0) + lz * math.cos(y0)]
        if max(abs(u - v) for u, v in zip(a['p'], want)) > 2e-4:
            P.append(f'Note_GenProcedure: p {a["p"]} != {want}')
        h = (y0 + yaw) / 2.0
        if max(abs(u - v) for u, v in zip(a['q'], [0.0, math.sin(h), 0.0, math.cos(h)])) > 2e-6:
            P.append(f'Note_GenProcedure: q {a["q"]}')
    elif d:
        P.append(f'opening item {a["id"]}: {d} changed')
# notes: only the generator procedure's texts
for k in set(Nt) | set(N3):
    if k != 'notes' and Nt.get(k) != N3.get(k):
        P.append(f'notes key {k} changed')
for a, b in zip(Nt['notes'], N3['notes']):
    d = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    if a['id'] == 'gen_procedure':
        if d != ['de', 'ru']:
            P.append(f'gen_procedure: {d} changed (want de, ru)')
        for lang, words in (('de', ('DIESEL', 'Schlüssel', 'START', '100 l', '28 Stunden')),
                            ('ru', ('DIESEL', 'ключ', 'START', '100 л', '28 часов'))):
            miss = [w for w in words if w not in a[lang]]
            if miss or 'HEIZÖL' in a[lang] or '60 ' in a[lang]:
                P.append(f'gen_procedure {lang}: missing {miss} or old text left')
    elif d:
        P.append(f'note {a["id"]}: {d} changed')
if len(Nt['notes']) != len(N3['notes']):
    P.append('notes: count changed')
for a, b in zip(O['interactables'], O3['interactables']):
    d = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    if a['id'] == 'Gen_FillNeck':
        if set(d) - {'neck', 'stand', 'label', 'capacityL'}:
            P.append(f'Gen_FillNeck: {d} changed')
    elif d:
        P.append(f'opening interactable {a["id"]} changed: {d}')
if len(O['interactables']) != len(O3['interactables']):
    P.append('opening interactables: count changed')
extra = {'X02_Crossing': 'figure', 'X03_BackSeat': 'figure', 'X08_Radio': 'radio'}
for a, b in zip(O['scares'], O3['scares']):
    d = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    want = [extra[a['id']]] if a['id'] in extra else []
    if d != want:
        P.append(f'scare {a["id"]}: keys {d} changed (want {want})')
if O['scares'][1].get('figure', {}).get('model') != 'Apparition' or O['scares'][2].get('figure', {}).get('model') != 'Apparition':
    P.append('scares X02 / X03: figure model not Apparition')

# items
cat = {e['model']: e for e in I['items']}
if [e['model'] for e in I['items']] != [e['model'] for e in I3['items']] + ['Item_RadioSet']:
    P.append('items: order or set changed (want Update 3\'s + Item_RadioSet at the end)')
for a, b in zip(I['items'], I3['items']):
    d = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    if set(d) - {'tris'}:
        P.append(f'item {a["model"]}: {d} changed')
for k in set(I) | set(I3):
    if k != 'items' and I.get(k) != I3.get(k):
        P.append(f'items key {k} changed')
r = cat.get('Item_RadioSet', {})
for k in ('label', 'itemKey', 'massKg', 'collider', 'kind', 'clean', 'tris'):
    if k not in r:
        P.append(f'Item_RadioSet: no {k}')

# dressing
if Dr['notes'] != D3['notes'] or Dr['decals'] != D3['decals'] or set(Dr) != set(D3):
    P.append('dressing: notes / decals / keys changed')
added = [e for e in Dr['props'] if e not in D3['props']]
rest = [e for e in Dr['props'] if e in D3['props']]
if rest != D3['props'] or len(added) != 1 or added[0].get('model') != 'Item_RadioSet' or added[0].get('room') != 'Leitstand':
    P.append(f'dressing props: added {added}')
if Dr['props'][:-1] != D3['props']:
    P.append('dressing props: the radio is not appended at the end (Update 3\'s props must keep their indices)')
radio = added[0] if added else {}
if radio and radio['model'] not in cat:
    P.append('the radio prop\'s model is not in the catalog')
if radio:
    qn = sum(c * c for c in radio['q'])
    if abs(qn - 1) > 1e-4 or abs(radio['q'][0]) > 1e-6 or abs(radio['q'][2]) > 1e-6:
        P.append(f'radio q {radio["q"]}: not a unit yaw')

# ---- textures
tex_in_pkg = {pn.split('/')[-1] for pn in paths if pn.startswith(f'{ROOT}/Textures/') and pn.endswith('.png')}
older = {pn.split('/')[-1] for pn in list(u3guid) + list(paths5) if pn.startswith(f'{ROOT}/Textures/')}
for n in new:
    for key in ('albedo', 'emissionMap', 'mask', 'normal'):
        f = mat[n].get(key) or ''
        if f and f not in tex_in_pkg | older:
            P.append(f'material {n}: {key} {f} not found')
used_tex = {m.get(key) for m in M['materials'] for key in ('albedo', 'emissionMap', 'mask', 'normal')}
for f in sorted(tex_in_pkg - used_tex):
    P.append(f'texture {f}: no material uses it')
tex_info = {}
for pn in paths:
    if pn.startswith(f'{ROOT}/Textures/'):
        im = Image.open(io.BytesIO(asset(pn)))
        im.load()
        name = pn.split('/')[-1][:-4]
        tex_info[name] = (im.size, im.mode)
        if not name.endswith('_px'):
            P.append(f'{pn}: not a _px name')
        if max(im.size) > 2048:
            P.append(f'{pn}: {im.size} > 2048')

# ---- FBX: materials, nodes, the figure's skin and takes
import bpy, addon_utils
addon_utils.enable('io_scene_fbx')
from io_scene_fbx import parse_fbx
fbx_nodes, fbx_mats, kinds = {}, {}, {}
tmp = os.path.join(os.path.dirname(os.path.abspath(pkg)), '_check_fbx.fbx')
takes = []
for pn in sorted(paths):
    if not pn.endswith('.fbx'):
        continue
    open(tmp, 'wb').write(asset(pn))
    root, ver = parse_fbx.parse(tmp)
    find = lambda e, n: [c for c in e.elems if c.id == n]
    name = pn.split('/')[-1][:-4]
    nodes, mats, ks = set(), set(), {}
    for e in find(root, b'Objects')[0].elems:
        nm = e.props[1].split(b'\x00')[0].decode()
        if e.id == b'Model':
            nodes.add(nm)
            ks[e.props[2].decode()] = ks.get(e.props[2].decode(), 0) + 1
        if e.id == b'Material':
            mats.add(nm)
    if name == 'Apparition':
        tk = find(root, b'Takes')
        takes = sorted(e.props[0].split(b'\x00')[0].decode() for e in tk[0].elems if e.id == b'Take') if tk else []
    elif name not in nodes:
        P.append(f'{name}: no root node of its name')
    fbx_nodes[name], fbx_mats[name], kinds[name] = nodes, mats, ks
    for m in mats:
        if m not in mat:
            P.append(f'{name}: material {m} is not in Forest_Materials.json')
os.remove(tmp)
used_mats = {m for s in fbx_mats.values() for m in s}
for n in new:
    if n not in used_mats and n != 'M_RadioDisplayOn':
        P.append(f'new material {n}: no FBX uses it')
for it in L['interactables']:
    if it['model'] == 'GenContainer':
        for c in [it['child']] + list(it.get('drives') or []):
            if c not in fbx_nodes['GenContainer']:
                P.append(f'interactable GenContainer/{c} not in its FBX')
for e in O['interactables']:
    if e.get('model') == 'GenContainer':
        for c in [e.get('child')] + list(e.get('children') or []):
            if c and c not in fbx_nodes['GenContainer']:
                P.append(f'opening {e["id"]}: {c} not in GenContainer.fbx')
for lk in O['locks']:
    if lk.get('part', '').startswith('IX_Cont') and lk['part'] not in fbx_nodes['GenContainer']:
        P.append(f'lock {lk["part"]} not in GenContainer.fbx')
u3models = {pn.split('/')[-1][:-4] for pn in u3guid if pn.startswith(f'{ROOT}/Models/')}
for m in cat:
    if m not in fbx_nodes and m not in u3models:
        P.append(f'catalog model {m}: no FBX')
if kinds.get('Apparition', {}).get('LimbNode', 0) < 19 or kinds['Apparition'].get('Mesh') != 1:
    P.append(f'Apparition: nodes {kinds.get("Apparition")}')
if takes != sorted(f'Apparition_Rig|{c}' for c in ('Stand', 'Walk', 'Sit', 'SitLook')):
    P.append(f'Apparition: takes {takes}')
for n, ks in kinds.items():
    if n != 'Apparition' and set(ks) != {'Mesh'}:
        P.append(f'{n}: node kinds {ks}')
placed = {p['m'] for p in L['prefabs']}
if 'GenContainer' not in placed:
    P.append('GenContainer not placed')
for f in L['flickers']:
    if f['material'] not in mat:
        P.append(f'flicker material {f["material"]} undefined')
for n in L['power']['materialsOff'] + L['power']['materialsOn']:
    if n not in mat:
        P.append(f'power material {n} undefined')

# ---- README
r5 = asset5(f'{ROOT}/README.md').decode('utf-8').rstrip('\n')
r6 = asset(f'{ROOT}/README.md').decode('utf-8')
if not r6.startswith(r5) or '## Обновление 6' not in r6[len(r5):]:
    P.append('README: not Update 5\'s README + the section "Обновление 6"')
if re.search(r'\{[a-z_]+\}', r6[len(r5):]):
    P.append('README: unfilled placeholder')

print(f'entries {len(paths)}: {len(models)} FBX, {len(tex_in_pkg)} PNG, {sum(1 for p in paths if p.endswith(".json"))} JSON, '
      f'README {int(f"{ROOT}/README.md" in paths)}')
print('materials: new', len(new), new)
print('textures:', {k: v for k, v in sorted(tex_info.items())})
print('GenContainer nodes:', sorted(fbx_nodes.get('GenContainer', [])))
print('Apparition:', kinds.get('Apparition'), takes)
print('radio prop:', radio)
print('PROBLEMS', len(P))
for p in P:
    print('  ', p)
