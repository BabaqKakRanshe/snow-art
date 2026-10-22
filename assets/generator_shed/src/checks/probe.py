import bpy
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
for o in bpy.data.objects:
    if o.name in ('Shed','Door_R','Genset','Board_Door','Window_Shutter','COL_Roof_N','LIGHT_Bulk_Ceiling','Needle_Oil'):
        print(o.name, o.type, 'parent', o.parent.name if o.parent else None, 'loc', tuple(round(x,4) for x in o.location),
              'rot', tuple(round(x,4) for x in o.rotation_euler), 'scale', tuple(o.scale), 'mw_t', tuple(round(x,4) for x in o.matrix_world.translation))
        if o.type=='MESH':
            print('   attrs', [(a.name, a.domain, a.data_type) for a in o.data.attributes], 'uv', [u.name for u in o.data.uv_layers], 'mats', [m.name for m in o.data.materials])
print(len([o for o in bpy.data.objects if o.type=='MESH']))
