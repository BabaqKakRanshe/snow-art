import bpy
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_unity_v11.blend')
for mn in ('M_Cockpit','M_Interior','M_Seats','M_Fittings','M_Webbing','M_Gauges','M_Annunciator','M_RadioDisplay','M_Screen','M_Airframe'):
    m=bpy.data.materials.get(mn)
    if not m: print(mn,'missing'); continue
    print('==',mn)
    for n in m.node_tree.nodes:
        extra=''
        if n.type=='TEX_IMAGE': extra=f' img={n.image.name if n.image else None} path={n.image.filepath if n.image else None} interp={n.interpolation} cs={n.image.colorspace_settings.name if n.image else None}'
        if n.type=='NORMAL_MAP': extra=f' strength={n.inputs["Strength"].default_value}'
        links=[(l.from_node.name+'.'+l.from_socket.name+'->'+l.to_node.name+'.'+l.to_socket.name) for l in m.node_tree.links if l.from_node==n]
        print('  ',n.type,n.name,extra,links)
