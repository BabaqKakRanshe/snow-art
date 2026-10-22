import bpy, sys
path = sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=path)
O = bpy.data.objects
print('scenes', [s.name for s in bpy.data.scenes], 'objects', len(O))
for n in ('UtilityPlane', 'Body', 'CargoDoor_L', 'Lens_Beacon_Bottom', 'Socket_Beacon_Bottom', 'Sockets'):
    ob = O.get(n)
    if ob: print(n, ob.type, 'parent', ob.parent.name if ob.parent else None, 'loc', tuple(round(v, 4) for v in ob.matrix_world.translation),
                 'mats', [m.name for m in ob.data.materials] if ob.type == 'MESH' else '')
lights = [o for o in O if o.type == 'LIGHT']
print('lights', len(lights))
for l in lights[:30]:
    print('  ', l.name, 'parent', l.parent.name if l.parent else None, tuple(round(v, 3) for v in l.matrix_world.translation), l.data.type)
for mn in ('M_Light_Red', 'M_Light_Beacon', 'M_Light_Landing'):
    m = bpy.data.materials.get(mn)
    if m:
        print(mn, [(n.type, n.name) for n in m.node_tree.nodes])
        pb = [n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED']
        if pb:
            p = pb[0]; print('   base', tuple(round(v, 3) for v in p.inputs['Base Color'].default_value), 'em', tuple(round(v, 3) for v in p.inputs['Emission Color'].default_value), p.inputs['Emission Strength'].default_value, 'links', [(l.from_node.name, l.to_socket.name) for l in m.node_tree.links])
print('texts', [t.name for t in bpy.data.texts])
print('images', len(bpy.data.images), [i.filepath for i in bpy.data.images][:5])
