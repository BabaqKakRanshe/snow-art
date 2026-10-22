import bpy, sys, json
res = {}
for tag in ('v11', 'v13'):
    bpy.ops.wm.open_mainfile(filepath=f'/home/claude/plane/out/plane_unity_{tag}.blend')
    res[tag] = {o.name: (o.type, o.parent.name if o.parent else None, len(o.data.polygons) if o.type == 'MESH' else 0)
                for o in bpy.data.objects}
a, b = res['v11'], res['v13']
print('v11', len(a), 'v13', len(b))
print('only v11:', sorted(set(a) - set(b)))
print('only v13:', sorted(set(b) - set(a)))
ch = [(n, a[n], b[n]) for n in sorted(set(a) & set(b)) if a[n] != b[n]]
print('changed:', len(ch))
for c in ch:
    print('  ', c)
