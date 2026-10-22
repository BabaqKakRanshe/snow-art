import bpy, json
from mathutils import Vector
out = {}
for o in bpy.data.objects:
    if o.name.startswith(('Glow_', 'Lens_', 'LIGHT_', 'Screen_')):
        root = o
        while root.parent: root = root.parent
        rinv = root.matrix_world.inverted()
        if o.type == 'MESH' and o.data.vertices:
            vs = [rinv @ (o.matrix_world @ v.co) for v in o.data.vertices]
            c = sum(vs, Vector()) / len(vs)
            lo = [min(v[i] for v in vs) for i in range(3)]; hi = [max(v[i] for v in vs) for i in range(3)]
        else:
            c = rinv @ o.matrix_world.translation; lo = hi = list(c)
        cu = [-c.x, c.z, -c.y]
        out[o.name] = {'root': root.name, 'blender': [round(v, 4) for v in c], 'unity': [round(v, 4) for v in cu],
                       'size': [round(hi[i] - lo[i], 3) for i in range(3)], 'type': o.type,
                       'mats': [s.material.name for s in o.material_slots if s.material] if o.type == 'MESH' else []}
print('LAMPSPOTS', json.dumps(out))
