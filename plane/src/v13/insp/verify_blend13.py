import bpy, sys, math, os
path = sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=path)
O = bpy.data.objects
print('objects', len(O), 'scene', bpy.context.scene.name)
for n in ('Body', 'CargoDoor_L', 'Lens_Landing', 'Lens_Beacon_Bottom'):
    print(n, 'polys', len(O[n].data.polygons), 'mats', [m.name for m in O[n].data.materials], 'mesh', O[n].data.name)
print('materials with suffix:', [m.name for m in bpy.data.materials if m.name[-4:-3] == '.' and m.name[-3:].isdigit()])
miss = [im.name for im in bpy.data.images if im.source == 'FILE' and not os.path.exists(bpy.path.abspath(im.filepath))]
print('missing images:', miss)
print('lens imgs', [(im.name, im.filepath) for im in bpy.data.images if 'Lens' in im.name])
root = O['UtilityPlane']
print('root props', {k: root[k] for k in root.keys() if k.startswith('cargo')})
d = O['CargoDoor_L']
for t in (0.0, 0.25, 1.0):
    root['cargoDoorL'] = t; root['cargoDoorR'] = t
    dg = bpy.context.evaluated_depsgraph_get(); root.update_tag(); dg.update()
    e = d.evaluated_get(dg); er = O['CargoDoor_R'].evaluated_get(dg)
    print('t', t, 'L loc', tuple(round(v, 4) for v in e.location), 'rotz', round(math.degrees(e.rotation_euler.z), 3),
          '| R loc', tuple(round(v, 4) for v in er.location), 'rotz', round(math.degrees(er.rotation_euler.z), 3))
root['cargoDoorL'] = 0.0; root['cargoDoorR'] = 0.0
for k in ('Socket_Beacon_Bottom', 'Lens_Beacon_Bottom', 'Socket_Nav_L'):
    print(k, 'local', tuple(round(v, 4) for v in O[k].location), 'world', tuple(round(v, 4) for v in O[k].matrix_world.translation))
for l in [o for o in O if o.type == 'LIGHT' and o.name in ('Light_Beacon_Bottom', 'Light_Beacon_Top', 'Light_Nav_L')]:
    print(l.name, 'world', tuple(round(v, 4) for v in l.matrix_world.translation))
print('texts', [t.name for t in bpy.data.texts][-3:])
print('drivers on doors', [(fc.data_path, fc.array_index, fc.driver.is_valid) for fc in d.animation_data.drivers])
for n in ('Socket_Handle_CargoDoor_L_Edge', 'Socket_Handle_CargoDoor_R_Edge', 'Socket_Handle_CargoDoor_L_In'):
    o = O.get(n)
    print(n, 'parent', o.parent.name if o and o.parent else None, 'world', tuple(round(v, 4) for v in o.matrix_world.translation) if o else None,
          'colls', [c.name for c in o.users_collection] if o else None)
print('CargoDoor_L polys', len(O['CargoDoor_L'].data.polygons))
