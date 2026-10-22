import bpy
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/v12r2/deliv/UtilityPlane_Unity_v12/Blender/UtilityPlane_v12_lights.blend')
for l in [o for o in bpy.data.objects if o.type == 'LIGHT']:
    ll = l.light_linking
    rc = ll.receiver_collection; bc = ll.blocker_collection
    def desc(c):
        if c is None: return None
        return (c.name, [o.name for o in c.objects][:8], [(ch.name) for ch in c.children][:4],
                [ (o.name, c.collection_objects[o.name].light_linking.link_state) if hasattr(c, 'collection_objects') else o.name for o in c.objects][:6])
    print(l.name, 'local', tuple(round(v, 4) for v in l.location), 'blockers', desc(bc), 'receivers', desc(rc))
