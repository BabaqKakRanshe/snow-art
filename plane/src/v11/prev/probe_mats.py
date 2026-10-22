import bpy, sys
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_unity_v10.blend')
for m in bpy.data.materials:
    if not m.use_nodes: print('MAT', m.name, 'no nodes'); continue
    pr = [n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED']
    info = []
    for p in pr:
        for k in ('Base Color', 'Metallic', 'Roughness', 'Emission Color', 'Emission Strength', 'Alpha', 'Transmission Weight'):
            if k in p.inputs:
                i = p.inputs[k]
                info.append('%s=%s' % (k, 'LINK' if i.is_linked else (tuple(round(x, 3) for x in i.default_value) if hasattr(i.default_value, '__len__') else round(i.default_value, 3))))
    users = [o.name for o in bpy.data.objects if o.type == 'MESH' and any(s.material == m for s in o.material_slots)][:6]
    print('MAT', m.name, '|', ' '.join(info), '| users', users)
imgs = sorted(set(bpy.path.basename(i.filepath) for i in bpy.data.images if i.filepath))
print('IMAGES', imgs)
tops = [o.name for o in bpy.data.objects if o.parent is None]
print('TOP', len(tops), tops[:60])
