import bpy, sys
bpy.ops.wm.open_mainfile(filepath=sys.argv[1])
print('scenes', [s.name for s in bpy.data.scenes], 'engine', bpy.context.scene.render.engine)
def walk(c, d=0):
    print('  ' * d + 'COLL', c.name, 'objs', len(c.objects), 'hide_render', getattr(c, 'hide_render', None))
    for ch in c.children: walk(ch, d + 1)
walk(bpy.context.scene.collection)
socks = [o for o in bpy.data.objects if o.name.startswith('Socket_')]
print('sockets', len(socks))
for o in socks:
    if any(k in o.name for k in ('Nav', 'Strobe', 'Beacon', 'Landing', 'Light_')):
        print('  ', o.name, 'parent', o.parent.name if o.parent else None, tuple(round(x, 4) for x in o.matrix_world.translation), tuple(round(x, 3) for x in o.rotation_euler))
print('lights', [o.name for o in bpy.data.objects if o.type == 'LIGHT'])
print('cameras', [o.name for o in bpy.data.objects if o.type == 'CAMERA'])
r = bpy.data.objects.get('UtilityPlane'); print('root', r and r.matrix_world)
print('lens', [o.name for o in bpy.data.objects if o.name.startswith('Lens_')])
print('images', len(bpy.data.images), [ (i.name, i.filepath) for i in bpy.data.images][:6])
print('world', bpy.context.scene.world and bpy.context.scene.world.name)
