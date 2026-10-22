import bpy, json
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
C = json.load(open('/home/claude/uaz/out/gen_contract.json'))
bad = []
for o in bpy.data.objects:
    n = o.name
    par = o.parent.name if o.parent else None
    if n in C['parts']:
        if par != C['parts'][n]['parent']:
            bad.append((n, 'blend parent', par, 'contract', C['parts'][n]['parent']))
        if o.type == 'MESH' and (o.matrix_world.to_3x3() - o.matrix_world.to_3x3().to_3x3().Identity(3)).median_scale if False else False:
            pass
        r = o.matrix_world.to_euler()
        if max(abs(a) for a in r) > 1e-6:
            bad.append((n, 'rotated at rest', tuple(r)))
        if (o.matrix_world.translation - __import__('mathutils').Vector(C['parts'][n]['pivot'])).length > 1e-3:
            bad.append((n, 'origin != pivot', tuple(round(x, 4) for x in o.matrix_world.translation), C['parts'][n]['pivot']))
    elif n.startswith('COL_'):
        c = next(c for c in C['colliders'] if c['name'] == n)
        if par != c['parent']:
            bad.append((n, 'collider parent', par, c['parent']))
    elif n.startswith('LIGHT_'):
        if par != 'Shed':
            bad.append((n, 'light parent', par))
    else:
        bad.append((n, 'object not in contract', o.type))
for b in bad:
    print(b)
print('objects', len(bpy.data.objects), 'checked')
# sockets whose parent is not an object
for k, s in C['sockets'].items():
    if s['parent'] not in bpy.data.objects:
        print('socket parent missing', k, s['parent'])
# hand sockets: distance to their part geometry
from mathutils.bvhtree import BVHTree
from mathutils import Vector
far = []
for k, s in C['sockets'].items():
    if s['kind'] != 'hand':
        continue
    o = bpy.data.objects[s['parent']]
    me = o.data; me.calc_loop_triangles()
    b = BVHTree.FromPolygons([o.matrix_world @ v.co for v in me.vertices], [tuple(t.vertices) for t in me.loop_triangles])
    loc, nrm, i, d = b.find_nearest(Vector(s['pos']))
    if d > 0.03:
        far.append((round(d, 3), k))
print('hand sockets > 3 cm from their part surface:', sorted(far, reverse=True))
