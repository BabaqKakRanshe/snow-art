import bpy
from collections import Counter
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_v9_final_v13.blend')
for n in ('CargoDoor_L', 'CargoDoor_L__Glass'):
    ob = bpy.data.objects[n]
    xs = [round(abs((ob.matrix_world @ v.co).x), 3) for v in ob.data.vertices]
    c = Counter(round(x, 2) for x in xs)
    print(n, len(xs), 'min', min(xs), 'max', max(xs), sorted(c.items()))
