import bpy, sys
bpy.ops.wm.open_mainfile(filepath=sys.argv[1])
def chain(o):
    c = []
    while o: c.append(o.name); o = o.parent
    return ' <- '.join(c)
for n in ('Sockets', 'Cockpit', 'Socket_Nav_L', 'Socket_Light_Flood', 'Body', 'WinterKit', 'Lens_Nav_L', 'Lens_Dome'):
    o = bpy.data.objects.get(n); print(n, '|', chain(o) if o else None, '| rot', tuple(round(x, 3) for x in o.rotation_euler) if o else '')
print('roots', [o.name for o in bpy.data.objects if o.parent is None and o.type in ('EMPTY', 'MESH')][:20])
for ln in ('Lens_Nav_L', 'Lens_Beacon_Top', 'Lens_Dome', 'Lens_Landing'):
    o = bpy.data.objects[ln]
    for s in o.material_slots:
        m = s.material
        print(ln, 'mat', m.name, [ (n.type, n.name) for n in m.node_tree.nodes][:8])
for mn in ('M_Gauges', 'M_RadioDisplay', 'M_Annunciator', 'M_Screen', 'M_Lens', 'M_LensRed'):
    m = bpy.data.materials.get(mn)
    if m:
        p = [n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED']
        if p:
            p = p[0]; ec = p.inputs['Emission Color']
            print(mn, 'emis strength', p.inputs['Emission Strength'].default_value, 'color linked', ec.is_linked, tuple(round(x, 3) for x in ec.default_value))
glass = [o.name for o in bpy.data.objects if 'Glass' in o.name and o.type == 'MESH']
print('glass objs', len(glass), glass[:12])
print('mats with Glass', [m.name for m in bpy.data.materials if 'lass' in m.name])
print('scene props', sc.frame_start if (sc := bpy.context.scene) else None, sc.frame_end, sc.render.fps, sc.view_settings.view_transform)
