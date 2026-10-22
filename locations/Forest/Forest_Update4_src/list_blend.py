import bpy, sys, json
from collections import Counter
out = {}
for o in bpy.data.objects:
    root = o
    while root.parent: root = root.parent
    d = out.setdefault(root.name, {'types': Counter(), 'n': 0, 'mats': set(), 'props': set(), 'children': [], 'coll': [c.name for c in root.users_collection]})
    d['types'][o.type] += 1; d['n'] += 1
    if o.type == 'MESH':
        for m in o.data.materials:
            if m: d['mats'].add(m.name)
    for k in o.keys():
        if not k.startswith('_'): d['props'].add(k)
    if o.parent == root: d['children'].append((o.name, o.type))
for r, d in out.items():
    print(f"ROOT {r} coll={d['coll']} n={d['n']} types={dict(d['types'])} props={sorted(d['props'])}")
    print('   mats', sorted(d['mats']))
    ch = d['children']
    print('   children', len(ch), ch[:40])
print('scenes', [s.name for s in bpy.data.scenes], 'images', len(bpy.data.images))
