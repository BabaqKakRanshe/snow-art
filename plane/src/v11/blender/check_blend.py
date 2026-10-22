import bpy, os, sys
bpy.ops.wm.open_mainfile(filepath=sys.argv[1])
miss = []
for im in bpy.data.images:
    if im.source == 'FILE' and im.filepath:
        p = bpy.path.abspath(im.filepath)
        if not os.path.exists(p):
            miss.append((im.name, im.filepath))
print('images', len(bpy.data.images), 'missing', len(miss), miss[:5])
print('paths sample', sorted({os.path.dirname(im.filepath) for im in bpy.data.images if im.filepath}))
print('lights', sorted(o.name for o in bpy.data.objects if o.type == 'LIGHT'))
print('texts', sorted(t.name for t in bpy.data.texts))
print('cameras', sorted(o.name for o in bpy.data.objects if o.type == 'CAMERA'))
print('node groups', sorted(g.name for g in bpy.data.node_groups if g.name.startswith('LF_')))
sc = bpy.context.scene
print('engine', sc.render.engine, 'samples', sc.cycles.samples, 'frames', sc.frame_start, sc.frame_end, 'fps', sc.render.fps, 'view', sc.view_settings.view_transform, 'props', {k: sc[k] for k in ('atmosphere', 'lf_flicker', 'lf_time_offset')})
r = bpy.data.objects['UtilityPlane']; print('root rot', tuple(round(x, 4) for x in r.rotation_euler), 'loc', tuple(round(x, 4) for x in r.location))
print('hidden render colls', [c.name for c in bpy.data.collections if c.hide_render])
