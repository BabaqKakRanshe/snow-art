import bpy
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_v9_final_v11.blend')
O = bpy.data.objects
for n in ['src_Fuselage','src_Fin','src_Wing','src_WingTE_TipL','src_FuseDetails','src_WingDetails','src_Dorsal','src_Lights','CargoDoor_L','src_Struts','src_Stabilizer','src_Antennas']:
    o = O[n]; me = o.data
    print(n, 'uv', [u.name for u in me.uv_layers], 'mats', [m.name for m in me.materials], 'attrs', [a.name for a in me.attributes if not a.name.startswith('.')][:12], 'faces', len(me.polygons), 'coll', [c.name for c in o.users_collection], 'parent', o.parent.name if o.parent else None)
print('collections', [c.name for c in bpy.data.collections])
