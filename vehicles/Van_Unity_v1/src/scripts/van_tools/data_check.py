"""Cross-check Assets/Van/Data against the FBX export report and the JSON classes of Editor/VanSetup.cs.
python3 data_check.py <Data dir> <van_export_report.json> <VanSetup.cs>"""
import sys, json, re, collections, os
D, REP, SETUP = sys.argv[1:4]
J = lambda n: json.load(open(os.path.join(D, n)))
rep = json.load(open(REP))
nodes = {n['name'] for n in rep['nodes']}
problems = []
def need(cond, msg):
    if not cond: problems.append(msg)
P = J('parts.json')['parts']; S = J('sockets.json')['sockets']; C = J('colliders.json')['colliders']
L = J('lights.json')['lights']; Z = J('zones.json')['zones']; G = J('glass.json'); I = J('items.json'); M = J('materials.json')['materials']
for p in P:
    need(p['name'] in nodes, 'part not in FBX: ' + p['name'])
    need(not p['parent'] or p['parent'] in nodes, 'part parent missing: ' + p['name'])
for nm, arr in (('socket', S), ('collider', C), ('light', L), ('zone', Z)):
    for e in arr:
        need(not e['parent'] or e['parent'] in nodes, '%s parent missing: %s' % (nm, e.get('name', e.get('id'))))
for l in L:
    need(not l['lens'] or l['lens'] in nodes, 'lens missing: ' + l['name'])
    need(l['unityLight'] != 'Spot' or l['cookie'], 'spot without cookie: ' + l['name'])
sock = {s['name'] for s in S}
for z in Z:
    need(not z['part'] or z['part'] in nodes, 'zone part missing: ' + z['id'])
    need(not z['socket'] or z['socket'] in sock, 'zone socket missing: ' + z['id'])
for k, arr, key in (('zone id', Z, 'id'), ('socket', S, 'name'), ('light', L, 'name'), ('part', P, 'name')):
    dup = [n for n, c in collections.Counter(e[key] for e in arr).items() if c > 1]
    need(not dup, 'duplicate %s: %s' % (k, dup))
for pn in G['panes']:
    need(pn['name'] in nodes, 'pane missing: ' + pn['name'])
for k in ('mirror', 'radioDisplay'):
    need(G[k] in nodes, 'glass.json %s missing: %s' % (k, G[k]))
need(G['mirrorCamera'] in sock, 'MirrorCam socket missing')
used = {m for n in rep['nodes'] for m in n.get('materials', [])}
need(used == {m['name'] for m in M}, 'materials differ: %s' % (used ^ {m['name'] for m in M}))
part_names = {p['name'] for p in P}
for t in I['types']:
    need(t['sourcePart'] in nodes, 'item source missing: ' + t['type'])
    for q in t['parts']: need(q in part_names, 'item part missing: %s %s' % (t['type'], q))
for s in I['stows']:
    need(s['part'] in part_names, 'stow part missing: ' + s['stowId'])
bs = {n['name']: n['blendshapes'] for n in rep['nodes'] if n.get('blendshapes')}
for p in P:
    b = p['blendshape'] or p['flatBlendshape']
    if b: need(b in bs.get(p['name'], []), 'blend shape %s not on %s' % (b, p['name']))
# nested arrays (JsonUtility cannot read them)
def nested(x, path):
    if isinstance(x, list):
        for i, y in enumerate(x):
            if isinstance(y, list): problems.append('nested array at ' + path)
            nested(y, path + '[%d]' % i)
    elif isinstance(x, dict):
        for k, y in x.items(): nested(y, path + '.' + k)
for f in sorted(os.listdir(D)):
    if f.endswith('.json'): nested(json.load(open(os.path.join(D, f))), f)
# field types of the setup's JsonUtility classes
src = open(SETUP).read(); classes = {}
for m in re.finditer(r'\[Serializable\] class (\w+)', src):
    i = src.index('{', m.end()); d = 0; j = i
    while True:
        d += {'{': 1, '}': -1}.get(src[j], 0)
        if d == 0: break
        j += 1
    F = {}
    for fm in re.finditer(r'public ([\w\[\]]+) ([^;]+);', src[i + 1:j]):
        for f in fm.group(2).split(','): F[f.strip()] = fm.group(1)
    classes[m.group(1)] = F
def typed(cls, arr, label):
    bad = collections.Counter()
    for e in arr:
        for f, t in classes[cls].items():
            if f not in e: bad[(f, 'missing')] += 1; continue
            v = e[f]
            ok = {'string': isinstance(v, str), 'float': isinstance(v, (int, float)) and not isinstance(v, bool),
                  'int': isinstance(v, int) and not isinstance(v, bool), 'bool': isinstance(v, bool),
                  'float[]': isinstance(v, list) and all(isinstance(x, (int, float)) for x in v),
                  'string[]': isinstance(v, list) and all(isinstance(x, str) for x in v)}.get(t, isinstance(v, list) if t.endswith('[]') else True)
            if not ok: bad[(f, t)] += 1
    for k, c in bad.items(): problems.append('%s: field %s x%d' % (label, k, c))
    print('%-10s %4d entries, %2d fields of %s' % (label, len(arr), len(classes[cls]), cls))
typed('PartJ', P, 'parts'); typed('GearJ', [g for p in P for g in p['gears']], 'gears'); typed('SocketJ', S, 'sockets')
typed('ColliderJ', C, 'colliders'); typed('LightJ', L, 'lights'); typed('PaneJ', G['panes'], 'panes'); typed('ZoneJ', Z, 'zones')
typed('MatJ', M, 'materials'); typed('ItemTypeJ', I['types'], 'items')
# zones of parts the rig hides must not hang under those parts (they must stay to put the part back)
PP = {p['name']: p for p in P}
def hideable(p):
    return p['kind'] == 'item' or p['removable'] in ('start', 'end') or (p['kind'] == 'spin' and p['name'].startswith('Wheel_'))
def ancestors(n):
    out = []
    while n:
        out.append(n); n = PP[n]['parent'] if n in PP else next((x['parent'] for x in rep['nodes'] if x['name'] == n), '')
    return out
for z in Z:
    # *_Take zones (pick up a placed jack / blowtorch) belong on the part: hidden with it while it is in someone's hands
    if z['part'] and z['part'] in PP and hideable(PP[z['part']]) and z['part'] in ancestors(z['parent']) \
            and not z['id'].endswith('_Take'):
        problems.append('zone %s hangs under the hideable part %s' % (z['id'], z['part']))
nested = [z for z in Z if z.get('insideOf')]
print('zones inside a bigger zone at rest (insideOf, the inner one must win): %d' % len(nested))
for k, c in collections.Counter(z['insideOf'] for z in nested).most_common():
    print('  %-20s %2d: %s' % (k, c, ', '.join(z['id'] for z in nested if z['insideOf'] == k)))
print('FBX nodes %d; parts %d, sockets %d, colliders %d, lights %d, panes %d, zones %d, item types %d, stows %d, materials %d'
      % (len(nodes), len(P), len(S), len(C), len(L), len(G['panes']), len(Z), len(I['types']), len(I['stows']), len(M)))
print('PROBLEMS %d' % len(problems))
for p in problems: print('  ' + p)
