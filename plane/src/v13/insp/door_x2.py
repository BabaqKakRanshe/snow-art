import bpy
from collections import defaultdict
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_v9_final_v13.blend')
ob = bpy.data.objects['CargoDoor_L']
me = ob.data
W = [ob.matrix_world @ v.co for v in me.vertices]
by = defaultdict(list)
for p in me.polygons:
    m = me.materials[p.material_index].name
    for vi in p.vertices:
        by[m].append(W[vi])
for m, pts in by.items():
    xs = [abs(q.x) for q in pts]
    inner = [q for q in pts if abs(q.x) < 0.655]
    print(m, 'n', len(pts), 'min x', round(min(xs), 3), 'max', round(max(xs), 3), '| below 0.655:', len(inner),
          'y range', (round(min(q.y for q in inner), 3), round(max(q.y for q in inner), 3)) if inner else '',
          'z range', (round(min(q.z for q in inner), 3), round(max(q.z for q in inner), 3)) if inner else '')
