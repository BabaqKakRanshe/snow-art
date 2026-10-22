import bpy
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
for n in ('Snow_DoorDrift', 'Snow_Roof'):
    o = bpy.data.objects[n]
    ws = [o.matrix_world @ v.co for v in o.data.vertices]
    print(n, 'verts', len(ws), 'z', round(min(w.z for w in ws), 3), round(max(w.z for w in ws), 3), 'x', round(min(w.x for w in ws), 3), round(max(w.x for w in ws), 3))
    if o.data.shape_keys:
        for kb in o.data.shape_keys.key_blocks:
            zs = [(o.matrix_world @ d.co).z for d in kb.data]
            print('  key', kb.name, kb.value, round(min(zs), 3), round(max(zs), 3))
