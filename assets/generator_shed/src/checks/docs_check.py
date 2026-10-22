import json, re
C = json.load(open('/home/claude/uaz/out/gen_contract.json'))
L = json.load(open('/home/claude/uaz/out/gen_lights.json'))
md = open('/home/claude/uaz/docs/GEN_CONTRACT.md', encoding='utf-8').read()
KIND = {'петля': 'hinge', 'неподвижно': 'static', 'крутится': 'twist', 'предмет': 'item', 'выдвигается': 'slide',
        'вращается': 'spin', 'растягивается': 'stretch'}


def vec(s):
    s = s.strip()
    if s in ('—', '-', ''):
        return None
    m = re.match(r'^\(([^)]*)\)', s)
    if not m:
        return s
    return [float(x) for x in m.group(1).split(',')]


def close(a, b, tol=0.0015):
    if a is None or b is None:
        return a is None and b is None
    return len(a) == len(b) and all(abs(x - y) <= tol for x, y in zip(a, b))


issues = []
seen = set()
for line in md.splitlines():
    if not line.startswith('| `'):
        continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    name = cells[0].strip('`')
    if name in C['parts'] and len(cells) >= 7:
        seen.add(name)
        p = C['parts'][name]
        kind = KIND.get(cells[1], cells[1])
        if kind != p['kind']:
            issues.append((name, 'kind', cells[1], p['kind']))
        if not close(vec(cells[2]), p['pivot']):
            issues.append((name, 'pivot', cells[2], p['pivot']))
        ax = vec(cells[3])
        if p['kind'] != 'static' and not close(ax, p['axis'], 0.002):
            issues.append((name, 'axis', cells[3], p['axis']))
        rng = cells[4]
        if p['range'] is not None:
            nums = [float(x.replace(',', '.')) for x in re.findall(r'-?\d+(?:[.,]\d+)?', rng.split('°')[0].split('м')[0].split('×')[0])]
            if not (len(nums) >= 2 and abs(nums[0] - p['range'][0]) < 1e-6 and abs(nums[1] - p['range'][1]) < 1e-6):
                issues.append((name, 'range', rng, p['range']))
        st = cells[5]
        if p['states'] and st != ', '.join(p['states']):
            issues.append((name, 'states', st, p['states']))
    elif name in C['sockets']:
        seen.add(name)
        s = C['sockets'][name]
        if len(cells) >= 4:
            if cells[1].strip('`') != (s['parent'] or ''):
                issues.append((name, 'socket parent', cells[1], s['parent']))
            if not close(vec(cells[2]), s['pos'], 0.0015):
                issues.append((name, 'socket pos', cells[2], s['pos']))
            d = vec(cells[3])
            if s.get('dir') is not None and not close(d, [float(x) for x in s['dir']], 0.006):
                issues.append((name, 'socket dir', cells[3], s.get('dir')))
    elif name.startswith('COL_'):
        c = next((c for c in C['colliders'] if c['name'] == name), None)
        if c is None:
            issues.append((name, 'collider missing in json', '', ''))
            continue
        seen.add(name)
        if not close(vec(cells[2]), c['center'], 0.0015) or not close(vec(cells[3]), c['size'], 0.0015):
            issues.append((name, 'collider', cells[2:4], (c['center'], c['size'])))
    elif name.startswith('LIGHT_'):
        seen.add(name)
for k in C['parts']:
    if k not in seen:
        issues.append((k, 'part not in doc tables', '', ''))
for k in C['sockets']:
    if k not in seen and not md.count('`%s`' % k):
        issues.append((k, 'socket not mentioned in doc', '', ''))
for c in C['colliders']:
    if c['name'] not in seen:
        issues.append((c['name'], 'collider not in doc', '', ''))
for i in issues:
    print(i)
print('checked', len(seen))
# names mentioned in the doc that do not exist
names = set(re.findall(r'`([A-Za-z][A-Za-z0-9_]*(?:_[A-Za-z0-9]+)+|[A-Z][a-z]+[A-Z][A-Za-z]+)`', md))
known = set(C['parts']) | set(C['sockets']) | {c['name'] for c in C['colliders']} | {l['socket'] for l in L['lights']}
print('doc names not in json:', sorted(n for n in names if n not in known))
# names referenced in json notes that do not exist
notes = ' '.join([p['note'] if isinstance(p['note'], str) else '' for p in C['parts'].values()] +
                 [s.get('note', '') for s in C['sockets'].values()] + [L['note']] + [l['desc'] for l in L['lights']])
refs = set(re.findall(r'\b([A-Z][A-Za-z]+_[A-Za-z0-9_]+)\b', notes))
print('json-note refs not existing:', sorted(r for r in refs if r not in known))
